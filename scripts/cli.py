import click
import functools
import os
import re
import sys

from scripts.case import TextCaseConverter
from scripts.cli_arg_parse_utils import (
    CliArgContext,
    EXTRA_ARG_WARN_FIRST_FILE_ONLY,
    PathCandidatePredicate,
    parse_non_negative_int_arg,
    regex_test_match,
    validate_positive_key_field,
)
from scripts.DataFile import DataFile
from scripts.dup_files import dups_main
from scripts.field_counts import FieldsCounter
from scripts.infer_field_separator import SeparatorInference
from scripts.join import Join
from scripts.kill_port import kill_port_main
from scripts.move import move_main
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
@click.argument("args", nargs=-1, required=False)
@click.option('--field-sep', '-s', default=None, help="Override the inferred field separator")
@click.option('--header', '-h', 'header', is_flag=True,
              help="First row is a header; summary rows get a label column")
def agg(args, field_sep, header):
    """
    Aggregate rows and columns: ``[FILE] [R_AGGS] [C_AGGS]``, or the same without FILE on stdin.

    Each is a comma-separated list of ``OP`` or ``OP|all`` or ``OP|START..END`` with OP one of
    ``+ - * /`` or ``m``/``mean``; ``0`` turns an axis off. Default: ``+|all`` on both axes.

    Example::

        ds . agg data.csv '+|all,mean|2..4' 0
        cat data.txt | ds . agg 0 'mean|all' --header
    """
    from scripts.agg import Agg, AggError
    from scripts.field_rows import read_rows
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=(3, "Warning: ignoring {extra} extra argument(s) after FILE, R_AGGS and C_AGGS."),
        field_separator=field_sep,
    )
    positional = list(ctx.args[1 if ctx.resolved_path else 0:])
    r_aggs = positional[0] if len(positional) > 0 and positional[0] else None
    c_aggs = positional[1] if len(positional) > 1 and positional[1] else None
    try:
        aggregator = Agg(r_aggs, c_aggs, header=header)
    except AggError as e:
        raise click.ClickException(str(e)) from e
    data_file = ctx.to_data_file()
    if data_file.n_rows == 0:
        return
    if field_sep is None:
        try:
            field_sep = data_file.get_field_separator()
        except Exception as e:
            raise click.ClickException(
                f"could not infer the field separator ({e}); pass --field-sep") from e
    ofs = field_sep if field_sep and field_sep.strip() else " "
    for row in aggregator.run(read_rows(data_file.file_path, field_sep)):
        click.echo(ofs.join(row))

@cli.command()
@click.argument("args", nargs=-1, required=False)
def asgn(args):
    """
    Print ``lineno:line`` for lines containing an assignment (``name = value``).

    Optional ``FILE`` or stdin.

    Example:  ds . asgn config.sh
    """
    from scripts.assignments import assignment_lines
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
    )
    if args and not ctx.resolved_path and not ctx.stdin_text:
        raise click.ClickException(f"not a file: {args[0]}")
    data_file = ctx.to_data_file()
    with open(data_file.file_path, encoding="utf-8", errors="replace") as f:
        for line in assignment_lines(f):
            click.echo(line)

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

@cli.command(name="cd", aliases=["cd"])
@click.argument("search", required=False, default=None)
def cd(search):
    """
    Resolve a directory for shell ``cd`` usage.

    Prints the selected directory path; use as:
    ``cd "$(ds . cd <search>)"``.
    """
    from scripts.cd_command import cd_cmd
    cd_cmd(search)

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
@click.argument("args", nargs=-1, required=False)
@click.option('--field-sep', '-s', default=None)
@click.option('--header', '-h', default=False)
def index(args, field_sep, header):
    """
    Print lines indexed: optional ``FILE`` or stdin (relative paths resolved).
    """
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
        field_separator=field_sep,
    )
    data_file = ctx.to_data_file()
    data_file.print_indexed(header=header)

@cli.command(aliases=["t"])
@click.argument("args", nargs=-1, required=False)
@click.option('--field-sep', '-s', default=None)
@click.option('--ofs', default=None)
def transpose(args, field_sep, ofs):
    """
    Transpose lines: optional ``FILE`` or stdin (relative paths resolved).
    """
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
        field_separator=field_sep,
        output_field_separator=ofs,
    )
    data_file = ctx.to_data_file()
    data_file.print_transposed()


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
@click.argument("args", nargs=-1, required=False)
@click.option('--field-sep', '-s', default=None)
@click.option('--ofs', default=None)
@click.option('--fields', '-f', default="0")
@click.option('--min', '-m', default=1)
@click.option('--only-vals', '-v', is_flag=True)
def field_counts(args, field_sep, ofs, fields="0", min=1, only_vals=False):
    """
    Count fields in data: optional ``FILE`` or stdin (relative paths resolved).
    """
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
        field_separator=field_sep,
        output_field_separator=ofs,
    )
    data_file = ctx.to_data_file()
    FieldsCounter(data_file, fields=fields, min=min, only_vals=only_vals).run()


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


