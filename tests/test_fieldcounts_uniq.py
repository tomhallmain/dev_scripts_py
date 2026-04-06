"""
Tests for ``field_counts`` (``ds:fieldcounts`` / ``ds:fc``) and ``field_uniques`` (``ds:uniq``).

Expectations mirror ``dev_scripts/tests/t_fieldcounts.sh``. Row reading uses
:class:`scripts.DataFile.DataFile` inside :class:`scripts.field_counts.FieldsCounter`
and :class:`scripts.field_uniques.FieldUniques`.
"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.DataFile import DataFile
from scripts.field_counts import FieldsCounter
from scripts.field_uniques import FieldUniques
from scripts.utils import Utils

TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / "data"
COMPANY_CSV = DATA_DIR / "company_funding_data.csv"

# --- t_fieldcounts.sh: fieldcounts ---
# shell: ds:fieldcounts tests/data/company_funding_data.csv a 2
EXPECTED_FC_ALL_FIELDS = """2,mozy,Mozy,26,web,American Fork,UT,1-May-05,1900000,USD,a
2,zoominfo,ZoomInfo,80,web,Waltham,MA,1-Jul-04,7000000,USD,a
"""

EXPECTED_FC_FIELD7 = """54,1-Jan-08
54,1-Oct-07
"""

EXPECTED_FC_MULTI = """7,450,Palo Alto,facebook
"""

# --- t_fieldcounts.sh: uniq (stdin-style data) ---
UNIQ_INPUT = """a
b
c
1
e
c
b
a
i
c
55
3
"""

EXPECTED_UNIQ_DEFAULT = """a
b
c
e
i
1
3
55
"""

EXPECTED_UNIQ_MIN2 = """a
b
c
"""

EXPECTED_UNIQ_MIN3 = """c
"""

EXPECTED_UNIQ_DESC = """55
3
1
i
e
c
b
a
"""


def _run_field_counts(fields: str, min_count: int) -> str:
    Utils.set_start_dir(str(TESTS_DIR.parent))
    df = DataFile(str(COMPANY_CSV))
    fc = FieldsCounter(df, fields=fields, min=min_count)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fc.run()
    return buf.getvalue()


def _run_field_uniques(
    text: str,
    *,
    fields_spec: str = "a",
    min_user: int = 1,
    order: str = "a",
) -> str:
    Utils.set_start_dir(str(TESTS_DIR.parent))
    p = TESTS_DIR / "data" / "_uniq_tmp.txt"
    p.write_text(text, encoding="utf-8")
    try:
        df = DataFile(str(p))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            FieldUniques(df, fields_spec=fields_spec, min_user=min_user, order=order).run()
        return buf.getvalue()
    finally:
        p.unlink(missing_ok=True)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_company_funding_csv_exists() -> None:
    assert COMPANY_CSV.is_file()


def test_fieldcounts_all_fields_min2_matches_t_fieldcounts() -> None:
    assert _run_field_counts("a", 2) == EXPECTED_FC_ALL_FIELDS


def test_fieldcounts_single_field7_min50_matches_t_fieldcounts() -> None:
    assert _run_field_counts("7", 50) == EXPECTED_FC_FIELD7


def test_fieldcounts_multifield_3_5_1_min6_matches_t_fieldcounts() -> None:
    assert _run_field_counts("3,5,1", 6) == EXPECTED_FC_MULTI


def test_uniq_default_matches_t_fieldcounts() -> None:
    out = _run_field_uniques(UNIQ_INPUT, fields_spec="a", min_user=1, order="a")
    assert out == EXPECTED_UNIQ_DEFAULT


def test_uniq_min2_fields0_matches_t_fieldcounts() -> None:
    """``ds:uniq 0 2`` → fields 0, min 2 (shell ``min-1`` in awk)."""
    out = _run_field_uniques(UNIQ_INPUT, fields_spec="0", min_user=2, order="a")
    assert out == EXPECTED_UNIQ_MIN2


def test_uniq_min3_field1_matches_t_fieldcounts() -> None:
    out = _run_field_uniques(UNIQ_INPUT, fields_spec="1", min_user=3, order="a")
    assert out == EXPECTED_UNIQ_MIN3


def test_uniq_desc_field1_matches_t_fieldcounts() -> None:
    out = _run_field_uniques(UNIQ_INPUT, fields_spec="1", min_user=1, order="d")
    assert out == EXPECTED_UNIQ_DESC


def test_field_uniques_requires_data_file() -> None:
    with pytest.raises(TypeError, match="DataFile"):
        FieldUniques(object(), fields_spec="a")  # type: ignore[arg-type]


def test_field_counts_cli_file_and_stdin_smoke(tmp_path: Path, runner: CliRunner) -> None:
    """``ds field-counts`` with optional file or stdin via CliArgContext."""
    p = tmp_path / "fc.txt"
    p.write_text("a b\na c\n", encoding="utf-8")
    r_file = runner.invoke(cli, [".", "field-counts", str(p)], catch_exceptions=False)
    assert r_file.exit_code == 0
    r_stdin = runner.invoke(cli, [".", "field-counts"], input="a b\n", catch_exceptions=False)
    assert r_stdin.exit_code == 0
