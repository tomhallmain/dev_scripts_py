from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from scripts.grep_edit import find_and_edit, grep_and_edit


def test_grep_and_edit_no_edit_prints_matches(tmp_path: Path, capsys) -> None:
    p = tmp_path / "a.txt"
    p.write_text("hello\nTODO item\nbye\n", encoding="utf-8")
    grep_and_edit("TODO", str(tmp_path), edit=False)
    out = capsys.readouterr().out
    assert "a.txt:2: TODO item" in out


def test_grep_and_edit_no_matches_prints_message(tmp_path: Path, capsys) -> None:
    p = tmp_path / "a.txt"
    p.write_text("hello\nworld\n", encoding="utf-8")
    grep_and_edit("TODO", str(tmp_path), edit=False)
    out = capsys.readouterr().out
    assert "No matches for 'TODO'" in out


@patch("scripts.grep_edit.subprocess.run")
def test_grep_and_edit_vim_opens_first_hit_line(
    mock_run, tmp_path: Path, monkeypatch
) -> None:
    p = tmp_path / "a.txt"
    p.write_text("x\nTODO one\nTODO two\n", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.tool_based_search.collect_search_hits",
        lambda *args, **kwargs: (0, {str(p): [(2, "TODO one"), (3, "TODO two")]}),
    )
    monkeypatch.setattr("scripts.grep_edit._resolve_editor", lambda: "vim")
    grep_and_edit("TODO", str(tmp_path), edit=True, print_matches=False)
    mock_run.assert_called_once_with(["vim", "+2", str(p)])


def test_find_and_edit_lists_matches_without_editor(tmp_path: Path, capsys) -> None:
    p = tmp_path / "target_file.py"
    p.write_text("print('x')\n", encoding="utf-8")
    find_and_edit("target", str(tmp_path), edit=False)
    out = capsys.readouterr().out
    assert str(p) in out
