import os
import re
import subprocess
import webbrowser
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple
from urllib.parse import quote_plus

import click

from scripts.cli_arg_parse_utils import (
    ArgCheck,
    CliArgContext,
    apply_arg_predicates,
    parse_non_negative_int_arg,
)
from scripts.DataFile import DataFile

# ``ds:todo`` / ``ds . todo`` (same regex as the original bash helper).
TODO_SEARCH_PATTERN = r"(TODO|FIXME|(^|[^X])XXX)( |:|\-)"


def run_todo(
    paths: Tuple[str, ...],
    *,
    echo: Optional[Callable[..., None]] = None,
) -> int:
    """
    Search paths for TODO / FIXME / XXX markers; delegates to :func:`scripts.tool_based_search.run_search`.
    """
    from scripts.tool_based_search import run_search

    return run_search(paths, TODO_SEARCH_PATTERN, echo=echo)


def path_elements_cmd(filepath: str) -> None:
    """
    Split a path into directory (with trailing ``/``), basename without final suffix, and suffix.

    Matches ``ds:path_elements``: tab-separated fields, no trailing newline (POSIX-style
    directory separator in the first field).
    """
    if not filepath or not filepath.strip():
        raise click.ClickException("path_elements requires a non-empty FILEPATH.")
    p = Path(filepath)
    parent = p.parent
    dir_str = parent.as_posix() if parent != Path(".") else "."
    dir_out = dir_str + "/"
    click.echo(f"{dir_out}\t{p.stem}\t{p.suffix}", nl=False)


def rev_cmd(stdin: Iterable[str]):
    lines = [line.rstrip("\n") for line in stdin]
    for line in reversed(lines):
        click.echo(line)


def decap_stdout(df: DataFile, n_remove: int) -> None:
    """Drop the first *n_remove* lines (``ds:decap``); ``df`` comes from CLI parsing / :class:`DataFile`."""
    try:
        lines = df.read_raw_lines()
        click.echo("".join(lines[n_remove:]), nl=False)
    finally:
        df.cleanup_temp_file()


def _normalize_crlf_text(text: str) -> str:
    # Match awk gsub(/\015$/, "") per line: strip only trailing CR before line end.
    return text.replace("\r\n", "\n")


def dostounix_cmd(
    files: Tuple[str, ...],
    *,
    stdin_data: Optional[str],
    echo: Optional[Callable[..., None]] = None,
) -> None:
    """
    Remove DOS CRLF line endings.

    - With stdin data and no files: write normalized content to stdout.
    - With one or more files: rewrite each file in place.
    """
    echo = echo or click.echo
    if stdin_data is not None and len(files) == 0:
        echo(_normalize_crlf_text(stdin_data), nl=False)
        return

    if len(files) == 0:
        raise click.ClickException("dostounix requires at least one FILE or piped stdin")

    for fp in files:
        if not os.path.isfile(fp):
            raise click.ClickException(f"path provided is not a file: {fp}")
        echo(f"Removing CR line endings in {fp}")
        with open(fp, "r", encoding="utf-8", errors="replace", newline="") as f:
            src = f.read()
        normalized = _normalize_crlf_text(src)
        with open(fp, "w", encoding="utf-8", newline="") as f:
            f.write(normalized)


def newfs_cmd(
    args: Tuple[str, ...],
    *,
    stdin_data: Optional[str],
    echo: Optional[Callable[..., None]] = None,
) -> None:
    """
    Convert field separators for a file or piped data.

    Syntax: ``[FILE] [newfs=,]`` (with stdin, first arg is ``newfs``).
    """
    echo = echo or click.echo
    piped = stdin_data is not None and not (
        stdin_data == "" and len(args) >= 1 and os.path.isfile(args[0])
    )

    if piped:
        newfs = args[0] if len(args) >= 1 else ","
        if len(args) > 1:
            n = len(args) - 1
            click.echo(
                click.style(
                    f"Warning: ignoring {n} extra argument(s) after NEWFS for piped input.",
                    fg="yellow",
                ),
                err=True,
            )
        df = DataFile(None, stdin_text=stdin_data)
    else:
        if len(args) == 0:
            raise click.ClickException("newfs requires a FILE when stdin is a TTY")
        file_path = args[0]
        if not os.path.isfile(file_path):
            raise click.ClickException(f"path provided is not a file: {file_path}")
        newfs = args[1] if len(args) >= 2 else ","
        if len(args) > 2:
            n = len(args) - 2
            click.echo(
                click.style(
                    f"Warning: ignoring {n} extra argument(s) after FILE and NEWFS.",
                    fg="yellow",
                ),
                err=True,
            )
        df = DataFile(file_path)

    try:
        echo(df.convert_field_separator(newfs), nl=False)
    finally:
        df.cleanup_temp_file()


