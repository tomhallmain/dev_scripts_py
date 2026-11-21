"""``ds asgn`` -- print lines that contain an assignment (``name = value``)."""
import re
from typing import Iterable, Iterator

# A name of word characters or ``<>[]-``, an ``=`` with optional spaces, then a value.
ASSIGNMENT_RE = re.compile(r"[\w<>\[\]\-]+ *= *\S+")


def assignment_lines(lines: Iterable[str]) -> Iterator[str]:
    """``lineno:line`` for each matching line, numbered from 1."""
    for lineno, line in enumerate(lines, start=1):
        line = line.rstrip("\n").rstrip("\r")
        if ASSIGNMENT_RE.search(line):
            yield f"{lineno}:{line}"