@cli.command(name="embrace")
@click.argument("args", nargs=-1)
def embrace(args):
    """
    Wrap a string or each stdin line with delimiters (default ``{`` … ``}``).

    With piped stdin: optional LEFT and RIGHT (``echo x | ds . embrace`` → ``{x}``).

    With a TTY: ``STR [LEFT] [RIGHT]`` (``ds . embrace test`` → ``{test}``).
    """
    from scripts.simple_commands import embrace_cmd
    ctx = CliArgContext.from_click(tuple(args), path_rule=PathCandidatePredicate.NONE)
    embrace_cmd(ctx)


@cli.command(name="cp")
def cp_clipboard():
    """
    Copy standard input to the system clipboard (UTF-8).

    Example: ``echo hello | ds . cp``
    """
    from scripts.clipboard_copy import copy_stdin_to_clipboard
    copy_stdin_to_clipboard()


@cli.command(name="decap")
@click.argument("args", nargs=-1)
def decap(args):
    """
    Remove the first *n* lines from a file or stdin (default *n* is 1).

    ``FILE [n_lines]`` or ``… | ds . decap [n_lines]`` (``n_lines`` = number of lines to drop).
    """
    from scripts.simple_commands import decap_stdout, parse_decap
    ctx = CliArgContext.from_click(
        tuple(args),
    )
    df, n_remove = parse_decap(ctx)
    decap_stdout(df, n_remove)


@cli.command(name="dostounix")
@click.argument("files", nargs=-1, required=False)
def dostounix(files):
    """
    Remove DOS CR line endings in place for file(s), or from stdin to stdout.
    """
    from scripts.simple_commands import dostounix_cmd
    stdin_data = None if sys.stdin.isatty() else sys.stdin.read()
    dostounix_cmd(tuple(files), stdin_data=stdin_data)


@cli.command(name="newfs")
@click.argument("args", nargs=-1, required=False)
def newfs(args):
    """
    Convert field separators (for example TSV to CSV).

    Syntax: ``[FILE] [newfs=,]``; with piped input, first arg is NEWFS.
    """
    from scripts.simple_commands import newfs_cmd
    stdin_data = None if sys.stdin.isatty() else sys.stdin.read()
    newfs_cmd(tuple(args), stdin_data=stdin_data)


@cli.command(name="path_elements")
@click.argument("filepath")
def path_elements(filepath):
    """
    Print directory (with trailing ``/``), basename without final extension, and extension.

    Tab-separated, no newline; same idea as ``ds:path_elements`` for ``read``-style parsing.

    Example:  ``ds . path_elements ./foo/bar.txt`` → ``./foo/\tbar\t.txt``
    """
    from scripts.simple_commands import path_elements_parts

    dir_out, stem, suffix = path_elements_parts(os.path.normpath(filepath))
    click.echo(f"{dir_out}\t{stem}\t{suffix}", nl=False)


@cli.command(name="filename_str")
@click.argument("filepath")
@click.argument("add")
@click.argument("position", required=False, default="append")
@click.argument("abs_path", required=False, default="t")
def filename_str(filepath, add, position, abs_path):
    """
    Add text to a filename while preserving extension and optional path.
    """
    from scripts.simple_commands import filename_str_cmd

    click.echo(filename_str_cmd(filepath, add, position=position, abs_path=abs_path), nl=False)


@cli.command(name="todo")
@click.argument("paths", nargs=-1, required=False)
def todo(paths):
    """
    Find TODO / FIXME / XXX markers under paths (default: current directory).

    Uses ``ripgrep`` when available (see :mod:`scripts.tool_availability`); otherwise scans in Python.
    """
    from scripts.simple_commands import run_todo
    code = run_todo(tuple(paths))
    if code:
        sys.exit(code)


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


@cli.command(name="test")
@click.argument("regex")
@click.argument("value_or_file", required=False, default="")
@click.argument("test_file", required=False, default="")
def test_cmd(regex, value_or_file, test_file):
    """
    Quiet regex test against stdin, a string, or optionally a file body.
    """
    stdin_data = None if sys.stdin.isatty() else sys.stdin.read()
    ok = regex_test_match(
        regex,
        stdin_text=stdin_data,
        value_or_file=value_or_file,
        test_file_flag=test_file,
    )
    if not ok:
        sys.exit(1)


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
@click.argument("args", nargs=-1, required=False)
@click.option("--key", "-k", "key", type=int, default=None, help="Key field index (1-based) for both files")
@click.option("--key1", type=int, default=None, help="Key field index for the first file (1-based)")
@click.option("--key2", type=int, default=None, help="Key field index for the second file (1-based)")
@click.option("--fs", "-s", "fs", default=None, help="Field separator for both files")
@click.option("--verbose", is_flag=True, help="When matches exist, print a short banner (two extra lines before rows)")
def matches(args, key, key1, key2, fs, verbose):
    """
    Lines from the second file whose key appears in the first file (two FILE paths, or one FILE
    with the second dataset on stdin).

    Examples::

        ds . matches a.csv b.csv -k 1
        cat b.csv | ds . matches a.csv -k 1
    """
    from scripts.matches import run_matches
    run_matches(tuple(args), key=key, key1=key1, key2=key2, fs=fs, verbose=verbose)


