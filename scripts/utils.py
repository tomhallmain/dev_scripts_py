import fnmatch
import os
import platform
import re
import sys

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
    DEBUG = True # TODO figure out how to fix this
    TEMP_FILE_LOCATION = "/tmp/dev_scripts_py/"
    COMMON_FS = [' ', '\t', ',', ';', ':', '|']
    SINGLE_QUOTE = "'"
    DOUBLE_QUOTE = "\""

    @staticmethod
    def set_debug(debug=False):
        Utils.DEBUG = debug

    @staticmethod
    def debug_print(message, context="dev_scripts_py"):
        if Utils.DEBUG:
            print(f"{context}: {message}")

    @staticmethod
    def stdin_open():
        return sys.stdin.isatty()

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
    def shared_elements(list1, list2):
       return any(item in list1 for item in list2)