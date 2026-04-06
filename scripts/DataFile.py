import csv
import os
import re
import random
import sys
import tempfile
from io import StringIO
from typing import Optional

from .utils import Utils
from .infer_field_separator import SeparatorInference

class DataFile:
    CACHE = []

    def __init__(self, file_path, field_separator=None, *, stdin_text=None):
        """
        ``file_path`` may be ``None`` / ``""`` for piped stdin.

        ``stdin_text``: if set, piped content is taken from this string instead of reading
        :data:`sys.stdin` (so the CLI can pass a body already read once, e.g. from Click).
        """
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
        self._stdin_text = stdin_text
        self.check_and_setup()
        DataFile.CACHE.append(self)

    @staticmethod
    def from_cli_file_or_stdin(
        path_candidate,
        stdin_text,
        *,
        field_separator=None,
        output_field_separator=None,
    ):
        """
        Resolve **file vs stdin** for typical ``ds`` commands: optional ``FILE`` plus piped body.

        - ``stdin_text is None``: nothing was read from stdin (interactive TTY) — ``path_candidate``
          must be a readable file path.
        - ``stdin_text`` is not ``None``: stdin was already consumed (possibly ``""``). If it is
          empty and ``path_candidate`` points to an existing file (CliRunner “empty pipe” quirk),
          open that file; otherwise materialize ``stdin_text`` as piped data.

        ``path_candidate`` may be a first positional that is *not* a file when stdin has content;
        it is ignored unless the empty-string + file heuristic applies.

        Optional ``field_separator`` / ``output_field_separator`` are passed through to
        :class:`DataFile` (output defaults to input separator when omitted).
        """
        if stdin_text is None:
            if not path_candidate:
                raise Exception("file path required when stdin is a TTY")
            df = DataFile(path_candidate, field_separator)
        elif stdin_text == "" and path_candidate and os.path.isfile(path_candidate):
            df = DataFile(path_candidate, field_separator)
        else:
            df = DataFile(None, field_separator, stdin_text=stdin_text)
        if output_field_separator is not None:
            df.output_field_separator = output_field_separator
        return df

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
            if self._stdin_text is not None:
                with tempfile.NamedTemporaryFile(
                    "w", encoding="utf-8", prefix=Utils.TEMP_FILE_LOCATION, delete=False
                ) as temp_file:
                    temp_file.write(self._stdin_text)
                    self.file_path = temp_file.name
                self.n_rows = len(self._stdin_text.splitlines()) if self._stdin_text else 0
                Utils.debug_print("Created temp file from stdin_text: " + self.file_path, "DataFile")
            else:
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

    def read_raw_lines(self):
        """Full text lines as in the file (newlines preserved), UTF-8. For non-field-aware tools."""
        with open(self.file_path, encoding="utf-8", errors="replace") as f:
            return f.readlines()

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
        if not self.data:
            if not self.field_separator:
                self.get_field_separator()
            self.get_data()
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

    def print_transposed(self, *, output_sep: Optional[str] = None) -> None:
        """Infer separator if needed, load rows, transpose, print one line per original column."""
        self.get_field_separator()
        sep = output_sep if output_sep is not None else (
            self.output_field_separator or self.field_separator or ""
        )
        for line in self.transpose():
            print(sep.join(str(x) for x in line))

    @staticmethod
    def _awk_expr_to_python(expr: str) -> str:
        """Convert a small AWK-like expression into Python syntax."""
        s = expr.strip().replace("&&", " and ").replace("||", " or ")
        q = s.find("?")
        if q == -1:
            return s
        c = s.find(":", q + 1)
        if c == -1:
            return s
        cond = s[:q].strip()
        left = s[q + 1:c].strip()
        right = s[c + 1:].strip()
        return f"({left}) if ({cond}) else ({right})"

    @staticmethod
    def _coerce_awk_val(raw: str):
        if raw == "":
            return 0
        if re.fullmatch(r"-?\d+", raw):
            return int(raw)
        if re.fullmatch(r"-?\d+\.\d+", raw):
            return float(raw)
        return raw

    def field_replace(self, replacement_expr: str, *, key: int = 1, pattern: str = "") -> str:
        """
        Replace one field using an expression over ``val`` for each matching row.

        ``replacement_expr`` follows the shell helper style (for example:
        ``val > 2 ? -1 : 11``). ``pattern`` is a regex tested against the raw field text.
        """
        if key < 1:
            raise Exception(f"Invalid key provided: {key}")
        self.get_field_separator()
        fs = self.field_separator or ""
        rows = self.get_data()
        rx = re.compile(pattern) if pattern is not None else re.compile("")
        py_expr = self._awk_expr_to_python(replacement_expr)

        out_lines = []
        idx = key - 1
        for row in rows:
            if idx >= len(row):
                row.extend([""] * (idx + 1 - len(row)))
            raw_val = row[idx]
            if rx.search(raw_val):
                val = self._coerce_awk_val(raw_val)
                row[idx] = str(
                    eval(  # noqa: S307 - command intentionally evaluates user expression
                        py_expr,
                        {"__builtins__": {}},
                        {"val": val, "rand": random.random},
                    )
                )
            out_lines.append(fs.join(row))
        return "\n".join(out_lines)

    def convert_field_separator(self, new_separator: str = ",") -> str:
        """
        Render rows using ``new_separator`` while preserving field structure.

        For comma output, uses :mod:`csv` writer semantics so fields containing commas/quotes are
        escaped correctly.
        """
        self.get_field_separator()
        rows = self.get_data()
        if new_separator == ",":
            buf = StringIO()
            w = csv.writer(buf, lineterminator="\n")
            for row in rows:
                w.writerow(row)
            return buf.getvalue().rstrip("\n")
        return "\n".join(new_separator.join(row) for row in rows)

    @staticmethod
    def cleanup():
        for data_file in DataFile.CACHE:
            data_file.cleanup_temp_file()
