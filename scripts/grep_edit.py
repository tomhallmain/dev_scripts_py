"""Search for files or grep content and optionally open matches in an editor.

Provides two entry points mirroring the original ds:vi and ds:grepvi commands:

- ``find_and_edit``: search for *files* by name pattern, list or open them.
- ``grep_and_edit``: search for *content* inside files, list or open matches.

The editor is resolved from the ``$EDITOR`` environment variable, falling
back to ``vim``, ``vi``, ``code``, ``notepad`` (Windows), or ``nano`` in
that order.
"""

import fnmatch
import os
import re
import shutil
import subprocess
import sys


def _resolve_editor():
    """Return the first available editor command."""
    editor = os.environ.get("EDITOR")
    if editor and shutil.which(editor):
        return editor
    for candidate in ("vim", "vi", "code", "notepad" if os.name == "nt" else "nano"):
        if shutil.which(candidate):
            return candidate
    return None


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


def find_and_edit(search, directory=".", edit_all=False, edit=True):
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
    """
    directory = os.path.abspath(directory)
    matches = []

    for filepath in _collect_files(directory):
        basename = os.path.basename(filepath)
        if fnmatch.fnmatch(basename, search) or search in basename:
            matches.append(filepath)

    if not matches:
        print(f"No files matching '{search}' found in {directory}")
        return

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


def grep_and_edit(search, target=".", edit_all=False, edit=True):
    """Grep for *search* in files under *target* and optionally open matches.

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
    """
    target = os.path.abspath(target)
    pattern = re.compile(search)
    file_matches = {}

    if os.path.isfile(target):
        files = [target]
    else:
        files = list(_collect_files(target))

    for filepath in files:
        try:
            with open(filepath, "r", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    if pattern.search(line):
                        file_matches.setdefault(filepath, []).append((lineno, line.rstrip()))
        except (OSError, UnicodeDecodeError):
            continue

    if not file_matches:
        print(f"No matches for '{search}' in {target}")
        return

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
