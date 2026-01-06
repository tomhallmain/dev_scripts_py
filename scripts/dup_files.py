import argparse
from collections import defaultdict
import hashlib
import os
import pickle
import re
import sys

from .utils import Utils

class DuplicateRemover:
    INDEX_REGEX = re.compile(r'\s\(\d+\)(.[a-z0-9]{1,5})?$') # regex to match files with indices like " (1)" or " (2)"
    NORMAL_FILE_CHARS_REGEX = re.compile(r'^[\w_\-. ]+$')
    STARTS_WITH_ALPHA_REGEX = re.compile(r'^[A-Za-z]')

    def __init__(self, source_folder, select_for_folder_depth=False, match_dir=False,
                 recursive=True, exclude_dirs=[], preferred_delete_dirs=[],
                 save_filedata=False, no_overwrite_filedata=True):
        # Strip any trailing quotes from the path
        self.source_folder = os.path.abspath(source_folder.rstrip('"'))
        if not os.path.isdir(self.source_folder):
            raise Exception("Invalid source folder provided: " + self.source_folder)
#        print(self.source_folder)
        self.file_dict, self.is_stored_filedata = self._load_file_data()
        self.duplicates = {}
        self.select_for_folder_depth = select_for_folder_depth
        self.save_filedata = save_filedata
        self.overwrite_filedata = not no_overwrite_filedata
        self.match_dir = match_dir
        self.recursive = recursive
        self.dir_separator_char = "\\" if sys.platform.startswith("win") else "/"
        self.exclude_dirs = []
        self.preferred_delete_dirs = []
        self.skip_exclusion_check = len(exclude_dirs) == 0
        if not self.skip_exclusion_check:
            print("Excluding directories from duplicates check:")
            for d in exclude_dirs:
                if os.path.abspath(d) == d:
                    full_path = d
                else:
                    full_path = os.path.join(os.path.abspath(self.source_folder), d)
                if not os.path.isdir(full_path):
                    raise Exception("Invalid exclude directory: " + d)
                print(full_path)
                self.exclude_dirs.append(full_path)
        if len(preferred_delete_dirs) > 0:
            print("Preferring directories for deletion:")
            for d in preferred_delete_dirs:
                if os.path.abspath(d) == d:
                    full_path = d
                else:
                    full_path = os.path.join(os.path.abspath(self.source_folder), d)
                if not os.path.isdir(full_path):
                    raise Exception("Invalid preferred delete directory: " + d)
                print(full_path)
                self.preferred_delete_dirs.append(full_path)

    def run(self):
        print(f"Running duplicate removal for: {self.source_folder}")
        if self.find_duplicates():
            self.handle_duplicates(testing=True)
            confirm = input("Confirm all duplicates removal (Y/n): ")
            if confirm.lower() == "y":
                self.handle_duplicates(testing=False)
                self._store_file_data()
                return
            print("No change made.")
            confirm = input("Remove duplicates with confirmation one by one? (Y/n): ")
            if confirm.lower() == "y":
                self.handle_duplicates(testing=False, skip_confirm=False)
                self._store_file_data()
                return
            print("No change made.")
            confirm_report = input("Save duplicates report? (Y/n): ")
            if confirm_report.lower() == "y":
                self.save_report()
        else:
            print("No duplicates found.")
        self._store_file_data()

    def _load_file_data(self):
        try:
            path = os.path.join(os.path.abspath(self.source_folder), "file_data.pkl")
            with open(path, "rb") as f:
                file_data = pickle.load(f)
                print("Loaded file data.")
                return file_data, True
        except Exception:
            return {}, False

    def _store_file_data(self):
        if self.overwrite_filedata and self.save_filedata:
            path = os.path.join(os.path.abspath(self.source_folder), "file_data.pkl")
            pickle.dump(self.file_dict, open(path, "wb"))
            print(f"Stored file hash data: {path}")

    def _get_file_hash(self, file_path):
        hash_obj = hashlib.md5()
        with open(file_path, 'rb') as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def _is_excluded(self, file_path):
        for d in self.exclude_dirs:
            if file_path.startswith(d):
                return True
        return False

    def _gather_filedata(self):
        for foldername, subfolders, filenames in os.walk(self.source_folder):
            if not self.recursive and foldername != self.source_folder: # TODO better way to handle this
                continue
            for filename in filenames:
                file_path = os.path.normpath(os.path.join(foldername, filename))
                if (self.overwrite_filedata or not self.is_stored_filedata or file_path not in self.file_dict) and \
                        (self.skip_exclusion_check or not self._is_excluded(file_path)):
                    try:
                        self.file_dict[file_path] = self._get_file_hash(file_path)
                    except Exception: # FileNotFoundError is possible
                        pass
        self._store_file_data() # Save here just in case of an error during duplicate search

    def find_duplicates(self):
        self._gather_filedata()
        hash_dict = defaultdict(list)
        for filepath, _hash_ in self.file_dict.items():
            hash_dict[_hash_].append(filepath)
        self.duplicates = {k: v for k, v in hash_dict.items() if len(v) > 1}
        return self.has_duplicates()

    def has_duplicates(self):
        return len(self.duplicates) > 0

    def determine_duplicates(self, file_list):
        best_duplicate = self._select_best_duplicate(file_list)
        if best_duplicate is None:
            return None, []
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
            if (self.match_dir and len(duplicates_to_remove) == 0) or best_duplicate is None:
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
                    try:
                        os.remove(file_path)
                        print("Removed file: " + file_path)
                    except Exception: # FileNotFoundError
                        pass

    def _is_preferred_delete_file(self, file_path):
        for d in self.preferred_delete_dirs:
            if file_path == d or file_path.startswith(d):
                return True
        return False

    def _get_ctime_remove_stale_file_ref(self, filepath):
        try:
            return os.path.getctime(filepath)
        except Exception: # FileNotFoundError
            try:
                del self.file_dict[filepath]
            except KeyError:
                pass
            return None

    def _select_best_duplicate(self, file_list):
        filtered_list = list(file_list)
        # only keep files that are in the preferred delete dirs, unless there are none
        if len(self.preferred_delete_dirs) > 0:
            for f in filtered_list[:]:
                if self._is_preferred_delete_file(f):
                    filtered_list.remove(f)
            if len(filtered_list) == 1:
                return filtered_list[0]
            elif len(filtered_list) == 0:
                filtered_list = list(file_list)
        # sort the file_list by the creation time
        temp_dict = {}
        for f in filtered_list[:]:
            ctime = self._get_ctime_remove_stale_file_ref(f)
            if ctime is not None:
                temp_dict[f] = ctime
            else:
                filtered_list.remove(f)
        if len(filtered_list) == 1:
            return None
        filtered_list.sort(key=lambda f: temp_dict[f])
        best_candidates = filtered_list[:]
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
        duplicates_list = [(self._select_best_duplicate(files), files) for files in self.duplicates.values()]
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

def dups_main(directory_path=".", select_deepest=False, match_dir=False, recursive=True, 
              exclude_dir_string="", preferred_delete_dirs_string="", 
              save_filedata=False, no_overwrite_filedata=True):
    exclude_dirs = Utils.get_list_from_string(exclude_dir_string)
    preferred_delete_dirs = Utils.get_list_from_string(preferred_delete_dirs_string)
    remover = DuplicateRemover(directory_path, select_for_folder_depth=select_deepest,
                               match_dir=match_dir, recursive=recursive, 
                               exclude_dirs=exclude_dirs, preferred_delete_dirs=preferred_delete_dirs,
                               save_filedata=save_filedata, no_overwrite_filedata=no_overwrite_filedata)
    remover.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Remove duplicate files in a directory.')
    parser.add_argument('dir', help='Directory to search for duplicate files')
    args = parser.parse_args()
    dups_main(args.dir)

