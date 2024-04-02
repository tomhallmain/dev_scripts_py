
class DataTransposer:
    def __init__(self, data_file, ofs=","):
        self.data_file = data_file
        self.ofs = ofs

    def transpose(self):
        transposed_data = self.data_file.transpose()
        for i in range(len(transposed_data)):
            transposed_data.append(self.ofs.join(transposed_data[i]))
        print('\n'.join(transposed_data))

