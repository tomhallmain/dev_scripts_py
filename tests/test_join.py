"""Tests for ``ds join`` (parity with the original bash ``ds:join`` cases from the README)."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli

TESTS_DIR = Path(__file__).resolve().parent
DATA = TESTS_DIR / "data"
TMP_JOIN = DATA / "tmp_join"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_join_readme_basic_cases(runner: CliRunner) -> None:
    """README single-keyset inner join, by field index and by generated field name."""
    expected = "a b c d b c\n1 2 3 4 3 2\n"
    stdin = "a b c d\n1 3 2 4\n"

    r = runner.invoke(
        cli,
        [".", "join", str(TMP_JOIN), "--join=inner", "--k1=1,4"],
        input=stdin,
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected

    r = runner.invoke(
        cli,
        [".", "join", str(TMP_JOIN), "--join=inner", "--k1=a,d"],
        input=stdin,
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected


def test_join_readme_multi_keyset_cases(runner: CliRunner) -> None:
    """README multi-keyset right join, by field index and by generated field name."""
    expected = "a c b d\n1 2 3 4\n"
    stdin = "a b c d\n1 3 2 4\n"

    r = runner.invoke(
        cli,
        [".", "join", str(TMP_JOIN), "--join=right", "--k1=1,2,3,4", "--k2=1,3,2,4"],
        input=stdin,
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected

    r = runner.invoke(
        cli,
        [".", "join", str(TMP_JOIN), "--join=right", "--k1=a,b,c,d", "--k2=a,c,b,d"],
        input=stdin,
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected


def test_join_readme_merge_case(runner: CliRunner) -> None:
    """README outer join with ``--merge``."""
    expected = "a b c d\n1 3 2 4\n1 2 3 4\n"
    stdin = "a b c d\n1 3 2 4\n"

    r = runner.invoke(
        cli,
        [".", "join", str(TMP_JOIN), "--join=outer", "--merge"],
        input=stdin,
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected


def test_join_merge_field_max_null_off(runner: CliRunner) -> None:
    """Outer join, merged, with a merge-field cap and null placeholders turned off."""
    expected = "a b c d d\n1 3 2  4\n1 2 3 4 \n"
    stdin = "a b c d\n1 3 2 4\n"

    r = runner.invoke(
        cli,
        [".", "join", str(TMP_JOIN), "--join=outer", "--merge", "--max-merge-fields=3", "--null-off"],
        input=stdin,
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected


def test_join_extra_unmatched_right_join(runner: CliRunner, tmp_path: Path) -> None:
    """Outer join on two real files (no stdin), including unmatched rows on both sides."""
    tmp1 = tmp_path / "join1"
    tmp1.write_text("a 1\na 2\nb 2\nc 1\nb 1", encoding="utf-8")
    tmp2 = tmp_path / "join2"
    tmp2.write_text("a 1\na 2\na 3\na 4\na 3", encoding="utf-8")
    expected = (
        "a 1 1\n"
        "a 2 2\n"
        "a <NULL> 3\n"
        "a <NULL> 4\n"
        "a <NULL> 3\n"
        "b 2 <NULL>\n"
        "b 1 <NULL>\n"
        "c 1 <NULL>\n"
    )

    r = runner.invoke(
        cli,
        [".", "join", str(tmp1), str(tmp2), "--join=outer", "--k1=1"],
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected


def test_join_standard_join_case(runner: CliRunner, tmp_path: Path) -> None:
    """Same inputs as the unmatched-right-join case, with ``--standard_join``.

    ``--standard_join`` produces the full cross product for matched keys (file1 has two ``a``
    rows, file2 has five, so ten paired rows), then the unmatched file1 rows in sorted
    compound-key order.
    """
    tmp1 = tmp_path / "join1"
    tmp1.write_text("a 1\na 2\nb 2\nc 1\nb 1", encoding="utf-8")
    tmp2 = tmp_path / "join2"
    tmp2.write_text("a 1\na 2\na 3\na 4\na 3", encoding="utf-8")
    expected = (
        "a 1 1\n"
        "a 2 1\n"
        "a 1 2\n"
        "a 2 2\n"
        "a 1 3\n"
        "a 2 3\n"
        "a 1 4\n"
        "a 2 4\n"
        "a 1 3\n"
        "a 2 3\n"
        "b 2 <NULL>\n"
        "b 1 <NULL>\n"
        "c 1 <NULL>\n"
    )

    r = runner.invoke(
        cli,
        [".", "join", str(tmp1), str(tmp2), "--join=outer", "--k1=1", "--standard_join"],
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected
