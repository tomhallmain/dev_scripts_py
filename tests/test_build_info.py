"""Tests for scripts/build_info.py and ``ds version``."""
import json

import pytest
from click.testing import CliRunner

from scripts import build_info
from scripts.cli import cli


@pytest.fixture
def resource_root(tmp_path, monkeypatch):
    monkeypatch.setattr(build_info, "RESOURCE_ROOT", str(tmp_path))
    return tmp_path


def _write_build_info(root, **overrides):
    info = {
        "version": "0.1.0",
        "build_id": "20260101-120000",
        "python": "3.12.1",
        "packages": {"click": "8.1.7", "Nuitka": "4.2.2"},
        "source": {"commit": "0123456789abcdef", "tree": "fedcba", "changes": ""},
    }
    info.update(overrides)
    (root / "build_info.json").write_text(json.dumps(info), encoding="utf-8")


def test_repo_has_version():
    assert build_info.app_version()


def test_source_checkout(resource_root):
    (resource_root / "VERSION").write_text("0.1.0\n")
    assert build_info.build_info() is None
    assert build_info.describe() == "ds 0.1.0 (source checkout)"


def test_build(resource_root):
    (resource_root / "VERSION").write_text("0.1.0\n")
    _write_build_info(resource_root)
    assert build_info.describe().splitlines() == [
        "ds 0.1.0",
        "Build 20260101-120000 from 0123456789",
        "Python 3.12.1; Nuitka 4.2.2, click 8.1.7",
    ]


@pytest.mark.parametrize("changes, suffix", [
    ("abc", " with uncommitted changes"),
    (None, " (uncommitted changes unknown)"),
])
def test_build_change_state(resource_root, changes, suffix):
    (resource_root / "VERSION").write_text("0.1.0\n")
    _write_build_info(resource_root, source={"commit": "0123456789abcdef", "changes": changes})
    assert build_info.describe().splitlines()[1] == f"Build 20260101-120000 from 0123456789{suffix}"


def test_missing_version_and_bad_build_info_do_not_raise(resource_root):
    (resource_root / "build_info.json").write_text("{not json", encoding="utf-8")
    lines = build_info.describe().splitlines()
    assert lines[0].startswith("ds (version unreadable:")
    assert lines[1].startswith("Build info unreadable:")


def test_version_command():
    r = CliRunner().invoke(cli, [".", "version"], catch_exceptions=False)
    assert r.exit_code == 0
    assert r.output.startswith(f"ds {build_info.app_version()}")
