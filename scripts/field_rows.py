"""Split a data file into rows of fields for the table commands.

A separator that is empty or only whitespace splits on runs of whitespace, as AWK's default
``FS=" "`` does, so aligned columns do not produce empty fields. Any other separator is
split on literally. Comma-separated ``.csv`` files are parsed as CSV, so quoted fields may
contain the separator.
"""
import csv
from typing import List, Optional

from scripts.utils import Utils


def split_fields(line: str, field_separator: Optional[str]) -> List[str]:
    if field_separator and field_separator.strip():
        return line.split(field_separator)
    return line.split()


def read_rows(file_path: str, field_separator: Optional[str],
              *, skip_blank: bool = False) -> List[List[str]]:
    """Rows of fields from ``file_path``; ``skip_blank`` drops lines with no content."""
    rows: List[List[str]] = []
    if field_separator == "," and (Utils.get_file_extension(file_path) or "").lower() == "csv":
        with open(file_path, newline="", encoding="utf-8", errors="replace") as f:
            for row in csv.reader(f, skipinitialspace=True):
                if skip_blank and not any(c.strip() for c in row):
                    continue
                rows.append([c.strip() for c in row])
        return rows
    with open(file_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if skip_blank and not line.strip():
                continue
            rows.append(split_fields(line, field_separator))
    return rows
