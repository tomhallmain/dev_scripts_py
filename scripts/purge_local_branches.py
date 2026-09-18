import os
import re
import subprocess

class GitBranchPurger:
    def __init__(self, base_dir):
        self.base_dir = base_dir if os.path.isdir(base_dir) else os.path.expanduser('~')
        self.master_branches = ['master', 'main', 'develop', 'dev', 'integration', 'integrations']
        # Anchored at both ends: only these exact names are protected, so a branch
        # merely starting with one of them (mainline, devops) stays purgeable.
        self._protected_re = re.compile('^(' + '|'.join(self.master_branches) + ')$')
        # Preference order for the branch to sit on while deleting another, since a
        # checked-out branch cannot be deleted.
        self.safe_checkout_branches = ['main', 'master', 'develop', 'integration']

    def get_base_dirs(self):
        return next(os.walk(self.base_dir))[1]

    def is_git_repo(self, directory):
        return (
            subprocess.call(
                ['git', '-C', directory, 'rev-parse'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            == 0
        )

    def get_all_repos(self):
        repos = []
        for d in self.get_base_dirs():
            abs_dir = os.path.join(self.base_dir, d)
            if self.is_git_repo(abs_dir):
                repos.append(abs_dir)
        return repos

    def get_branches(self, repo):
        branches = subprocess.check_output(['git', 'for-each-ref', '--format=%(refname:lstrip=2)', 'refs/heads/'], cwd=repo).decode().splitlines()
        return [branch for branch in branches if not self._protected_re.match(branch)]

    def branch_exists(self, repo, branch):
        return subprocess.call(
            ['git', '-C', repo, 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ) == 0

    def checkout_safe_branch(self, repo, avoid=None):
        """Move off `avoid` so it can be deleted, trying each safe branch that exists.

        Best effort: a branch that is not the checked-out one deletes without this, and
        a repo whose default branch is named something else should still get that far.
        """
        for candidate in self.safe_checkout_branches:
            if candidate == avoid or not self.branch_exists(repo, candidate):
                continue
            if subprocess.call(
                ['git', '-C', repo, 'checkout', candidate],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ) == 0:
                return candidate
        return None

    def purge_branches(self, branches_to_purge):
        all_repos = self.get_all_repos()
        for repo in all_repos:
            branches = self.get_branches(repo)
            for branch in branches:
                if branch in branches_to_purge:
                    print(f'Deleting {branch} from {repo}')
                    self.checkout_safe_branch(repo, avoid=branch)
                    try:
                        subprocess.check_call(['git', '-C', repo, 'branch', '-D', branch])
                    except subprocess.CalledProcessError as e:
                        print(f'Error deleting branch {branch} in repo {repo}: {str(e)}')

if __name__ == "__main__":
    purger = GitBranchPurger('/path/to/your/directory')
    purger.purge_branches(['branch1', 'branch2', 'branch3'])
