import re
from collections import defaultdict
from itertools import combinations

from .utils import Utils


class FSData:
    def __init__(self, fs):
        """
        Holds info about about a potential field separator.
        """
        self.fs = fs
        self.escaped = re.escape(fs)
        self.total = 0
        self.count = defaultdict(int)
        self.consec_counts = defaultdict(int)
        self.prev_nf = None
        self.quote = None
        self.quote_regex = None

    def quoted_fields_regex(self, q):
        sep = self.escaped
        q = re.escape(q)
        exc = f"[^\\{q}]*[^\\{sep}]*[^\\{q}]+"
        return f'({q}{sep}|{sep}{q}[^\\s]*{sep}|{sep}{q}$|{exc}{q}{sep}|{sep}{exc}{q}{sep}|{sep}{exc}{q}$)'
    
    def get_fields_quote(self, line):
        separator_regex = self.quoted_fields_regex(Utils.DOUBLE_QUOTE)
        if re.search(separator_regex, line):
            self.quote = Utils.DOUBLE_QUOTE
            self.quote_regex = re.compile(separator_regex)
        separator_regex = self.quoted_fields_regex(Utils.SINGLE_QUOTE)
        if re.search(separator_regex, line):
            self.quote = Utils.SINGLE_QUOTE
            self.quote_regex = re.compile(separator_regex)


class CommonFS:
    def __init__(self):
        self.map = {}

        for fs in Utils.COMMON_FS:
            self.map[fs] = FSData(fs)


class CustomFS:
    def __init__(self):
        self.map = defaultdict()
        self.CharFSCount = defaultdict(int)

    def test(self, line, compare=False, max_length=3):
        """
        In the first couple of lines of text data, search for any custom
        fields separators that may be present. On the first line, set up a
        dict of possible values with counts of their numbers of fields. On
        the second line, test the field counts previously seen and add to
        custom field separator data if matching.
        """
        Nonwords = re.split('[A-Za-z0-9(\\^\\)"\']+', line)
        Utils.debug_print(f"Nonwords: {Nonwords}", "inferfs")
        for j, word in enumerate(Nonwords):
            Chars = [char for char in word if not char in ' \n']
            for k, char in enumerate(Chars):
                for i in range(max_length):
                    if i == 0 and char in Utils.COMMON_FS:
                        continue
                    if k > i - 1:
                        char_string = ""
                        for c in range(k + 1):
                            char_string = Chars[k-i] + char_string
                        test = [i for i in re.split(char_string, line)]
                        nf = len(test) - 1
                        if compare:
                            if nf > 1:
                                self.CharFSCount[char_string] += nf
                        elif self.CharFSCount[char_string] == nf:
                            self.create_fs_data(char_string, nf)
    
    def create_fs_data(self, fs, nf):
        fs_data = FSData(fs)
        fs_data.count[0] = nf
        fs_data.count[1] = nf
        fs_data.total = nf * 2
        fs_data.prev_nf = nf
        self.map[fs] = fs_data

    def print_counts(self):
        Utils.debug_print(f"Character Frequency Counts: {self.CharFSCount}", "inferfs")


