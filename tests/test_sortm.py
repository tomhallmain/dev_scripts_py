"""``ds sortm`` tests; the reference cases follow ``dev_scripts/tests/t_sort.sh``."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.fields_qsort import SortKeyError, SortM, compare_numeric, leading_number

DATA = Path(__file__).resolve().parent / "data"

REFERENCE_CASES = [
    pytest.param(['d c a b f', 'f e c b a', 'f e d c b', 'e d c b a'], {'keys': '5,1', 'order': 'd', 'field_separator': ' '}, 'd c a b f\nf e d c b\nf e c b a\ne d c b a', id='awkargs'),
    pytest.param(['1', 'J', '98', '47', '9', '05', 'j2', '9ju', '9', '9d'], {'keys': '1', 'order': 'a', 'sort_type': 'n', 'field_separator': ' '}, '1\n05\n9\n9\n9d\n9ju\n47\n98\nJ\nj2', id='numeric'),
    pytest.param(['Test Header 1,Test Header 2,Header,Test', '3,88,h,3', ',5,Eq,:', ',,,', '', ',a,1,', 'Yh,4304,45900,H'], {'keys': 'Test.Header.2,Header,Test', 'order': 'a', 'sort_type': 'n', 'field_separator': ','}, 'Test Header 1,Test Header 2,Header,Test\n,,,\n,5,Eq,:\n3,88,h,3\nYh,4304,45900,H\n,a,1,', id='genkeys'),
    pytest.param(['Button-2', 'Control-e', 'Control-C', 'Control-Return', 'Control-Tab', 'Control-a', 'Control-b', 'Control-d', 'Control-g', 'Control-h', 'F11', 'Control-j', 'Control-k', 'Control-n', 'MouseWheel', 'Control-q', 'Control-r', 'Control-s', 'Control-t', 'Next', 'Control-x', 'Control-z', 'Button-3', 'Control-w', 'Shift-F', 'Shift-A', 'Escape', 'Shift-B', 'Shift-C', 'Shift-D', 'Shift-E', 'Shift-Escape', 'Shift-G', 'Control-m', 'Shift-H', 'Shift-I', 'Prior', 'Shift-J', 'Shift-K', 'Shift-L', 'Home', 'Shift-N', 'Shift-M', 'Shift-Q', 'Shift-T', 'Shift-R', 'Shift-S', 'Shift-U', 'End', 'Shift-V', 'Shift-Z', 'Shift-Y'], {'keys': '2,1', 'order': 'a', 'sort_type': 'ni', 'field_separator': '-'}, 'End\nEscape\nF11\nHome\nMouseWheel\nNext\nPrior\nButton-2\nButton-3\nControl-a\nShift-A\nControl-b\nShift-B\nControl-C\nShift-C\nControl-d\nShift-D\nControl-e\nShift-E\nShift-Escape\nShift-F\nControl-g\nShift-G\nControl-h\nShift-H\nShift-I\nControl-j\nShift-J\nControl-k\nShift-K\nShift-L\nControl-m\nShift-M\nControl-n\nShift-N\nControl-q\nShift-Q\nControl-r\nShift-R\nControl-Return\nControl-s\nShift-S\nControl-t\nShift-T\nControl-Tab\nShift-U\nShift-V\nControl-w\nControl-x\nShift-Y\nControl-z\nShift-Z', id='case-insens'),
]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize("lines, kwargs, expected", REFERENCE_CASES)
def test_sortm_reference_cases(lines, kwargs, expected) -> None:
    assert "\n".join(SortM(**kwargs).sort_lines(lines)) == expected


def test_sortm_multikey_deterministic_descending() -> None:
    """t_sort 'multikey case', with the ``&%#`` separator the original infers for this file."""
    lines = (DATA / "seps_test_base").read_text(encoding="utf-8").splitlines()
    expected = (DATA / "seps_test_sorted").read_text(encoding="utf-8").rstrip("\n")
    sorter = SortM("2,3,7", "d", field_separator="&%#", deterministic=True)
    assert "\n".join(sorter.sort_lines(lines)) == expected


def test_leading_number_and_numeric_compare() -> None:
    assert leading_number("9ju") == (9.0, "ju")
    assert leading_number("1,234 x") == (1.0, " x")
    assert leading_number("J") is None
    assert compare_numeric("9", "9d") < 0
    assert compare_numeric(",,", "5") < 0
    assert compare_numeric("a,1,", "4304") > 0


def test_sortm_default_single_key_compares_numbers_numerically() -> None:
    assert SortM("1").sort_lines(["10 a", "9 b", "x c"]) == ["9 b", "10 a", "x c"]


def test_sortm_equal_keys_keep_input_order() -> None:
    assert SortM("1").sort_lines(["a 2", "a 1", "b 0"]) == ["a 2", "a 1", "b 0"]


def test_sortm_nf_key_and_header() -> None:
    lines = ["h1 h2", "x 3", "y 1 0", "z 2"]
    assert SortM("NF", header=True).sort_lines(lines) == ["h1 h2", "y 1 0", "z 2", "x 3"]


def test_sortm_unmatched_header_patterns_error() -> None:
    with pytest.raises(SortKeyError):
        SortM("nomatch").sort_lines(["a b", "1 2"])


def test_sortm_cli_file_with_keys_order_type(runner: CliRunner, tmp_path: Path) -> None:
    p = tmp_path / "d.txt"
    p.write_text("b 10\na 9\nc 100\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "sortm", str(p), "2", "d", "n"], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "c 100\nb 10\na 9\n"


def test_sortm_cli_stdin_shifts_args(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "sortm", "1", "a", "i"], input="b\nA\nc\n",
                           catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "A\nb\nc\n"


def test_sortm_cli_default_is_deterministic(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "sortm"], input="a z\na b\n", catch_exceptions=False)
    assert result.output == "a b\na z\n"


def test_sortm_cli_header_pattern_error(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "sortm", "nomatch"], input="a b\n1 2\n")
    assert result.exit_code != 0
    assert "No key patterns provided matched header" in result.output


def test_sortm_cli_has_no_stub_banner(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "sortm"], input="b\na\n", catch_exceptions=False)
    assert result.output == "a\nb\n"
