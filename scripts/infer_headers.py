"""``ds inferh`` -- infer whether the first row of a data file is a header row.

The first row is scored against up to ``max_rows - 1`` following control rows:

- a first-row field matching a data-like pattern (integer, decimal, date, link, JSON)
  scores -100, a header-like pattern (alpha, uppercase, words, ``id``) +30, and a field
  that looks like a column name (CamelCase, snake_case, CONSTANT_CASE, a statistical or
  time-related term) +20; a first row with fewer than two fields scores -100
- each control row whose field count differs from the first row scores -50
- the length difference between each control field and the first-row field above it adds
  ``|difference| / (max_rows - 1)``
- per field and pattern seen in the control rows, ``|first_row_match - share_of_control_rows|``
  is added

A positive total means a header row. Fewer than two rows means no header.
"""
import csv
import math
import re
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

PATTERNS = {
    "i": re.compile(r"^[0-9]+$"),
    "d": re.compile(r"^[0-9]+\.[0-9]+$"),
    "a": re.compile(r"[A-Za-z]+"),
    "u": re.compile(r"^[A-Z]+$"),
    "hi": re.compile(r"[0-9]+"),
    "hd": re.compile(r"[0-9]+\.[0-9]+"),
    "ha": re.compile(r"[A-Za-z]+"),
    "hu": re.compile(r"[A-Z]+"),
    "nl": re.compile(r"^[^a-z]+$"),
    "w": re.compile(r"[A-Za-z ]+"),
    "ns": re.compile(r"^\S$"),
    "id": re.compile(r"(^|_| |-)?[Ii][Dd](-|_| |$)"),
    "d1": re.compile(r"^[0-9]{1,2}[-./][0-9]{1,2}[-./]([0-9]{2}|[0-9]{4})$"),
    "d2": re.compile(r"^[0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2}$"),
    "l": re.compile(r"://"),
    "j": re.compile(r"^\{[,:\"'{}\[\]A-z0-9.\-+ \n\r\t]{2,}\}$"),
    "x": re.compile(r"<[^>]+>"),
}
NON_HEADER_PATTERNS = {"i", "d", "d1", "d2", "l", "j"}
HEADER_PATTERNS = {"a", "u", "w", "id"}

_LIKELY_HEADER = [
    re.compile(r"^[A-Z][a-z]+([A-Z][a-z]+)*$"),
    re.compile(r"^[a-z]+(_[a-z]+)*$"),
    re.compile(r"^[A-Z_]+$"),
    re.compile(r"^(sum|avg|count|total|min|max|mean|median)_?", re.IGNORECASE),
    re.compile(r"(date|time|timestamp|created|updated|modified)", re.IGNORECASE),
]

DEFAULT_MAX_ROWS = 100


def split_row(line: str, field_separator: Optional[str]) -> List[str]:
    """Split one line; a single-character separator honours double-quoted fields."""
    if field_separator and len(field_separator) == 1 and not field_separator.isspace() \
            and '"' in line:
        return next(csv.reader([line], delimiter=field_separator))
    if field_separator and field_separator.strip():
        return line.split(field_separator)
    return line.split()


def is_likely_header(field: str) -> bool:
    return any(p.search(field) for p in _LIKELY_HEADER)


def header_score(lines: Sequence[str], field_separator: Optional[str],
                 *, max_rows: int = DEFAULT_MAX_ROWS, trim: bool = True) -> Optional[float]:
    """Score for the first of ``lines`` being a header, or ``None`` with fewer than two rows."""
    lines = [line.rstrip("\n").rstrip("\r") for line in lines]
    analysed = lines[:max_rows]
    if len(analysed) < 2:
        return None
    length_divisor = max_rows - 1

    def fields_of(line: str) -> List[str]:
        fields = split_row(line, field_separator)
        return [f.strip() for f in fields] if trim else fields

    score = 0.0
    first = fields_of(analysed[0])
    if len(first) < 2:
        score -= 100
    first_lengths: Dict[int, int] = {}
    first_matches: Dict[Tuple[int, str], int] = {}
    for i, field in enumerate(first):
        first_lengths[i] = len(field)
        for name, pattern in PATTERNS.items():
            if pattern.search(field):
                first_matches[(i, name)] = 1
                if name in NON_HEADER_PATTERNS:
                    score -= 100
                if name in HEADER_PATTERNS:
                    score += 30
        if is_likely_header(field):
            score += 20

    control_matches: Dict[Tuple[int, str], int] = defaultdict(int)
    for line in analysed[1:]:
        fields = fields_of(line)
        if len(fields) != len(first):
            score -= 50
        for i, field in enumerate(fields):
            score += abs(first_lengths.get(i, 0) - len(field)) / length_divisor
            for name, pattern in PATTERNS.items():
                if pattern.search(field):
                    control_matches[(i, name)] += 1

    control_rows = len(analysed) - 1
    for i in range(len(first)):
        for name in PATTERNS:
            count = control_matches.get((i, name), 0)
            if count > 0:
                score += math.sqrt((first_matches.get((i, name), 0) - count / control_rows) ** 2)
    return score


def has_header(lines: Sequence[str], field_separator: Optional[str], **kwargs) -> bool:
    score = header_score(lines, field_separator, **kwargs)
    return score is not None and score > 0
