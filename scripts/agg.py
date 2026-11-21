"""``ds agg`` -- append row aggregates as new columns and column aggregates as new rows.

An expression is ``OP`` or ``OP|SCOPE``. ``OP`` is ``+`` (sum), ``-`` (negated sum),
``*`` (product), ``/`` (first value divided by each following non-zero value) or
``m``/``mean``. ``SCOPE`` is ``all`` (the default) or ``START..END``: field numbers for row
aggregates, line numbers (counting a header line) for column aggregates.

Only numeric values take part; a row or column without any shows the expression itself,
so a header row or a text label column carries the expression as its label. Column
aggregates also cover the new row-aggregate columns. With ``header``, the first line gets
the expressions as its new cells, is left out of column aggregates, and every line gets a
leading cell that holds the expression on the summary rows.
"""
import re
from typing import List, Optional, Sequence, Tuple

DEFAULT_EXPRESSION = "+|all"
OPS = {"+": "+", "-": "-", "\\-": "-", "*": "*", "/": "/", "m": "m", "mean": "m"}

_NUMBER_RE = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$")


class AggError(Exception):
    pass


def awk_number(value: float) -> str:
    """A number as AWK prints it (``%.6g`` unless an integer)."""
    if value == int(value) and abs(value) < 1e16:
        return str(int(value))
    return "%.6g" % value


def to_number(value: str) -> Optional[float]:
    return float(value) if _NUMBER_RE.match(value) else None


class AggExpression:
    def __init__(self, text: str):
        self.raw = text.strip()
        op_text, _, scope = self.raw.partition("|")
        if op_text not in OPS:
            raise AggError(
                f'unsupported aggregation "{self.raw}"; supported: OP or OP|all or '
                "OP|START..END with OP one of + - * / m mean")
        self.op = OPS[op_text]
        self.scope: Optional[Tuple[int, int]] = None
        scope = scope.strip()
        if scope and scope != "all":
            m = re.fullmatch(r"(\d+)\.\.(\d+)", scope)
            if not m:
                raise AggError(f'unsupported scope "{scope}" in "{self.raw}"; use all or START..END')
            self.scope = (int(m.group(1)), int(m.group(2)))

    def in_scope(self, index: int) -> bool:
        return self.scope is None or self.scope[0] <= index <= self.scope[1]

    def apply(self, values: Sequence[float]) -> Optional[float]:
        if not values:
            return None
        if self.op == "+":
            return sum(values)
        if self.op == "-":
            return -sum(values)
        if self.op == "*":
            result = 1.0
            for v in values:
                result *= v
            return result
        if self.op == "/":
            result = values[0]
            for v in values[1:]:
                if v != 0:
                    result /= v
            return result
        return sum(values) / len(values)

    def cell(self, values: Sequence[float]) -> str:
        result = self.apply(values)
        return self.raw if result is None else awk_number(result)


def parse_expressions(spec: Optional[str]) -> List[AggExpression]:
    if not spec or spec.strip() == "0":
        return []
    return [AggExpression(part) for part in spec.split(",") if part.strip()]


class Agg:
    def __init__(self, r_aggs: Optional[str] = None, c_aggs: Optional[str] = None,
                 header: bool = False):
        if r_aggs is None and c_aggs is None:
            r_aggs = c_aggs = DEFAULT_EXPRESSION
        self.row_aggs = parse_expressions(r_aggs)
        self.column_aggs = parse_expressions(c_aggs)
        self.header = header

    def run(self, rows: Sequence[Sequence[str]]) -> List[List[str]]:
        rows = [list(r) for r in rows if r and any(c.strip() for c in r)]
        extended: List[List[str]] = []
        for i, row in enumerate(rows):
            if self.header and i == 0:
                extended.append(row + [e.raw for e in self.row_aggs])
                continue
            new_cells = []
            for expr in self.row_aggs:
                values = [v for f, cell in enumerate(row, start=1) if expr.in_scope(f)
                          for v in [to_number(cell)] if v is not None]
                new_cells.append(expr.cell(values))
            extended.append(row + new_cells)

        out = [([""] + r if self.header else r) for r in extended]
        n_columns = max((len(r) for r in extended), default=0)
        for expr in self.column_aggs:
            summary = []
            for c in range(n_columns):
                values = []
                for line_no, row in enumerate(extended, start=1):
                    if (self.header and line_no == 1) or not expr.in_scope(line_no):
                        continue
                    v = to_number(row[c]) if c < len(row) else None
                    if v is not None:
                        values.append(v)
                summary.append(expr.cell(values))
            out.append(([expr.raw] if self.header else []) + summary)
        return out
