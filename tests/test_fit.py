"""``ds fit`` tests; the reference cases follow ``dev_scripts/tests/t_fit.sh``."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.field_rows import read_rows, split_fields
from scripts.fit_columns import FitColumns

DATA = Path(__file__).resolve().parent / "data"

TAXABLES_EXPECTED = """\
Index  Item                              Cost   Tax  Total
    1  Fruit of the Loom Girl's Socks    7.97  0.60   8.57
    2  Rawlings Little League Baseball   2.97  0.22   3.19
    3  Secret Antiperspirant             1.29  0.10   1.39
    4  Deadpool DVD                     14.96  1.12  16.08
    5  Maxwell House Coffee 28 oz        7.28  0.55   7.83
    6  Banana Boat Sunscreen, 8 oz       6.68  0.50   7.18
    7  Wrench Set, 18 pieces            10.00  0.75  10.75
    8  M and M, 42 oz                    8.98  0.67   9.65
    9  Bertoli Alfredo Sauce             2.12  0.16   2.28"""


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_fit_pipe_case_aligns_all_lines(runner: CliRunner) -> None:
    """t_fit 'pipe case': every fitted line has the same length."""
    result = runner.invoke(cli, [".", "fit"], input="t 1\nte 2\ntes 3\ntest 4\n",
                           catch_exceptions=False)
    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert len(lines) == 4
    assert len({len(line) for line in lines}) == 1


def test_fit_base_case_addresses(runner: CliRunner) -> None:
    """t_fit 'base case': row 7, field 4 of the fitted output is 'Desert City'."""
    result = runner.invoke(cli, [".", "fit", str(DATA / "addresses.csv")],
                           catch_exceptions=False)
    assert result.exit_code == 0
    row7 = result.output.splitlines()[6]
    assert re.split(r" {2,}", row7)[3] == "Desert City"


def test_fit_spaced_quoted_field_case(runner: CliRunner) -> None:
    """t_fit 'spaced quoted field case': quoted CSV fields with commas, decimals aligned."""
    result = runner.invoke(cli, [".", "fit", str(DATA / "taxables.csv")],
                           catch_exceptions=False)
    assert result.exit_code == 0
    assert "\n".join(result.output.splitlines()[:10]) == TAXABLES_EXPECTED


def test_fit_stdin_matches_file(runner: CliRunner) -> None:
    text = "name,count\nalpha,3\nb,12\n"
    result = runner.invoke(cli, [".", "fit"], input=text, catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "name   count\nalpha      3\nb         12\n"


def test_fit_buffer_char(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "fit", "--buffer-char", "|"], input="a 1\nbb 22\n",
                           catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "a |  1\nbb| 22\n"


def test_fit_has_no_stub_banner(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "fit"], input="a b\n", catch_exceptions=False)
    assert "stub" not in result.output


def test_split_fields_whitespace_runs() -> None:
    assert split_fields("a  b   c", " ") == ["a", "b", "c"]
    assert split_fields("a,,b", ",") == ["a", "", "b"]


def test_read_rows_csv_quoted(tmp_path: Path) -> None:
    p = tmp_path / "q.csv"
    p.write_text('x, "a, b", y\n', encoding="utf-8")
    assert read_rows(str(p), ",") == [["x", "a, b", "y"]]


def test_fit_columns_right_aligns_numbers() -> None:
    out = FitColumns().fit_rows([["x", "1"], ["yy", "100"]])
    assert out == ["x     1", "yy  100"]
