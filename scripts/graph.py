# Python 3
from __future__ import annotations

import argparse
import sys
from typing import Callable, Iterable

from scripts.DataFile import DataFile


def backtrace(start, shoots):
    """Return ``(path, None)`` with the path from the root base down to ``start``, or
    ``(None, node)`` when the parent chain loops back to ``node``."""
    chain = [start]
    seen = {start}
    node = shoots[start]
    while True:
        if node in seen:
            return None, node
        chain.append(node)
        seen.add(node)
        if node not in shoots:
            break
        node = shoots[node]
    return " ".join(reversed(chain)), None


class GraphDagBacktrace:
    """Build shoots/bases from DAG edge lines, print backtraces (and optional bases), detect cycles."""

    def __init__(
        self,
        *,
        print_bases: bool = False,
        echo: Callable[[str], None] = print,
    ):
        self.print_bases = print_bases
        self.echo = echo

    def run(self, lines: Iterable[str]) -> int:
        shoots = {}
        bases = {}
        cycles = {}

        for line in lines:
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) > 1:
                    shoots[parts[0]] = parts[1]
                    bases[parts[1]] = 1
                elif len(parts) == 1:
                    bases[parts[0]] = 1

        if self.print_bases:
            for base in bases:
                if base not in shoots:
                    self.echo(base)

        for shoot in shoots:
            if shoots[shoot] and (self.print_bases or shoot not in bases):
                path, cycle_node = backtrace(shoot, shoots)
                if path is None:
                    cycles[cycle_node] = 1
                    continue
                self.echo(path)

        if cycles:
            self.echo(f"WARNING: {len(cycles)} cycles found!")
            for cycle in cycles:
                self.echo(f"CYCLENODE__ {cycle}")
            return 1
        return 0


def run_graph(
    data_file: DataFile,
    *,
    print_bases: bool = False,
    echo: Callable[[str], None] = print,
) -> int:
    """Read graph lines from ``data_file`` (UTF-8); return 0 or 1 if cycles detected."""
    with open(data_file.file_path, encoding="utf-8", errors="replace") as f:
        return GraphDagBacktrace(print_bases=print_bases, echo=echo).run(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--print_bases",
        help="With this option set, resulting graph output includes bases.",
        action="store_true",
    )
    args = parser.parse_args()
    code = GraphDagBacktrace(print_bases=args.print_bases).run(sys.stdin)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
