#       join.py is a script to run a join of two files or data streams with variant 
#       options for output.
#
#       Jointype takes one of five options:
#
#          o[uter] - default
#          i[nner]
#          l[eft]
#          r[ight]
#          d[iff]
#
#       If there is one field number to join on, assign it to var k at runtime:
#
#          $ join.py file1 file2 o 1
#
#       If there are different keys in each file, assign file2's key second:
#
#          $ join.py file1 file2 o 1 2
#
#       If there are multiple fields to join on in a single file, separate the column
#       numbers with commas. Note the key sets must be equal in length:
#
#          $ join.py file1 file2 o 1,2 2,3
#
#       Keys can also be generated from matching regex patterns in the first row with data 
#       in each file:
#
#          $ join.py file1 file2 o f1header1,f1header2 f2header1,f2header2
#
#       To join on all fields from both files, set k to "merge":
#
#          $ join.py file1 file2 left merge
#
# JOIN LOGIC
#       Assuming two data files as follows:
#
#          $ cat data1
#          a 1
#          a 2
#          $ cat data2
#          a 3
#          a 4
#
#       Standard relational joins are the relational products of left and right multisets
#       involved. This join logic is not the default for join.py. For example:
#
#          $ join.py data1 data2 outer 1 -v standard_join=1
#          a  1  3
#          a  2  3
#          a  1  4
#          a  2  4
#
#       join.py's default join is a recordwise merge-type join that produces a lower output 
#       record count. Provided the source files have been pre-sorted, this type of join can 
#       be more desirable.
#
#          $ join.py data1 data2 outer 1
#          a  1  3
#          a  2  4
#
#       Note the only difference between these join types occurs in the inner part of joins.
## TODO string distance comparison
from collections import defaultdict
import re

from .utils import Utils

