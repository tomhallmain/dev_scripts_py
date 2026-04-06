import os
import textwrap

def print_staggered(file_name, stag_size=5, tty_size=None):
    if tty_size is None:
        try:
            tty_size = os.get_terminal_size().columns
        except OSError:
            tty_size = 80
    space = " " * 100
    stag = space[:stag_size]

    with open(file_name, 'r') as f:
        for line in f:
            fields = line.split()
            spacer = 0
            stag_space = ""

            for field in fields:
                if spacer and tty_size / spacer < 1.5:
                    spacer = 0
                    stag_space = ""

                field_width = tty_size - spacer

                if len(field) > field_width:
                    for subfield in textwrap.wrap(field, field_width):
                        print(stag_space + subfield)
                        field = field[field_width:]

                print(stag_space + field)
                spacer += stag_size
                stag_space += stag
            print("")

if __name__ == "__main__":
    print_staggered('same_file')