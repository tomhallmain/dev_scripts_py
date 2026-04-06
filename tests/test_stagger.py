from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _strip_trailing_spaces(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).rstrip("\n")


def test_stagger_basic_format_matches_shell_contract(runner: CliRunner, tmp_path: Path) -> None:
    p = tmp_path / "stagger_basic.csv"
    p.write_text(
        "short,medium value,very long value that needs wrapping\n1,2,3\na,b,c with some extra text\n",
        encoding="utf-8",
    )
    r = runner.invoke(cli, [".", "stagger", str(p), "-F", ",", "--tty-size", "120"], catch_exceptions=False)
    assert r.exit_code == 0
    got = _strip_trailing_spaces(r.output)
    expected = _strip_trailing_spaces(
        "short\n     medium value\n          very long value that needs wrapping\n\n1\n     2\n          3\n\na\n     b\n          c with some extra text"
    )
    assert got == expected


def test_stagger_compact_and_wrap_char_mode(runner: CliRunner) -> None:
    r = runner.invoke(
        cli,
        [".", "stagger", "-F", ",", "--style", "compact", "--max-width", "10", "--wrap", "char"],
        input="abcdefghijklmnopqrstuvwxyz,ABCDEFGHIJKLMNOPQRSTUVWXYZ\n",
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    out = _strip_trailing_spaces(r.output)
    assert "abcdefghij" in out
    assert "↪ klmnopqrst" in out or "↪ klmnopqrs" in out
    assert "ABCDEFG" in out


def test_stagger_numbers_flag(runner: CliRunner) -> None:
    r = runner.invoke(
        cli,
        [".", "stagger", "-F", ",", "--numbers"],
        input="a,b\nc,d\n",
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    out = _strip_trailing_spaces(r.output)
    assert out.splitlines()[0].startswith("1")
    assert any(line.startswith("2") for line in out.splitlines())
