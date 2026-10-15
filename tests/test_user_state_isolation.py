"""Checks that conftest's isolation keeps tests out of the user's real state."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import tool_availability


def _real_cache_file(monkeypatch) -> Path:
    with monkeypatch.context() as m:
        m.delenv("DS_CACHE_DIR")
        return tool_availability._cache_file()


def _snapshot(path: Path):
    return (path.stat().st_mtime_ns, path.read_bytes()) if path.is_file() else None


def test_tool_cache_goes_to_isolated_dir(monkeypatch):
    isolated = Path(os.environ["DS_CACHE_DIR"])
    real = _real_cache_file(monkeypatch)
    assert isolated not in real.parents
    before = _snapshot(real)

    tool_availability.is_command_available("ds-surely-not-a-real-command")

    assert tool_availability._cache_file() == isolated / "tool_availability.json"
    assert (isolated / "tool_availability.json").is_file()
    assert _snapshot(real) == before


def test_in_process_cache_starts_empty():
    assert tool_availability._CACHE is None


def test_refresh_bypass_is_not_inherited():
    assert "DS_REFRESH_TOOL_CACHE" not in os.environ


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_global_git_config_is_empty():
    config = Path(os.environ["GIT_CONFIG_GLOBAL"])
    assert config.read_text(encoding="utf-8") == ""
    # Exit code 1 means no entries; git older than 2.32 ignores
    # GIT_CONFIG_GLOBAL and would list the user's config here.
    result = subprocess.run(["git", "config", "--global", "--list"], capture_output=True, text=True)
    assert result.stdout == ""
