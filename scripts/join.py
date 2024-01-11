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
class Join:
    def __init__(self, fs1=None, fs2=None, OFS=None, merge_verbose=None, verbose=None, merge=None,
                 debug=None, join=None, diff=None, left=None, right=None, inner=None,
                 run_inner=None, run_right=None, skip_left=None, null_field=None, stream1_has_data=None,
                 header_unset=None, keycount=None, keybase=None, key=None, max_nf1=None, max_nf2=None,
                 f1nr=None, err=None):
        self._ = None
        self.fs1 = fs1 if fs1 else None
        self.fs2 = fs2 if fs2 else None
        self.FS = self.fs1
        self.OFS = self.SetOFS(OFS)
        self.merge_verbose = merge_verbose
        self.verbose = verbose if verbose else False
        self.merge = merge if merge else False
        self.debug = debug if debug else False
        self.join = join
        self.diff = diff if diff else False
        self.left = left if left else False
        self.right = right if right else False
        self.inner = inner if inner else False
        self.run_inner = run_inner if run_inner else not self.diff
        self.run_right = run_right if run_right else not self.left and not self.inner
        self.skip_left = skip_left if skip_left else self.inner or self.right
        self.null_field = null_field if null_field else None
        self.stream1_has_data = stream1_has_data if stream1_has_data else False
        self.header_unset = header_unset if header_unset else False
        self.keycount = keycount if keycount else 0
        self.keybase = keybase if keybase else None
        self.key = key if key else None
        self.max_nf1 = max_nf1 if max_nf1 else None
        self.max_nf2 = max_nf2 if max_nf2 else None
        self.f1nr = f1nr if f1nr else None
        self.err = err if err else False

    def SetOFS(self, OFS):
        # implement the logic to set OFS
        pass
    def GenKeys(self, file2_call, nf, K1, K2, GenKeySet):
        # implement the logic to generate Keys
        pass
    def GenMergeKeys(self, nf, K1, K2):
        # implement the logic to generate Merge Keys
        pass

    def GenKeyString(self, Keys):
        # implement the logic to generate Key String
        pass
    def GenInnerOutputString(self, line1, line2, K2, nf1, nf2, fs1):
        # implement the logic to generate Inner Output String
        pass
    def GenRightOutputString(self, line2, K1, K2, nf1, nf2, fs2):
        # implement the logic to generate Right Output String
        pass
    def GenLeftOutputString(self, line1, line2, K1, nf1, nf2, fs1, fs2):
        # implement the logic to generate Left Output String
        pass
