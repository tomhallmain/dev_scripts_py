import os
import sys
import subprocess
from termcolor import colored


class GitStatus:
    def __init__(self, base_dir=None, track_non_repos=False):
        if base_dir is None:
            base_dir = os.path.expanduser('~')
        self.base_dir = os.path.abspath(os.path.expanduser(base_dir))
        self.repos = []
        self.track_non_repos = track_non_repos
        self.non_repos = []

    def get_git_repos(self):
        """Find all git repositories in the base directory."""
        if not os.path.isdir(self.base_dir):
            print(colored(f'Error: "{self.base_dir}" is not a valid directory.', 'red'))
            return
        
        # Check if base directory itself is a git repo
        if os.path.isdir(os.path.join(self.base_dir, '.git')):
            try:
                subprocess.check_output(['git', '-C', self.base_dir, 'rev-parse'], stderr=subprocess.STDOUT)
                self.repos.append(self.base_dir)
            except subprocess.CalledProcessError:
                if self.track_non_repos:
                    self.non_repos.append(self.base_dir)
        elif self.track_non_repos:
            self.non_repos.append(self.base_dir)
        
        # Check subdirectories
        try:
            for item in os.listdir(self.base_dir):
                item_path = os.path.join(self.base_dir, item)
                if os.path.isdir(item_path):
                    if os.path.isdir(os.path.join(item_path, '.git')):
                        try:
                            subprocess.check_output(['git', '-C', item_path, 'rev-parse'], stderr=subprocess.STDOUT)
                            self.repos.append(item_path)
                        except subprocess.CalledProcessError:
                            if self.track_non_repos:
                                self.non_repos.append(item_path)
                    elif self.track_non_repos:
                        self.non_repos.append(item_path)
        except PermissionError:
            print(colored(f'Error: Permission denied accessing "{self.base_dir}".', 'red'))

    def check_remote_tracking(self, repo):
        """Check if current branch has a remote tracking branch configured."""
        try:
            # Get current branch name
            current_branch = subprocess.check_output(
                ['git', '-C', repo, 'rev-parse', '--abbrev-ref', 'HEAD'],
                stderr=subprocess.STDOUT
            ).decode().strip()
            
            # Check if branch has upstream tracking
            try:
                upstream = subprocess.check_output(
                    ['git', '-C', repo, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'],
                    stderr=subprocess.STDOUT
                ).decode().strip()
                return True, current_branch, upstream
            except subprocess.CalledProcessError:
                # Check if any remotes exist
                remotes = subprocess.check_output(
                    ['git', '-C', repo, 'remote'],
                    stderr=subprocess.STDOUT
                ).decode().strip()
                if remotes:
                    return False, current_branch, remotes.split('\n')[0] if remotes else None
                return False, current_branch, None
        except subprocess.CalledProcessError:
            return None, None, None

    def print_git_status(self):
        for repo in self.repos:
            print(colored(f'\n{repo}', 'white'))
            
            # Check remote tracking status
            has_tracking, branch, upstream_or_remote = self.check_remote_tracking(repo)
            if has_tracking is not None:
                if has_tracking:
                    print(colored(f'  Branch: {branch} → tracking {upstream_or_remote}', 'green'))
                elif upstream_or_remote:
                    print(colored(f'  Branch: {branch} → no tracking branch (remote "{upstream_or_remote}" exists)', 'yellow'))
                else:
                    print(colored(f'  Branch: {branch} → no remote configured', 'red'))
            
            try:
                print(subprocess.check_output(['git', '-C', repo, 'status'], stderr=subprocess.STDOUT).decode())
            except subprocess.CalledProcessError:
                print(colored('Error requesting status.', 'red'))
        
        # Print non-repository directories if tracking is enabled
        if self.track_non_repos and self.non_repos:
            print(colored('\nNon-repository directories:', 'yellow'))
            for non_repo in self.non_repos:
                print(colored(f'  {non_repo}', 'yellow'))
        
        print('\n')


if __name__ == "__main__":
    base_dir = sys.argv[1] if len(sys.argv) > 1 else None
    track_non_repos = '--track-non-repos' in sys.argv or '-t' in sys.argv
    git_status = GitStatus(base_dir, track_non_repos=track_non_repos)
    git_status.get_git_repos()
    git_status.print_git_status()
