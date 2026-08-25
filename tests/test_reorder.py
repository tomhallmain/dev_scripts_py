"""Tests for ``ds reo`` (parity with the original bash ``ds:reo`` cases).

Expected values are transcribed from ``dev_scripts/tests/t_reorder.sh`` and
``t_reorder_extended.sh``. Cases the shell built with ``seq``/``bc`` construct the same
input in Python; cases that piped through other unported commands assert the equivalent
selection directly.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli

TESTS_DIR = Path(__file__).resolve().parent
DATA = TESTS_DIR / "data"
COMMANDS = DATA / "commands"
SEPS_TEST_BASE = DATA / "seps_test_base"
COMPANY_CSV = DATA / "company_funding_data.csv"

# t_reorder.sh L12-15 / L34-37: the two datasets most cases run against.
LETTERS = "d c a b f\nf e c b a\nf e d c b\ne d c b a\n"
COLONS = "1:2:3:4:5\n5:4:3:2:1\n::6::\n:3::2:1\n"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _reo(runner: CliRunner, argv: list, **kwargs) -> str:
    result = runner.invoke(cli, [".", "reo", *argv], catch_exceptions=False, **kwargs)
    assert result.exit_code == 0, result.output
    return result.output.rstrip("\n")


def _write(tmp_path: Path, name: str, text: str) -> str:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


# --- indices, ranges, reverse, others ---------------------------------------


def test_base_row_case(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L16."""
    p = _write(tmp_path, "letters.txt", LETTERS)
    assert _reo(runner, [p, "2"]) == "f e c b a"


