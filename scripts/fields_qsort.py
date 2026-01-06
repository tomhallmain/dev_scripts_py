import random

class SortM:
    def __init__(self, data_file, keys="", order='a', sort_type="", header=None, gen_keys=None, deterministic=None, multisort=None):
        self.data_file = data_file
        self.keys = keys
        self.Keys = {}
        self.order = order
        self.sort_type = sort_type
        self.header = header
        self.gen_keys = gen_keys
        self.case_sensitive = False # TODO
        self.deterministic = deterministic
        self.multisort = multisort
        self.n_keys = 0
        self.desc = False if (order and "desc" in order) else True
        self.err = 0
        self.sort_nr = 0
        self.A = {}
        self.TieBack = {}
        self.header_unset = self.header is not None and self.header
        self.has_started_sort_key = False
        self.sort_key = ""
        self.max_nf = 0
        self._R = {}
        self.NF = 0
        self.f = 0
        self.R = 0
        self.C = 0
        self.RCounts = {}
        self.CCounts = {}
        self.max_len = 0
        self.CharIdxCounts = {}
        self.ValsArr = {}

        if self.multisort:
            pass
        elif self.keys and self.keys.strip() != "":
            KeysInitial = [x.strip() for x in self.keys.split(',')]
            for i, key in enumerate(KeysInitial):
                if len(key) == 0:
                    continue
                elif (not key.isdigit() or len(key) > 3):
                    self.gen_keys = True
                else:
                    self.Keys[i] = int(key) - 1
        else:
            self.Keys[1] = 0
            self.n_keys = 1

        if self.sort_type and self.sort_type.startswith("numeric"):
            n = 1
            n_re = "^[[:space:]]*\\$?[[:space:]]?-?\\$?([0-9]{,3},)*[0-9]*\\.?[0-9]+((E|e)(\\+|-)?[0-9]+)?"
            f_re = "^[[:space:]]*-?[0-9]\.[0-9]+(E|e)(\\+|-)?[0-9]+[[:space:]]*$"

    def run_sort(self):
        self.handle_header()
        self.process_lines()
        if self.multisort:
            self.do_multisort()
        else:
            self.qsort()

    def handle_header(self):
        if self.header_unset or self.gen_keys:
            self.data_file.set_header()

            if self.gen_keys:
                for i in range(len(self.Keys)):
                    key_pattern = self.Keys[i]

                    if key_pattern == "NF":
                        continue

                    key_found = False

                    if not self.case_sensitive:
                        key_pattern = key_pattern.lower()
                    
                    for f in range(len(self.data_file.header)):
                        field = self.data_file.header[f]
                        if self.case_sensitive:
                            field = field.lower()
                        if key_pattern.startswith(field):
                            self.Keys[i] = field
                            self.KeyFields[f] = 1
                            key_found = True
                            break

                    if not key_found:
                        self.n_keys -= 1
                        del self.Keys[i]

                if self.n_keys < 1:
                    raise Exception("No key patterns provided matched header")

            self.header = self.data_file.header

    def process_lines(self):
        line = self.data_file.next_line()

        while line:
            sort_key = ""
            has_started_sort_key = False

            for i in range(self.n_keys):
                if i not in self.Keys:
                    continue
                
                kf = self.Keys[i]
                if kf < 0:
                    kf += self.data_file.max_nf
                elif kf == "NF":
                    kf = self.data_file.max_nf

                sort_key += self.data_file.field_separator + line[kf] if has_started_sort_key else line[kf]

                if not has_started_sort_key:
                    has_started_sort_key = True

            if self.deterministic:
                for i in range(len(self.data_file.max_nf)):
                    if i not in self.KeyFields:
                        sort_key = self.data_file.field_separator + line[i] if has_started_sort_key else line[i]
                        if not has_started_sort_key:
                            has_started_sort_key = True


            self.sort_nr += 1
            self.A[self.sort_nr] = sort_key
            self.TieBack[self.sort_nr] = line
            line = self.data_file.next_line()

    def do_multisort(self):
        pass # TODO

    def qsort(self):
        if self.sort_type.startswith("n"):
            if self.desc:
                self.QSDN()
            else:
                self.QSAN()
        else:
            if self.desc:
                self.QSD()
            else:
                self.QSA()

        if self.header:
            print(self.data_file.header)
        for i in range(self.sort_nr):
            print(self.TieBack[i])

    def GetN(self, str):
        if str in self.NS:
            pass
        elif str in self.n_re:
            pass
        else:
            pass

    def AdvChars(self, row, field, str, start):
        r_count = 0
        c_count = 0
        len_chars = len(str) + start
        for c in range(start, len_chars):
            pass
        if len_chars < 1:
            pass
        if len_chars > self.RCounts[row]: self.RCounts[row] = len_chars
        if len_chars > self.CCounts[field]: self.CCounts[field] = len_chars
        if len_chars > self.max_len: self.max_len = len_chars

    def ContractCharVals(self, max_base):
        for i in range(1, max_base + 1):
            pass
    def SA(self, A, TieBack, left, right):
        if left >= right: return
        self.SM(A, TieBack, left, left + int((right-left+1)*random.random()))
        last = left
        for i in range(left+1, right + 1):
            pass
        self.SM(A, TieBack, left, last)
        self.SA(A, TieBack, left, last-1)
        self.SA(A, TieBack, last+1, right)

    def SM(self, A, TieBack, i, j):
        t = A[i]
        A[i] = A[j]
        A[j] = t
        t = TieBack[i]
        TieBack[i] = TieBack[j]
        TieBack[j] = t

    def _OInit(self, low, high):
        low = '\x07'
        if low == "\a":
            low = 0
            high = 127
        elif '\x80\x07' == "\a":
            low = 128
            high = 255
        else:
            low = 0
            high = 255
        for i in range(ord(low), ord(high) + 1):
            pass

    def sort(self):
        with open(self.data_file, 'r') as f:
            for line in f:
                row = line.strip().split()
                self.NF = len(row)
                if self.multisort:
                    self._R[len(self._R) + 1] = len(self._R) + 1
                    for self.f in range(1, self.NF + 1):
                        pass
                if self.NF > self.max_nf: self.max_nf = self.NF
                if self.header_unset or self.gen_keys:
                    if self.gen_keys:
                        pass
                    if self.header_unset:
                        self.header = line
                        continue
                    for i in range(1, self.n_keys + 1):
                        pass
                    if self.deterministic:
                        pass
                    self.sort_nr += 1
                    self.A[self.sort_nr] = self.sort_key
                    self.TieBack[self.sort_nr] = line
        if self.err: return self.err
        if not len(self._R): return 1
        if self.multisort:
            pass
        else:
            pass

    def QSA(self, A, left, right):
        if left >= right:
            return

        self.swap(A, self.TieBack, left, left + int((right-left+1)*rand()))
        last = left

        for i in range(left+1, right+1):
            if (A[i] < A[left]):
                last += 1
                self.swap(A, self.TieBack, last, i)

        self.swap(A, self.TieBack, left, last)
        self.QSA(A, left, last-1)
        self.QSA(A, last+1, right)

    def QSAN(self, A,left,right):
        if left >= right:
            return

        self.swap(A, self.TieBack, left, left + int((right-left+1)*rand()))
        last = left

        for i in range(left+1, right+1):
            if (GetN(A[i]) < GetN(A[left])):
                last += 1
                self.swap(A, self.TieBack, last, i)
            elif (GetN(A[i]) == GetN(A[left]) and NExt[A[i]] < NExt[A[left]]):
                last += 1
                self.swap(A, self.TieBack, last, i)

        self.swap(A, self.TieBack, left, last)
        self.QSAN(A, left, last-1)
        self.QSAN(A, last+1, right)

    def QSD(self, A,left,right):
        if left >= right:
            return

        self.swap(A, self.TieBack, left, left + int((right-left+1)*rand()))
        last = left

        for i in range(left+1, right+1):
            if (A[i] > A[left]):
                self.swap(A, self.TieBack, ++last, i)

        self.swap(A, self.TieBack, left, last)
        self.QSD(A, left, last-1)
        self.QSD(A, last+1, right)

    def QSDN(self, A,left,right):
        if left >= right:
            return

        self.swap(A, self.TieBack, left, left + int((right-left+1)*rand()))
        last = left

        for i in range(left+1, right+1):
            if (GetN(A[i]) > GetN(A[left])):
                last += 1
                self.swap(A, self.TieBack, last, i)
            elif (GetN(A[i]) == GetN(A[left]) and NExt[A[i]] > NExt[A[left]]):
                last += 1
                self.swap(A, self.TieBack, last, i)

        self.swap(A, self.TieBack, left, last)
        self.QSDN(A, left, last-1)
        self.QSDN(A, last+1, right)

    def swap(self, A, TieBack, i,j):
        temp = A[i]
        A[i] = self.A[j]
        A[j] = temp
        temp = TieBack[i]
        TieBack[i] = TieBack[j]
        TieBack[j] = temp

