import sys
import re
from collections import defaultdict


def field_uniques_main(fields_str=None, min_count=0, input_stream=None):
    if input_stream is None:
        input_stream = sys.stdin

    OFS = " "
    fields = []

    if fields_str:
        if re.search("[A-z]+", fields_str):
            fields.append(0)
        else:
            fields = list(map(int, re.split("[ ,|:;._]+", fields_str)))
    else:
        fields.append(0)

    counts = defaultdict(int)
    printed_vals = []

    for line in input_stream:
        parts = line.split()
        val = OFS.join(parts[field - 1] for field in fields if field - 1 < len(parts))
        counts[val] += 1

        if val not in printed_vals and counts[val] > min_count:
            print(val)
            printed_vals.append(val)


if __name__ == "__main__":
    fields_arg = sys.argv[1] if len(sys.argv) > 1 else None
    field_uniques_main(fields_arg)
