import os
import sys
import tempfile

from dev_scripts_py.scripts.utils import Utils

class DataFile:
    def __init__(self, file_path, field_separator=None):
        self.is_stdin = file_path == None
        self.file_path = file_path.name # type '_io.TextIOWrapper'
        self.field_separator = field_separator
        self.n_rows = 0
        self.check_and_setup()

    def check_and_setup(self):
        if Utils.stdin_open():
            if self.is_stdin:
                raise Exception("file_path not provided but stdin was closed.")
            else:
                if not os.path.isfile(self.file_path):
                    raise Exception("path provided is not a file: " + self.file_path)
                with open(self.file_path, 'r') as file:
                    for line in file:
                        self.n_rows += 1
        else:
            if not os.path.exists(Utils.TEMP_FILE_LOCATION):
                os.makedirs(Utils.TEMP_FILE_LOCATION)
            with tempfile.NamedTemporaryFile('w', prefix=Utils.TEMP_FILE_LOCATION, delete=False) as temp_file:
                for line in sys.stdin:
                    temp_file.write(line)
                    self.n_rows += 1
            self.file_path = temp_file.name

    def read(self):
        return open(self.file_path, 'r')

    def cleanup(self):
        if self.is_stdin:
            os.remove(self.file_path)
