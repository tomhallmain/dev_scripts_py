import click
import os

from scripts.case import TextCaseConverter
from scripts.DataFile import DataFile
from scripts.dup_files import dups_main
from scripts.field_counts import FieldsCounter
from scripts.infer_field_separator import SeparatorInference
from scripts.index import index_main
from scripts.join import Join
from scripts.kill_port import kill_port_main
from scripts.move import move_main
from scripts.transpose import DataTransposer
from scripts.utils import Utils

@click.group(name="ds")
@click.argument('startpath')
@click.option('--debug/--no-debug', default=False)
def cli(startpath, debug):
    Utils.set_start_dir(startpath)
    Utils.set_debug(debug)
    if debug:
        click.echo('dev_scripts_py: Debug mode is on')

@cli.command()
def agg():
    """
    Aggregate field-based text data.
    """
    pass

@cli.command()
def asgn():
    pass

@cli.command()
@click.argument('tocase', default="pc")
@click.argument('text', default="")
@click.option('-fs', '--field-sep', default=None)
def case(tocase, text, field_sep):
    """
    Convert text data from one case to another.
    """
    try:
        data_file = DataFile(text, field_sep)
    except Exception:
        data_file = DataFile(None, field_sep) # TODO
    TextCaseConverter(tocase).recase(data_file)

@cli.command()
def cd():
    """
    Change to a different directory in context.
    """
    pass

@cli.command(name="dup_files")
@click.argument('dirpath')
@click.option('--select-deepest', '-d', is_flag=True, help="Select for best folder depth")
@click.option('--match-dir', '-m', is_flag=True, help="Only delete duplicates located in the same directory")
@click.option('--no-recurse', '-n', is_flag=True, help="Do not recurse")
@click.option('--exclude-dirs', '-e', default="", help="Comma-separated list of directories to exclude")
@click.option('--preferred-delete-dirs', '-p', default="", help="Comma-separated list of directories to prefer for deletion")
@click.option('--save-filedata', '-s', is_flag=True, help="Cache file data")
@click.option('--no-overwrite-filedata', '-o', is_flag=True, help="Do not overwrite file data cache")
def dups(dirpath=".", select_deepest=False, match_dir=False, no_recurse=False,
         exclude_dirs="", preferred_delete_dirs="", save_filedata=False, no_overwrite_filedata=True):
    """
    Identify and remove duplicate files.
    """
    dirpath = Utils.resolve_relative_path(dirpath)
    dups_main(dirpath, select_deepest=select_deepest, match_dir=match_dir, recursive=not no_recurse, 
              exclude_dir_string=exclude_dirs, preferred_delete_dirs_string=preferred_delete_dirs,
              save_filedata=save_filedata, no_overwrite_filedata=no_overwrite_filedata)

@cli.command()
@click.argument('source')
@click.argument('target')
@click.option('--filter', '-f', default=None, help="Filter pattern (tag like [video] or glob like *.mp4)")
def move(source, target, filter):
    """
    Move files or directories from source to target.
    Supports filtering with tags ([video], [audio], [document], [text], [bin]) or glob patterns.
    """
    source = Utils.resolve_relative_path(source)
    target = Utils.resolve_relative_path(target)
    move_main(source, target, filter)

@cli.command()
@click.argument('source')
@click.argument('target')
@click.option('--filter', '-f', default=None, help="Filter pattern (tag like [video] or glob like *.mp4)")
def copy(source, target, filter):
    """
    Copy files or directories from source to target.
    Supports filtering with tags ([video], [audio], [document], [text], [bin]) or glob patterns.
    """
    source = Utils.resolve_relative_path(source)
    target = Utils.resolve_relative_path(target)
    move_main(source, target, filter, copy=True)

