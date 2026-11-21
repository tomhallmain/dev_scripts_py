"""
Entry point for the standalone ``dsp`` executable built by build_exe.py.

The CLI's first argument is the caller's working directory (ds.py's wrappers
pass it because ds.bat changes directory before running Python). A packaged
executable already runs in the caller's directory, so it supplies that argument
itself and is invoked as plain ``dsp <command> ...``. It also removes the folders
older builds unpacked to (scripts/unpack_cleanup.py), on a thread the process
waits for before it exits.
"""
import os
import sys

from scripts import cli
from scripts.unpack_cleanup import start_unpack_cleanup

if __name__ == "__main__":
    start_unpack_cleanup()
    sys.argv.insert(1, os.getcwd())
    sys.exit(cli.main())
