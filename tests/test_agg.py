"""``ds agg`` tests; the reference cases follow ``dev_scripts/tests/t_aggregation.sh``.

Only its cases built from range expressions (``OP|all``, ``OP|START..END``) and the default
aggregation are included. 'multiple header' drops the ``$2/$3`` summary row of the original
case, since field-index expressions are not supported.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.agg import Agg, AggError, AggExpression
from scripts.cli import cli
from scripts.field_rows import split_fields

REFERENCE_CASES = [
    pytest.param('one,two,three,four\n1,2,3,4\n4,3,2,1\n1,2,4,3\n3,2,4,1', ',', {'r_aggs': '*|2..4'},
                 'one,two,three,four,*|2..4\n1,2,3,4,24\n4,3,2,1,6\n1,2,4,3,24\n3,2,4,1,8',
                 id='R range product'),
    pytest.param('one,two,three,four\n1,2,3,4\n4,3,2,1\n1,2,4,3\n3,2,4,1', ',', {'r_aggs': 'mean|2..4'},
                 'one,two,three,four,mean|2..4\n1,2,3,4,3\n4,3,2,1,2\n1,2,4,3,3\n3,2,4,1,2.33333',
                 id='R range mean'),
    pytest.param('one,two,three,four\n1,2,3,4\n4,3,2,1\n1,2,4,3\n3,2,4,1', ',', {'r_aggs': '0', 'c_aggs': '-|3..4'},
                 'one,two,three,four\n1,2,3,4\n4,3,2,1\n1,2,4,3\n3,2,4,1\n-5,-5,-6,-4',
                 id='C range minus'),
    pytest.param('one,two,three,four\n1,2,3,4\n4,3,2,1\n1,2,4,3\n3,2,4,1', ',', {'r_aggs': '0', 'c_aggs': 'mean|3..5'},
                 'one,two,three,four\n1,2,3,4\n4,3,2,1\n1,2,4,3\n3,2,4,1\n2.66667,2.33333,3.33333,1.66667',
                 id='C range mean'),
    pytest.param('one:two:three:four\n1:2:3:4\n4:3:2:1\n1:2:4:3\n3:2:4:1', ':', {'r_aggs': '+|all'},
                 'one:two:three:four:+|all\n1:2:3:4:10\n4:3:2:1:10\n1:2:4:3:10\n3:2:4:1:10',
                 id='R all sum'),
    pytest.param('one:two:three:four\n1:2:3:4\n4:3:2:1\n1:2:4:3\n3:2:4:1', ':', {'r_aggs': 'mean|all'},
                 'one:two:three:four:mean|all\n1:2:3:4:2.5\n4:3:2:1:2.5\n1:2:4:3:2.5\n3:2:4:1:2.5',
                 id='R all mean'),
    pytest.param('one;two;three;four\n1;2;3;4\n4;3;2;1\n1;2;4;3\n3;2;4;1', ';', {'r_aggs': '0', 'c_aggs': '+|all'},
                 'one;two;three;four\n1;2;3;4\n4;3;2;1\n1;2;4;3\n3;2;4;1\n9;9;13;9',
                 id='C all sum'),
    pytest.param('one two three four\n1 2 3 4\n4 3 2 1\n1 2 4 3\n3 2 4 1', ' ', {},
                 'one two three four +|all\n1 2 3 4 10\n4 3 2 1 10\n1 2 4 3 10\n3 2 4 1 10\n9 9 13 9 40',
                 id='R+C default'),
    pytest.param('one two three four\n1 2 3 4\n4 3 2 1\n1 2 4 3\n3 2 4 1', ' ', {'r_aggs': '+|all', 'c_aggs': '+|all', 'header': True},
                 ' one two three four +|all\n 1 2 3 4 10\n 4 3 2 1 10\n 1 2 4 3 10\n 3 2 4 1 10\n+|all 9 9 13 9 40',
                 id='R+C header'),
    pytest.param('a 1 -2 3 4\nb 0 -3 4 1\nc 3 6 2.5 4', ' ', {},
                 'a 1 -2 3 4 6\nb 0 -3 4 1 2\nc 3 6 2.5 4 15.5\n+|all 4 1 9.5 9 23.5',
                 id='readme default'),
    pytest.param('one two three four\n1 2 3 4\n4 3 2 1\n1 2 4 3\n3 2 4 1', ' ', {'r_aggs': '+|all,*|2..4,/|all', 'c_aggs': '+|all', 'header': True},
                 ' one two three four +|all *|2..4 /|all\n 1 2 3 4 10 24 0.0416667\n 4 3 2 1 10 6 0.666667\n 1 2 4 3 10 24 0.0416667\n 3 2 4 1 10 8 0.375\n+|all 9 9 13 9 40 62 1.125',
                 id='multiple header'),
]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize("text, field_sep, kwargs, expected", REFERENCE_CASES)
def test_agg_reference_cases(text, field_sep, kwargs, expected) -> None:
    rows = [split_fields(line, field_sep) for line in text.split("\n")]
    out = Agg(**kwargs).run(rows)
    assert "\n".join(field_sep.join(r) for r in out) == expected


def test_agg_operators() -> None:
    values = [2.0, 3.0, 4.0]
    assert AggExpression("+").apply(values) == 9
    assert AggExpression("-").apply(values) == -9
    assert AggExpression("*|all").apply(values) == 24
    assert AggExpression("/").apply([8.0, 0.0, 2.0]) == 4
    assert AggExpression("mean").apply(values) == 3
    assert AggExpression("m").apply([]) is None


def test_agg_only_one_axis_given_leaves_the_other_off() -> None:
    assert Agg("+|all").run([["1", "2"]]) == [["1", "2", "3"]]
    assert Agg(None, "+|all").run([["1"], ["2"]]) == [["1"], ["2"], ["3"]]


@pytest.mark.parametrize("expr", ["$3+$2", "~b", "med|all", "+|2-4"])
def test_agg_unsupported_expressions(expr: str) -> None:
    with pytest.raises(AggError):
        AggExpression(expr)


def test_agg_cli_stdin_default(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "agg"], input="a 1 2\nb 3 4\n", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "a 1 2 3\nb 3 4 7\n+|all 4 6 10\n"


def test_agg_cli_file_with_axes(runner: CliRunner, tmp_path: Path) -> None:
    p = tmp_path / "d.csv"
    p.write_text("x,1,2\ny,3,4\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "agg", str(p), "0", "mean|all"], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "x,1,2\ny,3,4\nmean|all,2,3\n"


def test_agg_cli_unsupported_expression_errors(runner: CliRunner) -> None:
    result = runner.invoke(cli, [".", "agg", "$1+$2"], input="1 2\n")
    assert result.exit_code != 0
    assert "unsupported aggregation" in result.output
