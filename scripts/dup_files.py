import argparse
from collections import defaultdict
import hashlib
import os
import re
import sys

# TODO maybe option to not preserve/ignore duplicates if they exist in different subdirectories within the root

class DuplicateRemover:
    INDEX_REGEX = re.compile(r'\s\(\d+\)(.[a-z0-9]{1,5})?$') # regex to match files with indices like " (1)" or " (2)"
    NORMAL_FILE_CHARS_REGEX = re.compile(r'^[\w_\-. ]+$')
    STARTS_WITH_ALPHA_REGEX = re.compile(r'^[A-Za-z]')

    def __init__(self, source_folder, select_for_folder_depth=False, match_dir=False, recursive=True, exclude_dirs=[]):
        self.source_folder = source_folder
        self.duplicates = {}
        self.select_for_folder_depth = select_for_folder_depth
        self.match_dir = match_dir
        self.recursive = recursive
        self.dir_separator_char = "\\" if sys.platform.startswith("win") else "/"
        self.exclude_dirs = list(map(lambda d: os.path.normpath(d), exclude_dirs))
        self.skip_exclusion_check = len(self.exclude_dirs) == 0
        if not self.skip_exclusion_check:
            print("Excluding directories from duplicates check:")
            for d in self.exclude_dirs:
                if not os.path.exists(d) or not os.path.isdir(d):
                    raise Exception("Invalid exclude directory: " + d)
                print(d)

    def get_file_hash(self, file_path):
        hash_obj = hashlib.md5()
        with open(file_path, 'rb') as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def is_excluded(self, file_path):
        for d in self.exclude_dirs:
            if file_path.startswith(d):
                return True
        return False

    def find_duplicates(self):
        file_dict = defaultdict(list)
        for foldername, subfolders, filenames in os.walk(self.source_folder):
            if not self.recursive and foldername != self.source_folder: # TODO better way to handle this
                continue
            for filename in filenames:
                file_path = os.path.normpath(os.path.join(foldername, filename))
                if self.skip_exclusion_check or not self.is_excluded(file_path):
                    file_dict[self.get_file_hash(file_path)].append(file_path)
        self.duplicates = {k: v for k, v in file_dict.items() if len(v) > 1}
        return self.has_duplicates()

    def has_duplicates(self):
        return len(self.duplicates) > 0

    def determine_duplicates(self, file_list):
        best_duplicate = self.select_best_duplicate(file_list)
        best_duplicate_dir = os.path.dirname(best_duplicate) if self.match_dir else ""
        def is_valid_duplicate(f, best_duplicate):
            if f == best_duplicate:
                return False
            return not self.match_dir or os.path.dirname(f) == best_duplicate_dir
        duplicates_to_remove = [f for f in file_list if is_valid_duplicate(f, best_duplicate)]
        return best_duplicate, duplicates_to_remove

    def handle_duplicates(self, testing, skip_confirm=True):
        for file_list in self.duplicates.values():
            best_duplicate, duplicates_to_remove = self.determine_duplicates(file_list)
            if self.match_dir and len(duplicates_to_remove) == 0:
                continue
            if testing:
                print("Keeping file:               " + best_duplicate)
                print("Removing duplicate files: " + str(duplicates_to_remove))
            else:
                if not skip_confirm:
                    print("Keeping file:               " + best_duplicate)
                    print("Removing duplicate files: " + str(duplicates_to_remove))
                    confirm = input(f"OK to remove? (Y/n): ")
                    if confirm.lower() != "y":
                        continue
                for file_path in duplicates_to_remove:
                    print("Removing file: " + file_path)
                    os.remove(file_path)

    def select_best_duplicate(self, file_list):
        # sort the file_list by the creation time
        file_list.sort(key=lambda x: os.path.getctime(x))
        best_candidates = file_list[:]
        # iterate over the sorted file_list to find the best
        if self.select_for_folder_depth:
            highest_dir_separators = 0
            for f in best_candidates:
                separator_count = len(f.split(self.dir_separator_char)) - 1
                if separator_count > highest_dir_separators:
                    highest_dir_separators = separator_count
            best_candidates = list(filter(lambda f: len(f.split(self.dir_separator_char)) - 1 == highest_dir_separators, best_candidates))
            if len(best_candidates) == 1:
                return best_candidates[0]
        candidate_dict = defaultdict(int)
        for f in best_candidates:
            basename = os.path.basename(f)
            index_not_present = DuplicateRemover.INDEX_REGEX.search(basename) is None
            normal_file_chars = DuplicateRemover.NORMAL_FILE_CHARS_REGEX.match(basename) is not None
            starts_with_alpha = DuplicateRemover.STARTS_WITH_ALPHA_REGEX.search(basename) is not None
            if index_not_present and normal_file_chars and starts_with_alpha:
                return f
            count = sum([index_not_present, normal_file_chars, starts_with_alpha])
            candidate_dict[f] = count
        highest_count = max(candidate_dict.values())
        for f, count in candidate_dict.items():
            if count == highest_count:
                return f
        raise Exception("Impossible case")

    def save_report(self):
        # Create a list of tuples with best duplicate file and its duplicates
        duplicates_list = [(self.select_best_duplicate(files), files) for files in self.duplicates.values()]
        # Sort the list based on the filename of the best duplicate
        sorted_duplicates_list = sorted(duplicates_list, key=lambda x: os.path.basename(x[0]))
        # Create a report
        report_path = os.path.join(self.source_folder, 'duplicates_report.txt')
        with open(report_path, 'w') as f:
            f.write("DUPLICATES REPORT FOR DIR: " + self.source_folder + "\n")
            for best, duplicates in sorted_duplicates_list:
                f.write(f'Best duplicate: {best}\n')
                f.write('Duplicates to be removed:\n')
                for duplicate in duplicates:
                    if duplicate != best:
                        f.write(f'{duplicate}\n')
                f.write('\n')

def dups_main(directory_path=".", select_deepest=False, match_dir=False, recursive=True, exclude_dir_string=""):
    if exclude_dir_string and exclude_dir_string != "":
        exclude_dirs = exclude_dir_string.split(",")
    else:
        exclude_dirs = []
    remover = DuplicateRemover(directory_path, select_for_folder_depth=select_deepest, match_dir=match_dir, recursive=recursive, exclude_dirs=exclude_dirs)

    if remover.find_duplicates():
        remover.handle_duplicates(testing=True)
        confirm = input("Confirm duplicate removal (Y/n): ")
        if confirm.lower() == "y":
            remover.handle_duplicates(testing=False)
            return
        print("No change made.")
        confirm = input("Remove duplicates one by one? (Y/n): ")
        if confirm.lower() == "y":
            remover.handle_duplicates(testing=False, skip_confirm=False)
            return
        print("No change made.")
        confirm_report = input("Save duplicates report? (Y/n): ")
        if confirm_report.lower() == "y":
            remover.save_report()
    else:
        print("No duplicates found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Remove duplicate files in a directory.')
    parser.add_argument('dir', help='Directory to search for duplicate files')
    args = parser.parse_args()
    dups_main(args.dir)

