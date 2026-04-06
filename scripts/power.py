import itertools
import operator

from scripts.DataFile import DataFile


class DataAnalyzer:
    """Combinatorial frequency over field values; rows come from a :class:`DataFile`."""

    def __init__(self, data_file: DataFile, min=0, return_fields=False, invert=False, choose=None):
        if not isinstance(data_file, DataFile):
            raise TypeError("DataAnalyzer expects a DataFile instance")
        self.data_file = data_file
        self.min = min
        self.return_fields = return_fields
        self.invert = invert
        self.choose = choose
        self.combinations = {}
        self._line_count = 0

    def analyze(self):
        lines = self.data_file.get_data()
        self._line_count = len(lines)
        for raw in lines:
            line = [f.strip() for f in raw if f.strip() != ""]
            if not line:
                continue
            for r in range(1, len(line) + 1):
                if self.choose and r != self.choose:
                    continue
                for c in itertools.combinations(line, r):
                    if c in self.combinations:
                        self.combinations[c] += 1
                    else:
                        self.combinations[c] = 1

        self.combinations = sorted(self.combinations.items(), key=operator.itemgetter(1), reverse=True)

    def print_results(self):
        for comb, occ in self.combinations:
            if (self.invert and occ < self.min) or (not self.invert and occ >= self.min):
                if self.return_fields:
                    denom = self._line_count if self._line_count else 1
                    print(f"{occ / denom} {' '.join(comb)}")
                else:
                    print(f"{occ} {' '.join(comb)}")


if __name__ == "__main__":
    analyzer = DataAnalyzer(DataFile("test.txt"), min=2, return_fields=True, choose=2)
    analyzer.analyze()
    analyzer.print_results()