class SeparatorInference:
    MAX_TESTED_ROWS = 5000
    EXTENSION_CSV = "csv"
    EXTENSION_TSV = "tsv"
    EXTENSION_PROPS = "properties"

    def __init__(self, custom, use_file_ext=True, high_certainty=False, max_rows=1000):
        self.common_fs = CommonFS()
        self.custom = custom
        self.custom_fs = CustomFS()
        self.nr = -1
        self.n_valid_rows = 0
        self.ds_sep = False
        self.use_file_ext = use_file_ext
        self.high_certainty = high_certainty
        self.max_rows = max_rows

    def infer_separator(self, data_file, max_rows=1000):
        """
        Infer the field separator in a text data file. This function 
        uses likelihood of common field separators and commonly found substrings
        in the data up to three characters.
        """
        if self.use_file_ext:
            extension = data_file.extension()
            if extension == SeparatorInference.EXTENSION_CSV:
                return ','
            elif extension == SeparatorInference.EXTENSION_TSV:
                return '\t'
            elif extension == SeparatorInference.EXTENSION_PROPS:
                return '='

        with data_file.read() as f:
            for row in range(SeparatorInference.MAX_TESTED_ROWS):
                line = f.readline().strip()
                Utils.debug_print(f"LINE:: {line}", "inferfs")
                if not line:
                    break
                self.nr += 1
                if len(line) == 0: # skip empty and whitespace lines
                    continue
                self.n_valid_rows += 1
                Utils.debug_print(f"n_valid_rows: {self.n_valid_rows}", "inferfs")
                if self.n_valid_rows > max_rows:
                    break

                # split the line by all separators and count occurrences
                self.process_line(line)

                if self.ds_sep:
                    return Utils.DS_SEP
        
        return self.calculate_best()
    
    def get_nf(self, fs_data, line):
        """
        Determine the number of fields in a line of text for a given potential field separator.
        """
        if self.n_valid_rows < 10 and fs_data.quote is None:
            fs_data.get_fields_quote(line)

        if fs_data.quote is not None:
            nf = 0
            match = fs_data.quote_regex.search(line)
            start, end = match.span()
            qf_line = line[end:]

            while len(qf_line):
                # TODO fix
                Utils.debug_print(qf_line, "inferfs")
                Utils.debug_print("NF: " + str(nf), "inferfs")
                end = len(qf_line)
                match = fs_data.quote_regex.search(qf_line)

                if match is not None:
                    nf += 1
                    start, end = match.span()
                    if start > 1:
                        nf += len(qf_line[0:start-1].split(fs_data.fs))
                else:
                    nf += len(qf_line.split(fs_data.fs))

                qf_line = qf_line[end:]
        else:
            nf = len(line.split(fs_data.fs))

        return nf

    def process_line(self, line):
        # If dev_scripts separator found, it's probably that so skip everything else
        if self.n_valid_rows < 3 and Utils.DS_SEP in line:
            self.ds_sep = True
            return

        # Gather data about each common field separator
        for fs in Utils.COMMON_FS:
            fs_data = self.common_fs.map[fs]
            nf = self.get_nf(fs_data, line)            
            fs_data.count[self.n_valid_rows] = nf
            fs_data.total += nf

            prev_nf = fs_data.prev_nf
            if prev_nf and nf != prev_nf and not fs_data.consec_counts[prev_nf] > 2:
                del fs_data.consec_counts[prev_nf]
            fs_data.prev_nf = nf

            if nf < 2:
                continue

            fs_data.consec_counts[nf] += 1

        # Gather data about each custom field separator
        if self.custom:
            if self.n_valid_rows == 1:
                self.custom_fs.test(line, False)
            elif self.n_valid_rows == 2:
                self.custom_fs.test(line, True)
            else:
                for fs in self.custom_fs.map:
                    fs_data = self.custom_fs.map[fs]
                    fields_split = line.split(fs)
                    nf = len(fields_split)
                    if nf > 0:
                        fs_data.count[self.n_valid_rows] = nf
                        fs_data.total += nf

    def calculate_best(self):
        Utils.debug_print("\n ---- common sep variance calcs ----", "inferfs")
        SumVar = defaultdict()
        FSVar = defaultdict()
        Winners = defaultdict()
        NoVar = defaultdict()
        winning_s = None
        winner_unsure = False

        if self.n_valid_rows == 0:
            raise Exception("No valid rows found in data to determine field separator.")

        for fs in Utils.COMMON_FS:
            SumVar[fs] = 0

        for fs in Utils.COMMON_FS:
            fs_data = self.common_fs.map[fs]
            average_nf = fs_data.total / self.n_valid_rows
            # nf_chunks = CommonFSNFSpec[fs]

            # if nf_chunks:
            #     NFChunks = nf_chunks.split(",")

            #     for nf in NFChunks:
            #         chunk_weight = CommonFSNFConsecCounts[s, nf] / max_rows

            #         if chunk_weight < 0.6:
            #             del CommonFSNFConsecCounts[s, nf]
            #             continue

            #         SectionalOverride[fs] = 1
            #         chunk_weight_composite = chunk_weight * int(nf)

            #         if not max_chunk_weight:
            #             max_chunk_weight = chunk_weight_composite

            #         if debug: DebugPrint(16)

            #         if chunk_weight_composite >= max_chunk_weight:
            #             max_chunk_sep = s
            Utils.debug_print(f"FS: {fs} fs_data.total: {fs_data.total} average nf: {average_nf}", "inferfs")
            if average_nf < 2:
                continue

            for j in range(self.n_valid_rows):
                point_var = (fs_data.count[j] - average_nf) ** 2
                SumVar[fs] += point_var

            FSVar[fs] = SumVar[fs] / self.n_valid_rows
            Utils.debug_print(6, "inferfs")

            if not FSVar[fs]:
                NoVar[fs] = fs
                winning_s = fs
                Winners[fs] = fs
                Utils.debug_print(7, "inferfs")
            elif not winning_s or FSVar[fs] < FSVar[winning_s]:
                winning_s = fs
                Winners[fs] = fs
                Utils.debug_print(8, "inferfs")
    
        if self.custom:
            for fs in self.custom_fs.map:
                fs_data = self.custom_fs.map[fs]
                Utils.debug_print("\n ---- custom sep variance calcs ----", "inferfs")
                Utils.debug_print(5, "inferfs")
                average_nf = fs_data.total / self.n_valid_rows
            
                for j in range(self.n_valid_rows):
                    point_var = (fs_data.count[j] - average_nf) ** 2
                    SumVar[fs] += point_var

                FSVar[fs] = SumVar[fs] / self.n_valid_rows
                Utils.debug_print(6, "inferfs")

                if FSVar[fs] == 0:
                    NoVar[fs] = fs
                    winning_s = fs
                    Winners[fs] = fs
                    Utils.debug_print(10, "inferfs")
                elif winning_s is None or (FSVar[fs] < FSVar[winning_s]):
                    winning_s = fs
                    Winners[fs] = fs
                    Utils.debug_print(11, "inferfs")
        
        # if (max_chunk_sep && !length(NoVar)) {
        #     if (debug) print "No zero var seps and sectional novar sep exists, override with sep "max_chunk_sep
        #     print CommonFS[max_chunk_sep]
        #     exit
        # }

        # Handle cases of multiple separators with no variance
        # TODO Refactor into new chunky logic above and add customFS chunks calcs
        if len(NoVar) > 1:
            for fs1, fs2 in combinations(NoVar, 2):
                fs1_regex = re.escape(fs1)
                fs2_regex = re.escape(fs2)
                
                # If one separator with no variance is contained inside another, use the longer one
                if (re.search(fs2_regex, fs1) or re.search(fs1_regex, fs2)):
                    if len(Winners[winning_s]) < len(fs2) and len(fs1) < len(fs2):
                        winning_s = fs2
                    elif len(Winners[winning_s]) < len(fs1) and len(fs1) > len(fs2):
                        winning_s = fs1

        if self.high_certainty: # TODO: add this check in chunks comparison
            scaled_var = FSVar[winning_s] * 10
            scaled_var_frac = scaled_var - int(scaled_var)
            winner_unsure = scaled_var_frac != 0

        if not winning_s or winner_unsure:
            return " " # Space is default separator
        elif re.search("(\\ )*\\,(\\ )+", Winners[winning_s]):
            return ","
        else:
            return Winners[winning_s]



if __name__ == "__main__":
    file = DataFile("C:\\Users\\tehal\\dev_scripts_py\\tests\\data\\company_funding_data.csv")
    print(">" + SeparatorInference(False).infer_separator(file) + "<")
