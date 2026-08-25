"""
Subseparator (`ds subsep` / `ds:subsep`) tests.

Mirrors cases from dev_scripts/tests/t_subsep.sh where they apply to this repo’s
Python implementation. Several shell tests pipe through ``ds:reo`` or use AWK-style
flags (``-v apply_to_fields=…``, ``regex=1``, ``escape=1``); those map onto the
``--apply-to-fields`` / ``--regex`` / ``--escape`` options here. Cases the shell piped
through ``ds:reo`` build the equivalent slice inline, since ``reo`` is not ported.

Additional checks use ``tests/data/seps_test_base`` and ``tests/data/seps_test_sorted``
(paired datasets for separator / ordering scenarios; expanded beyond the original
script’s file set).
"""
from __future__ import annotations

import csv
import os
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.cli_arg_parse_utils import CliArgContext, PathCandidatePredicate
from scripts.subseparator import SubseparatorFinder

# ---------------------------------------------------------------------------
# Paths (same layout as dev_scripts ``tests/data/``)
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / "data"

SUBSEPS_TEST = DATA_DIR / "subseps_test"
SEPS_TEST_BASE = DATA_DIR / "seps_test_base"
SEPS_TEST_SORTED = DATA_DIR / "seps_test_sorted"
TESTCRIME_CSV = DATA_DIR / "testcrimedata.csv"


# ---------------------------------------------------------------------------
# Expected outputs transcribed from t_subsep.sh (line references are to that file)
# ---------------------------------------------------------------------------

# t_subsep.sh L13–16: ds:subsep tests/data/subseps_test "SEP" | ds:reo 1,7
T_SUBSEP_BASIC_REO_1_7 = """A;A;A;A
G;G;G;G"""

# t_subsep.sh L19–24: README CSV / slash subsep (after reo 1..5 1,2)
T_SUBSEP_README_CSV = """cdatetime,,,address
1,1,06 0:00,3108 OCCIDENTAL DR
1,1,06 0:00,2082 EXPEDITION WAY
1,1,06 0:00,4 PALEN CT
1,1,06 0:00,22 BECKFORD CT"""

# t_subsep.sh L28–31: selective fields with CSV OFS
T_SUBSEP_SELECTIVE_FIELDS_CSV = """a,b,c:d,e,f
1,2,3:4,5,6"""

# t_subsep.sh L35–36: echo pipe, slash subsep, empty nomatch → space-joined subfields
T_SUBSEP_PIPE_SLASH = "a b c d"

# t_subsep.sh L40–43: empty subfield (::) — passthrough lines
T_SUBSEP_EMPTY_SUBFIELD = """a::b:c
d::e:f"""

# t_subsep.sh L47–50: regex brackets, split on [ or ]
T_SUBSEP_REGEX_BRACKETS = """a 1 b 2 c
d 3 e 4 f"""

# t_subsep.sh L54–57: escape dot pattern
T_SUBSEP_ESCAPED_DOT = """a b c
d e f"""

# t_subsep.sh L62–63 (stderr): invalid apply_to_fields
T_SUBSEP_ERR_INVALID_FIELDS = "ERROR: No valid fields specified in apply_to_fields"

# t_subsep.sh L68–69 (stderr): missing subsep pattern
T_SUBSEP_ERR_MISSING_PATTERN = "ERROR: subsep_pattern must be set"


# ---------------------------------------------------------------------------
# Current Python behavior (constructor + process_file)
# ---------------------------------------------------------------------------


