import os
import sys

# Get the directory containing ds.py
current_dir = os.path.dirname(os.path.abspath(__file__))
# Add the project root to Python path
sys.path.insert(0, current_dir)

from scripts import cli

if __name__ == "__main__":
    sys.exit(cli.main())
