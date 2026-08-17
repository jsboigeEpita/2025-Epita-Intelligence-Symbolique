"""
Tweety Logic SK plugin — exposes all Tweety logic handlers to LLM agents (#91).

Provides @kernel_function methods wrapping each of the 15+ logic handlers,
allowing LLM agents in AgentGroupChat to invoke formal reasoning directly.

Each method:
1. Parses string input (a JSON object — #1774: unparsable input renders a
   structured error naming the keys received and expected, never a verdict)
2. Delegates to the appropriate handler via asyncio.to_thread
3. Returns a JSON string result

Gracefully handles JVM unavailability (returns error message instead of crashing).
"""

import asyncio
import functools
import json
import logging
from typing import Optional

from semantic_kernel.functions import kernel_function

from argumentation_analysis.plugins.kernel_input import parse_kernel_json_object

logger = logging.getLogger(__name__)

# Check JVM availability once
_JVM_AVAILABLE = False
try:
    import jpype

    _JVM_AVAILABLE = jpype.isJVMStarted()
except ImportError:
    pass


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

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not _check_jvm():
            return json.dumps(
                {
                    "error": "JVM not available",
                    "message": "Tweety requires JVM. Start it via jvm_setup.initialize_jvm().",
                }
            )
        return func(self, *args, **kwargs)

    return wrapper


