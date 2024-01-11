import os
import subprocess
from termcolor import colored


class GitStatus:
    def __init__(self):
        self.home_dirs = [name for name in os.listdir(os.path.expanduser('~')) if os.path.isdir(os.path.join(os.path.expanduser('~'), name))]
        self.repos = []

    def get_git_repos(self):
        for dir in self.home_dirs:
            try:
                subprocess.check_output(['git', '-C', dir, 'rev-parse'], stderr=subprocess.STDOUT)
                self.repos.append(dir)
            except subprocess.CalledProcessError:
                pass

    def print_git_status(self):
        for repo in self.repos:
            print(colored(f'\n{repo}', 'white'))
            try:
                print(subprocess.check_output(['git', '-C', repo, 'status'], stderr=subprocess.STDOUT).decode())
            except subprocess.CalledProcessError:
                print(colored('Error requesting status.', 'red'))
        print('\n')


if __name__ == "__main__":
    git_status = GitStatus()
    git_status.get_git_repos()
    git_status.print_git_status()
