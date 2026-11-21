"""Removes the folders older builds of the standalone executable unpacked to.

The onefile build unpacks to ``<cache dir>/dev_scripts_py/unpacked/dsp-<build id>``
(``build_exe.py``), one folder per build, and Nuitka never removes them. Only a
compiled build runs this, and only on siblings of its own folder inside a folder
named ``unpacked``. A build runs its executable from its own folder, so a folder
holding the executable of a running process is skipped. Each folder is renamed to
``<name>.removing`` before it is deleted: a delete cut short is finished at the next
start, and on Windows the rename fails while a running exe holds files there.
macOS and Linux allow that rename, so there nothing is removed when processes
cannot be listed.

``dsp`` is a short-lived command, so the cleanup runs on a non-daemon thread that
the interpreter waits for at exit; a daemon thread would be cut off mid-delete. The
process list (the slow part) is read only when an older folder exists. Nothing is
printed: the command's own output may be captured, e.g. ``cd "$(dsp cd)"``.
``DS_SKIP_UNPACK_CLEANUP`` turns it off, which the build's smoke test does.
"""
import logging
import os
import shutil
import sys
import threading
from typing import List, Optional, Set

from scripts.build_info import RESOURCE_ROOT

IS_BUILD = "__compiled__" in globals()
UNPACK_PARENT_NAME = "unpacked"
UNPACK_DIR_PREFIX = "dsp-"
SKIP_ENV = "DS_SKIP_UNPACK_CLEANUP"
_REMOVING_SUFFIX = ".removing"
_IS_WINDOWS = sys.platform == "win32"

logger = logging.getLogger("dsp.unpack_cleanup")
logger.addHandler(logging.NullHandler())


def _normalize(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def _long_path(path: str) -> str:
    """*path* with Windows 8.3 short names (``DSP-20~1``) expanded. A build's
    ``__file__`` can hold the short name of its unpack folder, which
    ``os.listdir`` never returns."""
    if not _IS_WINDOWS:
        return path
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.kernel32.GetLongPathNameW(path, buffer, len(buffer)):
            return buffer.value
    except (AttributeError, OSError):
        pass
    return path


def _is_same_folder(path: str, other: str) -> bool:
    try:
        return os.path.samefile(path, other)
    except OSError:
        return _normalize(path) == _normalize(other)


def _running_executables() -> Optional[Set[str]]:
    """Normalized executable paths of the running processes this user can see,
    or None when they cannot be listed."""
    try:
        import psutil
    except ImportError:
        return None
    try:
        # A process this user may not inspect reports exe as None.
        return {_normalize(p.info["exe"]) for p in psutil.process_iter(["exe"]) if p.info.get("exe")}
    except Exception as e:
        logger.warning(f"Could not list running processes: {e}")
        return None


def _holds_running_executable(folder: str, executables: Set[str]) -> bool:
    prefix = _normalize(folder) + os.sep
    return any(exe.startswith(prefix) for exe in executables)


def _is_unpack_dir(name: str) -> bool:
    return name.startswith(UNPACK_DIR_PREFIX)


def _enabled() -> bool:
    return IS_BUILD and not os.environ.get(SKIP_ENV)


def remove_stale_unpack_dirs() -> List[str]:
    """Delete the running build's sibling build folders; returns the paths removed."""
    if not _enabled():
        return []
    current = _long_path(RESOURCE_ROOT)
    parent = os.path.dirname(_normalize(current))
    if (os.path.basename(parent) != _normalize(UNPACK_PARENT_NAME)
            or not _is_unpack_dir(os.path.basename(os.path.normpath(current)))):
        logger.warning(f"Not cleaning up old build folders: {current} is not an unpack folder")
        return []
    try:
        names = sorted(os.listdir(parent))
    except OSError as e:
        logger.error(f"Could not list {parent}: {e}")
        return []
    stale = [os.path.join(parent, name) for name in names
             if _is_unpack_dir(name) and os.path.isdir(os.path.join(parent, name))
             and not _is_same_folder(os.path.join(parent, name), current)]
    if not stale:
        return []
    executables = _running_executables()
    if executables is None:
        if not _IS_WINDOWS:
            logger.info("Not cleaning up old build folders: running processes cannot be listed")
            return []
        executables = set()  # the rename alone guards running builds
    removed = []
    for path in stale:
        if _holds_running_executable(path, executables):
            logger.info(f"Not removing {path}: a running build uses it")
            continue
        if not path.endswith(_REMOVING_SUFFIX):
            renamed = path + _REMOVING_SUFFIX
            try:
                os.rename(path, renamed)
            except OSError as e:
                logger.info(f"Not removing {path}, possibly in use: {e}")
                continue
            path = renamed
        shutil.rmtree(path, ignore_errors=True)
        if os.path.exists(path):
            logger.warning(f"Could not fully remove {path}; trying again at the next start")
        else:
            logger.info(f"Removed old build folder {path}")
            removed.append(path)
    return removed


def _run() -> None:
    try:
        remove_stale_unpack_dirs()
    except Exception:
        logger.exception("Cleaning up old build folders failed")


def start_unpack_cleanup() -> Optional[threading.Thread]:
    """Run the cleanup on a non-daemon thread in a build; returns the thread, or
    None in a source checkout or when turned off."""
    if not _enabled():
        return None
    thread = threading.Thread(target=_run, name="unpack-cleanup", daemon=False)
    thread.start()
    return thread