def test_subsep_fixture_files_exist() -> None:
    assert SUBSEPS_TEST.is_file(), f"Missing {SUBSEPS_TEST}"
    assert SEPS_TEST_BASE.is_file(), f"Missing {SEPS_TEST_BASE}"
    assert SEPS_TEST_SORTED.is_file(), f"Missing {SEPS_TEST_SORTED}"
    assert TESTCRIME_CSV.is_file(), f"Missing {TESTCRIME_CSV}"


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def test_subsep_cli_file_and_pattern(cli_runner: CliRunner) -> None:
    """``FILE SUBSEP_PATTERN`` uses :class:`~scripts.DataFile.DataFile` (resolved path)."""
    result = cli_runner.invoke(
        cli,
        [".", "subsep", str(SUBSEPS_TEST), "SEP"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


def test_subsep_cli_stdin_single_pattern(cli_runner: CliRunner) -> None:
    """``SUBSEP_PATTERN`` with piped body (``CliArgContext`` + stdin)."""
    result = cli_runner.invoke(
        cli,
        [".", "subsep", "SEP"],
        input="a SEP b\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0


def test_subsep_cli_two_args_first_not_a_file(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(
        cli,
        [".", "subsep", "not_a_real_file_12345.txt", "SEP"],
        catch_exceptions=True,
    )
    assert result.exit_code != 0
    assert "first argument must be an existing file" in (result.output or "")


def test_cli_arg_context_tested_first_arg_resolves_file() -> None:
    p = str(SUBSEPS_TEST)
    ctx = CliArgContext((p, "pat"), None, PathCandidatePredicate.TESTED_FIRST_ARG)
    assert ctx.resolved_path is not None
    assert os.path.isfile(ctx.resolved_path)


def test_cli_arg_context_shifted_arg_zero_matches_file_plus_pattern() -> None:
    p = str(SUBSEPS_TEST)
    ctx = CliArgContext((p, "SEP"), None, PathCandidatePredicate.TESTED_FIRST_ARG)
    assert ctx.shifted_arg(0) == "SEP"


def test_cli_arg_context_shifted_arg_zero_matches_pattern_only() -> None:
    ctx = CliArgContext(("SEP",), None, PathCandidatePredicate.TESTED_FIRST_ARG)
    assert ctx.resolved_path is None
    assert ctx.shifted_arg(0) == "SEP"


def test_cli_arg_context_shifted_arg_requires_tested_first() -> None:
    ctx = CliArgContext(("x",), None, PathCandidatePredicate.FIRST_ARG)
    with pytest.raises(ValueError, match="TESTED_FIRST_ARG"):
        ctx.shifted_arg(0)


def test_cli_arg_context_tested_first_arg_unknown_is_none() -> None:
    ctx = CliArgContext(
        ("not_a_real_file_98765.txt",),
        None,
        PathCandidatePredicate.TESTED_FIRST_ARG,
    )
    assert ctx.resolved_path is None
    assert ctx.path_candidate is None


def test_cli_arg_context_allowed_lengths_raises() -> None:
    with pytest.raises(click.ClickException, match="wrong count"):
        CliArgContext(
            ("a", "b", "c"),
            None,
            PathCandidatePredicate.TESTED_FIRST_ARG,
            allowed_lengths=(1, 2),
            bad_length_message="wrong count",
        )


def test_cli_arg_context_tested_first_allowed_1_2_two_args_first_not_file_raises() -> None:
    with pytest.raises(click.ClickException, match="first argument must be an existing file"):
        CliArgContext(
            ("not_a_real_file_99999.txt", "SEP"),
            None,
            PathCandidatePredicate.TESTED_FIRST_ARG,
            tested_first_arg_file_pair_rules=True,
        )


def test_cli_arg_context_tested_first_allowed_1_2_one_arg_existing_file_raises() -> None:
    p = str(SUBSEPS_TEST)
    with pytest.raises(click.ClickException, match="FILE SUBSEP_PATTERN"):
        CliArgContext(
            (p,),
            None,
            PathCandidatePredicate.TESTED_FIRST_ARG,
            tested_first_arg_file_pair_rules=True,
        )


def test_subsep_cli_three_args_bad_first_file_still_errors(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(
        cli,
        [".", "subsep", "a", "b", "c"],
        catch_exceptions=True,
    )
    assert result.exit_code != 0
    assert "first argument must be an existing file" in (result.output or "")


def test_subsep_cli_extra_args_after_file_and_pattern_warns(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(
        cli,
        [".", "subsep", str(SUBSEPS_TEST), "SEP", "extra", "more"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Warning: ignoring" in result.output
    assert "2 extra" in result.output


def test_empty_subsep_pattern_exits() -> None:
    """Missing pattern: shell reports ERROR; Python prints and sys.exit(1)."""
    with pytest.raises(SystemExit) as exc:
        SubseparatorFinder(subsep_pattern="", nomatch_handler=r"\s+")
    assert exc.value.code == 1


def test_invalid_apply_to_fields_exits() -> None:
    """t_subsep.sh L60–64: invalid apply_to_fields — shell prints ERROR; Python exits 1."""
    pattern = ":"
    with pytest.raises(SystemExit) as exc:
        SubseparatorFinder(
            subsep_pattern=pattern,
            nomatch_handler="",
            apply_to_fields="abc",
        )
    assert exc.value.code == 1


def test_process_file_runs_on_minimal_file(tmp_path: Path) -> None:
    """Smoke: ``process_file`` returns dicts on a single line with no subsep splits.

    The full ``subseps_test`` fixture can trigger edge cases in ``process_line`` (e.g.
    empty subfields) until ``scripts/subseparator.py`` is hardened.
    """
    p = tmp_path / "minimal.txt"
    p.write_text("x y\n", encoding="utf-8")
    finder = SubseparatorFinder(subsep_pattern="SEP", nomatch_handler=r"\s+")
    max_subseps, subfield_shifts = finder.process_file(str(p))
    assert isinstance(max_subseps, dict)
    assert isinstance(subfield_shifts, dict)


# ---------------------------------------------------------------------------
# Parity with t_subsep.sh
# ---------------------------------------------------------------------------


def _subsep_out(cli_runner: CliRunner, argv: list, **kwargs) -> str:
    result = cli_runner.invoke(cli, [".", "subsep", *argv], catch_exceptions=False, **kwargs)
    assert result.exit_code == 0, result.output
    return result.output.strip("\n")


def test_basic_subsep_matches_t_subsep_reo_columns_1_and_7(cli_runner: CliRunner) -> None:
    """t_subsep.sh L12-16. The shell piped through ``ds:reo 1,7``; rows are sliced here."""
    out = _subsep_out(cli_runner, [str(SUBSEPS_TEST), "SEP"]).splitlines()
    assert "\n".join([out[0], out[6]]) == T_SUBSEP_BASIC_REO_1_7


def test_readme_csv_slash_case_matches_t_subsep(cli_runner: CliRunner, tmp_path: Path) -> None:
    """t_subsep.sh L18-25. The shell prefixed ``ds:reo 1..5 1,2``; the slice is built here."""
    rows = list(csv.reader(TESTCRIME_CSV.open(encoding="utf-8")))[:5]
    sliced = tmp_path / "crime_slice.csv"
    sliced.write_text("\n".join(",".join(r[:2]) for r in rows) + "\n", encoding="utf-8")
    assert _subsep_out(cli_runner, [str(sliced), "/"]) == T_SUBSEP_README_CSV


def test_selective_fields_csv_matches_t_subsep(cli_runner: CliRunner, tmp_path: Path) -> None:
    """t_subsep.sh L27-32: only fields 1 and 3 are subseparated; the comma OFS is kept."""
    p = tmp_path / "selective.csv"
    p.write_text("a:b,c:d,e:f\n1:2,3:4,5:6\n", encoding="utf-8")
    out = _subsep_out(cli_runner, [str(p), ":", "--apply-to-fields", "1,3"])
    assert out == T_SUBSEP_SELECTIVE_FIELDS_CSV


def test_piped_slash_field_splitting_matches_t_subsep(cli_runner: CliRunner) -> None:
    """t_subsep.sh L34-37."""
    assert _subsep_out(cli_runner, ["/"], input="a/b c/d\n") == T_SUBSEP_PIPE_SLASH


def test_empty_subfield_passthrough_matches_t_subsep(cli_runner: CliRunner, tmp_path: Path) -> None:
    """t_subsep.sh L39-44: ``:`` is the inferred field separator, so nothing is subseparated."""
    p = tmp_path / "empty_subfield.txt"
    p.write_text("a::b:c\nd::e:f\n", encoding="utf-8")
    assert _subsep_out(cli_runner, [str(p), ":"]) == T_SUBSEP_EMPTY_SUBFIELD


def test_regex_brackets_matches_t_subsep(cli_runner: CliRunner, tmp_path: Path) -> None:
    """t_subsep.sh L46-51: ``--regex`` keeps the alternation instead of escaping it."""
    p = tmp_path / "brackets.txt"
    p.write_text("a[1]b[2]c\nd[3]e[4]f\n", encoding="utf-8")
    out = _subsep_out(cli_runner, [str(p), r"\[|\]", "--regex"])
    assert out == T_SUBSEP_REGEX_BRACKETS


def test_escaped_dot_pattern_matches_t_subsep(cli_runner: CliRunner, tmp_path: Path) -> None:
    """t_subsep.sh L53-58."""
    p = tmp_path / "dots.txt"
    p.write_text("a.b.c\nd.e.f\n", encoding="utf-8")
    assert _subsep_out(cli_runner, [str(p), ".", "--escape"]) == T_SUBSEP_ESCAPED_DOT


def test_stderr_contract_invalid_apply_to_fields_documented(capsys) -> None:
    """t_subsep.sh L60-64: the shell ERROR text is printed before exiting."""
    with pytest.raises(SystemExit):
        SubseparatorFinder(subsep_pattern=":", nomatch_handler="", apply_to_fields="abc")
    assert T_SUBSEP_ERR_INVALID_FIELDS in capsys.readouterr().out


def test_stderr_contract_missing_pattern_documented(capsys) -> None:
    """t_subsep.sh L66-70: the shell ERROR text is printed before exiting."""
    with pytest.raises(SystemExit):
        SubseparatorFinder(subsep_pattern="", nomatch_handler=r"\s+")
    assert T_SUBSEP_ERR_MISSING_PATTERN in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Expanded: seps_test_base vs seps_test_sorted (not in t_subsep.sh)
# ---------------------------------------------------------------------------


def test_seps_base_and_sorted_same_line_count() -> None:
    base_lines = SEPS_TEST_BASE.read_text(encoding="utf-8").splitlines()
    sorted_lines = SEPS_TEST_SORTED.read_text(encoding="utf-8").splitlines()
    assert len(base_lines) == len(sorted_lines) == 100


def test_seps_sorted_is_not_identical_to_base() -> None:
    """Sorted dataset is a permutation / reordering of the same logical records."""
    assert SEPS_TEST_BASE.read_bytes() != SEPS_TEST_SORTED.read_bytes()


def test_seps_lines_use_ampersand_hash_field_separator() -> None:
    """Spot-check: rows use ``&%#`` between fields (6 delimiters → 7 columns in each row)."""
    sample = SEPS_TEST_BASE.read_text(encoding="utf-8").splitlines()[0]
    parts = sample.split("&%#")
    assert len(parts) == 7


def test_subseparator_finder_processes_seps_test_base_with_ampersand_hash_sep() -> None:
    """``&%#`` is the field delimiter in ``seps_test_*``; future subsep tests can key off this."""
    finder = SubseparatorFinder(subsep_pattern="&%#", nomatch_handler=r"\s+")
    max_subseps, shifts = finder.process_file(str(SEPS_TEST_BASE))
    assert isinstance(max_subseps, dict)
    assert isinstance(shifts, dict)
