"""
UTF-8 / Unicode escapes: codepoint (``\\U`` hex per character) or UTF-8 percent (``hex`` / ``octet``).

Parity with ``ds:unicode`` from dev_scripts (``commands.sh`` + ``xxd``/``bc`` pipeline), without those tools.
"""
from __future__ import annotations

import sys
from typing import Literal

Mode = Literal["codepoint", "hex", "octet"]


def format_unicode(text: str, mode: Mode = "codepoint") -> str:
    """
    ``codepoint``: ``\\U`` + uppercase minimal hex per Unicode scalar (e.g. ``\\U63``, ``\\U1F63C``).

    ``hex`` / ``octet``: for each character, ``%`` + concatenated uppercase hex of its UTF-8 bytes
    (e.g. ASCII ``%63``, emoji ``%F09F98BC``), matching ``ds:unicode`` / ``xxd`` output.
    """
    if mode == "codepoint":
        return "".join(f"\\U{ord(ch):X}" for ch in text)
    if mode in ("hex", "octet"):
        out: list[str] = []
        for ch in text:
            raw = ch.encode("utf-8")
            blob = "".join(f"{b:02X}" for b in raw)
            out.append(f"%{blob}")
        return "".join(out)
    raise ValueError(f"unknown mode: {mode!r}")


def run_unicode(argv: tuple[str, ...] | list[str]) -> None:
    """CLI entry: ``[]`` → stdin; ``[mode]`` if mode is codepoint|hex|octet → stdin; else ``[text]`` or ``[text, mode]``."""
    import click

    known: frozenset[str] = frozenset({"codepoint", "hex", "octet"})
    args = tuple(argv)

    if not args:
        raw = sys.stdin.read()
        mode: Mode = "codepoint"
    elif len(args) == 1:
        if args[0] in known:
            raw = sys.stdin.read()
            mode = args[0]  # type: ignore[assignment]
        else:
            raw = args[0]
            mode = "codepoint"
    else:
        raw = args[0]
        m = args[1]
        if m not in known:
            raise click.ClickException(f"conversion must be one of {sorted(known)}, got {m!r}")
        mode = m  # type: ignore[assignment]

    text = raw.rstrip("\n\r")
    click.echo(format_unicode(text, mode), nl=True)


if __name__ == "__main__":
    run_unicode(tuple(sys.argv[1:]))
