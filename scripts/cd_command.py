from __future__ import annotations

import os
from typing import Optional

import click

from scripts.tool_based_search import find_parent_level_match, search_directories_by_name


def _normalize_dir_path(path: str) -> str:
    return os.path.normpath(os.path.abspath(path))


def _choose_directory(matches: list[str]) -> str:
    current = list(dict.fromkeys(matches))
    while True:
        click.echo("Multiple matches found - select a directory:")
        for i, path in enumerate(current, start=1):
            click.echo(f"{i}: {path}")
        choice = click.prompt(
            "Enter a number from the set of directories or a pattern",
            type=str,
        ).strip()
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(current):
                return current[n - 1]
            click.echo("Unable to read selection, try again.")
            continue
        filtered = [p for p in current if choice.lower() in p.lower()]
        if not filtered:
            click.echo("Unable to read selection, try again.")
            continue
        if len(filtered) == 1:
            return filtered[0]
        current = filtered


def cd_cmd(search: Optional[str]) -> str:
    """
    Resolve a target directory for ``ds cd`` and print it.

    A subprocess cannot mutate the caller shell's CWD; shell usage is:
    ``cd "$(ds . cd <search>)"``.
    """
    if not search:
        target = _normalize_dir_path(os.path.expanduser("~"))
        click.echo(target)
        return target

    direct = _normalize_dir_path(search)
    if os.path.isdir(direct):
        click.echo(direct)
        return direct

    matches = search_directories_by_name(search, root=".", max_results=100)
    if matches:
        target = _choose_directory(matches) if len(matches) > 1 else matches[0]
        click.echo(target)
        return target

    parent_match = find_parent_level_match(search, levels=6)
    if parent_match:
        click.echo(parent_match)
        return parent_match
    raise click.ClickException("Unable to find a match with current args")
