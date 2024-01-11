import re
import sys
from termcolor import colored

class DiffColor:
    def __init__(self, tty_half):
        self.bdiff = r" \|($| )"
        self.ldiff = r" <$"
        self.rdiff = r" > ?$"

        self.red = 'red'
        self.cyan = 'cyan'
        self.mag = 'magenta'

        self.left_n_chars = tty_half - 2
        self.diff_start = tty_half - 1
        self.right_start = tty_half + 2

        if tty_half % 2 == 0:
            self.left_n_chars -= 1
            self.diff_start -= 1
            self.right_start -= 1

    def color_diff(self, lines):
        for line in lines:
            coloron = False
            left = line[:self.left_n_chars]
            diff = line[self.diff_start:self.diff_start+3]
            right = line[self.right_start:]

            if re.search(self.ldiff, diff):
                print(colored(line, self.cyan))
            elif re.search(self.rdiff, diff):
                print(colored(line, self.red))
            elif re.search(self.bdiff, diff):
                self.color_chars(line, left, right, diff)
            else:
                print(line)

    def color_chars(self, line, left, right, diff):
        lchars = list(left)
        rchars = list(right)
        l_len = len(lchars)
        r_len = len(rchars)
        j = 1
        recap = False
        recaps = 0

        for i in range(l_len):
            if lchars[i] == rchars[j-1]:
                if coloron:
                    coloron = False
                    sys.stdout.write('\033[0m')
                j += 1
            else:
                if recap:
                    recap = False
                tmp_j = j
                for k in range(j-1, l_len):
                    mtch = lchars[i] == rchars[k]
                    mtch1 = lchars[i+1] == rchars[k+1] if i+1 < l_len and k+1 < r_len else False
                    mtch2 = lchars[i+2] == rchars[k+2] if i+2 < l_len and k+2 < r_len else False
                    mtch3 = lchars[i+3] == rchars[k+3] if i+3 < l_len and k+3 < r_len else False
                    if mtch and mtch1 and mtch2 and mtch3:
                        recap = True
                        recaps += 1
                        j = k + recaps + 1
                        coloron = False
                        sys.stdout.write('\033[0m')
                        break
                    j = tmp_j
                if not recap and not coloron:
                    sys.stdout.write(colored('', self.cyan))
                    coloron = True
            sys.stdout.write("%s" % lchars[i])

        sys.stdout.write(colored(diff, self.mag))
        j = 1
        recap = False
        recaps = 0
        for i in range(r_len):
            if rchars[i] == lchars[j-1]:
                if coloron:
                    coloron = False
                    sys.stdout.write('\033[0m')
                j += 1
            else:
                if recap:
                    recap = False
                tmp_j = j
                for k in range(j-1, r_len):
                    mtch = rchars[i] == lchars[k]
                    mtch1 = rchars[i+1] == lchars[k+1] if i+1 < r_len and k+1 < l_len else False
                    mtch2 = rchars[i+2] == lchars[k+2] if i+2 < r_len and k+2 < l_len else False
                    mtch3 = rchars[i+3] == lchars[k+3] if i+3 < r_len and k+3 < l_len else False
                    if mtch and mtch1 and mtch2 and mtch3:
                        recap = True
                        recaps += 1
                        j = k + recaps + 1
                        coloron = False
                        sys.stdout.write('\033[0m')
                        break
                    j = tmp_j
                if not recap and not coloron:
                    sys.stdout.write(colored('', self.red))
                    coloron = True
            sys.stdout.write("%s" % rchars[i])

        print("")
