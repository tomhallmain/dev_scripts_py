import os
import subprocess
from termcolor import colored

class GitRepo:
    def __init__(self):
        self.home_dirs = [name for name in os.listdir(os.path.expanduser('~')) if os.path.isdir(os.path.join(os.path.expanduser('~'), name))]
        self.repos = []

    def find_repos(self):
        for dir in self.home_dirs:
            try:
                subprocess.check_output(['git', '-C', dir, 'rev-parse'])
                self.repos.append(dir)
            except subprocess.CalledProcessError:
                pass

    def print_branches(self):
        for repo in self.repos:
            print(colored(repo, 'white'))
            try:
                branches = subprocess.check_output(['git', '-C', repo, 'branch']).decode('utf-8')
                if branches:
                    print(branches)
                else:
                    print(colored('No non-master branches found.', 'yellow'))
            except subprocess.CalledProcessError:
                print(colored('No non-master branches found.', 'yellow'))

if __name__ == "__main__":
    git_repo = GitRepo()
    git_repo.find_repos()
    git_repo.print_branches()
