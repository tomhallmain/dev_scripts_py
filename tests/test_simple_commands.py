"""
Pytest coverage for simple CLI commands, aligned with dev_scripts/tests/t_basic.sh
where those cases apply to the Python port.

t_basic.sh references:
- join_by: pipe and positional args -> "1, 2, 3"
- iter: ds:iter "a" 3 -> "aaa"
- rev: printf a\\nb\\nc\\nd | ds:rev -> lines reversed (concatenated: dcba)
- unicode: ds:unicode "cats😼😻" / pipe / hex (\\U… and %… forms)
- embrace: ds:embrace 'test' / pipe → ``{test}``
- cp: ``data | ds . cp`` → clipboard (UTF-8)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.simple_commands import embrace_cmd
from scripts.unicode import format_unicode


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


# --- t_basic.sh parity: unicode ---

# echo -n to avoid extra newline in string; shell strips one trailing newline from $(...)
CATS_WITH_MOJIS = "cats\U0001f63c\U0001f63b"

# t_basic.sh: ds:unicode / ds:unicode … hex
T_BASIC_UNICODE_CATS_CODEPOINT = r"\U63\U61\U74\U73\U1F63C\U1F63B"
T_BASIC_UNICODE_CATS_HEX = "%63%61%74%73%F09F98BC%F09F98BB"


def test_format_unicode_cats_codepoint_matches_t_basic() -> None:
    assert format_unicode(CATS_WITH_MOJIS, "codepoint") == T_BASIC_UNICODE_CATS_CODEPOINT


def test_format_unicode_cats_hex_matches_t_basic() -> None:
    assert format_unicode(CATS_WITH_MOJIS, "hex") == T_BASIC_UNICODE_CATS_HEX


def test_format_unicode_hex_and_octet_match_for_utf8_blobs() -> None:
    """Shell uses the same branch for hex and octet; per-char UTF-8 % blobs match."""
    assert format_unicode(CATS_WITH_MOJIS, "octet") == format_unicode(CATS_WITH_MOJIS, "hex")


def test_unicode_cli_positional_codepoint_matches_t_basic(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [".", "unicode", CATS_WITH_MOJIS],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == T_BASIC_UNICODE_CATS_CODEPOINT


def test_unicode_cli_stdin_codepoint_matches_t_basic(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [".", "unicode"],
        input=CATS_WITH_MOJIS + "\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == T_BASIC_UNICODE_CATS_CODEPOINT


def test_unicode_cli_positional_hex_matches_t_basic(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [".", "unicode", CATS_WITH_MOJIS, "hex"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == T_BASIC_UNICODE_CATS_HEX


def test_unicode_cli_stdin_hex_single_arg(runner: CliRunner) -> None:
    """``echo … | ds:unicode hex`` → one argument selects mode, body from stdin."""
    result = runner.invoke(
        cli,
        [".", "unicode", "hex"],
        input=CATS_WITH_MOJIS + "\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == T_BASIC_UNICODE_CATS_HEX


def test_unicode_cli_stdin_explicit_codepoint(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [".", "unicode", "codepoint"],
        input=CATS_WITH_MOJIS + "\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == T_BASIC_UNICODE_CATS_CODEPOINT


def test_format_unicode_ascii_single_char() -> None:
    assert format_unicode("a", "codepoint") == r"\U61"


def test_format_unicode_empty() -> None:
    assert format_unicode("", "codepoint") == ""
    assert format_unicode("", "hex") == ""


def test_unicode_cli_invalid_conversion_exits(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [".", "unicode", "x", "nope"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0


# --- t_basic.sh parity: embrace ---


def test_embrace_cmd_tty_matches_t_basic() -> None:
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        embrace_cmd(("test",), None)
    assert buf.getvalue().rstrip("\n") == "{test}"


@patch("click.testing._NamedTextIOWrapper.isatty", return_value=True)
def test_embrace_positional_matches_t_basic(_mock_isatty: object, runner: CliRunner) -> None:
    """CliRunner stdin is non-tty; real TTY uses string form — fake isatty for parity."""
    result = runner.invoke(cli, [".", "embrace", "test"], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == "{test}"


def test_embrace_stdin_matches_t_basic(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "embrace"], input="test\n", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == "{test}"


def test_embrace_pipe_custom_left_right(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [".", "embrace", "(", ")"],
        input="hi\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == "(hi)"


@patch("click.testing._NamedTextIOWrapper.isatty", return_value=True)
def test_embrace_tty_custom_left_right(_mock_isatty: object, runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "embrace", "x", "[", "]"], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == "[x]"


def test_embrace_multiline_pipe_concatenates_wrapped_lines(runner: CliRunner) -> None:
    """Awk prints each line wrapped with no separator between records."""
    result = runner.invoke(cli, [".", "embrace"], input="a\nb\n", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.rstrip("\n") == "{a}{b}"


# --- ds:cp (clipboard; shell uses ``LC_CTYPE=UTF-8 pbcopy`` on macOS) ---


@patch("scripts.clipboard_copy.copy_utf8_text_to_clipboard")
def test_cp_stdin_passes_full_text_to_clipboard(
    mock_copy: object, runner: CliRunner
) -> None:
    result = runner.invoke(cli, [".", "cp"], input="line1\nline2\n", catch_exceptions=False)
    assert result.exit_code == 0
    mock_copy.assert_called_once_with("line1\nline2\n")


@patch("scripts.clipboard_copy.copy_utf8_text_to_clipboard")
def test_cp_empty_stdin(mock_copy: object, runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "cp"], input="", catch_exceptions=False)
    assert result.exit_code == 0
    mock_copy.assert_called_once_with("")


@patch("scripts.clipboard_copy.copy_utf8_text_to_clipboard")
def test_cp_preserves_utf8(mock_copy: object, runner: CliRunner) -> None:
    text = "café\n日本\n"
    result = runner.invoke(cli, [".", "cp"], input=text, catch_exceptions=False)
    assert result.exit_code == 0
    mock_copy.assert_called_once_with(text)


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
