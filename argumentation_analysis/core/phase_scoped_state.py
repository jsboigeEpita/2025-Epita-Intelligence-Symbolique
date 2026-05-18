"""Phase-scoped state plugins for tool-gating per phase (#605).

Each agent receives only the StateManagerPlugin functions relevant to its phase,
instead of the full ~30-method surface. This prevents cross-phase tool pollution.

Classes:
    _SharedStateBase: 5 common methods (read, task control, turn designation)
    ExtractionPhaseState: Phase 1 — argument/extract/fallacy writes
    FormalPhaseState: Phase 2 — belief/formal/JTMS/quality writes
    SynthesisPhaseState: Phase 3 — counter/governance/debate/conclusion writes
"""

import json
import logging
from typing import List, Dict, Optional

from semantic_kernel.functions import kernel_function

from .shared_state import RhetoricalAnalysisState

sm_logger = logging.getLogger("Orchestration.PhaseState")


class _SharedStateBase:
    """Base for phase-scoped state plugins — read + task control methods."""

    _state: "RhetoricalAnalysisState"
    _logger: logging.Logger

    def __init__(self, state: "RhetoricalAnalysisState"):
        self._state = state
        self._logger = sm_logger

    @kernel_function(
        description="Récupère un aperçu de l'état actuel de l'analyse.",
        name="get_current_state_snapshot",
    )
    def get_current_state_snapshot(self, summarize: bool = True) -> str:
        try:
            snapshot_dict = self._state.get_state_snapshot(summarize=summarize)
            indent = 2 if not summarize else None
            return json.dumps(snapshot_dict, indent=indent, ensure_ascii=False, default=str)
        except Exception as e:
            self._logger.error(f"Snapshot error: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    @kernel_function(
        description="Ajoute une nouvelle tâche d'analyse à l'état.",
        name="add_analysis_task",
    )
    def add_analysis_task(self, description: str) -> str:
        try:
            task_id = self._state.add_task(description)
            return task_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Marque une tâche comme répondue dans l'état.",
        name="mark_task_as_answered",
    )
    def mark_task_as_answered(self, task_id: str, answer: str) -> str:
        try:
            self._state.mark_task_as_answered(task_id, answer)
            return f"OK: Tâche {task_id} marquée comme répondue."
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute une réponse d'un agent à une tâche d'analyse.",
        name="add_answer",
    )
    def add_answer(self, task_id: str, author_agent: str, answer_text: str, source_ids: List[str]) -> str:
        try:
            self._state.add_answer(task_id, author_agent, answer_text, source_ids)
            return f"OK: Réponse pour {task_id} ajoutée."
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Désigne quel agent doit parler au prochain tour.",
        name="designate_next_agent",
    )
    def designate_next_agent(self, agent_name: str) -> str:
        try:
            self._state.designate_next_agent(agent_name)
            return f"OK. Agent '{agent_name}' désigné pour le prochain tour."
        except Exception as e:
            return f"FUNC_ERROR: {e}"


# ---------------------------------------------------------------------------
# Phase 1: Extraction & Detection
# ---------------------------------------------------------------------------

