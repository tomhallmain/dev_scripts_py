#!/usr/bin/env python3
"""
Script to check which conda environments (and system Python) have a given set of packages installed.
"""

import sys
import subprocess
import os
from pathlib import Path

try:
    from packaging import version as packaging_version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False

# Configuration: Set your miniconda/anaconda installation path here
# Common locations:
# Windows: C:\Users\<username>\miniconda or C:\Users\<username>\anaconda
# Linux/Mac: ~/miniconda3 or ~/anaconda3
CONDA_BASE_PATH = os.path.expanduser("~/miniconda")  # Change this to your conda installation path

# Alternative: Try to auto-detect conda
if os.name == 'nt':  # Windows
    possible_paths = [
        os.path.expanduser("~/miniconda3"),
        os.path.expanduser("~/anaconda3"),
        "C:/ProgramData/miniconda3",
        "C:/ProgramData/anaconda3",
    ]
else:  # Linux/Mac
    possible_paths = [
        os.path.expanduser("~/miniconda3"),
        os.path.expanduser("~/anaconda3"),
        "/opt/miniconda3",
        "/opt/anaconda3",
    ]

# Try to find conda
for path in possible_paths:
    conda_exe = os.path.join(path, "Scripts", "conda.exe") if os.name == 'nt' else os.path.join(path, "bin", "conda")
    if os.path.exists(conda_exe):
        CONDA_BASE_PATH = path
        break


UNKNOWN_VERSION = "<unknown>"  # Error brackets
STDLIB_VERSION = "(stdlib)"    # Implication brackets
MISSING_VERSION = "<missing>"  # Error brackets

# Cache for Python version lookups: python_minor_version -> python_version
_python_version_cache = {}

# Cache for standard library checks: (python_minor_version, package) -> bool
_stdlib_cache = {}


