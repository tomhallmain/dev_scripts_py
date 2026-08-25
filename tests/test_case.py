"""Tests for ``ds case`` (parity with the original bash ``ds:case`` cases).

Only the case types ``TextCaseConverter`` actually implements are covered here --
``lc``/``uc``/``pc``/``cc``/``sc``/``vc``/``oc``. The shell command also accepted
``pathc``/``dc``/``tc``/``senc``/``ac``, which have no Python branch yet, so those
shell cases have no equivalent to assert against.
"""
from __future__ import annotations

import pytest
from click.testing import CliRunner

from scripts.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _case(runner: CliRunner, tocase: str, text: str) -> str:
    r = runner.invoke(cli, [".", "case", tocase], input=text + "\n", catch_exceptions=False)
    assert r.exit_code == 0
    return r.output


def test_lower_case(runner: CliRunner) -> None:
    assert _case(runner, "lc", "hello WORLD") == "hello world\n"


def test_upper_case(runner: CliRunner) -> None:
    assert _case(runner, "uc", "hello WORLD") == "HELLO WORLD\n"


def test_proper_case(runner: CliRunner) -> None:
    assert _case(runner, "pc", "hello WORLD") == "Hello World\n"


def test_snake_case_splits_camel_boundary(runner: CliRunner) -> None:
    """The shell case needed ``-v boundary=1``; the Python port always splits camel boundaries."""
    assert _case(runner, "sc", "myVariableName") == "my_variable_name\n"


def test_proper_case_keeps_lowercase_articles_after_second_word(runner: CliRunner) -> None:
    """``gen_pc`` capitalizes the first two words, then leaves articles/prepositions alone."""
    assert _case(runner, "pc", "a tale of two cities") == "A Tale of Two Cities\n"


def test_camel_case(runner: CliRunner) -> None:
    assert _case(runner, "cc", "hello WORLD") == "helloWorld\n"


def test_var_case(runner: CliRunner) -> None:
    assert _case(runner, "vc", "hello WORLD") == "HELLO_WORLD\n"


def test_dot_case(runner: CliRunner) -> None:
    assert _case(runner, "oc", "hello WORLD") == "Hello.World\n"


def test_underscore_and_period_are_word_separators(runner: CliRunner) -> None:
    """``prepare_line`` turns ``_`` and ``.`` into spaces before recasing."""
    assert _case(runner, "pc", "hello_world.again") == "Hello World Again\n"


def test_all_separators_split_words(runner: CliRunner) -> None:
    """Shell parity case: ``ds:case pc`` treats ``.``, ``-``, ``_`` and ``/`` as separators."""
    assert _case(runner, "pc", "a.b-c_d/e") == "A B C D E\n"
