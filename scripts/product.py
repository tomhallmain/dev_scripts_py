"""``ds prod`` -- product multiset of the lines of several inputs.

Each input is one set of lines. Every combination taking one line from each set, in input
order, is printed joined by a space; the first input varies slowest. Lines are used as they
are, without trimming. Passing the same file twice gives its product with itself.
"""
import itertools
import sys
from typing import Iterable, Iterator, List, Sequence


def read_line_set(file_path: str) -> List[str]:
    with open(file_path, encoding="utf-8", errors="replace") as f:
        return [line.rstrip("\n").rstrip("\r") for line in f]


def text_line_set(text: str) -> List[str]:
    return [line.rstrip("\r") for line in text.splitlines()]


def product_lines(line_sets: Sequence[Sequence[str]], separator: str = " ") -> Iterator[str]:
    if not line_sets or any(len(s) == 0 for s in line_sets):
        return iter(())
    return (separator.join(combo) for combo in itertools.product(*line_sets))


def product_main(filenames: Iterable[str], stdin_text=None, echo=print) -> None:
    line_sets = []
    if stdin_text:
        line_sets.append(text_line_set(stdin_text))
    line_sets.extend(read_line_set(f) for f in filenames)
    for line in product_lines(line_sets):
        echo(line)


if __name__ == "__main__":
    product_main(sys.argv[1:])
