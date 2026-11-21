"""``ds hist`` tests; the reference cases follow ``dev_scripts/tests/t_shape.sh``."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.field_rows import read_rows
from scripts.hist import Histogram, awk_key

DATA = Path(__file__).resolve().parent / "data"

CRIME_EXPECTED = 'Hist: district (field 3), cardinality 6\n                        1 ++++++++ (868)\n                        2 +++++++++++++ (1462)\n                        3 +++++++++++++++ (1575)\n                        4 +++++++++++ (1161)\n                        5 +++++++++++ (1159)\n                        6 ++++++++++++ (1359)\n\nHist: grid (field 5), cardinality 539\n                102 - 257 ++++ (383)\n                258 - 413 +++ (303)\n                414 - 569 +++++++++++++++ (1269)\n                570 - 725 +++++++ (593)\n                726 - 881 ++++++++++++++ (1187)\n               882 - 1037 ++++++++++++ (1091)\n              1038 - 1193 ++++++++ (692)\n              1194 - 1349 +++++ (471)\n              1350 - 1505 +++++++++ (833)\n              1506 - 1661 +++++++++ (762)\n\nHist: ucr_ncic_code (field 7), cardinality 88\n               909 - 1628 +++ (534)\n              1629 - 2347 ++++++++ (1429)\n              2348 - 3066 ++++++++++ (1787)\n              3067 - 3786 ++ (368)\n              3787 - 4505  (56)\n              4506 - 5224 + (176)\n              5225 - 5944 ++++ (731)\n              5945 - 6663  (0)\n              6664 - 7382 +++++++++++++++ (2471)\n              7383 - 8102  (32)\n\nHist: latitude (field 8), cardinality 1906\n            38.44 - 38.46 ++ (228)\n            38.46 - 38.49 +++++++++ (779)\n            38.49 - 38.51 +++++++ (676)\n            38.51 - 38.54 +++++++++++ (1002)\n            38.54 - 38.56 +++++++++++++ (1149)\n            38.56 - 38.59 +++++++++++++++ (1291)\n            38.59 - 38.61 ++++++ (555)\n            38.61 - 38.63 +++++++++++++ (1176)\n            38.63 - 38.66 ++++++ (577)\n            38.66 - 38.68 + (151)\n\nHist: longitude (field 9), cardinality 187\n        -121.56 - -121.54 + (121)\n        -121.54 - -121.52 +++ (337)\n        -121.52 - -121.50 +++++++ (769)\n        -121.50 - -121.48 ++++++++++++++ (1414)\n        -121.48 - -121.46 +++++++++++++++ (1480)\n        -121.46 - -121.44 +++++++++++++ (1283)\n        -121.44 - -121.42 +++++++++++++ (1330)\n        -121.42 - -121.40 ++++++ (652)\n        -121.40 - -121.38 + (117)\n        -121.38 - -121.36  (81)'

FEATURE_DATA = "value,category\n1.2,A\n2.5,A\n3.8,A\n10.5,B\n15.2,B\n25.6,B\n100.2,C\n150.5,C\n200.8,C\n500.1,C\n"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _render(histogram: Histogram) -> str:
    return "\n".join(line.rstrip() for line in histogram.render()).rstrip("\n")


def test_hist_reference_crime_data() -> None:
    """t_shape 'hist command': header detection, integer and decimal bins, bar scaling."""
    histogram = Histogram()
    histogram.process_rows(read_rows(str(DATA / "testcrimedata.csv"), ","))
    assert _render(histogram) == CRIME_EXPECTED


def test_hist_reference_five_bins() -> None:
    """Bin labels and counts of the t_shape 'blocks style' case (bars here are ``+``)."""
    histogram = Histogram(n_bins=5, header=True, fields=[1])
    histogram.process_rows([line.split(",") for line in FEATURE_DATA.splitlines()])
    assert _render(histogram) == (
        "Hist: value (field 1), cardinality 10\n"
        "              1.2 - 101.0 +++++++ (7)\n"
        "            101.0 - 200.8 + (1)\n"
        "            200.8 - 300.5 + (1)\n"
        "            300.5 - 400.3  (0)\n"
        "            400.3 - 500.1 + (1)"
    )


def test_hist_reference_single_value() -> None:
    """t_shape 'histogram edge case': one distinct integer gives one bin."""
    histogram = Histogram(header=True, fields=[1])
    histogram.process_rows([["value"]] + [["1"]] * 5)
    assert _render(histogram) == (
        "Hist: value (field 1), cardinality 1\n"
        "                        1 +++++ (5)"
    )


def test_hist_first_row_without_header_is_data() -> None:
    histogram = Histogram()
    histogram.process_rows([["1"], ["2"]])
    assert _render(histogram).startswith("Hist: field 1, cardinality 2")


def test_awk_key_rounds_like_awk() -> None:
    assert awk_key(38.55042047) == "38.5504"
    assert awk_key(1115.0) == "1115"


def test_hist_cli_stdin_bins_and_fields(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "hist", "5", "--fields", "1"], input=FEATURE_DATA,
                           catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.splitlines()[1] == "              1.2 - 101.0 +++++++ (7)"


def test_hist_cli_file_bar_len(runner: CliRunner, tmp_path: Path) -> None:
    p = tmp_path / "h.txt"
    p.write_text("n\n" + "1\n" * 20 + "2\n" * 10, encoding="utf-8")
    result = runner.invoke(cli, [".", "hist", str(p), "10", "4"], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == (
        "Hist: n (field 1), cardinality 2\n"
        "                        1 ++++ (20)\n"
        "                        2 ++ (10)\n"
        "\n"
    )


def test_hist_cli_has_no_wip_banner(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "hist"], input="x\n1\n", catch_exceptions=False)
    assert "work-in-progress" not in result.output
