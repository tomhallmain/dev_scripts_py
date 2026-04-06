"""
Copy UTF-8 text to the system clipboard (``data | ds . cp``).

Shell reference: ``LC_CTYPE=UTF-8 pbcopy`` on macOS.
"""
from __future__ import annotations

import base64
import os
import platform
import shutil
import subprocess
import sys
import click


def copy_utf8_text_to_clipboard(text: str) -> None:
    """Write ``text`` to the clipboard as UTF-8 (best-effort per OS)."""
    system = platform.system()
    if system == "Darwin":
        _copy_darwin(text)
    elif system == "Windows":
        _copy_windows(text)
    else:
        _copy_linux(text)


def copy_stdin_to_clipboard() -> None:
    """Read all of stdin (decoded UTF-8) and copy to the clipboard."""
    data = sys.stdin.read()
    copy_utf8_text_to_clipboard(data)


def _copy_darwin(text: str) -> None:
    env = dict(os.environ)
    env.setdefault("LC_CTYPE", "UTF-8")
    subprocess.run(
        ["pbcopy"],
        input=text.encode("utf-8"),
        env=env,
        check=True,
    )


def _copy_windows(text: str) -> None:
    """Use PowerShell ``Set-Clipboard`` so arbitrary UTF-8 is safe (avoids ``clip.exe`` code pages)."""
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    ps = (
        f'$raw = [System.Convert]::FromBase64String("{b64}"); '
        f'$s = [System.Text.Encoding]::UTF8.GetString($raw); '
        f"Set-Clipboard -Value $s"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        check=True,
        capture_output=True,
        text=True,
    )


def _copy_linux(text: str) -> None:
    data = text.encode("utf-8")
    for name, extra in (
        ("wl-copy", []),
        ("xclip", ["-selection", "clipboard"]),
        ("xsel", ["--clipboard", "--input"]),
    ):
        exe = shutil.which(name)
        if not exe:
            continue
        subprocess.run([exe, *extra], input=data, check=True)
        return
    raise click.ClickException(
        "No clipboard helper found. Install wl-copy, xclip, or xsel, or use macOS/Windows."
    )
