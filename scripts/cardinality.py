class Cardinality:
    def __init__(self):
        self._ = {}
        self.__ = {}
        self.max_nf = 0

    def process_line(self, line):
        fields = line.split()
        for i, field in enumerate(fields, start=1):
            if not self._.get((i, field)):
                self._[(i, field)] = 1
                self.__[i] = self.__.get(i, 0) + 1

        if len(fields) > self.max_nf:
            self.max_nf = len(fields)

    def print_cardinality(self):
        for i in range(1, self.max_nf + 1):
            print(i, self.__.get(i, 0))

# Usage
c = Cardinality()
with open('file', 'r') as f:
    for line in f:
        c.process_line(line)
c.print_cardinality()
