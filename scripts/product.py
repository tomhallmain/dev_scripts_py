import sys

MSets = {}
MSetLen = {}
set_base = 0
PFILE = None

for filename in sys.argv[1:]:
    with open(filename, 'r') as f:
        if filename != PFILE:
            set_base += 1
        PFILE = filename
        MSetLen[set_base] = 0
        for line in f:
            MSetLen[set_base] += 1
            MSets[(set_base, MSetLen[set_base])] = line.strip()

msets_len = set_base
def SimplePrintForMultiplier(start, max_val, mult, max_mult, advance_val=None):
    iter = max_mult - mult + 1
    init_adv = advance_val
    dec_mult = mult - 1
    for i in range(start, max_val+1):
        if iter < 2:
            advance_val = MSets[(iter, i)]
        else:
            advance_val = str(init_adv) + ' ' + str(MSets[(iter, i)])
        if mult > 1:
            SimplePrintForMultiplier(1, MSetLen[iter + 1], dec_mult, max_mult, advance_val)
        else:
            print(advance_val)

SimplePrintForMultiplier(1, MSetLen[1], msets_len, msets_len)
