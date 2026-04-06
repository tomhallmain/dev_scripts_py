import codecs
import fnmatch
import os
import platform
import re
import sys
from typing import Optional, Tuple


def re_unescape(pattern: str) -> str:
    """Decode escapes in a regex source string. ``re.unescape`` is Python 3.11+."""
    unescape = getattr(re, "unescape", None)
    if unescape is not None:
        return unescape(pattern)
    return codecs.decode(pattern.encode("latin1"), "unicode_escape")


def parse_line_drop_count(s: Optional[str], *, default: int = 1) -> int:
    """
    Parse an optional non-negative integer (e.g. ``n_lines`` to drop from the top of a file).
    ``None`` or ``""`` returns ``default``. Used by ``ds decap`` and similar commands.
    """
    if s is None or s == "":
        return default
    if not re.fullmatch(r"-?\d+", s):
        raise ValueError("n_lines must be an integer")
    n = int(s)
    if n < 0:
        raise ValueError("n_lines must be non-negative")
    return n


def parse_decap_args(args: Tuple[str, ...], stdin_text: Optional[str]) -> int:
    """
    Return how many leading lines ``ds decap`` should remove. Validates argument counts.

    ``stdin_text`` is ``None`` when stdin was not read (TTY); otherwise it is the result of
    ``sys.stdin.read()`` (possibly ``""``).
    """
    args = tuple(args)
    if stdin_text is None:
        if not args:
            raise ValueError("decap requires a FILE or data on stdin")
        if len(args) > 2:
            raise ValueError("too many arguments; expected FILE [n_lines]")
        return parse_line_drop_count(args[1] if len(args) > 1 else None)
    if stdin_text == "" and args and os.path.isfile(args[0]):
        if len(args) > 2:
            raise ValueError("too many arguments; expected FILE [n_lines]")
        return parse_line_drop_count(args[1] if len(args) > 1 else None)
    if len(args) > 1:
        raise ValueError("with stdin, at most one argument is allowed (n_lines)")
    return parse_line_drop_count(args[0] if args else None)


class _Getch:
    """
    Gets a single character from standard input. Does not echo to the screen.
    """
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()

class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()

