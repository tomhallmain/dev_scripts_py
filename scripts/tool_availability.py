"""
Cache whether commands exist on PATH — roughly the idea of ``ds:nset`` + ``type`` for binaries.

Results are stored under the user cache dir so later ``ds`` invocations skip repeated
``shutil.which`` / subprocess probes. Set ``DS_REFRESH_TOOL_CACHE=1`` to ignore the cache file
for that process.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

_CACHE: Dict[str, bool] | None = None


def _cache_file() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        p = Path(base) / "dev_scripts_py" / "tool_availability.json"
    else:
        p = Path.home() / ".cache" / "dev_scripts_py" / "tool_availability.json"
    return p


def _load_cache() -> Dict[str, bool]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if os.environ.get("DS_REFRESH_TOOL_CACHE", "").lower() in ("1", "true", "yes"):
        _CACHE = {}
        return _CACHE
    path = _cache_file()
    if path.is_file():
        try:
            raw: Any = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                _CACHE = {str(k): bool(v) for k, v in raw.items()}
            else:
                _CACHE = {}
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            _CACHE = {}
    else:
        _CACHE = {}
    return _CACHE


def _save_cache(data: Dict[str, bool]) -> None:
    path = _cache_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass


def is_command_available(name: str) -> bool:
    """
    Return whether ``name`` is on PATH, using a persistent JSON cache between runs.

    This matches the common shell pattern ``command -v name`` / ``type name`` for executables
    (not shell functions).
    """
    cache = _load_cache()
    if name in cache:
        return cache[name]
    found = shutil.which(name) is not None
    cache[name] = found
    _save_cache(cache)
    return found
