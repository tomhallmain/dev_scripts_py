"""
Build the standalone ``dsp`` executable with Nuitka: ``python build_exe.py``.

Nuitka compiles the code to C, then to a single native executable that embeds
the Python runtime. Needs a C compiler: Xcode Command Line Tools on macOS; on
Windows, Visual Studio Build Tools, or Nuitka downloads MinGW itself. Nuitka
does not cross-compile, so run this on each target OS.

Builds inside a dedicated ``.venv-build`` at the repo root, populated from
requirements-build.txt, so packages from the active conda env or venv aren't
bundled. The venv is based on the interpreter running this script, and the exe
embeds that interpreter's runtime, so it must be the Python version named in
.python-version (checked before anything is installed). ``--current-env``
builds with the running interpreter instead; it must already have
requirements-build.txt installed.

The exe is smoke-tested where Nuitka wrote it, from the home directory with its
tool cache and temporary files in a scratch directory: ``dsp commands`` (help
text present), ``dsp version`` (bundled VERSION and build info) and a join of a
test fixture with stdin. Only a build that passes is copied to dist/dsp
(macOS/Linux) or dist\\dsp.exe (Windows). At its first start the exe unpacks its
runtime to ``dev_scripts_py/unpacked/dsp-<build id>`` in the user cache dir and
removes older builds' folders there (scripts/unpack_cleanup.py); later starts of
the same build reuse that folder. On Windows Nuitka finds the cache dir without
the environment, so the smoke test also unpacks to the real one. Other args are
forwarded to Nuitka, e.g. ``--show-scons`` or ``--jobs=4``.

Before compressing the onefile payload, the last step of the compile, the build
waits for enough free memory (the memory-wait plugin, from app-release when
installed), since a failed allocation there loses the whole compile.
``--min-free-memory=<GiB>`` sets the amount instead of the estimate; 0 turns the
wait off. Each step is timed, and the log goes to
``build/logs/build_exe-<build id>.log`` as well (Nuitka's own output only to
the console).

The exe's version information comes from the VERSION file at the repo root,
with the build id (build time) in its description. Each build writes
``build_info.json`` (version, build id, Python and key package versions, and
this checkout's commit, the commit's tree and a fingerprint of its uncommitted
changes), bundled with VERSION so ``dsp version`` can show them, and
``build-requirements.lock.txt``, the build venv's ``pip freeze``. Both are
written to build/nuitka/staging/ and move to build/nuitka/ only with a build
that reached dist/, so the two always describe the exe there. ``--lock=<file>``
installs the build venv from such a file instead of requirements-build.txt, to
repeat a known good build; packages already in the venv but absent from the
file stay installed, so delete .venv-build first for an exact copy.
app-release publishes the executable in dist/ as a GitHub release; its own
options (``--bump``, ``--no-build``, ...) are refused here.
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
# app-release names the release and its asset after this base name.
EXE_BASE_NAME = "dsp"
EXE_NAME = EXE_BASE_NAME + (".exe" if sys.platform == "win32" else "")
# Nuitka's {CACHE_DIR} is %LOCALAPPDATA% on Windows and ~/.cache elsewhere,
# the same base scripts/tool_availability.py caches under.
APP_CACHE_SPEC = "{CACHE_DIR}/dev_scripts_py"
# scripts/unpack_cleanup.py removes older builds' folders by this prefix.
UNPACK_PREFIX = "dsp-"
VERSION_FILE = "VERSION"
# Major.minor of the Python the build must run with; app-release reads it too.
PYTHON_VERSION_FILE = ".python-version"
SMOKE_JOIN_FIXTURE = os.path.join(REPO_ROOT, "tests", "data", "tmp_join")
# Where release tooling reads them: only ever from a build that reached dist/.
BUILD_INFO_PATH = os.path.join(BUILD_DIR, "build_info.json")
LOCK_PATH = os.path.join(BUILD_DIR, "build-requirements.lock.txt")
# Written here during a build; the bundled build_info.json comes from here.
STAGING_DIR = os.path.join(BUILD_DIR, "staging")
STAGED_BUILD_INFO = os.path.join(STAGING_DIR, "build_info.json")
STAGED_LOCK = os.path.join(STAGING_DIR, "build-requirements.lock.txt")
# app-release passes the memory-wait plugin's path in this variable, and the
# plugin reads the free memory to wait for from MIN_FREE_MEMORY_ENV.
MEMORY_WAIT_PLUGIN_ENV = "NUITKA_MEMORY_WAIT_PLUGIN"
MIN_FREE_MEMORY_ENV = "BUILD_MIN_FREE_MEMORY_GB"
# app-release's own run options: given here they would reach Nuitka.
APP_RELEASE_OPTIONS = ("--no-build", "--bump", "--no-upload", "--publish", "--force")
# Versions the build output and build_info.json record.
RECORDED_DISTRIBUTIONS = ("Nuitka", "click", "termcolor", "pywin32", "psutil", "zstandard")
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


def _refuse_app_release_options(args) -> None:
    given = [a for a in args if a.split("=", 1)[0] in APP_RELEASE_OPTIONS]
    if given:
        sys.exit(f"{', '.join(given)}: app-release's option(s), not build_exe.py's; "
                 "run them as `app-release <checkout> ...`.")


def _target_python():
    """(major, minor) from .python-version, or None when the file is missing."""
    path = os.path.join(REPO_ROOT, PYTHON_VERSION_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except FileNotFoundError:
        return None
    except OSError as e:
        sys.exit(f"Cannot read {path}: {e}")
    match = re.fullmatch(r"(\d+)\.(\d+)(\.\d+)?", text)
    if not match:
        sys.exit(f"{PYTHON_VERSION_FILE} holds {text!r}; expected a version such as 3.11.")
    return int(match.group(1)), int(match.group(2))


def _check_python(target, version_info=sys.version_info) -> None:
    if target is None:
        logger.warning(f"No {PYTHON_VERSION_FILE}: building with Python "
                       f"{version_info[0]}.{version_info[1]} without checking it.")
        return
    if tuple(version_info[:2]) != tuple(target):
        wanted = ".".join(map(str, target))
        sys.exit(f"Run build_exe.py with Python {wanted} ({PYTHON_VERSION_FILE}): the build venv and "
                 f"the executable use the interpreter running it, and this is "
                 f"{version_info[0]}.{version_info[1]}.")


def _min_free_memory(value):
    """``--min-free-memory``'s value, checked, or None when not given."""
    if value is None:
        return None
    try:
        if float(value) >= 0:
            return value
    except ValueError:
        pass
    sys.exit(f"--min-free-memory={value}: give a number of GiB, or 0 to not wait for memory.")


