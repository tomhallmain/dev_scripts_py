import argparse
from collections import defaultdict
import fnmatch
import os
from pathlib import Path

from .utils import Utils
from support.safe_file_ops import SafeFileOps

class FileMover:
    # File type tag mappings
    FILE_TYPE_TAGS = {
        '[video]': [
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v',
            '.mpg', '.mpeg', '.3gp', '.ogv', '.divx', '.vob', '.ts', '.mts'
        ],
        '[audio]': [
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus',
            '.aiff', '.au', '.ra', '.amr', '.ac3', '.dts', '.mpc', '.ape'
        ],
        '[image]': [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp',
            '.svg', '.ico', '.heic', '.heif', '.raw', '.cr2', '.nef', '.orf',
            '.sr2', '.psd', '.ai', '.eps', '.dng', '.xcf', '.sketch', '.icns',
            '.jp2', '.j2k', '.pcx', '.tga', '.exr', '.hdr'
        ],
        '[document]': [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt',
            '.ods', '.odp', '.rtf', '.txt', '.csv', '.tsv', '.pages', '.numbers',
            '.key', '.epub', '.mobi', '.azw', '.fb2'
        ],
        '[text]': [
            '.txt', '.md', '.markdown', '.rst', '.log', '.csv', '.tsv', '.json',
            '.xml', '.html', '.htm', '.css', '.js', '.py', '.java', '.cpp', '.c',
            '.h', '.hpp', '.sh', '.bat', '.ps1', '.yaml', '.yml', '.ini', '.cfg',
            '.conf', '.properties', '.sql', '.r', '.m', '.swift', '.go', '.rs',
            '.php', '.rb', '.pl', '.lua', '.scala', '.kt', '.dart', '.ts', '.jsx',
            '.tsx', '.vue', '.svelte'
        ],
        '[bin]': [
            '.exe', '.dll', '.so', '.dylib', '.bin', '.app', '.deb', '.rpm',
            '.pkg', '.msi', '.dmg', '.iso', '.img', '.zip', '.tar', '.gz',
            '.bz2', '.xz', '.7z', '.rar', '.cab', '.jar', '.war', '.ear',
            '.class', '.o', '.obj', '.a', '.lib'
        ]
    }

    def __init__(self, source, target, filter_pattern=None, copy_mode=False):
        """
        Initialize FileMover.
        
        Args:
            source: Source file or directory path
            target: Target file or directory path
            filter_pattern: Optional filter pattern (tag like [video] or glob like *.mp4)
            copy_mode: If True, copy files instead of moving them
        """
        self.source = os.path.abspath(Utils.resolve_relative_path(source))
        self.target = os.path.abspath(Utils.resolve_relative_path(target))
        self.filter_pattern = filter_pattern
        self.copy_mode = copy_mode
        
        # Validate source exists
        if not os.path.exists(self.source):
            raise Exception(f"Source path does not exist: {self.source}")
        
        self.source_is_dir = os.path.isdir(self.source)
        self.target_is_dir = os.path.isdir(self.target) if os.path.exists(self.target) else None
        self._source_norm = os.path.normcase(self.source)
        self._target_norm = os.path.normcase(self.target)
        self._source_equals_target_dir = (
            self.source_is_dir
            and self.target_is_dir
            and self._source_norm == self._target_norm
        )
        self._last_scan_count = None
        self._last_scan_files = None

    def _expand_tag(self, tag):
        """
        Expand a file type tag (e.g., [video]) to a list of extensions.
        
        Args:
            tag: Tag string like '[video]' or '[audio]'
            
        Returns:
            List of extensions (with dots) or None if tag not found
        """
        tag_lower = tag.lower()
        if tag_lower in self.FILE_TYPE_TAGS:
            return self.FILE_TYPE_TAGS[tag_lower]
        return None
    
    def _paths_equal(self, path_a, path_b):
        """Fast normalized path equality check without filesystem resolution."""
        return os.path.normcase(os.path.abspath(path_a)) == os.path.normcase(os.path.abspath(path_b))

    def _matches_filter(self, filepath):
        """
        Check if a file matches the filter pattern.
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if file matches filter, False otherwise
        """
        if not self.filter_pattern:
            return True
        
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()
        
        # Check if filter is a tag
        if self.filter_pattern.startswith('[') and self.filter_pattern.endswith(']'):
            tag_extensions = self._expand_tag(self.filter_pattern)
            if tag_extensions:
                return ext in tag_extensions
            # If tag not found, treat as literal pattern
            return fnmatch.fnmatch(filename, self.filter_pattern)
        
        # Check glob pattern
        if '*' in self.filter_pattern or '?' in self.filter_pattern:
            return fnmatch.fnmatch(filename, self.filter_pattern)
        
        # Check exact extension match
        if self.filter_pattern.startswith('.'):
            return ext == self.filter_pattern.lower()
        
        # Check if pattern matches filename
        return fnmatch.fnmatch(filename, self.filter_pattern)

    def _get_files_to_move(self):
        """
        Get list of files to move based on source and filter.
        
        Returns:
            List of file paths to move
        """
        files_to_move = []
        
        if not self.source_is_dir:
            # Single file
            if self.filter_pattern and not self._matches_filter(self.source):
                return []
            return [self.source]
        
        # Directory - collect matching files
        for root, dirs, filenames in os.walk(self.source):
            # In flatten-in-place mode, ignore files already in the root directory.
            if self._source_equals_target_dir and os.path.normcase(os.path.abspath(root)) == self._source_norm:
                continue
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if self._matches_filter(filepath):
                    files_to_move.append(filepath)
        
        return files_to_move
    
    def get_file_list(self, force_refresh=False):
        """
        Get the current file list that would be moved/copied.
        
        Args:
            force_refresh: If True, always perform a fresh scan
        
        Returns:
            Sorted list of absolute file paths
        """
        if not force_refresh and self._last_scan_files is not None:
            return list(self._last_scan_files)
        
        files_to_move = [os.path.abspath(path) for path in self._get_files_to_move()]
        files_to_move.sort(key=lambda path: os.path.normcase(path))
        self._last_scan_files = files_to_move
        self._last_scan_count = len(files_to_move)
        return list(files_to_move)
    
    def get_file_count(self, force_refresh=False):
        """
        Get the count of files that would be moved.
        
        Args:
            force_refresh: If True, always perform a fresh scan
        
        Returns:
            Number of files to move, or None if source doesn't exist
        """
        if not force_refresh and self._last_scan_count is not None:
            return self._last_scan_count
        
        files_to_move = self.get_file_list(force_refresh=force_refresh)
        return len(files_to_move)

    def _determine_target_path(self, source_file, files_to_move_count):
        """
        Determine the target path for a source file.
        
        Args:
            source_file: Path to source file
            files_to_move_count: Number of files that will be moved (for validation)
            
        Returns:
            Target path for the file
        """
        filename = os.path.basename(source_file)
        
        # Check if target exists and is a directory (check dynamically in case it was created)
        if os.path.exists(self.target) and os.path.isdir(self.target):
            return os.path.join(self.target, filename)
        
        # If source is a single file, target is the new file path
        if not self.source_is_dir:
            return self.target
        
        # If target doesn't exist, preserve relative path structure (target will be created as directory)
        if not os.path.exists(self.target):
            # Preserve directory structure relative to source
            rel_path = os.path.relpath(source_file, self.source)
            return os.path.join(self.target, rel_path)
        
        # Target exists but is not a directory - only valid if exactly one file matches filter
        if files_to_move_count == 1:
            return self.target
        
        # Multiple files but target is a file - error case
        raise Exception(f"Cannot move multiple files to a single file target: {self.target}")

    def _get_file_type_summary(self, files_to_move, successful_files=None, failed_files=None):
        """
        Generate a summary of files grouped by extension.
        
        Args:
            files_to_move: List of file paths
            successful_files: Optional set of successfully moved file paths
            failed_files: Optional dict of failed file paths to error messages
            
        Returns:
            Tuple of (summary_string, total_count, success_count, failure_count)
        """
        # Always initialize as empty collections to avoid None checks
        if successful_files is None:
            successful_files = set()
        if failed_files is None:
            failed_files = {}
        
        ext_counts = defaultdict(int)
        success_ext_counts = defaultdict(int)
        failed_ext_counts = defaultdict(int)
        
        for filepath in files_to_move:
            ext = os.path.splitext(filepath)[1].lower()
            if not ext:
                ext = "(no extension)"
            ext_counts[ext] += 1
            
            if filepath in successful_files:
                success_ext_counts[ext] += 1
            if filepath in failed_files:
                failed_ext_counts[ext] += 1
        
        # Sort by count (descending), then by extension name
        sorted_exts = sorted(ext_counts.items(), key=lambda x: (-x[1], x[0]))
        
        summary_lines = []
        show_details = len(successful_files) > 0 or len(failed_files) > 0
        for ext, count in sorted_exts:
            if show_details:
                success_count = success_ext_counts.get(ext, 0)
                failed_count = failed_ext_counts.get(ext, 0)
                summary_lines.append(f"  {ext}: {count} (success: {success_count}, failed: {failed_count})")
            else:
                summary_lines.append(f"  {ext}: {count}")
        
        total = len(files_to_move)
        success_count = len(successful_files)
        failure_count = len(failed_files)
        summary = "\n".join(summary_lines)
        
        return summary, total, success_count, failure_count

    def run(self, dry_run=False, show_summary=False):
        """
        Execute the move operation.
        
        Args:
            dry_run: If True, only print what would be moved without actually moving
            show_summary: If True, show summary instead of individual files (for dry_run)
        """
        files_to_move = self.get_file_list(force_refresh=True)
        
        if not files_to_move:
            if self.filter_pattern:
                print(f"No files found matching filter: {self.filter_pattern}")
            else:
                print("No files found to move.")
            return False
        
        # Show summary in dry_run mode if requested
        if dry_run and show_summary:
            summary, total, _, _ = self._get_file_type_summary(files_to_move)
            action = "copied" if self.copy_mode else "moved"
            print(f"Files to be {action} ({total} total):")
            print(summary)
            return True
        
        # If target doesn't exist and we're moving a directory, create target directory
        if self.source_is_dir and not os.path.exists(self.target):
            if not dry_run:
                os.makedirs(self.target, exist_ok=True)
            print(f"Target directory created: {self.target}")
        
        successful_files = set()
        failed_files = {}
        files_count = len(files_to_move)
        skipped_same_path_count = 0
        
        for source_file in files_to_move:
            target_path = self._determine_target_path(source_file, files_count)
            if self._paths_equal(source_file, target_path):
                skipped_same_path_count += 1
                continue
            
            # Create target directory if needed
            target_dir = os.path.dirname(target_path)
            if target_dir and not os.path.exists(target_dir):
                if not dry_run:
                    os.makedirs(target_dir, exist_ok=True)
            
            if not dry_run:
                if self.copy_mode:
                    success, error = SafeFileOps.copy(source_file, target_path)
                else:
                    success, error = SafeFileOps.move(source_file, target_path)
                
                if success:
                    successful_files.add(source_file)
                else:
                    failed_files[source_file] = error if error else "Unknown error"
        
        # Show summary after actual operation
        if not dry_run:
            summary, total, success_count, failure_count = self._get_file_type_summary(
                files_to_move, successful_files, failed_files
            )
            action = "Copy" if self.copy_mode else "Move"
            action_past = "copied" if self.copy_mode else "moved"
            print(f"{action} operation completed ({total} total):")
            print(summary)
            if skipped_same_path_count > 0:
                print(f"Skipped {skipped_same_path_count} file(s) already at target path.")
            if failure_count > 0:
                print(f"\nFailed {action_past} ({failure_count}):")
                for filepath, error in failed_files.items():
                    print(f"  {filepath}: {error}")
            # Operation changed filesystem state; invalidate cached pre-scan count.
            self._last_scan_count = None
            self._last_scan_files = None
        
        return True


