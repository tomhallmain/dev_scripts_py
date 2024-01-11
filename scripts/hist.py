
import re
import sys

n_bins = 10
max_bar_len = 15
bar = '+' * max_bar_len
num_re = re.compile(r"^\s*\$?-?\$?[0-9]*\.?[0-9]+\s*$")
decimal_re = re.compile(r"^\s*\$?-?\$?[0-9]*\.[0-9]+\s*$")
float_re = re.compile(r"^\s*-?[0-9]\.[0-9]+(E|e)(\+|-)?[0-9]+\s*$")

def any_fmt_num(str):
    return num_re.match(str) or decimal_re.match(str) or float_re.match(str)

def get_or_set_trunc_val(val, trunc_val):
    if val in trunc_val:
        return trunc_val[val]
    large_val = val > 999
    large_dec = re.search(r"\.[0-9]{3,}", val)
    if (large_val and large_dec) or re.match(r"^-?[0-9]*\.?[0-9]+(E|e)\+?([4-9]|[1-9][0-9]+)$", val):
        trunc_val[val] = int(val)
    else:
        trunc_val[val] = round(float(val), 6)
    return trunc_val[val]

def main():
    counts = {}
    max_f_set = {}
    max = {}
    min = {}
    rec = {}
    headers = {}
    trunc_val = {}

    for line in sys.stdin:
        fields = line.split()
        for f in range(len(fields)):
            if not any_fmt_num(fields[f]):
                if not headers:
                    headers[f] = fields[f].replace(" ", "").replace(",", "")
                continue
            fval = get_or_set_trunc_val(fields[f].replace(" ", "").replace("(", "-").replace(")", "").replace("$", "").replace(",", ""), trunc_val)
            if (f, fval) not in counts:
                rec[f] = rec.get(f, 0) + 1
            counts[(f, fval)] = counts.get((f, fval), 0) + 1
            if f not in max_f_set:
                max[f] = fval
                max_f_set[f] = 1
            if fval < min.get(f, float('inf')):
                min[f] = fval
            elif fval > max[f]:
                max[f] = fval

    # rest of the code...

if __name__ == "__main__":
    main()
