"""Ensure repo root is on sys.path for `import scripts.*` when running pytest."""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(autouse=True)
def _suppress_utils_debug():
    from scripts.utils import Utils

    prev = Utils.DEBUG
    Utils.DEBUG = False
    yield
    Utils.DEBUG = prev
