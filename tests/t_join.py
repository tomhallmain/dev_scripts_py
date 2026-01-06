import os
import subprocess

from dev_scripts_py.tests.test_utils import evaluate, temp_file

tmp_join = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data", "tmp_join")

def test_joins():
    """
    Test the join command
    """
    test_join_readme_basic_cases()
    test_join_readme_multi_keyset_cases()
    test_join_readme_merge_case()
    test_join_merge_field_max_null_off()
    test_join_extra_unmatched_right_join()
    test_join_standard_join_case()

def test_join_readme_basic_cases():
    """
    Test the join command README cases
    """

    expected='''a b c d b c
1 2 3 4 3 2
'''

    in_args = ["(", "echo", "a", "b", "c", "d", "&&", "echo", "1", "3", "2", "4", ")", "|", "ds", "join", tmp_join, "--join=inner", "--k1=1,4"]
    out = subprocess.run(in_args, shell=True, encoding="utf-8", capture_output=True)
    evaluate(out, expected, "ds join failed readme single keyset case")

    in_args = ["(", "echo", "a", "b", "c", "d", "&&", "echo", "1", "3", "2", "4", ")", "|", "ds", "join", tmp_join, "--join=inner", "--k1=a,d"]
    out = subprocess.run(in_args, shell=True, encoding="utf-8", capture_output=True)
    evaluate(out, expected, "ds join failed readme single keyset gen keys case")

def test_join_readme_multi_keyset_cases():


    expected='''a c b d
1 2 3 4
'''

    in_args = ["(", "echo", "a", "b", "c", "d", "&&", "echo", "1", "3", "2", "4", ")", "|", "ds", "join", tmp_join, "--join=right", "--k1=1,2,3,4", "--k2=1,3,2,4"]
    out = subprocess.run(in_args, shell=True, encoding="utf-8", capture_output=True)
    evaluate(out, expected, "ds join failed readme multi-keyset case")

    in_args = ["(", "echo", "a", "b", "c", "d", "&&", "echo", "1", "3", "2", "4", ")", "|", "ds", "join", tmp_join, "--join=right", "--k1=a,b,c,d", "--k2=a,c,b,d"]
    out = subprocess.run(in_args, shell=True, encoding="utf-8", capture_output=True)
    evaluate(out, expected, "ds join failed readme multi-keyset gen keys case")

def test_join_readme_merge_case():
    expected='''a b c d
1 3 2 4
1 2 3 4
'''

    in_args = ["(", "echo", "a", "b", "c", "d", "&&", "echo", "1", "3", "2", "4", ")", "|", "ds", "join", tmp_join, "--join=outer", "--merge"]
    out = subprocess.run(in_args, shell=True, encoding="utf-8", capture_output=True)
    evaluate(out, expected, "ds join failed readme merge case")

def test_join_merge_field_max_null_off():
    expected='''a b c d d
1 3 2  4
1 2 3 4 
'''

    in_args = ["(", "echo", "a", "b", "c", "d", "&&", "echo", "1", "3", "2", "4", ")", "|", "ds", "join", tmp_join, "--join=outer", "--merge", "--max-merge-fields=3", "--null-off"]
    out = subprocess.run(in_args, shell=True, encoding="utf-8", capture_output=True)
    evaluate(out, expected, "ds join failed merge field max null off case")


def test_join_extra_unmatched_right_join():
    tmp1 = temp_file("test_join1", "a 1\na 2\nb 2\nc 1\nb 1")
    tmp2 = temp_file("test_join2", "a 1\na 2\na 3\na 4\na 3")
    expected='''a 1 1
a 2 2
a <NULL> 3
a <NULL> 4
a <NULL> 3
b 2 <NULL>
c 1 <NULL>
b 1 <NULL>
'''
    in_args = ["ds", "join", tmp1, tmp2, "--join=outer", "--k1=1"]
    try:
        out = subprocess.run(in_args, shell=True, encoding="utf-8", capture_output=True)
        evaluate(out, expected, 'ds join failed extra unmatched right join case')
    except subprocess.CalledProcessError as e:
        print(e.stderr)
    os.remove(tmp1)
    os.remove(tmp2)

def test_join_standard_join_case():
    tmp1 = temp_file("test_join1", "a 1\na 2\nb 2\nc 1\nb 1")
    tmp2 = temp_file("test_join2", "a 1\na 2\na 3\na 4\na 3")
    expected='''a 1 1
a 2 1
a 1 2
a 2 2
a 1 3
a 2 3
a 1 4
a 2 4
a 1 3
a 2 3
b 2 <NULL>
b 1 <NULL>
c 1 <NULL>'''
    in_args = ["ds", "join", tmp1, tmp2, "--join=outer", "--k1=1", "--standard_join"]
    try:
        out = subprocess.run(in_args, shell=True, encoding="utf-8", capture_output=True)
        evaluate(out, expected, 'ds:join failed standard join case', debug=True)
    except subprocess.CalledProcessError as e:
        print(e.stderr)
#    os.remove(tmp1)
#    os.remove(tmp2)

# expected="$(join /tmp/ds_join_test1 /tmp/ds_join_test2 | sort)"
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 i 1 -v standard_join=1 | sort)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed inner join unix join case'

# [ $(ds:join "$jnf1" "$jnf2" o 1 | grep -c "") -gt 15 ]        || ds:fail 'ds:join failed one-arg shell case'
# [ $(ds:join "$jnf1" "$jnf2" r -v ind=1 | grep -c "") -gt 15 ] || ds:fail 'ds:join failed awkarg nonkey case'
# [ $(ds:join "$jnf1" "$jnf2" l -v k=1 | grep -c "") -gt 15 ]   || ds:fail 'ds:join failed awkarg key case'
# [ $(ds:join "$jnf1" "$jnf2" i 1 | grep -c "") -gt 15 ]        || ds:fail 'ds:join failed inner join case'

