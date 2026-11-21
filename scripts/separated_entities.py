"""``ds enti`` -- count the text entities separated by a pattern across all lines.

A separator of a single space (the default) splits on runs of whitespace, a single other
character splits on that character, and anything longer is a regex. Output lines are
``count entity`` for entities seen at least ``min_count`` times, sorted by count; ties sort
by the whole output line.
"""
import re
from collections import Counter
from typing import Iterable, List


class TextEntities:
    def __init__(self, min_count=1, separator=" ", descending=False):
        self.min_count = max(int(min_count), 1)
        self.separator = separator
        self.descending = descending
        self.counter = Counter()

    def split(self, line: str) -> List[str]:
        if not self.separator or self.separator == " ":
            return line.split()
        if len(self.separator) == 1:
            return line.split(self.separator)
        return re.split(self.separator, line)

    def process_lines(self, lines: Iterable[str]) -> None:
        for line in lines:
            line = line.rstrip("\n").rstrip("\r")
            if not line:
                continue
            self.counter.update(self.split(line))

    def process_file(self, file_path: str) -> None:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            self.process_lines(f)

    def entity_lines(self) -> List[str]:
        kept = [(count, f"{count} {entity}") for entity, count in self.counter.items()
                if count >= self.min_count]
        kept.sort(reverse=self.descending)
        return [line for _count, line in kept]
