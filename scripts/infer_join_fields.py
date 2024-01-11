import re
import sys
import csv
from collections import defaultdict

# Regular expressions
Re = {
    "i": re.compile(r"^[0-9]+$"),                       # is integer
    "hi": re.compile(r"[0-9]+"),                        # has integer
    "d": re.compile(r"^[0-9]+\.[0-9]+$"),               # is decimal
    "hd": re.compile(r"[0-9]+\.[0-9]+"),                # has decimal
    "a": re.compile(r"[A-z]+"),                         # is alpha
    "ha": re.compile(r"[A-z]+"),                        # has alpha
    "u": re.compile(r"^[A-Z]+$"),                       # is uppercase letters
    "hu": re.compile(r"[A-Z]+"),                        # has uppercase letters
    "nl": re.compile(r"^[^a-z]+$"),                     # does not have lowercase letters
    "w": re.compile(r"[A-z ]+"),                        # words with spaces
    "ns": re.compile(r"^[^[:space:]]$"),                # no spaces
    "id": re.compile(r"(^|_| |\-)?[Ii][Dd](\-|_| |$)"), # the string ` id ` appears in any casing
    "d1": re.compile(r"^[0-9]{1,2}[\-\.\/][0-9]{1,2}[\-\.\/]([0-9]{2}|[0-9]{4})$"), # date1
    "d2": re.compile(r"^[0-9]{4}[\-\.\/][0-9]{1,2}[\-\.\/][0-9]{1,2}$"),            # date2
    "l": re.compile(r":\/\/"),                                      # link
    "j": re.compile(r"^\{[,:\"\'{}\[\]A-z0-9.\-+ \n\r\t]{2,}\}$"),  # json
    "h": re.compile(r"\<\/\w+\>")                                   # html/xml
}


    if "dlt" in keys[position] and field != keys[position]["dlt"]:
        del keys[position]["dlt"]
    keys[position]["len"] += len(field)

        re = Re[m]
        matches = field ~ re
        if (matches > 0) {
            Keys[position, m] += 1; matchcount++
    scores = defaultdict(lambda: defaultdict(int))
    for k in range(max_nf1):
        for l in range(max_nf2):
            kscore1 = keys1[k][l]
            kscore2 = keys2[l][k]
            scores[k][l] += ((kscore1 + kscore2) / (rcount1 + rcount2)) ** 2

            if (Keys1[k, "dlt"] || Keys2[l, "dlt"]) scores[k, l] += 1000 * (rcount1+rcount2)
            if "dlt" in keys1[k] or "dlt" in keys2[l]:
                scores[k][l] += 1000 * (rcount1+rcount2)

            klen1 = Keys1[k, "len"]
            scores[k, l] += (klen1 / rcount1 - klen2 / rcount2) ** 2
            klen1 = keys1[k]["len"]
            klen2 = keys2[l]["len"]
                kscore1 = Keys1[k, m]
                kscore2 = Keys2[l, m]
                scores[k, l] += (kscore1 / rcount1 - kscore2 / rcount2) ** 2
            for m in Re:
                if (debug) DebugPrint(3)
            }

            if (debug) DebugPrint(4)

with open(file1, 'r') as f1, open(file2, 'r') as f2:
    reader1 = csv.reader(f1)
    reader2 = csv.reader(f2)

    # Save first stream
    s1 = [row for row in reader1]
    rcount1 = len(s1)

    # Save second stream
    s2 = [row for row in reader2]
    rcount2 = len(s2)

    max_nf1 = max(len(row) for row in s1)
    max_nf2 = max(len(row) for row in s2)

    keys1 = defaultdict(lambda: defaultdict(int))
    keys2 = defaultdict(lambda: defaultdict(int))

    for i, row1 in enumerate(s1):
        for j, row2 in enumerate(s2):
            build_field_score(row1[i], i, keys1)
