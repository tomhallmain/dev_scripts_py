import sys
import re

def print_formatted_index(_index, space, max):
    if space:
        len_max = len(str(max)) if max else 6
        print("{:>{}}".format(_index, len_max), end="")
    else:
        print(_index, end="")

def index_main(data_file, header):
    space_fs = 0
    if re.match(r'\[\[:space:\]\]\{2.\}', data_file.field_separator):
        FS = "  "
        space_fs = 1
    elif re.match(r'\[.+\]', data_file.field_separator):
        FS = " "
        space_fs = 1
    elif data_file.field_separator.startswith('\\ '):
        FS = "  "
        space_fs = 1
    else:
        FS = data_file.field_separator

    space = space_fs and not sys.stdout.isatty()
    start_mod = 0 if header else 1
    max_nr = data_file.n_rows

    index_cols = True
    with data_file.read() as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if index_cols and i == 1:
                print_formatted_index("", space, max_nr)
                for f_i, field in enumerate(line.split(FS), start=1):
                    print(FS + str(f_i), end="")
                print()

            i = i - start_mod
            print_formatted_index(i, space, max_nr)
            print(FS + line)

