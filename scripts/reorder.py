"""``ds reo`` -- reorder, repeat, or slice data by rows and columns.

An order argument is a comma-separated list of tokens applied left to right, so tokens may
repeat an index and the output follows the order written rather than the source order. A
token is one of:

===============  ==========================================================
``a`` / ``all``  every index (also the default when the argument is empty)
``3``            a single index; negative counts back from the end
``2..5``         an inclusive range, descending when the endpoints invert
``r`` / ``rev``  every index in reverse, expanded where the token appears
``o`` / ``oth``  every index not already selected, in source order
===============  ==========================================================

``rev`` and ``others`` are prefix-matched, so ``r``/``re``/``rev``/``reverse`` are all the
same token. Both expand at the position they occupy: ``1,rev`` is index 1 followed by the
full reversed span, not a reversal of the whole argument.
"""
import re
from typing import Dict, List, Optional, Sequence

ALL_TOKENS = ("a", "all")

TYPE_INDEX = "index"
TYPE_RANGE = "range"
TYPE_REVERSE = "reverse"
TYPE_OTHERS = "others"
TYPE_ALL = "all"
TYPE_EXPR = "expr"
TYPE_FILTER = "filter"
TYPE_BOOL = "bool"
TYPE_FRAME = "frame"

TYPE_ANCHOR = "anchor"

# Anchored ranges: `start##end` or the regex form `/start/../end/`. Either endpoint may be
# omitted, defaulting to the first or last index.
_ANCHOR_RE_FORM = re.compile(r"^(?:/(?P<start>.*?)/)?\.\.(?:/(?P<end>.*?)/)?$")

# Tokens whose selection depends on the data; if an argument uses one and nothing matches,
# the command reports "No matches found" rather than printing an empty result.
DATA_DEPENDENT_TYPES = ("filter", "expr", "bool", "frame", "anchor")
# uniq applies to these, per "unique indices on searches, expressions, reverses".
UNIQ_TOKEN_TYPES = DATA_DEPENDENT_TYPES + ("reverse", "others")
# Only these leave an empty column behind when they select nothing.
PLACEHOLDER_TOKEN_TYPES = UNIQ_TOKEN_TYPES
NO_MATCHES_MESSAGE = "No matches found"

# A frame token is `N[frame_pattern<filter>`. The frame index sits on the same axis as the
# selection (a row for a row argument, a column for a column argument) and defaults to 1.
_FRAME_RE = re.compile(r"^(?P<frame>-?\d*)\[(?P<rest>.*)$")
# Where the frame pattern ends and its trailing filter begins.
_FRAME_FILTER_RE = re.compile(r"(!~|~|>=|<=|!=|>|<|=|[*/%+][0-9.]+$)")

# Filter forms, checked in this order. An optional leading index scopes the test to one
# cross-span position (field N for a row argument, row N for a column argument); without it
# the token matches when any value in the span satisfies the test.
_LEN_RE = re.compile(r"^(?:len|length)\((?P<scope>-?\d*)\)(?P<rest>.*)$", re.IGNORECASE)
_REGEX_FILTER_RE = re.compile(r"^(?P<scope>-?\d+)?(?P<op>!~|~)(?P<pattern>.*)$")
_COMP_FILTER_RE = re.compile(
    r"^(?P<scope>-?\d+)?(?P<arith>[*/%+\-][0-9.]+)?(?P<op>>=|<=|!=|>|<|=)(?P<rhs>.*)$"
)

# Longest first so ">=" is not read as ">" followed by a stray "=".
COMPARATORS = (">=", "<=", "!=", ">", "<", "=")

# An index expression may only contain the index variable, numbers, arithmetic and
# parentheses. Anything else is rejected rather than evaluated.
_EXPR_SAFE_RE = re.compile(r"^[\sNRF0-9+\-*/%().]*$")
_INDEX_VAR_RE = re.compile(r"\b(NR|NF)\b")


class ReorderError(Exception):
    """Raised for an order argument that cannot be parsed."""


