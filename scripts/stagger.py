from __future__ import annotations

import os
import textwrap
from typing import Optional

from scripts.DataFile import DataFile


def _align_text(text: str, width: int, align: str) -> str:
    if width <= 0:
        return text
    if align == "r":
        return text.rjust(width)
    if align == "c":
        return text.center(width)
    return text.ljust(width)


def _wrapped_lines(text: str, width: int, wrap_mode: str) -> list[str]:
    if width <= 0:
        return [text]
    if len(text) <= width:
        return [text]
    if wrap_mode == "char":
        return [text[i : i + width] for i in range(0, len(text), width)]
    out = textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False)
    return out or [text]


def print_staggered(
    data_file: DataFile,
    *,
    stag_size: int = 5,
    tty_size: Optional[int] = None,
    style: str = "simple",
    wrap: str = "smart",
    numbers: bool = False,
    align: str = "l",
    max_width: int = 0,
    ellipsis: bool = False,
    wrap_char: str = "↪",
) -> None:
    """
    Print rows as staggered fields.

    Supports the subset of ``stagger.awk`` options that are exercised in parity tests.
    """
    if tty_size is None:
        try:
            tty_size = os.get_terminal_size().columns
        except OSError:
            tty_size = 80

    rows = data_file.get_data()

    def next_indent(current: int) -> int:
        if style == "compact":
            return current + 2
        return current + stag_size

    for row_idx, row in enumerate(rows, start=1):
        indent = 0
        if numbers:
            print(f"{row_idx:<6}", end=" ")
        for field_idx, raw_field in enumerate(row):
            width = max(1, tty_size - indent)
            if max_width > 0:
                width = min(width, max_width)
            lines = _wrapped_lines(raw_field, width, wrap)
            if ellipsis and len(raw_field) > width * 2 and len(lines) > 0:
                lines = [lines[0] + "..."]
            indent_str = " " * indent
            if lines:
                print(indent_str + _align_text(lines[0], width, align))
                for extra in lines[1:]:
                    print(indent_str + f"{wrap_char} " + _align_text(extra, width - 2, align))
            else:
                print(indent_str)
            indent = next_indent(indent)
        if row_idx < len(rows):
            print("")