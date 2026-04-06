#!/usr/bin/env python3
import re
from collections import defaultdict

from scripts.DataFile import DataFile


class FieldsCounter:
    """Value counts over fields; rows are read via :class:`DataFile`."""

    IFS = "|||"
    IFSRE = re.compile(r"\|\|\|")

    def __init__(
        self,
        data_file: DataFile,
        fields=None,
        min: int = 1,
        only_vals: bool = False,
    ) -> None:
        self.data_file = data_file
        self.fields = self._parse_fields(fields)
        # Shell does `let min=min-1` before awk; awk filters `count > min`.
        self.min_threshold = max(0, min - 1)
        self.counts = not only_vals
        self.counter: dict[str, int] = defaultdict(int)

    def _out_sep(self) -> str:
        return self.data_file.output_field_separator or self.data_file.field_separator or ""

    def _parse_fields(self, fields) -> list[int]:
        if fields is None or fields == "":
            return [1]
        s = str(fields).strip()
        if re.search(r"[A-Za-z]", s):
            return [0]
        parts = [int(x) for x in re.split(r"[ ,|\.:;_]+", s) if x.strip() != ""]
        return parts if parts else [1]

    def _row_key(self, row: list[str]) -> str:
        if not row:
            return ""
        if len(self.fields) == 1 and self.fields[0] == 0:
            return self._out_sep().join(row)
        parts = []
        for f in self.fields:
            idx = f - 1
            if 0 <= idx < len(row):
                parts.append(row[idx])
        return self.IFS.join(parts)

    def run(self) -> None:
        self.data_file.get_field_separator()
        rows = self.data_file.get_data()
        for row in rows:
            key = self._row_key(row)
            if key == "" and not (len(self.fields) == 1 and self.fields[0] == 0):
                continue
            self.counter[key] += 1

        items = [(c, k) for k, c in self.counter.items() if c > self.min_threshold]
        items.sort(key=lambda t: (-t[0], t[1]))

        sep = self._out_sep()
        for count, key in items:
            if self.counts:
                print(count, end=sep)
            if len(self.fields) == 1 and self.fields[0] == 0:
                print(key)
            else:
                parts = self.IFSRE.split(key)
                print(sep.join(parts))
