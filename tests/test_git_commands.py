from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "a.txt").write_text("alpha\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")


def _current_branch(repo: Path) -> str:
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def test_git_cross_view_on_temp_repo(runner: CliRunner, tmp_path: Path) -> None:
    repo = tmp_path / "repo1"
    _init_repo(repo)
    r = runner.invoke(cli, [".", "git_cross_view", str(tmp_path)], catch_exceptions=False)
    assert r.exit_code == 0
    lines = [ln for ln in r.output.splitlines() if ln.strip()]
    assert lines[0].startswith("repo\tbranch\tupstream")
    assert str(repo) in r.output


def test_git_diff_default_shows_unstaged_diff(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo2"
    _init_repo(repo)
    (repo / "a.txt").write_text("beta\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    r = runner.invoke(cli, [".", "git_diff"], catch_exceptions=False)
    assert r.exit_code == 0
    assert "diff --git" in r.output
    assert "-alpha" in r.output
    assert "+beta" in r.output


def test_git_recent_display_has_header_and_commit(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo3"
    _init_repo(repo)
    monkeypatch.chdir(repo)
    r = runner.invoke(cli, [".", "git_recent", "heads", "display"], catch_exceptions=False)
    assert r.exit_code == 0
    assert "branch\trelative_time\tsubject\tauthor" in r.output
    assert "initial" in r.output


def test_git_checkout_pattern_switches_branch(
    runner: CliRunner, tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo4"
    _init_repo(repo)
    base = _current_branch(repo)
    _git(repo, "checkout", "-b", "feature/add-tests")
    _git(repo, "checkout", base)
    monkeypatch.chdir(repo)
    r = runner.invoke(cli, [".", "git_checkout", "feature/add", "f"], catch_exceptions=False)
    assert r.exit_code == 0
    current = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert current == "feature/add-tests"


def test_git_status_and_git_branch_on_base_dir(runner: CliRunner, tmp_path: Path) -> None:
    repo = tmp_path / "repo_status_branch"
    _init_repo(repo)

    r_status = runner.invoke(cli, [".", "git_status", str(tmp_path)], catch_exceptions=False)
    assert r_status.exit_code == 0
    assert str(repo) in r_status.output

    r_branch = runner.invoke(cli, [".", "git_branch", str(tmp_path)], catch_exceptions=False)
    assert r_branch.exit_code == 0
    assert str(repo) in r_branch.output
    assert _current_branch(repo) in r_branch.output


def test_git_recent_all_lists_multiple_repos(runner: CliRunner, tmp_path: Path) -> None:
    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    _init_repo(repo_a)
    _init_repo(repo_b)
    r = runner.invoke(cli, [".", "git_recent_all", "heads", str(tmp_path)], catch_exceptions=False)
    assert r.exit_code == 0
    assert "repo\tbranch\tdate\trelative\thash\tsubject\tauthor" in r.output
    assert str(repo_a) in r.output
    assert str(repo_b) in r.output


def test_git_refresh_runs_on_local_repo_without_remote(runner: CliRunner, tmp_path: Path) -> None:
    repo = tmp_path / "repo_refresh"
    _init_repo(repo)
    r = runner.invoke(cli, [".", "git_refresh", str(tmp_path)], catch_exceptions=False)
    assert r.exit_code == 0
    assert str(repo) in r.output


def test_git_squash_yes_reduces_commit_count(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo_squash"
    _init_repo(repo)
    (repo / "b.txt").write_text("beta\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "second")
    (repo / "c.txt").write_text("gamma\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "third")
    monkeypatch.chdir(repo)
    before = int(_git(repo, "rev-list", "--count", "HEAD").stdout.strip())
    assert before >= 3
    r = runner.invoke(cli, [".", "git_squash", "2", "--yes"], catch_exceptions=False)
    assert r.exit_code == 0
    after = int(_git(repo, "rev-list", "--count", "HEAD").stdout.strip())
    assert after == before - 1


def test_git_branch_refs_merged_branch_visible(
    runner: CliRunner, tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo_refs"
    _init_repo(repo)
    base = _current_branch(repo)
    _git(repo, "checkout", "-b", "feature/refs")
    (repo / "c.txt").write_text("c\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feature commit")
    _git(repo, "checkout", base)
    _git(repo, "merge", "--no-ff", "feature/refs", "-m", "merge feature")
    monkeypatch.chdir(repo)
    r = runner.invoke(cli, [".", "git_branch_refs", base, "f"], catch_exceptions=False)
    assert r.exit_code == 0
    assert "Merged branches on" in r.output
    assert "feature/refs" in r.output


def test_git_cross_view_then_git_purge_local_sequence(
    runner: CliRunner, tmp_path: Path, monkeypatch
) -> None:
    repo_a = tmp_path / "repo_seq_a"
    repo_b = tmp_path / "repo_seq_b"
    _init_repo(repo_a)
    _init_repo(repo_b)
    base_a = _current_branch(repo_a)
    base_b = _current_branch(repo_b)
    _git(repo_a, "checkout", "-b", "old-feature")
    _git(repo_a, "checkout", base_a)
    _git(repo_b, "checkout", "-b", "old-feature")
    _git(repo_b, "checkout", base_b)

    # Run cross-view late in this scenario, immediately before purge.
    r_view = runner.invoke(cli, [".", "git_cross_view", str(tmp_path)], catch_exceptions=False)
    assert r_view.exit_code == 0
    assert str(repo_a) in r_view.output and str(repo_b) in r_view.output

    monkeypatch.chdir(tmp_path)
    r_purge = runner.invoke(
        cli,
        [".", "git_purge_local", str(tmp_path), "old-feature"],
        catch_exceptions=False,
    )
    assert r_purge.exit_code == 0

    branches_a = _git(repo_a, "branch", "--list").stdout
    branches_b = _git(repo_b, "branch", "--list").stdout
    assert "old-feature" not in branches_a
    assert "old-feature" not in branches_b
