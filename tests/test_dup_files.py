"""Tests for scripts/dup_files.py — DuplicateRemover."""
from __future__ import annotations

import os
import pytest

from scripts.dup_files import DuplicateRemover


@pytest.fixture
def tmp_remover(tmp_path):
    """Return a factory that builds a DuplicateRemover rooted at tmp_path."""
    def _make(**kwargs):
        return DuplicateRemover(str(tmp_path), **kwargs)
    return tmp_path, _make


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ---------------------------------------------------------------------------
# Basename-sorting: same-basename groups must appear adjacent in output
# ---------------------------------------------------------------------------

def test_handle_duplicates_same_basename_groups_sorted_together(tmp_path, capsys):
    """
    When multiple distinct duplicate groups share the same basename they should
    appear adjacent in handle_duplicates output (sorted by min basename).

    Layout
    ------
    a/report.txt   }  group 1 — content "report-v1"
    b/report.txt   }

    c/apple.txt    }  group 2 — content "apple"
    d/apple.txt    }

    e/report.txt   }  group 3 — content "report-v2" (different from group 1)
    f/report.txt   }

    Expected order after sort: apple.txt groups first, then both report.txt
    groups together (groups 1 and 3 adjacent, not interleaved with apple.txt).
    """
    for subdir in "abcdef":
        (tmp_path / subdir).mkdir()

    # group 1: report-v1
    _write(tmp_path / "a" / "report.txt", "report-v1")
    _write(tmp_path / "b" / "report.txt", "report-v1")

    # group 2: apple
    _write(tmp_path / "c" / "apple.txt", "apple")
    _write(tmp_path / "d" / "apple.txt", "apple")

    # group 3: report-v2 (same basename as group 1, different content)
    _write(tmp_path / "e" / "report.txt", "report-v2")
    _write(tmp_path / "f" / "report.txt", "report-v2")

    remover = DuplicateRemover(str(tmp_path))
    remover.find_duplicates()
    remover.handle_duplicates(testing=True)

    output = capsys.readouterr().out

    # Collect the positions at which each basename first appears in the output
    apple_pos = output.find("apple.txt")
    report_pos = output.find("report.txt")
    assert apple_pos != -1 and report_pos != -1, "Expected both basenames in output"

    # apple.txt comes before report.txt alphabetically
    assert apple_pos < report_pos, (
        "Expected apple.txt groups before report.txt groups; "
        f"apple_pos={apple_pos}, report_pos={report_pos}"
    )

    # Both report.txt groups must be contiguous — no apple.txt mention between
    # the first and last occurrence of report.txt
    first_report = output.find("report.txt")
    last_report = output.rfind("report.txt")
    apple_between = output.find("apple.txt", first_report, last_report)
    assert apple_between == -1, (
        "apple.txt appeared between two report.txt groups; "
        "same-basename groups are not adjacent"
    )


def test_handle_duplicates_alphabetical_order_single_basename_per_group(tmp_path, capsys):
    """Groups whose files all share the same basename sort alphabetically by that name."""
    for subdir in ["p", "q", "r", "s"]:
        (tmp_path / subdir).mkdir()

    _write(tmp_path / "p" / "zebra.dat", "z")
    _write(tmp_path / "q" / "zebra.dat", "z")

    _write(tmp_path / "r" / "aardvark.dat", "a")
    _write(tmp_path / "s" / "aardvark.dat", "a")

    remover = DuplicateRemover(str(tmp_path))
    remover.find_duplicates()
    remover.handle_duplicates(testing=True)

    output = capsys.readouterr().out
    assert output.find("aardvark.dat") < output.find("zebra.dat"), (
        "Groups should appear in alphabetical basename order"
    )
