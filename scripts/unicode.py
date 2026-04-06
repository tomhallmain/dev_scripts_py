"""
UTF-8 / Unicode escapes: codepoint (``\\U`` hex per character) or UTF-8 percent (``hex`` / ``octet``).

Parity with ``ds:unicode`` from dev_scripts (``commands.sh`` + ``xxd``/``bc`` pipeline), without those tools.
"""
from __future__ import annotations

import sys
from typing import Literal

from scripts.cli_arg_parse_utils import CliArgContext

Mode = Literal["codepoint", "hex", "octet"]

KNOWN_MODES = frozenset({"codepoint", "hex", "octet"})


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


def run_unicode(ctx: CliArgContext) -> None:
    """CLI entry: ``[]`` → stdin; ``[mode]`` if mode is codepoint|hex|octet → stdin; else ``[text]`` or ``[text, mode]``."""
    import click

    args = ctx.args

    if not args:
        raw = ctx.stdin_text
        mode: Mode = "codepoint"
    elif len(args) == 1:
        if args[0] in KNOWN_MODES:
            raw = ctx.stdin_text
            mode = args[0]  # type: ignore[assignment]
        else:
            raw = args[0]
            mode = "codepoint"
    else:
        raw = args[0]
        m = args[1]
        if m not in KNOWN_MODES:
            raise click.ClickException(
                f"conversion must be one of {sorted(KNOWN_MODES)}, got {m!r}"
            )
        mode = m  # type: ignore[assignment]

    text = raw.rstrip("\n\r")
    click.echo(format_unicode(text, mode), nl=True)