def test_base_column_case(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L22."""
    p = _write(tmp_path, "letters.txt", LETTERS)
    assert _reo(runner, [p, "a", "2"]) == "c\ne\ne\nd"


def test_compound_range_reorder_case(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L26: repeats and a descending range inside one argument."""
    p = _write(tmp_path, "letters.txt", LETTERS)
    assert _reo(runner, [p, "4,1", "5,3..1,4"]) == "a c d e b\nf a c d b"


def test_compound_range_row_selection(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L98-107: ``1,2,5..3`` keeps written order, not source order."""
    text = "\n".join(f"row{i}" for i in range(1, 6)) + "\n"
    p = _write(tmp_path, "rows.txt", text)
    out = _reo(runner, [p, "1,2,5..3"]).splitlines()
    assert out == ["row1", "row2", "row5", "row4", "row3"]


def test_single_char_descending_range(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L37-41."""
    p = _write(tmp_path, "chars.txt", "a\nb\nc\n")
    assert _reo(runner, [p, "3..1"]) == "c\nb\na"


def test_unicode_fields_reversed(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L46-49."""
    p = _write(tmp_path, "uni.csv", "α,β,γ\n")
    assert _reo(runner, [p, "a", "3..1"]) == "γ,β,α"


def test_mixed_data_types_column_reorder(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L89-93."""
    p = _write(tmp_path, "mixed.csv", "123,abc,456\n")
    assert _reo(runner, [p, "a", "2,1,3"]) == "abc,123,456"


def test_empty_fields_are_preserved(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L23-31: empty fields keep their positions."""
    p = _write(tmp_path, "empty.csv", "a,,c\n,b,\nc,,\n")
    assert _reo(runner, [p, "1..3"]) == "a,,c\n,b,\nc,,"


def test_wide_row_column_slice(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L12-21: slicing 100 of 1000 columns yields exactly 100 fields.

    The shell passed ``chunk_size``/``buffer_size`` here; those tune the awk implementation's
    memory use and do not change output, so only the parity part is asserted. The separator
    is given explicitly because inferring it on a very wide row is pathologically slow --
    see ``docs/test_coverage.md``.
    """
    p = _write(tmp_path, "wide.txt", " ".join(str(i) for i in range(1, 1001)) + "\n")
    out = _reo(runner, [p, "a", "1..100", "--field-sep", " "])
    assert len(out.split()) == 100
    assert out.split()[:3] == ["1", "2", "3"]


def test_out_of_range_index_prints_nothing(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L74-75."""
    p = _write(tmp_path, "letters.txt", LETTERS)
    assert _reo(runner, [p, "999"]) == ""


# --- idx numbering ----------------------------------------------------------


def test_index_numbering_single_cell(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L66-69."""
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, "3", "3", "--idx"]) == ":3\n3:6"


def test_index_numbering_descending_range(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L71-75."""
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, "4..3", "4..3", "--idx"]) == ":4:3\n4:2:\n3::6"


def test_index_numbering_full_reverse(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L77-83."""
    p = _write(tmp_path, "colons.txt", COLONS)
    expected = (
        ":5:4:3:2:1\n"
        "4:1:2::3:\n"
        "3:::6::\n"
        "2:1:2:3:4:5\n"
        "1:5:4:3:2:1"
    )
    assert _reo(runner, [p, "rev", "rev", "--idx"]) == expected


# --- searches and comparisons ----------------------------------------------


def test_exclusive_search_case(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L31: negated searches keep rows/columns where nothing matches."""
    p = _write(tmp_path, "letters.txt", LETTERS)
    assert _reo(runner, [p, "4!~b", "!~c"]) == "f b"


def test_exclusive_row_filter(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L60-62."""
    p = _write(tmp_path, "words.txt", "begin\nstart middle end\n")
    assert _reo(runner, [p, "!~begin"]) == "start middle end"


def test_scoped_field_search(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L68-70: ``2~5`` tests field 2 only."""
    p = _write(tmp_path, "nums.csv", "1,2,3\n4,5,6\n")
    assert _reo(runner, [p, "2~5", "a"]) == "4,5,6"


def test_frame_pattern_column_selection(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L53-55."""
    p = _write(tmp_path, "digits.txt", "1 2 3 4 5\n")
    assert _reo(runner, [p, "a", "[1~^[1-5]$"]).split() == ["1", "2", "3", "4", "5"]


def test_malformed_frame_reports_no_matches(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder_extended.sh L78-79."""
    p = _write(tmp_path, "letters.txt", LETTERS)
    assert _reo(runner, [p, "[invalid"]) == "No matches found"


def test_comparison_ignores_non_numeric_fields(runner: CliRunner, tmp_path: Path) -> None:
    """A comparison only considers numeric fields, so text columns never satisfy ``>``."""
    p = _write(tmp_path, "letters.txt", LETTERS)
    assert _reo(runner, [p, ">4"]) == "No matches found"


# --- field separation off ---------------------------------------------------


def test_cols_off_numeric_comparison(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L40-41: ``off`` prints whole lines but still filters on fields."""
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, ">5", "off"]) == "::6::"


def test_cols_off_search(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L43-44."""
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, "~6", "off"]) == "::6::"


def test_cols_off_len_measures_whole_line(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L81: with ``off``, ``len()`` measures the line, not a field."""
    lines = [ln.rstrip("\n") for ln in COMMANDS.open(encoding="utf-8") if "ds:" in ln]
    p = _write(tmp_path, "commands.txt", "\n".join(lines) + "\n")
    out = _reo(runner, [p, "len()>130", "off"]).splitlines()
    assert out == [ln for ln in lines if len(ln) > 130]
    assert out, "fixture should contain at least one line longer than 130 characters"


# --- len() ------------------------------------------------------------------


def test_len_of_scoped_field(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L87-92: ``len(4)`` measures field 4 of each row."""
    lines = [ln.rstrip("\n") for ln in COMMANDS.open(encoding="utf-8") if "ds:" in ln]
    p = _write(tmp_path, "commands.txt", "\n".join(lines) + "\n")
    assert _reo(runner, [p, "len(4)>46", "2"]) == "ds:dups\nds:insert\nds:jira\nds:path_elements"


# --- anchored ranges --------------------------------------------------------


def test_anchor_range(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L46-51."""
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, "6##2", "3##"]) == "6::\n3:2:1\n3:4:5"


def test_anchor_range_regex_form(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L53-54: ``/a/../b/`` is equivalent to ``a##b``."""
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, "/6/../2/", "/3/.."]) == "6::\n3:2:1\n3:4:5"


def test_anchor_range_end_only(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L56-61."""
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, "6##2", "##3"]) == "::6\n5:4:3\n1:2:3"


def test_anchor_range_end_only_regex_form(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L62-63."""
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, "/6/../2/", "../3/"]) == "::6\n5:4:3\n1:2:3"


# --- uniq -------------------------------------------------------------------


def test_uniq_row_case(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L108-113."""
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, "len(1)>0,len(1)<2", "3", "--uniq"]) == "3\n3\n6"


def test_uniq_column_case(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L104-106.

    The trailing separator is expected: under ``--uniq`` the duplicates removed from the
    second token collapse into one empty column.
    """
    p = _write(tmp_path, "colons.txt", COLONS)
    assert _reo(runner, [p, "1", "len()>0,len()<2", "--uniq"]) == "1:2:3:4:5:"


# --- expressions, booleans, others/reverse ---------------------------------


def test_row_expression_and_scoped_column_comparison(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L116-142, with the ``seq``/``bc`` input rebuilt in Python."""
    def bc_mod(value: int, modulus: int) -> int:
        remainder = abs(value) % modulus
        return -remainder if value < 0 else remainder

    text = "\n".join(
        f"{i} {-1 * i} " + ("test" if bc_mod(i, 5) == 0 else "nah")
        for i in range(-16, 17)
    ) + "\n"
    p = _write(tmp_path, "seq.txt", text)

    expected = "\n".join(
        [f"{-i} " + ("test" if i % 5 == 0 else "nah") for i in range(1, 17)]
        + [f"{-i} test" for i in (-15, -10, -5, 0, 5, 10, 15)]
    )
    assert _reo(runner, [p, "2<0, 3~test", "31!=14"]) == expected


def test_others_and_reverse_with_frame(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L167-173.

    The leading empty column is expected: ``>4`` matches no numeric field, and a column
    token that selects nothing still occupies one column.
    """
    p = _write(tmp_path, "letters.txt", LETTERS)
    expected = (
        " f b a c d d a\n"
        " f b a c d d a\n"
        " a b c e f f c\n"
        " b c d e f f d\n"
        " a b c d e e c"
    )
    assert _reo(runner, [p, "1,1, others, [a", ">4, rev, [f~d"]) == expected


def test_others_and_reverse_without_spaces(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L175-181: the same argument without spaces around the commas."""
    p = _write(tmp_path, "letters.txt", LETTERS)
    expected = (
        " f b a c d d a\n"
        " f b a c d d a\n"
        " a b c e f f c\n"
        " b c d e f f d\n"
        " a b c d e e c"
    )
    assert _reo(runner, [p, "1,1,others,[a", ">4,rev,[f~d"]) == expected


def test_combined_and_or_logic(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L181-184: ``&&`` conjoins, and ``||`` binds tighter."""
    p = _write(tmp_path, "letters.txt", LETTERS)
    out = _reo(runner, [p, "[a~c && 5~a", "[f~d || [e~a && NF>3"])
    assert out.replace(" ", "") == "a\na"


# ``seps_test_base`` uses a three-character separator. The shell inferred it via
# ``ds:extractfs``; the Python SeparatorInference does not yet detect multi-character
# separators, so these cases pass it explicitly rather than exercising that unrelated gap.
SEPS_FS = ["--field-sep", "&%#"]


def test_conjunction_with_arithmetic_filter(runner: CliRunner) -> None:
    """t_reorder.sh L186-189: ``>100&&%7`` needs both conditions on one row."""
    out = _reo(runner, [str(SEPS_TEST_BASE), ">100&&%7", "%7", *SEPS_FS])
    assert out == "7&%#2\n420&%#1"


def test_frame_comparison_matches_frame_search(runner: CliRunner) -> None:
    """t_reorder.sh L191-192: ``5[2!~2`` and ``5[2!=2 && 5[2!=23`` select the same rows."""
    search = _reo(runner, [str(SEPS_TEST_BASE), "5[2!~2", "a", *SEPS_FS])
    comparison = _reo(runner, [str(SEPS_TEST_BASE), "5[2!=2 && 5[2!=23", "a", *SEPS_FS])
    assert [ln for ln in search.splitlines() if ln.startswith("1")] == [
        ln for ln in comparison.splitlines() if ln.startswith("1")
    ]


# --- README cases -----------------------------------------------------------


def test_readme_case_numeric_filter_and_header_frames(runner: CliRunner) -> None:
    """t_reorder.sh L195-199."""
    expected = (
        "company,category,city,raisedAmt,raisedCurrency,round\n"
        "Facebook,web,Palo Alto,300000000,USD,c\n"
        "ZeniMax,web,Rockville,300000000,USD,a"
    )
    assert _reo(runner, [str(COMPANY_CSV), "1, >200000000", "[^c, [^r"]) == expected


def _company_head(tmp_path: Path) -> str:
    rows = COMPANY_CSV.read_text(encoding="utf-8").splitlines()[:5]
    return _write(tmp_path, "company_head.csv", "\n".join(rows) + "\n")


def test_readme_case_frame_row_and_columns(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L201-205."""
    p = _company_head(tmp_path)
    assert _reo(runner, [p, "[lifelock", "[round,[funded"]) == "b,1-May-07\na,1-Oct-06\nc,1-Jan-08"


def test_readme_case_conjunction_and_range(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L207-213."""
    p = _company_head(tmp_path)
    expected = (
        "LifeLock,1-Jan-08\n"
        "MyCityFaces,1-Jan-08\n"
        "LifeLock,1-Oct-06\n"
        "LifeLock,1-May-07\n"
        "company,fundedDate"
    )
    assert _reo(runner, [p, "~Jan-08 && NR<6, 3..1", "[company,~Jan-08"]) == expected


def test_extended_logic_with_reverse(runner: CliRunner, tmp_path: Path) -> None:
    """t_reorder.sh L215-224."""
    p = _company_head(tmp_path)
    expected = (
        "b,USD,6850000,1-May-07,AZ,Tempe,web,,LifeLock,lifelock\n"
        "a,USD,6000000,1-Oct-06,AZ,Tempe,web,,LifeLock,lifelock\n"
        "c,USD,25000000,1-Jan-08,AZ,Tempe,web,,LifeLock,lifelock\n"
        "seed,USD,50000,1-Jan-08,AZ,Scottsdale,web,7,MyCityFaces,mycityfaces\n"
        "c,USD,25000000,1-Jan-08,AZ,Tempe,web,,LifeLock,lifelock\n"
        "a,USD,6000000,1-Oct-06,AZ,Tempe,web,,LifeLock,lifelock\n"
        "b,USD,6850000,1-May-07,AZ,Tempe,web,,LifeLock,lifelock\n"
        "round,raisedCurrency,raisedAmt,fundedDate,state,city,category,numEmps,company,permalink"
    )
    assert _reo(runner, [p, "!~permalink && !~mycity,rev", "rev"]) == expected


# --- case sensitivity -------------------------------------------------------


def test_cased_and_ignore_case_suffix(runner: CliRunner, tmp_path: Path) -> None:
    """Searches ignore case by default; ``--cased`` enforces it and ``/i`` opts back out."""
    p = _write(tmp_path, "cased.txt", "Plant Country\nflower ITALY\ntree italy\n")
    assert _reo(runner, [p, "~italy"]) == "flower ITALY\ntree italy"
    assert _reo(runner, [p, "~italy", "a", "--cased"]) == "tree italy"
    assert _reo(runner, [p, "~italy/i", "a", "--cased"]) == "flower ITALY\ntree italy"
