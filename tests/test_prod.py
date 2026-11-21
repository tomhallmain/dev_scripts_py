"""``ds prod`` tests: product multiset of the lines of several inputs."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli
from scripts.product import product_lines


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _write(tmp_path: Path, name: str, text: str) -> str:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_product_lines_order_first_set_slowest() -> None:
    assert list(product_lines([["a", "b"], ["1", "2"]])) == ["a 1", "a 2", "b 1", "b 2"]


def test_product_lines_empty_set_gives_nothing() -> None:
    assert list(product_lines([["a"], []])) == []


def test_prod_two_files(runner: CliRunner, tmp_path: Path) -> None:
    f1 = _write(tmp_path, "a.txt", "a\nb\n")
    f2 = _write(tmp_path, "b.txt", "1\n2\n")
    result = runner.invoke(cli, [".", "prod", f1, f2], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "a 1\na 2\nb 1\nb 2\n"


def test_prod_three_sets_keeps_line_whitespace(runner: CliRunner, tmp_path: Path) -> None:
    f1 = _write(tmp_path, "a.txt", " x\n")
    f2 = _write(tmp_path, "b.txt", "1\n2\n")
    f3 = _write(tmp_path, "c.txt", "z\n")
    result = runner.invoke(cli, [".", "prod", f1, f2, f3], catch_exceptions=False)
    assert result.output == " x 1 z\n x 2 z\n"


def test_prod_same_file_twice_is_self_product(runner: CliRunner, tmp_path: Path) -> None:
    f1 = _write(tmp_path, "a.txt", "a\nb\n")
    result = runner.invoke(cli, [".", "prod", f1, f1], catch_exceptions=False)
    assert result.output == "a a\na b\nb a\nb b\n"


def test_prod_stdin_is_first_set(runner: CliRunner, tmp_path: Path) -> None:
    f2 = _write(tmp_path, "b.txt", "1\n")
    result = runner.invoke(cli, [".", "prod", f2], input="a\nb\n", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output == "a 1\nb 1\n"


def test_prod_missing_file_errors(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(cli, [".", "prod", str(tmp_path / "nope.txt")])
    assert result.exit_code != 0
    assert "not a file" in result.output