@cli.command(name="comps")
@click.argument("args", nargs=-1, required=False)
@click.option("--key", "-k", "key", type=int, default=None, help="Key field index (1-based) for both files")
@click.option("--key1", type=int, default=None, help="Key field index for the first file (1-based)")
@click.option("--key2", type=int, default=None, help="Key field index for the second file (1-based)")
@click.option("--fs", "-s", "fs", default=None, help="Field separator for both files")
@click.option("--verbose", is_flag=True, help="When complements exist, print a short banner (two extra lines before rows)")
def comps(args, key, key1, key2, fs, verbose):
    """
    Lines from the second file whose key does not appear in the first file (two FILE paths, or one
    FILE with the second dataset on stdin).
    """
    from scripts.matches import run_comps
    code = run_comps(tuple(args), key=key, key1=key1, key2=key2, fs=fs, verbose=verbose)
    if code:
        sys.exit(code)


@cli.command(name="field_replace")
@click.argument("args", nargs=-1, required=False)
@click.option("--key", "-k", "key", type=int, default=1, show_default=True, help="1-based field index to replace")
@click.option("--pattern", "-p", "pattern", default="", show_default=True, help="Regex pattern the target field must match")
def field_replace(args, key, pattern):
    """
    Overwrite a field value when it matches a regex pattern.

    Syntax: ``[FILE] replacement_expr [key=1] [pattern='']``.
    """
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        no_arg_exception_text=(
            "field_replace requires replacement_expr (and optional FILE, key, pattern)."
        ),
        extra_arg_warn=(
            2,
            "Warning: ignoring {extra} extra argument(s) after [FILE] replacement_expr.",
        ),
    )
    replacement_expr = ctx.shifted_arg(0)
    validate_positive_key_field("--key", key)
    df = ctx.to_data_file()
    try:
        rendered = df.field_replace(replacement_expr, key=key, pattern=pattern)
        click.echo(rendered, nl=False)
    finally:
        df.cleanup_temp_file()


@cli.command(name="power")
@click.argument("args", nargs=-1, required=False)
@click.option('--min', '-m', 'min_count', default=0, help="Minimum occurrence count")
@click.option('--return-fields', '-r', is_flag=True, help="Return field proportions instead of counts")
@click.option('--invert', '-i', is_flag=True, help="Invert the min filter")
@click.option('--choose', '-c', type=int, default=None, help="Restrict combination size")
def power(args, min_count, return_fields, invert, choose):
    """
    Combinatorial frequency analysis of data field values.

    Optional ``FILE`` or stdin (relative paths resolved).

    Example:  ds . power data.txt --min 2 --choose 2
    """
    from scripts.power import DataAnalyzer
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
    )
    data_file = ctx.to_data_file()
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
@click.argument("args", nargs=-1)
def unicode_cmd(args):
    """
    Show ``\\U`` codepoint escapes or UTF-8 percent-encoded bytes.

    With no arguments, reads stdin (default mode: codepoint).

    One argument: if it is ``codepoint``, ``hex``, or ``octet``, reads stdin in that mode;
    otherwise treats the argument as the input string (codepoint mode).

    Two arguments: ``TEXT`` then ``codepoint`` | ``hex`` | ``octet``.

    Examples::

        ds . unicode "cats😼😻"
        echo "cats😼😻" | ds . unicode
        ds . unicode "cats😼😻" hex
    """
    from scripts.unicode import run_unicode
    ctx = CliArgContext.from_click(tuple(args), path_rule=PathCandidatePredicate.NONE)
    run_unicode(ctx)


# ---------------------------------------------------------------------------
# Graph / visualization commands
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("args", nargs=-1, required=False)
@click.option('--print-bases', '-p', is_flag=True, help="Include base nodes in output")
def graph(args, print_bases):
    """
    Extract graph relationships from DAG base data: optional ``FILE`` or stdin.

    Input: lines of ``child parent`` pairs (whitespace-separated); single-token lines mark bases.

    Examples::

        cat edges.txt | ds . graph --print-bases
        ds . graph edges.txt -p
    """
    from scripts.graph import run_graph
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
    )
    data_file = ctx.to_data_file()
    code = run_graph(data_file, print_bases=print_bases, echo=click.echo)
    if code:
        sys.exit(code)


