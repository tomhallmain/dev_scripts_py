"""
Generic CLI helpers: :class:`CliArgContext`, predicate checks, and optional int parsing.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import InitVar, dataclass, field
from enum import Enum, auto
from typing import Callable, List, Optional, Sequence, Tuple

import click

from scripts.DataFile import DataFile
from scripts.utils import Utils


class PathCandidatePredicate(Enum):
    """How :attr:`CliArgContext.path_candidate` / :attr:`CliArgContext.resolved_path` are derived.

    - ``FIRST_ARG``: first positional is a path string (resolved in :meth:`CliArgContext.to_data_file`).
    - ``NONE``: no path from positionals; stdin when not a TTY.
    - ``TESTED_FIRST_ARG``: resolve the first positional; if it names an existing file, use that
      path (see :attr:`CliArgContext.resolved_path`); otherwise behave like ``NONE`` for file input.
    - ``PAIR_CHAIN_OR_STDIN_SECOND``: join / diff style: **piped stdin** → ``args[0]`` must be an
      existing file (first dataset); the **second** dataset is **only** stdin; ``args[1:]`` are
      command options (even if they look like paths). **TTY** → greedily consume **leading**
      positionals that name existing files (two or more); those are pair-wise or chain inputs;
      stdin is not used. See :meth:`CliArgContext.resolve_join_style_paths`.
    """

    FIRST_ARG = auto()
    NONE = auto()
    TESTED_FIRST_ARG = auto()
    PAIR_CHAIN_OR_STDIN_SECOND = auto()


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


def _resolve_if_existing_file(raw: str) -> Optional[str]:
    """Resolve ``raw`` if it names an existing file; else ``None``."""
    if not raw:
        return None
    try:
        resolved = Utils.resolve_relative_path(raw)
    except Exception:
        return None
    if os.path.isfile(resolved):
        return resolved
    return None


def _greedy_leading_file_paths(args: Tuple[str, ...]) -> Tuple[List[str], int]:
    """Return ``(resolved_paths, count_consumed)`` for leading tokens that name existing files."""
    out: List[str] = []
    i = 0
    while i < len(args):
        r = _resolve_if_existing_file(args[i])
        if r is None:
            break
        out.append(r)
        i += 1
    return out, i


@dataclass
class JoinStylePathResolution:
    """Result of :meth:`CliArgContext.resolve_join_style_paths`.

    Holds resolved path strings; :meth:`materialize_data_files` fills :attr:`data_files` once the
    command knows ``field_separator`` and :attr:`~CliArgContext.stdin_text` (stdin-backed rows need
    the latter).

    - **Two or more leading files:** :attr:`path_paths` is **every** greedily resolved path (length
      ≥ 2). Stdin is ignored for pairing — this supports **N-way** pipelines (e.g. recursive
      ``join``) where the command folds over ``path_paths``. Pair-only commands call
      :meth:`require_exactly_two_inputs` before materializing.
    - **Pipe (stdin present, one file):** :attr:`path_paths` is a single file;
      :attr:`stdin_replaces_second_file` is True; the second input is stdin only.
      :attr:`remaining_args` is ``args[1:]``.
    """

    path_paths: Tuple[str, ...]
    stdin_replaces_second_file: bool
    remaining_args: Tuple[str, ...]
    check_same_file_pair: bool = True
    same_file_pair_message: str = "Files are the same!"
    data_files: Optional[List[DataFile]] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.check_same_file_pair and self.has_same_file_pair():
            raise click.ClickException(self.same_file_pair_message)

    def require_exactly_two_inputs(self, *, message: str) -> None:
        """Raise :exc:`click.ClickException` unless there are exactly two logical inputs.

        When :attr:`stdin_replaces_second_file` is true, one path plus stdin counts as two. When it
        is false, there must be exactly two resolved file paths (not three or more).
        """
        if self.stdin_replaces_second_file:
            return
        if len(self.path_paths) != 2:
            raise click.ClickException(message)

    def has_same_file_pair(self) -> bool:
        """
        Return whether the resolved pair points to the same on-disk file path.

        Only applies to two explicit file paths (non-stdin mode); stdin-second mode is always
        false because the second input does not come from a path.
        """
        if self.stdin_replaces_second_file:
            return False
        if len(self.path_paths) != 2:
            return False
        return self.path_paths[0] == self.path_paths[1]

    def materialize_data_files(
        self,
        *,
        stdin_text: Optional[str],
        field_separator: Optional[str] = None,
    ) -> List[DataFile]:
        """Open a :class:`~scripts.DataFile.DataFile` per resolved path, plus stdin when applicable.

        Sets :attr:`data_files` and returns the same list.

        - **``stdin_replaces_second_file``:** ``[df_first, df_stdin]`` (second may use a temp file).
        - **Otherwise:** one ``DataFile`` per :attr:`path_paths` entry (length 2, 3, …).

        Call :meth:`cleanup_stdin_backed_data_files` when done (or cleanup each stdin-backed file
        yourself).
        """
        if self.stdin_replaces_second_file:
            if len(self.path_paths) != 1:
                raise ValueError(
                    "stdin-as-second mode requires exactly one path in path_paths; got "
                    f"{len(self.path_paths)}"
                )
            self.data_files = [
                DataFile(self.path_paths[0], field_separator),
                DataFile(None, field_separator, stdin_text=stdin_text),
            ]
        else:
            self.data_files = [DataFile(p, field_separator) for p in self.path_paths]
        return self.data_files

    def cleanup_stdin_backed_data_files(self) -> None:
        """Call :meth:`~scripts.DataFile.DataFile.cleanup_temp_file` on stdin-backed instances."""
        if not self.data_files:
            return
        for df in self.data_files:
            if df.is_stdin:
                df.cleanup_temp_file()


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

    For :attr:`PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND`, use
    :meth:`resolve_join_style_paths` instead of :meth:`to_data_file`.
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
    no_arg_exception_text: InitVar[Optional[str]] = None

    def __post_init__(
        self,
        allowed_lengths: Optional[Tuple[int, ...]],
        bad_length_message: Optional[str],
        tested_first_arg_file_pair_rules: bool,
        extra_arg_warn: Optional[Tuple[int, str]],
        no_arg_exception_text: Optional[str],
    ) -> None:
        if no_arg_exception_text is not None and len(self.args) == 0:
            raise click.ClickException(no_arg_exception_text)

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
        no_arg_exception_text: Optional[str] = None,
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
            no_arg_exception_text=no_arg_exception_text,
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
        if self.path_candidate_rule is PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND:
            return None
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

    def resolve_join_style_paths(
        self,
        *,
        check_same_file_pair: bool = True,
        same_file_pair_message: str = "Files are the same!",
    ) -> JoinStylePathResolution:
        """Parse join / diff style inputs when :attr:`path_candidate_rule` is
        :attr:`PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND`.

        **Two or more leading files:** greedily consume path tokens that name existing files. If
        there are at least **two**, stdin is **ignored** (handles empty ``stdin`` from test runners
        and ``CliRunner``).

        **Otherwise, piped stdin** (``stdin_text`` is not ``None``): require exactly **one**
        leading file path; the second dataset is **only** stdin.

        **Otherwise (TTY, fewer than two files):** require a pipe or more paths — same error as
        before.
        """
        if self.path_candidate_rule is not PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND:
            raise ValueError(
                "resolve_join_style_paths requires path_candidate_rule "
                "PAIR_CHAIN_OR_STDIN_SECOND"
            )

        leading_paths, consumed = _greedy_leading_file_paths(self.args)

        if len(leading_paths) >= 2:
            return JoinStylePathResolution(
                path_paths=tuple(leading_paths),
                stdin_replaces_second_file=False,
                remaining_args=self.args[consumed:],
                check_same_file_pair=check_same_file_pair,
                same_file_pair_message=same_file_pair_message,
            )

        if self.stdin_text is not None:
            if len(leading_paths) != 1:
                raise click.ClickException(
                    "A single existing FILE path is required when the second input is stdin "
                    "(or use two FILE paths without piping)."
                )
            return JoinStylePathResolution(
                path_paths=(leading_paths[0],),
                stdin_replaces_second_file=True,
                remaining_args=self.args[1:],
                check_same_file_pair=check_same_file_pair,
                same_file_pair_message=same_file_pair_message,
            )

        raise click.ClickException(
            "At least two existing FILE paths are required when stdin is a TTY "
            "(pipe data on stdin to use one file path plus stdin as the second input)."
        )

    def to_data_file(self) -> DataFile:
        """After command-specific checks: materialize :class:`~scripts.DataFile.DataFile`."""
        if self.path_candidate_rule is PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND:
            raise click.ClickException(
                "Use resolve_join_style_paths() and open DataFile instances per path / stdin; "
                "to_data_file() does not apply to PAIR_CHAIN_OR_STDIN_SECOND."
            )
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


def validate_positive_key_field(name: str, value: Optional[int]) -> None:
    """Raise :exc:`click.ClickException` if ``value`` is set and not a valid 1-based index."""
    if value is not None and value < 1:
        raise click.ClickException(f"{name} must be a positive (1-based) field index")


@dataclass(frozen=True)
class EffectiveKeys:
    """Resolved key indices for two-input comparison commands."""

    k1: Optional[int]
    k2: Optional[int]


def validate_and_resolve_key_fields(
    *,
    key: Optional[int],
    key1: Optional[int],
    key2: Optional[int],
) -> EffectiveKeys:
    """
    Validate key flags and return effective keys.

    Resolution mirrors legacy ``matches`` behavior:
    - ``--key`` fills missing sides
    - one-sided explicit key mirrors to the other side
    """
    validate_positive_key_field("--key", key)
    validate_positive_key_field("--key1", key1)
    validate_positive_key_field("--key2", key2)

    out_key1 = key1
    out_key2 = key2
    if key is not None:
        if out_key1 is None:
            out_key1 = key
        if out_key2 is None:
            out_key2 = key
    if out_key1 is None and out_key2 is not None:
        out_key1 = out_key2
    if out_key2 is None and out_key1 is not None:
        out_key2 = out_key1
    return EffectiveKeys(k1=out_key1, k2=out_key2)


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
