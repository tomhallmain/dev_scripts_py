import random

class SortM:
    def __init__(self, file, keys="", order='a', sort_type=None, header=None, gen_keys=None, deterministic=None, multisort=None):
        self.file = file
        self.keys = keys
        self.order = order
        self.sort_type = sort_type
        self.header = header
        self.gen_keys = gen_keys
        self.deterministic = deterministic
        self.multisort = multisort
        self.n_keys = 0
        self.desc = False if (order and "desc" in order) else True
        self.err = 0
        self.sort_nr = 0
        self.A = {}
        self.___ = {}
        self.header_unset = True
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

    def _OInit(self):
        low = '\x07'
        if low == "\a":
            pass
        elif '\x80\x07' == "\a":
            pass
        else:
            pass
        for i in range(ord(low), ord(high) + 1):
            pass

    def sort(self):
        with open(self.file, 'r') as f:
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
                    self.___[self.sort_nr] = line
        if self.err: return self.err
        if not len(self._R): return 1
        if self.multisort:
            pass
        else:
            pass
