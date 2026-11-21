"""Tests for build_exe.py's helpers; no Nuitka or build venv needed."""
import importlib.util
import json
import logging
import os
import subprocess
import sys
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
    assert "--onefile-tempdir-spec={CACHE_DIR}/dev_scripts_py/unpacked/dsp-20260101-120000" in args
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
    # Bundled from staging: the build info under build/nuitka/ is the last good build's.
    assert f"--include-data-files={build_exe.STAGED_BUILD_INFO}=build_info.json" in args
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
    monkeypatch.setattr(build_exe, "STAGING_DIR", str(tmp_path))
    monkeypatch.setattr(build_exe, "STAGED_BUILD_INFO", str(tmp_path / "build_info.json"))
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
    monkeypatch.setenv("DS_TEMP_DIR", "/real/tmp")
    monkeypatch.delenv("DS_SKIP_UNPACK_CLEANUP", raising=False)
    env = build_exe._smoke_test_env("/scratch")
    assert env["DS_CACHE_DIR"] == "/scratch"
    assert env["DS_TEMP_DIR"] == os.path.join("/scratch", "tmp")
    assert env["DS_SKIP_UNPACK_CLEANUP"] == "1"
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


# --- app-release contract: options, memory-wait plugin, Python version ---


@pytest.mark.parametrize("arg", ["--bump", "--bump=patch", "--no-build", "--no-upload", "--publish", "--force"])
def test_app_release_options_are_refused(build_exe, arg):
    with pytest.raises(SystemExit) as e:
        build_exe._refuse_app_release_options(["--jobs=4", arg])
    assert "app-release" in str(e.value.code)


def test_other_options_pass(build_exe):
    build_exe._refuse_app_release_options(["--jobs=4", "--show-scons", "--lock=x.txt", "--forced-x"])


def test_target_python_from_file(build_exe, tmp_path, monkeypatch):
    monkeypatch.setattr(build_exe, "REPO_ROOT", str(tmp_path))
    assert build_exe._target_python() is None
    (tmp_path / ".python-version").write_text("3.11\n")
    assert build_exe._target_python() == (3, 11)
    (tmp_path / ".python-version").write_text("3.11.9")
    assert build_exe._target_python() == (3, 11)
    (tmp_path / ".python-version").write_text("python3")
    with pytest.raises(SystemExit):
        build_exe._target_python()


def test_repo_python_version_is_3_11(build_exe):
    assert build_exe._target_python() == (3, 11)


def test_check_python(build_exe, caplog):
    build_exe._check_python((3, 11), version_info=(3, 11, 9))
    with pytest.raises(SystemExit) as e:
        build_exe._check_python((3, 11), version_info=(3, 12, 1))
    assert "3.11" in str(e.value.code) and "3.12" in str(e.value.code)
    with caplog.at_level(logging.WARNING, logger="build_exe"):
        build_exe._check_python(None, version_info=(3, 12, 1))
    assert any(".python-version" in m for m in caplog.messages)


@pytest.mark.parametrize("value", ["0", "2", "2.5"])
def test_min_free_memory_accepts(build_exe, value):
    assert build_exe._min_free_memory(value) == value


@pytest.mark.parametrize("value", ["-1", "lots", ""])
def test_min_free_memory_rejects(build_exe, value):
    with pytest.raises(SystemExit):
        build_exe._min_free_memory(value)


def test_min_free_memory_not_given(build_exe):
    assert build_exe._min_free_memory(None) is None


def test_nuitka_env_passes_min_free_memory(build_exe, monkeypatch):
    monkeypatch.delenv(build_exe.MIN_FREE_MEMORY_ENV, raising=False)
    assert build_exe.MIN_FREE_MEMORY_ENV not in build_exe._nuitka_env()
    assert build_exe._nuitka_env("3")[build_exe.MIN_FREE_MEMORY_ENV] == "3"


def test_user_plugin_only_with_a_plugin(build_exe):
    assert not any(a.startswith("--user-plugin=") for a in build_exe._nuitka_args("0.1.0", "id", []))
    args = build_exe._nuitka_args("0.1.0", "id", ["--jobs=4"], "/p/nuitka_memory_wait.py")
    assert "--user-plugin=/p/nuitka_memory_wait.py" in args
    assert args[-2:] == ["--jobs=4", build_exe.ENTRY]