DECAP_CHECKS_TTY: Tuple[ArgCheck, ...] = (
    (lambda c: not c.args, "decap requires a FILE or data on stdin"),
    (lambda c: len(c.args) > 2, "too many arguments; expected FILE [n_lines]"),
)

DECAP_CHECKS_EMPTY_STDIN_FILE: Tuple[ArgCheck, ...] = (
    (lambda c: len(c.args) > 2, "too many arguments; expected FILE [n_lines]"),
)

DECAP_CHECKS_STDIN_PIPE: Tuple[ArgCheck, ...] = (
    (lambda c: len(c.args) > 1, "with stdin, at most one argument is allowed (n_lines)"),
)


def parse_decap(ctx: CliArgContext) -> Tuple[DataFile, int]:
    """
    ``ds decap``: branch-specific checks, then :meth:`~scripts.cli_arg_parse_utils.CliArgContext.to_data_file`.
    """
    args = ctx.args
    stdin_text = ctx.stdin_text

    if stdin_text is None:
        apply_arg_predicates(ctx, DECAP_CHECKS_TTY)
        n_remove = parse_non_negative_int_arg(
            args[1] if len(args) > 1 else None,
            descriptor="n_lines",
        )
    elif stdin_text == "" and args and os.path.isfile(args[0]):
        apply_arg_predicates(ctx, DECAP_CHECKS_EMPTY_STDIN_FILE)
        n_remove = parse_non_negative_int_arg(
            args[1] if len(args) > 1 else None,
            descriptor="n_lines",
        )
    else:
        apply_arg_predicates(ctx, DECAP_CHECKS_STDIN_PIPE)
        n_remove = parse_non_negative_int_arg(
            args[0] if args else None,
            descriptor="n_lines",
        )

    df = ctx.to_data_file()
    return df, n_remove


def join_by_cmd(delimiter: str, values: Tuple[str, ...], stdin_data: Optional[str] = None):
    items: List[str] = []
    if stdin_data is not None and stdin_data.strip():
        items.extend(stdin_data.split())
    items.extend(values)
    if len(items) < 2:
        raise click.ClickException("Not enough args to join.")
    click.echo(delimiter.join(items), nl=False)


def embrace_cmd(ctx: CliArgContext) -> None:
    """
    Enclose text with left/right delimiters (default ``{`` / ``}``).

    Uses :class:`~scripts.cli_arg_parse_utils.CliArgContext` (no file path; ``path_rule`` is
    typically :attr:`~scripts.cli_arg_parse_utils.PathCandidatePredicate.NONE`).

    ``ctx.stdin_text`` is ``None`` on a TTY (``STR [LEFT] [RIGHT]``). Otherwise stdin was read
    (pipe): optional ``LEFT`` and ``RIGHT`` then each input line wrapped, concatenated.
    """
    args = ctx.args
    stdin_text = ctx.stdin_text
    left_default = "{"
    right_default = "}"

    if stdin_text is not None:
        left = args[0] if len(args) >= 1 and args[0] != "" else left_default
        right = args[1] if len(args) >= 2 and args[1] != "" else right_default
        for line in stdin_text.splitlines():
            click.echo(left + line + right, nl=False)
        return

    s = args[0] if len(args) >= 1 else ""
    left = args[1] if len(args) >= 2 and args[1] != "" else left_default
    right = args[2] if len(args) >= 3 and args[2] != "" else right_default
    click.echo(left + s + right, nl=False)


def iter_cmd(text: str, n: int = 1, fs: str = ""):
    if n < 1:
        raise click.ClickException("n must be >= 1.")
    click.echo(fs.join([text] * n), nl=False)


