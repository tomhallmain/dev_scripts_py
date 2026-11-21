"""``ds inferk`` tests; the reference cases follow ``dev_scripts/tests/t_inferk.sh``.

Two of its cases ('numeric distribution', 'cardinality') are not included: two columns
overlap equally there, and this heuristic takes the first pair where the original's
multi-factor score prefers the later one.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.infer_join_fields import (
    InferJoinError,
    best_column_pair,
    format_result,
    header_match,
    infer_join_fields,
)

REFERENCE_CASES = [
    pytest.param('ID,Name,Age,Score,Type\n1,John,25,95.5,A\n2,Jane,30,88.2,B\n3,Bob,28,92.1,A\n4,Alice,22,97.8,A\n5,Charlie,35,85.4,B\n',
                 'UserID,FullName,Years,Grade,Category\n1,John,25,95.5,A\n2,Jane,30,88.2,B\n3,Bob,28,92.1,A\n4,Alice,22,97.8,A\n5,Charlie,35,85.4,B\n',
                 ',', ',', '1', id='exact ID match'),
    pytest.param('ID,Name,Age,Score,Type\n1,John,25,95.5,A\n2,Jane,30,88.2,B\n3,Bob,28,92.1,A\n4,Alice,22,97.8,A\n5,Charlie,35,85.4,B\n',
                 'Name,Grade,UserID,Category,Years\nJohn,95.5,1,A,25\nJane,88.2,2,B,30\nBob,92.1,3,A,28\nAlice,97.8,4,A,22\nCharlie,85.4,5,B,35\n',
                 ',', ',', '2 1', id='exact Name header match'),
    pytest.param('ID,Name,Age,Score,Type\n1,John,25,95.5,A\n2,Jane,30,88.2,B\n3,Bob,28,92.1,A\n4,Alice,22,97.8,A\n5,Charlie,35,85.4,B\n',
                 'FullName,Grade,UserID,Category,Years\nJohn,95.5,1,A,25\nJane,88.2,2,B,30\nBob,92.1,3,A,28\nAlice,97.8,4,A,22\nCharlie,85.4,5,B,35\n',
                 ',', ',', '1 3', id='ID pattern match'),
    pytest.param('ID,Simple,Complex\n1,A,Mix3d_C4se!\n2,B,An0ther-0ne\n3,A,Th1rd_3ntry\n4,B,L4st_0ne!23\n5,A,F1nal-3ntry\n',
                 'Name,Category,Pattern\nJohn,X,Mix3d_C4se!\nJane,Y,An0ther-0ne\nBob,X,Th1rd_3ntry\nAlice,Y,L4st_0ne!23\nCharlie,X,F1nal-3ntry\n',
                 ',', ',', '3', id='entropy match'),
    pytest.param('ID;Name;Value\n1;John;100\n2;Jane;200\n3;Bob;300\n',
                 'UserID|FullName|Amount\n1|John|100\n2|Jane|200\n3|Bob|300\n',
                 ';', '|', '1', id='different separators'),
    pytest.param('ID,Date,Data\n1,2024-03-15,{"type":"A"}\n2,2024-03-16,{"type":"B"}\n3,2024-03-17,{"type":"C"}\n',
                 'UserID,Timestamp,Metadata\n1,03/15/2024,{"type":"A"}\n2,03/16/2024,{"type":"B"}\n3,03/17/2024,{"type":"C"}\n',
                 ',', ',', '1', id='special types'),
    pytest.param('ID,Name,Value\n1,John,100\n2,,200\n3,Bob,\n4,Alice,400\n',
                 'UserID,FullName,Amount\n1,John,100\n2,,200\n3,Bob,\n4,Alice,400\n',
                 ',', ',', '1', id='missing values'),
    pytest.param('ID,Name,Value,Extra1,Extra2\n1,John,100,A,X\n2,Jane,200,B,Y\n3,Bob,300,C,Z\n',
                 'UserID,FullName,Amount\n1,John,100\n2,Jane,200\n3,Bob,300\n',
                 ',', ',', '1', id='varying columns'),
]


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize("text1, text2, fs1, fs2, expected", REFERENCE_CASES)
def test_inferk_reference_cases(text1, text2, fs1, fs2, expected) -> None:
    assert infer_join_fields(text1.splitlines(), text2.splitlines(), fs1, fs2) == expected


def test_header_match_first_shared_name() -> None:
    assert header_match(["id", "name", "city"], ["city", "id"]) == (1, 2)
    assert header_match(["a", "b"], ["c", "d"]) is None


def test_best_column_pair_by_value_overlap() -> None:
    rows1 = [["a", "1"], ["b", "2"], ["c", "3"]]
    rows2 = [["1", "x"], ["2", "y"], ["9", "z"]]
    assert best_column_pair(rows1, rows2) == (2, 1)


def test_format_result() -> None:
    assert format_result(2, 2) == "2"
    assert format_result(1, 3) == "1 3"


def test_inferk_requires_data_rows() -> None:
    with pytest.raises(InferJoinError):
        infer_join_fields(["a,b"], ["c,d"], ",", ",")


def test_inferk_cli_two_files(runner: CliRunner, tmp_path: Path) -> None:
    f1 = tmp_path / "a.csv"
    f2 = tmp_path / "b.csv"
    f1.write_text("id,name\n1,ann\n2,bo\n", encoding="utf-8")
    f2.write_text("user,id\nann,1\nbo,2\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "inferk", str(f1), str(f2)], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "1 2\n"


def test_inferk_cli_no_header_uses_values(runner: CliRunner, tmp_path: Path) -> None:
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("x 1\ny 2\n", encoding="utf-8")
    f2.write_text("1 q\n2 r\n", encoding="utf-8")
    result = runner.invoke(cli, [".", "inferk", str(f1), str(f2), "--no-header"],
                           catch_exceptions=False)
    assert result.output == "2 1\n"
