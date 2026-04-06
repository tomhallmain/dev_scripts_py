"""
Match lines from a second dataset against keys seen in a first (``matches.awk`` port).

Uses :class:`~scripts.DataFile.DataFile` for separator inference and row parsing — callers pass
two ``DataFile`` instances into :class:`FileComparator`.
"""
from __future__ import annotations

import sys
from typing import Optional, Tuple

from scripts.DataFile import DataFile
from scripts.cli_arg_parse_utils import EffectiveKeys


class FileComparator:
    def __init__(
        self,
        data_file1: DataFile,
        data_file2: DataFile,
        *,
        effective_keys: EffectiveKeys,
    ) -> None:
        self.df1 = data_file1
        self.df2 = data_file2
        self.effective_keys = effective_keys
        self.records: dict[str, int] = {}
        self.selected_lines: list[str] = []

    @staticmethod
    def _key_from_row(row: list[str], key_1based: Optional[int]) -> Optional[str]:
        if key_1based is None:
            return None
        i = key_1based - 1
        if i < 0 or i >= len(row):
            return None
        return row[i]

    def compare_files(self, *, include_matches: bool = True) -> None:
        df1, df2 = self.df1, self.df2

        if self.effective_keys.k1 is None and self.effective_keys.k2 is None:
            raw1 = df1.read_raw_lines()
            raw2 = df2.read_raw_lines()
            for ln in raw1:
                self.records[ln.rstrip("\n\r")] = 1
            for ln in raw2:
                found = ln.rstrip("\n\r") in self.records
                if found == include_matches:
                    self.selected_lines.append(ln)
            return

        data1 = df1.get_data()
        data2 = df2.get_data()
        raw2 = df2.read_raw_lines()
        if len(data2) != len(raw2):
            raise RuntimeError("internal error: row count mismatch for second DataFile")

        for row in data1:
            k = self._key_from_row(row, self.effective_keys.k1)
            if k is not None:
                self.records[k] = 1

        for i, row in enumerate(data2):
            k = self._key_from_row(row, self.effective_keys.k2)
            found = k is not None and k in self.records
            if found == include_matches:
                self.selected_lines.append(raw2[i])

    def print_selected_lines(self, *, verbose: bool = False, inverse: bool = False) -> None:
        if len(self.selected_lines) > 0:
            if verbose:
                if inverse:
                    print("Records unique to second file:")
                else:
                    print("Records found in both files:")
                print()
            sys.stdout.writelines(self.selected_lines)
        else:
            if inverse:
                print("NO COMPLEMENTS FOUND")
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
        validate_and_resolve_key_fields,
    )

    effective_keys = validate_and_resolve_key_fields(key=key, key1=key1, key2=key2)

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
        comparator = FileComparator(df1, df2, effective_keys=effective_keys)
        comparator.compare_files(include_matches=True)
        comparator.print_selected_lines(verbose=verbose, inverse=False)
    finally:
        resolution.cleanup_stdin_backed_data_files()


def run_comps(
    args: Tuple[str, ...],
    *,
    key: Optional[int] = None,
    key1: Optional[int] = None,
    key2: Optional[int] = None,
    fs: Optional[str] = None,
    verbose: bool = False,
) -> int:
    """CLI entry: complement of ``matches`` (rows from second dataset not present in first)."""
    from scripts.cli_arg_parse_utils import (
        CliArgContext,
        PathCandidatePredicate,
        validate_and_resolve_key_fields,
    )

    effective_keys = validate_and_resolve_key_fields(key=key, key1=key1, key2=key2)
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND,
        field_separator=fs,
    )
    resolution = ctx.resolve_join_style_paths(
        check_same_file_pair=True,
        same_file_pair_message="Files are the same!",
    )
    resolution.require_exactly_two_inputs(
        message="comps expects exactly two FILE paths, or one FILE with the second input on stdin."
    )
    data_files = resolution.materialize_data_files(
        stdin_text=ctx.stdin_text, field_separator=fs
    )
    df1, df2 = data_files[0], data_files[1]
    try:
        comparator = FileComparator(df1, df2, effective_keys=effective_keys)
        comparator.compare_files(include_matches=False)
        comparator.print_selected_lines(verbose=verbose, inverse=True)
        return 0
    finally:
        resolution.cleanup_stdin_backed_data_files()


