import sys
import re
from collections import defaultdict

# Set the fields as command line arguments
fields_str = sys.argv[1] if len(sys.argv) > 1 else None
min = 0
OFS = " " # TODO update
fields = []

if fields_str:
    if re.search("[A-z]+", fields_str):
        fields.append(0)
    else:
        fields = list(map(int, re.split("[ ,|:;._]+", fields_str)))
else:
    fields.append(0)

len_f = len(fields)
_ = defaultdict(int)
printed_vals = []

for line in sys.stdin:
    parts = line.split()
    val = OFS.join(parts[field - 1] for field in fields)
    _[val] += 1

    if val not in printed_vals and _[val] > min:
        print(val)
        printed_vals.append(val)

