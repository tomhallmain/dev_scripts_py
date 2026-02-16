import json
import os
import shutil
import threading


class AppInfoCache:
    CACHE_LOC = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), "app_info_cache.json")
    INFO_KEY = "info"
    HISTORY_KEY = "run_history"
    MAX_HISTORY_ENTRIES = 1000
    DIRECTORIES_KEY = "directories"
    NUM_BACKUPS = 4

    def __init__(self, debug=False):
        self._lock = threading.RLock()
        self._debug = debug
        self._cache = {
            AppInfoCache.INFO_KEY: {},
            AppInfoCache.HISTORY_KEY: [],
            AppInfoCache.DIRECTORIES_KEY: {},
        }
        self.load()
        self.validate()

    def _debug_print(self, message):
        if self._debug:
            print(f"[AppInfoCache] {message}")

    def wipe_instance(self):
        with self._lock:
            self._cache = {
                AppInfoCache.INFO_KEY: {},
                AppInfoCache.HISTORY_KEY: [],
                AppInfoCache.DIRECTORIES_KEY: {},
            }

    def store(self):
        """Persist cache to JSON file. Raises on failure."""
        with self._lock:
            try:
                cache_json = json.dumps(self._cache, ensure_ascii=False, indent=2)
            except Exception as e:
                raise Exception("Error serializing application cache") from e

            try:
                with open(AppInfoCache.CACHE_LOC, "w", encoding="utf-8") as f:
                    f.write(cache_json)
                self._debug_print(f"Cache stored to {AppInfoCache.CACHE_LOC}")
            except Exception as e:
                raise Exception(f"Error writing cache to {AppInfoCache.CACHE_LOC}") from e

    def load(self):
        """Load cache from JSON file, falling back to backups if the main file is corrupt."""
        with self._lock:
            cache_paths = [self.CACHE_LOC] + self._get_backup_paths()
            any_exist = any(os.path.exists(p) for p in cache_paths)

            if not any_exist:
                self._debug_print(f"No cache file found at {self.CACHE_LOC}, starting fresh")
                return

            for path in cache_paths:
                if not os.path.exists(path):
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self._cache = json.load(f)

                    if path == self.CACHE_LOC:
                        rotated = self._rotate_backups()
                        self._debug_print(f"Loaded cache from {path}" + (f", rotated {rotated} backup(s)" if rotated else ""))
                    else:
                        self._debug_print(f"Loaded cache from backup: {path}")
                    return
                except Exception as e:
                    self._debug_print(f"Failed to load cache from {path}: {e}")
                    continue

            self._debug_print("All cache files unreadable, starting fresh")

    def validate(self):
        """Ensure the cache has the expected top-level structure."""
        with self._lock:
            for key, factory in (
                (AppInfoCache.INFO_KEY, dict),
                (AppInfoCache.HISTORY_KEY, list),
                (AppInfoCache.DIRECTORIES_KEY, dict),
            ):
                if key not in self._cache or not isinstance(self._cache[key], factory):
                    self._cache[key] = factory()

    # ----- info helpers -----

    def set(self, key, value):
        with self._lock:
            self._cache[AppInfoCache.INFO_KEY][key] = value

    def get(self, key, default_val=None):
        with self._lock:
            return self._cache.get(AppInfoCache.INFO_KEY, {}).get(key, default_val)

    # ----- directory-scoped helpers -----

    def set_directory(self, directory, key, value):
        with self._lock:
            directory = self.normalize_directory_key(directory)
            if not directory or not directory.strip():
                raise ValueError(f"Invalid directory for set_directory(key={key!r}, value={value!r})")
            dirs = self._cache[AppInfoCache.DIRECTORIES_KEY]
            dirs.setdefault(directory, {})[key] = value

    def get_directory(self, directory, key, default_val=None):
        with self._lock:
            directory = self.normalize_directory_key(directory)
            return self._cache.get(AppInfoCache.DIRECTORIES_KEY, {}).get(directory, {}).get(key, default_val)

    # ----- history helpers -----

    def add_history(self, entry):
        with self._lock:
            history = self._cache[AppInfoCache.HISTORY_KEY]
            history.append(entry)
            if len(history) > AppInfoCache.MAX_HISTORY_ENTRIES:
                self._cache[AppInfoCache.HISTORY_KEY] = history[-AppInfoCache.MAX_HISTORY_ENTRIES:]

    def get_history(self):
        with self._lock:
            return list(self._cache.get(AppInfoCache.HISTORY_KEY, []))

    # ----- utilities -----

    @staticmethod
    def normalize_directory_key(directory):
        return os.path.normpath(os.path.abspath(directory))

    def export_as_json(self, json_path=None):
        """Export the cache to an arbitrary JSON path (pretty-printed)."""
        if json_path is None:
            json_path = AppInfoCache.CACHE_LOC
        with self._lock:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        return json_path

    # ----- backup rotation -----

    def _get_backup_paths(self):
        base = self.CACHE_LOC
        return [f"{base}.bak{'' if i == 1 else i}" for i in range(1, self.NUM_BACKUPS + 1)]

    def _rotate_backups(self):
        backup_paths = self._get_backup_paths()
        rotated = 0

        if os.path.exists(backup_paths[-1]):
            os.remove(backup_paths[-1])

        for i in range(len(backup_paths) - 1, 0, -1):
            if os.path.exists(backup_paths[i - 1]):
                shutil.copy2(backup_paths[i - 1], backup_paths[i])
                rotated += 1

        if os.path.exists(self.CACHE_LOC):
            shutil.copy2(self.CACHE_LOC, backup_paths[0])

        return rotated


app_info_cache = AppInfoCache()