class ExtractionPhaseState(_SharedStateBase):
    """State plugin scoped for Phase 1 — Extraction & Detection.

    Exposes: read + task control + argument/extract writes + fallacy writes.
    """

    @kernel_function(
        description="Ajoute un argument identifié à l'état.",
        name="add_identified_argument",
    )
    def add_identified_argument(self, description: str) -> str:
        try:
            arg_id = self._state.add_argument(description)
            return arg_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute une liste d'arguments identifiés à l'état.",
        name="add_identified_arguments",
    )
    def add_identified_arguments(self, arguments: List[str]) -> str:
        try:
            self._state.add_identified_arguments(arguments)
            return f"OK: {len(arguments)} arguments ajoutés."
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute un sophisme identifié à l'état.",
        name="add_identified_fallacy",
    )
    def add_identified_fallacy(
        self,
        fallacy_type: str,
        justification: str,
        target_argument_id: Optional[str] = None,
    ) -> str:
        try:
            fallacy_id = self._state.add_fallacy(fallacy_type, justification, target_argument_id)
            return fallacy_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute une liste de sophismes identifiés à l'état.",
        name="add_identified_fallacies",
    )
    def add_identified_fallacies(self, fallacies: List[Dict[str, str]]) -> str:
        try:
            self._state.add_identified_fallacies(fallacies)
            return f"OK: {len(fallacies)} sophismes ajoutés."
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute un extrait textuel identifié pendant l'extraction.",
        name="add_extract",
    )
    def add_extract(self, name: str, content: str) -> str:
        try:
            ext_id = self._state.add_extract(name, content)
            return ext_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute un score de détection neurale de sophisme.",
        name="add_neural_fallacy_score",
    )
    def add_neural_fallacy_score(self, text_segment: str, label: str, confidence: str = "0.5") -> str:
        try:
            nf_id = self._state.add_neural_fallacy_score(text_segment, label, float(confidence))
            return nf_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"


# ---------------------------------------------------------------------------
# Phase 2: Formal Analysis & Quality
# ---------------------------------------------------------------------------

