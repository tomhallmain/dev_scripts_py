import argparse
from collections import defaultdict
import hashlib
import os
import re

class DuplicateRemover:
    def __init__(self, source_folder):
        self.source_folder = source_folder
        self.duplicates = {}

    def get_file_hash(self, file_path):
        hash_obj = hashlib.md5()
        with open(file_path, 'rb') as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def find_duplicates(self):
        file_dict = defaultdict(list)
        for foldername, subfolders, filenames in os.walk(self.source_folder):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                file_dict[self.get_file_hash(file_path)].append(file_path)
        self.duplicates = {k: v for k, v in file_dict.items() if len(v) > 1}
        return self.has_duplicates()

    def has_duplicates(self):
        return len(self.duplicates) > 0

    def handle_duplicates(self, testing):
        for file_list in self.duplicates.values():
            best_duplicate = self.select_best_duplicate(file_list)
            duplicates_to_remove = [f for f in file_list if f != best_duplicate]
            if testing:
                print("Keeping file: " + best_duplicate)
                print("Removing duplicate files: " + str(duplicates_to_remove))
            else:
                for file_path in duplicates_to_remove:
                    print("Removing file: " + file_path)
                    os.remove(file_path)

    def select_best_duplicate(self, file_list):
        # sort the file_list by the creation time
        file_list.sort(key=lambda x: os.path.getctime(x))
        # regex to match files with indices like " (1)" or " (2)"
        index_regex = re.compile(r'\s\(\d+\)$')
        # iterate over the sorted file_list to find the best
        for file in file_list:
            if not index_regex.search(file) and re.match(r'^[\w_\-. ]+$', file):
                return file
        for file in file_list:
            if not index_regex.search(file):
                return file
        return file_list[0]

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

def dups_main(directory_path="."):
    remover = DuplicateRemover(directory_path)
    
    if remover.find_duplicates():
        remover.handle_duplicates(testing=True)
        confirm = input("Confirm duplicate removal (Y/n): ")
        if confirm.lower() == "y":
            remover.handle_duplicates(testing=False)
        else:
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

