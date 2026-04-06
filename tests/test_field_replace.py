from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_field_replace_only_replacement_expr_matches_shell_case(runner: CliRunner) -> None:
    input_data = "1:2:3:4:\n4:3:2:5:6\n::::\n4:6:2:4\n"
    expected = "11:2:3:4:\n-1:3:2:5:6\n11::::\n-1:6:2:4"
    r = runner.invoke(
        cli,
        [".", "field_replace", "val > 2 ? -1 : 11"],
        input=input_data,
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected


def test_field_replace_key_and_pattern_matches_shell_case(runner: CliRunner) -> None:
    input_data = "1:2:3:4:\n4:3:2:5:6\n::::\n4:6:2:4\n"
    expected = "1:11:3:4:\n4:-1:2:5:6\n::::\n4:-1:2:4"
    r = runner.invoke(
        cli,
        [".", "field_replace", "val > 2 ? -1 : 11", "--key", "2", "--pattern", "[0-9]"],
        input=input_data,
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == expected


def test_field_replace_file_input(tmp_path: Path, runner: CliRunner) -> None:
    p = tmp_path / "a.txt"
    p.write_text("1:2\n3:4\n", encoding="utf-8")
    r = runner.invoke(
        cli,
        [".", "field_replace", str(p), "val > 2 ? -1 : 11", "--key", "1", "--pattern", "[0-9]"],
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert r.output == "11:2\n-1:4"


def test_field_replace_invalid_key_fails(runner: CliRunner) -> None:
    r = runner.invoke(
        cli,
        [".", "field_replace", "val > 2 ? -1 : 11", "--key", "bad"],
        input="1:2\n",
        catch_exceptions=False,
    )
    assert r.exit_code != 0
    assert "Invalid value for '--key'" in r.output
