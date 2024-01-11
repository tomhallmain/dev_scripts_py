import random
import time
import re
import sys

def randomize_text(mode, text):
    chars_seen = 0
    
    if not mode or mode == "" or "number".startswith(mode):
        mode = 0 # Gen random number
    elif "text".startswith(mode):
        mode = 1
    else:
        print("[mode] not understood - available options: [number|text]")
        sys.exit(1)

    if mode == 0:
        print(random.random())
        sys.exit(0)

    if mode == 1:
        for f in text.split():
            chars_seen += 1

            # Soft randomization, only randomize these character classes
            if re.match(r'[0-9A-Za-z]', f): 
                if chars_seen % 150 == 0:
                    random.seed(time.time())
                if re.match(r'[0-9]', f):
                    print(chr(int(random.random() * (57 - 48)) + 48), end="")
                elif re.match(r'[A-Z]', f):
                    print(chr(int(random.random() * (90 - 65)) + 65), end="")
                else:
                    print(chr(int(random.random() * (121 - 97)) + 97), end="")
            else:
                print(f, end="")
        print("")