def move_main(source, target, filter_pattern=None, threshold=20, copy=False):
    """
    Main function for moving or copying files/directories.
    
    Args:
        source: Source file or directory path
        target: Target file or directory path
        filter_pattern: Optional filter pattern (tag like [video] or glob like *.mp4)
        threshold: File count threshold for additional confirmation (default: 20)
        copy: If True, copy files instead of moving them
    """
    mover = FileMover(source, target, filter_pattern, copy_mode=copy)
    
    # Show summary of what would be moved/copied first
    has_files = mover.run(dry_run=True, show_summary=True)
    
    # Cancel if no files found
    if not has_files:
        action = "copy" if copy else "move"
        print(f"{action.capitalize()} operation cancelled - no files to {action}.")
        return
    
    def _format_display_path(path):
        if mover.source_is_dir:
            try:
                return os.path.relpath(path, mover.source)
            except ValueError:
                return path
        return path
    
    # Get file count for threshold check
    baseline_files = mover.get_file_list()
    file_count = len(baseline_files)
    
    # Ask for confirmation
    action = "copy" if copy else "move"
    confirm = input(f"\nConfirm {action} operation? (Y/n): ")
    if confirm.lower() != "y" and confirm.lower() != "":
        print(f"{action.capitalize()} operation cancelled.")
        return
    
    # Additional confirmation if file count meets or exceeds threshold
    if file_count >= threshold:
        print(f"\nWarning: {file_count} files to {action} (threshold: {threshold})")
        double_confirm = input("Are you sure you want to proceed? (Y/n): ")
        if double_confirm.lower() != "y":
            print(f"{action.capitalize()} operation cancelled.")
            return
    
    # Re-scan until the result is stable; if it changes, require re-confirmation.
    while True:
        refreshed_files = mover.get_file_list(force_refresh=True)
        if refreshed_files == baseline_files:
            break
        
        old_set = set(baseline_files)
        new_set = set(refreshed_files)
        removed_files = sorted(old_set - new_set, key=lambda path: os.path.normcase(path))
        added_files = sorted(new_set - old_set, key=lambda path: os.path.normcase(path))
        refreshed_count = len(refreshed_files)
        
        print(f"\nFile list changed since preview: {file_count} -> {refreshed_count}. Please re-confirm.")
        if removed_files:
            print("Removed from operation list:")
            for path in removed_files[:10]:
                print(f"  - {_format_display_path(path)}")
            if len(removed_files) > 10:
                print(f"  ... and {len(removed_files) - 10} more")
        if added_files:
            print("Added to operation list:")
            for path in added_files[:10]:
                print(f"  + {_format_display_path(path)}")
            if len(added_files) > 10:
                print(f"  ... and {len(added_files) - 10} more")
        
        if refreshed_count == 0:
            print(f"{action.capitalize()} operation cancelled - no files to {action}.")
            return
        
        file_count = refreshed_count
        baseline_files = refreshed_files
        reconfirm = input(f"Proceed with updated {action} set? (Y/n): ")
        if reconfirm.lower() != "y" and reconfirm.lower() != "":
            print(f"{action.capitalize()} operation cancelled.")
            return
        
        if file_count >= threshold:
            print(f"\nWarning: {file_count} files to {action} (threshold: {threshold})")
            double_confirm = input("Are you sure you want to proceed? (Y/n): ")
            if double_confirm.lower() != "y":
                print(f"{action.capitalize()} operation cancelled.")
                return
    
    # Perform the actual move/copy
    mover.run(dry_run=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Move files and directories with optional filtering.')
    parser.add_argument('source', help='Source file or directory')
    parser.add_argument('target', help='Target file or directory')
    parser.add_argument('--filter', '-f', help='Filter pattern (tag like [video] or glob like *.mp4)')
    args = parser.parse_args()
    move_main(args.source, args.target, args.filter)

