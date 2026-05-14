"""Logic Agent SK Plugin — exposes PL/FOL/Modal agent methods as @kernel_function.

Wraps the three logic agents (PropositionalLogicAgent, FOLLogicAgent,
ModalLogicAgent) so that LLM agents in AgentGroupChat can call core
logic operations as tools: parse formulas, execute queries, validate,
check consistency, and translate text to belief sets.

Issue #477: Decorate PL/FOL/Modal logic agents with @kernel_function.
"""

import json
import logging
from typing import Optional

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


def _jvm_available() -> bool:
    """Check if JVM/TweetyBridge is available."""
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        return TweetyBridge.get_instance().is_jvm_ready()
    except Exception:
        return False


def _error_json(msg: str) -> str:
    return json.dumps({"error": msg})


class LogicAgentPlugin:
    """Semantic Kernel plugin exposing PL/FOL/Modal logic operations.

    Provides @kernel_function methods for:
    1. Parsing and validating formulas in each logic type
    2. Executing queries against belief sets
    3. Checking consistency of belief sets
    4. Translating natural language to formal belief sets (LLM-required)

    Usage:
        kernel.add_plugin(LogicAgentPlugin(), plugin_name="logic_agents")
    """

    # --- Propositional Logic (PL) ---

    @kernel_function(
        name="parse_pl_formula",
        description=(
            "Analyser et valider une formule de logique propositionnelle. "
            "Vérifie la syntaxe via TweetyProject. "
            "Entrée: formule PL (ex: 'a => b', '!(p && q)'). "
            "Retourne JSON: {'is_valid', 'formula', 'error'}."
        ),
    )
    def parse_pl_formula(self, formula: str) -> str:
        """Validate a propositional logic formula syntax."""
        if not _jvm_available():
            return _error_json("JVM/Tweety non disponible")

        try:
            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )

            bridge = TweetyBridge.get_instance()
            is_valid = bridge.validate_pl_formula(formula)
            return json.dumps(
                {"is_valid": is_valid, "formula": formula, "error": None}
            )
        except Exception as e:
            return _error_json(str(e))

    @kernel_function(
        name="execute_pl_query",
        description=(
            "Exécuter une requête PL sur un ensemble de croyances. "
            "Entrée: JSON {'belief_set': 'a => b\\nb', 'query': 'b'}. "
            "Retourne JSON: {'result', 'query', 'belief_set', 'accepted'}."
        ),
    )
    def execute_pl_query(self, payload: str) -> str:
        """Execute a propositional logic query against a belief set."""
        if not _jvm_available():
            return _error_json("JVM/Tweety non disponible")

        try:
            params = json.loads(payload) if isinstance(payload, str) else payload
            belief_set = params.get("belief_set", "")
            query = params.get("query", "")

            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )

            bridge = TweetyBridge.get_instance()
            accepted, message = bridge.execute_pl_query(belief_set, query)
            return json.dumps(
                {
                    "result": message,
                    "query": query,
                    "belief_set": belief_set[:200],
                    "truncated": len(belief_set) > 200,
                    "accepted": accepted,
                }
            )
        except Exception as e:
            return _error_json(str(e))

    @kernel_function(
        name="check_pl_consistency",
        description=(
            "Vérifier la cohérence d'un ensemble de croyances propositionnelles. "
            "Entrée: ensemble de croyances PL (formules séparées par \\n). "
            "Retourne JSON: {'is_consistent', 'belief_set', 'message'}."
        ),
    )
    def check_pl_consistency(self, belief_set: str) -> str:
        """Check consistency of a propositional belief set."""
        if not _jvm_available():
            return _error_json("JVM/Tweety non disponible")

        try:
            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )

            bridge = TweetyBridge.get_instance()
            is_consistent, message = bridge.check_consistency(
                belief_set, logic_type="propositional"
            )
            return json.dumps(
                {
                    "is_consistent": is_consistent,
                    "belief_set": belief_set[:200],
                    "truncated": len(belief_set) > 200,
                    "message": message,
                }
            )
        except Exception as e:
            return _error_json(str(e))

    # --- First-Order Logic (FOL) ---

    @kernel_function(
        name="execute_fol_query",
        description=(
            "Exécuter une requête FOL sur un ensemble de croyances. "
            "Entrée: JSON {'belief_set': 'forall X: (p(X) => q(X))\\nexists Y: p(Y)', "
            "'query': 'exists Z: q(Z)'}. "
            "Retourne JSON: {'result', 'query', 'accepted'}."
        ),
    )
    def execute_fol_query(self, payload: str) -> str:
        """Execute a first-order logic query against a belief set."""
        if not _jvm_available():
            return _error_json("JVM/Tweety non disponible")

        try:
            params = json.loads(payload) if isinstance(payload, str) else payload
            belief_set = params.get("belief_set", "")
            query = params.get("query", "")

            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )

            bridge = TweetyBridge.get_instance()
            accepted, message = bridge.execute_fol_query(belief_set, query)
            return json.dumps(
                {
                    "result": message,
                    "query": query,
                    "belief_set": belief_set[:200],
                    "truncated": len(belief_set) > 200,
                    "accepted": accepted,
                }
            )
        except Exception as e:
            return _error_json(str(e))

    @kernel_function(
        name="check_fol_consistency",
        description=(
            "Vérifier la cohérence d'un ensemble de croyances FOL. "
            "Entrée: ensemble de croyances FOL. "
            "Retourne JSON: {'is_consistent', 'message'}."
        ),
    )
    def check_fol_consistency(self, belief_set: str) -> str:
        """Check consistency of a FOL belief set."""
        if not _jvm_available():
            return _error_json("JVM/Tweety non disponible")

        try:
            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )

            bridge = TweetyBridge.get_instance()
            is_consistent, message = bridge.check_consistency(
                belief_set, logic_type="fol"
            )
            return json.dumps(
                {
                    "is_consistent": is_consistent,
                    "belief_set": belief_set[:200],
                    "truncated": len(belief_set) > 200,
                    "message": message,
                }
            )
        except Exception as e:
            return _error_json(str(e))

    # --- Modal Logic ---

    @kernel_function(
        name="execute_modal_query",
        description=(
            "Exécuter une requête modale sur un ensemble de croyances. "
            "Entrée: JSON {'belief_set': 'constant a\\nconstant b\\n[](a => b)', "
            "'query': '[](a)', 'logic_type': 'K'}. "
            "Types de logique: K, T, S5. "
            "Retourne JSON: {'result', 'query', 'accepted'}."
        ),
    )
    def execute_modal_query(self, payload: str) -> str:
        """Execute a modal logic query against a belief set."""
        if not _jvm_available():
            return _error_json("JVM/Tweety non disponible")

        try:
            params = json.loads(payload) if isinstance(payload, str) else payload
            belief_set = params.get("belief_set", "")
            query = params.get("query", "")
            logic_type = params.get("logic_type", "K")

            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )

            bridge = TweetyBridge.get_instance()
            accepted, message = bridge.execute_modal_query(
                belief_set, query, logic_type=logic_type
            )
            return json.dumps(
                {
                    "result": message,
                    "query": query,
                    "belief_set": belief_set[:200],
                    "truncated": len(belief_set) > 200,
                    "accepted": accepted,
                    "logic_type": logic_type,
                }
            )
        except Exception as e:
            return _error_json(str(e))

    @kernel_function(
        name="check_modal_consistency",
        description=(
            "Vérifier la cohérence d'un ensemble de croyances modales. "
            "Entrée: JSON {'belief_set': '...formulas...', 'logic_type': 'K'}. "
            "Retourne JSON: {'is_consistent', 'message'}."
        ),
    )
    def check_modal_consistency(self, payload: str) -> str:
        """Check consistency of a modal belief set."""
        if not _jvm_available():
            return _error_json("JVM/Tweety non disponible")

        try:
            params = json.loads(payload) if isinstance(payload, str) else payload
            belief_set = params.get("belief_set", "")
            logic_type = params.get("logic_type", "K")

            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )

            bridge = TweetyBridge.get_instance()
            is_consistent, message = bridge.check_consistency(
                belief_set, logic_type=f"modal_{logic_type.lower()}"
            )
            return json.dumps(
                {
                    "is_consistent": is_consistent,
                    "belief_set": belief_set[:200],
                    "truncated": len(belief_set) > 200,
                    "message": message,
                    "logic_type": logic_type,
                }
            )
        except Exception as e:
            return _error_json(str(e))

    # --- Cross-logic utilities ---

    @kernel_function(
        name="validate_formula",
        description=(
            "Valider la syntaxe d'une formule logique. "
            "Entrée: JSON {'formula': 'a => b', 'logic_type': 'propositional'}. "
            "Types: 'propositional', 'fol', 'modal'. "
            "Retourne JSON: {'is_valid', 'formula', 'logic_type'}."
        ),
    )
    def validate_formula(self, payload: str) -> str:
        """Validate a formula's syntax for the given logic type."""
        if not _jvm_available():
            return _error_json("JVM/Tweety non disponible")

        try:
            params = json.loads(payload) if isinstance(payload, str) else payload
            formula = params.get("formula", "")
            logic_type = params.get("logic_type", "propositional")

            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )

            bridge = TweetyBridge.get_instance()

            if logic_type == "propositional":
                is_valid = bridge.validate_pl_formula(formula)
            elif logic_type == "fol":
                is_valid, _ = bridge.check_consistency(formula, logic_type="fol")
            elif logic_type == "modal":
                is_valid, _ = bridge.check_consistency(
                    formula, logic_type="modal_k"
                )
            else:
                return _error_json(f"Unknown logic_type: {logic_type}")

            return json.dumps(
                {
                    "is_valid": is_valid,
                    "formula": formula,
                    "logic_type": logic_type,
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "is_valid": False,
                    "formula": params.get("formula", ""),
                    "logic_type": params.get("logic_type", "propositional"),
                    "error": str(e),
                }
            )
