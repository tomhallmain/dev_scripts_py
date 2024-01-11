import os
import re

class FileComparator:
    def __init__(self, file1, file2, fs=None, key=None, fs1=None, fs2=None, key1=None, key2=None):
        self.file1 = file1
        self.file2 = file2
        self.fs = fs
        self.key = key
        self.fs1 = fs1
        self.fs2 = fs2
        self.key1 = key1
        self.key2 = key2
        self.records = {}
        self.matches = []

    def infer_separator(self, filename):
        with open(filename, 'r') as file:
            line = file.readline()
            for sep in [',', '\t', '|']:
                if sep in line:
                    return sep
        return None

    def process_file(self, filename, fs, key):
        with open(filename, 'r') as file:
            for line in file:
                fields = line.strip().split(fs)
                if key is None:
                    self.records[line] = 1
                else:
                    self.records[fields[key-1]] = 1

    def compare_files(self):
        if self.fs:
            self.fs1 = self.fs
            self.fs2 = self.fs
        else:
            if not self.fs1:
                self.fs1 = self.infer_separator(self.file1)
            if not self.fs2:
                self.fs2 = self.infer_separator(self.file2)

        if self.key:
            self.key1 = self.key
            self.key2 = self.key
        else:
            if not self.key1:
                self.key1 = self.key2
            if not self.key2:
                self.key2 = self.key1

        self.process_file(self.file1, self.fs1, self.key1)

        with open(self.file2, 'r') as file2:
            for line in file2:
                fields = line.strip().split(self.fs2)
                if self.key2 is None:
                    key = line
                else:
                    key = fields[self.key2-1]
                if key in self.records:
                    self.matches.append(line)

    def print_matches(self):
        if len(self.matches) > 0:
            print("Records found in both files:")
            for match in self.matches:
                print(match)
        else:
            print("NO MATCHES FOUND")

if __name__ == "__main__":
    comparator = FileComparator("file1.txt", "file2.txt", key=1)
    comparator.compare_files()
    comparator.print_matches()