def goog_cmd(query_parts: Tuple[str, ...]):
    if not query_parts:
        raise click.ClickException("Query required for search.")
    query = quote_plus(" ".join(query_parts))
    url = f"https://www.google.com/search?query={query}"
    webbrowser.open(url)
    click.echo(url)


def jira_cmd(workspace_subdomain: str, issue_or_query: Optional[str] = None):
    base = f"https://{workspace_subdomain}.atlassian.net"
    if not issue_or_query:
        url = base
    elif re.match(r"^[A-Z]+-\d+$", issue_or_query):
        url = f"{base}/browse/{issue_or_query}"
    else:
        url = f"{base}/search/{quote_plus(issue_or_query)}"
    webbrowser.open(url)
    click.echo(url)


def _read_insert_source(source: Optional[str], stdin_data: Optional[str]) -> str:
    if stdin_data is not None and stdin_data != "":
        return stdin_data
    if source is None:
        raise click.ClickException("Insertion source not provided.")
    if os.path.isfile(source):
        with open(source, "r", encoding="utf-8") as f:
            return f.read()
    return source


def insert_cmd(sink: str, where: str, source: Optional[str], inplace: str, stdin_data: Optional[str]):
    if not os.path.isfile(sink):
        raise click.ClickException(f'File "{sink}" not provided or invalid')
    insert_data = _read_insert_source(source, stdin_data)
    with open(sink, "r", encoding="utf-8") as f:
        sink_lines = f.read().splitlines(keepends=True)

    out_lines = list(sink_lines)
    where_int: Optional[int] = None
    if where.isdigit() or (where.startswith("-") and where[1:].isdigit()):
        where_int = int(where)

    if where_int is not None:
        idx = max(0, min(len(out_lines), where_int - 1))
        out_lines[idx:idx] = insert_data.splitlines(keepends=True)
    else:
        pattern = re.compile(where)
        match_indices = [i for i, line in enumerate(out_lines) if pattern.search(line)]
        if not match_indices:
            raise click.ClickException("Insertion pattern not found in sink file.")
        if len(match_indices) > 1:
            click.echo("WARNING: pattern matched multiple lines; inserting before first match.")
        idx = match_indices[0]
        out_lines[idx:idx] = insert_data.splitlines(keepends=True)

    rendered = "".join(out_lines)
    if inplace.lower() in {"t", "true", "y", "yes"}:
        with open(sink, "w", encoding="utf-8") as f:
            f.write(rendered)
        return
    click.echo(rendered, nl=False)


def line_cmd(seed_cmds: Optional[str], line_cmds: str, ifs: str, stdin_data: Optional[str]):
    if stdin_data is not None:
        src = stdin_data
    elif seed_cmds:
        seed_res = subprocess.run(seed_cmds, shell=True, text=True, capture_output=True, check=False)
        if seed_res.returncode != 0:
            raise click.ClickException(seed_res.stderr.strip() or "seed_cmds failed.")
        src = seed_res.stdout
    else:
        raise click.ClickException("Either piped stdin or seed_cmds is required.")

    parts = src.split(ifs) if ifs else src.splitlines()
    status = 0
    for item in parts:
        if item == "":
            continue
        cmd = line_cmds.replace("{line}", item)
        env = dict(os.environ)
        env["line"] = item
        result = subprocess.run(
            cmd, shell=True, text=True, env=env, check=False, capture_output=True
        )
        if result.stdout:
            click.echo(result.stdout, nl=False)
        if result.stderr:
            click.echo(result.stderr, nl=False, err=True)
        if result.returncode != 0:
            status = result.returncode
    if status:
        raise SystemExit(status)



class Cardinality:
    def __init__(self):
        self._ = {}
        self.__ = {}
        self.max_nf = 0

    def process_line(self, line):
        fields = line.split()
        for i, field in enumerate(fields, start=1):
            if not self._.get((i, field)):
                self._[(i, field)] = 1
                self.__[i] = self.__.get(i, 0) + 1

        if len(fields) > self.max_nf:
            self.max_nf = len(fields)

    def print_cardinality(self):
        for i in range(1, self.max_nf + 1):
            print(i, self.__.get(i, 0))


def cardinality_cmd(ctx: CliArgContext):
    df = ctx.to_data_file()
    c = Cardinality()
    with open(df.file_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            c.process_line(line)
    c.print_cardinality()

