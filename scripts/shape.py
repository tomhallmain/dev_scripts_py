"""``ds shape`` -- how a length or pattern measure is distributed over the lines of a file.

Each measure is either ``length`` (any prefix of ``_length_``, e.g. an empty string) or a
regex whose case-insensitive, non-overlapping matches are counted. Measures apply to the
whole line (field ``0``) or to the given fields. For each field and measure, the line count,
matching lines, total occurrences and average per line are printed, then a bar chart of the
total per bucket of ``span`` lines, one column per measure.

Bars are scaled so the largest bucket fits the column width. A final partial bucket counts
towards that scaling as if it were a full bucket but is not drawn, and the chart always ends
with one empty bucket row; both match the original command's output.
"""
import re
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_CHART_SIZE = 15
DEFAULT_TTY_SIZE = 100


def awk_number(value: float) -> str:
    """A number as AWK prints it in string concatenation (``%.6g`` unless an integer)."""
    if value == int(value) and abs(value) < 1e16:
        return str(int(value))
    return "%.6g" % value


def parse_measures(measures: Optional[str]) -> List[Tuple[str, Optional[re.Pattern]]]:
    """``(display_name, pattern)`` per measure; ``pattern`` is ``None`` for length."""
    out = []
    for measure in (measures or "_length_").split(","):
        if "_length_".startswith(measure):
            out.append(("length", None))
        else:
            out.append((measure, re.compile(measure.lower())))
    return out


def parse_fields(fields: Optional[str]) -> List[int]:
    out = []
    for field in (fields or "0").split(","):
        field = field.strip()
        if field == "0":
            out.append(0)
        elif field.isdigit() and int(field) > 0:
            out.append(int(field))
    return out or [0]


class Shape:
    def __init__(self, measures: Optional[str] = None, fields: Optional[str] = None,
                 span: int = DEFAULT_CHART_SIZE, tty_size: int = DEFAULT_TTY_SIZE,
                 field_separator: Optional[str] = None, header: bool = False,
                 simple: bool = False):
        self.measures = parse_measures(measures)
        self.fields = parse_fields(fields)
        self.span = max(int(span), 1)
        self.tty_size = tty_size or DEFAULT_TTY_SIZE
        self.field_separator = field_separator
        self.header = header
        self.simple = simple

    def _field_value(self, line: str, field: int) -> str:
        if field == 0:
            return line
        if self.field_separator and self.field_separator.strip():
            parts = line.split(self.field_separator)
        else:
            parts = line.split()
        return parts[field - 1] if field <= len(parts) else ""

    @staticmethod
    def _occurrences(value: str, pattern: Optional[re.Pattern]) -> int:
        if pattern is None:
            return len(value)
        return len(pattern.findall(value.lower())) if value else 0

    def render(self, lines: Sequence[str]) -> List[str]:
        lines = [line.rstrip("\n").rstrip("\r") for line in lines]
        n_lines = len(lines)
        if not n_lines:
            return []
        headers: Dict[int, str] = {}
        data = lines
        if self.header:
            headers = {i: v.strip() for i, v in enumerate(lines[0].split(
                self.field_separator if self.field_separator and self.field_separator.strip()
                else None), start=1)}
            data = lines[1:]

        keys = [(f, m) for f in range(len(self.fields)) for m in range(len(self.measures))]
        total = {k: 0 for k in keys}
        matched = {k: 0 for k in keys}
        running = {k: 0.0 for k in keys}
        max_bucket = {k: 0.0 for k in keys}
        buckets: Dict[Tuple[Tuple[int, int], float], float] = {}
        n_buckets = 0
        nr = 1 if self.header else 0
        discriminant = 0

        for line in data:
            nr += 1
            discriminant = nr % self.span
            if discriminant == 0:
                n_buckets += 1
            for f_i, field in enumerate(self.fields):
                value = self._field_value(line, field)
                for m_i, (_name, pattern) in enumerate(self.measures):
                    key = (f_i, m_i)
                    occurrences = self._occurrences(value, pattern)
                    total[key] += occurrences
                    running[key] += occurrences
                    if occurrences:
                        matched[key] += 1
                    if discriminant == 0:
                        max_bucket[key] = max(max_bucket[key], running[key])
                        buckets[(key, nr // self.span)] = running[key]
                        running[key] = 0

        for key in keys:
            if discriminant:
                running[key] = running[key] / discriminant * self.span
                max_bucket[key] = max(max_bucket[key], running[key])
                buckets[(key, (nr - running[key] + self.span) / self.span)] = running[key]

        if not any(max_bucket.values()):
            return ["Data not found with given parameters"]

        lineno_size = max(len(str(n_lines)), 5)
        column_len = int((self.tty_size - lineno_size - 2) / len(self.measures)) - 1
        indent = "" if self.simple else " " * (lineno_size + 2)

        def columns(values: Sequence[str]) -> str:
            return "".join(f"{v:<{column_len}} " for v in values)

        out = [f"{indent}lines: {nr}"]
        n_measures = len(self.measures)
        for f_i, field in enumerate(self.fields):
            row_keys = [(f_i, m_i) for m_i in range(n_measures)]
            if len(self.fields) > 1 or field:
                name = f" ({headers[field]})" if headers.get(field) else ""
                out.append(f"{indent}stats from field: ${field}{name}")
            out.append(indent + columns(
                [f'lines with "{self.measures[k[1]][0]}": {matched[k]}' for k in row_keys]))
            out.append(indent + columns([f"occurrence: {total[k]}" for k in row_keys]))
            out.append(indent + columns(
                [f"average: {awk_number(total[k] / nr)}" for k in row_keys]))
            if self.simple:
                continue

            scale = {k: 1 if max_bucket[k] <= column_len else column_len / max_bucket[k]
                     for k in row_keys}
            descriptions = [f'distribution of "{name}"' if pattern is not None
                            else "distribution of length"
                            for name, pattern in self.measures]
            out.append(f"{'lineno':>{lineno_size}} " + columns(descriptions))
            for i in range(1, n_buckets + 2):
                bars = []
                for k in row_keys:
                    length = int(buckets.get((k, i), 0) * scale[k] + 0.5)
                    bars.append("+" * min(max(length, 0), column_len))
                out.append(f" {i * self.span:>{lineno_size}} " + columns(bars))
        return out
