"""#1773 constat 3 — le validateur PL doit lire la valeur de retour.

``PLHandler.parse_pl_formula`` signale l'échec de deux façons : ``raise
ValueError`` (parse Java levé) et ``return None`` (rejet sanitizer / entrée
non exploitable). ``TweetyBridge.validate_pl_formula`` ne testait que
l'exception — tout ``None`` devenait un verdict ``True`` : le validateur
était toujours-vrai sur la moitié des chemins d'échec.

Le contrôle visé par le dispatch : ``validate_pl_formula('))garbage((')``
doit rendre ``False``. Rouge sur main d'aujourd'hui.

Inclut les deux frères découverts au sweep constat 1 :
- ``query_executor`` sondait ``bridge.is_jvm_ready()`` (inexistant) et
  dépaquetait un bool comme tuple (validateur fantôme sur le handler) ;
- ``first_order_logic_agent_adapter`` importait ``bridges.tweety_bridge``
  (module inexistant) → ImportError permanent → mode dégradé à toutes les
  exécutions, sans que la JVM soit jamais consultée.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.logic.query_executor import QueryExecutor
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet
from argumentation_analysis.agents.core.logic.first_order_logic_agent_adapter import (
    FOLLogicAgent as FOLLogicAgentAdapter,
)


class TestValidatePlFormulaReadsReturnValue:
    """Le verdict doit refléter le retour du handler, pas seulement l'absence d'exception."""

    def setup_method(self):
        self._patchers = [
            patch(
                "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyInitializer"
            ),
            patch(
                "argumentation_analysis.agents.core.logic.tweety_bridge."
                "PropositionalLogicHandler"
            ),
        ]
        self.mock_initializer_class = self._patchers[0].start()
        self.mock_pl_handler_class = self._patchers[1].start()
        self.mock_initializer_class.return_value.is_jvm_ready.return_value = True
        self.mock_pl_handler = self.mock_pl_handler_class.return_value
        TweetyBridge._instance = None
        self.bridge = TweetyBridge.get_instance()

    def teardown_method(self):
        for p in self._patchers:
            p.stop()
        TweetyBridge._instance = None

    def test_none_return_is_not_valid(self):
        """Chemin None (rejet sanitizer) => verdict négatif. Rouge sur main."""
        self.mock_pl_handler.parse_pl_formula.return_value = None
        assert self.bridge.validate_pl_formula("))garbage((") is False

    def test_parsed_return_is_valid(self):
        self.mock_pl_handler.parse_pl_formula.return_value = MagicMock()
        assert self.bridge.validate_pl_formula("a => b") is True

    def test_value_error_is_not_valid(self):
        self.mock_pl_handler.parse_pl_formula.side_effect = ValueError("syntax")
        assert self.bridge.validate_pl_formula("a ==> b") is False


# ---------------------------------------------------------------------------
# Contrôle réel (JVM up) — le test que le dispatch veut voir échouer sur main
# ---------------------------------------------------------------------------


class TestValidatePlFormulaRealJvm:
    pytestmark = pytest.mark.tweety

    def test_garbage_formula_is_invalid(self, tweety_bridge_fixture):
        """'))garbage((' passe par le rejet sanitizer (return None) : doit etre False."""
        bridge = TweetyBridge.get_instance()
        assert bridge.validate_pl_formula("))garbage((") is False

    def test_wellformed_formula_is_valid(self, tweety_bridge_fixture):
        bridge = TweetyBridge.get_instance()
        assert bridge.validate_pl_formula("a => b") is True


# ---------------------------------------------------------------------------
# Frère 1 — query_executor : sonde fantôme + validateur fantôme
# ---------------------------------------------------------------------------


class TestQueryExecutorRealContract:
    def _executor_with_mock_bridge(self):
        executor = QueryExecutor.__new__(QueryExecutor)
        executor._logger = MagicMock()
        executor._tweety_bridge = MagicMock()
        executor._tweety_bridge.initializer.is_jvm_ready.return_value = True
        return executor

    def test_jvm_probe_goes_through_initializer(self):
        """La sonde doit consulter initializer.is_jvm_ready (pas bridge.is_jvm_ready)."""
        executor = self._executor_with_mock_bridge()
        executor._tweety_bridge.initializer.is_jvm_ready.return_value = False
        result, message = executor.execute_query(PropositionalBeliefSet("a => b"), "a")
        executor._tweety_bridge.initializer.is_jvm_ready.assert_called_once()
        assert result is None
        assert "FUNC_ERROR" in message

    def test_pl_validation_uses_bridge_validator_bool(self):
        """Le validateur vit sur le bridge (bool) — pas de tuple a dépaqueter."""
        executor = self._executor_with_mock_bridge()
        executor._tweety_bridge.validate_pl_formula.return_value = False
        result, message = executor.execute_query(PropositionalBeliefSet("a => b"), "a")
        executor._tweety_bridge.validate_pl_formula.assert_called_once_with("a")
        assert result is None
        assert "Requête invalide" in message


# ---------------------------------------------------------------------------
# Frère 2 — adaptateur FOL : l'ImportError permanent fabriquait le mode dégradé
# ---------------------------------------------------------------------------


class TestFolAdapterBridgeInit:
    def test_bridge_survives_when_module_path_is_real(self):
        """Avec le vrai module patché et une JVM prete, le bridge doit etre pose.

        Sur main, l'import pointait vers ``bridges.tweety_bridge`` (module
        inexistant) : ImportError capture => _tweety_bridge reste None a
        TOUTES les exécutions, même JVM prete.
        """
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
        ) as mock_bridge_class:
            mock_bridge_class.return_value.initializer.is_jvm_ready.return_value = True
            adapter = FOLLogicAgentAdapter(agent_name="test_adapter")
            assert adapter._tweety_bridge is mock_bridge_class.return_value, (
                "le bridge n'a pas été posé alors que la JVM est prête "
                "(import fantôme ou sonde fantôme)"
            )

    def test_degraded_still_honest_when_jvm_not_ready(self):
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
        ) as mock_bridge_class:
            mock_bridge_class.return_value.initializer.is_jvm_ready.return_value = False
            adapter = FOLLogicAgentAdapter(agent_name="test_adapter")
            assert adapter._tweety_bridge is None