def get_python_version(python_exe):
    """Get Python version from executable."""
    # Check cache first
    if python_exe in _python_version_cache:
        return _python_version_cache[python_exe]
    
    try:
        result = subprocess.run(
            [python_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            version_str = result.stdout.strip()
            # Extract version number (e.g., "Python 3.10.5" -> "3.10.5")
            import re
            match = re.search(r'(\d+\.\d+\.\d+)', version_str)
            if match:
                version = match.group(1)
                _python_version_cache[python_exe] = version
                return version
            match = re.search(r'(\d+\.\d+)', version_str)
            if match:
                version = match.group(1)
                _python_version_cache[python_exe] = version
                return version
            _python_version_cache[python_exe] = version_str
            return version_str
    except:
        pass
    _python_version_cache[python_exe] = UNKNOWN_VERSION
    return UNKNOWN_VERSION


def is_standard_library(python_exe, package):
    """Check if a package is part of Python's standard library."""
    # Check cache first - use Python minor version for cache key
    # since stdlib status depends on Python minor version, not patch version
    python_version = get_python_version(python_exe)
    # Extract major.minor version (e.g., "3.10" from "3.10.5")
    import re
    major_minor_match = re.search(r'(\d+\.\d+)', python_version)
    python_minor_version = major_minor_match.group(1) if major_minor_match else python_version
    cache_key = (python_minor_version, package)
    if cache_key in _stdlib_cache:
        return _stdlib_cache[cache_key]
    
    try:
        check_code = f"""
import {package}
import sys
import os
try:
    mod_file = getattr({package}, '__file__', None)
    if mod_file is None:
        # Built-in modules have no __file__
        print('stdlib')
    else:
        # Check if module is in standard library paths (not in site-packages)
        mod_dir = os.path.dirname(os.path.abspath(mod_file))
        stdlib_paths = [os.path.abspath(p) for p in sys.path 
                       if p and 'site-packages' not in p and 'dist-packages' not in p]
        for stdlib_path in stdlib_paths:
            if mod_dir.startswith(stdlib_path):
                print('stdlib')
                exit(0)
        print('not_stdlib')
except Exception as e:
    # If we can't determine, assume it's not stdlib to be safe
    print('not_stdlib')
"""
        result = subprocess.run(
            [python_exe, "-c", check_code],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and 'stdlib' in result.stdout:
            _stdlib_cache[cache_key] = True
            return True
    except:
        pass
    _stdlib_cache[cache_key] = False
    return False


def check_packages_in_python(python_exe, packages):
    """Check which packages are installed in a given Python installation."""
    installed = {}
    missing = []
    
    # Get Python version for cache lookup
    python_version = get_python_version(python_exe)
    import re
    major_minor_match = re.search(r'(\d+\.\d+)', python_version)
    python_minor_version = major_minor_match.group(1) if major_minor_match else python_version
    
    for package in packages:
        # Check if package is already known to be standard library
        stdlib_cache_key = (python_minor_version, package)
        if stdlib_cache_key in _stdlib_cache and _stdlib_cache[stdlib_cache_key]:
            # Skip import check - standard library modules are always available
            installed[package] = STDLIB_VERSION
            continue
        
        try:
            # Try importing the package
            result = subprocess.run(
                [python_exe, "-c", f"import {package}; print('OK')"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Get version if possible
                try:
                    version_result = subprocess.run(
                        [python_exe, "-c", f"import {package}; print(getattr({package}, '__version__', 'unknown'))"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    version = version_result.stdout.strip() if version_result.returncode == 0 else UNKNOWN_VERSION
                    
                    # If version is unknown, check if it's a standard library module
                    if version == UNKNOWN_VERSION:
                        if is_standard_library(python_exe, package):
                            version = STDLIB_VERSION
                except:
                    # Check if it's standard library even if version check failed
                    if is_standard_library(python_exe, package):
                        version = STDLIB_VERSION
                    else:
                        version = UNKNOWN_VERSION
                installed[package] = version
            else:
                missing.append(package)
        except Exception as e:
            missing.append(package)
    
    return installed, missing


def parse_version(version_str):
    """Parse version string for comparison. Returns tuple for sorting."""
    if version_str == UNKNOWN_VERSION:
        return (0, 0, 0, "")
    if version_str == STDLIB_VERSION:
        # Standard library should sort after all versioned packages
        # Use a very high version number so it appears at the end
        return (999999, 999999, 999999, STDLIB_VERSION)
    try:
        # Try using packaging library if available
        if HAS_PACKAGING:
            v = packaging_version.parse(version_str)
            return (v.major, v.minor, v.micro, "")
    except:
        pass
    
    # Fallback: try to extract numbers
    import re
    parts = re.findall(r'\d+', version_str)
    if parts:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        micro = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, micro, version_str)
    return (0, 0, 0, version_str)


def sort_key_all(env_data, packages):
    """Sort key for environments with ALL packages."""
    name, py_version, installed = env_data
    # Get package versions in order of packages list
    package_versions = [installed.get(pkg, UNKNOWN_VERSION) for pkg in packages]
    # Create sort tuple: (package versions descending, python version descending, name)
    # For descending order, negate the numeric values
    version_tuples = [parse_version(v) for v in package_versions]
    py_version_tuple = parse_version(py_version)
    # Negate numeric parts for descending order (but keep string parts for tie-breaking)
    negated_versions = [(-major, -minor, -micro, suffix) for major, minor, micro, suffix in version_tuples]
    negated_py = (-py_version_tuple[0], -py_version_tuple[1], -py_version_tuple[2], py_version_tuple[3])
    return tuple(negated_versions) + (negated_py, name)


def sort_key_some(env_data, packages):
    """Sort key for environments with SOME packages."""
    name, py_version, installed, count = env_data
    # Get package versions in order of packages list
    package_versions = [installed.get(pkg, UNKNOWN_VERSION) for pkg in packages]
    # Create sort tuple: (count descending, package versions descending, python version descending, name)
    version_tuples = [parse_version(v) for v in package_versions]
    py_version_tuple = parse_version(py_version)
    # Negate numeric parts for descending order
    negated_versions = [(-major, -minor, -micro, suffix) for major, minor, micro, suffix in version_tuples]
    negated_py = (-py_version_tuple[0], -py_version_tuple[1], -py_version_tuple[2], py_version_tuple[3])
    return (-count,) + tuple(negated_versions) + (negated_py, name)


def print_table(headers, rows, col_widths=None):
    """Print a formatted table."""
    if not rows:
        return
    
    # Calculate column widths if not provided
    if col_widths is None:
        col_widths = [max(len(str(row[i])) if i < len(row) else 0 for row in rows + [headers]) 
                        for i in range(len(headers))]
        col_widths = [max(w, len(h)) for w, h in zip(col_widths, headers)]
    
    # Print header
    header_row = " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    print(header_row)
    print("-" * len(header_row))
    
    # Print rows
    for row in rows:
        row_str = " | ".join(str(r).ljust(w) if i < len(col_widths) else str(r) 
                            for i, (r, w) in enumerate(zip(row, col_widths)))
        print(row_str)


def get_conda_environments(conda_base_path):
    """Get list of conda environments."""
    if not os.path.exists(conda_base_path):
        return []
    
    envs_dir = os.path.join(conda_base_path, "envs")
    if not os.path.exists(envs_dir):
        return []
    
    environments = []
    for item in os.listdir(envs_dir):
        env_path = os.path.join(envs_dir, item)
        if os.path.isdir(env_path):
            python_exe = os.path.join(env_path, "python.exe") if os.name == 'nt' else os.path.join(env_path, "bin", "python")
            if os.path.exists(python_exe):
                environments.append((item, python_exe))
    
    return environments


def get_system_python():
    """Get system Python executable."""
    # Try python3 first, then python
    for cmd in ['python3', 'python']:
        try:
            result = subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return cmd, result.stdout.strip()
        except:
            continue
    return None, None


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_packages.py <package1> [package2] [package3] ...")
        print("\nExample:")
        print("  python check_packages.py sentence_transformers scikit-learn numpy")
        sys.exit(1)
    
    packages = sys.argv[1:]
    
    print("=" * 80)
    print("PACKAGE CHECKER")
    print("=" * 80)
    print(f"\nChecking for packages: {', '.join(packages)}")
    print(f"Conda base path: {CONDA_BASE_PATH}")
    print()
    
    results = []
    
    # Check system Python
    print("=" * 80)
    print("SYSTEM PYTHON")
    print("=" * 80)
    python_cmd, python_version_str = get_system_python()
    if python_cmd:
        python_version = get_python_version(python_cmd)
        print(f"Python: {python_cmd} ({python_version})")
        installed, missing = check_packages_in_python(python_cmd, packages)
        results.append(("System Python", python_cmd, python_version, installed, missing))
        
        if installed:
            print("\nInstalled packages:")
            for pkg, version in installed.items():
                print(f"  ✓ {pkg} ({version})")
        if missing:
            print("\nMissing packages:")
            for pkg in missing:
                print(f"  ✗ {pkg}")
        if not installed and not missing:
            print("  (Unable to check packages)")
    else:
        print("  System Python not found")
    
    # Check conda environments
    print("\n" + "=" * 80)
    print("CONDA ENVIRONMENTS")
    print("=" * 80)
    
    if not os.path.exists(CONDA_BASE_PATH):
        print(f"\nConda installation not found at: {CONDA_BASE_PATH}")
        print("Please update CONDA_BASE_PATH at the top of this script.")
    else:
        environments = get_conda_environments(CONDA_BASE_PATH)
        
        if not environments:
            print("\nNo conda environments found.")
        else:
            print(f"\nFound {len(environments)} conda environment(s):\n")
            
            for env_name, python_exe in environments:
                print(f"Environment: {env_name}")
                python_version = get_python_version(python_exe)
                print(f"  Python: {python_exe} ({python_version})")
                
                installed, missing = check_packages_in_python(python_exe, packages)
                results.append((env_name, python_exe, python_version, installed, missing))
                
                if installed:
                    print("  Installed packages:")
                    for pkg, version in installed.items():
                        print(f"    ✓ {pkg} ({version})")
                if missing:
                    print("  Missing packages:")
                    for pkg in missing:
                        print(f"    ✗ {pkg}")
                if not installed and not missing:
                    print("  (Unable to check packages)")
                print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Find environments with all packages
    complete_envs = []
    partial_envs = []
    empty_envs = []
    
    for name, python_exe, python_version, installed, missing in results:
        if len(installed) == len(packages):
            complete_envs.append((name, python_version, installed))
        elif len(installed) > 0:
            partial_envs.append((name, python_version, installed, len(installed)))
        else:
            empty_envs.append(name)
    
    # Sort and display complete environments
    if complete_envs:
        print(f"\n✓ Environments with ALL packages ({len(complete_envs)}):")
        print()
        sorted_complete = sorted(complete_envs, key=lambda x: sort_key_all(x, packages))
        
        # Build table
        headers = ["Environment", "Python Version"] + [f"{pkg} Version" for pkg in packages]
        rows = []
        for name, py_version, installed in sorted_complete:
            row = [name, py_version] + [installed.get(pkg, MISSING_VERSION) for pkg in packages]
            rows.append(row)
        
        print_table(headers, rows)
    
    # Sort and display partial environments
    if partial_envs:
        print(f"\n⚠ Environments with SOME packages ({len(partial_envs)}):")
        print()
        sorted_partial = sorted(partial_envs, key=lambda x: sort_key_some(x, packages))
        
        # Build table
        headers = ["Environment", "Python Version", "Matches"] + [f"{pkg} Version" for pkg in packages]
        rows = []
        for name, py_version, installed, count in sorted_partial:
            row = [name, py_version, f"{count}/{len(packages)}"] + [installed.get(pkg, MISSING_VERSION) for pkg in packages]
            rows.append(row)
        
        print_table(headers, rows)
    
    if empty_envs:
        print(f"\n✗ Environments with NO packages ({len(empty_envs)}):")
        for env in empty_envs:
            print(f"  - {env}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if complete_envs:
        # Get names from sorted list
        env_names = [name for name, _, _ in sorted_complete]
        print(f"\nUse one of these environments: {', '.join(env_names)}")
    elif partial_envs:
        best_env, _, _, best_count = max(partial_envs, key=lambda x: x[3])
        print(f"\nBest match: {best_env} ({best_count}/{len(packages)} packages)")
        print(f"  Install missing packages with:")
        print(f"    conda activate {best_env}")
        for name, python_exe, python_version, installed, missing in results:
            if name == best_env:
                print(f"    pip install {' '.join(missing)}")
                break
    else:
        print("\nNo environments found with the required packages.")
        print("Create a new environment and install packages:")
        print("  conda create -n myenv python=3.10")
        print("  conda activate myenv")
        print(f"  pip install {' '.join(packages)}")


if __name__ == '__main__':
    main()
