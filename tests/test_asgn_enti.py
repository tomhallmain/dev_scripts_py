"""``ds asgn`` and ``ds enti`` tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.assignments import assignment_lines
from scripts.cli import cli
from scripts.separated_entities import TextEntities


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# --- asgn ---


def test_assignment_lines_matches_assignments_and_numbers_lines() -> None:
    lines = ["x = 1\n", "no assign\n", "arr[0]=5\n", "if a == b\n", "a =\n"]
    assert list(assignment_lines(lines)) == ["1:x = 1", "3:arr[0]=5", "4:if a == b"]


def test_asgn_cli_file(runner: CliRunner, tmp_path: Path) -> None:
    p = tmp_path / "conf.sh"
    p.write_text("# comment\nNAME=value\necho hi\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "asgn", str(p)], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "2:NAME=value\n"


def test_asgn_cli_stdin(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "asgn"], input="a = 1\nb\n", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "1:a = 1\n"


def test_asgn_cli_missing_file(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(cli, [".", "asgn", str(tmp_path / "nope")])
    assert result.exit_code != 0
    assert "not a file" in result.output


# --- enti ---


def test_entities_default_whitespace_ascending() -> None:
    te = TextEntities()
    te.process_lines(["a b a\n", "  b c\n", "\n"])
    assert te.entity_lines() == ["1 c", "2 a", "2 b"]


def test_entities_min_is_inclusive_and_descending_order() -> None:
    te = TextEntities(min_count=2, descending=True)
    te.process_lines(["a b a\n", "b c\n"])
    assert te.entity_lines() == ["2 b", "2 a"]


def test_entities_single_char_separator_keeps_empty_entities() -> None:
    te = TextEntities(separator=",")
    te.process_lines(["a,,b\n", "a\n"])
    assert te.entity_lines() == ["1 ", "1 b", "2 a"]


def test_entities_regex_separator() -> None:
    te = TextEntities(separator=", *")
    te.process_lines(["a, b,c\n"])
    assert te.entity_lines() == ["1 a", "1 b", "1 c"]


def test_entities_non_positive_min_means_one() -> None:
    assert TextEntities(min_count=0).min_count == 1


def test_enti_cli_stdin_with_options(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "enti", "--min", "2", "--order", "d"],
                           input="x y x\ny z\n", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "2 y\n2 x\n"


def test_enti_cli_file(runner: CliRunner, tmp_path: Path) -> None:
    p = tmp_path / "e.txt"
    p.write_text("q,r\nq\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "enti", str(p), "--sep", ","], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "1 r\n2 q\n"