@cli.command(name="kill_port")
@click.argument('port', type=int)
@click.option('--force', '-f', is_flag=True, help="Force-kill processes immediately (SIGKILL / taskkill /F)")
@click.option('--dry-run', '-n', is_flag=True, help="Show what would be killed without actually killing")
def kill_port(port, force, dry_run):
    """
    Kill all processes bound to PORT.

    Scans for every process with a socket on the given port (listeners first,
    then remaining connections) and terminates them.  Works on Windows
    (netstat + taskkill) and Unix (lsof / ss + signals).

    Example:  ds . kill_port 8188
    """
    kill_port_main(port, force=force, dry_run=dry_run)


@cli.command()
@click.argument('filepath', type=click.File(), required=False)
@click.option('--custom', '-c', is_flag=True, help="Custom field separator")
@click.option('--file_ext', '-e', is_flag=True, help="Use file extension")
@click.option('--high_certainty', '-h', is_flag=True, help="Calculate with high certainty")
def inferfs(filepath, custom=True, file_ext=True, high_certainty=False):
    """
    Infer field separator from data: ds inferfs filepath [reparse=f] [custom=t] [file_ext=t] [high_cert=f]
    """
#    reparse = False
    file_ext = False # TODO change to true
    data_file = DataFile(filepath)
    inference = SeparatorInference(custom=custom, use_file_ext=file_ext, high_certainty=high_certainty)
    print(inference.infer_separator(data_file))


@cli.command()
@click.argument('filepath', type=click.File(), required=False)
@click.option('--field-sep', '-s', default=None)
@click.option('--header', '-h', default=False)
def index(filepath, field_sep, header):
    """
    Print lines indexed: ds index [filepath]
    """
    data_file = DataFile(filepath, field_sep)
    data_file.get_field_separator()
    index_main(data_file, header)

@cli.command()
@click.argument('file', type=click.File(), required=False)
@click.option('--field-sep', '-s', default=None)
@click.option('--ofs', default=None)
def transpose(filepath, field_sep, ofs):
    """
    Transpose lines: ds transpose [filepath]
    """
    data_file = DataFile(filepath, field_sep)
    if ofs is None:
        ofs = data_file.get_field_separator()
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
@click.option('--standard_join', is_flag=True)
def join(file1, file2, field_sep=None, ofs=None, header=False, verbose=False, join="outer", null_off=False, merge=False, bias_merge_keys=None,
         left_label=None, right_label=None, inner_label=None, gen_keys=False, k1="1", k2=None, max_merge_fields=None, standard_join=False):
    """
    Print lines indexed: ds index [file]
    """
    data_file1 = DataFile(file1, field_sep)
    data_file2 = DataFile(file2, field_sep)
    join = Join(data_file1=data_file1, data_file2=data_file2, OFS=ofs, header=header, verbose=verbose, join=join,
                null_off=null_off, merge=merge, bias_merge_keys=bias_merge_keys, left_label=left_label,
                right_label=right_label, inner_label=inner_label, gen_keys=gen_keys, k1=k1, k2=k2,
                max_merge_fields=max_merge_fields, standard_join=standard_join)
    join.run()


@cli.command()
@click.argument('file', type=click.File(), required=False)
@click.option('--field-sep', '-s', default=None)
@click.option('--ofs', default=None)
@click.option('--fields', '-f', default="0")
@click.option('--min', '-m', default=1)
@click.option('--only-vals', '-v', is_flag=True)
def field_counts(file, field_sep, ofs, fields="0", min=1, only_vals=False):
    """
    Count fields in data: ds field_counts [file]
    """
    data_file = DataFile(file, field_sep)
    if ofs is None:
        ofs = data_file.get_field_separator()
    FieldsCounter(data_file, ofs=ofs, fields=fields, min=min, only_vals=only_vals).run()


# @cli.command()
# @click.argument('file', type=click.File(), required=False)
# @click.option('--field-sep', '-s', default=None)
# @click.option('--header', '-h', default=False)
# def join_multi(file, field_sep, header):
#     """
#     Print lines indexed: ds index [file]
#     """
#     data_file = DataFile(file, field_sep)
#     data_file.get_field_separator()
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
