"""
Pytest coverage for simple CLI commands, aligned with dev_scripts/tests/t_basic.sh
where those cases apply to the Python port.

t_basic.sh references:
- join_by: pipe and positional args -> "1, 2, 3"
- iter: ds:iter "a" 3 -> "aaa"
- rev: printf a\\nb\\nc\\nd | ds:rev -> lines reversed (concatenated: dcba)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from scripts.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# --- t_basic.sh parity: join_by, iter, rev ---


def test_join_by_positional_args_matches_t_basic(runner: CliRunner) -> None:
    """echo 1 2 3 | ds:join_by ', ' and ds:join_by ', ' 1 2 3 -> 1, 2, 3"""
    result = runner.invoke(cli, [".", "join_by", ", ", "1", "2", "3"], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "1, 2, 3"


def test_join_by_stdin_matches_t_basic(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [".", "join_by", ", "],
        input="1 2 3\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output == "1, 2, 3"


def test_iter_matches_t_basic(runner: CliRunner) -> None:
    """ds:iter "a" 3 -> aaa"""
    result = runner.invoke(cli, [".", "iter", "a", "3"], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "aaa"


def test_iter_with_separator(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "iter", "a", "3", "-"], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "a-a-a"


def test_rev_matches_t_basic(runner: CliRunner) -> None:
    """printf "%s\\n" a b c d | ds:rev | tr -d '\\n' == dcba"""
    result = runner.invoke(
        cli,
        [".", "rev"],
        input="a\nb\nc\nd\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.replace("\n", "") == "dcba"


def test_join_by_too_few_args_fails(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "join_by", ", ", "only"], catch_exceptions=False)
    assert result.exit_code != 0


# --- insert, line, goog, jira (Python port; not in t_basic.sh) ---


def test_insert_at_line_number_stdout(tmp_path, runner: CliRunner) -> None:
    sink = tmp_path / "sink.txt"
    sink.write_text("one\ntwo\nthree\n", encoding="utf-8")
    # Insertion text via stdin (matches shell pipe case); avoid passing literal text as SOURCE
    # because cli resolves SOURCE as a path.
    result = runner.invoke(
        cli,
        [".", "insert", str(sink), "2", "", "f"],
        input="INSERT\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "INSERT" in result.output
    assert result.output.startswith("one\nINSERT\ntwo\n")


def test_insert_inplace(tmp_path, runner: CliRunner) -> None:
    sink = tmp_path / "sink.txt"
    sink.write_text("a\nb\n", encoding="utf-8")
    result = runner.invoke(
        cli,
        [".", "insert", str(sink), "1", "", "t"],
        input="0\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert sink.read_text(encoding="utf-8") == "0\na\nb\n"


def test_line_stdin_with_placeholder(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [".", "line", 'echo "{line}"'],
        input="x\ny\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "x" in result.output
    assert "y" in result.output


@patch("scripts.simple_commands.webbrowser.open")
def test_goog_builds_google_search_url(mock_open, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [".", "goog", "hello", "world"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "https://www.google.com/search?query=" in result.output
    mock_open.assert_called_once()


@patch("scripts.simple_commands.webbrowser.open")
def test_jira_browse_issue_url(mock_open, runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "jira", "acme", "PROJ-123"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "https://acme.atlassian.net/browse/PROJ-123" in result.output
    mock_open.assert_called_once()


@patch("scripts.simple_commands.webbrowser.open")
def test_jira_search_url(mock_open, runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "jira", "acme", "my query"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "https://acme.atlassian.net/search/" in result.output
    mock_open.assert_called_once()


def test_goog_requires_query(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "goog"], catch_exceptions=False)
    assert result.exit_code != 0
