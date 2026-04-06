"""Tests for ``ds matches`` (shell ``ds:matches`` parity for key cases)."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli

TESTS_DIR = Path(__file__).resolve().parent
DATA = TESTS_DIR / "data"
JNF1 = DATA / "infer_join_fields_test1.csv"
JNF2 = DATA / "infer_join_fields_test2.csv"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_matches_no_matches_distinct_keys(runner: CliRunner) -> None:
    """``-v k1=2 -v k2=2`` → no overlapping keys between columns."""
    r = runner.invoke(
        cli,
        [
            ".",
            "matches",
            str(JNF1),
            str(JNF2),
            "--key1",
            "2",
            "--key2",
            "2",
        ],
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output.strip() == "NO MATCHES FOUND"


def test_matches_count_lines_key1(runner: CliRunner) -> None:
    """``-v k=1``: line count matches shell ``grep -c`` on output (167 rows)."""
    r = runner.invoke(
        cli,
        [".", "matches", str(JNF1), str(JNF2), "-k", "1"],
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert len(r.output.splitlines()) == 167


def test_matches_verbose_two_extra_lines(runner: CliRunner) -> None:
    """``verbose=1`` adds banner + blank line before rows (169 lines)."""
    r = runner.invoke(
        cli,
        [".", "matches", str(JNF1), str(JNF2), "-k", "1", "--verbose"],
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert len(r.output.splitlines()) == 169


def test_matches_stdin_as_second_input(runner: CliRunner) -> None:
    """One file path + second dataset on stdin (``PAIR_CHAIN_OR_STDIN_SECOND`` pipe branch)."""
    body = JNF2.read_text(encoding="utf-8")
    r = runner.invoke(
        cli,
        [".", "matches", str(JNF1), "-k", "1"],
        input=body,
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert len(r.output.splitlines()) == 167
