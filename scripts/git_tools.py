import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

import click


def truthy(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    value = str(value).strip().lower()
    if value in {"1", "t", "true", "y", "yes"}:
        return True
    if value in {"0", "f", "false", "n", "no"}:
        return False
    return default


def run_git(
    args: Sequence[str],
    cwd: Optional[str] = None,
    capture_output: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=capture_output,
        check=check,
    )


def ensure_git_repo(cwd: Optional[str] = None) -> str:
    try:
        top = run_git(["rev-parse", "--show-toplevel"], cwd=cwd).stdout.strip()
    except subprocess.CalledProcessError:
        raise click.ClickException("Current directory is not a git repository.")
    if not top:
        raise click.ClickException("Unable to determine git repository root.")
    return top


def iter_repos(base_dir: Optional[str]) -> List[str]:
    if base_dir is None:
        base_dir = os.path.expanduser("~")
    root = os.path.abspath(os.path.expanduser(base_dir))
    if not os.path.isdir(root):
        raise click.ClickException(f'"{root}" is not a valid directory.')

    repos: List[str] = []

    def _is_repo(path: str) -> bool:
        try:
            run_git(["rev-parse", "--git-dir"], cwd=path)
            return True
        except subprocess.CalledProcessError:
            return False

    if _is_repo(root):
        repos.append(root)

    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if os.path.isdir(path) and _is_repo(path):
            repos.append(path)
    return repos


def current_branch(cwd: Optional[str] = None) -> str:
    return run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd).stdout.strip()


def branch_tracking(cwd: Optional[str] = None) -> Optional[str]:
    try:
        return run_git(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=cwd,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def git_recent_rows(repo_dir: str, refs: str = "heads") -> List[Dict[str, str]]:
    fmt = "%(HEAD) %(refname:short)@@@%(committerdate:short)@@@%(committerdate:relative)@@@%(objectname:short)@@@%(subject)@@@%(authorname)"
    out = run_git(
        ["for-each-ref", f"refs/{refs}", "--sort=-committerdate", f"--format={fmt}"],
        cwd=repo_dir,
    ).stdout
    rows: List[Dict[str, str]] = []
    for raw in out.splitlines():
        parts = raw.split("@@@")
        if len(parts) != 6:
            continue
        head_and_ref = parts[0].strip()
        rows.append(
            {
                "head_ref": head_and_ref,
                "short_date": parts[1].strip(),
                "relative_time": parts[2].strip(),
                "hash": parts[3].strip(),
                "subject": parts[4].strip(),
                "author": parts[5].strip(),
            }
        )
    return rows


def repo_change_counts(repo_dir: str) -> Tuple[int, int]:
    out = run_git(["status", "--porcelain"], cwd=repo_dir).stdout
    staged = 0
    unstaged = 0
    for line in out.splitlines():
        if not line:
            continue
        if len(line) >= 2:
            if line[0] not in {" ", "?"}:
                staged += 1
            if line[1] not in {" "}:
                unstaged += 1
    return staged, unstaged


def fmt_timestamp(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts).strftime("%a %b %d %H:%M:%S %Y %z")