class OrderToken:
    __slots__ = ("kind", "start", "end", "expr", "comp", "rhs",
                 "scope", "op", "pattern", "arith", "measure", "groups", "ignore_case")

    def __init__(self, kind: str, start=None, end=None, expr=None, comp=None, rhs=None,
                 scope=None, op=None, pattern=None, arith=None, measure=None, groups=None):
        self.kind = kind
        self.start = start
        self.end = end
        self.expr = expr
        self.comp = comp
        self.rhs = rhs
        self.scope = scope
        self.op = op
        self.pattern = pattern
        self.arith = arith
        # "len" tests the length of a value rather than the value itself.
        self.measure = measure
        # For TYPE_BOOL: a list of OR-groups, all of which must hold.
        self.groups = groups
        # Set by a "/i" suffix, which forces a case-insensitive match even under --cased.
        self.ignore_case = False

    def __repr__(self):
        if self.kind == TYPE_RANGE:
            return f"<{self.kind} {self.start}..{self.end}>"
        if self.kind == TYPE_INDEX:
            return f"<{self.kind} {self.start}>"
        if self.kind == TYPE_EXPR:
            return f"<{self.kind} {self.expr}{self.comp}{self.rhs}>"
        return f"<{self.kind}>"


def split_comparator(token: str):
    """Split ``token`` into ``(left, comparator, right)``; comparator is None if absent."""
    for comp in COMPARATORS:
        position = token.find(comp)
        # position 0 is valid for a bare comparison like ">0", where there is no left side.
        if position >= 0:
            return token[:position].strip(), comp, token[position + len(comp):].strip()
    return token.strip(), None, None


def evaluate_arithmetic(expr: str, index: int) -> Optional[float]:
    """Evaluate an index expression with NR/NF bound to ``index``.

    The expression is whitelist-checked first, so only the index variable, numbers and
    arithmetic operators reach evaluation.
    """
    if not _EXPR_SAFE_RE.match(expr):
        raise ReorderError(f"unsupported characters in expression: {expr}")
    substituted = _INDEX_VAR_RE.sub(str(index), expr)
    try:
        return eval(substituted, {"__builtins__": {}}, {})  # noqa: S307 - whitelisted above
    except Exception:
        return None


def compare(left, right, comp: str) -> bool:
    """Apply a comparator, preferring a numeric comparison when both sides are numbers."""
    try:
        left_val, right_val = float(left), float(right)
    except (TypeError, ValueError):
        left_val, right_val = str(left), str(right)
    if comp == "=":
        return left_val == right_val
    if comp == "!=":
        return left_val != right_val
    if comp == ">":
        return left_val > right_val
    if comp == ">=":
        return left_val >= right_val
    if comp == "<":
        return left_val < right_val
    if comp == "<=":
        return left_val <= right_val
    return False


def split_order_arg(arg: str) -> List[str]:
    """Split on commas, honoring a backslash-escaped comma as a literal."""
    parts: List[str] = []
    current = ""
    escaped = False
    for char in arg:
        if escaped:
            current += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ",":
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [p.strip() for p in parts]


def _is_int(token: str) -> bool:
    return bool(token) and (token[1:] if token[0] in "+-" else token).isdigit()


_IGNORE_CASE_RE = re.compile(r"/[Ii](?=$|~)")


def parse_token(token: str) -> OrderToken:
    """Parse one order-argument token, honoring a ``/i`` case-insensitivity suffix."""
    stripped = _IGNORE_CASE_RE.sub("", token)
    parsed = _parse_token(stripped)
    if stripped != token:
        parsed.ignore_case = True
    return parsed