@cli.command()
@click.argument("args", nargs=-1, required=False)
@click.option('--stag-size', '-s', default=5, help="Number of spaces to indent per field")
@click.option('--field-sep', '-F', default=None, help="Input field separator override (regex-like not supported)")
@click.option('--tty-size', type=int, default=None, help="Terminal width for wrapping")
@click.option('--style', type=click.Choice(["simple", "compact"]), default="simple")
@click.option('--wrap', type=click.Choice(["smart", "char"]), default="smart")
@click.option('--numbers', is_flag=True, help="Prefix each record with its line number")
@click.option('--align', type=click.Choice(["l", "r", "c"]), default="l")
@click.option('--max-width', type=int, default=0, help="Maximum width per field before wrapping")
@click.option('--ellipsis', is_flag=True, help="Use ellipsis for very long fields")
@click.option('--wrap-char', default="↪", help="Continuation marker for wrapped lines")
def stagger(args, stag_size, field_sep, tty_size, style, wrap, numbers, align, max_width, ellipsis, wrap_char):
    """
    Print tabular data in staggered rows: optional ``FILE`` or stdin.

    Examples::

        ds . stagger data.txt --stag-size 4
        cat data.txt | ds . stagger -s 4
    """
    from scripts.stagger import print_staggered
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
        field_separator=field_sep,
    )
    data_file = ctx.to_data_file()
    print_staggered(
        data_file,
        stag_size=stag_size,
        tty_size=tty_size,
        style=style,
        wrap=wrap,
        numbers=numbers,
        align=align,
        max_width=max_width,
        ellipsis=ellipsis,
        wrap_char=wrap_char,
    )


@cli.command()
@click.argument("args", nargs=-1, required=False)
@click.option('--y-keys', '-y', required=True, help="Comma-separated y-axis key fields")
@click.option('--x-keys', '-x', required=True, help="Comma-separated x-axis key fields")
@click.option('--z-keys', '-z', default=None, help="Comma-separated z-axis value fields")
@click.option('--agg-type', '-a', default=None, type=click.Choice(['count', 'sum', 'product', 'mean']),
              help="Aggregation type")
@click.option('--gen-keys', '-g', is_flag=True,
              help="Treat all keys as header-name patterns, even numeric ones")
def pivot(args, y_keys, x_keys, z_keys, agg_type, gen_keys):
    """
    Pivot tabular data: optional ``FILE`` or stdin (relative paths resolved).

    Example::

        ds . pivot data.csv -y 1 -x 2
        cat data.txt | ds . pivot -y 2 -x 1
    """
    from scripts.pivot import Pivot, load_pivot_rows

    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
    )
    data_file = ctx.to_data_file()
    try:
        field_sep = data_file.get_field_separator()
    except Exception:
        field_sep = None
    p = Pivot(data_file.file_path, y_keys, x_keys, z_keys=z_keys, agg_type=agg_type,
              gen_keys=gen_keys)
    p.data = load_pivot_rows(data_file.file_path, field_sep)
    p.pivot()
    p.print_pivot()


@cli.command()
@click.argument("args", nargs=-1, required=False)
@click.option('--field-sep', '-s', default=None, help="Override the inferred field separator")
@click.option('--header', '-h', 'header', is_flag=True,
              help="First row is a header (default: detected when it has no numbers)")
@click.option('--fields', '-f', default=None, help="Comma-separated 1-based fields to chart")
def hist(args, field_sep, header, fields):
    """
    Print a histogram per numeric field: ``[FILE] [N_BINS=10] [BAR_LEN=15]``, or stdin.

    Example::

        ds . hist data.csv 5
        cat data.txt | ds . hist --fields 2,3
    """
    from scripts.field_rows import read_rows
    from scripts.hist import Histogram
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=(3, "Warning: ignoring {extra} extra argument(s) after FILE, N_BINS and BAR_LEN."),
        field_separator=field_sep,
    )
    numbers = [parse_non_negative_int_arg(a, descriptor=name)
               for a, name in zip(ctx.args[1 if ctx.resolved_path else 0:], ("N_BINS", "BAR_LEN"))]
    n_bins = numbers[0] if len(numbers) > 0 and numbers[0] else 10
    bar_len = numbers[1] if len(numbers) > 1 and numbers[1] else 15
    try:
        field_list = [int(f) for f in fields.split(",") if f.strip()] if fields else None
    except ValueError as e:
        raise click.ClickException("--fields must be comma-separated field numbers") from e
    data_file = ctx.to_data_file()
    if data_file.n_rows == 0:
        return
    if field_sep is None:
        try:
            field_sep = data_file.get_field_separator()
        except Exception as e:
            raise click.ClickException(
                f"could not infer the field separator ({e}); pass --field-sep") from e
    histogram = Histogram(n_bins=n_bins, max_bar_len=bar_len, header=header, fields=field_list)
    histogram.process_rows(read_rows(data_file.file_path, field_sep))
    for line in histogram.render():
        click.echo(line)


# ---------------------------------------------------------------------------
# Stub commands — incomplete ports, hidden from `ds commands` by default
# ---------------------------------------------------------------------------

@cli.command(name="diff_fields", aliases=["df"])
@click.argument("args", nargs=-1, required=True)
@click.option('--exclude-fields', '-e', default=None, help="Comma-separated 1-based fields passed through unchanged")
@click.option('--header', '-h', is_flag=True, help="First row is a header")
@click.option('--precision', '-p', type=int, default=None, help="Decimal places for results")
@click.option('--diff-list', type=click.Choice(["on", "only"]), default=None,
              help="Also list non-trivial differences sorted by size (only: just the list)")
