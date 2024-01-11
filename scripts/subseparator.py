import re
import sys

class SubseparatorFinder:
    def __init__(self, subsep_pattern=None, nomatch_handler=r'\s+', debug=False, escape=False, apply_to_fields=None, OFS=None):
        self.subsep_pattern = subsep_pattern
        self.nomatch_handler = nomatch_handler
        self.debug = debug
        self.escape = escape
        self.apply_to_fields = apply_to_fields
        self.OFS = OFS

        if not self.subsep_pattern:
            print("Variable subsep_pattern must be set")
            sys.exit(1)

        if not self.nomatch_handler:
            if self.debug:
                print(f"splitting lines on {self.subsep_pattern} with whitespace tiebreaker")
        else:
            if self.debug:
                print(f"splitting lines on {self.subsep_pattern} with tiebreaker {self.nomatch_handler}")
            if self.escape:
                self.nomatch_handler = re.escape(self.nomatch_handler)
            else:
                self.nomatch_handler = re.escape(self.nomatch_handler)

        self.unescaped_pattern = re.unescape(self.subsep_pattern)
        if self.escape:
            self.subsep_pattern = re.escape(self.subsep_pattern)
        else:
            self.subsep_pattern = re.escape(self.subsep_pattern)

        if self.apply_to_fields:
            Fields = self.apply_to_fields.split(',')
            len_af = len(Fields)
            self.RelevantFields = {}
            for f in range(len_af):
                af = Fields[f]
                if not re.match(r'^[0-9]+$', af):
                    continue
                self.RelevantFields[af] = 1

            if len(self.RelevantFields) < 1:
                sys.exit(1)

        self.OFS = self.SetOFS()

    def SetOFS(self):
        pass

    def process_line(self, fields):
        max_subseps = {}
        subfield_shifts = {}
        for f in fields:
            subseparated_line = re.split(self.subsep_pattern, f)
            num_subseps = len(subseparated_line)

            if num_subseps > 1 and num_subseps > max_subseps.get(f, 0):
                if self.debug:
                    print("Debug: ", 3)
                max_subseps[f] = num_subseps

                for j in range(num_subseps):
                    if not subseparated_line[j].strip():
                        subfield_shifts[f] -= 1

        return max_subseps, subfield_shifts

    def process_file(self, file_path):
        with open(file_path, 'r') as file:
            lines = file.readlines()

        for line in lines:
            fields = line.strip().split()
            max_subseps, subfield_shifts = self.process_line(fields)

        return max_subseps, subfield_shifts

    def trim(self, text):
        return text.strip()

    def debug_print(self, level):
        print(level)

    def parse_file(self, file):
        for line_number, line in enumerate(file, 1):
            fields = line.split()
            for field_index, field in enumerate(fields):
                last_field = field_index == len(fields) - 1
                shift = self.subfield_shifts[field_index]
                n_outer_subfields = self.max_subseps[field_index] + shift
                subfield_partitions = n_outer_subfields * 2 - 1 - shift

                if subfield_partitions > 0:
                    if self.debug: self.debug_print(1)
                    subseparated_line = re.split(self.subsep_pattern, field)
                    num_subseps = len(subseparated_line)
                    k = 0

                    for j in range(subfield_partitions):
                        conditional_ofs = "" if last_field and j == subfield_partitions - 1 else " "
                        outer_subfield = j % 2 + shift

                        if outer_subfield: k += 1
                        if self.debug and (self.retain_pattern or outer_subfield): self.debug_print(2)

                        if num_subseps < n_outer_subfields - shift:
                            handling_line = re.split(self.nomatch_handler, field)
                            if outer_subfield:
                                print(self.trim(handling_line[k-1]), end=conditional_ofs)
                            elif self.retain_pattern:
                                print("", end=conditional_ofs)
                        else:
                            if outer_subfield:
                                print(self.trim(subseparated_line[k-shift-1]), end=conditional_ofs)
                            elif self.retain_pattern:
                                print(self.unescaped_pattern, end=" ")
                    print()
                else:
                    conditional_ofs = "" if last_field else " "
                    print(self.trim(field), end=conditional_ofs)
            print()
