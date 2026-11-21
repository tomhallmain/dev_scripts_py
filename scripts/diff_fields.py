"""``ds diff_fields`` -- elementwise arithmetic between two files with the same layout.

Line ``n`` of the second file is combined field by field with line ``n`` of the first.
Ops: ``-`` (first minus second), ``+``, ``*``, ``/`` (first divided by second, 0 for a zero
divisor), ``%`` (change from first to second as a fraction of the first), ``b``/``bin``/
``binary`` (1 where the raw values differ, else 0), and the per-field summaries ``m``/``mad``
(mean absolute difference), ``r``/``rmsd`` (root mean square difference) and ``s``/``stats``.

A value is a number when it is numeric after removing thousands commas. Where only one
side is a number the other counts as 0 if it is empty, otherwise that side's raw value is
passed through; where neither is a number the output field is empty. Excluded fields
(1-based) are passed through from the second file. Blank lines are skipped.

The diff list collects every non-trivial result (non-zero, or not 1 for ``/``) as
``ROW FIELD LEFT RIGHT DIFF``, sorted by the difference, descending by default.
"""
import math
import re
from typing import Dict, List, Optional, Sequence, Tuple

OPS = {
    "-": "-", "+": "+", "*": "*", "/": "/", "%": "%",
    "b": "b", "bin": "b", "binary": "b",
    "m": "m", "mad": "m", "r": "r", "rmsd": "r", "s": "s", "stats": "s",
}
STATS_OPS = {"m", "r", "s"}

_NUMBER_RE = re.compile(r"-?[0-9]*\.?[0-9]+((E|e)(\+|-)[0-9]+)?")
_LARGE_EXPONENT_RE = re.compile(r"^-?[0-9]*\.?[0-9]+(E|e)\+?([4-9]|[1-9][0-9]+)$")


class DiffFieldsError(Exception):
    pass


def awk_number(value: float) -> str:
    """A number as AWK prints it (``%.6g`` unless an integer)."""
    if value == int(value) and abs(value) < 1e16:
        return str(int(value))
    return "%.6g" % value


def extract_value(value: str) -> Optional[float]:
    cleaned = value.replace(",", "")
    m = _NUMBER_RE.search(cleaned)
    if not m or m.start() > 0 or m.end() < len(cleaned):
        return None
    return float(m.group(0))


def truncate_value(value: float) -> float:
    """Round to six decimals; very large values (by their AWK string form) to integers."""
    text = awk_number(value)
    if (value > 999 and re.search(r"\.[0-9]{3,}", text)) or _LARGE_EXPONENT_RE.match(text):
        return float(math.trunc(value))
    return float("%f" % value)


def split_fields(line: str, field_separator: Optional[str]) -> List[str]:
    if field_separator and field_separator.strip():
        return line.split(field_separator)
    return line.split()


def parse_exclude_fields(spec: Optional[str]) -> List[int]:
    out = []
    for part in re.split(r",+", (spec or "").strip()):
        part = part.strip()
        if not part or part == "0":
            continue
        if not part.isdigit():
            raise DiffFieldsError(
                f"Invalid exclude field index (exclude_fields must be a list of ints): {part}")
        out.append(int(part))
    return out


