"""
Search helpers that prefer fast external tools when available, with Python fallbacks.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Callable, Optional, Tuple

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


def _scan_file(fp: str, rx: re.Pattern[str]) -> list[str]:
    out: list[str] = []
    try:
        with open(fp, encoding="utf-8", errors="replace") as f:
            for line in f:
                if rx.search(line):
                    stripped = line.rstrip("\n\r")
                    out.append(f"{fp}:{stripped}")
    except OSError:
        return out
    return out


def _python_scan(path: str, rx: re.Pattern[str]) -> list[str]:
    out: list[str] = []
    if os.path.isfile(path):
        return _scan_file(path, rx)
    for dirpath, _dirnames, filenames in os.walk(path):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            if os.path.isfile(fp):
                out.extend(_scan_file(fp, rx))
    return out


def _rg_scan(
    paths: Tuple[str, ...],
    pattern: str,
) -> tuple[int, list[str]]:
    rg = shutil.which("rg")
    if not rg:
        return -1, []
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
        return -1, []
    if r.returncode not in (0, 1):
        raise click.ClickException(r.stderr.strip() or f"rg failed with code {r.returncode}")
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return 0, lines


def collect_search_matches(
    paths: Tuple[str, ...],
    pattern: str,
    *,
    echo: Callable[..., None] | None = None,
    print_matches: bool = True,
) -> tuple[int, list[str]]:
    """
    Search ``paths`` for regex ``pattern`` and return ``(exit_code, matches)``.

    ``matches`` are rendered strings (``filepath:line``), same format used by ``run_search``.
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
        return 1, []

    use_rg = is_command_available("rg") and shutil.which("rg") is not None
    all_matches: list[str] = []
    for root in resolved:
        if use_rg:
            try:
                code, matches = _rg_scan((root,), pattern)
            except click.ClickException:
                use_rg = False
                matches = _python_scan(root, rx)
            else:
                if code == -1:
                    use_rg = False
                    matches = _python_scan(root, rx)
        else:
            matches = _python_scan(root, rx)
        all_matches.extend(matches)

    if print_matches:
        for line in all_matches:
            echo(line)

    if bad:
        echo("Some paths provided could not be searched", err=True)
        return 1, all_matches
    return 0, all_matches


def run_search(
    paths: Tuple[str, ...],
    pattern: str,
    *,
    echo: Callable[..., None] | None = None,
    print_matches: bool = True,
) -> int:
    """
    Search ``paths`` for ``pattern`` (regex). With no paths, searches ``'.'``.

    Uses ``rg`` when it is on PATH (see :mod:`scripts.tool_availability`); otherwise walks
    with :func:`re.compile` using case-insensitive matching (``rg -i`` parity).

    Returns ``0`` or ``1`` (some paths invalid).
    """
    code, _matches = collect_search_matches(
        paths,
        pattern,
        echo=echo,
        print_matches=print_matches,
    )
    return code


def _normalize_path(path: str) -> str:
    return os.path.normpath(os.path.abspath(path))


def _search_dirs_with_fd(search: str, binary: str, max_results: int) -> list[str]:
    try:
        r = subprocess.run(
            [binary, "-t", "d", search],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return []
    if r.returncode not in (0, 1):
        return []
    out: list[str] = []
    for raw in r.stdout.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("./"):
            s = s[2:]
        out.append(_normalize_path(s))
        if len(out) >= max_results:
            break
    return out


def _search_dirs_python(search: str, root: str, max_results: int) -> list[str]:
    needle = search.lower()
    out: list[str] = []
    for dirpath, dirnames, _filenames in os.walk(root):
        for dname in dirnames:
            if needle in dname.lower():
                out.append(_normalize_path(os.path.join(dirpath, dname)))
                if len(out) >= max_results:
                    return out
    return out


def search_directories_by_name(
    search: str,
    *,
    root: str = ".",
    max_results: int = 100,
) -> list[str]:
    """
    Return matching directories by name (tool-first: ``fd``, ``fd-find``, then Python walk).
    """
    if is_command_available("fd"):
        found = _search_dirs_with_fd(search, "fd", max_results)
        if found:
            return found
    if is_command_available("fd-find"):
        found = _search_dirs_with_fd(search, "fd-find", max_results)
        if found:
            return found
    return _search_dirs_python(search, _normalize_path(root), max_results)


def find_parent_level_match(search: str, *, levels: int = 6) -> Optional[str]:
    needle = search.lower()
    here = _normalize_path(".")
    for _ in range(levels):
        here = _normalize_path(os.path.join(here, ".."))
        try:
            entries = list(os.scandir(here))
        except OSError:
            break
        for entry in entries:
            if entry.is_dir() and needle in entry.name.lower():
                return _normalize_path(entry.path)
    return None
