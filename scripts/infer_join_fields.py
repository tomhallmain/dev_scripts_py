"""``ds inferk`` -- infer the fields on which two data files most likely join.

If both files have a header row and some header name appears in both (exact, after trimming
whitespace), the first such pair wins. Otherwise every pair of columns is scored on up to
``max_rows`` data rows of each file: the Jaccard similarity of the two columns' value sets,
minus a tenth of the difference between their cardinality ratios (distinct values per row).
The first pair with the highest score wins.

The result is printed as ``k`` when both files join on the same field index, else ``k1 k2``
(1-based). On ambiguous data this heuristic can pick a different pair than the original
command's weighted multi-factor score.
"""
from typing import List, Optional, Sequence, Tuple

from scripts.field_rows import split_fields

DEFAULT_MAX_ROWS = 50


class InferJoinError(Exception):
    pass


def header_match(header1: Sequence[str], header2: Sequence[str]) -> Optional[Tuple[int, int]]:
    for i, h1 in enumerate(header1, start=1):
        for j, h2 in enumerate(header2, start=1):
            if h1.strip() == h2.strip():
                return i, j
    return None


def best_column_pair(rows1: Sequence[Sequence[str]],
                     rows2: Sequence[Sequence[str]]) -> Tuple[int, int]:
    n_cols1 = max((len(r) for r in rows1), default=0)
    n_cols2 = max((len(r) for r in rows2), default=0)
    columns2 = []
    for j in range(n_cols2):
        values = {r[j] for r in rows2 if j < len(r)}
        columns2.append((values, len(values) / max(len(rows2), 1)))

    best, best_score = (1, 1), float("-inf")
    for i in range(n_cols1):
        values1 = {r[i] for r in rows1 if i < len(r)}
        if not values1:
            continue
        cardinality1 = len(values1) / max(len(rows1), 1)
        for j, (values2, cardinality2) in enumerate(columns2):
            if not values2:
                continue
            union = len(values1 | values2)
            jaccard = len(values1 & values2) / union if union else 0.0
            score = jaccard - abs(cardinality1 - cardinality2) * 0.1
            if score > best_score:
                best, best_score = (i + 1, j + 1), score
    return best


def infer_join_fields(lines1: Sequence[str], lines2: Sequence[str],
                      field_separator1: Optional[str], field_separator2: Optional[str],
                      *, header: bool = True, max_rows: int = DEFAULT_MAX_ROWS) -> str:
    lines1 = [l.rstrip("\n").rstrip("\r") for l in lines1 if l.strip()]
    lines2 = [l.rstrip("\n").rstrip("\r") for l in lines2 if l.strip()]
    rows1: List[List[str]] = [split_fields(l, field_separator1) for l in lines1]
    rows2: List[List[str]] = [split_fields(l, field_separator2) for l in lines2]
    if header and rows1 and rows2:
        matched = header_match(rows1[0], rows2[0])
        if matched:
            return format_result(*matched)
        rows1, rows2 = rows1[1:], rows2[1:]
    rows1, rows2 = rows1[:max_rows], rows2[:max_rows]
    if not rows1 or not rows2:
        raise InferJoinError("both files need at least one data row")
    return format_result(*best_column_pair(rows1, rows2))


def format_result(i: int, j: int) -> str:
    return str(i) if i == j else f"{i} {j}"