class DiffFields:
    def __init__(self, op: str = "-", exclude_fields: Optional[str] = None, *,
                 header: bool = False, precision: Optional[int] = None,
                 diff_list: Optional[str] = None, diff_list_sort: str = "d",
                 left_label: str = "FILE1", right_label: str = "FILE2",
                 field_separator: Optional[str] = None,
                 right_field_separator: Optional[str] = None):
        if op.lower() not in OPS:
            raise DiffFieldsError(f"Unknown op: {op}")
        self.op = OPS[op.lower()]
        self.exclude = parse_exclude_fields(exclude_fields)
        self.header = header
        self.precision = precision
        self.diff_list = bool(diff_list)
        self.diff_list_only = (diff_list or "").lower() == "only"
        self.diff_list_sort = (diff_list_sort or "d").lower()
        self.left_label = left_label
        self.right_label = right_label
        self.field_separator = field_separator
        self.right_field_separator = right_field_separator or field_separator
        self.ofs = field_separator if field_separator and field_separator.strip() else " "
        self.row_label_field = self.exclude[0] if self.diff_list and self.exclude else None

    def _format(self, value: float) -> str:
        if self.precision:
            return f"{value:.{self.precision}f}"
        return awk_number(value)

    def _combine(self, s1: float, s2: float) -> float:
        op = self.op
        if op == "%":
            if s1 == 0:
                return 0.0 if s2 == 0 else 1.0
            diff = (s2 - s1) / s1
            return -diff if s1 < 0 and s2 < 0 else diff
        if op == "-" or op in STATS_OPS:
            return s1 - s2
        if op == "+":
            return s1 + s2
        if op == "*":
            return s1 * s2
        return s1 / s2 if s2 else 0.0

    def _numeric_pair(self, raw1: str, raw2: str) -> Tuple[Optional[Tuple[float, float]], str]:
        """Both values as numbers, or ``None`` and the text to print instead."""
        s1, s2 = raw1.strip(), raw2.strip()
        if not s1 and not s2:
            return None, ""
        if not s1:
            v2 = extract_value(s2)
            return (None, raw2) if v2 is None else ((0.0, v2), "")
        if not s2:
            v1 = extract_value(s1)
            return (None, raw1) if v1 is None else ((v1, 0.0), "")
        v1, v2 = extract_value(s1), extract_value(s2)
        if v1 is None:
            return None, ("" if v2 is None else raw2)
        if v2 is None:
            return None, raw1
        return (truncate_value(v1), truncate_value(v2)), ""

    def run(self, lines1: Sequence[str], lines2: Sequence[str]) -> List[str]:
        lines1 = [line.rstrip("\n").rstrip("\r") for line in lines1]
        lines2 = [line.rstrip("\n").rstrip("\r") for line in lines2]
        out: List[str] = []
        diff_entries: List[Tuple[List[str], float]] = []
        abs_sum: Dict[int, float] = {}
        sq_sum: Dict[int, float] = {}
        counts: Dict[int, int] = {}
        minimum: Dict[int, float] = {}
        maximum: Dict[int, float] = {}
        header_names: List[str] = []
        prints_rows = not (self.diff_list_only or self.op in STATS_OPS)

        header_index = {"left": None, "right": None}
        if self.header:
            for side, lines in (("left", lines1), ("right", lines2)):
                header_index[side] = next((i for i, l in enumerate(lines) if l.strip()), None)
            if header_index["right"] is not None:
                header_line = lines2[header_index["right"]]
                header_fields = split_fields(header_line, self.right_field_separator)
                header_names = [h.strip() for h in header_fields]
                if prints_rows:
                    out.append(self.ofs.join(header_fields)
                               if self.right_field_separator and self.right_field_separator.strip()
                               else header_line)

        for index, line in enumerate(lines2):
            if not line.strip() or index == header_index["right"]:
                continue
            row2 = split_fields(line, self.right_field_separator)
            left_line = lines1[index] if index < len(lines1) and index != header_index["left"] else ""
            row1 = split_fields(left_line, self.field_separator)
            cells: List[str] = []
            for f, raw2 in enumerate(row2, start=1):
                raw1 = row1[f - 1] if f <= len(row1) else ""
                if f in self.exclude:
                    cells.append(raw2)
                    continue
                if self.op == "b":
                    diff = 1.0 if raw1 != raw2 else 0.0
                    formatted = awk_number(diff)
                else:
                    pair, passthrough = self._numeric_pair(raw1, raw2)
                    if pair is None:
                        cells.append(passthrough)
                        continue
                    diff = self._combine(*pair)
                    if self.op in STATS_OPS:
                        a = abs(diff)
                        abs_sum[f] = abs_sum.get(f, 0.0) + a
                        sq_sum[f] = sq_sum.get(f, 0.0) + diff * diff
                        counts[f] = counts.get(f, 0) + 1
                        minimum[f] = min(minimum.get(f, a), a)
                        maximum[f] = max(maximum.get(f, a), a)
                        continue
                    formatted = self._format(diff)
                cells.append(formatted)
                trivial = diff == 1 if self.op == "/" else diff == 0
                if self.diff_list and not trivial:
                    if self.row_label_field is not None:
                        row_label = row2[self.row_label_field - 1] if self.row_label_field <= len(row2) else ""
                        field_label = (header_names[f - 1] if self.header and f <= len(header_names)
                                       else str(f))
                    else:
                        row_label, field_label = str(index + 1), str(f)
                    diff_entries.append(([row_label, field_label, raw1, raw2, formatted], diff))
            if prints_rows:
                out.append(self.ofs.join(cells))

        if self.op in STATS_OPS:
            out.extend(self._stats_lines(abs_sum, sq_sum, counts, minimum, maximum, header_names))
            return out
        if self.diff_list and diff_entries:
            if self.diff_list_sort != "off":
                diff_entries.sort(key=lambda e: (e[1], self.ofs.join(e[0][:4])),
                                  reverse=not self.diff_list_sort.startswith("a"))
            if not self.diff_list_only:
                out.extend(["", "", ""])
            out.append(self.ofs.join(["ROW", "FIELD", self.left_label, self.right_label, "DIFF"]))
            out.extend(self.ofs.join(entry) for entry, _diff in diff_entries)
        return out

    def _stats_lines(self, abs_sum, sq_sum, counts, minimum, maximum, header_names) -> List[str]:
        out = ["Field Statistics:", "---------------"]
        for f in sorted(counts):
            n = counts[f]
            name = header_names[f - 1] if self.header and f <= len(header_names) else str(f)
            mean = abs_sum[f] / n
            if self.op == "m":
                out.append(f"MAD [{name}]: {self._format(mean)}")
            elif self.op == "r":
                out.append(f"RMSD [{name}]: {self._format(math.sqrt(sq_sum[f] / n))}")
            else:
                variance = (sq_sum[f] - abs_sum[f] ** 2 / n) / (n - 1) if n > 1 else 0.0
                out.extend([
                    f"Stats [{name}]:",
                    f"  Min: {self._format(minimum[f])}",
                    f"  Max: {self._format(maximum[f])}",
                    f"  Mean: {self._format(mean)}",
                    f"  StdDev: {self._format(math.sqrt(variance) if variance > 0 else 0.0)}",
                ])
        return out
