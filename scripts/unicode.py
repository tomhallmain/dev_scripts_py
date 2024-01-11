import sys
import re

class Converter:
    def __init__(self, to=0):
        self.to = to
    def convert_line(self, line):
        fields = line.split()
        d = ""
        b = [""] * 4
        if self.to < 1:
            # Codepoint case
            if re.match(r'^[0-1]+', fields[2]):
                b[0] = fields[1][4:8]
                b[1] = fields[2][2:8]

                if re.match(r'^[0-1]+', fields[3]):
                    b[2] = fields[3][2:8]
                    if re.match(r'^[0-1]+', fields[4]):
                        b[3] = fields[4][2:8]
            else:
                b[0] = fields[1][1:8]

            for i in range(len(b)):
                d += b[i]
        elif self.to == 1:
            # Octet/hex case
            for i in range(1, len(fields)):
                if i < 1: 
                    continue
                if re.match(r'^[0-1]+', fields[i]):
                    if d:
                        d += ";" + fields[i]
                    else:
                        d = fields[i]
        print("obase=16; ibase=2; " + d)

    def set_conversion_type(self, conversion_type):
        if conversion_type == "codepoint":
            self.to = 0
        elif conversion_type == "octet" or conversion_type == "hex":
            self.to = 1

    def convert_input(self, input_lines):
        for line in input_lines:
            self.convert_line(line)

if __name__ == "__main__":
    converter = Converter()
    if len(sys.argv) > 1:
        converter.set_conversion_type(sys.argv[1])
    converter.convert_input(sys.stdin)
