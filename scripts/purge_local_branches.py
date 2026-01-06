import os
import re
import subprocess

class GitBranchPurger:
    def __init__(self, base_dir):
        self.base_dir = base_dir if os.path.isdir(base_dir) else os.path.expanduser('~')
        self.master_branches = ['master', 'main', 'develop', 'dev', 'integration']

    def get_base_dirs(self):
        return next(os.walk(self.base_dir))[1]

    def is_git_repo(self, directory):
        return subprocess.call(['git', '-C', directory, 'rev-parse'], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

    def get_all_repos(self):
        return [dir for dir in self.get_base_dirs() if self.is_git_repo(dir)]

    def get_branches(self, repo):
        branches = subprocess.check_output(['git', 'for-each-ref', '--format=%(refname:lstrip=2)', 'refs/heads/'], cwd=repo).decode().splitlines()
        return [branch for branch in branches if not re.match('|'.join(self.master_branches), branch)]

    def purge_branches(self, branches_to_purge):
        all_repos = self.get_all_repos()
        for repo in all_repos:
            os.chdir(repo)
            branches = self.get_branches(repo)
            for branch in branches:
                if branch in branches_to_purge:
                    print(f'Deleting {branch} from {repo}')
                    try:
                        subprocess.check_call(['git', 'checkout', self.master_branches[0]])
                        subprocess.check_call(['git', 'branch', '-D', branch])
                    except subprocess.CalledProcessError as e:
                        print(f'Error deleting branch {branch} in repo {repo}: {str(e)}')
            os.chdir(self.base_dir)

if __name__ == "__main__":
    purger = GitBranchPurger('/path/to/your/directory')
    purger.purge_branches(['branch1', 'branch2', 'branch3'])
