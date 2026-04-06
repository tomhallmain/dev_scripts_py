"""
Generic CLI helpers: :class:`CliArgContext`, predicate checks, and optional int parsing.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import InitVar, dataclass
from enum import Enum, auto
from typing import Callable, Optional, Sequence, Tuple

import click

from scripts.DataFile import DataFile
from scripts.utils import Utils


class PathCandidatePredicate(Enum):
    """How :attr:`CliArgContext.path_candidate` / :attr:`CliArgContext.resolved_path` are derived.

    - ``FIRST_ARG``: first positional is a path string (resolved in :meth:`CliArgContext.to_data_file`).
    - ``NONE``: no path from positionals; stdin when not a TTY.
    - ``TESTED_FIRST_ARG``: resolve the first positional; if it names an existing file, use that
      path (see :attr:`CliArgContext.resolved_path`); otherwise behave like ``NONE`` for file input.
    """

    FIRST_ARG = auto()
    NONE = auto()
    TESTED_FIRST_ARG = auto()


Predicate = Callable[["CliArgContext"], bool]
ArgCheck = Tuple[Predicate, str]

# ``extra_arg_warn`` for optional FILE + stdin commands: only the first positional may be FILE.
EXTRA_ARG_WARN_FIRST_FILE_ONLY: Tuple[int, str] = (
    1,
    "Warning: ignoring {extra} extra argument(s); only the first is used as FILE if present.",
)


def _resolved_path_tested_first_arg(args: Tuple[str, ...]) -> Optional[str]:
    """Resolve ``args[0]`` if it names an existing file; else ``None``."""
    if not args:
        return None
    raw = args[0]
    if not raw:
        return None
    try:
        resolved = Utils.resolve_relative_path(raw)
    except Exception:
        return None
    if os.path.isfile(resolved):
        return resolved
    return None


@dataclass(frozen=True)
class CliArgContext:
    """
    Positional ``args`` plus stdin snapshot. Build with :meth:`from_click` so ``isatty`` /
    ``read`` live in one place (callers pass only Click ``args``).

    Optional :class:`dataclasses.InitVar` parameters ``allowed_lengths`` and
    ``bad_length_message`` (see :meth:`from_click`) validate ``len(args)`` during construction.
    ``tested_first_arg_file_pair_rules`` enables subsep-style checks for
    :attr:`PathCandidatePredicate.TESTED_FIRST_ARG` (two or more positionals require a file as
    ``args[0]``; a single positional must not be only an existing file).
    ``extra_arg_warn`` is an optional ``(max_used_positionals, template)``: if
    ``len(args)`` exceeds the first value, a yellow stderr warning is printed using ``template``
    with ``{extra}`` set to the surplus count. For optional-``FILE``-or-stdin commands, pass
    :data:`EXTRA_ARG_WARN_FIRST_FILE_ONLY`.

    Optional ``field_separator`` / ``output_field_separator`` are applied when building a
    :class:`~scripts.DataFile.DataFile` via :meth:`to_data_file` (same meaning as in
    :class:`~scripts.DataFile.DataFile`).
    """

    args: Tuple[str, ...]
    stdin_text: Optional[str]
    path_candidate_rule: PathCandidatePredicate
    field_separator: Optional[str] = None
    output_field_separator: Optional[str] = None
    allowed_lengths: InitVar[Optional[Tuple[int, ...]]] = None
    bad_length_message: InitVar[Optional[str]] = None
    tested_first_arg_file_pair_rules: InitVar[bool] = False
    extra_arg_warn: InitVar[Optional[Tuple[int, str]]] = None

    def __post_init__(
        self,
        allowed_lengths: Optional[Tuple[int, ...]],
        bad_length_message: Optional[str],
        tested_first_arg_file_pair_rules: bool,
        extra_arg_warn: Optional[Tuple[int, str]],
    ) -> None:
        if extra_arg_warn is not None:
            max_used, template = extra_arg_warn
            if len(self.args) > max_used:
                n = len(self.args) - max_used
                click.echo(click.style(template.format(extra=n), fg="yellow"), err=True)

        if allowed_lengths is not None:
            n = len(self.args)
            if n not in allowed_lengths:
                if bad_length_message is None:
                    raise ValueError(
                        "bad_length_message is required when allowed_lengths is set"
                    )
                raise click.ClickException(bad_length_message)

        if (
            self.path_candidate_rule is PathCandidatePredicate.TESTED_FIRST_ARG
            and tested_first_arg_file_pair_rules
        ):
            rp = _resolved_path_tested_first_arg(self.args)
            n = len(self.args)
            if n >= 2:
                if rp is None:
                    raise click.ClickException(
                        f"first argument must be an existing file; {self.args[0]!r} is not"
                    )
            elif n == 1 and rp is not None:
                raise click.ClickException(
                    "one argument is the subsep pattern (read from stdin); "
                    "for a file use: FILE SUBSEP_PATTERN"
                )

    @classmethod
    def from_click(
        cls,
        args: Tuple[str, ...],
        *,
        path_rule: PathCandidatePredicate = PathCandidatePredicate.FIRST_ARG,
        allowed_lengths: Optional[Tuple[int, ...]] = None,
        bad_length_message: Optional[str] = None,
        tested_first_arg_file_pair_rules: bool = False,
        extra_arg_warn: Optional[Tuple[int, str]] = None,
        field_separator: Optional[str] = None,
        output_field_separator: Optional[str] = None,
    ) -> CliArgContext:
        """Build context from Click positionals; snapshot stdin when not a TTY.

        If ``allowed_lengths`` is set, ``len(args)`` must be one of those values or
        :exc:`click.ClickException` is raised with ``bad_length_message`` (required in that case).

        When ``tested_first_arg_file_pair_rules`` is true and ``path_rule`` is
        :attr:`PathCandidatePredicate.TESTED_FIRST_ARG`, construction enforces subsep-style
        rules: if there are two or more positionals, ``args[0]`` must name an existing file;
        a single positional must not be only an existing file (use ``FILE SUBSEP_PATTERN``).
        ``extra_arg_warn`` is forwarded to the dataclass initializer (see class docstring).
        ``field_separator`` / ``output_field_separator`` are stored for :meth:`to_data_file`.
        """
        stdin_text = None if sys.stdin.isatty() else sys.stdin.read()
        return cls(
            args=args,
            stdin_text=stdin_text,
            path_candidate_rule=path_rule,
            field_separator=field_separator,
            output_field_separator=output_field_separator,
            allowed_lengths=allowed_lengths,
            bad_length_message=bad_length_message,
            tested_first_arg_file_pair_rules=tested_first_arg_file_pair_rules,
            extra_arg_warn=extra_arg_warn,
        )

    @property
    def resolved_path(self) -> Optional[str]:
        """For :attr:`PathCandidatePredicate.TESTED_FIRST_ARG` only: resolved path if
        :attr:`args`\\ ``[0]`` names an existing file, else ``None``. Other rules: ``None``.
        """
        if self.path_candidate_rule is not PathCandidatePredicate.TESTED_FIRST_ARG:
            return None
        return _resolved_path_tested_first_arg(self.args)

    @property
    def path_candidate(self) -> Optional[str]:
        if self.path_candidate_rule is PathCandidatePredicate.NONE:
            return None
        if self.path_candidate_rule is PathCandidatePredicate.FIRST_ARG:
            return self.args[0] if self.args else None
        if self.path_candidate_rule is PathCandidatePredicate.TESTED_FIRST_ARG:
            return self.resolved_path
        raise NotImplementedError(self.path_candidate_rule)

    def shifted_arg(self, n: int) -> str:
        """``n``-th positional *after* an optional leading file path (``TESTED_FIRST_ARG`` only).

        If :attr:`resolved_path` is set, ``args[0]`` is treated as the file and logical index
        ``n`` maps to ``args[n + 1]``. If there is no resolved file, logical ``n`` maps to
        ``args[n]``.
        """
        if self.path_candidate_rule is not PathCandidatePredicate.TESTED_FIRST_ARG:
            raise ValueError("shifted_arg is only for PathCandidatePredicate.TESTED_FIRST_ARG")
        if n < 0:
            raise click.ClickException("shifted_arg index must be non-negative")
        shift = 1 if self.resolved_path else 0
        i = n + shift
        if i >= len(self.args):
            raise click.ClickException(
                f"not enough arguments for shifted_arg({n}): have {len(self.args)} positional(s)"
            )
        return self.args[i]

    def to_data_file(self) -> DataFile:
        """After command-specific checks: materialize :class:`~scripts.DataFile.DataFile`."""
        try:
            path = self.path_candidate
            if path and self.path_candidate_rule is PathCandidatePredicate.FIRST_ARG:
                path = Utils.resolve_relative_path(path)
            return DataFile.from_cli_file_or_stdin(
                path,
                self.stdin_text,
                field_separator=self.field_separator,
                output_field_separator=self.output_field_separator,
            )
        except Exception as e:
            raise click.ClickException(str(e)) from e


def apply_arg_predicates(ctx: CliArgContext, checks: Sequence[ArgCheck]) -> None:
    """Raise :exc:`click.ClickException` for the first ``predicate(ctx)`` that is true."""
    for predicate, message in checks:
        if predicate(ctx):
            raise click.ClickException(message)


def parse_non_negative_int_arg(
    s: Optional[str], *, default: int = 1, descriptor: Optional[str] = None
) -> int:
    """Parse an optional non-negative integer; ``None`` / ``""`` → ``default``."""
    if s is None or s == "":
        return default
    if not re.fullmatch(r"-?\d+", s):
        desc_prefix = (descriptor + " ") if descriptor else ""
        raise click.ClickException(f"{desc_prefix}must be an integer")
    n = int(s)
    if n < 0:
        desc_prefix = (descriptor + " ") if descriptor else ""
        raise click.ClickException(f"{desc_prefix}must be non-negative")
    return n
