import csv
import os
import re
import sys
import tempfile

from .utils import Utils
from .infer_field_separator import SeparatorInference

class DataFile:
    CACHE = []

    def __init__(self, file_path, field_separator=None):
        self.is_stdin = file_path == None or file_path == ""
        self.file_path = file_path.name if hasattr(file_path, "name") else file_path # can be type '_io.TextIOWrapper'
        self.file_path = Utils.resolve_relative_path(self.file_path)
        self.name = os.path.basename(self.file_path) if self.file_path else "Piped data"
        self.field_separator = field_separator
        self.output_field_separator = field_separator
        self.n_rows = 0
        self.max_nf = 0
        self.line_cursor = -1
        self.data = []
        self.header = None
        self.check_and_setup()
        DataFile.CACHE.append(self)

    def check_and_setup(self):
        if not self.is_stdin:
            if not os.path.isfile(self.file_path):
                raise Exception("path provided is not a file: " + self.file_path)
            with self.read() as f:
                for line in f:
                    self.n_rows += 1
        else:
            if not os.path.exists(Utils.TEMP_FILE_LOCATION):
                os.makedirs(Utils.TEMP_FILE_LOCATION)
            with tempfile.NamedTemporaryFile('w', prefix=Utils.TEMP_FILE_LOCATION, delete=False) as temp_file:
                for line in sys.stdin:
                    temp_file.write(line)
                    self.n_rows += 1
            self.file_path = temp_file.name
            Utils.debug_print("Created temp file: " + self.file_path, "DataFile")

    def extension(self):
        return Utils.get_file_extension(self.file_path) if self.file_path else None

    def read(self):
        return open(self.file_path, 'r')

    def get_data(self):
        """Load ``self.data`` from disk. CSV files use :mod:`csv` (quoted fields); other
        files split lines with the configured field separator (see ``get_field_separator``).
        """
        ext = (self.extension() or "").lower()
        if ext == "csv":
            self.data = []
            with open(self.file_path, newline="", encoding="utf-8") as f:
                for row in csv.reader(f):
                    # Keep empty cells so column indices align with the header / shell FS.
                    line_data = [c.strip() for c in row]
                    self.data.append(line_data)
                    if len(line_data) > self.max_nf:
                        self.max_nf = len(line_data)
            return self.data

        escaped_fs = self.escape_field_separator()

        with self.read() as f:
            line = f.readline()
            while line:
                line = line.strip()
                line_data = re.split(escaped_fs, line)
                self.data.append(line_data)
                if len(line_data) > self.max_nf:
                    self.max_nf = len(line_data)
                line = f.readline()

        return self.data

    def current_line(self):
        return self.data[self.line_cursor]

    def nf(self):
        return len(self.current_line())

    def next_line(self):
        self.line_cursor += 1
        if self.header:
            if self.line_cursor >= len(self.data) - 1:
                return None
        elif self.line_cursor >= len(self.data):
            return None
#        Utils.debug_print(f"line cursor: {self.line_cursor}", "DataFile")
        return self.current_line()

    def get_field_separator(self, overwrite=False, custom=False, use_file_ext=True, high_certainty=False):
        if self.n_rows == 0:
            self.cleanup_temp_file()
            raise Exception("Data file has no data: " + self.name)
        if not self.field_separator or overwrite:
            self.field_separator = SeparatorInference(custom=custom,
                                                      use_file_ext=use_file_ext,
                                                      high_certainty=high_certainty).infer_separator(self)
        if Utils.DEBUG:
            Utils.debug_print(f"{self.name} - FS set: >{self.field_separator}<", "DataFile")
        return self.field_separator

    def set_field_separator(self, field_separator):
        self.field_separator = field_separator

    def set_header(self):
        if self.line_cursor > -1:
            raise Exception("DataFile.set_header must be called on the first line of data.")
        self.line_cursor += 1
        self.header = self.current_line()
        if Utils.DEBUG:
            Utils.debug_print(f"{self.name} - Header set", "DataFile")

    def escape_field_separator(self):
        return re.escape(self.field_separator)

    def cleanup_temp_file(self):
        if self.is_stdin:
            Utils.debug_print("Removing temp file: " + self.file_path, "DataFile")
            try:
                os.remove(self.file_path)
            except Exception:
                Utils.debug_print("Temp file was not removed: " + self.file_path, "DataFile")

    def transpose(self, max_nf=None):
        transposed_data = []
        if max_nf == None or max_nf < 0:
            max_nf = self.max_nf
        for i in range(max_nf):
            transposed_line = []
            for j in range(len(self.data)):
                try:
                    transposed_line.append(self.data[j][i])
                except IndexError:
                    transposed_line.append('')
            transposed_data.append(transposed_line)
        return transposed_data

    @staticmethod
    def cleanup():
        for data_file in DataFile.CACHE:
            data_file.cleanup_temp_file()
