# dev_scripts_py

Python CLI commands for data manipulation and file operations.

All commands are namespaced to `ds` so there should be little to no clashing with any existing commands in your local shell environment.

**Note:** This project is still in development. The tested executable is currently a batch file (`ds.bat`) for Windows.

## Installation

### Building the Executable

To create a `ds` executable, use PyInstaller with the provided spec file:

```bash
pyinstaller ds.spec
```

This will create a `build` directory, update `ds.spec`, and generate the executable in the `dist` directory. Add the executable from `dist` to your PATH.

Alternatively, for development, you can use the `ds.bat` wrapper (Windows) or create a similar shell script for Unix systems that calls `python ds.py` with the current directory as the first argument.

The executable automatically uses the current directory as the working context.

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
- `ds index [filepath]` - Print lines indexed
- `ds field_counts [file]` - Count fields in data
- `ds inferfs [filepath]` - Infer field separator from data
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
- `ds cd` - Change to a different directory in context

#### Stubs (hidden from `ds commands` by default — use `ds commands --all`)

These commands are wired up but their Python ports are incomplete. They are tagged **[STUB]** and hidden from the default command listing.

- `ds diff_fields <file1> <file2> <op>` - Elementwise diff of two datasets
- `ds fit` - Fit fielded data in columns with dynamic width
- `ds reo` - Reorder, repeat, or slice data by rows and columns
- `ds sortm` - Sort with inferred multi-char field separator
- `ds subsep <filepath> <pattern>` - Extend fields by a common sub-separator
- `ds inferh` - Infer if headers are present in a file (still AWK)
- `ds cardinality <filepath>` - Calculate distinct values per field
- `ds prod <files...>` - Cartesian product of lines from multiple files
- `ds shape` - Print data shape by length or pattern (stdin)
- `ds field_uniques [fields]` - Get unique values from fields (stdin)
- `ds enti <filepath>` - Print text entities separated by a pattern

## Issues

To report bugs please contact: tomhall.main@gmail.com