def _nuitka_env(min_free_memory=None) -> dict:
    env = dict(os.environ)
    if min_free_memory is not None:
        env[MIN_FREE_MEMORY_ENV] = min_free_memory
    return env


def _memory_wait_plugin():
    """The memory-wait plugin's path: from app-release's variable, else from an
    installed app-release, else None (the build does not wait)."""
    path = os.environ.get(MEMORY_WAIT_PLUGIN_ENV)
    tool = None if path else shutil.which("app-release")
    if tool:
        try:
            result = subprocess.run([tool, "--memory-wait-plugin"], capture_output=True, text=True,
                                    stdin=subprocess.DEVNULL, timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning(f"Cannot ask {tool} for the memory-wait plugin: {e}")
        else:
            if result.returncode == 0:
                path = result.stdout.strip()
    if path and os.path.isfile(path):
        logger.info(f"Memory-wait plugin: {path}")
        return path
    logger.warning("No memory-wait plugin: the onefile step will not wait for free memory. "
                   "Install app-release, or build through it.")
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
    os.makedirs(STAGING_DIR, exist_ok=True)
    with open(STAGED_LOCK, "w", encoding="utf-8") as f:
        f.write(freeze.stdout)
    logger.info(f"Build environment recorded in {STAGED_LOCK}")


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
    os.makedirs(STAGING_DIR, exist_ok=True)
    with open(STAGED_BUILD_INFO, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    logger.info("Building " + ", ".join(
        [f"{EXE_BASE_NAME} {version}", f"build {build_id}",
         f"from {info['source']['commit'][:10] or 'unknown commit'}"
         + (" with uncommitted changes" if info["source"]["changes"] else ""),
         f"Python {info['python']}"]
        + [f"{name} {v}" for name, v in sorted(info["packages"].items())]
    ))
    return info


def _nuitka_args(version: str, build_id: str, extra_args, memory_wait_plugin=None) -> list:
    return [
        "--onefile",
        # The exe unpacks its runtime to this folder. A fixed path (no
        # {PID}/{TIME}) makes Nuitka keep it between runs, so only the first
        # run pays the unpacking cost; the build id gives each build its own
        # folder, so a rebuilt exe never reuses a previous build's files.
        # Nothing else goes under unpacked/, so the exe removes older builds'
        # folders there.
        f"--onefile-tempdir-spec={APP_CACHE_SPEC}/unpacked/{UNPACK_PREFIX}{build_id}",
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
        f"--include-data-files={STAGED_BUILD_INFO}=build_info.json",
        f"--include-data-files={os.path.join(REPO_ROOT, VERSION_FILE)}={VERSION_FILE}",
        # Never add --python-flag=no_docstrings (or -OO): click command
        # docstrings are the help text shown by `dsp commands` and `--help`.
        *([f"--user-plugin={memory_wait_plugin}"] if memory_wait_plugin else []),
        *extra_args,
        ENTRY,
    ]


def _promote_build_record() -> None:
    """Move the staged build info and lock file to where release tooling reads
    them, once their build has reached dist/."""
    for staged, final in ((STAGED_BUILD_INFO, BUILD_INFO_PATH), (STAGED_LOCK, LOCK_PATH)):
        os.replace(staged, final)
    logger.info(f"Build info and lock file recorded in {BUILD_DIR}")


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
    """The smoke test's environment, with the tool cache and temporary files in
    *scratch*. Set, not inherited, so a value exported in the developer's shell
    can't point the test at real data."""
    env = dict(os.environ)
    env["DS_CACHE_DIR"] = scratch
    env["DS_TEMP_DIR"] = os.path.join(scratch, "tmp")
    # Each check exits within a moment, which would cut a removal short.
    env["DS_SKIP_UNPACK_CLEANUP"] = "1"
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
                # The hex form shows a Windows crash code such as 0xc0000409.
                problem = f"exited {result.returncode} ({result.returncode & 0xFFFFFFFF:#010x})"
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
    _refuse_app_release_options(args)
    lock = _pop_option(args, "--lock")
    min_free_memory = _min_free_memory(_pop_option(args, "--min-free-memory"))
    # Before installing anything, so a bad VERSION or Python stops the build in seconds.
    version = _app_version()
    target_python = _target_python()
    build_id = time.strftime("%Y%m%d-%H%M%S")
    logger.info(f"Log: {_setup_logging(build_id)}")
    _check_python(target_python)

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
    nuitka_args = _nuitka_args(version, build_id, args, _memory_wait_plugin())

    with _timed(f"Compiling {EXE_BASE_NAME} with Nuitka"):
        result = subprocess.run([python, "-m", "nuitka", *nuitka_args], cwd=REPO_ROOT,
                                env=_nuitka_env(min_free_memory))
        if result.returncode != 0:
            sys.exit(f"Nuitka exited {result.returncode}; its output is above.")
    # Tested before it replaces the exe in dist/, so a failing build leaves the
    # previous exe and its build info in place.
    with _timed(f"Smoke-testing {EXE_NAME}"):
        _smoke_test(os.path.join(BUILD_DIR, EXE_NAME), version, build_id)
    exe_path = _copy_to_dist(EXE_NAME)
    _promote_build_record()
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
