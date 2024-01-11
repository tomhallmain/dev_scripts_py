import re
import sys
def prepare_line(line):
    line = re.sub('_', ' ', line)
    line = re.sub('\.', ' ', line)
    line = re.sub(' +', ' ', line)
    return space_case_vars(line)

def space_case_vars(s):
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', s)

def gen_pc(word, idx):
    if idx < 2:
        return word.capitalize()
    elif re.match(r'^(and|as|but|for|if|nor|or|so|yet|a|an|the|upon|from|as|at|by|for|in|of|off|on|per|to|up|via)$', word):
        return word
    else:
        return word.capitalize()

def gen_cc(word, idx):
    if idx == 1:
        start_char = word[0].lower()
    else:
        start_char = word[0].upper()
  
    return start_char + word[1:].lower()

def process_line(line, tocase, filter):
    if filter and not re.search(filter, line):
        return

    if tocase.startswith('lc'):
        print(line.lower())
    elif tocase.startswith('uc'):
        print(line.upper())
    else:
        words = prepare_line(line).split(' ')
        n_wds = len(words)

        if tocase.startswith('pc'):
            print(' '.join(gen_pc(word, i) for i, word in enumerate(words)))
        elif tocase.startswith('cc') or tocase == 'ucc':
            print(''.join(gen_cc(word, i + 1) for i, word in enumerate(words)))
        elif tocase.startswith('sc'):
            print('_'.join(word.lower() for word in words))
        elif tocase.startswith('vc'):
            print('_'.join(word.upper() for word in words))
        elif tocase.startswith('oc'):
            print('.'.join(word.capitalize() for word in words))

def main():
    tocase = sys.argv[1].lower() if len(sys.argv) > 1 else ''
    filter = sys.argv[2] if len(sys.argv) > 2 else None

    for line in sys.stdin:
        process_line(line.rstrip(), tocase, filter)

if __name__ == '__main__':
    main()
