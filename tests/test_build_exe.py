"""Tests for build_exe.py's helpers; no Nuitka or build venv needed."""
import importlib.util
import json
import logging
import os
import subprocess
from pathlib import Path

import pytest

_BUILD_EXE = Path(__file__).resolve().parents[1] / "build_exe.py"


@pytest.fixture
def build_exe():
    # Loaded by path as a fresh module, so monkeypatching its globals affects
    # the functions that read them.
    spec = importlib.util.spec_from_file_location("build_exe", _BUILD_EXE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("seconds, expected", [
    (0, "0s"),
    (59.4, "59s"),
    (60, "1m 00s"),
    (3599, "59m 59s"),
    (3600, "1h 00m 00s"),
    (3725, "1h 02m 05s"),
])
def test_duration(build_exe, seconds, expected):
    assert build_exe._duration(seconds) == expected


def test_timed_logs_success(build_exe, caplog):
    with caplog.at_level(logging.INFO, logger="build_exe"):
        with build_exe._timed("Step"):
            pass
    assert [r.getMessage() for r in caplog.records] == ["Step...", "Step done in 0s"]


def test_timed_logs_failure_and_reraises(build_exe, caplog):
    with caplog.at_level(logging.INFO, logger="build_exe"):
        with pytest.raises(RuntimeError):
            with build_exe._timed("Step"):
                raise RuntimeError("boom")
    assert caplog.records[-1].levelno == logging.ERROR
    assert caplog.records[-1].getMessage() == "Step failed after 0s"


def test_unpack_folder_is_per_build_under_unpacked(build_exe):
    args = build_exe._nuitka_args("0.1.0", "20260101-120000", ["--show-scons"])
    assert "--onefile-tempdir-spec={CACHE_DIR}/dev_scripts_py/unpacked/ds-20260101-120000" in args
    assert args[-2:] == ["--show-scons", build_exe.ENTRY]


def test_no_docstring_stripping(build_exe):
    # click docstrings are the CLI's help text.
    args = build_exe._nuitka_args("0.1.0", "id", [])
    assert not any("no_docstrings" in a or a == "-OO" for a in args)


def test_copy_to_dist_replaces_folder_build(build_exe, tmp_path, monkeypatch):
    build_dir, dist_dir = tmp_path / "build", tmp_path / "dist"
    build_dir.mkdir()
    (build_dir / "ds").write_bytes(b"new exe")
    (dist_dir / "ds").mkdir(parents=True)
    (dist_dir / "ds" / "leftover").write_text("old folder build")
    monkeypatch.setattr(build_exe, "BUILD_DIR", str(build_dir))
    monkeypatch.setattr(build_exe, "DIST_DIR", str(dist_dir))

    path = build_exe._copy_to_dist("ds")

    assert Path(path) == dist_dir / "ds"
    assert (dist_dir / "ds").read_bytes() == b"new exe"


def test_copy_to_dist_creates_dist(build_exe, tmp_path, monkeypatch):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "ds.exe").write_bytes(b"exe")
    monkeypatch.setattr(build_exe, "BUILD_DIR", str(build_dir))
    monkeypatch.setattr(build_exe, "DIST_DIR", str(tmp_path / "dist"))

    assert (Path(build_exe._copy_to_dist("ds.exe"))).read_bytes() == b"exe"


def test_version_info_and_bundled_files(build_exe):
    args = build_exe._nuitka_args("1.2.3", "20260101-120000", [])
    assert "--product-version=1.2.3" in args
    assert "--file-version=1.2.3" in args
    assert any(a.startswith("--file-description=") and a.endswith("build 20260101-120000") for a in args)
    assert f"--include-data-files={build_exe.BUILD_INFO_PATH}=build_info.json" in args
    assert any(a.startswith("--include-data-files=") and a.endswith("=VERSION") for a in args)


def test_repo_version_file_is_valid(build_exe):
    assert build_exe._app_version()


@pytest.mark.parametrize("content", ["1.0.0\n", "2\n", "1.2.3.4"])
def test_app_version_accepts(build_exe, tmp_path, monkeypatch, content):
    (tmp_path / "VERSION").write_text(content)
    monkeypatch.setattr(build_exe, "REPO_ROOT", str(tmp_path))
    assert build_exe._app_version() == content.strip()


@pytest.mark.parametrize("content", ["", "v1.0", "1.0.0-beta", "1.2.3.4.5"])
def test_app_version_rejects(build_exe, tmp_path, monkeypatch, content):
    (tmp_path / "VERSION").write_text(content)
    monkeypatch.setattr(build_exe, "REPO_ROOT", str(tmp_path))
    with pytest.raises(SystemExit):
        build_exe._app_version()


def test_app_version_missing_file(build_exe, tmp_path, monkeypatch):
    monkeypatch.setattr(build_exe, "REPO_ROOT", str(tmp_path))
    with pytest.raises(SystemExit):
        build_exe._app_version()


def test_pop_option(build_exe):
    args = ["--jobs=4", "--lock=a=b.txt", "--show-scons"]
    assert build_exe._pop_option(args, "--lock") == "a=b.txt"
    assert args == ["--jobs=4", "--show-scons"]
    assert build_exe._pop_option(args, "--lock") is None


def _fake_git(outputs):
    def git(*args):
        return outputs.get(args)
    return git


