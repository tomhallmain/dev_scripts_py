class Pivot:
    COUNT = "count"
    SUM = "sum"
    PRODUCT = "product"
    MEAN = "mean"
    AGG_TYPES = [COUNT, SUM, PRODUCT, MEAN]

    def __init__(self, file, y_keys, x_keys, z_keys=None, agg_type=None, header=True, gen_keys=True, sort_off=False):
        self.file = file
        self.y_keys = y_keys.split(',')
        self.x_keys = x_keys.split(',')
        self.z_keys = z_keys.split(',') if z_keys else None
        if agg_type:
            selected_agg_types = [t for t in Pivot.AGG_TYPES if t.startswith(agg_type)]
            if len(selected_agg_types) != 1:
                raise Exception(f"Invalid agg type: {agg_type}")
            self.agg_type = selected_agg_types[0]
        else:
            self.agg_type = Pivot.COUNT
        self.header = header
        self.gen_keys = gen_keys
        self.sort_off = sort_off
        self.X = {}
        self.Y = {}
        self.Z = {}
        self.data = []

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
        if self.agg_type == Pivot.COUNT:
            return
        elif self.agg_type == Pivot.SUM:
            for key in self.Z:
                self.Z[key] = sum(self.Z[key])
        elif self.agg_type == Pivot.PRODUCT:
            for key in self.Z:
                self.Z[key] = prod(self.Z[key])
        elif self.agg_type == Pivot.MEAN:
            for key in self.Z:
                self.Z[key] = sum(self.Z[key]) / len(self.Z[key])

    def pivot(self):
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