@click.option('--diff-list-sort', type=click.Choice(["d", "a", "off"]), default="d", show_default=True)
@click.option('--field-sep', '-s', default=None, help="Field separator for both files")
def diff_fields(args, exclude_fields, header, precision, diff_list, diff_list_sort, field_sep):
    """
    Elementwise diff of two datasets: ``FILE1 FILE2 [OP=-] [EXCLUDE_FIELDS]``.

    With the second dataset on stdin: ``FILE1 [OP] [EXCLUDE_FIELDS]``. OP is one of
    ``- + * / %``, ``b`` (binary), ``m`` (MAD), ``r`` (RMSD) or ``s`` (stats).

    Example::

        ds . diff_fields a.csv b.csv - 1 --header
        cat b.csv | ds . df a.csv % --diff-list on
    """
    from scripts.diff_fields import OPS, DiffFields, DiffFieldsError
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND,
        field_separator=field_sep,
    )
    resolution = ctx.resolve_join_style_paths(check_same_file_pair=False)
    resolution.require_exactly_two_inputs(
        message="diff_fields expects two FILE paths, or one FILE with the second input on stdin.")
    remaining = list(resolution.remaining_args)
    op = "-"
    if remaining and remaining[0].lower() in OPS:
        op = remaining.pop(0)
    if remaining and exclude_fields is None:
        exclude_fields = remaining.pop(0)
    if remaining:
        click.echo(click.style(
            f"Warning: ignoring {len(remaining)} extra argument(s) after OP and EXCLUDE_FIELDS.",
            fg="yellow"), err=True)
    if resolution.stdin_replaces_second_file:
        labels = (args[0], "PIPEDATA")
    else:
        labels = (args[0], args[1]) if args[0] != args[1] else ("FILE1", "FILE2")

    df1, df2 = resolution.materialize_data_files(stdin_text=ctx.stdin_text, field_separator=field_sep)
    try:
        separators = []
        for df in (df1, df2):
            if field_sep is not None or df.n_rows == 0:
                separators.append(field_sep)
                continue
            try:
                separators.append(df.get_field_separator())
            except Exception as e:
                raise click.ClickException(
                    f"could not infer the field separator of {df.name} ({e}); pass --field-sep") from e
        differ = DiffFields(op, exclude_fields, header=header, precision=precision,
                            diff_list=diff_list, diff_list_sort=diff_list_sort,
                            left_label=labels[0], right_label=labels[1],
                            field_separator=separators[0], right_field_separator=separators[1])
        for line in differ.run(df1.read_raw_lines(), df2.read_raw_lines()):
            click.echo(line)
    except DiffFieldsError as e:
        raise click.ClickException(str(e)) from e
    finally:
        resolution.cleanup_stdin_backed_data_files()


@cli.command(name="fit")
@click.argument("args", nargs=-1, required=False)
@click.option('--field-sep', '-s', default=None, help="Override the inferred field separator")
@click.option('--buffer', '-b', type=int, default=None, help="Characters between columns (default 2)")
@click.option('--buffer-char', default=None, help="First character of each column gap (default space)")
def fit(args, field_sep, buffer, buffer_char):
    """
    Fit fielded data in columns with dynamic width: optional ``FILE`` or stdin.

    Number columns are right-aligned, text columns left-aligned.

    Example::

        ds . fit data.csv
        cat data.txt | ds . fit --buffer-char '|'
    """
    from scripts.field_rows import read_rows
    from scripts.fit_columns import FitColumns

    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
        field_separator=field_sep,
    )
    data_file = ctx.to_data_file()
    if field_sep is None:
        try:
            field_sep = data_file.get_field_separator()
        except Exception as e:
            raise click.ClickException(str(e)) from e
    fitter = FitColumns(field_separator=field_sep, buffer=buffer, buffer_char=buffer_char)
    for line in fitter.fit_rows(read_rows(data_file.file_path, field_sep)):
        click.echo(line)


@cli.command(name="reo")
@click.argument("args", nargs=-1, required=False)
@click.option('--idx', is_flag=True, help="Prefix output with source row/column index numbers")
@click.option('--uniq', is_flag=True, help="Constrain the result to unique indices")
@click.option('--cased', is_flag=True, help="Match patterns case-sensitively")
@click.option('--field-sep', '-s', default=None, help="Override the inferred field separator")
def reo(args, idx, uniq, cased, field_sep):
    """
    Reorder, repeat, or slice data by rows and columns.

    ``[FILE] [ROWS] [COLS]`` or ``[ROWS] [COLS]`` with data on stdin. Each order argument is
    a comma-separated list of indices, ranges (``2..5``), ``rev``, ``others``, expressions
    (``NR%2``), searches (``~pat``), frames (``[hdr~val``) or anchors (``start##end``).
    Pass ``off`` as COLS to leave field separation alone.

    Example::

        ds . reo data.csv 1,3..5 rev
        cat data.txt | ds . reo '~error' '[level'
    """
    from scripts.reorder import Reorder, ReorderError

    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=(
            3,
            "Warning: ignoring {extra} extra argument(s) after FILE, ROWS and COLS.",
        ),
    )
    shift = 1 if ctx.resolved_path else 0
    positional = ctx.args[shift:]
    rows_arg = positional[0] if len(positional) > 0 else None
    cols_arg = positional[1] if len(positional) > 1 else None

    data_file = ctx.to_data_file()
    if field_sep is None:
        try:
            field_sep = data_file.get_field_separator()
        except Exception:
            field_sep = None

    cols_off = (cols_arg or "").strip().lower() == "off"
    try:
        reorder = Reorder(
            rows_arg, None if cols_off else cols_arg,
            field_separator=field_sep, ofs=field_sep or " ",
            uniq=uniq, idx=idx, cols_off=cols_off, cased=cased,
        )
        for line in reorder.transform_file(data_file.file_path):
            click.echo(line)
    except ReorderError as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="sortm", aliases=["s"])
