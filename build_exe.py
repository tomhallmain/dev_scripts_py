"""
Build the standalone ``ds`` executable with Nuitka: ``python build_exe.py``.

Nuitka compiles the code to C, then to a single native executable that embeds
the Python runtime. Needs a C compiler: Xcode Command Line Tools on macOS; on
Windows, Visual Studio Build Tools, or Nuitka downloads MinGW itself. Nuitka
does not cross-compile, so run this on each target OS.

Builds inside a dedicated ``.venv-build`` at the repo root, populated from
requirements-build.txt, so packages from the active conda env or venv aren't
bundled. The venv is based on the interpreter running this script, and the exe
embeds that interpreter's runtime. ``--current-env`` builds with the running
interpreter instead; it must already have requirements-build.txt installed.

The output, dist/ds (macOS/Linux) or dist\\ds.exe (Windows), is smoke-tested
with ``ds commands``. Other args are forwarded to Nuitka, e.g. ``--show-scons``.
"""
import os
import shutil
import subprocess
import sys
import time
import venv

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(REPO_ROOT, ".venv-build")
ENTRY = os.path.join(REPO_ROOT, "ds_entry.py")
BUILD_DIR = os.path.join(REPO_ROOT, "build", "nuitka")
EXE_NAME = "ds.exe" if sys.platform == "win32" else "ds"
EXE_PATH = os.path.join(REPO_ROOT, "dist", EXE_NAME)


def _venv_python(venv_dir: str) -> str:
    if sys.platform == "win32":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def _ensure_build_venv() -> str:
    python = _venv_python(VENV_DIR)
    if not os.path.exists(python):
        print(f"Creating build venv at {VENV_DIR}")
        venv.create(VENV_DIR, with_pip=True)
    subprocess.run(
        [python, "-m", "pip", "install", "-q", "-r", os.path.join(REPO_ROOT, "requirements-build.txt")],
        check=True,
    )
    return python


def _nuitka_args(extra_args) -> list:
    # The onefile exe unpacks its runtime to this folder. A fixed path (no
    # {PID}/{TIME}) makes Nuitka keep it between runs, so only the first run
    # pays the unpacking cost. The build id gives each build its own folder so
    # a rebuilt exe never reuses a previous build's files; old folders under
    # the user cache dir's dev_scripts_py/ are safe to delete.
    build_id = time.strftime("%Y%m%d-%H%M%S")
    return [
        "--onefile",
        f"--onefile-tempdir-spec={{CACHE_DIR}}/dev_scripts_py/ds-{build_id}",
        f"--output-dir={BUILD_DIR}",
        f"--output-filename={EXE_NAME}",
        # Lets Nuitka fetch build helpers (e.g. MinGW on Windows) without prompting.
        "--assume-yes-for-downloads",
        *extra_args,
        ENTRY,
    ]


def _smoke_test() -> None:
    # Run from outside the repo so a passing test can't depend on the checkout.
    result = subprocess.run(
        [EXE_PATH, "commands"], cwd=os.path.expanduser("~"), capture_output=True, text=True, errors="replace",
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        sys.exit(f"Smoke test failed: `{EXE_PATH} commands` exited {result.returncode}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--current-env" in args:
        args.remove("--current-env")
        python = sys.executable
    else:
        python = _ensure_build_venv()

    subprocess.run([python, "-m", "nuitka"] + _nuitka_args(args), cwd=REPO_ROOT, check=True)
    os.makedirs(os.path.dirname(EXE_PATH), exist_ok=True)
    shutil.copy2(os.path.join(BUILD_DIR, EXE_NAME), EXE_PATH)
    _smoke_test()
    print(f"Built {EXE_PATH}")