class Join:
    SUBSEP = "\u2022" # "\u0034" # TODO move this somewhere portable
    join_types = ["left", "right", "inner", "outer", "diff"]

    def __init__(self, data_file1, data_file2, OFS=None, header=False, verbose=False, merge=False,
                 join="outer", null_off=False, bias_merge_keys=None, 
                 left_label="", right_label="", inner_label="", gen_keys=False,
                 k1=None, k2=None, max_merge_fields=None, standard_join=False):
        self._ = None
        self.data_file1 = data_file1
        self.data_file2 = data_file2
        self.data_file1.get_field_separator()
        self.data_file2.get_field_separator()
        self.data_file1.get_data()
        self.data_file2.get_data()
        if OFS is None:
            OFS = self.data_file1.field_separator
        self.OFS = self.SetOFS(OFS)
        self.verbose = verbose
        self.merge = merge
        self.left, self.right, self.inner, self.outer, self.diff = [type.startswith(join) for type in Join.join_types]
        self.join = list(filter(lambda type: type.startswith(join), Join.join_types))[0]
        self.run_inner = not self.diff
        self.run_right = not self.left and not self.inner
        self.run_left = not self.inner and not self.right
        self.null_field = "" if null_off else "<NULL>"
        self.equal_keys = False
        self.bias_merge = False
        self.gen_keys = gen_keys

        self.record_count = 0
        self.index = False # TODO set this
        self.header = header
        self.full_bias = False # TODO set this
        self.inherit_keys = False # TODO set this
        self.standard_join = standard_join
        self.case_sensitive = False # TODO set this
        self.bias_merge_exclude_keys = False # TODO set this
        self.gen_bias_merge_keys_from_exclusion = False # set later
        self.max_merge_fields = int(max_merge_fields) if max_merge_fields else self.data_file1.max_nf
        # TODO print warning to stderr if data_file2.max_nf is greater than data_file1.max_nf
        self.K1 = {}
        self.K2 = {}
        self.Keys1 = {}
        self.Keys2 = {}
        self.KeysInitial1 = []
        self.KeysInitial2 = []
        self.BiasMergeKeys = {}
        self.BiasMergeExcludeKeys = {}
        self.S1 = defaultdict(list)
        self.S2 = defaultdict(list)
        self.SK1 = defaultdict(int)
        self.SK2 = defaultdict(int)
    

        if verbose:
            verbose = 1
            file_labels = len(data_file1.name) > 0 and len(data_file2.name) > 0 and data_file1.name != data_file2.name

            if not left_label:
                left_label = (data_file1.name if file_labels else "FILE1")
            if not right_label:
                right_label = (data_file2.name if file_labels else "FILE2")
                right_label = "PIPEDATA" if data_file2.is_stdin else right_label
            if not inner_label:
                inner_label = "BOTH"

            self.left_label = left_label + self.OFS
            self.right_label = right_label + self.OFS
            self.inner_label = inner_label + self.OFS
        else:
            self.left_label = ""
            self.right_label = ""
            self.inner_label = ""

        if self.merge:
            if bias_merge_keys:
                self.bias_merge = 1
                _BiasMergeKeys = bias_merge_keys.split(",")

                for key_index, key in enumerate(_BiasMergeKeys):
                    if not key.isdigit():
                        print("Bias merge keys must be integers, found key: " + key)
                        exit(1)

                    self.BiasMergeKeys[key] = key_index

            if self.bias_merge_exclude_keys:
                self.bias_merge = True
                self.gen_bias_merge_keys_from_exclusion = True
                _BiasMergeExcludeKeys = self.bias_merge_exclude_keys.split(",")

                for key_index, key in enumerate(_BiasMergeExcludeKeys):
                    if not key.isdigit():
                        print("Bias merge exclude keys must be integers, found key: " + key)
                        exit(1)

                    if key in self.BiasMergeKeys:
                        del self.BiasMergeKeys[key]

                    self.BiasMergeExcludeKeys[key] = 1

        else:
            self.bias_merge = False

            if not k1 and not k2:
                print("Missing join key fields")
                exit(1)

            self.k1 = k1 if k1 else k2
            self.k2 = k2 if k2 else k1

            if not k1 or not k2:
                self.equal_keys = True

            self.KeysInitial1 = [x.strip() for x in self.k1.split(',')]
            self.KeysInitial2 = [x.strip() for x in self.k2.split(',')]

            if len(self.KeysInitial1) != len(self.KeysInitial2):
                print("Keysets must be equal in length")
                exit(1)

            for i, key in enumerate(self.KeysInitial1):
                if len(key) == 0:
                    continue
                elif (not key.isdigit() or len(key) > 3):
                    self.gen_keys = True
                else:
                    self.Keys1[i] = int(key) - 1

            for i, key in enumerate(self.KeysInitial2):
                joint_key = self.KeysInitial1[i]

                if len(key) == 0:
                    pass
                elif (not key.isdigit() or len(key) > 3):
                    self.gen_keys = True
                    self.K2[key] = joint_key
                    self.K1[joint_key] = key
                else:
                    self.Keys2[i] = int(key) - 1
                    self.K2[int(key) - 1] = joint_key
                    self.K1[joint_key] = int(key) - 1

        if Utils.DEBUG:
            Utils.debug_print(f"Running {self.join} join between files {self.data_file1.name} and {self.data_file2.name}", "join")
            for i, key in enumerate(self.Keys1):
                Utils.debug_print(f"Key for {self.data_file1.name}: {i} - {key}", "join")
            for i, key in enumerate(self.Keys2):
                Utils.debug_print(f"Key for {self.data_file2.name}: {i} - {key}", "join")

        self.stream1_has_data = self.data_file1.n_rows > 0

    def run(self):
        if self.merge:
            self._gen_merge_keys()
        if self.data_file1.n_rows > 0:
            self._save_first_stream()
        self._print_matches_and_second_file_unmatched()
        if self.run_left:
            self._print_left_joins()
        if Utils.DEBUG:
            Utils.debug_print(self.S1, context="join")
            Utils.debug_print(self.S2, context="join")
            Utils.debug_print(self.Keys1, context="join")
            Utils.debug_print(self.Keys2, context="join")

    def _save_first_stream(self):
        if Utils.DEBUG:
            Utils.debug_print(f"Saving first stream of data from {self.data_file1.name}", "join")

        #if (k1 > NF) { print "Key out of range in file 1"; err = 1; exit }

        if self.gen_keys:
            self._gen_keys(False, self.data_file1)

        if self.header:
            self.data_file1.set_header()
            self.data_file2.set_header()

        line = self.data_file1.next_line()

        while line:
            keycount = 1
            keybase = self._gen_key_string(self.Keys1, line)
            Utils.debug_print(f"file1 keybase: {keybase}", context="join")
            key = f"{keybase}{keycount}"

            while key in self.S1:
                if Utils.DEBUG:
                    Utils.debug_print(f"key was found in s1: {key}", "join")
                keycount += 1
                key = f"{keybase}{keycount}"

            self.SK1[key] += 1
            Utils.debug_print(key, context="join")
            Utils.debug_print(self.SK1[key], context="join")
            self.S1[key] = line
            line = self.data_file1.next_line()

    def _print_matches_and_second_file_unmatched(self):
        # Check if key is out of range in file 2
        if self.gen_keys:
            self._gen_keys(True, self.data_file2)

        if self.header:
            if self.index:
                print(self.OFS, end='')
            print(self._gen_inner_output_string(self.data_file1.header, self.data_file2.header))

        if Utils.DEBUG:
            Utils.debug_print(f"Printing matches and second file unmatched data from {self.data_file2.name}", "join")

        line = self.data_file2.next_line()

        while line:
            self.handle_line(line)
            line = self.data_file2.next_line()


    def handle_line(self, line):
        keybase = self._gen_key_string(self.Keys2, line)
        if Utils.DEBUG:
            Utils.debug_print(f"file2 keybase: {keybase}", context="join")
        keycount = 1
        key = f"{keybase}{keycount}"

        # Print right joins and inner joins
        if key in self.SK1:
            self.SK2[key] += 1

            if self.standard_join:
                if self.run_inner:
                    self.record_count += 1
                    stream1_keycount = self.SK1[key]    
                    for i in range(1, stream1_keycount + 1):
                        self.record_count += 1
                        if self.index:
                            print(f'{self.record_count}{self.OFS}', end='')
                        print(self._gen_inner_output_string(self.S1[f"{keybase}{i}"], line))
            else:
                if f"{keybase}{self.SK2[key]}" in self.S1:
                    if Utils.DEBUG:
                        Utils.debug_print(f"Found in S1: {keybase}{self.SK2[key]} - S1 {self.S1}", context="join")
                    while f"{keybase}{self.SK2[key]}" in self.S1:
                        sk2_keycount = self.SK2[key]
                        if self.run_inner:
                            self.record_count += 1
                            if self.index:
                                print(f'{self.record_count}{self.OFS}', end='')
                            print(self._gen_inner_output_string(self.S1[f"{keybase}{sk2_keycount}"], line))
                        del self.S1[f"{keybase}{sk2_keycount}"]
                        keycount += 1
                        key = f"{keybase}{keycount}"
                else:
                    if Utils.DEBUG:
                        Utils.debug_print(f"Not found in S1: {keybase}{self.SK2[key]} - S1 {self.S1}", context="join")
                    if self.run_right:
                        self.record_count += 1
                        if self.index:
                            print(f'{self.record_count}{self.OFS}', end='')
                        print(self._gen_right_output_string(line))
                    keycount += 1
                    key = f"{keybase}{keycount}"
        else:
            self.S2[key] = line
            while key in self.S2:
                if self.run_right:
                    self.record_count += 1
                    if self.index:
                        print(f'{self.record_count}{self.OFS}', end='')
                    print(self._gen_right_output_string(self.S2[key]))
                keycount += 1
                key = f"{keybase}{keycount}"

    def _print_left_joins(self):
        if Utils.DEBUG:
            Utils.debug_print(f"Printing left joins from {self.data_file1.name}", "join")

        record_count = 0

        for compound_key in self.S1.keys():
            if self.standard_join and self.run_inner:
                base_key = compound_key[:-2]
                if base_key in self.SK2:
                    if Utils.DEBUG:
                        Utils.debug_print(f"Found in both: {compound_key} - S1 {self.S1}, S2 {self.SK2}")
                    continue
                if Utils.DEBUG:
                    Utils.debug_print(f"Not found in SK2: {base_key} - compound_key {compound_key}", context="join")

            record_count += 1
            if self.index:
                print(f"{record_count}", end=" ")
            stream2_line = self.S2[compound_key] if self.full_bias else ""
            print(self._gen_left_output_string(self.S1[compound_key], stream2_line))

    def SetOFS(self, OFS):
        # implement the logic to set OFS
        if re.search(r'\[\:.+\:\]\{2,\}', OFS):
            OFS = "  "
        elif re.search(r'\[\:.+\:\]', OFS):
            OFS = " "
        return OFS

    def _gen_keys(self, file2_call, data_file):
        MissingKeys = {}
        header_fields = data_file.data[0]
        KeysInitial = self.KeysInitial2 if file2_call else self.KeysInitial1

        if Utils.DEBUG:
            Utils.debug_print("Generating keys", "join")
            Utils.debug_print(f"Header fields: {header_fields}", "join")
            Utils.debug_print(f"Keys: {KeysInitial}", "join")

        for i in range(len(KeysInitial)):
            key_pattern = KeysInitial[i]
            key_found = False

            if not self.case_sensitive:
                key_pattern = key_pattern.lower()

            for f in range(len(header_fields)):
                field = header_fields[f] if self.case_sensitive else header_fields[f].lower()

                if field.startswith(key_pattern):
                    if file2_call:
                        self.Keys2[i] = f
                        self.K2[f] = self.KeysInitial1[i]
                        self.K1[self.K2[f]] = f
                        
                        if self.K2[key_pattern] in self.K1:
                            del self.K1[self.K2[key_pattern]]
                        del self.K2[key_pattern]
                    else:
                        self.Keys1[i] = f
                        self.K1[f] = f
                        self.K2[self.K1[f]] = f
                        del self.K1[key_pattern]
                    key_found = True
                    break

            if not key_found:
                MissingKeys[key_pattern] = 1

        if Utils.DEBUG:
            Utils.debug_print(self.Keys1, "join")
            Utils.debug_print(self.Keys2, "join")
            Utils.debug_print(self.K1, "join")
            Utils.debug_print(self.K2, "join")

        if len(MissingKeys) > 0:
            if file2_call and self.inherit_keys:
                n_keys = len(self.Keys2)

                for i in range(n_keys):
                    del self.K2[self.Keys2[i]]
                    del self.Keys2[i]
                for i in range(n_keys):
                    key = self.Keys1[i]
                    self.Keys2[i] = key
                    self.K2[key] = self.K1[key]
                return

            if data_file.is_stdin:
                filename = "right data" if file2_call else "left data"
            else:
                filename = data_file.name
            print(f"join: Could not locate keys in {filename}: ", end="")
            print(f"join: {MissingKeys}")
            exit(1)

    def _gen_merge_keys(self):
        if Utils.DEBUG:
            Utils.debug_print("Generating merge keys", "join")

        for f in range(0, self.max_merge_fields):
            if f in self.BiasMergeKeys:
                continue
            elif self.gen_bias_merge_keys_from_exclusion and f not in self.BiasMergeExcludeKeys:
                self.BiasMergeKeys[f] = f
                continue
            self.K1[f] = f
            self.K2[f] = f
            self.Keys1[f] = f
            self.Keys2[f] = f

    def _gen_key_string(self, keys, fields):
        s = ""
        for k in keys.values():
            f = fields[k]
            if len(f) == 0:
                f = self.null_field
            s += f + Join.SUBSEP
        return s

    def _gen_inner_output_string(self, fields1, fields2):
        # implement the logic to generate Inner Output String
        jn = self.inner_label
        if Utils.DEBUG:
            Utils.debug_print(f"Fields1: {fields1}", context="join")
            Utils.debug_print(f"Fields2: {fields2}", context="join")

        if self.bias_merge:
            for f in range(self.data_file1.max_nf):
                if f in self.BiasMergeKeys and (self.full_bias or (len(fields2[f]) > 0 and fields2[f] != self.null_field)):
                    if self.full_bias and len(fields2[f]) == 0:
                        jn += self.null_field
                    else:
                        jn += fields2[f]
                else:
                    jn += fields1[f]

                if f < self.data_file1.max_nf - 1:
                    jn += self.OFS
        else:
            nf_pad = max(self.data_file1.max_nf - len(fields1) + 1, 0)
            jn += self.OFS.join(fields1)

            for f in range(nf_pad, 1, -1):
                jn += self.OFS

        for f in range(self.data_file2.max_nf):
            if (self.data_file1.max_nf > 0 and f in self.K2) or (self.bias_merge and f in self.BiasMergeKeys):
                continue
            jn += self.OFS + fields2[f]

        if Utils.DEBUG:
            Utils.debug_print(f"Inner output string: {jn}", "join")

        return jn

    def _gen_right_output_string(self, fields):
        jn = self.right_label

        for f in range(0, self.data_file1.max_nf):
            # TODO figure out if this block is actually correct
            if f in self.Keys2:
                jn += fields[self.Keys2[f]]
            elif self.bias_merge and f in self.BiasMergeKeys:
                field = fields[f]
                jn += self.null_field if len(field) == 0 else field
            else:
                jn += self.null_field
            if f < self.data_file1.max_nf - 1:
                jn += self.OFS
    
        for f in range(0, self.data_file2.max_nf):
            if self.data_file1.max_nf > 0 and f in self.Keys2:
                continue
            if self.bias_merge and f in self.BiasMergeKeys: 
                continue
            field = fields[f]
            jn += self.OFS
            jn += field #self.null_field if len(field) == 0 else field

        if Utils.DEBUG:
            Utils.debug_print(f"Right output string: {jn}", "join")

        return jn

    def _gen_left_output_string(self, fields1, fields2):
        jn = self.left_label

        if self.full_bias:
            for f in range(self.data_file1.max_nf):
                if f in self.BiasMergeKeys:
                    new_field = fields2[f] if f < len(fields2) else ""
                else:
                    new_field = fields1[f] if f < len(fields1) else ""
    
                if len(new_field) == 0:
                    new_field = self.null_field
    
                jn += new_field
    
                if f < len(fields1) - 1:
                    jn += self.OFS
        else:
            nf_pad = max(self.data_file1.max_nf - len(fields1) + 1, 0)
            jn += self.OFS.join(fields1)

            for f in range(nf_pad, 1, -1):
                jn += self.OFS # TODO maybe null field here
    
        for f in range(self.data_file2.max_nf):
            if f in self.Keys2 or (self.bias_merge and f in self.BiasMergeKeys):
                continue
            jn += self.OFS + self.null_field

        if Utils.DEBUG:
            Utils.debug_print(f"Left output string: {jn}", "join")

        return jn
