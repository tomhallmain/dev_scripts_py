import os
import re
import subprocess
import webbrowser
from typing import Iterable, List, Optional, Tuple
from urllib.parse import quote_plus

import click

from scripts.DataFile import DataFile


def rev_cmd(stdin: Iterable[str]):
    lines = [line.rstrip("\n") for line in stdin]
    for line in reversed(lines):
        click.echo(line)


def decap_stdout(n_remove: int, path_candidate: Optional[str], stdin_text: Optional[str]) -> None:
    """Drop the first *n_remove* lines from a file or stdin (``ds:decap``)."""
    try:
        df = DataFile.from_cli_file_or_stdin(path_candidate, stdin_text)
    except Exception as e:
        raise click.ClickException(str(e)) from e
    try:
        lines = df.read_raw_lines()
        click.echo("".join(lines[n_remove:]), nl=False)
    finally:
        df.cleanup_temp_file()


def join_by_cmd(delimiter: str, values: Tuple[str, ...], stdin_data: Optional[str] = None):
    items: List[str] = []
    if stdin_data is not None and stdin_data.strip():
        items.extend(stdin_data.split())
    items.extend(values)
    if len(items) < 2:
        raise click.ClickException("Not enough args to join.")
    click.echo(delimiter.join(items), nl=False)


def embrace_cmd(args: Tuple[str, ...], stdin_data: Optional[str]) -> None:
    """
    Enclose text with left/right delimiters (default ``{`` / ``}``).

    ``stdin_data`` is ``None`` when stdin was a TTY (string form: ``str [left [right]]``).
    Otherwise stdin was read (pipe): ``[left [right]]`` apply to each line, concatenated.
    """
    left_default = "{"
    right_default = "}"

    if stdin_data is not None:
        left = args[0] if len(args) >= 1 and args[0] != "" else left_default
        right = args[1] if len(args) >= 2 and args[1] != "" else right_default
        for line in stdin_data.splitlines():
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
