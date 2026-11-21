"""``ds diff`` tests: side-by-side diff without an external ``diff`` binary."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.diff_color import CYAN, MAGENTA, RED, RESET, diff_rows, side_by_side

LEFT = ["same", "old line", "only left", "a  b", "tail"]
RIGHT = ["same", "new line", "a b", "added", "tail"]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_diff_rows_markers() -> None:
    assert diff_rows(LEFT, RIGHT) == [
        ("same", " ", "same"),
        ("old line", "|", "new line"),
        ("only left", "<", ""),
        ("a  b", " ", "a b"),
        ("", ">", "added"),
        ("tail", " ", "tail"),
    ]


def test_side_by_side_layout() -> None:
    assert side_by_side(LEFT, RIGHT, 23) == [
        "same         same",
        "old line   | new line",
        "only left  <",
        "a  b         a b",
        "           > added",
        "tail         tail",
    ]


def test_side_by_side_suppress_common() -> None:
    assert side_by_side(LEFT, RIGHT, 23, suppress_common=True) == [
        "old line   | new line",
        "only left  <",
        "           > added",
    ]


def test_side_by_side_colours_changed_characters() -> None:
    assert side_by_side(["abc"], ["abd"], 23, colour=True) == [
        f"ab{CYAN}c{RESET}        {MAGENTA}|{RESET} ab{RED}d{RESET}"
    ]


def test_diff_cli_two_files(runner: CliRunner, tmp_path: Path) -> None:
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("\n".join(LEFT) + "\n", encoding="utf-8")
    f2.write_text("\n".join(RIGHT) + "\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "diff", str(f1), str(f2), "-w", "23", "-s"],
                           catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "old line   | new line\nonly left  <\n           > added\n"


def test_diff_cli_literal_strings(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "diff", "x\\ny", "x\\nz", "-w", "13"],
                           catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "x       x\ny     | z\n"


def test_diff_cli_stdin_is_left(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "diff", "b", "-w", "13"], input="a\n",
                           catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "a     | b\n"


def test_diff_cli_requires_two_inputs(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "diff", "only"])
    assert result.exit_code != 0
