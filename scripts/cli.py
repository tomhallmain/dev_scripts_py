import click

from scripts.DataFile import DataFile
from scripts.dup_files import dups_main
from scripts.infer_field_separator import SeparatorInference
from scripts.utils import Utils

@click.group(name="ds")
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    Utils.set_debug(debug)
    if debug:
        click.echo('Debug mode is on')

@cli.command()
def agg():
    pass

@cli.command()
def asgn():
    pass

@cli.command()
def case():
    pass

@cli.command()
def cd():
    pass

@cli.command(name="dup_files")
@click.argument('dirpath')
def dups(dirpath="."):
    dups_main(dirpath)

@cli.command()
@click.argument('file', type=click.File())
@click.option('--custom', '-c', is_flag=True, help="Custom field separator")
@click.option('--file_ext', '-e', is_flag=True, help="Use file extension")
@click.option('--high_certainty', '-h', is_flag=True, help="Calculate with high certainty")
def inferfs(file, custom=True, file_ext=True, high_certainty=False):
    """
    Infer field separator from data: ds inferfs file [reparse=f] [custom=t] [file_ext=t] [high_cert=f]
    """
#    reparse = False
    file_ext = False # TODO change to true

    if file_ext:
        extension = Utils.get_file_extension(file)
        if extension in ['csv', 'tsv', 'properties']:
            if extension == 'csv':
                print(',')
            elif extension == 'tsv':
                print('\t')
            elif extension == 'properties':
                print('=')
            return

    data_file = DataFile(file)
    print(SeparatorInference(custom=custom, high_certainty=high_certainty).infer_separator(data_file))

# Add other functions here following the same pattern
# ...

def main():
    cli()

if __name__ == '__main__':
    cli()
