import fnmatch
import os
import platform
import re
import sys

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
    def debug_print(message):
        if Utils.DEBUG:
            print(message)

    @staticmethod
    def stdin_open():
        return sys.stdin.isatty()

    @staticmethod
    def get_file_extension(filepath):
        # todo use os path
        filename, extension = filepath.rsplit('.', 1)
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