@click.argument("args", nargs=-1, required=False)
@click.option('--field-sep', '-s', default=None, help="Override the inferred field separator")
@click.option('--header', '-h', 'header', is_flag=True, help="Keep the first row first")
@click.option('--deterministic', '-d', is_flag=True,
              help="Break ties on the remaining fields (default when KEYS is omitted)")
def sortm(args, field_sep, header, deterministic):
    """
    Sort lines by fields: ``[FILE] [KEYS] [ORDER] [TYPE]``, or the same without FILE on stdin.

    KEYS: comma-separated field indices or ``NF`` (default 1); any other value makes all
    keys header patterns. ORDER: ``a`` or ``d``. TYPE: ``n`` numeric, ``i`` case-insensitive,
    or both. Lines with equal keys keep their input order.

    Example::

        ds . sortm data.csv 2,3 d n
        cat data.txt | ds . sortm 1 a i
    """
    from scripts.fields_qsort import SortKeyError, SortM
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=(4, "Warning: ignoring {extra} extra argument(s) after FILE, KEYS, ORDER and TYPE."),
        field_separator=field_sep,
    )
    positional = list(ctx.args[1 if ctx.resolved_path else 0:]) + ["", "", ""]
    keys, order, sort_type = positional[:3]
    if not keys:
        keys, deterministic = "1", True
    data_file = ctx.to_data_file()
    lines = data_file.read_raw_lines()
    if not any(line.strip() for line in lines):
        return
    if field_sep is None:
        try:
            field_sep = data_file.get_field_separator()
        except Exception as e:
            raise click.ClickException(
                f"could not infer the field separator ({e}); pass --field-sep") from e
    try:
        sorter = SortM(keys, order or "a", sort_type, field_separator=field_sep,
                       header=header, deterministic=deterministic)
        for line in sorter.sort_lines(lines):
            click.echo(line)
    except SortKeyError as e:
        raise click.ClickException(str(e)) from e


@cli.command(name="subsep")
@click.argument("args", nargs=-1, required=True)
@click.option('--nomatch-handler', '-n', default=" ", help="Fallback split pattern for non-matching lines")
@click.option('--apply-to-fields', default=None, help="Comma-separated field indices to subseparate")
@click.option('--regex', is_flag=True, help="Treat the pattern as a regex rather than a literal")
@click.option('--escape', is_flag=True, help="Escape the pattern for literal matching")
@click.option('--retain-pattern', is_flag=True, help="Keep the subseparator between output fields")
def subsep(args, nomatch_handler, apply_to_fields, regex, escape, retain_pattern):
    """
    Extend fields by a common sub-separator.

    ``FILE SUBSEP_PATTERN`` or ``SUBSEP_PATTERN`` with data on stdin (relative paths resolved).

    Example:  ds . subsep data.txt ":"
    """
    from scripts.subseparator import SubseparatorFinder
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        tested_first_arg_file_pair_rules=True,
        extra_arg_warn=(
            2,
            "Warning: ignoring {extra} extra argument(s) after FILE and SUBSEP_PATTERN.",
        ),
    )
    subsep_pattern = ctx.shifted_arg(0)
    df = ctx.to_data_file()
    try:
        field_sep = df.get_field_separator()
    except Exception:
        field_sep = None
    finder = SubseparatorFinder(
        subsep_pattern=subsep_pattern,
        nomatch_handler=nomatch_handler,
        apply_to_fields=apply_to_fields,
        regex=regex,
        escape=escape,
        retain_pattern=retain_pattern,
        OFS=field_sep or " ",
    )
    for line in finder.transform_file(df.file_path, field_sep):
        click.echo(line)


@cli.command(name="inferh")
@click.argument("args", nargs=-1, required=False)
@click.option('--field-sep', '-s', default=None, help="Override the inferred field separator")
@click.option('--max-rows', type=int, default=100, show_default=True, help="Rows to analyze")
@click.option('--verbose', '-v', is_flag=True, help="Print the header score")
def inferh(args, field_sep, max_rows, verbose):
    """
    Infer whether the first row is a header: optional ``FILE`` or stdin.

    Exits 0 if a header row is detected, 1 otherwise (also for fewer than two rows).

    Example:  ds . inferh data.csv && echo has header
    """
    from scripts.infer_headers import header_score
    if max_rows < 2:
        raise click.ClickException("--max-rows must be at least 2")
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
        field_separator=field_sep,
    )
    data_file = ctx.to_data_file()
    lines = data_file.read_raw_lines()
    score = None
    if len(lines) >= 2:
        if field_sep is None:
            try:
                field_sep = data_file.get_field_separator()
            except Exception as e:
                raise click.ClickException(
                    f"could not infer the field separator ({e}); pass --field-sep") from e
        score = header_score(lines, field_sep, max_rows=max_rows)
    if verbose:
        click.echo(f"header score: {score}")
    if score is None or score <= 0:
        sys.exit(1)


