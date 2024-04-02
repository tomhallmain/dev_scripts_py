import click
import os

from dev_scripts_py.scripts.case import TextCaseConverter
from dev_scripts_py.scripts.DataFile import DataFile
from dev_scripts_py.scripts.dup_files import dups_main
from dev_scripts_py.scripts.infer_field_separator import SeparatorInference
from dev_scripts_py.scripts.index import index_main
from dev_scripts_py.scripts.join import Join
from dev_scripts_py.scripts.transpose import DataTransposer
from dev_scripts_py.scripts.utils import Utils

@click.group(name="ds")
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    Utils.set_debug(debug)
    if debug:
        click.echo('dev_scripts_py: Debug mode is on')

@cli.command()
def agg():
    pass

@cli.command()
def asgn():
    pass

@cli.command()
@click.argument('tocase', default="pc")
@click.argument('text', default="")
@click.option('-fs', '--field-sep', default=None)
def case(tocase, text, field_sep):
    if os.path.isfile(text) and not os.path.isdir(text):
        data_file = DataFile(text, field_sep)
    else:
        data_file = DataFile(None, field_sep)
    TextCaseConverter(tocase).recase(data_file)

@cli.command()
def cd():
    pass

@cli.command(name="dup_files")
@click.argument('dirpath')
@click.option('--select-deepest', '-d', is_flag=True, help="Select for best folder depth")
@click.option('--match-dir', '-m', is_flag=True, help="Only delete duplicates located in the same directory")
@click.option('--no-recurse', '-n', is_flag=True, help="Do not recurse")
@click.option('--exclude-dirs', '-e', default="", help="Comma-separated list of directories to exclude")
def dups(dirpath=".", select_deepest=False, match_dir=False, no_recurse=False, exclude_dirs=""):
    dups_main(dirpath, select_deepest=select_deepest, match_dir=match_dir, recursive=not no_recurse, exclude_dir_string=exclude_dirs)

@cli.command()
@click.argument('file', type=click.File(), required=False)
@click.option('--custom', '-c', is_flag=True, help="Custom field separator")
@click.option('--file_ext', '-e', is_flag=True, help="Use file extension")
@click.option('--high_certainty', '-h', is_flag=True, help="Calculate with high certainty")
def inferfs(file, custom=True, file_ext=True, high_certainty=False):
    """
    Infer field separator from data: ds inferfs file [reparse=f] [custom=t] [file_ext=t] [high_cert=f]
    """
#    reparse = False
    file_ext = False # TODO change to true
    data_file = DataFile(file)
    inference = SeparatorInference(custom=custom, use_file_ext=file_ext, high_certainty=high_certainty)
    print(inference.infer_separator(data_file))


@cli.command()
@click.argument('file', type=click.File(), required=False)
@click.option('--field-sep', '-s', default=None)
@click.option('--header', '-h', default=False)
def index(file, field_sep, header):
    """
    Print lines indexed: ds index [file]
    """
    data_file = DataFile(file, field_sep)
    data_file.detect_field_separator()
    index_main(data_file, header)

@cli.command()
@click.argument('file', type=click.File(), required=False)
@click.option('--field-sep', '-s', default=None)
@click.option('--ofs', default=None)
def transpose(file, field_sep, ofs):
    """
    Transpose lines: ds transpose [file]
    """
    data_file = DataFile(file, field_sep)
    if ofs is None:
        ofs = data_file.detect_field_separator()
    DataTransposer(data_file, ofs=ofs).transpose()


@cli.command()
@click.argument('file1', type=click.File(), required=True)
@click.argument('file2', type=click.File(), required=False)
@click.option('--field-sep', '-s', default=None)
@click.option('--ofs', default=None)
@click.option('--header', '-h', default=False)
@click.option('--verbose', '-v', is_flag=True)
@click.option('--join', '-j', default="outer")
@click.option('--merge', '-m', is_flag=True)
@click.option('--null-off', is_flag=True)
@click.option('--bias-merge-keys', default=None)
@click.option('--left-label', default=None)
@click.option('--right-label', default=None)
@click.option('--inner-label', default=None)
@click.option('--gen-keys', is_flag=True)
@click.option('--k1', default="1")
@click.option('--k2', default=None)
@click.option('--max-merge-fields', default=None)
def join(file1, file2, field_sep=None, ofs=None, header=False, verbose=False, join="outer", null_off=False, merge=False, bias_merge_keys=None,
         left_label=None, right_label=None, inner_label=None, gen_keys=False, k1="1", k2=None, max_merge_fields=None):
    """
    Print lines indexed: ds index [file]
    """
    data_file1 = DataFile(file1, field_sep)
    data_file2 = DataFile(file2, field_sep)
    join = Join(data_file1=data_file1, data_file2=data_file2, OFS=ofs, header=header, verbose=verbose, join=join,
                null_off=null_off, merge=merge, bias_merge_keys=bias_merge_keys, left_label=left_label,
                right_label=right_label, inner_label=inner_label, gen_keys=gen_keys, k1=k1, k2=k2, max_merge_fields=max_merge_fields)
    join.run()


# @cli.command()
# @click.argument('file', type=click.File(), required=False)
# @click.option('--field-sep', '-s', default=None)
# @click.option('--header', '-h', default=False)
# def join_multi(file, field_sep, header):
#     """
#     Print lines indexed: ds index [file]
#     """
#     data_file = DataFile(file, field_sep)
#     data_file.detect_field_separator()
#     index_main(data_file, header)


# Add other functions here following the same pattern
# ...

def main():
    try:
        cli()
    finally:
        DataFile.cleanup()
    

if __name__ == '__main__':
    cli()
