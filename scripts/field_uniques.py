import sys
import re
from collections import defaultdict

# Set the fields as command line arguments
fields = sys.argv[1] if len(sys.argv) > 1 else None
min = 0
Fields = []

if fields:
    if re.search("[A-z]+", fields):
        Fields.append(0)
    else:
        Fields = list(map(int, re.split("[ ,|:;._]+", fields)))
else:
    Fields.append(0)
len_f = len(Fields)
_ = defaultdict(int)
HasPrintedVals = {}

for line in sys.stdin:
    parts = line.split()
    val = " ".join(parts[field - 1] for field in Fields)
    _[val] += 1

    if val not in HasPrintedVals and _[val] > min:
        print(val)
        HasPrintedVals[val] = 1

