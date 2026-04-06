"""
Graph / DAG backtrace tests, adapted from dev_scripts/tests/t_graph.sh.

The original shell tests used ``FS=``: (colon-separated child/parent) and colon-separated
paths in the output. This port uses whitespace-separated fields on each line and
space-separated path strings from :func:`scripts.graph.extend`.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.DataFile import DataFile
from scripts.cli import cli
from scripts.graph import GraphDagBacktrace, run_graph


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# --- t_graph.sh parity (whitespace fields + space-separated paths) ---


def test_graph_base_case_non_bases() -> None:
    """t_graph: ``1 2`` … ``3 4`` | graph → single backtrace root chain."""
    out: list[str] = []
    code = GraphDagBacktrace(echo=out.append).run(["1 2\n", "2 3\n", "3 4\n"])
    assert code == 0
    assert out == ["4 3 2 1"]


def test_graph_print_bases_case_1() -> None:
    """t_graph: same edges with print_bases — root-only base line then chains per shoot."""
    out: list[str] = []
    code = GraphDagBacktrace(print_bases=True, echo=out.append).run(
        ["1 2\n", "2 3\n", "3 4\n"]
    )
    assert code == 0
    assert out == ["4", "4 3 2 1", "4 3 2", "4 3"]


def test_graph_print_bases_case_2() -> None:
    """t_graph: reversed chain ``2 1`` … ``4 3`` with print_bases."""
    out: list[str] = []
    code = GraphDagBacktrace(print_bases=True, echo=out.append).run(
        ["2 1\n", "3 2\n", "4 3\n"]
    )
    assert code == 0
    assert out == ["1", "1 2", "1 2 3", "1 2 3 4"]


def test_run_graph_consumes_data_file(tmp_path: Path) -> None:
    """``run_graph`` opens the file path from :class:`~scripts.DataFile.DataFile`."""
    p = tmp_path / "edges.txt"
    p.write_text("1 2\n2 3\n3 4\n", encoding="utf-8")
    df = DataFile(str(p))
    out: list[str] = []
    code = run_graph(df, echo=out.append)
    assert code == 0
    assert out == ["4 3 2 1"]


def test_graph_cycle_exits_nonzero() -> None:
    """Self-edge is a cycle when that shoot is processed (here: ``print_bases=True``)."""
    out: list[str] = []
    code = GraphDagBacktrace(print_bases=True, echo=out.append).run(["1 1\n"])
    assert code == 1
    assert any("WARNING" in line for line in out)
    assert any("CYCLENODE__ 1" in line for line in out)


def test_graph_cli_stdin_smoke(runner: CliRunner) -> None:
    """CLI pipes edges on stdin; output includes graph line (WIP banner may precede)."""
    result = runner.invoke(
        cli,
        [".", "graph"],
        input="1 2\n2 3\n3 4\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "4 3 2 1" in result.output


def test_graph_cli_optional_file(runner: CliRunner, tmp_path: Path) -> None:
    """Optional first positional file (TESTED_FIRST_ARG), same result as stdin."""
    p = tmp_path / "edges.txt"
    p.write_text("1 2\n2 3\n3 4\n", encoding="utf-8")
    result = runner.invoke(
        cli,
        [".", "graph", str(p)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "4 3 2 1" in result.output
