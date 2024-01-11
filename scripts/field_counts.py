#!/usr/bin/env python3
import argparse
import re
from collections import defaultdict

# Parsing command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-f', '--fields', help='Fields to be considered for counting.')
parser.add_argument('-m', '--min', type=int, default=0, help='Minimum count to be considered.')
parser.add_argument('-o', '--only_vals', action='store_true', help='Only output the values.')
parser.add_argument('file', help='Input file.')
args = parser.parse_args()

# Preparing field separators
fs = '|||'
fsre = re.compile(r'\|\|\|')

# Preparing fields
if args.fields:
    if re.search(r'[A-z]+', args.fields):
        Fields = [0]
    else:
        Fields = list(map(int, re.split(r'[ ,|\.:;_]+', args.fields)))
else:
    Fields = [1]

counts = not args.only_vals
len_f = len(Fields)

# Counting occurrences
counter = defaultdict(int)
with open(args.file, 'r') as f:
    for line in f:
        line = line.strip()
        if Fields[0] == 1:
            counter[line] += 1
        else:
            key = fs.join(line.split()[field-1] for field in Fields)
            counter[key] += 1

# Printing results
for key, count in counter.items():
    if count > args.min:
        if counts:
            print(f'{count}', end=' ')
        if Fields[0] == 0:
            print(key)
        else:
            print(' '.join(fsre.split(key)))