def _parse_token(token: str) -> OrderToken:
    """Parse one order-argument token. Raises :class:`ReorderError` if unrecognized."""
    # Boolean combination. "||" binds tighter than "&&", so the token is read as an AND of
    # OR-groups: `a && b || c` selects indices satisfying a AND (b OR c).
    if "&&" in token or "||" in token:
        groups = [
            [parse_token(part.strip()) for part in group.split("||") if part.strip()]
            for group in token.split("&&")
            if group.strip()
        ]
        return OrderToken(TYPE_BOOL, groups=groups)

    lowered = token.lower()

    if lowered in ALL_TOKENS:
        return OrderToken(TYPE_ALL)
    # Prefix matches, the way the shell original accepts r/re/rev/reverse.
    if lowered and "reverse".startswith(lowered):
        return OrderToken(TYPE_REVERSE)
    if lowered and "others".startswith(lowered):
        return OrderToken(TYPE_OTHERS)

    # Anchored ranges are checked before ranges and indices, since "3##" and "/6/../2/"
    # would otherwise be misread as an index or a numeric range.
    if "##" in token:
        start_pattern, _, end_pattern = token.partition("##")
        return OrderToken(TYPE_ANCHOR, start=start_pattern.strip() or None,
                          end=end_pattern.strip() or None)
    anchor_re = _ANCHOR_RE_FORM.match(token)
    if anchor_re and (anchor_re.group("start") or anchor_re.group("end")):
        return OrderToken(TYPE_ANCHOR, start=anchor_re.group("start") or None,
                          end=anchor_re.group("end") or None)

    frame_match = _FRAME_RE.match(token)
    if frame_match:
        frame = frame_match.group("frame")
        rest = frame_match.group("rest")
        split_at = _FRAME_FILTER_RE.search(rest)
        if not split_at:
            # No trailing filter: this is a plain cross-span search at the frame index.
            return OrderToken(
                TYPE_FILTER, op="~", pattern=rest, scope=int(frame) if frame else 1
            )
        frame_pattern = rest[: split_at.start()]
        trailing = rest[split_at.start():]
        if trailing[0] in "*/%+":
            # An arithmetic tail with no comparator is compared against zero.
            trailing_token = OrderToken(TYPE_FILTER, op="=", rhs="0", arith=trailing)
        else:
            trailing_token = parse_token(trailing)
        return OrderToken(
            TYPE_FRAME, scope=int(frame) if frame else 1,
            pattern=frame_pattern, groups=[trailing_token],
        )

    len_match = _LEN_RE.match(token)
    if len_match:
        scope = len_match.group("scope")
        _, comp, rhs = split_comparator(len_match.group("rest"))
        if comp is None:
            comp, rhs = "=", "0"
        return OrderToken(
            TYPE_FILTER, measure="len", op=comp, rhs=rhs,
            scope=int(scope) if scope else None,
        )

    regex_match = _REGEX_FILTER_RE.match(token)
    if regex_match:
        scope = regex_match.group("scope")
        return OrderToken(
            TYPE_FILTER, op=regex_match.group("op"),
            pattern=regex_match.group("pattern"),
            scope=int(scope) if scope else None,
        )

    # An index expression is anything referring to the index variable (NR for rows, NF for
    # columns). With no comparator the expression is tested against zero.
    if _INDEX_VAR_RE.search(token):
        left, comp, right = split_comparator(token)
        return OrderToken(TYPE_EXPR, expr=left, comp=comp or "=", rhs=right if comp else "0")

    if ".." in token:
        left, _, right = token.partition("..")
        left, right = left.strip(), right.strip()
        if (left == "" or _is_int(left)) and (right == "" or _is_int(right)):
            start = int(left) if left else None
            end = int(right) if right else None
            return OrderToken(TYPE_RANGE, start, end)
        raise ReorderError(f"unrecognized range token: {token}")

    if _is_int(token):
        return OrderToken(TYPE_INDEX, int(token))

    # A bare arithmetic tail such as "%7" is compared against zero.
    if re.match(r"^[*/%+][0-9.]+$", token):
        return OrderToken(TYPE_FILTER, op="=", rhs="0", arith=token)

    comp_match = _COMP_FILTER_RE.match(token)
    if comp_match:
        scope = comp_match.group("scope")
        return OrderToken(
            TYPE_FILTER, op=comp_match.group("op"), rhs=comp_match.group("rhs"),
            arith=comp_match.group("arith"), scope=int(scope) if scope else None,
        )

    raise ReorderError(f"unrecognized order token: {token}")


_NUMERIC_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([Ee][+-]?\d+)?$")


def _as_number(value: str):
    """Return ``value`` as a number, stripping currency/thousands marks; None if not numeric."""
    cleaned = re.sub(r'[$,"]', "", (value or "").strip())
    if not _NUMERIC_RE.match(cleaned):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _matches_value(token: OrderToken, value: str, cased: bool) -> bool:
    """Test one cross-span value against a filter token."""
    cased = cased and not token.ignore_case
    if token.measure == "len":
        return compare(len(value), token.rhs, token.op)

    if token.op in ("~", "!~"):
        flags = 0 if cased else re.IGNORECASE
        try:
            found = re.search(token.pattern, value, flags) is not None
        except re.error:
            found = token.pattern in value
        return found if token.op == "~" else not found

    # Only numeric fields take part in a comparison; a non-numeric field is skipped, except
    # under "!=" where it counts as empty and so differs from any number.
    numeric = _as_number(value)
    if numeric is None:
        return token.op == "!=" and compare("", token.rhs, token.op)

    left = numeric
    if token.arith:
        try:
            left = eval(f"({numeric}){token.arith}", {"__builtins__": {}}, {})
        except Exception:
            return False
    return compare(left, token.rhs, token.op)


