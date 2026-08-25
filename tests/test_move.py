"""Tests for ``ds move`` / ``ds copy`` (parity with the original bash ``ds:mv`` / ``ds:copy`` cases).

``move_main`` prompts once for confirmation below its 20-file threshold, so each invocation
feeds ``"y\\n"`` on stdin the way the shell cases piped ``printf 'y\\n'``.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_copy_tag_filter_flattens_into_existing_target(runner: CliRunner, tmp_path: Path) -> None:
    """``[video]`` tag filter pulls nested matches into an existing target; source is left intact."""
    src = tmp_path / "copy_src"
    dst = tmp_path / "copy_dst"
    _write(src / "a.mp4", "v1\n")
    _write(src / "sub" / "b.mp4", "v2\n")
    _write(src / "notes.txt", "t1\n")
    dst.mkdir()

    r = runner.invoke(
        cli, [".", "copy", str(src), str(dst), "--filter", "[video]"], input="y\n"
    )
    assert r.exit_code == 0

    assert (dst / "a.mp4").is_file()
    assert (dst / "b.mp4").is_file()
    assert not (dst / "notes.txt").exists()
    # copy must not remove the source
    assert (src / "a.mp4").is_file()
    assert (dst / "a.mp4").read_text(encoding="utf-8") == "v1\n"


def test_copy_glob_filter(runner: CliRunner, tmp_path: Path) -> None:
    src = tmp_path / "glob_src"
    dst = tmp_path / "glob_dst"
    _write(src / "keep.log", "x\n")
    _write(src / "skip.csv", "y\n")

    r = runner.invoke(
        cli, [".", "copy", str(src), str(dst), "--filter", "*.log"], input="y\n"
    )
    assert r.exit_code == 0
    assert (dst / "keep.log").is_file()
    assert not (dst / "skip.csv").exists()


def test_copy_bare_extension_filter(runner: CliRunner, tmp_path: Path) -> None:
    src = tmp_path / "ext_src"
    dst = tmp_path / "ext_dst"
    _write(src / "keep.csv", "x\n")
    _write(src / "skip.tsv", "y\n")

    r = runner.invoke(
        cli, [".", "copy", str(src), str(dst), "--filter", ".csv"], input="y\n"
    )
    assert r.exit_code == 0
    assert (dst / "keep.csv").is_file()
    assert not (dst / "skip.tsv").exists()


def test_move_single_file_renames_and_removes_source(runner: CliRunner, tmp_path: Path) -> None:
    src = tmp_path / "single.txt"
    dst = tmp_path / "renamed.txt"
    _write(src, "hello\n")

    r = runner.invoke(cli, [".", "move", str(src), str(dst)], input="y\n")
    assert r.exit_code == 0
    assert dst.is_file()
    assert not src.exists()
    assert dst.read_text(encoding="utf-8") == "hello\n"


def test_move_flatten_in_place(runner: CliRunner, tmp_path: Path) -> None:
    """source dir == target dir pulls nested matches to the root, leaving root files alone."""
    flat = tmp_path / "flat"
    _write(flat / "root.mp4", "a\n")
    _write(flat / "inner" / "deep.mp4", "b\n")

    r = runner.invoke(
        cli, [".", "move", str(flat), str(flat), "--filter", "[video]"], input="y\n"
    )
    assert r.exit_code == 0
    assert (flat / "deep.mp4").is_file()
    assert (flat / "root.mp4").is_file()
    assert not (flat / "inner" / "deep.mp4").exists()


def test_copy_no_filter_matches_leaves_target_uncreated(runner: CliRunner, tmp_path: Path) -> None:
    """No file matches the filter: nothing is created and the source is untouched."""
    src = tmp_path / "nomatch_src"
    dst = tmp_path / "nomatch_dst"
    _write(src / "only.txt", "x\n")

    r = runner.invoke(
        cli, [".", "copy", str(src), str(dst), "--filter", "[video]"], input="y\n"
    )
    assert not dst.exists()
    assert (src / "only.txt").is_file()


def test_move_declined_confirmation_makes_no_change(runner: CliRunner, tmp_path: Path) -> None:
    """Answering anything other than y/empty at the prompt cancels before touching the source."""
    src = tmp_path / "keep_src"
    dst = tmp_path / "keep_dst"
    _write(src / "a.mp4", "v1\n")

    r = runner.invoke(
        cli, [".", "move", str(src), str(dst), "--filter", "[video]"], input="n\n"
    )
    assert (src / "a.mp4").is_file()
    assert not (dst / "a.mp4").exists()
