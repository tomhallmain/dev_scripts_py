import sys


def SimplePrintForMultiplier(MSets, MSetLen, start, max_val, mult, max_mult, advance_val=None):
    iteration = max_mult - mult + 1
    init_adv = advance_val
    dec_mult = mult - 1
    for i in range(start, max_val + 1):
        if iteration < 2:
            advance_val = MSets[(iteration, i)]
        else:
            advance_val = str(init_adv) + ' ' + str(MSets[(iteration, i)])
        if mult > 1:
            SimplePrintForMultiplier(MSets, MSetLen, 1, MSetLen[iteration + 1], dec_mult, max_mult, advance_val)
        else:
            print(advance_val)


def product_main(filenames):
    MSets = {}
    MSetLen = {}
    set_base = 0
    prev_file = None

    for filename in filenames:
        with open(filename, 'r') as f:
            if filename != prev_file:
                set_base += 1
            prev_file = filename
            MSetLen[set_base] = 0
            for line in f:
                MSetLen[set_base] += 1
                MSets[(set_base, MSetLen[set_base])] = line.strip()

    msets_len = set_base
    if msets_len and MSetLen.get(1):
        SimplePrintForMultiplier(MSets, MSetLen, 1, MSetLen[1], msets_len, msets_len)


if __name__ == "__main__":
    product_main(sys.argv[1:])