def test_source_state_clean(build_exe, monkeypatch):
    monkeypatch.setattr(build_exe, "_git", _fake_git({
        ("rev-parse", "HEAD"): b"abc123\n",
        ("rev-parse", "HEAD^{tree}"): b"def456\n",
        ("diff", "HEAD", "--binary"): b"",
    }))
    assert build_exe._source_state() == {"commit": "abc123", "tree": "def456", "changes": ""}


def test_source_state_with_changes(build_exe, monkeypatch):
    monkeypatch.setattr(build_exe, "_git", _fake_git({
        ("rev-parse", "HEAD"): b"abc123\n",
        ("rev-parse", "HEAD^{tree}"): b"def456\n",
        ("diff", "HEAD", "--binary"): b"diff --git a/x b/x\n\xff\n",
    }))
    changes = build_exe._source_state()["changes"]
    assert changes and len(changes) == 40


def test_source_state_without_git(build_exe, monkeypatch):
    monkeypatch.setattr(build_exe, "_git", _fake_git({}))
    assert build_exe._source_state() == {"commit": "", "tree": "", "changes": None}


def test_write_build_info(build_exe, tmp_path, monkeypatch):
    monkeypatch.setattr(build_exe, "BUILD_DIR", str(tmp_path))
    monkeypatch.setattr(build_exe, "BUILD_INFO_PATH", str(tmp_path / "build_info.json"))
    monkeypatch.setattr(build_exe, "_source_state", lambda: {"commit": "abc", "tree": "def", "changes": ""})
    environment = {"python": "3.12.1", "packages": {"click": "8.1.7", "pywin32": None}}

    build_exe._write_build_info("0.1.0", "20260101-120000", environment)

    info = json.loads((tmp_path / "build_info.json").read_text(encoding="utf-8"))
    assert info == {
        "version": "0.1.0",
        "build_id": "20260101-120000",
        "python": "3.12.1",
        "packages": {"click": "8.1.7"},
        "source": {"commit": "abc", "tree": "def", "changes": ""},
    }


def test_smoke_test_env_overrides_shell_values(build_exe, monkeypatch):
    monkeypatch.setenv("DS_CACHE_DIR", "/real/user/cache")
    monkeypatch.setenv("DS_REFRESH_TOOL_CACHE", "1")
    env = build_exe._smoke_test_env("/scratch")
    assert env["DS_CACHE_DIR"] == "/scratch"
    assert "DS_REFRESH_TOOL_CACHE" not in env


def test_smoke_join_fixture_exists(build_exe):
    assert Path(build_exe.SMOKE_JOIN_FIXTURE).is_file()


_GOOD_OUTPUT = {
    "commands": "  commands  List all available commands.\n"
                "  version  Show the ds version, and for a standalone build its build details.\n",
    "version": "ds 0.1.0\nBuild 20260101-120000 from 0123456789\nPython 3.12.1\n",
    "join": "a b c d b c\n1 2 3 4 3 2\n",
}


def _checks(build_exe):
    return {args[0]: check for _, args, _, check in build_exe._smoke_checks("0.1.0", "20260101-120000")}


def test_smoke_checks_accept_good_output(build_exe):
    for command, check in _checks(build_exe).items():
        assert check(_GOOD_OUTPUT[command]) is None, command


@pytest.mark.parametrize("command, output", [
    ("commands", "  version\n"),
    ("version", "ds 0.0.9\nBuild 20260101-120000 from x\n"),
    ("version", "ds 0.1.0 (source checkout)\n"),
    ("version", "ds 0.1.0\nBuild 20250101-000000 from x\n"),
    ("join", "a b c d\n"),
])
def test_smoke_checks_reject_bad_output(build_exe, command, output):
    assert _checks(build_exe)[command](output)


def _fake_run(outputs, calls, returncode=0):
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, returncode, outputs.get(command[1], ""), "")
    return run


def test_smoke_test_passes(build_exe, monkeypatch):
    calls = []
    monkeypatch.setattr(build_exe.subprocess, "run", _fake_run(_GOOD_OUTPUT, calls))
    build_exe._smoke_test("ds", "0.1.0", "20260101-120000")
    assert [c[0][1] for c in calls] == ["commands", "version", "join"]
    for _, kwargs in calls:
        assert kwargs["cwd"] == os.path.expanduser("~")
        assert kwargs["env"]["DS_CACHE_DIR"] != os.environ.get("DS_CACHE_DIR")


def test_smoke_test_reports_every_failure(build_exe, monkeypatch):
    outputs = dict(_GOOD_OUTPUT, version="ds 0.0.1\n", join="")
    monkeypatch.setattr(build_exe.subprocess, "run", _fake_run(outputs, []))
    with pytest.raises(SystemExit) as e:
        build_exe._smoke_test("ds", "0.1.0", "20260101-120000")
    assert e.value.code == "Smoke test failed: version and build info, join of a file and stdin."


def test_smoke_test_fails_on_exit_code(build_exe, monkeypatch):
    monkeypatch.setattr(build_exe.subprocess, "run", _fake_run(_GOOD_OUTPUT, [], returncode=1))
    with pytest.raises(SystemExit):
        build_exe._smoke_test("ds", "0.1.0", "20260101-120000")
