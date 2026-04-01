import os

import click

from scripts.all_repo_git_branch import GitRepo
from scripts.all_repo_git_status import GitStatus
from scripts.git_tools import (
    branch_tracking,
    current_branch,
    ensure_git_repo,
    fmt_timestamp,
    git_recent_rows,
    iter_repos,
    repo_change_counts,
    run_git,
    truthy,
)
from scripts.purge_local_branches import GitBranchPurger


def git_status_cmd(base_dir, track_non_repos=False):
    gs = GitStatus(base_dir, track_non_repos=track_non_repos)
    gs.get_git_repos()
    gs.print_git_status()


def git_branch_cmd(base_dir):
    gr = GitRepo()
    if base_dir:
        gr.home_dirs = [
            os.path.join(base_dir, d)
            for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d))
        ]
    gr.find_repos()
    gr.print_branches()


def git_purge_local_cmd(base_dir, branches):
    purger = GitBranchPurger(base_dir)
    purger.purge_branches(list(branches))


def git_add_com_push_cmd(commit_message="", prompt="t"):
    repo_root = ensure_git_repo()
    if truthy(prompt, default=True):
        click.echo(run_git(["status"], cwd=repo_root).stdout.rstrip())
        confirm = click.prompt(
            "Proceed with add+commit+push? (y/n/new_commit_message)",
            default="n",
            show_default=False,
        ).strip()
        if confirm.lower() == "n":
            click.echo("No add/commit/push made.")
            return
        if confirm.lower() != "y":
            commit_message = confirm
            if not click.confirm(f'Change message to "{commit_message}"?', default=True):
                click.echo("No add/commit/push made.")
                return

    run_git(["add", repo_root], cwd=repo_root)
    if commit_message:
        run_git(["commit", "-m", commit_message], cwd=repo_root)
    else:
        run_git(["commit"], cwd=repo_root)

    upstream = run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=repo_root,
        check=False,
    )
    if upstream.returncode != 0:
        branch = current_branch(repo_root)
        run_git(["push", "--set-upstream", "origin", branch], cwd=repo_root)
        click.echo("\nSet a new upstream branch for current branch.")
    else:
        run_git(["push"], cwd=repo_root)


def git_checkout_cmd(branch_pattern="", new_branch="f"):
    repo_root = ensure_git_repo()
    if truthy(new_branch, default=False):
        if not branch_pattern:
            raise click.ClickException("Branch name is required when new_branch is true.")
        run_git(["checkout", "-b", branch_pattern], cwd=repo_root)
        return

    branches = [
        b.strip().lstrip("*").strip()
        for b in run_git(["branch", "--list"], cwd=repo_root).stdout.splitlines()
        if b.strip()
    ]
    if not branch_pattern:
        click.echo("\n".join(branches))
        return

    exact = [b for b in branches if b == branch_pattern]
    if exact:
        run_git(["checkout", exact[0]], cwd=repo_root)
        return

    matches = [b for b in branches if branch_pattern.lower() in b.lower()]
    if not matches:
        raise click.ClickException(f'No branch matched pattern "{branch_pattern}".')
    if len(matches) > 1:
        raise click.ClickException(f"Multiple matches found: {', '.join(matches)}")
    run_git(["checkout", matches[0]], cwd=repo_root)


def git_cross_view_cmd(base_dir=None, show_status=False):
    repos = iter_repos(base_dir)
    if not repos:
        click.echo("No git repositories found.")
        return
    header = "repo\tbranch\tupstream"
    if show_status:
        header += "\tstaged\tunstaged"
    click.echo(header)
    for repo in repos:
        branch = current_branch(repo)
        upstream = branch_tracking(repo) or "-"
        row = f"{repo}\t{branch}\t{upstream}"
        if show_status:
            staged, unstaged = repo_change_counts(repo)
            row += f"\t{staged}\t{unstaged}"
        click.echo(row)


def git_diff_cmd(git_args):
    repo_root = ensure_git_repo()
    args = list(git_args)
    if not args:
        click.echo(run_git(["diff"], cwd=repo_root).stdout.rstrip())
        return

    first = args[0]
    if first and os.path.isfile(first):
        click.echo(run_git(["diff", *args], cwd=repo_root).stdout.rstrip())
        return

    if len(args) < 2:
        raise click.ClickException("Missing commit or branch objects.")

    from_object, to_object = args[0], args[1]
    exclusions = [f":(exclude){x}" for x in args[2:]]
    out = run_git(["diff", from_object, to_object, "-b", "--", ".", *exclusions], cwd=repo_root).stdout
    click.echo(out.rstrip())


def git_graph_cmd():
    repo_root = ensure_git_repo()
    click.echo(run_git(["log", "--all", "--decorate", "--oneline", "--graph"], cwd=repo_root).stdout.rstrip())


