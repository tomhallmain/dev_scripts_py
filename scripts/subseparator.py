import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

from scripts.utils import re_unescape

# Characters that carry regex meaning; a pattern made up entirely of these is escaped
# for literal matching, anything else is passed through as a regex.
METACHARS = "\\.^$(){}[]|*+?"

ERR_MISSING_PATTERN = "ERROR: subsep_pattern must be set"
ERR_INVALID_FIELDS = "ERROR: No valid fields specified in apply_to_fields"


def escape_preserve_regex(pattern: str) -> str:
    """Escape ``pattern`` unless it carries regex syntax worth preserving."""
    meta_count = sum(1 for c in pattern if c in METACHARS)
    if meta_count == len(pattern):
        return re.escape(pattern)
    return pattern


class SubseparatorFinder:
    """Extend fields that share a common sub-separator into separate output fields.

    Runs in two passes over the same rows: the first records, per field position, the
    largest number of subfields seen and how many of those were empty; the second emits
    every row padded out to that width, so a column that splits into three parts on one
    row still occupies three output columns on rows where it does not split at all.
    """

    def __init__(self, subsep_pattern=None, nomatch_handler=" ", debug=False, escape=False,
                 regex=False, apply_to_fields=None, OFS=" ", retain_pattern=False):
        self.debug = debug
        self.escape = escape
        self.regex = regex
        self.retain_pattern = retain_pattern
        self.OFS = " " if OFS is None else OFS

        if not subsep_pattern:
            print(ERR_MISSING_PATTERN)
            sys.exit(1)

        self.unescaped_pattern = re_unescape(subsep_pattern)
        if regex:
            self.subsep_pattern = subsep_pattern
        elif escape:
            self.subsep_pattern = re.escape(subsep_pattern)
        else:
            self.subsep_pattern = escape_preserve_regex(subsep_pattern)

        if not nomatch_handler:
            self.nomatch_handler = r"\s+"
        elif regex:
            self.nomatch_handler = nomatch_handler
        elif escape:
            self.nomatch_handler = re.escape(nomatch_handler)
        else:
            self.nomatch_handler = escape_preserve_regex(nomatch_handler)

        self.RelevantFields: Dict[int, int] = {}
        if apply_to_fields:
            for af in apply_to_fields.split(','):
                if re.match(r'^[0-9]+$', af):
                    self.RelevantFields[int(af)] = 1
            if len(self.RelevantFields) < 1:
                print(ERR_INVALID_FIELDS)
                sys.exit(1)

        self.max_subseps: Dict[int, int] = {}
        self.subfield_shifts: Dict[int, int] = {}

    # -- splitting -------------------------------------------------------

    def _split_subsep(self, field: str) -> List[str]:
        return re.split(self.subsep_pattern, field)

    def _split_nomatch(self, field: str) -> List[str]:
        # A bare space means "split on whitespace runs, ignoring leading/trailing".
        if self.nomatch_handler == " ":
            return field.split()
        return re.split(self.nomatch_handler, field)

    @staticmethod
    def read_rows(file_path: str, field_separator: Optional[str] = None) -> List[List[str]]:
        """Split each line of ``file_path`` into fields on ``field_separator``/whitespace."""
        rows: List[List[str]] = []
        with open(file_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n").rstrip("\r")
                if field_separator and field_separator.strip():
                    rows.append(line.split(field_separator))
                else:
                    rows.append(line.split())
        return rows

    # -- pass one --------------------------------------------------------

    def analyze_rows(self, rows: Sequence[Sequence[str]]) -> Tuple[Dict[int, int], Dict[int, int]]:
        """Record the widest split and the empty-subfield shift for each field position."""
        for fields in rows:
            if self.RelevantFields:
                indices = sorted(self.RelevantFields)
            else:
                indices = range(1, len(fields) + 1)
            for index in indices:
                if index > len(fields):
                    continue
                parts = self._split_subsep(fields[index - 1])
                num_subseps = len(parts)
                if num_subseps > 1 and num_subseps > self.max_subseps.get(index, 0):
                    self.max_subseps[index] = num_subseps
                    for part in parts:
                        if not part.strip():
                            self.subfield_shifts[index] = self.subfield_shifts.get(index, 0) - 1
        return self.max_subseps, self.subfield_shifts

    # -- pass two --------------------------------------------------------

    def _render_field(self, field: str, index: int, last_field: bool) -> str:
        shift = self.subfield_shifts.get(index, 0)
        n_subfields = self.max_subseps.get(index, 0) + shift
        partitions = n_subfields * 2 - 1 - shift

        if partitions <= 0:
            return field.strip() + ("" if last_field else self.OFS)

        parts = self._split_subsep(field)
        num_subseps = len(parts)
        handling: Optional[List[str]] = None
        pieces: List[str] = []
        k = 0

        for j in range(1, partitions + 1):
            conditional_ofs = "" if (last_field and j == partitions) else self.OFS
            outer_subfield = j % 2 + shift
            if outer_subfield:
                k += 1

            if num_subseps < n_subfields - shift:
                if handling is None:
                    handling = self._split_nomatch(field)
                if outer_subfield:
                    value = handling[k - 1] if 0 <= k - 1 < len(handling) else ""
                    pieces.append(value.strip() + conditional_ofs)
                elif self.retain_pattern:
                    pieces.append(conditional_ofs)
            else:
                if outer_subfield:
                    i = k - shift - 1
                    value = parts[i] if 0 <= i < len(parts) else ""
                    pieces.append(value.strip() + conditional_ofs)
                elif self.retain_pattern:
                    pieces.append(self.unescaped_pattern + self.OFS)

        return "".join(pieces)

    def transform_rows(self, rows: Sequence[Sequence[str]]) -> List[str]:
        out: List[str] = []
        for fields in rows:
            nf = len(fields)
            out.append("".join(
                self._render_field(fields[i - 1], i, i == nf) for i in range(1, nf + 1)
            ))
        return out

    # -- entry points ----------------------------------------------------

    def process_file(self, file_path: str, field_separator: Optional[str] = None):
        """Run the analysis pass only, returning ``(max_subseps, subfield_shifts)``."""
        return self.analyze_rows(self.read_rows(file_path, field_separator))

    def transform_file(self, file_path: str, field_separator: Optional[str] = None) -> List[str]:
        """Run both passes over ``file_path`` and return the transformed lines."""
        rows = self.read_rows(file_path, field_separator)
        self.analyze_rows(rows)
        return self.transform_rows(rows)
