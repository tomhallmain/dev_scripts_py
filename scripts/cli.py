import click
import functools
import os
import sys

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


def wip(fn):
    """Mark a Click command callback as work-in-progress."""
    original_doc = fn.__doc__ or ""
    fn.__doc__ = original_doc.rstrip() + "\n\n    [WIP] Port in progress — may not function correctly."
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        click.echo(click.style(
            "Warning: this command is a work-in-progress port and may not function correctly.",
            fg='yellow',
        ))
        return fn(*args, **kwargs)
    return wrapper


def stub(fn):
    """Mark a Click command callback as a stub (incomplete port).

    Stubs are hidden from ``ds commands`` unless ``--all`` is passed.
    """
    original_doc = fn.__doc__ or ""
    fn.__doc__ = original_doc.rstrip() + "\n\n    [STUB] Not yet ported — implementation incomplete."
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        click.echo(click.style(
            "Warning: this command is a stub — the port is incomplete and may not work at all.",
            fg='red',
        ))
        return fn(*args, **kwargs)
    wrapper._ds_stub = True
    return wrapper


class AliasedGroup(click.Group):
    """A Click group that supports short aliases for commands."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aliases = {}          # alias -> canonical name
        self._reverse_aliases = {}  # canonical name -> list of aliases

    def add_alias(self, alias, cmd_name):
        self._aliases[alias] = cmd_name
        self._reverse_aliases.setdefault(cmd_name, []).append(alias)

    def get_command(self, ctx, cmd_name):
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv
        canonical = self._aliases.get(cmd_name)
        if canonical is not None:
            return super().get_command(ctx, canonical)
        return None

    def resolve_command(self, ctx, args):
        # Override so Click's error messages show the canonical name
        cmd_name, cmd, args = super().resolve_command(ctx, args)
        if cmd is None and args:
            canonical = self._aliases.get(cmd_name)
            if canonical:
                cmd = super().get_command(ctx, canonical)
                cmd_name = canonical
        return cmd_name, cmd, args

    def command(self, *args, aliases=None, **kwargs):
        decorator = super().command(*args, **kwargs)
        if aliases:
            def wrapper(fn):
                cmd = decorator(fn)
                for alias in aliases:
                    self.add_alias(alias, cmd.name)
                return cmd
            return wrapper
        return decorator

    def get_aliases_for(self, cmd_name):
        return self._reverse_aliases.get(cmd_name, [])


@click.group(name="ds", cls=AliasedGroup)
@click.argument('startpath')
@click.option('--debug/--no-debug', default=False)
def cli(startpath, debug):
    Utils.set_start_dir(startpath)
    Utils.set_debug(debug)
    if debug:
        click.echo('dev_scripts_py: Debug mode is on')

@cli.command()
@click.option('--all', '-a', 'show_all', is_flag=True, help="Include stub (incomplete) commands")
@click.pass_context
def commands(ctx, show_all):
    """
    List all available commands.
    """
    group = ctx.parent.command
    cmd_names = group.list_commands(ctx.parent)
    if not cmd_names:
        click.echo("No commands available.")
        return

    visible = []
    hidden_count = 0
    for name in cmd_names:
        cmd = group.get_command(ctx.parent, name)
        if not cmd:
            continue
        is_stub = getattr(cmd.callback, '_ds_stub', False)
        if is_stub and not show_all:
            hidden_count += 1
            continue
        help_text = cmd.get_short_help_str(limit=80)
        aliases = group.get_aliases_for(name) if hasattr(group, 'get_aliases_for') else []
        visible.append((name, aliases, help_text, is_stub))

    if not visible:
        click.echo("No commands available.")
        return

    max_len = max(len(name) for name, _, _, _ in visible)
    for name, aliases, help_text, is_stub in visible:
        alias_str = click.style(f" ({', '.join(aliases)})", fg='cyan') if aliases else ""
        tag = click.style(" [STUB]", fg='red') if is_stub else ""
        click.echo(f"  {name:<{max_len}}{alias_str}  {help_text}{tag}")

    if hidden_count and not show_all:
        click.echo(click.style(
            f"\n  ({hidden_count} stub command(s) hidden — use ds commands --all to show)",
            fg='bright_black',
        ))

@cli.command()
@wip
def agg():
    """
    Aggregate field-based text data.
    """
    click.echo("Not yet implemented.")

@cli.command()
@wip
def asgn():
    """
    Print lines matching assignment pattern.
    """
    click.echo("Not yet implemented.")

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
@wip
def cd():
    """
    Change to a different directory in context.
    """
    click.echo("Not yet implemented.")

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

@cli.command(aliases=["t"])
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


@cli.command(aliases=["jn"])
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


# ---------------------------------------------------------------------------
# Git commands
# ---------------------------------------------------------------------------

@cli.command(name="git_status", aliases=["gs"])
@click.argument('base_dir', default=None, required=False)
@click.option('--track-non-repos', '-t', is_flag=True, help="Also list non-repository directories")
def git_status(base_dir, track_non_repos):
    """
    Show git status for all repos under a directory.

    Defaults to the home directory when BASE_DIR is omitted.

    Example:  ds . git_status ~/repos
    """
    from scripts.git_commands import git_status_cmd
    if base_dir:
        base_dir = Utils.resolve_relative_path(base_dir)
    git_status_cmd(base_dir, track_non_repos=track_non_repos)


@cli.command(name="git_branch", aliases=["gb"])
@click.argument('base_dir', default=None, required=False)
def git_branch(base_dir):
    """
    List branches for all local git repos.

    Scans the home directory (or BASE_DIR) for git repositories and prints
    their branches.

    Example:  ds . git_branch
    """
    from scripts.git_commands import git_branch_cmd
    if base_dir:
        base_dir = Utils.resolve_relative_path(base_dir)
    git_branch_cmd(base_dir)


@cli.command(name="git_purge_local", aliases=["gpl"])
@click.argument('base_dir')
@click.argument('branches', nargs=-1, required=True)
def git_purge_local(base_dir, branches):
    """
    Purge specified branches from all local git repos under BASE_DIR.

    Example:  ds . git_purge_local ~/repos feature-old bugfix-stale
    """
    from scripts.git_commands import git_purge_local_cmd
    base_dir = Utils.resolve_relative_path(base_dir)
    git_purge_local_cmd(base_dir, branches)


@cli.command(name="git_add_com_push", aliases=["gacp"])
@click.argument('commit_message', required=False, default="")
@click.argument('prompt', required=False, default="t")
def git_add_com_push(commit_message, prompt):
    """
    Add, commit with message, and push.
    """
    from scripts.git_commands import git_add_com_push_cmd
    git_add_com_push_cmd(commit_message, prompt)


@cli.command(name="git_checkout", aliases=["gco"])
@click.argument('branch_pattern', required=False, default="")
@click.argument('new_branch', required=False, default="f")
def git_checkout(branch_pattern, new_branch):
    """
    Checkout branch matching pattern.
    """
    from scripts.git_commands import git_checkout_cmd
    git_checkout_cmd(branch_pattern, new_branch)


@cli.command(name="git_cross_view", aliases=["gcv"])
@click.argument('base_dir', required=False, default=None)
@click.option('--show-status', '-s', is_flag=True, help="Show staged/unstaged counts")
def git_cross_view(base_dir, show_status):
    """
    Display table of git repos vs branches.
    """
    from scripts.git_commands import git_cross_view_cmd
    if base_dir:
        base_dir = Utils.resolve_relative_path(base_dir)
    git_cross_view_cmd(base_dir, show_status=show_status)


@cli.command(name="git_diff")
@click.argument('git_args', nargs=-1, required=False)
def git_diff(git_args):
    """
    Diff shortcut for exclusions.
    """
    from scripts.git_commands import git_diff_cmd
    git_diff_cmd(git_args)


@cli.command(name="git_graph", aliases=["gg"])
def git_graph():
    """
    Print colorful git history graph.
    """
    from scripts.git_commands import git_graph_cmd
    git_graph_cmd()


@cli.command(name="git_recent", aliases=["gr"])
@click.argument('refs', required=False, default="heads")
@click.argument('run_context', required=False, default="display")
def git_recent(refs, run_context):
    """
    Display commits sorted by recency.
    """
    from scripts.git_commands import git_recent_cmd
    git_recent_cmd(refs=refs, run_context=run_context)


@cli.command(name="git_recent_all", aliases=["gra"])
@click.argument('refs', required=False, default="heads")
@click.argument('base_dir', required=False, default=None)
def git_recent_all(refs, base_dir):
    """
    Display recent commits for local repos.
    """
    from scripts.git_commands import git_recent_all_cmd
    if base_dir:
        base_dir = Utils.resolve_relative_path(base_dir)
    git_recent_all_cmd(refs=refs, base_dir=base_dir)


@cli.command(name="git_refresh", aliases=["grf"])
@click.argument('base_dir', required=False, default=None)
def git_refresh(base_dir):
    """
    Pull latest for all repos.
    """
    from scripts.git_commands import git_refresh_cmd
    if base_dir:
        base_dir = Utils.resolve_relative_path(base_dir)
    git_refresh_cmd(base_dir=base_dir)


@cli.command(name="git_squash", aliases=["gsq"])
@click.argument('n_commits', required=False, default=1, type=int)
@click.option('--yes', '-y', is_flag=True, help="Skip confirmation prompt")
def git_squash(n_commits, yes):
    """
    Squash last n commits.
    """
    from scripts.git_commands import git_squash_cmd
    git_squash_cmd(n_commits=n_commits, yes=yes)


@cli.command(name="git_time_stat", aliases=["gts"])
def git_time_stat():
    """
    Last local pull, change, and commit times.
    """
    from scripts.git_commands import git_time_stat_cmd
    git_time_stat_cmd()


@cli.command(name="git_word_diff", aliases=["gwdf"])
@click.argument('git_diff_args', nargs=-1, required=False)
def git_word_diff(git_diff_args):
    """
    Git word diff shortcut.
    """
    from scripts.git_commands import git_word_diff_cmd
    git_word_diff_cmd(git_diff_args)


@cli.command(name="git_branch_refs", aliases=["gbr"])
@click.argument('branch', required=False, default=None)
@click.argument('invert', required=False, default="f")
def git_branch_refs(branch, invert):
    """
    List branches merged to a branch.
    """
    from scripts.git_commands import git_branch_refs_cmd
    git_branch_refs_cmd(branch=branch, invert=invert)


# ---------------------------------------------------------------------------
# Simple utility commands
# ---------------------------------------------------------------------------

@cli.command(name="rev")
def rev():
    """
    Reverse lines from standard input.
    """
    from scripts.simple_commands import rev_cmd
    rev_cmd(sys.stdin)


@cli.command(name="join_by")
@click.argument('delimiter')
@click.argument('values', nargs=-1, required=False)
def join_by(delimiter, values):
    """
    Join values by a delimiter.
    """
    from scripts.simple_commands import join_by_cmd
    stdin_data = None if sys.stdin.isatty() else sys.stdin.read()
    join_by_cmd(delimiter, values, stdin_data=stdin_data)


@cli.command(name="iter")
@click.argument('text')
@click.argument('n', required=False, default=1, type=int)
@click.argument('fs', required=False, default="")
def iter_cmd(text, n, fs):
    """
    Repeat a string.
    """
    from scripts.simple_commands import iter_cmd as _iter_cmd
    _iter_cmd(text, n=n, fs=fs)


@cli.command(name="goog")
@click.argument('query', nargs=-1, required=False)
def goog(query):
    """
    Search Google.
    """
    from scripts.simple_commands import goog_cmd
    goog_cmd(query)


@cli.command(name="jira")
@click.argument('workspace_subdomain')
@click.argument('issue_or_query', required=False, default=None)
def jira(workspace_subdomain, issue_or_query):
    """
    Open Jira issue/search for a workspace.
    """
    from scripts.simple_commands import jira_cmd
    jira_cmd(workspace_subdomain, issue_or_query=issue_or_query)


@cli.command(name="insert")
@click.argument('sink')
@click.argument('where')
@click.argument('source', required=False, default=None)
@click.argument('inplace', required=False, default="f")
def insert(sink, where, source, inplace):
    """
    Redirect input into a file at line number or pattern.
    """
    from scripts.simple_commands import insert_cmd
    sink = Utils.resolve_relative_path(sink)
    source_path = Utils.resolve_relative_path(source) if source else None
    stdin_data = None if sys.stdin.isatty() else sys.stdin.read()
    insert_cmd(sink, where, source_path, inplace, stdin_data)


@cli.command(name="line")
@click.argument('seed_cmds', required=False, default=None)
@click.argument('line_cmds', required=False, default=None)
@click.argument('ifs', required=False, default="\n")
def line(seed_cmds, line_cmds, ifs):
    """
    Execute command(s) for each input line.
    """
    from scripts.simple_commands import line_cmd
    if line_cmds is None:
        line_cmds = seed_cmds
        seed_cmds = None
    stdin_data = None if sys.stdin.isatty() else sys.stdin.read()
    line_cmd(seed_cmds=seed_cmds, line_cmds=line_cmds, ifs=ifs, stdin_data=stdin_data)


# ---------------------------------------------------------------------------
# Conda commands
# ---------------------------------------------------------------------------

@cli.command(name="conda_check")
@click.argument('packages', nargs=-1, required=True)
def conda_check(packages):
    """
    Check which conda environments have given packages installed.

    Example:  ds . conda_check numpy pandas scikit-learn
    """
    from scripts.conda_check_packages import main as _conda_check_main
    old_argv = sys.argv
    sys.argv = ['conda_check'] + list(packages)
    try:
        _conda_check_main()
    finally:
        sys.argv = old_argv


@cli.command(name="conda_envs")
@click.option('--json', 'as_json', is_flag=True, help="Output JSON instead of a table")
@click.option('--sort', type=click.Choice(['name', 'size', 'python']), default='python', help="Sort column")
def conda_envs(as_json, sort):
    """
    List conda environments with Python version, size, and package count.

    Example:  ds . conda_envs --sort size
    """
    from scripts.conda_env_details import main as _conda_envs_main
    argv = []
    if as_json:
        argv.append('--json')
    argv.extend(['--sort', sort])
    _conda_envs_main(argv)


# ---------------------------------------------------------------------------
# Data comparison / analysis commands
# ---------------------------------------------------------------------------

@cli.command()
@click.argument('file1', type=click.Path(exists=True))
@click.argument('file2', type=click.Path(exists=True))
@click.option('--key', '-k', type=int, default=None, help="Key field index (1-based) for matching")
@click.option('--fs', '-s', default=None, help="Field separator for both files")
def matches(file1, file2, key, fs):
    """
    Get matching records between two files.

    Example:  ds . matches data1.csv data2.csv --key 1
    """
    from scripts.matches import FileComparator
    file1 = Utils.resolve_relative_path(file1)
    file2 = Utils.resolve_relative_path(file2)
    comparator = FileComparator(file1, file2, fs=fs, key=key)
    comparator.compare_files()
    comparator.print_matches()


@cli.command(name="power")
@click.argument('file', type=click.Path(exists=True))
@click.option('--min', '-m', 'min_count', default=0, help="Minimum occurrence count")
@click.option('--return-fields', '-r', is_flag=True, help="Return field proportions instead of counts")
@click.option('--invert', '-i', is_flag=True, help="Invert the min filter")
@click.option('--choose', '-c', type=int, default=None, help="Restrict combination size")
def power(file, min_count, return_fields, invert, choose):
    """
    Combinatorial frequency analysis of data field values.

    Example:  ds . power data.txt --min 2 --choose 2
    """
    from scripts.DataFile import DataFile
    from scripts.power import DataAnalyzer
    file = Utils.resolve_relative_path(file)
    data_file = DataFile(file)
    analyzer = DataAnalyzer(data_file, min=min_count, return_fields=return_fields, invert=invert, choose=choose)
    analyzer.analyze()
    analyzer.print_results()


@cli.command(name="random")
@click.argument('mode', default="number")
@click.argument('text', default="", required=False)
def random_cmd(mode, text):
    """
    Generate a random number or randomize text.

    MODE is 'number' (default) or 'text'.

    Example:  ds . random text "Hello World"
    """
    from scripts.randomize import randomize_text
    randomize_text(mode, text)


@cli.command(name="unicode")
@click.argument('conversion', default="codepoint", type=click.Choice(['codepoint', 'hex', 'octet']))
def unicode_cmd(conversion):
    """
    Convert UTF-8 unicode representations from stdin.

    CONVERSION is 'codepoint' (default), 'hex', or 'octet'.

    Example:  echo "data" | ds . unicode hex
    """
    from scripts.unicode import Converter
    converter = Converter()
    converter.set_conversion_type(conversion)
    converter.convert_input(sys.stdin)


# ---------------------------------------------------------------------------
# Graph / visualization commands
# ---------------------------------------------------------------------------

@cli.command()
@click.option('--print-bases', '-p', is_flag=True, help="Include base nodes in output")
@wip
def graph(print_bases):
    """
    Extract graph relationships from DAG base data (reads from stdin).

    Input: lines of "child parent" pairs on stdin.

    Example:  cat edges.txt | ds . graph --print-bases
    """
    from scripts.graph import backtrace
    shoots = {}
    bases = {}
    cycles = {}

    for line in sys.stdin:
        line = line.strip()
        if line:
            parts = line.split()
            if len(parts) > 1:
                shoots[parts[0]] = parts[1]
                bases[parts[1]] = 1
            elif len(parts) == 1:
                bases[parts[0]] = 1

    if print_bases:
        for base in bases:
            if base not in shoots:
                click.echo(base)

    for shoot in shoots:
        if shoots[shoot] and (print_bases or shoot not in bases):
            if shoot == shoots[shoot]:
                cycles[shoot] = 1
                continue
            click.echo(backtrace(shoot, shoots[shoot], shoots))

    if cycles:
        click.echo(f"WARNING: {len(cycles)} cycles found!")
        for cycle in cycles:
            click.echo(f"CYCLENODE__ {cycle}")
        sys.exit(1)


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--stag-size', '-s', default=5, help="Number of spaces to indent per field")
@wip
def stagger(filepath, stag_size):
    """
    Print tabular data in staggered rows.

    Example:  ds . stagger data.txt --stag-size 4
    """
    from scripts.stagger import print_staggered
    filepath = Utils.resolve_relative_path(filepath)
    print_staggered(filepath, stag_size=stag_size)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--y-keys', '-y', required=True, help="Comma-separated y-axis key fields")
@click.option('--x-keys', '-x', required=True, help="Comma-separated x-axis key fields")
@click.option('--z-keys', '-z', default=None, help="Comma-separated z-axis value fields")
@click.option('--agg-type', '-a', default=None, type=click.Choice(['count', 'sum', 'product', 'mean']),
              help="Aggregation type")
@wip
def pivot(file, y_keys, x_keys, z_keys, agg_type):
    """
    Pivot tabular data.

    Example:  ds . pivot data.csv -y 1 -x 2
    """
    from scripts.pivot import Pivot
    file = Utils.resolve_relative_path(file)
    p = Pivot(file, y_keys, x_keys, z_keys=z_keys, agg_type=agg_type)
    with open(file, 'r') as f:
        p.data = [line.strip().split() for line in f]
    p.pivot()
    p.print_pivot()


@cli.command()
@wip
def hist():
    """
    Print histograms for numeric fields in data (reads from stdin).

    Example:  cat data.txt | ds . hist
    """
    from scripts.hist import main as _hist_main
    _hist_main()


# ---------------------------------------------------------------------------
# Stub commands — incomplete ports, hidden from `ds commands` by default
# ---------------------------------------------------------------------------

@cli.command(name="diff_fields", aliases=["df"])
@click.argument('file1', type=click.Path(exists=True))
@click.argument('file2', type=click.Path(exists=True))
@click.argument('op', default='-')
@click.option('--exclude-fields', '-e', default="0", help="Comma-separated field indices to exclude")
@click.option('--header', '-h', is_flag=True, help="First row is a header")
@click.option('--summary', is_flag=True, help="Print diff summary")
@click.option('--summary-sort', is_flag=True, help="Sort the diff summary")
@stub
def diff_fields(file1, file2, op, exclude_fields, header, summary, summary_sort):
    """
    Elementwise diff of two datasets.

    Example:  ds . diff_fields a.csv b.csv - --header
    """
    from scripts.diff_fields import DiffFields
    file1 = Utils.resolve_relative_path(file1)
    file2 = Utils.resolve_relative_path(file2)
    df = DiffFields(file1, file2, op, exclude_fields, header, summary=summary, summary_sort=summary_sort)
    df.run()


@cli.command(name="fit")
@stub
def fit():
    """
    Fit fielded data in columns with dynamic width.
    """
    click.echo("Not yet ported.")


@cli.command(name="reo")
@stub
def reo():
    """
    Reorder, repeat, or slice data by rows and columns.
    """
    click.echo("Not yet ported.")


@cli.command(name="sortm", aliases=["s"])
@stub
def sortm():
    """
    Sort with inferred field separator (multi-char support).
    """
    click.echo("Not yet ported.")


@cli.command(name="subsep")
@click.argument('filepath', type=click.Path(exists=True))
@click.argument('subsep_pattern')
@click.option('--nomatch-handler', '-n', default=r'\s+', help="Fallback split pattern for non-matching lines")
@stub
def subsep(filepath, subsep_pattern, nomatch_handler):
    """
    Extend fields by a common sub-separator.

    Example:  ds . subsep data.txt ":"
    """
    from scripts.subseparator import SubseparatorFinder
    filepath = Utils.resolve_relative_path(filepath)
    finder = SubseparatorFinder(subsep_pattern=subsep_pattern, nomatch_handler=nomatch_handler)
    finder.process_file(filepath)


@cli.command(name="inferh")
@stub
def inferh():
    """
    Infer if headers are present in the first row of a file.
    """
    click.echo("Not yet ported (still AWK).")


@cli.command(name="cardinality")
@click.argument('filepath', type=click.Path(exists=True))
@stub
def cardinality(filepath):
    """
    Calculate cardinality (distinct values) per field.

    Example:  ds . cardinality data.txt
    """
    from scripts.cardinality import Cardinality
    filepath = Utils.resolve_relative_path(filepath)
    c = Cardinality()
    with open(filepath, 'r') as f:
        for line in f:
            c.process_line(line)
    c.print_cardinality()


@cli.command(name="prod")
@click.argument('files', nargs=-1, required=True, type=click.Path(exists=True))
@stub
def prod(files):
    """
    Cartesian product of lines from multiple files.

    Example:  ds . prod set_a.txt set_b.txt
    """
    from scripts.product import product_main
    product_main([Utils.resolve_relative_path(f) for f in files])


@cli.command(name="shape")
@stub
def shape():
    """
    Print data shape by length or pattern (reads from stdin).

    Example:  cat data.txt | ds . shape
    """
    from scripts.shape import shape_main
    shape_main()


@cli.command(name="field_uniques", aliases=["u"])
@click.argument('fields_spec', default="0")
@stub
def field_uniques(fields_spec):
    """
    Get unique values from specified fields (reads from stdin).

    Example:  cat data.txt | ds . field_uniques 1,2
    """
    from scripts.field_uniques import field_uniques_main
    field_uniques_main(fields_spec)


@cli.command(name="enti")
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--sep', '-s', default=r'\s+', help="Separator pattern")
@click.option('--min', '-m', 'min_count', default=0, help="Minimum count to display")
@stub
def enti(filepath, sep, min_count):
    """
    Print text entities separated by a pattern.

    Example:  ds . enti data.txt --sep "," --min 2
    """
    from scripts.separated_entities import TextEntities
    filepath = Utils.resolve_relative_path(filepath)
    te = TextEntities(min_count=min_count, separator=sep)
    te.process_file(filepath)
    te.print_entities()


@cli.command(name="diff")
@click.argument('file1', type=click.Path(exists=True))
@click.argument('file2', type=click.Path(exists=True))
@click.option('--suppress-common', '-s', is_flag=True, help="Suppress common lines")
@click.option('--no-color', is_flag=True, help="Disable colorized output")
@stub
def diff_cmd(file1, file2, suppress_common, no_color):
    """
    Side-by-side diff with colorized output.

    Example:  ds . diff old.txt new.txt
    """
    import shutil
    import subprocess
    file1 = Utils.resolve_relative_path(file1)
    file2 = Utils.resolve_relative_path(file2)

    tty_width = shutil.get_terminal_size().columns
    diff_args = ['diff', '--side-by-side', f'--width={tty_width}']
    if suppress_common:
        diff_args.append('--suppress-common-lines')
    diff_args.extend([file1, file2])

    result = subprocess.run(diff_args, capture_output=True, text=True)
    lines = result.stdout.splitlines()

    if not lines:
        click.echo("Files are identical.")
        return

    if no_color:
        for line in lines:
            click.echo(line)
    else:
        from scripts.diff_color import DiffColor
        dc = DiffColor(tty_width // 2)
        dc.color_diff(lines)


@cli.command(name="inferk")
@stub
def inferk():
    """
    Infer join fields between two text data files.
    """
    click.echo("Not yet ported (script has mixed AWK/Python syntax).")


@cli.command(name="grepvi", aliases=["gvi"])
@click.argument('search')
@click.argument('target', default=".", required=False)
@click.option('--edit-all', '-a', is_flag=True, help="Open all matching files in editor")
@click.option('--no-edit', '-n', is_flag=True, help="Only list matches, don't open editor")
@click.option('--print', '-p', 'print_matches', is_flag=True, help="Print matches in addition to opening editor")
def grepvi(search, target, edit_all, no_edit, print_matches):
    """
    Grep for a pattern and open matching files in an editor.

    Uses $EDITOR (falls back to vim, code, nano, or notepad).
    Matches are printed automatically with --no-edit; use --print
    to also see them when opening the editor.

    Example:  ds grepvi "TODO" src/
    """
    from scripts.grep_edit import grep_and_edit
    target = Utils.resolve_relative_path(target)
    grep_and_edit(search, target, edit_all=edit_all, edit=not no_edit,
                  print_matches=print_matches or None)


@cli.command(name="vi")
@click.argument('search')
@click.argument('directory', default=".", required=False)
@click.option('--edit-all', '-a', is_flag=True, help="Open all matching files in editor")
@click.option('--no-edit', '-n', is_flag=True, help="Only list matches, don't open editor")
@click.option('--print', '-p', 'print_matches', is_flag=True, help="Print matches in addition to opening editor")
def vi_cmd(search, directory, edit_all, no_edit, print_matches):
    """
    Search for files by name and open in an editor.

    Uses $EDITOR (falls back to vim, code, nano, or notepad).
    Matches are printed automatically with --no-edit; use --print
    to also see them when opening the editor.

    Example:  ds vi "*.py" src/
    """
    from scripts.grep_edit import find_and_edit
    directory = Utils.resolve_relative_path(directory)
    find_and_edit(search, directory, edit_all=edit_all, edit=not no_edit,
                  print_matches=print_matches or None)


def main():
    try:
        cli()
    finally:
        DataFile.cleanup()
    

if __name__ == '__main__':
    cli()