def evaluate_filter(token: OrderToken, values: Sequence[str], cased: bool) -> bool:
    """Apply a filter token across one span's values.

    A scoped token tests only that cross-span position. An unscoped token matches when any
    value satisfies it -- except a negated regex, which requires that none do.
    """
    if token.scope is not None:
        position = normalize_index(token.scope, len(values))
        if not 1 <= position <= len(values):
            return False
        return _matches_value(token, values[position - 1], cased)

    if token.op == "!~":
        return all(_matches_value(token, v, cased) for v in values)
    return any(_matches_value(token, v, cased) for v in values)


def parse_order_arg(arg: Optional[str]) -> List[OrderToken]:
    """Parse a full order argument into tokens; an empty argument means every index."""
    if arg is None or arg.strip() == "":
        return [OrderToken(TYPE_ALL)]
    return [parse_token(t) for t in split_order_arg(arg) if t != ""]


def normalize_index(index: int, max_index: int) -> int:
    """Map a possibly-negative 1-based index onto a positive one; -1 is the last index."""
    if index < 0:
        return max_index + 1 + index
    return index


def token_selects(token: OrderToken, index: int, max_index: int, values_at, cased: bool,
                  whole_line_at=None, frame_resolver=None) -> bool:
    """Whether a data-dependent token selects ``index``."""
    if token.kind == TYPE_BOOL:
        return all(
            any(token_selects(t, index, max_index, values_at, cased, whole_line_at,
                              frame_resolver) for t in group)
            for group in token.groups
        )
    if token.kind == TYPE_EXPR:
        value = evaluate_arithmetic(token.expr, index)
        return value is not None and compare(value, token.rhs, token.comp)
    if token.kind == TYPE_FILTER:
        if values_at is None:
            raise ReorderError("value filters require data to test against")
        # With field separation off, len() measures the whole line rather than a field.
        if token.measure == "len" and whole_line_at is not None:
            return evaluate_filter(token, [whole_line_at(index)], cased)
        return evaluate_filter(token, values_at(index), cased)
    if token.kind == TYPE_INDEX:
        return index == normalize_index(token.start, max_index)
    if token.kind == TYPE_ANCHOR or token.kind == TYPE_FRAME:
        if frame_resolver is None:
            raise ReorderError("frame and anchor tokens require data to test against")
        return index in set(frame_resolver(token))
    return False


def resolve_frame(token: OrderToken, rows: Sequence[Sequence[str]], field_count: int,
                  row_call: bool, cased: bool) -> List[int]:
    """Resolve a frame token to the indices it selects, including the frame itself."""
    flags = 0 if (cased and not token.ignore_case) else re.IGNORECASE

    def matches(value: str) -> bool:
        try:
            return re.search(token.pattern, value, flags) is not None
        except re.error:
            return token.pattern in value

    def cell(r: int, c: int) -> str:
        row = rows[r - 1]
        return row[c - 1] if c - 1 < len(row) else ""

    trailing = token.groups[0]
    selected = set()

    if row_call:
        frame_row = normalize_index(token.scope, len(rows))
        if not 1 <= frame_row <= len(rows):
            return []
        frame_cols = [c for c in range(1, field_count + 1) if matches(cell(frame_row, c))]
        if not frame_cols:
            # The frame itself is only emitted once something in it has matched.
            return []
        selected.add(frame_row)
        for r in range(1, len(rows) + 1):
            values = [cell(r, c) for c in frame_cols]
            if values and evaluate_filter(trailing, values, cased):
                selected.add(r)
        return sorted(selected)

    frame_col = normalize_index(token.scope, field_count)
    if not 1 <= frame_col <= field_count:
        return []
    active_rows = [r for r in range(1, len(rows) + 1) if matches(cell(r, frame_col))]
    if not active_rows:
        return []
    # The frame column is recorded first, ahead of the columns its filter goes on to match.
    ordered = [frame_col]
    for c in range(1, field_count + 1):
        if c == frame_col:
            continue
        values = [cell(r, c) for r in active_rows]
        if values and evaluate_filter(trailing, values, cased):
            ordered.append(c)
    return ordered


