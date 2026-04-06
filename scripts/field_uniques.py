import re
from collections import defaultdict

from scripts.DataFile import DataFile


class FieldUniques:
    """Unique values (first time count exceeds threshold); rows from :class:`DataFile`."""

    def __init__(
        self,
        data_file: DataFile,
        fields_spec: str = "a",
        min_user: int = 1,
        order: str = "a",
    ) -> None:
        if not isinstance(data_file, DataFile):
            raise TypeError("FieldUniques expects a DataFile instance")
        self.data_file = data_file
        self.fields = self._parse_fields(fields_spec)
        # Shell: `let min=min-1` then awk `_[val] > min`
        self.min_threshold = max(0, min_user - 1)
        self.order = (order or "a").lower()

    def _parse_fields(self, fields_spec: str) -> list[int]:
        if not fields_spec or fields_spec == "a":
            return [0]
        s = str(fields_spec).strip()
        if re.search(r"[A-Za-z]", s):
            return [0]
        parts = [int(x) for x in re.split(r"[ ,|:;._]+", s) if x.strip() != ""]
        return parts if parts else [0]

    def _row_value(self, row: list[str], ofs: str) -> str:
        if not row:
            return ""
        if len(self.fields) == 1 and self.fields[0] == 0:
            return ofs.join(row)
        parts = []
        for f in self.fields:
            idx = f - 1
            if 0 <= idx < len(row):
                parts.append(row[idx])
        return ofs.join(parts)

    def _sort_lines(self, lines: list[str]) -> list[str]:
        """Match shell ``uniq`` / ``sort -n`` grouping: letters vs numbers, order flips with ``-r``."""
        non_numeric: list[str] = []
        numeric: list[tuple[int, str]] = []
        for s in lines:
            t = s.strip()
            if t and t.lstrip("-").isdigit():
                numeric.append((int(t), s))
            else:
                non_numeric.append(s)

        rev = self.order in ("d", "desc", "r")
        if not rev:
            non_numeric.sort()
            numeric.sort(key=lambda x: x[0])
            return non_numeric + [orig for _, orig in numeric]
        numeric.sort(key=lambda x: x[0], reverse=True)
        non_numeric.sort(reverse=True)
        return [orig for _, orig in numeric] + non_numeric

    def run(self) -> None:
        self.data_file.get_field_separator()
        rows = self.data_file.get_data()
        ofs = self.data_file.field_separator or " "

        counts: dict[str, int] = defaultdict(int)
        printed: list[str] = []
        seen: set[str] = set()

        for row in rows:
            val = self._row_value(row, ofs)
            counts[val] += 1
            if val not in seen and counts[val] > self.min_threshold:
                printed.append(val)
                seen.add(val)

        for line in self._sort_lines(printed):
            print(line)


def field_uniques_main(
    fields_spec: str | None = None,
    min_count: int = 1,
    order: str = "a",
    *,
    data_file: DataFile | None = None,
) -> None:
    """Optional helper: stdin-backed :class:`DataFile` when ``data_file`` is omitted."""
    df = data_file if data_file is not None else DataFile(None)
    FieldUniques(df, fields_spec=fields_spec or "a", min_user=min_count, order=order).run()


if __name__ == "__main__":
    import sys

    fs = sys.argv[1] if len(sys.argv) > 1 else "a"
    mc = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    ord_ = sys.argv[3] if len(sys.argv) > 3 else "a"
    field_uniques_main(fs, mc, ord_)
