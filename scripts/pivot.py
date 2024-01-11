class Pivot:
    def __init__(self, file, y_keys, x_keys, z_keys=None, agg_type=None, header=True, gen_keys=True, sort_off=False):
        self.file = file
        self.y_keys = y_keys.split(',')
        self.x_keys = x_keys.split(',')
        self.z_keys = z_keys.split(',') if z_keys else None
        self.agg_type = agg_type
        self.header = header
        self.gen_keys = gen_keys
        self.sort_off = sort_off
        self.X = {}
        self.Y = {}
        self.Z = {}
        self.data = []

    def read_file(self):
        with open(self.file, 'r') as f:
            for line in f:
                self.data.append(line.strip().split(','))

    def process_header(self):
        if self.header:
            self.header = self.data.pop(0)

    def process_data(self):
        for row in self.data:
            x_str = ''
            y_str = ''
            z_str = ''
            for i in range(len(row)):
                if str(i+1) in self.x_keys:
                    x_str += row[i]
                if str(i+1) in self.y_keys:
                    y_str += row[i]
                if self.z_keys and str(i+1) in self.z_keys:
                    z_str += row[i]
            self.X[x_str] = self.X.get(x_str, 0) + 1
            self.Y[y_str] = self.Y.get(y_str, 0) + 1
            self.Z[(x_str, y_str)] = self.Z.get((x_str, y_str), 0) + 1

    def aggregate(self):
        if self.agg_type == 'count':
            return
        elif self.agg_type == 'sum':
            for key in self.Z:
                self.Z[key] = sum(self.Z[key])
        elif self.agg_type == 'product':
            for key in self.Z:
                self.Z[key] = prod(self.Z[key])
        elif self.agg_type == 'mean':
            for key in self.Z:
                self.Z[key] = sum(self.Z[key]) / len(self.Z[key])

    def pivot(self):
        self.read_file()
        self.process_header()
        self.process_data()
        self.aggregate()

    def print_pivot(self):
        print('PIVOT')
        for k, v in self.X.items():
            print(k, v)
        for k, v in self.Y.items():
            print(k, v)
        for k, v in self.Z.items():
            print(k, v)