@cli.command(name="cardinality")
@click.argument("args", nargs=-1, required=False)
def cardinality(args):
    """
    Calculate cardinality (distinct values) per field.

    Optional ``FILE`` or stdin (relative paths resolved).

    Example:  ds . cardinality data.txt
    """
    from scripts.simple_commands import cardinality_cmd
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
    )
    cardinality_cmd(ctx)


@cli.command(name="prod")
@click.argument('files', nargs=-1, required=False)
def prod(files):
    """
    Cartesian product of the lines of several inputs, joined by a space.

    Each FILE is one set of lines; piped stdin is used as the first set.

    Example::

        ds . prod set_a.txt set_b.txt
        cat set_a.txt | ds . prod set_b.txt
    """
    from scripts.product import product_main
    stdin_text = None if sys.stdin.isatty() else sys.stdin.read()
    paths = []
    for f in files:
        path = Utils.resolve_relative_path(f)
        if not Utils.isfile_with_retry(path):
            raise click.ClickException(f"not a file: {f}")
        paths.append(path)
    if not paths and not stdin_text:
        raise click.ClickException("prod requires at least one FILE or piped stdin")
    product_main(paths, stdin_text=stdin_text, echo=click.echo)


@cli.command(name="shape")
@click.argument("args", nargs=-1, required=False)
@click.option('--field-sep', '-s', default=None, help="Override the inferred field separator")
@click.option('--header', '-h', 'header', is_flag=True, help="First row is a header (names the fields)")
@click.option('--tty-size', type=int, default=None, help="Output width (default: terminal width)")
def shape(args, field_sep, header, tty_size):
    """
    Distribution of line length or pattern matches: ``[FILE] [MEASURES] [FIELDS] [CHART_SIZE]``.

    MEASURES: comma-separated regexes (case-insensitive), default line length. FIELDS:
    comma-separated field indices, default ``0`` (whole line). CHART_SIZE: number of chart
    rows (default 15); ``0`` prints the stats only. Without FILE, data is read from stdin.

    Example::

        ds . shape data.csv 'error,warn' 0 20
        cat app.log | ds . shape timeout
    """
    import shutil
    from scripts.shape import Shape
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=(4, "Warning: ignoring {extra} extra argument(s) after FILE, MEASURES, FIELDS and CHART_SIZE."),
        field_separator=field_sep,
    )
    positional = list(ctx.args[1 if ctx.resolved_path else 0:]) + ["", "", ""]
    measures, fields, chart_size = positional[:3]
    data_file = ctx.to_data_file()
    lines = data_file.read_raw_lines()
    n_lines = sum(1 for line in lines if line.endswith("\n"))
    if not n_lines:
        sys.exit(1)
    simple = False
    print_lines = 15
    if chart_size:
        if re.fullmatch(r"-?\d+", chart_size):
            simple = int(chart_size) == 0
            print_lines = int(chart_size) or 15
        else:
            simple = True
    span = n_lines // print_lines if print_lines > 0 else 0
    if fields and fields != "0" and field_sep is None:
        try:
            field_sep = data_file.get_field_separator()
        except Exception as e:
            raise click.ClickException(
                f"could not infer the field separator ({e}); pass --field-sep") from e
    if tty_size is None:
        tty_size = shutil.get_terminal_size((100, 24)).columns
    renderer = Shape(measures or None, fields or None, span=span or 15, tty_size=tty_size,
                     field_separator=field_sep, header=header, simple=simple)
    for line in renderer.render(lines):
        click.echo(line.rstrip())


@cli.command(name="field_uniques", aliases=["u"])
@click.argument("args", nargs=-1, required=False)
@click.option("-f", "--fields", "fields_spec", default="a", show_default=True, help="Which fields to use (e.g. comma-separated 1-based indices, or 'a' for whole row).")
@click.option("-m", "--min-count", type=int, default=1, show_default=True, help="Minimum occurrence count before a value is printed.")
@click.option("-o", "--order", "order", default="a", show_default=True, help="Output sort: ascending (a) or descending (d / r).")
def field_uniques(args, fields_spec, min_count, order):
    """
    Get unique values from specified fields: optional ``FILE`` or stdin.

    Options set field selection, threshold, and sort (defaults match the prior port: ``a``, ``1``, ``a``).

    Examples::

        cat data.txt | ds . field_uniques
        ds . field_uniques data.txt -f 1 -m 3 -o a
    """
    from scripts.field_uniques import FieldUniques

    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
    )
    data_file = ctx.to_data_file()
    FieldUniques(data_file, fields_spec=fields_spec, min_user=min_count, order=order).run()


