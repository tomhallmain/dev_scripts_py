"""``ds fit`` -- fit fielded data into columns of dynamic width.

Column widths come from the widest value in each column. String columns are left-aligned
and number columns right-aligned, with ``buffer`` characters between columns; the final
column is never padded, so lines carry no trailing whitespace.
"""
import re
import unicodedata
from typing import List, Optional, Sequence

DEFAULT_BUFFER = 2
DEFAULT_BUFFER_CHAR = " "

# A field counts as a number if it is an integer, a decimal, or scientific notation,
# optionally carrying a sign, thousands commas or a currency mark.
_NUMBER_RE = re.compile(
    r"^[+-]?[$£]?[+-]?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?([Ee][+-]?\d+)?%?$"
)
_DECIMAL_RE = re.compile(r"^[+-]?[$£]?[+-]?(\d{1,3}(,\d{3})+|\d+)\.(\d+)([Ee][+-]?\d+)?$")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# East Asian wide/fullwidth characters occupy two terminal columns; combining marks none.
_WIDE_EAST_ASIAN = ("W", "F")


def display_width(text: str) -> int:
    """Terminal columns occupied by ``text``, ignoring ANSI colour and combining marks."""
    width = 0
    for char in _ANSI_RE.sub("", text):
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in _WIDE_EAST_ASIAN else 1
    return width


def is_number(value: str) -> bool:
    return bool(_NUMBER_RE.match(value.strip()))


def is_decimal(value: str) -> bool:
    return bool(_DECIMAL_RE.match(value.strip()))


class FitColumns:
    """Compute column widths for a table and render it aligned."""

    def __init__(self, field_separator=None, buffer=None, buffer_char=None):
        self.field_separator = field_separator
        self.buffer = DEFAULT_BUFFER if buffer is None else int(buffer)
        self.buffer_char = DEFAULT_BUFFER_CHAR if buffer_char is None else buffer_char
        self.field_max: List[int] = []
        self.number_set: List[bool] = []

    # -- input -----------------------------------------------------------

    def read_rows(self, file_path: str) -> List[List[str]]:
        separator = self.field_separator
        rows: List[List[str]] = []
        with open(file_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n").rstrip("\r")
                if separator and separator.strip():
                    rows.append([c.strip() for c in line.split(separator)])
                else:
                    rows.append(line.split())
        return rows

    # -- pass one: widths and column types -------------------------------

    def analyze(self, rows: Sequence[Sequence[str]]) -> None:
        """Record each column's width and whether it should be treated as numeric.

        The number test is order-dependent: a non-numeric value only disqualifies a column
        that has *already* seen a number, so a text header above numeric data still leaves
        the column right-aligned. A column holding decimals is never disqualified.
        """
        max_nf = max((len(r) for r in rows), default=0)
        number_set = [False] * max_nf
        number_overset = [False] * max_nf
        self.decimal_set = [False] * max_nf
        self.decimal_max = [0] * max_nf

        for row in rows:
            for i, value in enumerate(row):
                value = value.strip()
                if not value or value == "-":
                    continue
                if is_decimal(value):
                    self.decimal_set[i] = True
                    number_set[i] = True
                    places = len(value.rsplit(".", 1)[1])
                    if places > self.decimal_max[i]:
                        self.decimal_max[i] = places
                elif is_number(value):
                    number_set[i] = True
                elif number_set[i] and not self.decimal_set[i]:
                    number_overset[i] = True

        self.number_set = [
            self.decimal_set[i] or (number_set[i] and not number_overset[i])
            for i in range(max_nf)
        ]

        # Widths are measured on the rendered value, since a decimal column pads every
        # value out to the same number of places.
        self.field_max = [0] * max_nf
        for row in rows:
            for i in range(max_nf):
                width = display_width(self.render_value(row, i))
                if width > self.field_max[i]:
                    self.field_max[i] = width

    def render_value(self, row: Sequence[str], index: int) -> str:
        """The text a field prints as, before padding."""
        value = row[index].strip() if index < len(row) else ""
        if not self.decimal_set[index] or not value:
            return value
        if not is_number(value):
            return value
        return f"{float(value.replace(',', '').lstrip('$£')):.{self.decimal_max[index]}f}"

    # -- pass two: render -------------------------------------------------

    def _buffer_text(self) -> str:
        """The separator between columns: the buffer character then spaces."""
        if self.buffer <= 0:
            return ""
        return (self.buffer_char + " " * self.buffer)[: self.buffer]

    def _pad(self, value: str, width: int, right_align: bool) -> str:
        """Pad to ``width`` display columns; ANSI colour does not consume width."""
        padding = " " * max(width - display_width(value), 0)
        return padding + value if right_align else value + padding

    def format_row(self, row: Sequence[str]) -> str:
        max_nf = len(self.field_max)
        separator = self._buffer_text()
        cells: List[str] = []
        for i in range(max_nf):
            value = self.render_value(row, i)
            last = i == max_nf - 1
            if last:
                # The final column is not padded, so no trailing whitespace is emitted.
                cells.append(self._pad(value, self.field_max[i], True)
                             if self.number_set[i] else value)
            else:
                cells.append(self._pad(value, self.field_max[i], self.number_set[i]))
        return separator.join(cells)

    def fit_rows(self, rows: Sequence[Sequence[str]]) -> List[str]:
        self.analyze(rows)
        return [self.format_row(row) for row in rows]

    def fit_file(self, file_path: str) -> List[str]:
        return self.fit_rows(self.read_rows(file_path))
