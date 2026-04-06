"""Search for files or grep content and optionally open matches in an editor.

Provides two entry points mirroring the original ds:vi and ds:grepvi commands:

- ``find_and_edit``: search for *files* by name pattern, list or open them.
- ``grep_and_edit``: search for *content* inside files, list or open matches.

The editor is resolved from the ``$EDITOR`` environment variable, falling
back to ``vim``, ``vi``, ``code``, ``notepad`` (Windows), or ``nano`` in
that order.

Content search delegates to :mod:`scripts.tool_based_search` so backend/tool
selection stays consistent across commands.
"""

import fnmatch
import os
import subprocess
import sys

from scripts.tool_availability import resolve_editor


# ---------------------------------------------------------------------------
# Tool resolution helper
# ---------------------------------------------------------------------------

# Keep a local alias for easier test patching.
_resolve_editor = resolve_editor


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

    Uses :mod:`scripts.tool_based_search` (same backend selection as other search commands).

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
    from scripts.tool_based_search import collect_search_hits

    target = os.path.abspath(target)
    should_print = print_matches if print_matches is not None else (not edit)
    _code, file_matches = collect_search_hits(
        (target,),
        search,
        print_matches=False,
    )

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
