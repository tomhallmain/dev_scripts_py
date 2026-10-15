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
from the home directory with its tool cache in a scratch directory: ``ds
commands`` (help text present), ``ds version`` (bundled VERSION and build
info) and a join of a test fixture with stdin. At its first start the exe unpacks its runtime to
``dev_scripts_py/unpacked/ds-<build id>`` in the user cache dir; later starts
of the same build reuse that folder. Each step is timed, and the log goes to
``build/logs/build_exe-<build id>.log`` as well (Nuitka's own output only to
the console). Other args are forwarded to Nuitka, e.g. ``--show-scons``.

The exe's version information comes from the VERSION file at the repo root,
with the build id (build time) in its description. Each build writes
``build/nuitka/build_info.json`` (version, build id, Python and key package
versions, and this checkout's commit, the commit's tree and a fingerprint of
its uncommitted changes), bundled with VERSION so ``ds version`` can show
them, and ``build/nuitka/build-requirements.lock.txt``, the build venv's
``pip freeze``. ``--lock=<file>`` installs the build venv from such a file
instead of requirements-build.txt, to repeat a known good build; packages
already in the venv but absent from the file stay installed, so delete
.venv-build first for an exact copy.
"""
import contextlib
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import venv

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(REPO_ROOT, ".venv-build")
ENTRY = os.path.join(REPO_ROOT, "ds_entry.py")
BUILD_DIR = os.path.join(REPO_ROOT, "build", "nuitka")
DIST_DIR = os.path.join(REPO_ROOT, "dist")
LOG_DIR = os.path.join(REPO_ROOT, "build", "logs")
EXE_NAME = "ds.exe" if sys.platform == "win32" else "ds"
# Nuitka's {CACHE_DIR} is %LOCALAPPDATA% on Windows and ~/.cache elsewhere,
# the same base scripts/tool_availability.py caches under.
APP_CACHE_SPEC = "{CACHE_DIR}/dev_scripts_py"
VERSION_FILE = "VERSION"
SMOKE_JOIN_FIXTURE = os.path.join(REPO_ROOT, "tests", "data", "tmp_join")
# Both bundled at the resource root, where scripts/build_info.py reads them.
BUILD_INFO_PATH = os.path.join(BUILD_DIR, "build_info.json")
LOCK_PATH = os.path.join(BUILD_DIR, "build-requirements.lock.txt")
# Versions the build output and build_info.json record.
RECORDED_DISTRIBUTIONS = ("Nuitka", "click", "termcolor", "pywin32", "zstandard")
# Prints {"python": ..., "packages": {name: version}} for the names in argv.
_VERSIONS_PROBE = (
    "import json, sys\n"
    "from importlib.metadata import PackageNotFoundError, version\n"
    "def get(name):\n"
    "    try:\n"
    "        return version(name)\n"
    "    except PackageNotFoundError:\n"
    "        return None\n"
    "print(json.dumps({'python': sys.version.split()[0],\n"
    "                  'packages': {n: get(n) for n in sys.argv[1:]}}))\n"
)

logger = logging.getLogger("build_exe")


class _LevelPrefix(logging.Filter):
    def filter(self, record):
        record.level_prefix = "" if record.levelno == logging.INFO else f"{record.levelname}: "
        return True


def _setup_logging(build_id: str) -> str:
    """Log to the console and to a file for this build; returns the file's path."""
    os.makedirs(LOG_DIR, exist_ok=True)
    path = os.path.join(LOG_DIR, f"build_exe-{build_id}.log")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("[%(asctime)s] %(level_prefix)s%(message)s", "%H:%M:%S"))
    log_file = logging.FileHandler(path, encoding="utf-8")
    log_file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    for handler in (console, log_file):
        handler.addFilter(_LevelPrefix())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return path


