import argparse
import re

        # self.operations = {
        #     '-': operator.sub,
        #     '+': operator.add,
        #     '%': lambda a, b: ((a - b) / a) * 100 if a != 0 else 0,
        #     '*': operator.mul,
        #     '/': operator.truediv,
        #     'b': lambda a, b: a != b,
        #     'bin': lambda a, b: a != b,
        #     'binary': lambda a, b: a != b
        # }

class DiffFields:
    def __init__(self, data_file1, data_file2, op, exclude_fields, header, summary, summary_only, summary_sort, left_label, right_label):
        self.data_file1 = data_file1
        self.data_file2 = data_file2
        self.op = op
        self.exclude_fields = self.parse_exclude_fields(exclude_fields)
        self.header = header
        self.has_diff = not self.summary_only
        self.summary = summary
        self.summary_sort = summary_sort
        self.summary_only = summary_only
        self.diff_counter = 0
        self.left_label = left_label if left_label else ''
        self.right_label = right_label if right_label else ''
        self.subtract = False
        self.add = False
        self.pc = False
        self.mult = False
        self.div = False
        self.bin = False
        self.set_switches()

    def set_switches(self):
        if self.op == '-':
            self.subtract = 1
        elif self.op == '+':
            self.add = 1
        elif self.op == '%':
            self.pc = 1
        elif self.op == '*':
            self.mult = 1
        elif self.op == '/':
            self.div = 1
        else:
            self.bin = True


    def parse_exclude_fields(self, exclude_fields_str):
        exclude_fields = []
        if not exclude_fields_str or exclude_fields_str.strip() == "":
            return []
        else:
            _ExcludeFields = exclude_fields_str.split(',')
            for field_index in _ExcludeFields:
                field_index = field_index.strip()  # remove leading/trailing spaces
                if not field_index or field_index == "":
                    continue
                try:
                    exclude_fields.append(int(field_index))
                except:
                    print(f"Invalid exclude field index (exclude_fields must be a list of ints): {field_index}")
            return exclude_fields

    def _exclude_fields(self, row):
        return [val for i, val in enumerate(row) if i not in self.exclude_fields]

    # def diff(self):
    #     data1 = self.data_file1.data()
    #     data2 = self.data_file2.data()

    #     if self.header:
    #         headers1 = data1.pop(0)
    #         headers2 = data2.pop(0)

    #     for row1, row2 in zip(data1, data2):
    #         row1 = self._exclude_fields(row1)
    #         row2 = self._exclude_fields(row2)

    #         for val1, val2 in zip(row1, row2):
    #             val1 = float(val1)
    #             val2 = float(val2)

    #             diff = self.operations[self.op](val1, val2)

    #             if diff != 0 and self.summary:
    #                 print(f'Row: {row1}, {row2}, Diff: {diff}')

    #     if self.summary_sort:
    #         data1.sort(key=lambda x: float(x[1]))
    #         data2.sort(key=lambda x: float(x[1]))

    #     return data1, data2

    def process_lines(self):
        global diff_counter, has_diff
        Stream1Line = S1[FNR].split(fs1)
        
        for f in range(len(self.data1)):
            s1_val = Stream1Line[f]
            s2_val = FNR[f]
            
            if bin:
                diff_val = (s1_val != s2_val)
                self.print_diff_field(diff_val)
                
                if self.summary:
                    if self.div:
                        if diff_val == 1:
                            break
                    else:
                        if diff_val == 0:
                            break
                    if self.summary_only and not has_diff and diff_val:
                        has_diff = 1
                    if self.summary_row_header:
                        if self.header:
                            list_val = f"{summary_row_header}{Header[f]}{Stream1Line[f]}{FNR[f]}{diff_val}"
                        else:
                            list_val = f"{summary_row_header}{f}{Stream1Line[f]}{FNR[f]}{diff_val}"
                    else:
                        list_val = f"{FNR}{f}{Stream1Line[f]}{FNR[f]}{diff_val}"
                    DiffList[diff_counter] = list_val
                    self.diff_counter += 1

                if f < len(Stream1Line) - 1:
                    self.print_diff_field(OFS)
                continue

            if f in self.exclude_fields:
                self.print_diff_field(FNR[f])
            else:
                s1_val = s1_val.strip()
                s2_val = s2_val.strip()
                while s1_val or s2_val:
                    if not s1_val:
                        s1_val = 0
                        s2_val = self.extract_val(s2_val)
                        if not s2_val and s2_val != 0:
                            self.print_diff_field(FNR[f])
                            break

                        s2_val = self.truncate_val(s1_val)
                    elif not s2_val:
                        s1_val = self.extract_val(s1_val)
                        s2_val = 0
                        if not s1_val and s1_val != 0:
                            self.print_diff_field(Stream1Line[f])
                            break

                        s1_val = self.truncate_val(s1_val)
                    else:
                        s1_val = self.extract_val(s1_val)
                        s2_val = self.extract_val(s2_val)
                        if not s1_val and s1_val != 0:
                            if not s2_val and s2_val != 0:
                                break
                            else:
                                self.print_diff_field(FNR[f])
                                break
                        elif not s2_val and s2_val != 0:
                            self.print_diff_field(Stream1Line[f])
                            break

                        s1_val = self.truncate_val(s1_val)
                        s2_val = self.truncate_val(s2_val)
                    if self.subtract:
                        diff_val = s1_val - s2_val
                    elif self.pc:
                        if s1_val == 0:
                            if s2_val == 0:
                                diff_val = 0
                            else:
                                diff_val = 1
                        else:
                            diff_val = (s2_val - s1_val) / s1_val
                            
                            if s1_val < 0 and s2_val < 0:
                                diff_val *= -1
                    elif self.add:
                        diff_val = s1_val + s2_val
                    elif self.mult:
                        diff_val = s1_val * s2_val
                    else:
                        if s2_val == 0:
                            break
                        else:
                            diff_val = s1_val / s2_val
                    self.print_diff_field(diff_val)

                    if self.summary:
                        if self.div:
                            if diff_val == 1:
                                break
                        else:
                            if diff_val == 0:
                                break

                        if self.summary_only and not has_diff and diff_val:
                            has_diff = 1

                        if self.summary_row_header:
                            if self.header:
                                list_val = f"{self.summary_row_header}{Header[f]}{Stream1Line[f]}{FNR[f]}{diff_val}"
                            else:
                                list_val = f"{self.summary_row_header}{f}{Stream1Line[f]}{FNR[f]}{diff_val}"
                        else:
                            list_val = f"{FNR}{f}{Stream1Line[f]}{FNR[f]}{diff_val}"

                        DiffList[diff_counter] = list_val
                        self.diff_counter += 1

                    break

            if f < len(Stream1Line) - 1:
                self.print_diff_field(OFS)

        self.print_diff_field("\n")
    
    def print_diff_field(self, field_val):
        if not self.summary_only:
            print(field_val)
    
    def truncate_val(self, val):
        large_val = val > 999
        large_dec = bool(re.search(r'\.[0-9]{3,}', str(val)))

        if (large_val and large_dec) or re.match(r'^-?[0-9]*\.?[0-9]+(E|e)\+?([4-9]|[1-9][0-9]+)$', str(val)):
            trunc_val = int(val)
        else:
            trunc_val = float("{:.6f}".format(val)) # Small floats flow through this logic

        trunc_val += 0
        return trunc_val

    def extract_val(self, val):
        if val in ExtractVal:
            return ExtractVal[val]
        if val in NoVal:
            return ""

        cleaned_val = val.replace(",", "")

        if cleaned_val in ExtractVal:
            return ExtractVal[cleaned_val]
        if cleaned_val in NoVal:
            return ""

        match_obj = re.search(r'-?[0-9]*\.?[0-9]+((E|e)(\+|-)[0-9]+)?', cleaned_val)
        if match_obj:
            if extract_vals:
                extract_val = cleaned_val[match_obj.start():match_obj.start()+match_obj.end()]
            elif match_obj.start() > 1 or match_obj.end() < len(cleaned_val):
                NoVal[val] = 1
                return ""
            else:
                extract_val = cleaned_val
        else:
            NoVal[val] = 1
            return ""

        extract_val += 0
        ExtractVal[val] = extract_val
        return extract_val


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('file1', help='First file for comparison')
    parser.add_argument('file2', help='Second file for comparison')
    parser.add_argument('op', help='Operation to be performed')
    parser.add_argument('--exclude_fields', nargs='+', type=int, default=[0], help='Fields to be excluded from the operation')
    parser.add_argument('--header', action='store_true', help='Flag to indicate if header is present')
    parser.add_argument('--summary', action='store_true', help='Flag to indicate if diff list should be printed')
    parser.add_argument('--summary_sort', action='store_true', help='Flag to indicate if diff list should be sorted')

    args = parser.parse_args()

    diff_fields = DiffFields(args.file1, args.file2, args.op, args.exclude_fields, args.header, args.summary, args.summary_sort)
    diff_fields.diff()


