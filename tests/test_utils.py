import os
import tempfile

from scripts.utils import Utils

def evaluate(process_res, expected, failure_message, debug=False):
    if process_res.returncode != 0:
        print(failure_message)
        exit(1)
    if process_res.stderr is not None and len(process_res.stderr)!= 0:
        print(process_res.stderr)
    differences = Utils.identify_string_differences(expected, process_res.stdout, debug=debug)
    if differences is not None:
        print(differences)
        print(failure_message)
        exit(1)

def temp_file(name, data):
    name = os.path.join(os.path.dirname(__file__), "data", "dsp_" + name)
    actual_file = open(name, "w")
    actual_file.write(data)
    actual_file.close()
    return name

