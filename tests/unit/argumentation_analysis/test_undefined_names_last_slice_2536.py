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

import jpype

from argumentation_analysis.agents.core.logic import pl_handler

REPO = Path(__file__).resolve().parents[3]


class _JException(Exception):
    pass


def test_pl_formula_with_constants_reaches_the_parser():
    parser = MagicMock()
    parser.parseFormula.return_value = "parsed"
    initializer = MagicMock()
    initializer.get_pl_parser.return_value = parser
    with patch.object(pl_handler, "jpype") as fake_jpype:
        fake_jpype.JClass.side_effect = lambda name: MagicMock(name=name)
        fake_jpype.JString.side_effect = lambda text: ("JString", text)
        fake_jpype.JException = _JException
        handler = pl_handler.PLHandler(initializer)
        result = handler.parse_pl_formula("a && b", constants=["a", "b"])

    assert result == "parsed"
    parser.parseFormula.assert_called_once()
    formula, _signature = parser.parseFormula.call_args.args
    assert formula == ("JString", handler._normalize_formula("a && b"))


class _StartJVMReached(Exception):
    pass


def _refuse_to_start(*args, **kwargs):
    raise _StartJVMReached("startJVM reached")


def test_dung_demo_gets_past_its_path_line(monkeypatch, capsys):
    """The demo reaches the Tweety library lookup instead of a NameError.

    The JVM is never started: the test stops the demo at ``startJVM``, or
    earlier if the jars are absent, and each of those outcomes proves that the
    ``Path`` line ran.
    """
    monkeypatch.setattr(jpype, "isJVMStarted", lambda: False)
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
