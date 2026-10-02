"""
Entry point for the standalone ``ds`` executable built by build_exe.py.

The CLI's first argument is the caller's working directory (ds.py's wrappers
pass it because ds.bat changes directory before running Python). A packaged
executable already runs in the caller's directory, so it supplies that argument
itself and is invoked as plain ``ds <command> ...``.
"""
import os
import sys

from scripts import cli

if __name__ == "__main__":
    sys.argv.insert(1, os.getcwd())
    sys.exit(cli.main())
