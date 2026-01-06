import os
import sys

sys.path.insert(0, '')
sys.path.insert(0, "C:\\Users\\tehal")
os.environ["PYTHONPATH"] = "C:\\Users\\tehal"  

# print(sys.path)

os.chdir("C:\\Users\\tehal")

from dev_scripts_py.tests.t_join import test_joins

test_joins()