def resolve_anchor(token: OrderToken, rows: Sequence[Sequence[str]], field_count: int,
                   row_call: bool, cased: bool) -> List[int]:
    """Resolve an anchored range to the indices between its two pattern endpoints."""
    flags = 0 if (cased and not token.ignore_case) else re.IGNORECASE

    def matches(value: str, pattern: str) -> bool:
        try:
            return re.search(pattern, value, flags) is not None
        except re.error:
            return pattern in value

    def cell(r: int, c: int) -> str:
        row = rows[r - 1]
        return row[c - 1] if c - 1 < len(row) else ""

    max_index = len(rows) if row_call else field_count

    # Both endpoints are found by a single ordered scan, each taking its first match. The one
    # exception: a position that has just set the start cannot also set an unset end, so
    # `2##3` starts at the first row holding "2" and ends at the *next* row holding "3".
    # Columns scan row-major, so a value in a later row can still anchor an earlier column.
    if row_call:
        positions = [(r, [v for v in rows[r - 1]]) for r in range(1, len(rows) + 1)]
    else:
        positions = [
            (c, [cell(r, c)])
            for r in range(1, len(rows) + 1)
            for c in range(1, field_count + 1)
        ]

    start = end = None
    for index, values in positions:
        if token.start is not None and start is None and any(
            matches(v, token.start) for v in values
        ):
            start = index
            if end is None:
                continue
        if token.end is not None and end is None and any(
            matches(v, token.end) for v in values
        ):
            end = index
        if start is not None and end is not None:
            break

    if token.start is not None and start is None:
        return []
    if token.end is not None and end is None:
        return []
    start = 1 if start is None else start
    end = max_index if end is None else end
    step = 1 if start <= end else -1
    return list(range(start, end + step, step))


def resolve_order(tokens: Sequence[OrderToken], max_index: int, uniq: bool = False,
                  values_at=None, cased: bool = False, frame_resolver=None,
                  discovery_order=None, whole_line_at=None,
                  unmatched_placeholder: bool = False) -> List[int]:
    """Expand tokens into the ordered, 1-based index list they select.

    ``values_at`` is a callable mapping a 1-based index to that span's cross-span values,
    and is required only when the argument contains value filters.

    Out-of-range indices are dropped rather than raising, matching the shell behavior of
    quietly producing nothing for an index past the end of the data.
    """
    order: List[int] = []
    seen = set()
    dropped_duplicate = False

    def in_range(index: int) -> bool:
        return 1 <= index <= max_index

    for token in tokens:
        produced: List[int] = []

        if token.kind == TYPE_ALL:
            produced = list(range(1, max_index + 1))
        elif token.kind == TYPE_REVERSE:
            produced = list(range(max_index, 0, -1))
        elif token.kind == TYPE_OTHERS:
            already = set(order)
            produced = [i for i in range(1, max_index + 1) if i not in already]
        elif token.kind == TYPE_INDEX:
            index = normalize_index(token.start, max_index)
            produced = [index] if in_range(index) else []
        elif token.kind == TYPE_RANGE:
            start = 1 if token.start is None else normalize_index(token.start, max_index)
            end = max_index if token.end is None else normalize_index(token.end, max_index)
            step = 1 if start <= end else -1
            produced = [i for i in range(start, end + step, step) if in_range(i)]
        elif token.kind in (TYPE_FRAME, TYPE_ANCHOR):
            if frame_resolver is None:
                raise ReorderError("frame and anchor tokens require data to test against")
            produced = [i for i in frame_resolver(token) if in_range(i)]
        elif token.kind in (TYPE_EXPR, TYPE_FILTER, TYPE_BOOL):
            produced = [
                i for i in range(1, max_index + 1)
                if token_selects(token, i, max_index, values_at, cased, whole_line_at,
                                 frame_resolver)
            ]
            if discovery_order is not None:
                produced = discovery_order(token, produced)

        # A column token that matches nothing still occupies one empty column.
        if not produced and unmatched_placeholder and token.kind in PLACEHOLDER_TOKEN_TYPES:
            order.append(0)
            continue

        # uniq constrains searches, expressions and reverses -- not plain indices or ranges.
        if uniq and token.kind in UNIQ_TOKEN_TYPES:
            kept = [i for i in produced if i not in seen]
            if len(kept) != len(produced):
                dropped_duplicate = True
            produced = kept

        order.extend(produced)
        seen.update(produced)

    # However many duplicates uniq removed, they collapse into a single empty column.
    if dropped_duplicate and unmatched_placeholder:
        order.append(0)

    return order