class TestMemoryWait:
    """The lookup as app-release expects it (its app_requirements.md)."""

    @staticmethod
    def _no_tool(build_exe, monkeypatch, tools=None):
        """No variable, *tools* ({command: path}) as what shutil.which finds."""
        monkeypatch.delenv(build_exe.MEMORY_WAIT_PLUGIN_ENV, raising=False)
        monkeypatch.setattr(build_exe.shutil, "which", lambda name: (tools or {}).get(name))

    def test_the_variable_names_the_plugin(self, build_exe, monkeypatch, tmp_path):
        plugin = tmp_path / "nuitka_memory_wait.py"
        plugin.write_text("", encoding="utf-8")
        self._no_tool(build_exe, monkeypatch)
        monkeypatch.setenv(build_exe.MEMORY_WAIT_PLUGIN_ENV, str(plugin))
        assert build_exe._memory_wait_plugin() == str(plugin)

    def test_an_installed_tool_names_the_plugin(self, build_exe, monkeypatch, tmp_path):
        plugin = tmp_path / "nuitka_memory_wait.py"
        plugin.write_text("", encoding="utf-8")
        self._no_tool(build_exe, monkeypatch, tools={"app-release": "/bin/app-release"})
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, stdout=f"{plugin}\n", stderr="")

        monkeypatch.setattr(build_exe.subprocess, "run", fake_run)
        assert build_exe._memory_wait_plugin() == str(plugin)
        assert calls == [["/bin/app-release", "--memory-wait-plugin"]]

    def test_no_plugin_anywhere_builds_without_it(self, build_exe, monkeypatch, caplog):
        self._no_tool(build_exe, monkeypatch)
        with caplog.at_level("WARNING", logger="build_exe"):
            assert build_exe._memory_wait_plugin() is None
        assert any("app-release" in message for message in caplog.messages)

    def test_the_variable_is_the_one_the_plugin_reads(self, build_exe):
        # app-release's tests pin the plugin's side of this name.
        assert build_exe.MIN_FREE_MEMORY_ENV == "BUILD_MIN_FREE_MEMORY_GB"


def test_unpack_folder_matches_the_cleanup(build_exe):
    from scripts import unpack_cleanup

    spec = build_exe._pop_option(build_exe._nuitka_args("0.1.0", "20260101-120000", []),
                                 "--onefile-tempdir-spec")
    parent, folder = spec.split("/")[-2:]
    assert parent == unpack_cleanup.UNPACK_PARENT_NAME
    assert unpack_cleanup._is_unpack_dir(folder)
    assert build_exe.UNPACK_PREFIX == unpack_cleanup.UNPACK_DIR_PREFIX


def test_smoke_failure_names_the_exit_code_in_hex(build_exe, monkeypatch, caplog):
    monkeypatch.setattr(build_exe.subprocess, "run", _fake_run(_GOOD_OUTPUT, [], returncode=-1073740791))
    with caplog.at_level(logging.ERROR, logger="build_exe"), pytest.raises(SystemExit):
        build_exe._smoke_test("dsp", "0.1.0", "20260101-120000")
    assert any("0xc0000409" in m for m in caplog.messages)


# --- staging: build info and lock file move into place with a good build ---


@pytest.fixture
def build_tree(build_exe, tmp_path, monkeypatch):
    """build_exe's output paths moved into tmp_path; returns (build_dir, dist_dir)."""
    build_dir, dist_dir = tmp_path / "build" / "nuitka", tmp_path / "dist"
    staging = build_dir / "staging"
    for name, value in {
        "BUILD_DIR": build_dir, "DIST_DIR": dist_dir, "STAGING_DIR": staging,
        "BUILD_INFO_PATH": build_dir / "build_info.json",
        "LOCK_PATH": build_dir / "build-requirements.lock.txt",
        "STAGED_BUILD_INFO": staging / "build_info.json",
        "STAGED_LOCK": staging / "build-requirements.lock.txt",
    }.items():
        monkeypatch.setattr(build_exe, name, str(value))
    return build_dir, dist_dir


def test_lock_file_is_written_to_staging(build_exe, build_tree, monkeypatch):
    build_dir, _ = build_tree
    monkeypatch.setattr(build_exe.subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, "click==8.1.7\n", ""))
    build_exe._write_lock_file("python")
    assert (build_dir / "staging" / "build-requirements.lock.txt").read_text() == "click==8.1.7\n"
    assert not (build_dir / "build-requirements.lock.txt").exists()


