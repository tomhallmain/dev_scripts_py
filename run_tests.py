"""
Convenience entry point for the full test suite: ``python run_tests.py``.

Self-provisioning: if no virtual environment is active (venv or conda) when this
runs, creates/reuses a ``.venv`` at the repo root, installs requirements.txt into
it, and runs pytest through that interpreter directly -- the portable equivalent
of "activate the venv, then run tests", without needing a separate shell/batch
script to do the activating. If a venv or conda env is already active, that one
is used as-is; nothing is created. No conda env is required either way.

Any extra CLI args are forwarded to pytest, e.g.:

    python run_tests.py -k join -v
"""
import os
import subprocess
import sys
import venv

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(REPO_ROOT, ".venv")
TESTS_DIR = os.path.join(REPO_ROOT, "tests")


def _in_virtual_env() -> bool:
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    in_conda = bool(os.environ.get("CONDA_DEFAULT_ENV"))
    return in_venv or in_conda


def _venv_python(venv_dir: str) -> str:
    if sys.platform == "win32":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def _ensure_venv_python() -> str:
    python = _venv_python(VENV_DIR)
    if not os.path.exists(python):
        print(f"No active venv/conda env found -- creating one at {VENV_DIR}")
        venv.create(VENV_DIR, with_pip=True)
    subprocess.run(
        [python, "-m", "pip", "install", "-q", "-r", os.path.join(REPO_ROOT, "requirements.txt")],
        check=True,
    )
    return python


if __name__ == "__main__":
    if _in_virtual_env():
        import pytest
        sys.exit(pytest.main([TESTS_DIR] + sys.argv[1:]))

    python = _ensure_venv_python()
    result = subprocess.run([python, "-m", "pytest", TESTS_DIR] + sys.argv[1:])
    sys.exit(result.returncode)
