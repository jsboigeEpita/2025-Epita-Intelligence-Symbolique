"""
Tweety Logic SK plugin — exposes all Tweety logic handlers to LLM agents (#91).

Provides @kernel_function methods wrapping each of the 15+ logic handlers,
allowing LLM agents in AgentGroupChat to invoke formal reasoning directly.

Each method:
1. Parses string input (JSON or plain text)
2. Delegates to the appropriate handler via asyncio.to_thread
3. Returns a JSON string result

Gracefully handles JVM unavailability (returns error message instead of crashing).
"""

import asyncio
import json
import logging
from typing import Optional

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)

# Check JVM availability once
_JVM_AVAILABLE = False
try:
    import jpype

    _JVM_AVAILABLE = jpype.isJVMStarted()
except ImportError:
    pass


def _parse_json_or_default(text: str, default: dict) -> dict:
    """Try to parse JSON from text, return default on failure."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return default
    except (json.JSONDecodeError, TypeError):
        return default


def _check_jvm() -> bool:
    """Check if JVM is available, updating the cached flag."""
    global _JVM_AVAILABLE
    if _JVM_AVAILABLE:
        return True
    try:
        import jpype as jp

        if jp.isJVMStarted():
            _JVM_AVAILABLE = True
            return True
    except ImportError:
        pass
    return False


def _jvm_required(func):
    """Decorator that checks JVM availability before calling handler."""

    def wrapper(self, *args, **kwargs):
        if not _check_jvm():
            return json.dumps(
                {
                    "error": "JVM not available",
                    "message": "Tweety requires JVM. Start it via jvm_setup.initialize_jvm().",
                }
            )
        return func(self, *args, **kwargs)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


class TweetyLogicPlugin:
    """Semantic Kernel plugin exposing Tweety logic handlers to LLM agents.

    Wraps all 15+ logic handlers (Dung AF, propositional, FOL, modal,
    ranking, bipolar, ABA, ADF, ASPIC+, belief revision, probabilistic,
    dialogue, DL, CL) plus SAT solver as @kernel_function methods.

    Usage:
        kernel.add_plugin(TweetyLogicPlugin(), plugin_name="tweety_logic")
    """

    # ── Dung Abstract Frameworks ──────────────────────────────────────

    @kernel_function(
        name="analyze_dung_framework",
        description=(
            "Analyze arguments using Dung abstract argumentation frameworks. "
            "Input: JSON with 'arguments' (list), 'attacks' (list of pairs), "
            "and optional 'semantics' (preferred/stable/grounded/complete/etc). "
            "Returns extensions under the chosen semantics."
        ),
    )
    @_jvm_required
    def analyze_dung_framework(self, input: str) -> str:
        params = _parse_json_or_default(input, {"arguments": [], "attacks": []})
        from argumentation_analysis.agents.core.logic.af_handler import AFHandler

        handler = AFHandler()
        args = params.get("arguments", [])
        attacks = params.get("attacks", [])
        semantics = params.get("semantics", "preferred")
        result = handler.compute_extensions(args, attacks, semantics)
        return json.dumps(result, default=str)

    # ── Propositional Logic ───────────────────────────────────────────

    @kernel_function(
        name="check_propositional_consistency",
        description=(
            "Check propositional logic formula consistency via Tweety. "
            "Input: JSON with 'formulas' (list of PL formula strings). "
            "Returns satisfiability result."
        ),
    )
    @_jvm_required
    def check_propositional_consistency(self, input: str) -> str:
        params = _parse_json_or_default(input, {"formulas": [input]})
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge()
        formulas = params.get("formulas", [input])
        kb_str = "\n".join(formulas)
        result = bridge.check_consistency(kb_str)
        return json.dumps(result, default=str)

    # ── First-Order Logic ─────────────────────────────────────────────

    @kernel_function(
        name="check_fol_consistency",
        description=(
            "Check first-order logic formula consistency via Tweety/EProver. "
            "Input: JSON with 'formulas' (list of FOL formula strings). "
            "Returns consistency result."
        ),
    )
    @_jvm_required
    def check_fol_consistency(self, input: str) -> str:
        params = _parse_json_or_default(input, {"formulas": [input]})
        from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler

        handler = FOLHandler()
        formulas = params.get("formulas", [input])
        result = handler.check_consistency(formulas)
        return json.dumps(result, default=str)

    # ── Modal Logic ───────────────────────────────────────────────────

    @kernel_function(
        name="check_modal_satisfiability",
        description=(
            "Check modal logic formula satisfiability via Tweety/SPASS. "
            "Input: JSON with 'formula' (string) and optional 'logic_type' (S5/K/T). "
            "Returns satisfiability result."
        ),
    )
    @_jvm_required
    def check_modal_satisfiability(self, input: str) -> str:
        params = _parse_json_or_default(input, {"formula": input})
        from argumentation_analysis.agents.core.logic.modal_handler import ModalHandler

        handler = ModalHandler()
        formula = params.get("formula", input)
        logic_type = params.get("logic_type", "S5")
        result = handler.check_satisfiability(formula, logic_type)
        return json.dumps(result, default=str)

    # ── Ranking Semantics ─────────────────────────────────────────────

    @kernel_function(
        name="rank_arguments",
        description=(
            "Rank arguments using formal ranking semantics (categorizer, burden, etc). "
            "Input: JSON with 'arguments' (list), 'attacks' (list of pairs), "
            "optional 'method' (categorizer/burden/discussion/counting/tuples). "
            "Returns ranked argument ordering."
        ),
    )
    @_jvm_required
    def rank_arguments(self, input: str) -> str:
        params = _parse_json_or_default(input, {})
        from argumentation_analysis.agents.core.logic.ranking_handler import (
            RankingHandler,
        )

        handler = RankingHandler()
        args = params.get("arguments", [])
        attacks = params.get("attacks", [])
        method = params.get("method", "categorizer")
        result = handler.rank_arguments(args, attacks, method)
        return json.dumps(result, default=str)

    # ── Bipolar Argumentation ─────────────────────────────────────────

    @kernel_function(
        name="analyze_bipolar_framework",
        description=(
            "Analyze bipolar argumentation framework (attacks + supports). "
            "Input: JSON with 'arguments', 'attacks', 'supports' (lists), "
            "optional 'framework_type' (necessity/evidential). "
            "Returns bipolar analysis results."
        ),
    )
    @_jvm_required
    def analyze_bipolar_framework(self, input: str) -> str:
        params = _parse_json_or_default(input, {})
        from argumentation_analysis.agents.core.logic.bipolar_handler import (
            BipolarHandler,
        )

        handler = BipolarHandler()
        result = handler.analyze_bipolar_framework(
            params.get("arguments", []),
            params.get("attacks", []),
            params.get("supports", []),
            params.get("framework_type", "necessity"),
        )
        return json.dumps(result, default=str)

    # ── ABA (Assumption-Based Argumentation) ──────────────────────────

    @kernel_function(
        name="analyze_aba",
        description=(
            "Analyze Assumption-Based Argumentation framework. "
            "Input: JSON with 'assumptions' (list), 'rules' (list), "
            "optional 'contraries' (dict), 'semantics' (preferred/stable/complete). "
            "Returns ABA extensions."
        ),
    )
    @_jvm_required
    def analyze_aba(self, input: str) -> str:
        params = _parse_json_or_default(input, {})
        from argumentation_analysis.agents.core.logic.aba_handler import ABAHandler

        handler = ABAHandler()
        result = handler.analyze_aba_framework(
            params.get("assumptions", []),
            params.get("rules", []),
            params.get("contraries"),
            params.get("semantics", "preferred"),
        )
        return json.dumps(result, default=str)

    # ── ADF (Abstract Dialectical Frameworks) ─────────────────────────

    @kernel_function(
        name="analyze_adf",
        description=(
            "Analyze Abstract Dialectical Framework. "
            "Input: JSON with 'statements' (list), 'acceptance_conditions' (dict), "
            "optional 'semantics' (grounded/complete/preferred). "
            "Returns ADF interpretations."
        ),
    )
    @_jvm_required
    def analyze_adf(self, input: str) -> str:
        params = _parse_json_or_default(input, {})
        from argumentation_analysis.agents.core.logic.adf_handler import ADFHandler

        handler = ADFHandler()
        result = handler.analyze_adf(
            params.get("statements", []),
            params.get("acceptance_conditions", {}),
            params.get("semantics", "grounded"),
        )
        return json.dumps(result, default=str)

    # ── ASPIC+ ────────────────────────────────────────────────────────

    @kernel_function(
        name="analyze_aspic",
        description=(
            "Analyze ASPIC+ structured argumentation framework. "
            "Input: JSON with 'strict_rules', 'defeasible_rules' (lists), "
            "optional 'axioms' (list). Returns ASPIC+ extensions."
        ),
    )
    @_jvm_required
    def analyze_aspic(self, input: str) -> str:
        params = _parse_json_or_default(input, {})
        from argumentation_analysis.agents.core.logic.aspic_handler import ASPICHandler

        handler = ASPICHandler()
        result = handler.analyze_aspic_framework(
            params.get("strict_rules", []),
            params.get("defeasible_rules", []),
            params.get("axioms"),
        )
        return json.dumps(result, default=str)

    # ── Belief Revision ───────────────────────────────────────────────

    @kernel_function(
        name="revise_beliefs",
        description=(
            "Revise a belief set with new evidence using AGM operators. "
            "Input: JSON with 'belief_set' (list of formulas), 'new_belief' (string), "
            "optional 'method' (dalal/levi). Returns revised belief set."
        ),
    )
    @_jvm_required
    def revise_beliefs(self, input: str) -> str:
        params = _parse_json_or_default(input, {"belief_set": [], "new_belief": input})
        from argumentation_analysis.agents.core.logic.belief_revision_handler import (
            BeliefRevisionHandler,
        )

        handler = BeliefRevisionHandler()
        result = handler.revise(
            params.get("belief_set", []),
            params.get("new_belief", input),
            params.get("method", "dalal"),
        )
        return json.dumps(result, default=str)

    # ── Probabilistic Argumentation ───────────────────────────────────

    @kernel_function(
        name="analyze_probabilistic",
        description=(
            "Compute probabilistic argument acceptance. "
            "Input: JSON with 'arguments' (list), 'attacks' (list), "
            "'probabilities' (dict mapping arg→probability). "
            "Returns acceptance probabilities per argument."
        ),
    )
    @_jvm_required
    def analyze_probabilistic(self, input: str) -> str:
        params = _parse_json_or_default(input, {})
        from argumentation_analysis.agents.core.logic.probabilistic_handler import (
            ProbabilisticHandler,
        )

        handler = ProbabilisticHandler()
        result = handler.analyze_probabilistic_framework(
            params.get("arguments", []),
            params.get("attacks", []),
            params.get("probabilities", {}),
        )
        return json.dumps(result, default=str)

    # ── Dialogue Protocols ────────────────────────────────────────────

    @kernel_function(
        name="execute_dialogue",
        description=(
            "Execute a Walton-Krabbe style dialogue protocol between proponent/opponent. "
            "Input: JSON with 'proponent_args', 'proponent_attacks', "
            "'opponent_args', 'opponent_attacks' (lists), 'topic' (string). "
            "Returns dialogue outcome and trace."
        ),
    )
    @_jvm_required
    def execute_dialogue(self, input: str) -> str:
        params = _parse_json_or_default(input, {"topic": input})
        from argumentation_analysis.agents.core.logic.dialogue_handler import (
            DialogueHandler,
        )

        handler = DialogueHandler()
        result = handler.execute_dialogue(
            params.get("proponent_args", []),
            params.get("proponent_attacks", []),
            params.get("opponent_args", []),
            params.get("opponent_attacks", []),
            params.get("topic", input),
        )
        return json.dumps(result, default=str)

    # ── Description Logic ─────────────────────────────────────────────

    @kernel_function(
        name="check_dl_consistency",
        description=(
            "Check Description Logic (ALC) knowledge base consistency. "
            "Input: JSON with 'tbox' (list of [concept, equivalent] pairs), "
            "'abox_concepts' (list of [individual, concept] pairs), "
            "'abox_roles' (list of [ind1, role, ind2] triples). "
            "Returns consistency result."
        ),
    )
    @_jvm_required
    def check_dl_consistency(self, input: str) -> str:
        params = _parse_json_or_default(input, {})
        from argumentation_analysis.agents.core.logic.dl_handler import DLHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = DLHandler(initializer)
        kb = handler.create_knowledge_base(
            tbox=params.get("tbox", []),
            abox_concepts=params.get("abox_concepts", []),
            abox_roles=params.get("abox_roles", []),
        )
        consistent, msg = handler.is_consistent(kb)
        return json.dumps({"consistent": consistent, "message": msg})

    # ── Conditional Logic ─────────────────────────────────────────────

    @kernel_function(
        name="query_conditional_logic",
        description=(
            "Query a Conditional Logic knowledge base (non-monotonic reasoning). "
            "Input: JSON with 'conditionals' (list of [conclusion, premise] pairs, "
            "premise null for facts), optional 'query_conclusion' and 'query_premise'. "
            "Returns query result."
        ),
    )
    @_jvm_required
    def query_conditional_logic(self, input: str) -> str:
        params = _parse_json_or_default(input, {})
        from argumentation_analysis.agents.core.logic.cl_handler import CLHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = CLHandler(initializer)
        kb = handler.create_knowledge_base(
            conditionals=params.get("conditionals", []),
        )
        query_conclusion = params.get("query_conclusion")
        if query_conclusion:
            entailed, msg = handler.query(
                kb, query_conclusion, params.get("query_premise")
            )
        else:
            entailed, msg = True, "KB constructed, no query specified."
        return json.dumps({"entailed": entailed, "message": msg})

    # ── SAT Solver (no JVM needed) ────────────────────────────────────

    @kernel_function(
        name="solve_sat",
        description=(
            "Solve a SAT problem using PySAT. No JVM required. "
            "Input: JSON with 'formulas' (list of PL formula strings), "
            "optional 'solver' (cadical195/glucose42/minisat22), "
            "'mode' (solve/mus/maxsat). Returns satisfiability and model."
        ),
    )
    def solve_sat(self, input: str) -> str:
        params = _parse_json_or_default(input, {"formulas": [input]})
        try:
            from argumentation_analysis.agents.core.logic.sat_handler import SATHandler
        except RuntimeError as e:
            return json.dumps({"error": str(e)})
        handler = SATHandler(params.get("solver", "cadical195"))
        formulas = params.get("formulas", [input])
        mode = params.get("mode", "solve")
        if mode == "mus":
            try:
                mus = handler.find_mus(formulas)
                return json.dumps(
                    {"mode": "mus", "mus_count": len(mus), "subsets": mus}
                )
            except RuntimeError as e:
                return json.dumps({"error": str(e)})
        is_sat, model, stats = handler.solve_formulas(formulas)
        return json.dumps(
            {
                "satisfiable": is_sat,
                "model": model,
                "statistics": stats,
            },
            default=str,
        )

    @kernel_function(
        name="analyze_setaf",
        description="Analyze a Set Argumentation Framework with collective attacks",
    )
    @_jvm_required
    def analyze_setaf(self, input: str) -> str:
        params = _parse_json_or_default(input, {"arguments": [], "set_attacks": []})
        from argumentation_analysis.agents.core.logic.setaf_handler import SetAFHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = SetAFHandler(initializer)
        result = handler.analyze_setaf(
            arguments=params.get("arguments", []),
            attacks=params.get("set_attacks", []),
            semantics=params.get("semantics", "grounded"),
        )
        return json.dumps(result, default=str)

    @kernel_function(
        name="analyze_weighted_framework",
        description="Analyze a Weighted AF with numeric attack weights",
    )
    @_jvm_required
    def analyze_weighted_framework(self, input: str) -> str:
        params = _parse_json_or_default(
            input, {"arguments": [], "weighted_attacks": []}
        )
        from argumentation_analysis.agents.core.logic.weighted_handler import (
            WeightedHandler,
        )
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = WeightedHandler(initializer)
        result = handler.analyze_weighted_framework(
            arguments=params.get("arguments", []),
            attacks=params.get("weighted_attacks", []),
            semantics=params.get("semantics", "grounded"),
        )
        return json.dumps(result, default=str)

    @kernel_function(
        name="analyze_social_framework",
        description="Analyze a Social AF with voting and attack structure",
    )
    @_jvm_required
    def analyze_social_framework(self, input: str) -> str:
        params = _parse_json_or_default(input, {"arguments": [], "attacks": []})
        from argumentation_analysis.agents.core.logic.social_handler import (
            SocialHandler,
        )
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = SocialHandler(initializer)
        votes = params.get("votes", {})
        if votes:
            votes = {
                k: tuple(v) if isinstance(v, list) else v for k, v in votes.items()
            }
        result = handler.analyze_social_framework(
            arguments=params.get("arguments", []),
            attacks=params.get("attacks", []),
            votes=votes,
        )
        return json.dumps(result, default=str)

    @kernel_function(
        name="analyze_epistemic_framework",
        description="Analyze an Epistemic AF with multi-agent belief states",
    )
    @_jvm_required
    def analyze_epistemic_framework(self, input: str) -> str:
        params = _parse_json_or_default(input, {"arguments": [], "attacks": []})
        from argumentation_analysis.agents.core.logic.eaf_handler import EAFHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = EAFHandler(initializer)
        result = handler.analyze_epistemic_framework(
            arguments=params.get("arguments", []),
            attacks=params.get("attacks", []),
            epistemic_beliefs=params.get("epistemic_beliefs"),
            semantics=params.get("semantics", "grounded"),
        )
        return json.dumps(result, default=str)

    @kernel_function(
        name="analyze_delp",
        description="Analyze a Defeasible Logic Program with dialectical trees",
    )
    @_jvm_required
    def analyze_delp(self, input: str) -> str:
        params = _parse_json_or_default(input, {"program": input})
        from argumentation_analysis.agents.core.logic.delp_handler import DeLPHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = DeLPHandler(initializer)
        result = handler.analyze_delp(
            program_text=params.get("program", input),
            queries=params.get("queries", []),
            criterion=params.get("criterion", "generalized_specificity"),
        )
        return json.dumps(result, default=str)

    @kernel_function(
        name="check_qbf",
        description="Check validity of a Quantified Boolean Formula",
    )
    @_jvm_required
    def check_qbf(self, input: str) -> str:
        params = _parse_json_or_default(input, {"formula": input, "quantifiers": []})
        from argumentation_analysis.agents.core.logic.qbf_handler import QBFHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = QBFHandler(initializer)
        result = handler.analyze_qbf(
            quantifiers=params.get("quantifiers", []),
            formula_str=params.get("formula", input),
        )
        return json.dumps(result, default=str)
