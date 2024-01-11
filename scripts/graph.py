# Python 3
import sys
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--print_bases", help="With this option set, resulting graph output includes bases.", action="store_true")
    args = parser.parse_args()
    
    shoots = {}
    bases = {}
    cycles = {}

    for line in sys.stdin:
        line = line.strip()
        if line:
            parts = line.split()
            if len(parts) > 1:
                shoots[parts[0]] = parts[1]
                bases[parts[1]] = 1
            elif len(parts) == 1:
                bases[parts[0]] = 1

    if args.print_bases:
        for base in bases:
            if base not in shoots:
                print(base)

    for shoot in shoots:
        if shoots[shoot] and (args.print_bases or shoot not in bases):
            if shoot == shoots[shoot]:
                cycles[shoot] = 1
                continue
            print(backtrace(shoot, shoots[shoot], shoots))

    if cycles:
        print(f"WARNING: {len(cycles)} cycles found!")
        for cycle in cycles:
            print(f"CYCLENODE__ {cycle}")
        exit(1)
def backtrace(start, test_base, shoots):
    if test_base in shoots:
        return extend(backtrace(test_base, shoots[test_base], shoots), start)
    return extend(test_base, start)
def extend(branch, offshoot):
    return f"{branch} {offshoot}"

if __name__ == "__main__":
    main()
