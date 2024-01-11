import sys
import re
import os
def print_formatted_index(_index, space, max):
    if space:
        len_max = len(str(max)) if max else 6
        print("{:>{}}".format(_index, len_max), end="")
    else:
        print(_index, end="")

def main():
    space_fs = 0
    FS = sys.argv[1] if len(sys.argv) > 1 else " "
    if re.search(r'\[\[:space:\]\]\{2.\}', FS):
        FS = "  "
        space_fs = 1
    elif re.search(r'\[.+\]', FS):
        FS = " "
        space_fs = 1
    elif FS.startswith('\\ '):
        FS = "  "
        space_fs = 1
    else:
        FS = re.escape(FS)

    space = space_fs and not sys.stdout.isatty()
    start_mod = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0

    max_nr = 0
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            max_nr = sum(1 for _ in f)

    index_cols = True
    with open(sys.argv[1]) as f:
        for i, line in enumerate(f, start=1):
            if index_cols and i < 2:
                print_formatted_index("", space, max_nr)
                for f_i, _ in enumerate(line.split(FS), start=1):
                    print(FS + str(f_i), end="")
                print()

            i = i - start_mod
            print_formatted_index(i, space, max_nr)
            print(FS + line, end="")

    if i == 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
