"""
Search files with ``ripgrep`` when available, otherwise a small Python walker.

The **pattern** is a regular expression string (same for ``rg --regexp`` and Python ``re``).
Callers (e.g. :func:`scripts.simple_commands.run_todo`) supply the pattern.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Callable, Tuple

import click

from scripts.tool_availability import is_command_available


def _resolve_paths(
    paths: Tuple[str, ...],
    echo: Callable[..., None],
) -> tuple[list[str], bool]:
    bad = False
    resolved: list[str] = []
    for p in paths:
        np = os.path.normpath(p)
        if not os.path.isdir(np) and not os.path.isfile(np):
            echo(f"{p} is not a file or directory or is not found", err=True)
            bad = True
            continue
        resolved.append(np)
    return resolved, bad


def _scan_file(fp: str, rx: re.Pattern[str], echo: Callable[..., None]) -> None:
    try:
        with open(fp, encoding="utf-8", errors="replace") as f:
            for line in f:
                if rx.search(line):
                    stripped = line.rstrip("\n\r")
                    echo(f"{fp}:{stripped}")
    except OSError:
        pass


def _python_scan(path: str, rx: re.Pattern[str], echo: Callable[..., None]) -> None:
    if os.path.isfile(path):
        _scan_file(path, rx, echo)
        return
    for dirpath, _dirnames, filenames in os.walk(path):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            if os.path.isfile(fp):
                _scan_file(fp, rx, echo)


def _rg_scan(
    paths: Tuple[str, ...],
    pattern: str,
    echo: Callable[..., None],
) -> int:
    rg = shutil.which("rg")
    if not rg:
        return -1
    cmd = [
        rg,
        "-H",
        "-N",
        "--color",
        "never",
        "-i",
        "--regexp",
        pattern,
        *paths,
    ]
    if os.name == "nt":
        cmd.insert(1, "--path-separator")
        cmd.insert(2, "/")
    try:
        r = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return -1
    if r.returncode not in (0, 1):
        echo(r.stderr, nl=False, err=True)
        return r.returncode
    if r.stdout:
        echo(r.stdout, nl=False)
    return 0


def run_search(
    paths: Tuple[str, ...],
    pattern: str,
    *,
    echo: Callable[..., None] | None = None,
) -> int:
    """
    Search ``paths`` for ``pattern`` (regex). With no paths, searches ``'.'``.

    Uses ``rg`` when it is on PATH (see :mod:`scripts.tool_availability`); otherwise walks
    with :func:`re.compile` using case-insensitive matching (``rg -i`` parity).

    Returns ``0`` or ``1`` (some paths invalid).
    """
    echo = echo or click.echo
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise click.ClickException(f"Invalid search pattern: {e}") from e

    if not paths:
        paths = (".",)

    resolved, bad = _resolve_paths(paths, echo)
    if not resolved:
        return 1

    use_rg = is_command_available("rg") and shutil.which("rg") is not None

    for i, root in enumerate(resolved):
        if i > 0:
            echo("")
        if use_rg:
            code = _rg_scan((root,), pattern, echo)
            if code in (-1, 2) or code > 2:
                use_rg = False
                _python_scan(root, rx, echo)
            elif code not in (0, 1):
                return code
        else:
            _python_scan(root, rx, echo)

    if bad:
        echo("Some paths provided could not be searched", err=True)
        return 1
    return 0
