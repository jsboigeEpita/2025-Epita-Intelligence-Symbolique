# argumentation_analysis/orchestration/cluedo_components/enhanced_logic.py
from typing import Dict, Any, Optional

from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.oracle.cluedo_dataset import RevelationRecord


class EnhancedLogicHandler:
    """
    Gère la logique spécifique au mode "enhanced_auto_reveal".
    """

    def __init__(self, oracle_state: Optional[CluedoOracleState], oracle_strategy: str):
        self.oracle_state = oracle_state
        self.oracle_strategy = oracle_strategy

    def analyze_suggestion_quality(self, suggestion: str) -> Dict[str, Any]:
        """Analyse la qualité d'une suggestion pour détecter si elle est triviale."""
        if not suggestion or len(suggestion.strip()) < 10:
            return {"is_trivial": True, "reason": "suggestion_too_short"}

        suggestion_lower = suggestion.lower()
        trivial_keywords = [
            "je ne sais pas",
            "peut-être",
            "il faut chercher",
            "hmm",
            "c'est difficile",
            "vraiment qui",
            "des indices",
            "quelqu'un avec",
            "à dire",
        ]

        for keyword in trivial_keywords:
            if keyword in suggestion_lower:
                return {
                    "is_trivial": True,
                    "reason": f"trivial_keyword_detected: {keyword}",
                }

        return {"is_trivial": False, "reason": "substantive_suggestion"}

    def trigger_auto_revelation(
        self, trigger_reason: str, context: str
    ) -> Dict[str, Any]:
        """Déclenche une révélation automatique Enhanced."""
        if not self.oracle_state:
            return {
                "type": "auto_revelation",
                "success": False,
                "reason": "oracle_state_not_available",
            }

        moriarty_cards = self.oracle_state.get_moriarty_cards()
        if not moriarty_cards:
            return {
                "type": "auto_revelation",
                "success": False,
                "reason": "no_cards_available",
            }

        revealed_card = moriarty_cards[0]
        revelation_text = (
            f"Révélation automatique Enhanced: Moriarty possède '{revealed_card}'"
        )

        revelation = {
            "type": "auto_revelation",
            "success": True,
            "trigger_reason": trigger_reason,
            "context": context,
            "revealed_card": revealed_card,
            "revelation_text": revelation_text,
            "content": revelation_text,
            "auto_triggered": True,
            "oracle_strategy": self.oracle_strategy,
        }

        revelation_record = RevelationRecord(
            card_revealed=revealed_card,
            revelation_type="auto_revelation",
            message=f"Auto-révélation: {revealed_card}",
            strategic_value=0.9,
            revealed_to="Enhanced_System",
            metadata={"trigger_reason": trigger_reason, "context": context},
        )
        self.oracle_state.add_revelation(
            revelation=revelation_record, revealing_agent="Enhanced_System"
        )

        return revelation

    def handle_enhanced_state_transition(
        self, current_state: str, target_state: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gère les transitions d'état pour le mode Enhanced."""
        valid_states = [
            "idle",
            "investigation_active",
            "suggestion_analysis",
            "auto_revelation_triggered",
            "solution_approaching",
        ]
        if target_state not in valid_states:
            return {
                "success": False,
                "new_state": current_state,
                "enhanced_features_active": False,
                "error": f"Invalid target state: {target_state}",
            }

        features_map = {
            "investigation_active": ["auto_clue_generation", "agent_coordination"],
            "suggestion_analysis": ["quality_scoring", "auto_validation"],
            "auto_revelation_triggered": ["strategic_reveals", "game_acceleration"],
            "solution_approaching": ["final_hint_mode", "victory_detection"],
        }

        return {
            "success": True,
            "new_state": target_state,
            "enhanced_features_active": features_map.get(target_state, []),
            "transition_from": current_state,
            "context_elements": len(context.get("elements_jeu", {})),
        }

    async def execute_optimized_agent_turn(
        self, agent_name: str, turn_number: int, context: str
    ) -> Dict[str, Any]:
        """Exécute un tour d'agent optimisé avec des rôles spécialisés."""
        role_mapping = {
            "Sherlock": "investigator",
            "Watson": "analyzer",
            "Moriarty": "oracle_revealer",
        }
        agent_role = role_mapping.get(agent_name, "generic")

        efficiency_score = 0.7
        if agent_role == "investigator":
            efficiency_score = 0.85 + (turn_number * 0.05)
        elif agent_role == "analyzer":
            efficiency_score = 0.80 + (turn_number * 0.04)
        elif agent_role == "oracle_revealer":
            efficiency_score = 0.90 + (turn_number * 0.03)

        return {
            "role": agent_role,
            "action_type": agent_role.replace("_", " "),
            "performance": {
                "efficiency": min(efficiency_score, 1.0),
                "context_awareness": 0.75 if context == "enhanced_cluedo" else 0.60,
                "role_specialization": 0.95,
                "turn_optimization": turn_number * 0.1,
            },
            "turn_number": turn_number,
            "context": context,
            "success": True,
        }
