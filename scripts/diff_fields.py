import csv
import argparse
import sys
import operator

class DiffFields:
    def __init__(self, file1, file2, op, exclude_fields, header, diff_list, diff_list_sort):
        self.file1 = file1
        self.file2 = file2
        self.op = op
        self.exclude_fields = exclude_fields
        self.header = header
        self.diff_list = diff_list
        self.diff_list_sort = diff_list_sort
        self.operations = {
            '-': operator.sub,
            '+': operator.add,
            '%': lambda a, b: ((a - b) / a) * 100 if a != 0 else 0,
            '*': operator.mul,
            '/': operator.truediv,
            'b': lambda a, b: a != b,
            'bin': lambda a, b: a != b,
            'binary': lambda a, b: a != b
        }

    def _read_file(self, file):
        with open(file, 'r') as f:
            reader = csv.reader(f)
            return list(reader)

    def _exclude_fields(self, row):
        return [val for i, val in enumerate(row) if i not in self.exclude_fields]

    def diff(self):
        data1 = self._read_file(self.file1)
        data2 = self._read_file(self.file2)

        if self.header:
            headers1 = data1.pop(0)
            headers2 = data2.pop(0)

        for row1, row2 in zip(data1, data2):
            row1 = self._exclude_fields(row1)
            row2 = self._exclude_fields(row2)

            for val1, val2 in zip(row1, row2):
                val1 = float(val1)
                val2 = float(val2)

                diff = self.operations[self.op](val1, val2)

                if diff != 0 and self.diff_list:
                    print(f'Row: {row1}, {row2}, Diff: {diff}')
        if self.diff_list_sort:
            data1.sort(key=lambda x: float(x[1]))
            data2.sort(key=lambda x: float(x[1]))

        return data1, data2

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('file1', help='First file for comparison')
    parser.add_argument('file2', help='Second file for comparison')
    parser.add_argument('op', help='Operation to be performed')
    parser.add_argument('--exclude_fields', nargs='+', type=int, default=[0], help='Fields to be excluded from the operation')
    parser.add_argument('--header', action='store_true', help='Flag to indicate if header is present')
    parser.add_argument('--diff_list', action='store_true', help='Flag to indicate if diff list should be printed')
    parser.add_argument('--diff_list_sort', action='store_true', help='Flag to indicate if diff list should be sorted')

    args = parser.parse_args()

    diff_fields = DiffFields(args.file1, args.file2, args.op, args.exclude_fields, args.header, args.diff_list, args.diff_list_sort)
    diff_fields.diff()