def _duration(seconds: float) -> str:
    seconds = int(round(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


@contextlib.contextmanager
def _timed(step: str):
    """Log how long *step* took, or after how long it failed."""
    started = time.monotonic()
    logger.info(f"{step}...")
    try:
        yield
    except BaseException:
        logger.error(f"{step} failed after {_duration(time.monotonic() - started)}")
        raise
    logger.info(f"{step} done in {_duration(time.monotonic() - started)}")


def _venv_python(venv_dir: str) -> str:
    if sys.platform == "win32":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def _ensure_build_venv(requirements=None) -> str:
    """The build venv's interpreter, after installing *requirements*
    (requirements-build.txt by default, or a lock file)."""
    python = _venv_python(VENV_DIR)
    if not os.path.exists(python):
        logger.info(f"Creating build venv at {VENV_DIR}")
        venv.create(VENV_DIR, with_pip=True)
    requirements = requirements or os.path.join(REPO_ROOT, "requirements-build.txt")
    result = subprocess.run([python, "-m", "pip", "install", "-q", "-r", requirements])
    if result.returncode != 0:
        sys.exit(f"pip exited {result.returncode} installing {requirements}; its output is above.")
    return python


def _pop_option(args: list, name: str):
    """Remove ``name=value`` from *args* and return the value, or None."""
    for arg in list(args):
        if arg.startswith(name + "="):
            args.remove(arg)
            return arg.split("=", 1)[1]
    return None


def _app_version() -> str:
    path = os.path.join(REPO_ROOT, VERSION_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            version = f.read().strip()
    except OSError as e:
        sys.exit(f"Cannot read {path}: {e}")
    # Windows file versions take up to four numbers.
    if not re.fullmatch(r"\d+(\.\d+){0,3}", version):
        sys.exit(f"{VERSION_FILE} holds {version!r}; it must be up to four dot-separated numbers.")
    return version


def _git(*args: str):
    """git's raw stdout, or None when git is missing or the command fails."""
    try:
        result = subprocess.run(["git", "-C", REPO_ROOT, *args], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def _source_state() -> dict:
    """This checkout's commit, the commit's tree ("" when git cannot tell
    either), and a fingerprint of uncommitted changes to tracked files ("" for
    none, None when git cannot tell). Untracked files are not covered. The
    tree lets release tooling accept a build whose commit was replaced by one
    with the same files (amend, squash, empty commit)."""
    commit = (_git("rev-parse", "HEAD") or b"").decode("ascii", "replace").strip()
    tree = (_git("rev-parse", "HEAD^{tree}") or b"").decode("ascii", "replace").strip()
    diff = _git("diff", "HEAD", "--binary")
    changes = None if diff is None else (hashlib.sha1(diff).hexdigest() if diff else "")
    return {"commit": commit, "tree": tree, "changes": changes}


def _environment_versions(python: str) -> dict:
    probe = subprocess.run(
        [python, "-c", _VERSIONS_PROBE, *RECORDED_DISTRIBUTIONS], capture_output=True, text=True, check=True,
    )
    return json.loads(probe.stdout.strip().splitlines()[-1])


def _write_lock_file(python: str) -> None:
    freeze = subprocess.run([python, "-m", "pip", "freeze"], capture_output=True, text=True, check=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        f.write(freeze.stdout)
    logger.info(f"Build environment recorded in {LOCK_PATH}")


def _write_build_info(version: str, build_id: str, environment: dict) -> dict:
    # No checkout path: anyone with the exe could read it, and nothing here
    # looks the checkout up from a build.
    info = {
        "version": version,
        "build_id": build_id,
        "python": environment["python"],
        "packages": {name: v for name, v in environment["packages"].items() if v},
        "source": _source_state(),
    }
    os.makedirs(BUILD_DIR, exist_ok=True)
    with open(BUILD_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    logger.info("Building " + ", ".join(
        [f"ds {version}", f"build {build_id}",
         f"from {info['source']['commit'][:10] or 'unknown commit'}"
         + (" with uncommitted changes" if info["source"]["changes"] else ""),
         f"Python {info['python']}"]
        + [f"{name} {v}" for name, v in sorted(info["packages"].items())]
    ))
    return info


def _nuitka_args(version: str, build_id: str, extra_args) -> list:
    return [
        "--onefile",
        # The exe unpacks its runtime to this folder. A fixed path (no
        # {PID}/{TIME}) makes Nuitka keep it between runs, so only the first
        # run pays the unpacking cost; the build id gives each build its own
        # folder, so a rebuilt exe never reuses a previous build's files.
        # Nothing else goes under unpacked/, so old builds' folders there are
        # safe to delete.
        f"--onefile-tempdir-spec={APP_CACHE_SPEC}/unpacked/ds-{build_id}",
        f"--output-dir={BUILD_DIR}",
        f"--output-filename={EXE_NAME}",
        # Lets Nuitka fetch build helpers (e.g. MinGW on Windows) without prompting.
        "--assume-yes-for-downloads",
        # Version information; Windows shows it in the executable's properties
        # and crash reports. The file version takes numbers only, so the build
        # id goes in the description.
        "--product-name=dev_scripts_py",
        f"--product-version={version}",
        f"--file-version={version}",
        f"--file-description=ds command-line tools, build {build_id}",
        f"--include-data-files={BUILD_INFO_PATH}=build_info.json",
        f"--include-data-files={os.path.join(REPO_ROOT, VERSION_FILE)}={VERSION_FILE}",
        # Never add --python-flag=no_docstrings (or -OO): click command
        # docstrings are the help text shown by `ds commands` and `--help`.
        *extra_args,
        ENTRY,
    ]


def _copy_to_dist(exe_name: str) -> str:
    exe_path = os.path.join(DIST_DIR, exe_name)
    if os.path.isdir(exe_path):
        # Left by a folder build; on macOS/Linux it has the executable's name.
        logger.info(f"Removing the folder build at {exe_path}")
        shutil.rmtree(exe_path)
    os.makedirs(DIST_DIR, exist_ok=True)
    shutil.copy2(os.path.join(BUILD_DIR, exe_name), exe_path)
    return exe_path


def _smoke_test_env(scratch: str) -> dict:
    """The smoke test's environment, with the tool cache in *scratch*. Set,
    not inherited, so a value exported in the developer's shell can't point
    the test at real data."""
    env = dict(os.environ)
    env["DS_CACHE_DIR"] = scratch
    # The smoke test checks the real cache code path.
    env.pop("DS_REFRESH_TOOL_CACHE", None)
    return env


def _smoke_checks(version: str, build_id: str) -> list:
    """(name, ds arguments, stdin, check) for each smoke test check; a check
    takes the command's stdout and returns an error message or None."""

    def commands(out):
        # A command's docstring in the listing shows docstrings survived.
        if "Show the ds version" not in out:
            return "`ds version`'s help text is missing from the listing"
        return None

    def version_info(out):
        lines = out.splitlines()
        if lines[:1] != [f"ds {version}"]:
            return f"expected first line 'ds {version}' (bundled VERSION)"
        if len(lines) < 2 or not lines[1].startswith(f"Build {build_id} "):
            return f"expected second line to start 'Build {build_id}' (bundled build_info.json)"
        return None

    def join(out):
        # The README's inner join, also in tests/test_join.py: a file and
        # stdin through DataFile.
        if out != "a b c d b c\n1 2 3 4 3 2\n":
            return "join output differs from the expected inner join"
        return None

    return [
        ("command listing", ["commands"], "", commands),
        ("version and build info", ["version"], "", version_info),
        ("join of a file and stdin", ["join", SMOKE_JOIN_FIXTURE, "--join=inner", "--k1=1,4"],
         "a b c d\n1 3 2 4\n", join),
    ]


def _smoke_test(exe_path: str, version: str, build_id: str) -> None:
    # Run from outside the repo so a passing test can't depend on the checkout
    # (the join fixture is only input data), with the tool cache in a scratch
    # directory so the user's is untouched. Each check runs even if an earlier
    # one failed, so one run reports every failure.
    failures = []
    with tempfile.TemporaryDirectory(prefix="ds-smoke-") as scratch:
        env = _smoke_test_env(scratch)
        for name, args, stdin, check in _smoke_checks(version, build_id):
            command = [exe_path, *args]
            result = subprocess.run(
                command, input=stdin, cwd=os.path.expanduser("~"), env=env,
                capture_output=True, text=True, errors="replace",
            )
            if result.returncode != 0:
                problem = f"exited {result.returncode}"
            else:
                problem = check(result.stdout)
            if problem:
                failures.append(name)
                logger.error(f"Smoke check '{name}' failed: `{' '.join(command)}` {problem}.\n"
                             f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
            else:
                logger.info(f"Smoke check '{name}' passed")
    if failures:
        sys.exit(f"Smoke test failed: {', '.join(failures)}.")


def main() -> None:
    args = sys.argv[1:]
    lock = _pop_option(args, "--lock")
    # Before installing anything, so a bad VERSION stops the build in seconds.
    version = _app_version()
    build_id = time.strftime("%Y%m%d-%H%M%S")
    logger.info(f"Log: {_setup_logging(build_id)}")

    if "--current-env" in args:
        args.remove("--current-env")
        if lock:
            sys.exit("--lock installs into the build venv; it cannot be combined with --current-env.")
        python = sys.executable
    else:
        if lock:
            lock = os.path.abspath(lock)
            if not os.path.isfile(lock):
                sys.exit(f"--lock: {lock} not found.")
        with _timed("Installing the build venv"):
            python = _ensure_build_venv(requirements=lock)

    _write_lock_file(python)
    _write_build_info(version, build_id, _environment_versions(python))

    with _timed("Compiling ds with Nuitka"):
        result = subprocess.run([python, "-m", "nuitka", *_nuitka_args(version, build_id, args)], cwd=REPO_ROOT)
        if result.returncode != 0:
            sys.exit(f"Nuitka exited {result.returncode}; its output is above.")
    exe_path = _copy_to_dist(EXE_NAME)
    with _timed(f"Smoke-testing {EXE_NAME}"):
        _smoke_test(exe_path, version, build_id)
    logger.info(f"Built {exe_path}")


if __name__ == "__main__":
    started = time.monotonic()
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            if isinstance(e.code, str):
                logger.error(e.code)
            logger.error(f"Build failed after {_duration(time.monotonic() - started)}")
            sys.exit(1)
        raise
    except KeyboardInterrupt:
        logger.error(f"Build stopped after {_duration(time.monotonic() - started)}")
        sys.exit(1)
    except BaseException:
        logger.exception(f"Build failed after {_duration(time.monotonic() - started)}")
        sys.exit(1)
    logger.info(f"Build finished in {_duration(time.monotonic() - started)}")