def git_recent_cmd(refs="heads", run_context="display"):
    repo_root = ensure_git_repo()
    rows = git_recent_rows(repo_root, refs=refs)
    if run_context == "display":
        click.echo("branch\trelative_time\tsubject\tauthor")
        for row in rows:
            click.echo(f"{row['head_ref']}\t{row['relative_time']}\t{row['subject']}\t{row['author']}")
    else:
        for row in rows:
            click.echo(
                f"{row['head_ref']}@@@{row['short_date']}@@@{row['relative_time']}@@@{row['hash']}@@@{row['subject']}@@@{row['author']}"
            )


def git_recent_all_cmd(refs="heads", base_dir=None):
    repos = iter_repos(base_dir)
    all_rows = []
    for repo in repos:
        for row in git_recent_rows(repo, refs=refs):
            all_rows.append((repo, row))
    all_rows.sort(key=lambda x: x[1]["short_date"], reverse=True)
    click.echo("repo\tbranch\tdate\trelative\thash\tsubject\tauthor")
    for repo, row in all_rows:
        click.echo(
            f"{repo}\t{row['head_ref']}\t{row['short_date']}\t{row['relative_time']}\t{row['hash']}\t{row['subject']}\t{row['author']}"
        )


def git_refresh_cmd(base_dir=None):
    repos = iter_repos(base_dir)
    if not repos:
        click.echo("No git repositories found.")
        return
    for repo in repos:
        click.echo(f"\n{repo}")
        result = run_git(["pull"], cwd=repo, check=False)
        if result.returncode == 0:
            click.echo(result.stdout.rstrip())
        else:
            click.echo(click.style(result.stderr.rstrip(), fg="yellow"))


def git_squash_cmd(n_commits=1, yes=False):
    repo_root = ensure_git_repo()
    if n_commits < 1:
        raise click.ClickException("n_commits must be >= 1.")
    if not yes:
        conf = click.prompt(
            f"Are you sure you want to squash the last {n_commits} commit(s)? (y/n)",
            default="n",
            show_default=False,
        ).strip().lower()
        if conf != "y":
            click.echo("No change made.")
            return

    msg = run_git(["log", "--format=%B", "--reverse", f"HEAD~{n_commits}..HEAD"], cwd=repo_root).stdout.strip()
    run_git(["reset", "--soft", f"HEAD~{n_commits}"], cwd=repo_root)
    if msg:
        run_git(["commit", "-m", msg], cwd=repo_root)
    else:
        run_git(["commit"], cwd=repo_root)


def git_time_stat_cmd():
    repo_root = ensure_git_repo()
    git_dir = run_git(["rev-parse", "--git-dir"], cwd=repo_root).stdout.strip()
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(repo_root, git_dir)

    last_pull = fmt_timestamp(os.path.join(git_dir, "FETCH_HEAD"))
    last_change = fmt_timestamp(os.path.join(git_dir, "HEAD"))
    last_commit = run_git(["log", "-1", "--format=%cd"], cwd=repo_root, check=False).stdout.strip()

    if last_pull:
        click.echo(f"{'Time of last pull:':<40}{last_pull}")
    else:
        click.echo("No pulls found")
    if last_change:
        click.echo(f"{'Time of last local change:':<40}{last_change}")
    else:
        click.echo("No local changes found")
    if last_commit:
        click.echo(f"{'Time of last commit found locally:':<40}{last_commit}")
    else:
        click.echo("No local commit found")


def git_word_diff_cmd(git_diff_args):
    repo_root = ensure_git_repo()
    out = run_git(
        [
            "diff",
            "--word-diff-regex=[A-Za-z0-9. ]|[^[:space:]]",
            "--word-diff=color",
            *git_diff_args,
        ],
        cwd=repo_root,
    ).stdout
    click.echo(out.rstrip())


def git_branch_refs_cmd(branch=None, invert="f"):
    repo_root = ensure_git_repo()
    current = current_branch(repo_root)
    local_branches = sorted(
        [
            x.strip()
            for x in run_git(["for-each-ref", "--format=%(refname:short)", "refs/heads"], cwd=repo_root).stdout.splitlines()
            if x.strip()
        ]
    )
    target = branch or current
    if target not in local_branches:
        raise click.ClickException(f"Branch not found: {target}")

    run_git(["fetch"], cwd=repo_root, check=False)
    is_clean = len(run_git(["status", "--porcelain"], cwd=repo_root).stdout.strip()) == 0
    if is_clean and target != current:
        run_git(["checkout", target], cwd=repo_root, check=False)
        run_git(["pull"], cwd=repo_root, check=False)
    elif not is_clean:
        click.echo(f"WARNING: Unable to pull latest {target}; uncommitted changes exist.")

    merged = {
        x.strip().lstrip("*").strip()
        for x in run_git(["branch", "--merged", target], cwd=repo_root).stdout.splitlines()
        if x.strip()
    }
    show_unmerged = truthy(invert, default=False)
    if show_unmerged:
        click.echo(f"Unmerged branches on {target}:\n")
        lines = [b for b in local_branches if b not in merged]
    else:
        click.echo(f"Merged branches on {target}:\n")
        lines = [b for b in local_branches if b in merged]
    for line in lines:
        click.echo(line)

    if target != current:
        run_git(["checkout", current], cwd=repo_root, check=False)
