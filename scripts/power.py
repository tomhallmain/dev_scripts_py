import itertools
import operator

class DataAnalyzer:
    def __init__(self, file, min=0, return_fields=False, invert=False, choose=None):
        self.file = file
        self.min = min
        self.return_fields = return_fields
        self.invert = invert
        self.choose = choose
        self.combinations = {}

    def analyze(self):
        with open(self.file, 'r') as f:
            lines = [line.strip().split() for line in f.readlines()]
            for line in lines:
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
                    print(f"{occ/len(self.combinations)} {' '.join(comb)}")
                else:
                    print(f"{occ} {' '.join(comb)}")

if __name__ == "__main__":
    analyzer = DataAnalyzer('test.txt', min=2, return_fields=True, choose=2)
    analyzer.analyze()
    analyzer.print_results()