class Reorder:
    """Select and reorder rows and columns of fielded data."""

    def __init__(self, rows_arg=None, cols_arg=None, field_separator=None, ofs=None,
                 uniq=False, idx=False, cols_off=False, cased=False):
        self.rows_arg = rows_arg
        self.cols_arg = cols_arg
        self.field_separator = field_separator
        self.ofs = ofs if ofs is not None else (field_separator or " ")
        self.uniq = uniq
        self.idx = idx
        self.cased = cased
        # ``c=off`` disables field splitting entirely; rows are passed through whole.
        self.cols_off = cols_off
        self.row_tokens = parse_order_arg(rows_arg)
        self.col_tokens = parse_order_arg(cols_arg)

    def read_rows(self, file_path: str) -> List[List[str]]:
        """Split each line into fields, also recording the raw line for ``c=off`` output."""
        separator = self.field_separator
        rows: List[List[str]] = []
        self.raw_lines: List[str] = []
        with open(file_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n").rstrip("\r")
                self.raw_lines.append(line)
                if separator and separator.strip():
                    rows.append(line.split(separator))
                elif separator == "":
                    rows.append(list(line))
                else:
                    rows.append(line.split())
        return rows

    def max_field_count(self, rows: Sequence[Sequence[str]]) -> int:
        return max((len(r) for r in rows), default=0)

    def transform_rows(self, rows: Sequence[Sequence[str]]) -> List[str]:
        field_count = self.max_field_count(rows)

        def row_values(i):
            return list(rows[i - 1])

        def col_values(j):
            return [r[j - 1] if j - 1 < len(r) else "" for r in rows]

        whole_line_at = self._raw_line_at if self.cols_off else None
        row_order = resolve_order(
            self.row_tokens, len(rows), self.uniq, row_values, self.cased,
            lambda t: self._resolve_data_token(t, rows, field_count, True),
            whole_line_at=whole_line_at,
        )
        if self.cols_off:
            col_order = [1]
        else:
            col_order = resolve_order(
                self.col_tokens, field_count, self.uniq, col_values, self.cased,
                lambda t: self._resolve_data_token(t, rows, field_count, False),
                lambda t, matched: self._column_discovery_order(t, matched, rows),
                unmatched_placeholder=True,
            )

        uses_data_filters = any(
            t.kind in DATA_DEPENDENT_TYPES for t in self.row_tokens + self.col_tokens
        )
        if uses_data_filters and (not row_order or not any(c > 0 for c in col_order)):
            self.no_matches = True
            return [NO_MATCHES_MESSAGE]

        out: List[str] = []
        if self.idx and not self.cols_off:
            # Index header: a leading blank cell for the row-number column.
            out.append(self.ofs.join([""] + [str(c) if c > 0 else "" for c in col_order]))

        for row_number in row_order:
            if self.cols_off:
                # Field separation is off for output only; filters still saw split fields.
                out.append(self._raw_line(rows, row_number))
                continue
            row = rows[row_number - 1]
            cells = [self._cell(row, c) for c in col_order]
            if self.idx:
                cells = [str(row_number)] + cells
            out.append(self.ofs.join(cells))
        return out

    def _resolve_data_token(self, token, rows, field_count, row_call):
        if token.kind == TYPE_ANCHOR:
            return resolve_anchor(token, rows, field_count, row_call, self.cased)
        return resolve_frame(token, rows, field_count, row_call, self.cased)

    def _column_discovery_order(self, token, matched, rows):
        """Order matched columns the way a row-major scan discovers them.

        Rows are selected in source order simply because they are scanned in order, but a
        column is recorded the first time any row matches it, so column order follows first
        appearance rather than column number.
        """
        if token.kind != TYPE_FILTER or not matched:
            return matched

        def first_hit(column):
            for row_number, row in enumerate(rows, 1):
                value = row[column - 1] if column - 1 < len(row) else ""
                if _matches_value(token, value, self.cased):
                    return row_number
            return len(rows) + 1

        return sorted(matched, key=lambda c: (first_hit(c), c))

    @staticmethod
    def _cell(row: Sequence[str], column: int) -> str:
        """Index 0 is the placeholder an unmatched column token leaves behind."""
        if column < 1 or column - 1 >= len(row):
            return ""
        return row[column - 1]

    def _raw_line_at(self, row_number: int) -> str:
        raw = getattr(self, "raw_lines", None)
        if raw is not None and row_number - 1 < len(raw):
            return raw[row_number - 1]
        return ""

    def _raw_line(self, rows: Sequence[Sequence[str]], row_number: int) -> str:
        raw = getattr(self, "raw_lines", None)
        if raw is not None and row_number - 1 < len(raw):
            return raw[row_number - 1]
        return self.ofs.join(rows[row_number - 1])

    def transform_file(self, file_path: str) -> List[str]:
        return self.transform_rows(self.read_rows(file_path))
