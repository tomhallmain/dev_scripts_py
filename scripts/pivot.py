"""``ds pivot`` -- cross-tabulate rows by x/y key fields.

Output shape (matching the shell original): a header line of the x values, then one line
per y value. Every cell is followed by the output separator, and the y label itself is
followed by one separator per y key, so columns line up when the result is fed to a
column-fitting command.

Keys are either 1-based field indices or header-name patterns. A pattern matches the
first not-yet-claimed header field that starts with it, so ``win,win`` picks up ``wing``
then ``wind``. Using any pattern means the first row is consumed as a header.
"""
import re
from typing import List, Optional, Sequence, Tuple

from scripts.utils import Utils

KEY_NOT_FOUND_MESSAGE = "Fields not found for both x and y dimensions with given key params"
Z_NOT_FOUND_MESSAGE = "Z dimension fields not found with given key params"

_NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _is_number(value: str) -> bool:
    return bool(value) and bool(_NUMERIC_RE.match(value.strip()))


def _format_number(value: float) -> str:
    """Render an aggregate without a trailing ``.0`` when it lands on a whole number."""
    if value == int(value):
        return str(int(value))
    return str(value)


def load_pivot_rows(file_path: str, field_separator: Optional[str] = None) -> List[List[str]]:
    """Load non-blank rows from ``file_path``, split on ``field_separator`` or whitespace.

    Only a single non-space separator is honored; anything else (a whitespace run, a
    character-class pattern) falls back to a plain whitespace split.
    """
    split_char = None
    if field_separator and len(field_separator) == 1 and not field_separator.isspace():
        split_char = field_separator

    rows: List[List[str]] = []
    with open(file_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if split_char:
                rows.append([cell.strip() for cell in line.split(split_char)])
            else:
                rows.append(line.split())
    return rows


class Pivot:
    COUNT = "count"
    SUM = "sum"
    PRODUCT = "product"
    MEAN = "mean"
    AGG_TYPES = [COUNT, SUM, PRODUCT, MEAN]

    OFS = Utils.DS_SEP
    VALUE_SEP = "::"

    def __init__(self, file, y_keys, x_keys, z_keys=None, agg_type=None, header=True,
                 gen_keys=False, sort_off=False):
        self.file = file
        self.y_keys = [k for k in y_keys.split(',') if k]
        self.x_keys = [k for k in x_keys.split(',') if k]
        self.z_keys = [k for k in z_keys.split(',') if k] if z_keys else None
        # No z at all counts rows; z=0 pulls in every field that isn't already an x/y key.
        self.count_xy = z_keys is None
        self.use_remaining_fields = z_keys == "0"

        if agg_type:
            selected_agg_types = [t for t in Pivot.AGG_TYPES if t.startswith(agg_type)]
            if len(selected_agg_types) != 1:
                raise Exception(f"Invalid agg type: {agg_type}")
            self.agg_type = selected_agg_types[0]
        elif self.count_xy:
            self.agg_type = Pivot.COUNT
        else:
            # A z field with no explicit aggregation shows the value itself.
            self.agg_type = None

        self.gen_keys = gen_keys
        self.sort_off = sort_off
        self.header = None
        self.error = None
        self.data: List[List[str]] = []
        self.x_indices: List[int] = []
        self.y_indices: List[int] = []
        self.z_indices: List[int] = []
        self.x_names: List[str] = []
        self.y_names: List[str] = []
        self.X: List[str] = []
        self.Y: List[str] = []
        self.cells = {}

    def _is_pattern(self, key: str) -> bool:
        return self.gen_keys or not key.isdigit()

    def _uses_header(self) -> bool:
        return any(self._is_pattern(k) for k in self.x_keys + self.y_keys + (self.z_keys or []))

    def _resolve(self, keys: Sequence[str], header_row) -> Tuple[List[int], List[str]]:
        """Resolve keys to field indices; unmatched patterns are dropped."""
        indices: List[int] = []
        names: List[str] = []
        claimed = set()

        for key in keys:
            if self._is_pattern(key):
                if header_row is None:
                    continue
                index = None
                for i, field in enumerate(header_row):
                    if i in claimed:
                        continue
                    if field.lower().startswith(key.lower()):
                        index = i
                        break
                if index is None:
                    continue
            else:
                index = int(key) - 1
                if index < 0:
                    continue
            claimed.add(index)
            indices.append(index)
            if header_row is not None and index < len(header_row):
                names.append(header_row[index])
            else:
                names.append(key)
        return indices, names

    @staticmethod
    def _field(row: Sequence[str], index: int) -> str:
        return row[index] if index < len(row) else ""

    def pivot(self):
        header_row = None
        if self._uses_header() and self.data:
            header_row = self.data.pop(0)
            self.header = header_row

        self.x_indices, self.x_names = self._resolve(self.x_keys, header_row)
        self.y_indices, self.y_names = self._resolve(self.y_keys, header_row)
        if not self.x_indices or not self.y_indices:
            self.error = KEY_NOT_FOUND_MESSAGE
            return

        if not self.count_xy and not self.use_remaining_fields:
            self.z_indices, _ = self._resolve(self.z_keys or [], header_row)
            if not self.z_indices:
                self.error = Z_NOT_FOUND_MESSAGE
                return

        self.process_data()

    def process_data(self):
        skip = set(self.x_indices) | set(self.y_indices)
        for row in self.data:
            if not row:
                continue
            # A y label spans one column per y key, so it is joined by the output separator.
            # An x label has to fit in a single column, so its keys are joined by "::".
            x_str = self.VALUE_SEP.join(self._field(row, i) for i in self.x_indices)
            y_str = self.OFS.join(self._field(row, i) for i in self.y_indices)

            if self.count_xy:
                value = ""
            elif self.use_remaining_fields:
                value = self.VALUE_SEP.join(
                    self._field(row, i) for i in range(len(row)) if i not in skip
                )
            else:
                value = self.VALUE_SEP.join(self._field(row, i) for i in self.z_indices)

            if not x_str and not y_str and not value:
                continue
            if x_str not in self.X:
                self.X.append(x_str)
            if y_str not in self.Y:
                self.Y.append(y_str)
            self.cells.setdefault((x_str, y_str), []).append(value)

    def _sorted(self, values: Sequence[str]) -> List[str]:
        if self.sort_off:
            return list(values)
        if values and all(_is_number(v) for v in values):
            return sorted(values, key=float)
        return sorted(values)

    def _aggregate(self, values: List[str]) -> str:
        if self.agg_type == Pivot.COUNT:
            return str(len(values))
        if self.agg_type is None:
            return values[-1]

        numbers = [float(v) for v in values if _is_number(v)]
        if not numbers:
            return values[-1]
        if self.agg_type == Pivot.SUM:
            result = sum(numbers)
        elif self.agg_type == Pivot.PRODUCT:
            result = 1.0
            for n in numbers:
                result *= n
        else:
            result = sum(numbers) / len(numbers)
        return _format_number(result)

    def _cell_text(self, x_str: str, y_str: str) -> str:
        values = self.cells.get((x_str, y_str))
        if not values:
            return ""
        return self._aggregate(values)

    def pivot_header(self) -> str:
        if self.header is None:
            return "PIVOT"
        return self.VALUE_SEP.join(self.y_names) + " \\ " + self.VALUE_SEP.join(self.x_names)

    def print_pivot(self):
        if self.error:
            print(self.error)
            return

        xs = self._sorted(self.X)
        ys = self._sorted(self.Y)

        header_line = self.pivot_header() + self.OFS * len(self.y_indices)
        header_line += "".join(x + self.OFS for x in xs)
        print(header_line)

        for y in ys:
            print(y + self.OFS + "".join(self._cell_text(x, y) + self.OFS for x in xs))
