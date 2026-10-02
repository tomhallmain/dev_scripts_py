# dev_scripts_py

Python CLI commands for data manipulation and file operations.

All commands are namespaced to `ds` so there should be little to no clashing with any existing commands in your local shell environment.

**Note:** This project is still in development. The tested executable is currently a batch file (`ds.bat`) for Windows.

## Installation

### Building the Executable

To build a standalone `ds` executable that needs no Python, conda, or venv at runtime, run this with any Python 3:

```bash
python build_exe.py
```

This compiles the project with [Nuitka](https://nuitka.net) into a single native executable, `dist/ds` on macOS/Linux or `dist\ds.exe` on Windows, and smoke-tests it with `ds commands`. Copy it somewhere on your PATH. The first build takes a few minutes; the script creates (or reuses) a dedicated `.venv-build` venv and installs `requirements-build.txt` (the runtime deps plus Nuitka) into it.

- **C compiler required.** On macOS, install the Xcode Command Line Tools (`xcode-select --install`). On Windows, Nuitka uses Visual Studio Build Tools if installed, and otherwise downloads MinGW itself.
- **Build on each OS** you want a binary for; Nuitka does not cross-compile. The binary targets the architecture of the Python that ran the build, so on Apple Silicon use a native arm64 Python (e.g. Homebrew's) rather than an Intel one.
- **First run is slower.** The exe embeds the Python runtime and unpacks it once, on first run, into a folder under your user cache directory (`dev_scripts_py/ds-<build time>`). Later runs reuse it. Each rebuild gets a new folder; old ones are safe to delete.
- **Copies on other Macs.** The binary is ad-hoc signed, which is enough on the Mac that built it. A copy downloaded onto another Mac gets quarantined by Gatekeeper; clear that with `xattr -d com.apple.quarantine ds`.
- **Using an existing environment.** `python build_exe.py --current-env` builds with the running interpreter instead, which needs `requirements-build.txt` installed. Nuitka bundles libraries from whichever environment runs the build, so a lean venv gives a smaller exe than a full conda env. In either mode, the embedded Python runtime is the one that ran `build_exe.py`.

The executable uses the directory it's invoked from as the working context, so you run it as `ds <command> ...`.

Alternatively, for development, use one of the bundled wrappers, which call `python ds.py` with the current directory as the first argument:

- **Unix (macOS, Linux):** `ds.sh`. It locates `ds.py` relative to itself, so put it on your PATH wherever you like:

  ```bash
  chmod +x ds.sh
  ln -s "$PWD/ds.sh" ~/bin/ds
  ```

  Set `DS_PYTHON` to choose an interpreter; otherwise `python3` is used when present. An activated conda env or venv is picked up automatically.

- **Windows:** `ds.bat`. Edit the `CD` line to point at your checkout before using it.

The executable automatically uses the current directory as the working context.

## Tests

Install dev dependencies (including pytest), then run the suite from the repository root:

```bash
pip install -r requirements.txt
python -m pytest
```

Run a single file, for example: `python -m pytest tests/test_power.py`.

## Usage

Run `ds <command>` where `<command>` is one of the available commands below. The current directory is automatically used as the working context.

To list all available commands, run:

```bash
ds commands
```

or equivalently:

```bash
ds --help
```

To include incomplete stub commands in the listing:

```bash
ds commands --all
```

You can also get detailed help for a specific command with:

```bash
ds <command> --help
```

### Available Commands

#### File Operations

- `ds move <source> <target> [--filter]` - Move files or directories with optional filtering
- `ds copy <source> <target> [--filter]` - Copy files or directories with optional filtering
- `ds dup_files <dirpath>` - Identify and remove duplicate files

#### Data Manipulation

- `ds join <file1> [file2]` - Join data files
- `ds transpose [filepath]` - Transpose tabular data
- `ds reo [file] [rows] [cols]` - Reorder, repeat, or slice data by rows and columns
- `ds index [filepath]` - Print lines indexed
- `ds field_counts [file]` - Count fields in data
- `ds inferfs [filepath]` - Infer field separator from data
- `ds subsep <filepath> <pattern>` - Extend fields by a common sub-separator
- `ds case <tocase> [text]` - Convert text case
- `ds matches <file1> <file2> [--key] [--fs]` - Get matching records between two files
- `ds power <file> [--min] [--choose]` - Combinatorial frequency analysis of field values
- `ds random [mode] [text]` - Generate a random number or randomize text
- `ds unicode [conversion]` - Convert UTF-8 unicode representations from stdin

#### Git

- `ds git_status [base_dir] [--track-non-repos]` - Show git status for all repos under a directory
- `ds git_branch [base_dir]` - List branches for all local git repos
- `ds git_purge_local <base_dir> <branches...>` - Purge branches from local repos **(WIP)**

#### Conda

- `ds conda_check <packages...>` - Check which conda environments have given packages
- `ds conda_envs [--json] [--sort]` - List conda environments with details

#### System

- `ds kill_port <port> [--force] [--dry-run]` - Kill all processes bound to a port

#### Visualization (WIP)

- `ds graph [--print-bases]` - Extract graph relationships from DAG data (stdin)
- `ds stagger <filepath> [--stag-size]` - Print tabular data in staggered rows
- `ds pivot <file> -y <keys> -x <keys>` - Pivot tabular data
- `ds hist` - Print histograms for numeric fields (stdin)

#### Not Yet Ported (WIP)

- `ds agg` - Aggregate field-based text data
- `ds asgn` - Print lines matching assignment pattern

#### Stubs (hidden from `ds commands` by default — use `ds commands --all`)

These commands are wired up but their Python ports are incomplete. They are tagged **[STUB]** and hidden from the default command listing.

- `ds diff_fields <file1> <file2> <op>` - Elementwise diff of two datasets
- `ds fit` - Fit fielded data in columns with dynamic width
- `ds sortm` - Sort with inferred multi-char field separator
- `ds inferh` - Infer if headers are present in a file (still AWK)
- `ds cardinality <filepath>` - Calculate distinct values per field
- `ds prod <files...>` - Cartesian product of lines from multiple files
- `ds shape` - Print data shape by length or pattern (stdin)
- `ds field_uniques [fields]` - Get unique values from fields (stdin)
- `ds enti <filepath>` - Print text entities separated by a pattern

## Issues

To report bugs please contact: tomhall.main@gmail.com