def _ready_initializer():
    """#1775: a bare ``TweetyInitializer()`` never loads the Tweety classes,
    so the handler guards rejected a booted JVM and axis availability depended
    on which tools happened to run first in the process. Warm the initializer
    explicitly (idempotent after the first call, traced) before constructing
    handlers."""
    from argumentation_analysis.agents.core.logic.tweety_initializer import (
        TweetyInitializer,
    )

    initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
    if not initializer.is_jvm_ready():
        logger.info(
            "#1775: Tweety classes not loaded on this path — warming the "
            "initializer before handler construction so axis availability "
            "does not depend on call order."
        )
        initializer.ensure_jvm_and_components_are_ready()
    return initializer


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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["arguments", "attacks", "semantics"],
            required_keys=["arguments"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.af_handler import AFHandler

        # CONV-B #1333 (po-2025): AFHandler requires an ``initializer_instance``
        # (af_handler.py:38) and exposes ``analyze_dung_framework`` -- NOT
        # ``compute_extensions``. Same dead-cable bug class as the modal decider
        # (#1371): the previous call constructed the handler with no args
        # (TypeError) and invoked a nonexistent method (AttributeError), so the
        # FormalAgent's prescribed ETAPE 3 (Dung analysis) crashed at call time.
        initializer = _ready_initializer()
        handler = AFHandler(initializer)
        args = params.get("arguments", [])
        attacks = params.get("attacks", [])
        semantics = params.get("semantics", "preferred")
        result = handler.analyze_dung_framework(args, attacks, semantics)
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
        params, err = parse_kernel_json_object(
            input, expected_keys=["formulas"], required_keys=["formulas"]
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge()
        formulas = params.get("formulas", [])
        if not isinstance(formulas, list):
            formulas = [str(formulas)]
        kb_str = "\n".join(str(f) for f in formulas)
        # CONV-B #1333 (po-2025): TweetyBridge.check_consistency returns a
        # ``(bool, str)`` tuple; ``json.dumps(tuple)`` serialized it as a JSON
        # *array* ``[true, "..."]`` instead of the documented
        # ``{"is_consistent": ...}`` object, breaking the SK tool-call contract.
        is_consistent, message = bridge.check_consistency(
            kb_str, logic_type="propositional"
        )
        return json.dumps(
            {
                "is_consistent": is_consistent,
                "belief_set": kb_str[:200],
                "truncated": len(kb_str) > 200,
                "message": message,
            },
            default=str,
        )

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
        params, err = parse_kernel_json_object(
            input, expected_keys=["formulas"], required_keys=["formulas"]
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler

        handler = FOLHandler()
        formulas = params.get("formulas", [])
        if not isinstance(formulas, list):
            formulas = [str(formulas)]
        # CONV-B #1333 (po-2025): FOLHandler.check_consistency accepts a
        # Tweety-syntax STRING (or a Java FolBeliefSet), NOT a Python list —
        # passing the list raised ``'list' object has no attribute 'size'``.
        belief_set_str = "\n".join(str(f) for f in formulas)
        is_consistent, message = handler.check_consistency(belief_set_str)
        return json.dumps(
            {
                "is_consistent": is_consistent,
                "belief_set": belief_set_str[:200],
                "truncated": len(belief_set_str) > 200,
                "message": message,
            },
            default=str,
        )

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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["formula", "logic_type"],
            required_keys=["formula"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.modal_handler import ModalHandler

        # CONV-B #1333 (po-2025): ``ModalHandler`` requires an
        # ``initializer_instance`` in its constructor and exposes
        # ``is_modal_kb_consistent`` (query-based consistency, #1205); the
        # previous call constructed the handler with no args (TypeError) and
        # invoked a nonexistent ``check_satisfiability`` (AttributeError).
        initializer = _ready_initializer()
        handler = ModalHandler(initializer)
        formula = params.get("formula", "")
        is_consistent, message = handler.is_modal_kb_consistent(str(formula))
        # #1339: name the RESOLVED solver in the verdict (SPASS when
        # auto-routed) — the genuine-solver invariant (#1019), surfacing which
        # reasoner actually decided rather than the configured default.
        solver_name = handler._resolve_active_solver_choice().value
        return json.dumps(
            {
                "is_consistent": is_consistent,
                "formula": str(formula)[:200],
                "solver": solver_name,
                "message": message,
            },
            default=str,
        )

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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["arguments", "attacks", "method"],
            required_keys=["arguments"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.ranking_handler import (
            RankingHandler,
        )

        handler = RankingHandler()
        args = params.get("arguments", [])
        # #1774 (triage R820): empty framework is a real INPUT problem — the
        # handler AIOOBEs (rank of nothing), render it as a structured error
        # instead of a naked RuntimeError.
        if not args:
            return json.dumps(
                {
                    "error": "Empty framework: 'arguments' is empty — nothing to rank",
                    "received_keys": sorted(params.keys()),
                }
            )
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["arguments", "attacks", "supports", "framework_type"],
            required_keys=["arguments"],
        )
        if params is None:
            return json.dumps(err)
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
        # Definitional pair required: the "extensions: [[]]" verdict must only
        # be reachable from an explicitly-empty framework (#1774 §3/§4).
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["assumptions", "rules", "contraries", "semantics"],
            required_keys=["assumptions", "rules"],
        )
        if params is None:
            return json.dumps(err)
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["statements", "acceptance_conditions", "semantics"],
            required_keys=["statements"],
        )
        if params is None:
            return json.dumps(err)
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
        # Definitional pair required (same rationale as analyze_aba): an
        # extensions verdict implies an explicitly-specified framework.
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["strict_rules", "defeasible_rules", "axioms"],
            required_keys=["strict_rules", "defeasible_rules"],
        )
        if params is None:
            return json.dumps(err)
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
        # Definitional pair required: a revision needs both a base and a belief.
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["belief_set", "new_belief", "method"],
            required_keys=["belief_set", "new_belief"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.belief_revision_handler import (
            BeliefRevisionHandler,
        )

        handler = BeliefRevisionHandler()
        result = handler.revise(
            params.get("belief_set", []),
            params["new_belief"],
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["arguments", "attacks", "probabilities"],
            required_keys=["arguments"],
        )
        if params is None:
            return json.dumps(err)
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=[
                "proponent_args",
                "proponent_attacks",
                "opponent_args",
                "opponent_attacks",
                "topic",
            ],
            required_keys=["proponent_args"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.dialogue_handler import (
            DialogueHandler,
        )

        handler = DialogueHandler()
        result = handler.execute_dialogue(
            params.get("proponent_args", []),
            params.get("proponent_attacks", []),
            params.get("opponent_args", []),
            params.get("opponent_attacks", []),
            params.get("topic"),
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["tbox", "abox_concepts", "abox_roles"],
            required_keys=["tbox"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.dl_handler import DLHandler

        initializer = _ready_initializer()
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["conditionals", "query_conclusion", "query_premise"],
            required_keys=["conditionals"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.cl_handler import CLHandler

        initializer = _ready_initializer()
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["formulas", "solver", "mode"],
            required_keys=["formulas"],
        )
        if params is None:
            return json.dumps(err)
        try:
            from argumentation_analysis.agents.core.logic.sat_handler import SATHandler
        except RuntimeError as e:
            return json.dumps({"error": str(e)})
        handler = SATHandler(params.get("solver", "cadical195"))
        formulas = params.get("formulas", [])
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["arguments", "set_attacks", "semantics"],
            required_keys=["arguments"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.setaf_handler import SetAFHandler

        initializer = _ready_initializer()
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["arguments", "weighted_attacks", "semantics"],
            required_keys=["arguments"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.weighted_handler import (
            WeightedHandler,
        )

        initializer = _ready_initializer()
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["arguments", "attacks", "votes"],
            required_keys=["arguments"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.social_handler import (
            SocialHandler,
        )

        initializer = _ready_initializer()
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["arguments", "attacks", "epistemic_beliefs", "semantics"],
            required_keys=["arguments"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.eaf_handler import EAFHandler

        initializer = _ready_initializer()
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["program", "queries", "criterion"],
            required_keys=["program"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.delp_handler import DeLPHandler

        initializer = _ready_initializer()
        handler = DeLPHandler(initializer)
        result = handler.analyze_delp(
            program_text=params.get("program", ""),
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["formula", "quantifiers"],
            required_keys=["formula"],
        )
        if params is None:
            return json.dumps(err)
        from argumentation_analysis.agents.core.logic.qbf_handler import QBFHandler

        initializer = _ready_initializer()
        handler = QBFHandler(initializer)
        result = handler.analyze_qbf(
            quantifiers=params.get("quantifiers", []),
            formula_str=params.get("formula", ""),
        )
        return json.dumps(result, default=str)
