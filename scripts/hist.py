"""``ds hist`` -- print a ``+`` bar histogram for every numeric field.

A field is numeric where its values (after removing whitespace, ``$``, ``,`` and
parentheses) are integers, decimals or scientific notation; non-numeric values are skipped.
The first row is a header row when ``header`` is set, or when none of its values is numeric
and the second row has a numeric value.

Integer-only fields get integer-aligned bins: one per value when the value range is
smaller than ``n_bins``, otherwise ``n_bins`` bins with edges on half-integers. Other fields
get ``n_bins`` equal-width bins, labelled with enough decimals to tell edges apart. Bars
scale so the fullest bin is at most ``max_bar_len`` characters.

Distinct values and bin edges are kept at six significant digits, as AWK stores them, so
the cardinality, bin edges and bin assignment of long decimals match the original command.
"""
import math
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Set

DEFAULT_BINS = 10
DEFAULT_BAR_LEN = 15
LABEL_WIDTH = 25

_NUM_RE = re.compile(r"^\s*\$?-?\$?[0-9]*\.?[0-9]+\s*$")
_DECIMAL_RE = re.compile(r"^\s*\$?-?\$?[0-9]*\.[0-9]+\s*$")
_FLOAT_RE = re.compile(r"^\s*-?[0-9]\.[0-9]+(E|e)(\+|-)?[0-9]+\s*$")
_INTEGER_RE = re.compile(r"^-?[0-9]+$")
_CLEAN_RE = re.compile(r"[\s$,()]+")


def clean_field(value: str) -> str:
    return _CLEAN_RE.sub("", value)


def is_number(value: str) -> bool:
    return bool(_NUM_RE.match(value) or _DECIMAL_RE.match(value) or _FLOAT_RE.match(value))


def to_number(value: str) -> float:
    """``value`` (already a matching number string) as a float; ``$`` signs are dropped."""
    return float(value.replace("$", ""))


def awk_key(value: float) -> str:
    """The string AWK uses for a number as an array index (``CONVFMT`` is ``%.6g``)."""
    if value == int(value) and abs(value) < 1e16:
        return str(int(value))
    return "%.6g" % value


def precision_for_bins(min_value: float, max_value: float, n_bins: int) -> int:
    bin_size = (max_value - min_value) / n_bins
    if max_value == 0 or bin_size == 0:
        return 2
    return min(max(int(-math.log10(bin_size)) + 1, 1), 6)


class FieldHistogram:
    def __init__(self):
        self.counts: Dict[str, int] = defaultdict(int)
        self.min: Optional[float] = None
        self.max: Optional[float] = None
        self.integer_only = True

    def add(self, value: float, is_integer: bool) -> None:
        self.counts[awk_key(value)] += 1
        if self.min is None:
            self.min = self.max = value
        else:
            self.min = min(self.min, value)
            self.max = max(self.max, value)
        self.integer_only = self.integer_only and is_integer

    def edges(self, n_bins: int) -> List[float]:
        # The original passes the edges through a joined string, so they are rounded the
        # same way as the counted values; keeping that keeps the bin assignment identical.
        return [float(awk_key(e)) for e in self._raw_edges(n_bins)]

    def _raw_edges(self, n_bins: int) -> List[float]:
        lo, hi = self.min, self.max
        if self.integer_only:
            value_range = hi - lo
            if value_range == 0:
                return [hi + 0.5]
            n = value_range + 1 if value_range < n_bins else n_bins
            if n == 1:
                return [hi + 0.5]
            int_range = math.trunc(hi) - math.trunc(lo) + 1
            if n >= int_range:
                return [math.trunc(lo) + b - 1 + 0.5 for b in range(1, int_range + 1)]
            bin_size = value_range / n
            return [math.trunc(lo + b * bin_size) + 0.5 for b in range(1, int(n) + 1)]
        bin_size = (hi - lo) / n_bins
        return [lo + b * bin_size for b in range(1, n_bins + 1)]

    def bin_counts(self, edges: Sequence[float]) -> List[int]:
        bins = [0] * len(edges)
        for key, count in self.counts.items():
            value = float(key)
            for b, edge in enumerate(edges):
                if value <= edge:
                    bins[b] += count
                    break
        return bins

    def labels(self, edges: Sequence[float], n_bins: int) -> List[str]:
        out = []
        if self.integer_only:
            for b, edge in enumerate(edges):
                start = math.trunc(self.min) if b == 0 else math.trunc(edges[b - 1] - 0.5) + 1
                end = math.trunc(edge - 0.5)
                out.append(f"{start:.0f}" if start == end else f"{start:.0f} - {end:.0f}")
            return out
        precision = precision_for_bins(self.min, self.max, len(edges))
        for b, edge in enumerate(edges):
            start = self.min if b == 0 else edges[b - 1]
            out.append(f"{start:.{precision}f} - {edge:.{precision}f}")
        return out


class Histogram:
    def __init__(self, n_bins: int = DEFAULT_BINS, max_bar_len: int = DEFAULT_BAR_LEN,
                 header: bool = False, fields: Optional[Iterable[int]] = None):
        self.n_bins = n_bins
        self.max_bar_len = max_bar_len
        self.header = header
        self.fields: Optional[Set[int]] = set(fields) if fields else None
        self.headers: Dict[int, str] = {}
        self.histograms: Dict[int, FieldHistogram] = {}

    def _has_number(self, row: Sequence[str]) -> bool:
        return any(is_number(clean_field(v)) for v in row)

    def _set_headers(self, row: Sequence[str]) -> None:
        self.headers = {f: re.sub(r"\s+", " ", v).strip() for f, v in enumerate(row, start=1)}

    def process_rows(self, rows: Sequence[Sequence[str]]) -> None:
        rows = [r for r in rows if r]
        if not rows:
            return
        start = 0
        if self.header:
            self._set_headers(rows[0])
            start = 1
        elif len(rows) > 1 and not self._has_number(rows[0]) and self._has_number(rows[1]):
            self._set_headers(rows[0])
            start = 1
        for row in rows[start:]:
            for f, raw in enumerate(row, start=1):
                if self.fields is not None and f not in self.fields:
                    continue
                value = clean_field(raw)
                if not is_number(value):
                    continue
                hist = self.histograms.setdefault(f, FieldHistogram())
                hist.add(to_number(value), bool(_INTEGER_RE.match(value)))

    def render(self) -> List[str]:
        out: List[str] = []
        for f in sorted(self.histograms):
            hist = self.histograms[f]
            name = self.headers.get(f)
            title = f"Hist: {name} (field {f})" if name else f"Hist: field {f}"
            out.append(f"{title}, cardinality {len(hist.counts)}")
            edges = hist.edges(self.n_bins)
            bins = hist.bin_counts(edges)
            max_bin = max(bins) if bins else 0
            scale = self.max_bar_len / max_bin if max_bin > self.max_bar_len else 1
            for label, count in zip(hist.labels(edges, self.n_bins), bins):
                bar = "+" * int(count * scale)
                out.append(f"{label:>{LABEL_WIDTH}} {bar} ({count})")
            out.append("")
        return out
