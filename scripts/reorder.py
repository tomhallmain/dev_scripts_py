class Reorder:
    def __init__(self):
        self.indx = None
        self.base = None
        self.base_range = None
        self.reorder = None
        self.p = None
    def reo(self, key, CrossSpan, row_call):
        pass
    def fields_print(self, Order, ord_len, run_call):
        pass
    def fields_index_print(self, Order, ord_len):
        pass
    def fill_range(self, row_call, range_arg, RangeArr, reo_count, ReoArr):
        pass
    def fill_reo_arr(self, row_call, val, KeyArr, count, ReoArr, type):
        pass
    def store_row(self, _):
        pass
    def store_field_refs(self):
        pass
    def store_row_refs(self):
        pass
    def resolve_row_filter_frame(self, frame):
        pass
    def resolve_filter_extensions(self, row_call, Extensions, ReoArr, OrdArr, max_val):
        pass
    def resolve_multiset_logic(self, row_call, key, max_val):
        pass
    def set_negative_index_field_order(self, range_call, ArgArr, max_val):
        pass
    def fill_anchor_range(self, row_call, AncArr, AncOrder):
        pass
    def gen_remainder(self, row_call, ReoArr, max_val):
        pass
    def enforce_unique(self, row_call, Order, ord_len):
        pass
    def get_order(self, row_call, key):
        pass
    def setup(self, row_call, order_arg, reo_count, OArr, RangeArr, ReoArr, base_o, rev_o, oth_o, ExprArr, SearchArr, IdxSearchArr, FramesArr, AncArr, ExtArr):
        pass
    def token_precedence(self, arg):
        pass
    def test_arg(self, arg, max_i, type, row_call):
        pass
    def match_check(self, ExprOrder, SearchOrder, AncOrder, CNidx, CNidxRanges):
        pass
    def indexed(self, idx_ord, test_idx):
        pass
    def build_re(self, Re):
        pass
    def build_token_map(self, TkMap):
        pass
    def build_tokens(self, Tk):
        pass
    def eval_comp_expr(self, left, right, comp):
        pass
    def get_comp(self, string):
        pass
    def print_field(self, field_val, field_no, end_field_no):
        pass
    def qsort_asc(self, A,lft,rght, x, last):
        pass
    def qsort_desc(self, A,lft,rght, x, last):
        pass
    def swap(self, A, B, x, y, z):
        pass
