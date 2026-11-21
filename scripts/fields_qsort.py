"""``ds sortm`` -- sort lines by one or more fields.

Keys are 1-based field indices or ``NF`` (the last field). If any key is not an index of
at most three digits, all keys are header patterns instead: each is a case-insensitive
regex matched against the start of the first row's fields, and that row stays first.

The values of the key fields are joined by the field separator into one sort key per line.
With ``deterministic``, the remaining fields are appended so that only identical lines tie.

Comparison follows AWK, since that is what defines this command's ordering:

- default: a sort key that is a single field compares numerically against another numeric
  one, everything else compares as a string
- type ``n``: the leading number of the key is compared first, then the text after it;
  a key without a leading number compares as a string against the other key (a number
  in its AWK string form), so e.g. ``,,`` sorts before numbers and ``a,1`` after them
- type ``i``: keys are lowercased first (and so always compare as strings)

Lines with equal keys keep their input order. Blank lines are dropped.
"""
import functools
import re
from typing import List, Optional, Sequence, Tuple

from scripts.field_rows import split_fields

# A leading number, optionally with spaces, a currency sign, a sign and thousands commas.
_LEADING_NUMBER_RE = re.compile(
    r"^\s*\$?\s?-?\$?([0-9]{0,3},)*[0-9]*\.?[0-9]+((E|e)(\+|-)?[0-9]+)?"
)
_STRTONUM_RE = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?")
_NUMERIC_STRING_RE = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$")


class SortKeyError(Exception):
    pass


def awk_strtonum(text: str) -> float:
    """The number AWK reads from the start of ``text`` (0 when there is none)."""
    m = _STRTONUM_RE.match(text)
    return float(m.group(0)) if m else 0.0


def awk_number_string(value: float) -> str:
    """A number as AWK converts it to a string: integers plainly, others with ``%.6g``."""
    if value == int(value) and abs(value) < 1e16:
        return str(int(value))
    return "%.6g" % value


def leading_number(text: str) -> Optional[Tuple[float, str]]:
    """``(value, rest)`` for a key starting with a number, else ``None``."""
    m = _LEADING_NUMBER_RE.match(text)
    if not m:
        return None
    return awk_strtonum(m.group(0)), text[m.end():]


def _cmp(a, b) -> int:
    return (a > b) - (a < b)


def compare_default(a: str, b: str, single_field: bool) -> int:
    if single_field and _NUMERIC_STRING_RE.match(a) and _NUMERIC_STRING_RE.match(b):
        return _cmp(float(a), float(b))
    return _cmp(a, b)


def compare_numeric(a: str, b: str) -> int:
    na, nb = leading_number(a), leading_number(b)
    if na is not None and nb is not None:
        return _cmp(na[0], nb[0]) or _cmp(na[1], nb[1])
    left = awk_number_string(na[0]) if na is not None else a
    right = awk_number_string(nb[0]) if nb is not None else b
    return _cmp(left, right)


class SortM:
    def __init__(self, keys: Optional[str] = "1", order: Optional[str] = "a",
                 sort_type: Optional[str] = "", *, field_separator: Optional[str] = None,
                 header: bool = False, deterministic: bool = False):
        self.field_separator = field_separator
        self.key_separator = field_separator if field_separator and field_separator.strip() else " "
        self.descending = bool(order) and "desc".startswith(order)
        sort_type = sort_type or ""
        self.numeric = "n" in sort_type
        self.case_insensitive = "i" in sort_type
        self.header = header
        self.deterministic = deterministic
        self.keys = [k.strip() for k in re.split(r",+", keys or "1") if k.strip()]
        if not self.keys:
            self.keys = ["1"]
        self.gen_keys = any(k != "NF" and (not k.isdigit() or len(k) > 3) for k in self.keys)

    def _resolve_header_keys(self, header_fields: Sequence[str]) -> List[object]:
        resolved: List[object] = []
        for pattern in self.keys:
            if pattern == "NF":
                resolved.append("NF")
                continue
            rx = re.compile("^(\"|')*" + pattern.lower())
            for index, field in enumerate(header_fields, start=1):
                if rx.search(field.lower()):
                    resolved.append(index)
                    break
        if not resolved:
            raise SortKeyError("No key patterns provided matched header")
        return resolved

    def _sort_key(self, fields: Sequence[str], key_fields: Sequence[object]) -> Tuple[str, int]:
        """The joined key and how many field values it holds."""
        values = []
        for kf in key_fields:
            index = len(fields) if kf == "NF" else kf
            if not index:
                continue
            value = fields[index - 1] if index <= len(fields) else ""
            values.append(value.lower() if self.case_insensitive else value)
        if self.deterministic:
            used = {kf for kf in key_fields if kf != "NF"}
            values.extend(v for i, v in enumerate(fields, start=1) if i not in used)
        return self.key_separator.join(values), len(values)

    def sort_lines(self, lines: Sequence[str]) -> List[str]:
        lines = [line.rstrip("\n").rstrip("\r") for line in lines]
        lines = [line for line in lines if line.strip()]
        header_line = None
        if lines and (self.header or self.gen_keys):
            header_line, lines = lines[0], lines[1:]
        if self.gen_keys:
            key_fields = self._resolve_header_keys(split_fields(header_line, self.field_separator))
        else:
            key_fields = ["NF" if k == "NF" else int(k) for k in self.keys]

        entries = []
        for line in lines:
            key, n_values = self._sort_key(split_fields(line, self.field_separator), key_fields)
            entries.append((key, n_values == 1 and not self.case_insensitive, line))

        def compare(x, y) -> int:
            if self.numeric:
                result = compare_numeric(x[0], y[0])
            else:
                result = compare_default(x[0], y[0], x[1] and y[1])
            return -result if self.descending else result

        entries.sort(key=functools.cmp_to_key(compare))
        out = [line for _key, _single, line in entries]
        return ([header_line] if header_line is not None else []) + out