# ds:join $jnf1 $jnf2 -v ind=1 > $tmp
# cmp --silent $tmp $jnd1                                     || ds:fail 'ds:join failed base outer join case'
# cat $jnf2 | ds:join $jnf1 -v ind=1 > $tmp
# cmp --silent $tmp $jnd1                                     || ds:fail 'ds:join failed base outer join case piped infer key'
# ds:join "$jnr1" "$jnr2" o 2,3,4,5 > $tmp
# cmp --silent $tmp $jnrjn1                                   || ds:fail 'ds:join failed repeats partial keyset case'
# ds:join "$jnr1" "$jnr2" o "h,j,f,total" > $tmp
# cmp --silent $tmp $jnrjn1                                   || ds:fail 'ds:join failed repeats partial keyset gen keys case'
# ds:join "$jnr3" "$jnr4" o merge -v verbose=1 > $tmp
# cmp --silent $tmp $jnrjn2                                   || ds:fail 'ds:join failed repeats merge case'

# echo -e "a b d f\nd c e f" > /tmp/ds_join_test1
# echo -e "a b d f\nd c e f\ne r t a\nt o y l" > /tmp/ds_join_test2
# echo -e "a b l f\nd p e f\ne o t a\nt p y 6" > /tmp/ds_join_test3

# expected='a b d f a d f a l f'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 i 2)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 2-join inner case'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 i b)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 2-join inner gen key case'

# expected='a b l f
# d p e f
# e o t a
# t p y 6
# a b d f
# d c e f
# t o y l
# e r t a'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 o merge)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 2-join merge case'

# expected='a <NULL> l <NULL> <NULL> <NULL> b f
# d c e f c f p f
# e <NULL> t <NULL> r a o a
# t <NULL> y <NULL> o l p 6
# a b d f b f <NULL> <NULL>'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 o 1,3)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 2-join multikey case 1'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 o a,d -v inherit_keys=1)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 2-join multikey case 1 - gen and inherit keys'

# expected='a b d f b d b l
# d c e f c e p e
# e <NULL> <NULL> a r t o t
# t <NULL> <NULL> 6 <NULL> <NULL> p y
# t <NULL> <NULL> l o y <NULL> <NULL>'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 o 4,1)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 2-join multikey case 2'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 o "f,a")"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 2-join multikey gen keys case 2'

# echo -e "a b d 3\nd c e f" > /tmp/ds_join_test4

# expected='a b d f b d f b l f b d 3
# d c e f c e f p e f c e f'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 /tmp/ds_join_test4 i 1)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 3-join inner case'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 /tmp/ds_join_test4 i a)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 3-join inner gen key case'

# expected='a b d f b f <NULL> <NULL> b 3
# d c e f c f p f c f
# t <NULL> y <NULL> o l p 6 <NULL> <NULL>
# e <NULL> t <NULL> r a o a <NULL> <NULL>
# a <NULL> l <NULL> <NULL> <NULL> b f <NULL> <NULL>'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 /tmp/ds_join_test4 o 1,3)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 3-join outer case'

# echo -e "a,b,c,d\n1,2,3,4\n1,2,2,5" > /tmp/ds_join_test1
# echo -e "a b c d\n1 3 2 4" > /tmp/ds_join_test2
# echo -e "a b c d\n1 3 2\n1 2 3 7" > /tmp/ds_join_test3

# expected='a,b,c,d
# 1,3,2,4
# 1,2,3,7
# 1,2,2,5'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 outer merge -v bias_merge_keys=4)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 3-join bias merge default case'

# expected='a,b,c,d
# 1,3,2,<NULL>
# 1,2,3,7
# 1,2,2,<NULL>'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 outer merge -v bias_merge_keys=4 -v full_bias=1)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 3-join bias merge full_bias case'

# expected='a,b,c,d
# 1,3,2,
# 1,2,3,7
# 1,2,2,'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 outer merge -v bias_merge_keys=4 -v full_bias=1 -v null_off=1)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 3-join bias merge full_bias null_off case'
# actual="$(ds:join /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 outer merge -v bias_merge_exclude_keys=1,2,3 -v full_bias=1 -v null_off=1)"
# [ "$actual" = "$expected" ]                                 || ds:fail 'ds:join failed 3-join bias merge exclude keys full_bias null_off case'

# rm /tmp/ds_join_test1 /tmp/ds_join_test2 /tmp/ds_join_test3 /tmp/ds_join_test4

# cat "$jnf1" > $tmp
# ds:comps $jnf1 $tmp                                         || ds:fail 'comps failed no complement case'
# [ $(ds:comps $jnf1 $tmp -v verbose=1 | grep -c "") -eq 7 ]  || ds:fail 'comps failed no complement verbose case'
# [ "$(ds:comps $jnf1{,})" = 'Files are the same!' ]          || ds:fail 'comps failed no complement samefile case'
# [ $(ds:comps $jnf1 $jnf2 -v k1=2 -v k2=3,4 -v verbose=1 | grep -c "") -eq 196 ] \
#                                                             || ds:fail 'comps failed complments case'

# [ "$(ds:matches $jnf1 $jnf2 -v k1=2 -v k2=2)" = "NO MATCHES FOUND" ] \
#                                                             || ds:fail 'matches failed no matches case'
# [ $(ds:matches $jnf1 $jnf2 -v k=1 | grep -c "") = 167 ]     || ds:fail 'matches failed matches case'
# [ $(ds:matches $jnf1 $jnf2 -v k=1 -v verbose=1 | grep -c "") = 169 ] \
#                                                             || ds:fail 'matches failed matches case'






if __name__ == "__main__":
    test_joins()

