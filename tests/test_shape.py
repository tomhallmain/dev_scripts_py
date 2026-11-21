"""``ds shape`` tests; the reference cases follow ``dev_scripts/tests/t_shape.sh``."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.shape import Shape, parse_fields, parse_measures

DATA = Path(__file__).resolve().parent / "data"

AUBURN_EXPECTED = '       lines: 7585\n       lines with "AUBURN": 75\n       occurrence: 76\n       average: 0.0100198\nlineno distribution of "AUBURN"\n   758 +++++++++++\n  1516 +++++++\n  2274 ++++++\n  3032 +++++++\n  3790 ++++++\n  4548 ++++++++\n  5306 ++++++++\n  6064 +++++++++\n  6822 ++++++++\n  7580 ++++++\n  8338'

MULTI_MEASURE_EXPECTED = '       lines: 7585\n       stats from field: $6\n       lines with "AUTO": 237                                   lines with "INDECE": 2                                   lines with "PUBLI": 31                                   lines with "BURGL": 986\n       occurrence: 237                                          occurrence: 2                                            occurrence: 31                                           occurrence: 986\n       average: 0.0312459                                       average: 0.000263678                                     average: 0.00408701                                      average: 0.129993\nlineno distribution of "AUTO"                                   distribution of "INDECE"                                 distribution of "PUBLI"                                  distribution of "BURGL"\n   252 +++                                                                                                               ++++                                                     +++++++++++++++++++++++++++++++++\n   504 ++++++++++++++++                                         +                                                        ++                                                       +++++++++++++++++++++++++++++++++++++\n   756 +++++++++++++                                                                                                     +                                                        +++++++++++++++++++++++++++++++++++++++++++++++\n  1008 +++++                                                                                                                                                                      ++++++++++++++++++++\n  1260 +++++                                                                                                             +                                                        ++++++++++++++++++++++++++++++++++++++++\n  1512 ++++                                                                                                              ++++                                                     ++++++++++++++++++++++++++++++++++++\n  1764 ++++++++                                                                                                                                                                   +++++++++++++++++++++++++++++++++++++++++++++++++\n  2016 +++++                                                                                                                                                                      ++++++++++++++++++++++++++++++\n  2268 ++++++++++                                                                                                                                                                 ++++++++++++++++++++++++++++++++++\n  2520 ++++++                                                                                                                                                                     +++++++++++++++++++++++++++++++++++++\n  2772 ++++++                                                                                                            +                                                        ++++++++++++++++++++++++++++++++++++\n  3024 +++++++                                                                                                           +                                                        +++++++++++++++++++++++++++++++++++\n  3276 ++                                                                                                                +                                                        ++++++++++++++++++++++++++++++++++++\n  3528 ++++                                                                                                                                                                       ++++++++++++++++++++++++++++++\n  3780 ++++++++                                                                                                                                                                   +++++++++++++++++++++++\n  4032 +++++++++                                                                                                                                                                  ++++++++++++++++++++++++++++++\n  4284 ++++++++++++++++                                                                                                                                                           ++++++++++++++++++++++++++++++++\n  4536 ++++++                                                                                                            ++                                                       +++++++++++++++++++++++++++++\n  4788 +++++++++                                                                                                                                                                  +++++++++++++++++++++++++++++++++++++++\n  5040 +++++                                                                                                             +++                                                      +++++++++++++++++++++++++++++++++++++++++\n  5292 +++++                                                                                                                                                                      ++++++++++++++++++++++++++++++\n  5544 +++++++++++++++                                                                                                   +++                                                      ++++++++++++++++++++++++++++\n  5796 ++++++++++                                                                                                                                                                 +++++++++++++++++++++++\n  6048 +++++++++                                                                                                         +                                                        +++++++++++++++++++++++++++++++++\n  6300 +++++++++                                                                                                                                                                  ++++++++++++++++++++++++++++++++++\n  6552 +++++++++++                                                                                                       ++                                                       ++++++++++++++++++++++++++++++++\n  6804 ++++++                                                                                                            +                                                        ++++++++++++++++++++++++++++++++\n  7056 +                                                        +                                                                                                                 ++++++++++++++++++++++++++++++++\n  7308 ++++++++++++++                                                                                                    +++                                                      +++++++++++++++++\n  7560 ++++++++++                                                                                                        +                                                        ++++++++++++++++++++++++++++\n  7812'

SIMPLE_EXPECTED = 'lines: 3\nlines with "Hello": 3\noccurrence: 3\naverage: 1'

SMALL_EXPECTED = '       lines: 6\n       lines with "a": 3\n       occurrence: 3\n       average: 0.5\nlineno distribution of "a"\n     3 +++\n     6\n     9'


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _crime_lines():
    return (DATA / "testcrimedata.csv").read_text(encoding="utf-8").splitlines(True)


def _render(shape: Shape, lines) -> str:
    return "\n".join(line.rstrip() for line in shape.render(lines))


@pytest.mark.parametrize("fields", ["0", "wfwe"])
def test_shape_reference_single_measure(fields: str) -> None:
    """t_shape: ``AUBURN`` over whole lines, 10 chart rows; an invalid field means line."""
    lines = _crime_lines()
    assert _render(Shape("AUBURN", fields, span=len(lines) // 10), lines) == AUBURN_EXPECTED


def test_shape_reference_multiple_measures_side_by_side() -> None:
    lines = _crime_lines()
    shape = Shape("AUTO,INDECE,PUBLI,BURGL", "6", span=len(lines) // 30, tty_size=238,
                  field_separator=",")
    assert _render(shape, lines) == MULTI_MEASURE_EXPECTED


def test_shape_reference_case_insensitive_simple() -> None:
    assert _render(Shape("Hello", simple=True), ["Hello", "hello", "HELLO"]) == SIMPLE_EXPECTED


def test_shape_reference_small_chart() -> None:
    """t_shape 'default style' case for the plus style."""
    lines = ["a", "a", "a", "b", "b", "c"]
    assert _render(Shape("a", span=3), lines) == SMALL_EXPECTED


def test_shape_no_match() -> None:
    assert Shape("zzz").render(["a", "b"]) == ["Data not found with given parameters"]


def test_parse_measures_and_fields() -> None:
    assert parse_measures("") == [("length", None)]
    assert parse_measures("_len")[0] == ("length", None)
    assert parse_fields("wfwe") == [0]
    assert parse_fields("2,x,3") == [2, 3]


def test_shape_cli_stdin(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "shape", "a", "0", "2"], input="a\na\na\nb\nb\nc\n",
                           catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == SMALL_EXPECTED + "\n"


def test_shape_cli_chart_size_zero_prints_stats_only(runner: CliRunner, tmp_path: Path) -> None:
    p = tmp_path / "s.txt"
    p.write_text("Hello\nhello\nHELLO\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "shape", str(p), "Hello", "0", "0"], catch_exceptions=False)
    assert result.output == SIMPLE_EXPECTED + "\n"


def test_shape_cli_empty_input_exits_1(runner: CliRunner) -> None:
    assert runner.invoke(cli, [".", "shape"], input="").exit_code == 1
