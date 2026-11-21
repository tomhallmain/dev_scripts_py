"""``ds diff`` -- side-by-side line diff, optionally coloured, without an external ``diff``.

Each output row shows the left line, a marker and the right line: ``|`` for a changed line,
``<`` for a line only on the left, ``>`` for a line only on the right, and a space for a
common line. Lines are compared ignoring changes in the amount of whitespace (as with
``diff -b``), and tabs are expanded before layout.
"""
import difflib
import re
from typing import List, Sequence, Tuple

RESET = "\033[0m"
CYAN = "\033[36m"
RED = "\033[31m"
MAGENTA = "\033[35m"

_SPACE_RUN = re.compile(r"[ \t]+")

# One aligned row: (left text, marker, right text).
Row = Tuple[str, str, str]


def _compare_key(line: str) -> str:
    return _SPACE_RUN.sub(" ", line).rstrip()


def text_to_lines(text: str) -> List[str]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line.rstrip("\r") for line in lines]


def literal_to_lines(value: str) -> List[str]:
    """A literal argument, with ``\\n`` and ``\\t`` escapes interpreted as ``echo -e`` does."""
    return text_to_lines(value.replace("\\n", "\n").replace("\\t", "\t"))


def diff_rows(left: Sequence[str], right: Sequence[str]) -> List[Row]:
    matcher = difflib.SequenceMatcher(
        None, [_compare_key(x) for x in left], [_compare_key(x) for x in right], autojunk=False
    )
    rows: List[Row] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            rows.extend((left[i], " ", right[j]) for i, j in zip(range(i1, i2), range(j1, j2)))
        elif tag == "delete":
            rows.extend((left[i], "<", "") for i in range(i1, i2))
        elif tag == "insert":
            rows.extend(("", ">", right[j]) for j in range(j1, j2))
        else:
            n_left, n_right = i2 - i1, j2 - j1
            for k in range(max(n_left, n_right)):
                if k < n_left and k < n_right:
                    rows.append((left[i1 + k], "|", right[j1 + k]))
                elif k < n_left:
                    rows.append((left[i1 + k], "<", ""))
                else:
                    rows.append(("", ">", right[j1 + k]))
    return rows


def _colour_changed(left: str, right: str) -> Tuple[str, str]:
    """Colour the characters that differ between a changed pair: left cyan, right red."""
    matcher = difflib.SequenceMatcher(None, left, right, autojunk=False)
    out_left, out_right = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out_left.append(left[i1:i2])
            out_right.append(right[j1:j2])
            continue
        if i2 > i1:
            out_left.append(CYAN + left[i1:i2] + RESET)
        if j2 > j1:
            out_right.append(RED + right[j1:j2] + RESET)
    return "".join(out_left), "".join(out_right)


def render_rows(rows: Sequence[Row], width: int, *, suppress_common: bool = False,
                colour: bool = False) -> List[str]:
    """Lay rows out in two columns filling ``width``; trailing whitespace is trimmed."""
    column = max((width - 3) // 2, 1)
    out: List[str] = []
    for left, marker, right in rows:
        if marker == " " and suppress_common:
            continue
        left = left.expandtabs()[:column]
        right = right.expandtabs()[:column]
        padding = " " * (column - len(left))
        if not colour or marker == " ":
            out.append(f"{left}{padding} {marker} {right}".rstrip())
        elif marker == "<":
            out.append(f"{CYAN}{left}{RESET}{padding} {marker}".rstrip())
        elif marker == ">":
            out.append(f"{padding} {marker} {RED}{right}{RESET}")
        else:
            c_left, c_right = _colour_changed(left, right)
            out.append(f"{c_left}{padding} {MAGENTA}{marker}{RESET} {c_right}")
    return out


def side_by_side(left: Sequence[str], right: Sequence[str], width: int, *,
                 suppress_common: bool = False, colour: bool = False) -> List[str]:
    return render_rows(diff_rows(left, right), width,
                       suppress_common=suppress_common, colour=colour)
