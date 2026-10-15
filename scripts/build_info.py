"""
The ds version and, in a standalone build, the build info bundled with it.

Both files live at the resource root: the repo root in a checkout, and the
unpack folder's root in a build, where build_exe.py bundles them. This module
is one level below that root in both cases. Standard library only.
"""
import json
import os

RESOURCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = "VERSION"
BUILD_INFO_FILE = "build_info.json"


def app_version() -> str:
    """The VERSION file's contents; raises OSError when it can't be read."""
    with open(os.path.join(RESOURCE_ROOT, VERSION_FILE), "r", encoding="utf-8") as f:
        return f.read().strip()


def build_info():
    """The bundled build info as a dict, or None outside a build."""
    path = os.path.join(RESOURCE_ROOT, BUILD_INFO_FILE)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def describe() -> str:
    """Version and build details for ``ds version``; never raises on a missing
    or unreadable file, so a damaged build can still say what it is."""
    try:
        lines = [f"ds {app_version()}"]
    except OSError as e:
        lines = [f"ds (version unreadable: {e})"]
    try:
        info = build_info()
    except (OSError, ValueError) as e:
        lines.append(f"Build info unreadable: {e}")
        return "\n".join(lines)
    if info is None:
        lines[0] += " (source checkout)"
        return "\n".join(lines)

    source = info.get("source", {})
    commit = (source.get("commit") or "")[:10] or "an unknown commit"
    if source.get("changes"):
        commit += " with uncommitted changes"
    elif source.get("changes") is None:
        commit += " (uncommitted changes unknown)"
    lines.append(f"Build {info.get('build_id', '?')} from {commit}")
    packages = ", ".join(f"{name} {v}" for name, v in sorted(info.get("packages", {}).items()))
    lines.append(f"Python {info.get('python', '?')}" + (f"; {packages}" if packages else ""))
    return "\n".join(lines)
