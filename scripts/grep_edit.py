"""Search for files or grep content and optionally open matches in an editor.

Provides two entry points mirroring the original ds:vi and ds:grepvi commands:

- ``find_and_edit``: search for *files* by name pattern, list or open them.
- ``grep_and_edit``: search for *content* inside files, list or open matches.

The editor is resolved from the ``$EDITOR`` environment variable, falling
back to ``vim``, ``vi``, ``code``, ``notepad`` (Windows), or ``nano`` in
that order.

Content search prefers ripgrep (``rg``) when available; the result of the
availability check is cached in ``app_info_cache`` so subsequent runs skip
the probe.
"""

import fnmatch
import os
import re
import shutil
import subprocess
import sys


# ---------------------------------------------------------------------------
# Tool resolution helpers
# ---------------------------------------------------------------------------

def _resolve_editor():
    """Return the first available editor command."""
    editor = os.environ.get("EDITOR")
    if editor and shutil.which(editor):
        return editor
    for candidate in ("vim", "vi", "code", "notepad" if os.name == "nt" else "nano"):
        if shutil.which(candidate):
            return candidate
    return None


def _has_ripgrep():
    """Check whether ripgrep is available, using the cache when possible.

    The first call probes the system and persists the result so that later
    invocations are essentially free.
    """
    from support.app_info_cache import app_info_cache

    cached = app_info_cache.get("has_ripgrep")
    if cached is not None:
        return cached

    available = shutil.which("rg") is not None
    app_info_cache.set("has_ripgrep", available)
    app_info_cache.store()
    return available


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def _collect_files(directory, recurse=True):
    """Yield all file paths under *directory*."""
    if recurse:
        for dirpath, _, filenames in os.walk(directory):
            for fname in filenames:
                yield os.path.join(dirpath, fname)
    else:
        for entry in os.scandir(directory):
            if entry.is_file():
                yield entry.path


# ---------------------------------------------------------------------------
# Grep backends
# ---------------------------------------------------------------------------

def _grep_ripgrep(pattern, target):
    """Run ripgrep and return ``{filepath: [(lineno, line), ...]}``.

    Returns *None* if ``rg`` exits with an unexpected error so the caller
    can fall back to the Python backend.
    """
    cmd = ["rg", "--line-number", "--no-heading", "--color=never", pattern, target]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except OSError:
        return None

    if result.returncode not in (0, 1):
        # 0 = matches found, 1 = no matches, anything else = error
        return None

    file_matches = {}
    for line in result.stdout.splitlines():
        # rg output: filepath:lineno:content
        # On Windows, paths start with a drive letter (e.g. "C:\...") which
        # contains a colon, so we skip past it before splitting.
        if len(line) >= 2 and line[0].isalpha() and line[1] == ":":
            rest = line[2:]
            parts = rest.split(":", 2)
            if len(parts) < 3:
                continue
            filepath = line[0] + ":" + parts[0]
            lineno_str, content = parts[1], parts[2]
        else:
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            filepath, lineno_str, content = parts[0], parts[1], parts[2]

        try:
            lineno = int(lineno_str)
        except ValueError:
            continue
        file_matches.setdefault(filepath, []).append((lineno, content))
    return file_matches


def _grep_python(pattern, target):
    """Pure-Python fallback grep. Returns ``{filepath: [(lineno, line), ...]}``."""
    compiled = re.compile(pattern)
    file_matches = {}

    if os.path.isfile(target):
        files = [target]
    else:
        files = list(_collect_files(target))

    for filepath in files:
        try:
            with open(filepath, "r", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    if compiled.search(line):
                        file_matches.setdefault(filepath, []).append((lineno, line.rstrip()))
        except (OSError, UnicodeDecodeError):
            continue

    return file_matches


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_and_edit(search, directory=".", edit_all=False, edit=True,
                  print_matches=None):
    """Search for files whose name matches *search* (glob or substring).

    Parameters
    ----------
    search : str
        Glob pattern or plain substring to match against file names.
    directory : str
        Root directory to search.
    edit_all : bool
        When *True*, open **all** matching files in the editor at once.
        When *False* (default), list matches and open only the first.
    edit : bool
        When *False*, only list matches without opening an editor.
    print_matches : bool or None
        Explicitly control whether matches are printed.  When *None*
        (default), matches are printed only if *edit* is False.
    """
    directory = os.path.abspath(directory)
    should_print = print_matches if print_matches is not None else (not edit)
    matches = []

    for filepath in _collect_files(directory):
        basename = os.path.basename(filepath)
        if fnmatch.fnmatch(basename, search) or search in basename:
            matches.append(filepath)

    if not matches:
        print(f"No files matching '{search}' found in {directory}")
        return

    if should_print:
        for m in matches:
            print(m)

    if not edit:
        return

    editor = _resolve_editor()
    if not editor:
        print("No editor found. Set $EDITOR or install vim/code/nano.", file=sys.stderr)
        return

    if edit_all:
        subprocess.run([editor] + matches)
    else:
        subprocess.run([editor, matches[0]])


def grep_and_edit(search, target=".", edit_all=False, edit=True,
                  print_matches=None):
    """Grep for *search* in files under *target* and optionally open matches.

    Uses ripgrep (``rg``) when available for speed, falling back to a
    pure-Python implementation otherwise.

    Parameters
    ----------
    search : str
        Regex pattern to search for inside file contents.
    target : str
        A file path or directory to search.  When a directory is given every
        file underneath is searched recursively.
    edit_all : bool
        Open all files that contain a match (instead of just the first).
    edit : bool
        When *False*, only print matching lines without opening an editor.
    print_matches : bool or None
        Explicitly control whether matches are printed.  When *None*
        (default), matches are printed only if *edit* is False.
    """
    target = os.path.abspath(target)
    should_print = print_matches if print_matches is not None else (not edit)

    file_matches = None
    if _has_ripgrep():
        file_matches = _grep_ripgrep(search, target)

    if file_matches is None:
        file_matches = _grep_python(search, target)

    if not file_matches:
        print(f"No matches for '{search}' in {target}")
        return

    if should_print:
        for filepath, hits in file_matches.items():
            for lineno, line in hits:
                print(f"{filepath}:{lineno}: {line}")

    if not edit:
        return

    editor = _resolve_editor()
    if not editor:
        print("No editor found. Set $EDITOR or install vim/code/nano.", file=sys.stderr)
        return

    matched_files = list(file_matches.keys())
    if edit_all:
        subprocess.run([editor] + matched_files)
    else:
        first_file = matched_files[0]
        first_line = file_matches[first_file][0][0]
        if editor in ("vim", "vi"):
            subprocess.run([editor, f"+{first_line}", first_file])
        elif editor == "code":
            subprocess.run([editor, "--goto", f"{first_file}:{first_line}"])
        else:
            subprocess.run([editor, first_file])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: grep_edit.py <search> [file|dir] [--all]")
        sys.exit(1)
    _search = sys.argv[1]
    _target = sys.argv[2] if len(sys.argv) > 2 else "."
    _all = "--all" in sys.argv
    grep_and_edit(_search, _target, edit_all=_all)
