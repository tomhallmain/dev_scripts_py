from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_test_cmd_matches_string_true(runner: CliRunner) -> None:
    r = runner.invoke(cli, [".", "test", "t(rue)?", "true"], catch_exceptions=False)
    assert r.exit_code == 0
    assert r.output == ""


def test_test_cmd_matches_string_false(runner: CliRunner) -> None:
    r = runner.invoke(cli, [".", "test", "^q$", "not-q"], catch_exceptions=False)
    assert r.exit_code == 1


def test_test_cmd_stdin_precedence(runner: CliRunner) -> None:
    r = runner.invoke(cli, [".", "test", "foo", "bar"], input="foo\n", catch_exceptions=False)
    assert r.exit_code == 0


def test_test_cmd_file_mode(runner: CliRunner, tmp_path: Path) -> None:
    p = tmp_path / "a.txt"
    p.write_text("abc\n", encoding="utf-8")
    r = runner.invoke(cli, [".", "test", "abc", str(p), "t"], catch_exceptions=False)
    assert r.exit_code == 0
