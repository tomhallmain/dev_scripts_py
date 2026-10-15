"""Ensure repo root is on sys.path for `import scripts.*` when running pytest."""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(autouse=True)
def _isolate_user_state(tmp_path_factory, monkeypatch):
    """Keep every test away from the user's tool cache and global git config.

    Variables are set, not defaulted, so values exported in the developer's
    shell can't reach a test. The directory is outside the test's tmp_path,
    which some tests scan for repos. Git's system config is left alone.
    """
    from scripts import tool_availability

    state_dir = tmp_path_factory.mktemp("ds-user-state")
    monkeypatch.setenv("DS_CACHE_DIR", str(state_dir / "cache"))
    # Tests exercise the cache file itself, not the bypass.
    monkeypatch.delenv("DS_REFRESH_TOOL_CACHE", raising=False)
    # The in-process cache would otherwise carry results between tests.
    monkeypatch.setattr(tool_availability, "_CACHE", None)

    git_config = state_dir / "gitconfig"
    git_config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(git_config))


@pytest.fixture(autouse=True)
def _suppress_utils_debug():
    from scripts.utils import Utils

    prev = Utils.DEBUG
    Utils.DEBUG = False
    yield
    Utils.DEBUG = prev
