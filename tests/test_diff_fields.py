"""``ds diff_fields`` tests; the reference cases follow ``dev_scripts/tests/t_diff_fields.sh``."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.diff_fields import DiffFields, DiffFieldsError, extract_value, truncate_value

LEFT = ["a 1 2 3 4", "b 3 4 2 1", "c 22 # , 2"]
RIGHT = ["a 1 5 60 5", "b 3 7 2 7", "c 22 # , 2"]
LABELS = dict(left_label="/tmp/ds_df_tests1", right_label="/tmp/ds_df_tests2")
LIST_HEADER = "ROW FIELD /tmp/ds_df_tests1 /tmp/ds_df_tests2 DIFF"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _run(*args, **kwargs) -> str:
    return "\n".join(DiffFields(*args, **kwargs).run(LEFT, RIGHT))


def test_diff_fields_base_case() -> None:
    assert _run() == " 0 -3 -57 -1\n 0 -3 0 -6\n 0   0"


def test_diff_fields_percent_diff_list() -> None:
    assert _run("%", "1", diff_list="on", **LABELS) == (
        "a 0 1.5 19 0.25\nb 0 0.75 0 6\nc 0   0\n\n\n\n" + LIST_HEADER + "\n"
        "a 4 3 60 19\nb 5 1 7 6\na 3 2 5 1.5\nb 3 4 7 0.75\na 5 4 5 0.25"
    )


def test_diff_fields_divide_diff_list_only() -> None:
    assert _run("/", "1", diff_list="only", **LABELS) == (
        LIST_HEADER + "\n"
        "a 5 4 5 0.8\nb 3 4 7 0.571429\na 3 2 5 0.4\nb 5 1 7 0.142857\na 4 3 60 0.05"
    )


def test_diff_fields_percent_diff_list_header() -> None:
    assert _run("%", header=True, diff_list="on", **LABELS) == (
        "a 1 5 60 5\n 0 0.75 0 6\n 0   0\n\n\n\n" + LIST_HEADER + "\n2 5 1 7 6\n2 3 4 7 0.75"
    )


def test_diff_fields_multiply_excluded_fields_header() -> None:
    assert _run("*", "1,3", header=True) == "a 1 5 60 5\nb 9 7 4 7\nc 484 #  4"


def test_diff_fields_precision() -> None:
    assert _run("-", "1", precision=2) == (
        "a 0.00 -3.00 -57.00 -1.00\nb 0.00 -3.00 0.00 -6.00\nc 0.00   0.00"
    )


# The original's MAD/RMSD/stats cases stop at field 4 because their loop runs over
# 1..(number of counted fields); field 5 has differences too (1, 6, 0) and is reported here.


def test_diff_fields_mad() -> None:
    assert _run("m", "1") == (
        "Field Statistics:\n---------------\n"
        "MAD [2]: 0\nMAD [3]: 3\nMAD [4]: 28.5\nMAD [5]: 2.33333"
    )


def test_diff_fields_rmsd() -> None:
    assert _run("r", "1", precision=6) == (
        "Field Statistics:\n---------------\n"
        "RMSD [2]: 0.000000\nRMSD [3]: 3.000000\nRMSD [4]: 40.305087\nRMSD [5]: 3.511885"
    )


def test_diff_fields_stats() -> None:
    out = _run("s", "1", precision=6).split("\n")
    assert out[:2] == ["Field Statistics:", "---------------"]
    assert out[12:17] == [
        "Stats [4]:", "  Min: 0.000000", "  Max: 57.000000", "  Mean: 28.500000",
        "  StdDev: 40.305087",
    ]
    assert out[17:] == [
        "Stats [5]:", "  Min: 0.000000", "  Max: 6.000000", "  Mean: 2.333333",
        "  StdDev: 3.214550",
    ]


def test_diff_fields_binary() -> None:
    assert _run("b", "1") == "a 0 1 1 1\nb 0 1 0 1\nc 0 0 0 0"


def test_extract_and_truncate_values() -> None:
    assert extract_value("1,234") == 1234.0
    assert extract_value("$5") is None
    assert extract_value("12abc") is None
    assert truncate_value(0.1234567) == 0.123457


def test_diff_fields_invalid_exclude_fields() -> None:
    with pytest.raises(DiffFieldsError):
        DiffFields("-", "x")


def test_diff_fields_cli_two_files(runner: CliRunner, tmp_path: Path) -> None:
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("\n".join(LEFT) + "\n", encoding="utf-8")
    f2.write_text("\n".join(RIGHT) + "\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "diff_fields", str(f1), str(f2), "/", "1",
                                 "--diff-list", "only"], catch_exceptions=False)
    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert lines[0] == f"ROW FIELD {f1} {f2} DIFF"
    assert lines[1] == "a 5 4 5 0.8"


def test_diff_fields_cli_stdin_second(runner: CliRunner, tmp_path: Path) -> None:
    f1 = tmp_path / "a.txt"
    f1.write_text("x 1 2\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "df", str(f1), "+"], input="x 3 4\n",
                           catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == " 4 6\n"