class Utils:
    DS_SEP = "@@@"
    DEBUG = True
    TEMP_FILE_LOCATION = "/tmp/dev_scripts_py/"
    COMMON_FS = [' ', '\t', ',', ';', ':', '|']
    SINGLE_QUOTE = "'"
    DOUBLE_QUOTE = "\""
    START_DIR = None

    @staticmethod
    def set_start_dir(start_dir):
        Utils.START_DIR = start_dir

    @staticmethod
    def resolve_relative_path(path, return_abs_path=False):
        if path is None:
            return path
        if os.path.abspath(path) == path:
            if return_abs_path:
                return os.path.normpath(os.path.abspath(path))
            return os.path.normpath(path)
        if Utils.START_DIR is None:
            print("No start dir set, relative paths may be incorrect.") # TODO error print or just better implementation
            if return_abs_path:
                return os.path.normpath(os.path.abspath(path))
            return os.path.normpath(path)
        if path.startswith("."):
            if path.startswith(".."):
                raise Exception("Unhandled path, use absolute path instead: " + path)
            path = os.path.normpath(Utils.START_DIR + path[1:])
        else:
            path = os.path.normpath(os.path.join(Utils.START_DIR, path))
        if return_abs_path:
            return os.path.normpath(os.path.abspath(path))
        return path

    @staticmethod
    def set_debug(debug=False):
        Utils.DEBUG = debug

    @staticmethod
    def debug_print(message, context="dev_scripts_py"):
        if Utils.DEBUG:
            print(f"{context}: {message}")

    @staticmethod
    def stdin_open():
        return sys.stdin.isatty() # TODO not working as expected

    @staticmethod
    def get_file_extension(filepath):
        # todo use os path
        if '.' in filepath:
            filename, extension = filepath.rsplit('.', 1)
        else:
            extension = None
        return extension
    
    @staticmethod
    def file_check(tf, check_writable=False, allow_binary=False, enable_search=None):
        if not tf:
            raise ValueError('File not provided!')

        filelike = os.path.exists(tf) and not os.path.isdir(tf)

        if check_writable:
            if not (os.access(tf, os.W_OK) and os.path.isfile(tf)):
                raise ValueError(f'File "{tf}" is not writable')
        elif enable_search:
            if filelike:
                if not allow_binary and not re.match(r'/dev/fd/', tf) and os.path.getsize(tf) > 0:
                    with open(tf, 'rb') as f:
                        if b'\0' in f.read():
                            raise ValueError(f'Found file "{tf}" Binary files have been disallowed for this command')
                return tf
            else:
                f = None
                if allow_binary:
                    for root, dirnames, filenames in os.walk('.'):
                        for filename in fnmatch.filter(filenames, '*' + tf + '*'):
                            f = os.path.join(root, filename)
                            break
                else:
                    for root, dirnames, filenames in os.walk('.'):
                        for filename in fnmatch.filter(filenames, '*' + tf + '*'):
                            f = os.path.join(root, filename)
                            with open(f, 'rb') as file:
                                if b'\0' not in file.read():
                                    break

                if not f or not os.path.isfile(f):
                    raise ValueError(f'File "{tf}" not provided or invalid')
                conf = input(f'Arg is not a file - run on closest match {f}? (y/n)')
                if conf == 'y':
                    return f
                else:
                    raise ValueError(f'File "{f}" not provided or invalid')

        if not filelike:
            raise ValueError(f'File "{tf}" not provided or invalid')

        if not allow_binary and not re.match(r'/dev/fd/', tf) and os.path.getsize(tf) > 0:
            with open(tf, 'rb') as f:
                if b'\0' in f.read():
                    raise ValueError(f'Found file "{tf}" Binary files have been disallowed for this command')

        return tf

    # ** Run ds:fit on output only if to a terminal: data | ds:ttyf [FS] [run_fit=t] [fit_awkargs]
    # @staticmethod
    # def ttyf(fit, FS, debug, fit_args):
    #     if fit == "t" and os.isatty(1):
    #         if debug:
    #             return sys.stdin.read()
    #         elif FS:
    #             return fit(FS=FS, *fit_args)
    #         else:
    #             return fit(*fit_args)
    #     else:
    #         return sys.stdin.read()

    @staticmethod
    def get_os():
        return platform.system()

    @staticmethod
    def string_distance(s, t):
        # create two work vectors of integer distances
        v0 = [0] * (len(t) + 1)
        v1 = [0] * (len(t) + 1)

        # initialize v0 (the previous row of distances)
        # this row is A[0][i]: edit distance from an empty s to t;
        # that distance is the number of characters to append to  s to make t.
        for i in range(len(t) + 1):
            v0[i] = i

        for i in range(len(s)):
            # calculate v1 (current row distances) from the previous row v0

            # first element of v1 is A[i + 1][0]
            # edit distance is delete (i + 1) chars from s to match empty t
            v1[0] = i + 1

            for j in range(len(t)):
                # calculating costs for A[i + 1][j + 1]
                deletion_cost = v0[j + 1] + 1
                insertion_cost = v1[j] + 1
                substitution_cost = v0[j] if s[i] == t[j] else v0[j] + 1

                v1[j + 1] = min(deletion_cost, insertion_cost, substitution_cost)
            # copy v1 (current row) to v0 (previous row) for next iteration
            v0,v1 = v1,v0
        # after the last swap, the results of v1 are now in v0
        return v0[len(t)]

    @staticmethod
    def identify_string_differences(s, t, unicode_escape=False, debug=False):
        if debug:
            print(f"Expected:\n{s}")
            print(f"Actual:\n{t}")
        len_s = len(s)
        len_t = len(t)
        if len_s == 0:
            if len_t == 0:
                return None
            return f"EXPECTED:\n[]\nACTUAL:\n[{t}]"
        elif len_t == 0:
            return f"EXPECTED:\n[{s}]\nACTUAL:\n[]"
        out_s = ""
        out_t = ""
        max_len = max(len_s, len_t)
        has_found_one_difference = False
        has_found_difference = False
        to_close_s = False
        to_close_t = False
        for i in range(max_len):
            c_s = None
            c_t = None
            if i < len_s:
                c_s = s[i]
            if i < len_t:
                c_t = t[i]
            if c_s is not None and c_t is not None:
                if c_s == c_t:
                    if has_found_difference:
                        has_found_difference = False
                        out_s += "]"
                        out_t += "]"
                    out_s += c_s
                    out_t += c_t
                else:
                    if not has_found_difference:
                        has_found_difference = True
                        has_found_one_difference = True
                        out_s += "["
                        out_t += "["
                    if unicode_escape:
                        out_s += repr(c_s)
                        out_t += repr(c_t)
                    else:
                        out_s += c_s
                        out_t += c_t
            elif c_s is not None:
                if not has_found_difference:
                    has_found_difference = True
                    has_found_one_difference = True
                    to_close_s = True
                    out_s += "["
                if unicode_escape:
                    out_s += repr(c_s)
                else:
                    out_s += c_s
            elif c_t is not None:
                if not has_found_difference:
                    has_found_difference = True
                    has_found_one_difference = True
                    to_close_t = True
                    out_t += "["
                if unicode_escape:
                    out_t += repr(c_t)
                else:
                    out_t += c_t

        if not has_found_one_difference:
            Utils.debug_print("No differences were found between the two strings!", "utils")
            return None

        if to_close_s:
            out_s += "]"
        if to_close_t:
            out_t += "]"

        return f"EXPECTED:\n{out_s}\nACTUAL:\n{out_t}"

    @staticmethod
    def longest_common_substring(str1, str2):
        m = [[0] * (1 + len(str2)) for _ in range(1 + len(str1))]
        longest, x_longest = 0, 0
        for x in range(1, 1 + len(str1)):
            for y in range(1, 1 + len(str2)):
                if str1[x - 1] == str2[y - 1]:
                    m[x][y] = m[x - 1][y - 1] + 1
                    if m[x][y] > longest:
                        longest = m[x][y]
                        x_longest = x
                else:
                    m[x][y] = 0
        return str1[x_longest - longest: x_longest]

    @staticmethod
    def shared_elements(list1, list2):
       return any(item in list1 for item in list2)

    @staticmethod
    def get_list_from_string(s, sep=","):
        if s is None or s.strip() == "":
            return []
        return [x.strip() for x in s.split(sep)]
