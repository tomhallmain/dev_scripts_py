import re
import sys

class TextCaseConverter:
    def __init__(self, tocase="pc", filter=None):
        self.tocase = tocase
        self.filter = filter

    def recase(self, data_file):
        """
        Change the case of lines in a text data file or stdin.
        """
        with data_file.read() as f:
            line = f.readline().strip()
            self.process_line(line)

    def prepare_line(self, line):
        line = re.sub('_', ' ', line)
        line = re.sub('\\.', ' ', line)
        line = re.sub(' +', ' ', line)
        return self.space_case_vars(line)

    def space_case_vars(self, s):
        return re.sub(r'([a-z])([A-Z])', r'\1 \2', s)    

    def gen_pc(self, word, idx):
        if idx < 2:
            return word.capitalize()
        elif re.match(r'^(and|as|but|for|if|nor|or|so|yet|a|an|the|upon|from|as|at|by|for|in|of|off|on|per|to|up|via)$', word):
            return word
        else:
            return word.capitalize()    

    def gen_cc(self, word, idx):
        if idx == 1:
            start_char = word[0].lower()
        else:
            start_char = word[0].upper()

        return start_char + word[1:].lower()    
    
    def process_line(self, line):
        if self.filter and not re.search(self.filter, line):
            return

        if self.tocase.startswith('lc'):
            print(line.lower())
        elif self.tocase.startswith('uc'):
            print(line.upper())
        else:
            words = self.prepare_line(line).split(' ')

            if self.tocase.startswith('pc'):
                print(' '.join(self.gen_pc(word, i) for i, word in enumerate(words)))
            elif self.tocase.startswith('cc') or self.tocase == 'ucc':
                print(''.join(self.gen_cc(word, i + 1) for i, word in enumerate(words)))
            elif self.tocase.startswith('sc'):
                print('_'.join(word.lower() for word in words))
            elif self.tocase.startswith('vc'):
                print('_'.join(word.upper() for word in words))
            elif self.tocase.startswith('oc'):
                print('.'.join(word.capitalize() for word in words))

def main():
    tocase = sys.argv[1].lower() if len(sys.argv) > 1 else ''
    filter = sys.argv[2] if len(sys.argv) > 2 else None
    converter = TextCaseConverter(tocase, filter)
    for line in sys.stdin:
        converter.process_line(line.rstrip())

if __name__ == '__main__':
    main()