def test_promote_moves_the_staged_files(build_exe, build_tree):
    build_dir, _ = build_tree
    staging = build_dir / "staging"
    staging.mkdir(parents=True)
    (staging / "build_info.json").write_text("new")
    (staging / "build-requirements.lock.txt").write_text("new lock")
    (build_dir / "build_info.json").write_text("old")
    build_exe._promote_build_record()
    assert (build_dir / "build_info.json").read_text() == "new"
    assert (build_dir / "build-requirements.lock.txt").read_text() == "new lock"
    assert not list(staging.iterdir())


def _fake_build(build_exe, monkeypatch, build_dir, calls, smoke_ok=True):
    """main() with every slow or external step replaced; *calls* records the order."""
    monkeypatch.setattr(build_exe, "_setup_logging", lambda build_id: "log")
    monkeypatch.setattr(build_exe, "_target_python", lambda: tuple(sys.version_info[:2]))
    monkeypatch.setattr(build_exe, "_ensure_build_venv", lambda requirements=None: "python")
    monkeypatch.setattr(build_exe, "_environment_versions",
                        lambda python: {"python": "3.11.9", "packages": {"click": "8.1.7"}})
    monkeypatch.setattr(build_exe, "_source_state", lambda: {"commit": "abc", "tree": "def", "changes": ""})
    monkeypatch.setattr(build_exe, "_memory_wait_plugin", lambda: "/p/plugin.py")

    def run(command, **kwargs):
        if "nuitka" in command:
            calls.append(("nuitka", command, kwargs.get("env", {})))
            (build_dir / build_exe.EXE_NAME).write_bytes(b"exe")
            return subprocess.CompletedProcess(command, 0, "", "")
        return subprocess.CompletedProcess(command, 0, "click==8.1.7\n", "")

    def smoke_test(exe_path, version, build_id):
        calls.append(("smoke", exe_path, os.path.exists(os.path.join(build_exe.DIST_DIR, build_exe.EXE_NAME))))
        if not smoke_ok:
            sys.exit("Smoke test failed: join of a file and stdin.")

    monkeypatch.setattr(build_exe.subprocess, "run", run)
    monkeypatch.setattr(build_exe, "_smoke_test", smoke_test)


def test_main_tests_before_dist_and_promotes_after(build_exe, build_tree, monkeypatch):
    build_dir, dist_dir = build_tree
    calls = []
    _fake_build(build_exe, monkeypatch, build_dir, calls)
    monkeypatch.setattr(sys, "argv", ["build_exe.py", "--min-free-memory=2", "--jobs=4"])
    build_exe.main()
    nuitka, smoke = calls
    assert "--user-plugin=/p/plugin.py" in nuitka[1] and "--jobs=4" in nuitka[1]
    assert nuitka[2][build_exe.MIN_FREE_MEMORY_ENV] == "2"
    assert smoke[1] == os.path.join(str(build_dir), build_exe.EXE_NAME)
    assert smoke[2] is False  # not yet in dist/ while it was tested
    assert (dist_dir / build_exe.EXE_NAME).read_bytes() == b"exe"
    info = json.loads((build_dir / "build_info.json").read_text(encoding="utf-8"))
    assert info["version"] == build_exe._app_version()
    assert (build_dir / "build-requirements.lock.txt").is_file()


def test_failed_smoke_test_keeps_the_previous_build(build_exe, build_tree, monkeypatch):
    build_dir, dist_dir = build_tree
    build_dir.mkdir(parents=True)
    (build_dir / "build_info.json").write_text("previous build")
    dist_dir.mkdir()
    (dist_dir / build_exe.EXE_NAME).write_bytes(b"previous exe")
    _fake_build(build_exe, monkeypatch, build_dir, [], smoke_ok=False)
    monkeypatch.setattr(sys, "argv", ["build_exe.py"])
    with pytest.raises(SystemExit):
        build_exe.main()
    assert (build_dir / "build_info.json").read_text() == "previous build"
    assert (dist_dir / build_exe.EXE_NAME).read_bytes() == b"previous exe"


def test_main_refuses_app_release_options_before_anything_else(build_exe, monkeypatch):
    monkeypatch.setattr(build_exe, "_app_version", lambda: pytest.fail("got past the option check"))
    monkeypatch.setattr(sys, "argv", ["build_exe.py", "--bump=patch"])
    with pytest.raises(SystemExit):
        build_exe.main()