@cli.command(name="enti")
@click.argument("args", nargs=-1, required=False)
@click.option('--sep', '-s', default=" ", show_default=True,
              help="Separator: a space splits on whitespace, one other character literally, longer is a regex")
@click.option('--min', '-m', 'min_count', type=int, default=1, show_default=True,
              help="Minimum count to display")
@click.option('--order', '-o', type=click.Choice(["a", "d", "asc", "desc"]), default="a",
              show_default=True, help="Sort by count ascending (a) or descending (d)")
def enti(args, sep, min_count, order):
    """
    Count text entities separated by a pattern: optional ``FILE`` or stdin.

    Prints ``count entity`` per entity seen at least ``--min`` times, sorted by count.

    Example:  ds . enti data.txt --sep "," --min 2
    """
    from scripts.separated_entities import TextEntities
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.TESTED_FIRST_ARG,
        extra_arg_warn=EXTRA_ARG_WARN_FIRST_FILE_ONLY,
    )
    data_file = ctx.to_data_file()
    te = TextEntities(min_count=min_count, separator=sep, descending=order.startswith("d"))
    te.process_file(data_file.file_path)
    for line in te.entity_lines():
        click.echo(line)


@cli.command(name="diff")
@click.argument("args", nargs=-1, required=True)
@click.option('--suppress-common', '-s', is_flag=True, help="Suppress common lines")
@click.option('--no-color', is_flag=True, help="Disable colorized output")
@click.option('--width', '-w', type=int, default=None, help="Output width (default: terminal width)")
def diff_cmd(args, suppress_common, no_color, width):
    """
    Side-by-side diff of two files or strings, colorized on a terminal.

    ``FILE1|STR1 FILE2|STR2``, or ``FILE2|STR2`` with the first input piped on stdin.
    Changes in the amount of whitespace are ignored.

    Example::

        ds . diff old.txt new.txt
        ds . diff 'a\\nb' 'a\\nc'
    """
    import shutil
    from scripts.diff_color import literal_to_lines, side_by_side, text_to_lines

    def lines_of(value):
        path = Utils.resolve_relative_path(value)
        if Utils.isfile_with_retry(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                return text_to_lines(f.read())
        return literal_to_lines(value)

    stdin_text = None if sys.stdin.isatty() else sys.stdin.read()
    if len(args) == 1 and stdin_text:
        left, right = text_to_lines(stdin_text), lines_of(args[0])
    elif len(args) == 2:
        left, right = lines_of(args[0]), lines_of(args[1])
    else:
        raise click.ClickException("diff takes two FILE|STR inputs, or one with the other piped on stdin")

    if width is None:
        width = shutil.get_terminal_size((100, 24)).columns
    colour = not no_color and sys.stdout.isatty()
    for line in side_by_side(left, right, width, suppress_common=suppress_common, colour=colour):
        click.echo(line)


@cli.command(name="inferk")
@click.argument("args", nargs=-1, required=True)
@click.option('--fs1', default=None, help="Field separator of the first file")
@click.option('--fs2', default=None, help="Field separator of the second file")
@click.option('--no-header', is_flag=True, help="Files have no header row")
@click.option('--max-rows', type=int, default=50, show_default=True, help="Data rows sampled per file")
def inferk(args, fs1, fs2, no_header, max_rows):
    """
    Infer join fields of two data files: ``FILE1 FILE2``, or ``FILE1`` with the second on stdin.

    Prints ``k`` when both join on the same field, else ``k1 k2``. A header name shared by
    both files wins; otherwise the columns with the most overlapping values.

    Example:  ds . inferk users.csv orders.csv
    """
    from scripts.infer_join_fields import InferJoinError, infer_join_fields
    ctx = CliArgContext.from_click(
        tuple(args),
        path_rule=PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND,
    )
    resolution = ctx.resolve_join_style_paths(check_same_file_pair=False)
    resolution.require_exactly_two_inputs(
        message="inferk expects two FILE paths, or one FILE with the second input on stdin.")
    df1, df2 = resolution.materialize_data_files(stdin_text=ctx.stdin_text)
    try:
        separators = []
        for df, given in ((df1, fs1), (df2, fs2)):
            if given is not None or df.n_rows == 0:
                separators.append(given)
                continue
            try:
                separators.append(df.get_field_separator())
            except Exception as e:
                raise click.ClickException(
                    f"could not infer the field separator of {df.name} ({e}); pass --fs1/--fs2") from e
        click.echo(infer_join_fields(df1.read_raw_lines(), df2.read_raw_lines(), *separators,
                                     header=not no_header, max_rows=max_rows))
    except InferJoinError as e:
        raise click.ClickException(str(e)) from e
    finally:
        resolution.cleanup_stdin_backed_data_files()


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


@cli.command(name="version")
def version_cmd():
    """
    Show the ds version, and for a standalone build its build details.
    """
    from scripts.build_info import describe
    click.echo(describe())


def main():
    try:
        cli()
    finally:
        DataFile.cleanup()
    

if __name__ == '__main__':
    cli()
