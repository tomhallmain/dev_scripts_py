"""Text decoding/encoding is explicit UTF-8 regardless of the locale code page.

Each test feeds bytes that fail under both old behaviours: ``\\xc3\\x81`` (``Á``)
contains 0x81, which cp1252 (the Windows default) can't decode, and ``\\xff``
is invalid UTF-8, which a strict UTF-8 locale can't decode.
"""
from __future__ import annotations

import io
import os
import shlex
import subprocess
import sys
from pathlib import Path

from scripts import git_tools, simple_commands, tool_based_search
from scripts.DataFile import DataFile

PAYLOAD = b"caf\xc3\xa9 \xc3\x81 \xff"
DECODED = "caf\u00e9 \u00c1 \ufffd"


def _emit_bytes_argv(data: bytes) -> list[str]:
    """argv for a Python child that writes ``data`` to stdout unmodified."""
    return [sys.executable, "-c", f"import sys; sys.stdout.buffer.write(bytes.fromhex('{data.hex()}'))"]


def _shell_cmd(argv: list[str]) -> str:
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def _replace_subprocess_command(monkeypatch, argv: list[str]) -> list:
    """Run ``argv`` in place of whatever command the code under test starts,
    keeping its other ``subprocess.run`` arguments (and so its decoding)."""
    real_run = subprocess.run
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


# ---------------------------------------------------------------------------
# DataFile
# ---------------------------------------------------------------------------

def test_datafile_read_decodes_utf8_and_replaces_invalid_bytes(tmp_path):
    path = tmp_path / "data.txt"
    path.write_bytes(PAYLOAD + b"\nsecond\n")

    df = DataFile(str(path))  # counts rows through read()

    assert df.n_rows == 2
    with df.read() as f:
        assert f.read() == DECODED + "\nsecond\n"


def test_datafile_piped_stdin_temp_file_is_utf8(monkeypatch):
    # "\udcff" is how an undecodable stdin byte arrives under surrogateescape.
    monkeypatch.setattr(sys, "stdin", io.StringIO("caf\u00e9 \u00c1\nbad \udcff\n"))

    df = DataFile(None)
    try:
        assert df.n_rows == 2
        written = Path(df.file_path).read_bytes().replace(b"\r\n", b"\n")
        assert written == "caf\u00e9 \u00c1\nbad \\udcff\n".encode("utf-8")
        with df.read() as f:
            assert f.read() == "caf\u00e9 \u00c1\nbad \\udcff\n"
    finally:
        df.cleanup_temp_file()


# ---------------------------------------------------------------------------
# subprocess output decoding
# ---------------------------------------------------------------------------

def test_rg_scan_decodes_output_as_utf8(monkeypatch):
    monkeypatch.setattr(tool_based_search.shutil, "which", lambda name: "rg")
    calls = _replace_subprocess_command(monkeypatch, _emit_bytes_argv(b"f.txt:" + PAYLOAD + b"\n"))

    code, lines = tool_based_search._rg_scan(("f.txt",), "caf")

    assert calls, "expected rg to be invoked"
    assert code == 0
    assert lines == ["f.txt:" + DECODED]


def test_rg_scan_hits_decodes_output_as_utf8(monkeypatch):
    monkeypatch.setattr(tool_based_search.shutil, "which", lambda name: "rg")
    calls = _replace_subprocess_command(monkeypatch, _emit_bytes_argv(b"f.txt:3:" + PAYLOAD + b"\n"))

    code, hits = tool_based_search._rg_scan_hits(("f.txt",), "caf")

    assert calls, "expected rg to be invoked"
    assert code == 0
    assert hits == {"f.txt": [(3, DECODED)]}


def test_fd_directory_search_decodes_output_as_utf8(monkeypatch):
    calls = _replace_subprocess_command(monkeypatch, _emit_bytes_argv(PAYLOAD + b"\n"))

    dirs = tool_based_search._search_dirs_with_fd("caf", "fd", max_results=10)

    assert calls, "expected fd to be invoked"
    assert dirs == [tool_based_search._normalize_path(DECODED)]


def test_run_git_decodes_output_as_utf8(monkeypatch, tmp_path):
    calls = _replace_subprocess_command(monkeypatch, _emit_bytes_argv(PAYLOAD + b"\n"))

    result = git_tools.run_git(["log"], cwd=str(tmp_path))

    assert calls[0] == ["git", "log"]
    assert result.stdout == DECODED + "\n"


def test_line_cmd_decodes_per_line_command_output_as_utf8(capsys):
    line_cmds = _shell_cmd(_emit_bytes_argv(PAYLOAD + b"\n"))

    simple_commands.line_cmd(None, line_cmds, "", "only-line\n")

    assert capsys.readouterr().out == DECODED + "\n"


def test_line_cmd_decodes_seed_command_output_as_utf8(capsys):
    seed_cmds = _shell_cmd(_emit_bytes_argv(PAYLOAD + b"\n"))
    # line_cmd exposes each seed line to the per-line command as $line.
    echo_line = _shell_cmd([
        sys.executable, "-c",
        "import os, sys; sys.stdout.buffer.write(os.environ['line'].encode('utf-8'))",
    ])

    simple_commands.line_cmd(seed_cmds, echo_line, "", None)

    assert capsys.readouterr().out == DECODED
