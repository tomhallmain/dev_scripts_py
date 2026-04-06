from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cd_without_search_prints_home(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", "/tmp/ds-home")
    monkeypatch.setenv("USERPROFILE", "/tmp/ds-home")
    result = runner.invoke(cli, [".", "cd"], catch_exceptions=False)
    assert result.exit_code == 0
    expected = str(Path("/tmp/ds-home").expanduser().resolve())
    assert result.output.strip() == expected


def test_cd_direct_directory_prints_absolute_path(tmp_path: Path, runner: CliRunner) -> None:
    target = tmp_path / "proj"
    target.mkdir()
    result = runner.invoke(cli, [".", "cd", str(target)], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == str(target.resolve())


def test_cd_search_uses_python_fallback_when_fd_unavailable(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "root"
    (root / "alpha").mkdir(parents=True)
    want = root / "beta_target"
    want.mkdir()
    monkeypatch.chdir(root)
    monkeypatch.setattr("scripts.tool_based_search.is_command_available", lambda _name: False)
    result = runner.invoke(cli, [".", "cd", "target"], catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == str(want.resolve())


def test_cd_multiple_matches_can_be_refined_by_pattern(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "root"
    (root / "app-one").mkdir(parents=True)
    target = root / "app-two"
    target.mkdir()
    monkeypatch.chdir(root)
    monkeypatch.setattr("scripts.tool_based_search.is_command_available", lambda _name: False)
    result = runner.invoke(cli, [".", "cd", "app"], input="two\n", catch_exceptions=False)
    assert result.exit_code == 0
    assert "Multiple matches found - select a directory:" in result.output
    assert result.output.strip().endswith(str(target.resolve()))
