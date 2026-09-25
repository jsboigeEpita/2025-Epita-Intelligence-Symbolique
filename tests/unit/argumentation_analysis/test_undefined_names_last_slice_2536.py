"""#2536, last slice: the two undefined names left on reachable paths.

- ``PLHandler.parse_pl_formula(formula, constants=[...])`` used ``JString``,
  whose import was removed in 2025-06, so the ``constants`` branch raised
  ``NameError`` instead of parsing.
- ``abs_arg_dung/agent.py`` run as a script used ``Path`` without importing it,
  so its demo stopped at its first line with ``NameError``, which its own
  ``except`` printed as a demo error.
"""

import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import jpype

from argumentation_analysis.agents.core.logic import pl_handler

REPO = Path(__file__).resolve().parents[3]


class _JException(Exception):
    pass


def test_pl_formula_with_constants_reaches_the_parser():
    parser = MagicMock()
    parsed = MagicMock()

    def _atom(name):
        atom = MagicMock()
        atom.getName.return_value = name
        return atom

    parsed.getAtoms.return_value = [_atom("a"), _atom("b")]
    parser.parseFormula.return_value = parsed
    initializer = MagicMock()
    initializer.get_pl_parser.return_value = parser
    with patch.object(pl_handler, "jpype") as fake_jpype:
        fake_jpype.JClass.side_effect = lambda name: MagicMock(name=name)
        fake_jpype.JString.side_effect = lambda text: ("JString", text)
        fake_jpype.JException = _JException
        handler = pl_handler.PLHandler(initializer)
        result = handler.parse_pl_formula("a && b", constants=["a", "b"])

    assert result is parsed
    parser.parseFormula.assert_called_once()
    # #2537 : ce Tweety n'expose pas de surcharge parseFormula(String,
    # PlSignature) — l'appel réel est mono-argument, le vocabulaire déclaré est
    # vérifié après coup sur les atomes de la formule parsée.
    (formula,) = parser.parseFormula.call_args.args
    assert formula == ("JString", handler._normalize_formula("a && b"))


def test_pl_formula_with_constants_rejects_undeclared_atoms():
    parser = MagicMock()
    parsed = MagicMock()

    def _atom(name):
        atom = MagicMock()
        atom.getName.return_value = name
        return atom

    parsed.getAtoms.return_value = [_atom("a"), _atom("c")]
    parser.parseFormula.return_value = parsed
    initializer = MagicMock()
    initializer.get_pl_parser.return_value = parser
    with patch.object(pl_handler, "jpype") as fake_jpype:
        fake_jpype.JClass.side_effect = lambda name: MagicMock(name=name)
        fake_jpype.JString.side_effect = lambda text: ("JString", text)
        fake_jpype.JException = _JException
        handler = pl_handler.PLHandler(initializer)
        with pytest.raises(ValueError, match="non déclarées"):
            handler.parse_pl_formula("a && c", constants=["a", "b"])


class _StartJVMReached(Exception):
    pass


def _refuse_to_start(*args, **kwargs):
    raise _StartJVMReached("startJVM reached")


def test_dung_demo_gets_past_its_path_line(monkeypatch, capsys):
    """The demo reaches the Tweety library lookup instead of a NameError.

    The JVM is never looked up nor started: the test stops the demo at
    ``startJVM``, or earlier if the jars are absent, and each of those outcomes
    proves that the ``Path`` line ran. ``getDefaultJVMPath`` is stubbed because
    the demo evaluates it as ``startJVM``'s argument, and on a machine where it
    finds no JVM it would raise first (measured in CI on #2595).
    """
    monkeypatch.setattr(jpype, "isJVMStarted", lambda: False)
    monkeypatch.setattr(jpype, "getDefaultJVMPath", lambda: "jvm-path-2536")
    monkeypatch.setattr(jpype, "startJVM", _refuse_to_start)

    runpy.run_path(str(REPO / "abs_arg_dung" / "agent.py"), run_name="__main__")

    out = capsys.readouterr().out
    assert "is not defined" not in out
    reached = [
        "startJVM reached",
        "Le répertoire des librairies Tweety est introuvable",
        "Aucun JAR trouvé",
    ]
    assert any(marker in out for marker in reached), out
