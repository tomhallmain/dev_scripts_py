#!/usr/bin/env python3
import argparse
import re
from collections import defaultdict


class FieldsCounter:
    IFS = '|||'
    IFSRE = re.compile(r'\|\|\|')

    def __init__(self, data_file, ofs=" ", fields=None, min=0, only_vals=False) -> None:
        self.data_file = data_file

        if fields:
            if re.search(r'[A-z]+', fields):
                self.fields = [0]
            else:
                self.fields = list(map(int, re.split(r'[ ,|\.:;_]+', fields)))
        else:
            self.fields = [1]

        self.counts = not only_vals
        self.counter = defaultdict(int)
        self.ofs = ofs
        self.min = min

    def run(self):
        # Counting occurrences
        with self.data_file.read() as f:
            for line in f:
                line = line.strip()
                if self.fields[0] == 1:
                    self.counter[line] += 1
                else:
                    key = FieldsCounter.IFS.join(line.split()[field-1] for field in self.fields)
                    self.counter[key] += 1

        # Printing results
        for key, count in self.counter.items():
            if count > self.min:
                if self.counts:
                    print(f'{count}', end=' ')
                if self.fields[0] == 0:
                    print(key)
                else:
                    print(self.ofs.join(FieldsCounter.IFSRE.split(key)))
