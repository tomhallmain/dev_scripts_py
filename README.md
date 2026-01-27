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

### Available Commands

- `ds move <source> <target> [--filter]` - Move files or directories with optional filtering
- `ds copy <source> <target> [--filter]` - Copy files or directories with optional filtering
- `ds dup_files <dirpath>` - Identify and remove duplicate files
- `ds join <file1> [file2]` - Join data files
- `ds transpose [filepath]` - Transpose tabular data
- `ds index [filepath]` - Print lines indexed
- `ds field_counts [file]` - Count fields in data
- `ds inferfs [filepath]` - Infer field separator from data
- `ds case <tocase> [text]` - Convert text case

## Issues

To report bugs please contact: tomhall.main@gmail.com
