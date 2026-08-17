"""#1774 — la sémantique ABA d'un cadre explicitement vide est UNE extension.

Un cadre ABA sans hypothèse ni règle admet exactement une extension sous
les sémantiques preferred/stable/complete : l'ensemble vide. La sortie
correcte est donc ``extensions: [[]]`` avec ``extensions_count: 1``.

Ce pin vit HORS CI (``tests/agents/`` n'est pas couvert par le harnais CI,
qui ne lance que ``tests/unit/ tests/scripts/`` — constat coord R822) : il
est destiné aux environnements JVM réels (mesure locale myia-po-2023). La
divergence mesurée — CI rend ``extensions: []`` (zéro extension) sur un
cadre vide — est un défaut réel de l'environnement CI, suivi sur l'issue
#1785 (famille #1019, verdict fabriqué par divergence d'environnement).

Le test unitaire de #1774 (``test_tweety_logic_plugin_error_vocabulary.py``,
dans CI) ne pince volontairement que la forme : un cadre explicitement vide
est ANALYSÉ, pas rejeté comme garbage. Coupler le gate CI à ce pin sémantique
ré-introduirait le rouge croisé-environnement que cette PR ne doit pas porter.
"""

import json

import pytest

from argumentation_analysis.agents.core.logic.aba_handler import ABAHandler
from argumentation_analysis.plugins.tweety_logic_plugin import TweetyLogicPlugin

pytestmark = pytest.mark.tweety


class TestEmptyAbaFrameworkSemantics:
    """Le cadre ABA vide a exactement une extension : l'ensemble vide."""

    def test_handler_renders_single_empty_extension(
        self, tweety_bridge_fixture
    ) -> None:
        handler = ABAHandler()
        result = handler.analyze_aba_framework(
            assumptions=[], rules=[], contraries={}, semantics="preferred"
        )
        assert result["extensions"] == [[]], (
            "un cadre ABA vide admet exactement une extension (l'ensemble vide); "
            f"rendu: {result['extensions']}"
        )
        assert result["statistics"]["extensions_count"] == 1
        assert result["statistics"]["assumptions_count"] == 0
        assert result["statistics"]["rules_count"] == 0

    def test_plugin_renders_single_empty_extension(self, tweety_bridge_fixture) -> None:
        """Chemin de production complet : plugin -> handler -> raisonneur Java."""
        plugin = TweetyLogicPlugin()
        result = json.loads(plugin.analyze_aba('{"assumptions": [], "rules": []}'))
        assert "error" not in result, f"le cadre vide n'est pas analysé: {result}"
        assert result["extensions"] == [[]]
        assert result["statistics"]["extensions_count"] == 1
