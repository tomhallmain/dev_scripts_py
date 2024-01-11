import sys

class DataTransposer:
    def __init__(self, input_data):
        self.input_data = input_data
    def transpose(self):
        max_nf = 0
        data = []
        for line in self.input_data:
            fields = line.strip().split()
            if len(fields) > max_nf:
                max_nf = len(fields)
            data.append(fields)

        transposed_data = []
        for i in range(max_nf):
            transposed_line = []
            for j in range(len(data)):
                try:
                    transposed_line.append(data[j][i])
                except IndexError:
                    transposed_line.append('')
            transposed_data.append(' '.join(transposed_line))

        return '\n'.join(transposed_data)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data_transposer = DataTransposer(f)
            print(data_transposer.transpose())
    else:
        data_transposer = DataTransposer(sys.stdin)
        print(data_transposer.transpose())

