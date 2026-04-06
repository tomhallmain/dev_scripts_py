"""
Match lines from a second dataset against keys seen in a first (``matches.awk`` port).

Uses :class:`~scripts.DataFile.DataFile` for separator inference and row parsing — callers pass
two ``DataFile`` instances into :class:`FileComparator`.
"""
from __future__ import annotations

import sys
from typing import Optional, Tuple

from scripts.DataFile import DataFile


class FileComparator:
    def __init__(
        self,
        data_file1: DataFile,
        data_file2: DataFile,
        *,
        key: Optional[int] = None,
        key1: Optional[int] = None,
        key2: Optional[int] = None,
    ) -> None:
        self.df1 = data_file1
        self.df2 = data_file2
        self.key = key
        self.key1 = key1
        self.key2 = key2
        self.records: dict[str, int] = {}
        self.matches: list[str] = []

    def _merge_key_indices(self) -> None:
        if self.key is not None:
            if self.key1 is None:
                self.key1 = self.key
            if self.key2 is None:
                self.key2 = self.key
        if self.key1 is None and self.key2 is not None:
            self.key1 = self.key2
        if self.key2 is None and self.key1 is not None:
            self.key2 = self.key1

    @staticmethod
    def _key_from_row(row: list[str], key_1based: Optional[int]) -> Optional[str]:
        if key_1based is None:
            return None
        i = key_1based - 1
        if i < 0 or i >= len(row):
            return None
        return row[i]

    def compare_files(self) -> None:
        self._merge_key_indices()
        df1, df2 = self.df1, self.df2
        df1.get_field_separator()
        df2.get_field_separator()

        if self.key1 is None and self.key2 is None:
            raw1 = df1.read_raw_lines()
            raw2 = df2.read_raw_lines()
            for ln in raw1:
                self.records[ln.rstrip("\n\r")] = 1
            for ln in raw2:
                if ln.rstrip("\n\r") in self.records:
                    self.matches.append(ln)
            return

        data1 = df1.get_data()
        data2 = df2.get_data()
        raw2 = df2.read_raw_lines()
        if len(data2) != len(raw2):
            raise RuntimeError("internal error: row count mismatch for second DataFile")

        for row in data1:
            k = self._key_from_row(row, self.key1)
            if k is not None:
                self.records[k] = 1

        for i, row in enumerate(data2):
            k = self._key_from_row(row, self.key2)
            if k is not None and k in self.records:
                self.matches.append(raw2[i])

    def print_matches(self, verbose: bool = False) -> None:
        if len(self.matches) > 0:
            if verbose:
                print("Records found in both files:")
                print()
            sys.stdout.writelines(self.matches)
        else:
            print("NO MATCHES FOUND")


def run_matches(
    args: Tuple[str, ...],
    *,
    key: Optional[int] = None,
    key1: Optional[int] = None,
    key2: Optional[int] = None,
    fs: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """CLI entry: two paths, or one path + stdin for the second dataset."""
    from scripts.cli_arg_parse_utils import (
        CliArgContext,
        PathCandidatePredicate,
        validate_positive_key_field,
    )

    validate_positive_key_field("--key", key)
    validate_positive_key_field("--key1", key1)
    validate_positive_key_field("--key2", key2)

    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND,
        field_separator=fs,
    )
    resolution = ctx.resolve_join_style_paths()
    resolution.require_exactly_two_inputs(
        message=(
            "matches expects exactly two FILE paths, or one FILE with the second input on stdin."
        )
    )
    data_files = resolution.materialize_data_files(
        stdin_text=ctx.stdin_text, field_separator=fs
    )
    df1, df2 = data_files[0], data_files[1]
    try:
        comparator = FileComparator(df1, df2, key=key, key1=key1, key2=key2)
        comparator.compare_files()
        comparator.print_matches(verbose=verbose)
    finally:
        resolution.cleanup_stdin_backed_data_files()


if __name__ == "__main__":
    df_a = DataFile("file1.txt")
    df_b = DataFile("file2.txt")
    c = FileComparator(df_a, df_b, key=1)
    c.compare_files()
    c.print_matches()