class FormalPhaseState(_SharedStateBase):
    """State plugin scoped for Phase 2 — Formal Analysis & Quality.

    Exposes: read + task control + belief/formal/JTMS/quality writes.
    """

    @kernel_function(
        description="Ajoute un belief set formel à l'état.",
        name="add_belief_set",
    )
    def add_belief_set(self, logic_type: str, content: str) -> str:
        valid_logic_types = {"propositional": "Propositional", "pl": "Propositional", "fol": "FOL", "first_order": "FOL"}
        normalized = logic_type.strip().lower()
        if normalized not in valid_logic_types:
            return f"FUNC_ERROR: Type logique '{logic_type}' non supporté."
        try:
            bs_id = self._state.add_belief_set(valid_logic_types[normalized], content)
            return bs_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Enregistre une requête formelle et son résultat brut.",
        name="log_query_result",
    )
    def log_query_result(self, belief_set_id: str, query: str, raw_result: str) -> str:
        try:
            log_id = self._state.log_query(belief_set_id, query, raw_result)
            return log_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Enregistre une traduction NL → logique formelle.",
        name="add_nl_to_logic_translation",
    )
    def add_nl_to_logic_translation(
        self,
        original_text: str,
        formula: str,
        logic_type: str,
        is_valid: str = "true",
        variables: str = "{}",
        confidence: str = "0.7",
    ) -> str:
        try:
            parsed_vars = json.loads(variables) if isinstance(variables, str) else variables
            tr_id = self._state.add_nl_to_logic_translation(
                original_text=original_text[:200], formula=formula, logic_type=logic_type,
                is_valid=is_valid.lower() in ("true", "1", "yes"),
                variables=parsed_vars, confidence=float(confidence),
            )
            return tr_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute des scores de qualité pour un argument.",
        name="add_quality_score",
    )
    def add_quality_score(self, arg_id: str, scores_json: str, overall: str = "0.5") -> str:
        try:
            scores = json.loads(scores_json) if isinstance(scores_json, str) else scores_json
            self._state.add_quality_score(arg_id, scores, float(overall))
            return f"OK: Quality scores added for {arg_id}"
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute un framework d'argumentation de Dung.",
        name="add_dung_framework",
    )
    def add_dung_framework(
        self, name: str, arguments_json: str, attacks_json: str, extensions_json: str = "{}",
    ) -> str:
        try:
            arguments = json.loads(arguments_json)
            attacks = json.loads(attacks_json)
            extensions = json.loads(extensions_json) if extensions_json != "{}" else None
            df_id = self._state.add_dung_framework(name, arguments, attacks, extensions)
            return df_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute un résultat d'analyse ASPIC+.",
        name="add_aspic_result",
    )
    def add_aspic_result(self, reasoner_type: str, extensions_json: str, statistics_json: str) -> str:
        try:
            extensions = json.loads(extensions_json)
            statistics = json.loads(statistics_json)
            as_id = self._state.add_aspic_result(reasoner_type, extensions, statistics)
            return as_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute un résultat de révision de croyances.",
        name="add_belief_revision_result",
    )
    def add_belief_revision_result(self, method: str, original_json: str, revised_json: str) -> str:
        try:
            original = json.loads(original_json)
            revised = json.loads(revised_json)
            br_id = self._state.add_belief_revision_result(method, original, revised)
            return br_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute un résultat de ranking sémantique.",
        name="add_ranking_result",
    )
    def add_ranking_result(self, method: str, arguments_json: str, comparisons_json: str) -> str:
        try:
            arguments = json.loads(arguments_json)
            comparisons = json.loads(comparisons_json)
            rk_id = self._state.add_ranking_result(method, arguments, comparisons)
            return rk_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    # --- JTMS methods ---

    @kernel_function(
        description="Crée une croyance JTMS avec métadonnées étendues.",
        name="jtms_create_belief",
    )
    def jtms_create_belief(
        self, belief_name: str, agent_source: str = "unknown",
        confidence: float = 0.5, context: Optional[str] = None,
    ) -> str:
        self._logger.info(f"jtms_create_belief: '{belief_name}', source={agent_source}")
        try:
            from argumentation_analysis.services.jtms.extended_belief import JTMSSession
            if not hasattr(self._state, "_jtms_session"):
                self._state._jtms_session = JTMSSession(session_id="shared_jtms", owner_agent="phase_state")
            session = self._state._jtms_session
            context_dict = {}
            if context:
                try:
                    context_dict = json.loads(context)
                except (json.JSONDecodeError, TypeError):
                    context_dict = {"raw": context}
            session.add_belief(belief_name, agent_source=agent_source, context=context_dict, confidence=confidence)
            if hasattr(self._state, "add_jtms_belief"):
                self._state.add_jtms_belief(name=belief_name, valid=True, justifications=[])
            return f"OK: Belief '{belief_name}' created by {agent_source}"
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute une justification JTMS entre croyances.",
        name="jtms_add_justification",
    )
    def jtms_add_justification(
        self, in_list: List[str], out_list: List[str], conclusion: str, agent_source: str = "unknown",
    ) -> str:
        try:
            from argumentation_analysis.services.jtms.extended_belief import JTMSSession
            if not hasattr(self._state, "_jtms_session"):
                self._state._jtms_session = JTMSSession(session_id="shared_jtms", owner_agent="phase_state")
            self._state._jtms_session.add_justification(in_list, out_list, conclusion, agent_source=agent_source)
            return f"OK: Justification for '{conclusion}' added by {agent_source}"
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Interroge les croyances JTMS avec métadonnées.",
        name="jtms_query_beliefs",
    )
    def jtms_query_beliefs(self, agent_filter: Optional[str] = None) -> str:
        try:
            from argumentation_analysis.services.jtms.extended_belief import JTMSSession
            if not hasattr(self._state, "_jtms_session"):
                return "FUNC_ERROR: No JTMS session initialized."
            session = self._state._jtms_session
            results = []
            for name, ext_belief in session.extended_beliefs.items():
                if agent_filter and ext_belief.agent_source != agent_filter:
                    continue
                results.append({
                    "name": name, "valid": ext_belief.valid,
                    "agent_source": ext_belief.agent_source, "confidence": ext_belief.confidence,
                })
            return json.dumps(results, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Vérifie la cohérence de la session JTMS.",
        name="jtms_check_consistency",
    )
    def jtms_check_consistency(self) -> str:
        try:
            from argumentation_analysis.services.jtms.extended_belief import JTMSSession
            if not hasattr(self._state, "_jtms_session"):
                return "FUNC_ERROR: No JTMS session initialized."
            session = self._state._jtms_session
            result = session.check_consistency()
            return json.dumps({
                "is_consistent": result.get("is_consistent", True),
                "conflicts_detected": result.get("conflicts", []),
                "total_beliefs": len(session.extended_beliefs),
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Rétracte une croyance JTMS et propage.",
        name="jtms_retract_belief",
    )
    def jtms_retract_belief(self, belief_name: str, reason: str = "") -> str:
        self._logger.info(f"jtms_retract_belief: '{belief_name}', reason='{reason[:60]}'")
        try:
            from argumentation_analysis.services.jtms.extended_belief import JTMSSession
            if not hasattr(self._state, "_jtms_session"):
                return "FUNC_ERROR: No JTMS session initialized."
            session = self._state._jtms_session
            if belief_name not in session.extended_beliefs:
                candidates = [n for n in session.extended_beliefs if belief_name.lower() in n.lower()]
                if candidates:
                    belief_name = candidates[0]
                else:
                    return f"FUNC_ERROR: Belief '{belief_name}' not found."
            ext_belief = session.extended_beliefs[belief_name]
            was_valid = ext_belief.valid
            session.jtms.set_belief_validity(belief_name, None)
            import datetime as _dt
            ext_belief.record_modification("retract", {"reason": reason, "timestamp": _dt.datetime.now().isoformat()})
            ext_belief.context["retracted"] = True
            ext_belief.context["retraction_reason"] = reason
            if hasattr(self._state, "jtms_beliefs"):
                for bid, bdata in self._state.jtms_beliefs.items():
                    if bdata.get("name") == belief_name:
                        bdata["valid"] = False
                        bdata["retracted"] = True
                        bdata["retraction_reason"] = reason
                        break
            affected = [n for n, b in session.extended_beliefs.items() if n != belief_name and not b.valid]
            return json.dumps({"retracted_belief": belief_name, "was_valid": was_valid, "affected_count": len(affected)}, ensure_ascii=False)
        except Exception as e:
            return f"FUNC_ERROR: {e}"


# ---------------------------------------------------------------------------
# Phase 3: Synthesis & Debate
# ---------------------------------------------------------------------------

class SynthesisPhaseState(_SharedStateBase):
    """State plugin scoped for Phase 3 — Synthesis & Debate.

    Exposes: read + task control + counter/governance/debate/conclusion writes.
    """

    @kernel_function(
        description="Ajoute un contre-argument.",
        name="add_counter_argument",
    )
    def add_counter_argument(
        self, original_arg: str, counter_content: str, strategy: str,
        score: str = "0.5", target_arg_id: str = "",
    ) -> str:
        try:
            ca_id = self._state.add_counter_argument(
                original_arg, counter_content, strategy, float(score),
                target_arg_id=target_arg_id or None,
            )
            return ca_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute une décision de gouvernance/vote.",
        name="add_governance_decision",
    )
    def add_governance_decision(self, method: str, winner: str, scores_json: str) -> str:
        try:
            scores = json.loads(scores_json)
            gd_id = self._state.add_governance_decision(method, winner, scores)
            return gd_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Ajoute une transcription de débat.",
        name="add_debate_transcript",
    )
    def add_debate_transcript(self, topic: str, exchanges_json: str, winner: str = "") -> str:
        try:
            exchanges = json.loads(exchanges_json)
            dt_id = self._state.add_debate_transcript(topic, exchanges, winner if winner else None)
            return dt_id
        except Exception as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Enregistre la conclusion finale de l'analyse.",
        name="set_final_conclusion",
    )
    def set_final_conclusion(self, conclusion: str) -> str:
        try:
            self._state.set_conclusion(conclusion)
            return "OK: Conclusion finale enregistrée."
        except Exception as e:
            return f"FUNC_ERROR: {e}"


# ---------------------------------------------------------------------------
# Agent → Phase mapping
# ---------------------------------------------------------------------------

AGENT_PHASE_MAP = {
    "ExtractAgent": ExtractionPhaseState,
    "InformalAgent": ExtractionPhaseState,
    "FormalAgent": FormalPhaseState,
    "QualityAgent": FormalPhaseState,
    "DebateAgent": SynthesisPhaseState,
    "CounterAgent": SynthesisPhaseState,
    "GovernanceAgent": SynthesisPhaseState,
    # ProjectManager gets full StateManagerPlugin (appears in all phases)
}
