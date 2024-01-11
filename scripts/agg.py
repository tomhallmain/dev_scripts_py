import re

class Agg:
    def __init__(self, r_aggs=None, c_aggs=None, extract_vals=0, fixed_nf=25, og_off=1):
        self.r_aggs = r_aggs
        self.c_aggs = c_aggs
        self.extract_vals = extract_vals
        self.fixed_nf = fixed_nf
        self.og_off = og_off
        self.RowAggs = {}
        self.ColumnAggs = {}
        self.CrossAggs = {}
        self.AllAgg = {}
        self.SearchAgg = {}
        self.ConditionalAgg = {}
        self.header_unset = True
        self.max_nr = 0
        self.OFS = self.set_OFS()

    def set_OFS(self):
        return "\t"

    def gen_all_aggregation_expr(self, max, call):
        for agg in self.AllAgg:
            pass

    def aggregation_expr(self, agg_expr, call, call_idx, reparse):
        orig_agg_expr = agg_expr
        agg_expr = re.sub(r'\s+', '', agg_expr)
        all_agg = 0
        mean_agg = 0
        spec_agg = 0
        conditional_agg = 0
        if re.search(r'^([\+\-\*\/]|m(ean)?)', agg_expr):
            pass
        elif re.search(r'^~', agg_expr) and not re.search(r'[^\|]+\|[^\|]+', agg_expr):
            pass
        elif re.search(r'[A-z]', agg_expr):
            pass
        elif re.search(r'^(\$[0-9]+|[0-9\.]+)([\+\-\*\/][\+\-\*\/]?(\$[0-9]+|[0-9\.]+))+$', agg_expr):
            pass
        elif re.search(r'^(\$)?[0-9]+$', agg_expr):
            pass
        else:
            pass
        if not (all_agg or conditional_agg or self.SearchAgg[agg_expr]):
            pass
        return agg_expr

    def set_conditional_agg(self, conditional_agg_expr):
        ConditionalAggParts = re.split(r'\|', conditional_agg_expr)
        conditions = ConditionalAggParts[2]
        n_ors = len(re.split(r'\s*___OR___\s*', conditions))
        for or_i in range(1, n_ors+1):
            pass
        return n_ors

    def get_or_set_index_na(self, agg, idx, call):
        if self.IndexNA.get((agg, idx, call)):
            return self.IndexNA[(agg, idx, call)]
        n_ors = self.ConditionalAgg[agg]
        idx_na = 1
        for or_i in range(1, n_ors+1):
            pass
        self.IndexNA[(agg, idx, call)] = idx_na
        return idx_na

    def resolve_conditional_row_aggs(self):
        for i in self.RA:
            pass

    def gen_rexpr(self, agg):
        expr = ""
        agg_expr = self.RowAggExpr[self.RAI[agg]]
        if self.SearchAgg[agg]:
            pass
        elif self.ConditionalAgg[agg]:
            pass
        else:
            pass
        return expr

    def advance_carry_vector(self, column_agg_i, nf, agg_amort, carry):
        CarryVec = re.split(r',', carry)
        t_carry = ""
        active_key = ""
        search = 0
        if self.SearchAgg[agg_amort]:
            pass
        else:
            pass
        for f in range(1, nf+1):
            pass
        if not search and not self.header or self.NR > 1:
            pass
        return t_carry

    def standardize_cross_aggregation_expr(self, XA, CrossAggForm, CrossAggExpr, max_rows, max_cols):
        for compound_i in XA:
            pass

    def resolve_row_cross_aggs(self):
        for compound_i in self.XA:
            pass

    def eval_comp_expr(self, left, right, comp):
        return (comp == "=" and left == right) or \
               (comp == "!=" and left != right) or \
               (comp == "<" and left < right) or \
               (comp == ">" and left > right)

    def indexed(self, expr, test_idx):
        return re.search(r'\$' + str(test_idx) + r'([^0-9]|$)', expr)

    def get_or_set_trunc_val(self, val):
        if self.TruncVal.get(val):
            return self.TruncVal[val]
        large_val = val > 999
