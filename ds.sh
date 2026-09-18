#!/bin/sh
# Unix wrapper for the ds CLI, the counterpart to ds.bat.
#
# ds.py takes the caller's working directory as its first argument and uses it
# to resolve relative paths, so that has to be passed explicitly rather than
# left to the process cwd.
#
# Put this on your PATH, by symlink or by copy:
#     ln -s "$PWD/ds.sh" ~/bin/ds
# Set DS_PYTHON to pick a specific interpreter; otherwise python3 is used when
# present, python otherwise. An activated conda or venv is picked up either way.

set -u

# Resolve this script's own directory, following symlinks, so a link on PATH
# still finds ds.py next to the real file.
self="$0"
while [ -L "$self" ]; do
    target="$(readlink "$self")"
    case "$target" in
        /*) self="$target" ;;
        *)  self="$(dirname "$self")/$target" ;;
    esac
done
ds_dir="$(cd "$(dirname "$self")" && pwd)"

python_bin="${DS_PYTHON:-}"
if [ -z "$python_bin" ]; then
    if command -v python3 >/dev/null 2>&1; then
        python_bin=python3
    else
        python_bin=python
    fi
fi

exec "$python_bin" "$ds_dir/ds.py" "$PWD" "$@"
