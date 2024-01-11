import os
import sys

sys.path.insert(0, '')
sys.path.insert(0, "C:\\Users\\tehal")
os.environ["PYTHONPATH"] = "C:\\Users\\tehal"  

# print(sys.path)

os.chdir("C:\\Users\\tehal")

from scripts import cli

if __name__ == "__main__":
    sys.exit(cli.main())
