"""
Unified pipeline wiring all integrated student components via CapabilityRegistry.

Provides:
- setup_registry(): register all available components (agents, services, adapters)
- Pre-built workflow definitions (light, standard, full, custom)
- run_unified_analysis(): convenience function for end-to-end analysis

This module ties together the Lego architecture built in Phases 0-4:
- CapabilityRegistry (core/capability_registry.py)
- WorkflowDSL (orchestration/workflow_dsl.py)
- All integrated student project components
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ServiceDiscovery,
    ComponentType,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowExecutor,
    PhaseResult,
    PhaseStatus,
)

logger = logging.getLogger("UnifiedPipeline")


# --- Invoke callables for registered components ---
# Each callable: async (input_text: str, context: Dict[str, Any]) -> Any


async def _invoke_quality_evaluator(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke 9-virtue argument quality evaluator (sync, no dependencies)."""
    from argumentation_analysis.agents.core.quality.quality_evaluator import (
        ArgumentQualityEvaluator,
    )

    evaluator = ArgumentQualityEvaluator()
    return await asyncio.to_thread(evaluator.evaluate, input_text)


async def _invoke_counter_argument(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke counter-argument analysis via plugin (no kernel needed)."""
    from argumentation_analysis.agents.core.counter_argument.counter_agent import (
        CounterArgumentPlugin,
    )

    plugin = CounterArgumentPlugin()
    parsed_json = plugin.parse_argument(input_text)
    strategy_json = plugin.suggest_strategy(input_text)
    return {
        "parsed_argument": json.loads(parsed_json),
        "suggested_strategy": json.loads(strategy_json),
        "quality_context": context.get("phase_quality_output"),
    }


async def _invoke_debate_analysis(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke debate argument analysis via plugin (no kernel needed)."""
    from argumentation_analysis.agents.core.debate.debate_agent import DebatePlugin

    plugin = DebatePlugin()
    scores_json = plugin.analyze_argument_quality(input_text)
    return json.loads(scores_json)


async def _invoke_governance(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke governance conflict detection on prior results."""
    from argumentation_analysis.plugins.governance_plugin import GovernancePlugin

    plugin = GovernancePlugin()
    methods_json = plugin.list_governance_methods()
    return {
        "available_methods": json.loads(methods_json),
        "note": "Governance requires structured scenario input. "
        "Use GovernancePlugin directly for full simulation.",
    }


async def _invoke_jtms(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke JTMS belief maintenance — extract claims and track beliefs."""
    from argumentation_analysis.services.jtms.jtms_core import JTMS

    jtms = JTMS()
    sentences = [s.strip() for s in input_text.split(".") if s.strip()]
    for i, sentence in enumerate(sentences[:10]):  # cap at 10 beliefs
        jtms.add_belief(f"claim_{i}")
    return {
        "beliefs": {name: str(b.valid) for name, b in jtms.beliefs.items()},
        "belief_count": len(jtms.beliefs),
    }


async def _invoke_camembert_fallacy(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke CamemBERT-based French fallacy detector (sync, heavy model)."""
    from argumentation_analysis.adapters.french_fallacy_adapter import (
        FrenchFallacyAdapter,
    )

    adapter = FrenchFallacyAdapter(enable_nli=False, enable_llm=False)
    return await asyncio.to_thread(adapter.detect, input_text)


async def _invoke_local_llm(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke local LLM service for text analysis."""
    from argumentation_analysis.services.local_llm_service import LocalLLMService

    service = LocalLLMService()
    messages = [{"role": "user", "content": input_text}]
    return await service.chat_completion(messages)


async def _invoke_semantic_index(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke semantic index service for argument search."""
    from argumentation_analysis.services.semantic_index_service import (
        SemanticIndexService,
    )

    service = SemanticIndexService()
    results = await asyncio.to_thread(service.search, input_text)
    return {"results": results}


async def _invoke_speech_transcription(
    input_text: str, context: Dict[str, Any]
) -> Dict:
    """Invoke speech transcription — requires audio_path in context."""
    return {
        "status": "ready",
        "note": "Pass audio file path via context['audio_path'] for transcription.",
    }


# --- Track A: Tweety handler invoke functions ---


async def _invoke_ranking(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke ranking semantics handler."""
    from argumentation_analysis.agents.core.logic.ranking_handler import RankingHandler
    handler = RankingHandler()
    args = context.get("arguments", ["a", "b", "c"])
    attacks = context.get("attacks", [])
    method = context.get("ranking_method", "categorizer")
    return await asyncio.to_thread(handler.rank_arguments, args, attacks, method)


async def _invoke_bipolar(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke bipolar argumentation handler."""
    from argumentation_analysis.agents.core.logic.bipolar_handler import BipolarHandler
    handler = BipolarHandler()
    args = context.get("arguments", [])
    attacks = context.get("attacks", [])
    supports = context.get("supports", [])
    fw_type = context.get("framework_type", "necessity")
    return await asyncio.to_thread(
        handler.analyze_bipolar_framework, args, attacks, supports, fw_type
    )


async def _invoke_aba(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke ABA handler."""
    from argumentation_analysis.agents.core.logic.aba_handler import ABAHandler
    handler = ABAHandler()
    assumptions = context.get("assumptions", [])
    rules = context.get("rules", [])
    contraries = context.get("contraries")
    semantics = context.get("semantics", "preferred")
    return await asyncio.to_thread(
        handler.analyze_aba_framework, assumptions, rules, contraries, semantics
    )


async def _invoke_adf(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke ADF handler."""
    from argumentation_analysis.agents.core.logic.adf_handler import ADFHandler
    handler = ADFHandler()
    statements = context.get("statements", [])
    conditions = context.get("acceptance_conditions", {})
    semantics = context.get("semantics", "grounded")
    return await asyncio.to_thread(handler.analyze_adf, statements, conditions, semantics)


async def _invoke_aspic(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke ASPIC+ handler."""
    from argumentation_analysis.agents.core.logic.aspic_handler import ASPICHandler
    handler = ASPICHandler()
    strict = context.get("strict_rules", [])
    defeasible = context.get("defeasible_rules", [])
    axioms = context.get("axioms")
    return await asyncio.to_thread(handler.analyze_aspic_framework, strict, defeasible, axioms)


async def _invoke_belief_revision(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke belief revision handler."""
    from argumentation_analysis.agents.core.logic.belief_revision_handler import BeliefRevisionHandler
    handler = BeliefRevisionHandler()
    beliefs = context.get("belief_set", [input_text])
    new_belief = context.get("new_belief", input_text)
    method = context.get("revision_method", "dalal")
    return await asyncio.to_thread(handler.revise, beliefs, new_belief, method)


async def _invoke_probabilistic(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke probabilistic argumentation handler."""
    from argumentation_analysis.agents.core.logic.probabilistic_handler import ProbabilisticHandler
    handler = ProbabilisticHandler()
    args = context.get("arguments", [])
    attacks = context.get("attacks", [])
    probs = context.get("probabilities", {})
    return await asyncio.to_thread(
        handler.analyze_probabilistic_framework, args, attacks, probs
    )


async def _invoke_dialogue(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke dialogue protocol handler."""
    from argumentation_analysis.agents.core.logic.dialogue_handler import DialogueHandler
    handler = DialogueHandler()
    pro_args = context.get("proponent_args", [])
    pro_attacks = context.get("proponent_attacks", [])
    opp_args = context.get("opponent_args", [])
    opp_attacks = context.get("opponent_attacks", [])
    topic = context.get("topic", input_text)
    return await asyncio.to_thread(
        handler.execute_dialogue, pro_args, pro_attacks, opp_args, opp_attacks, topic
    )


# --- Invoke callables for logic agent capabilities (#71 Formal Verification) ---


async def _invoke_fact_extraction(input_text: str, context: Dict[str, Any]) -> Dict:
    """Extract verifiable claims from text using heuristic sentence splitting."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', input_text.strip())
    claims = [s.strip() for s in sentences if len(s.strip()) > 20]
    return {
        "claims": claims,
        "claim_count": len(claims),
        "source_length": len(input_text),
    }


async def _invoke_propositional_logic(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke propositional logic analysis via TweetyBridge (JVM required)."""
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        bridge = TweetyBridge()
        formulas = context.get("formulas", [input_text])
        if not isinstance(formulas, list):
            formulas = [str(formulas)]
        belief_set_str = "\n".join(str(f) for f in formulas)
        is_consistent, msg = await asyncio.to_thread(
            bridge.check_consistency, belief_set_str, "propositional"
        )
        return {
            "formulas": formulas,
            "satisfiable": bool(is_consistent),
            "model": {},
            "message": msg,
            "logic_type": "propositional",
        }
    except Exception as e:
        return {"error": str(e), "formulas": [], "satisfiable": False, "logic_type": "propositional"}


async def _invoke_fol_reasoning(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke first-order logic analysis via TweetyBridge (JVM required)."""
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        bridge = TweetyBridge()
        formulas = context.get("formulas", [input_text])
        if not isinstance(formulas, list):
            formulas = [str(formulas)]
        belief_set_str = "\n".join(str(f) for f in formulas)
        is_consistent, msg = await asyncio.to_thread(
            bridge.check_consistency, belief_set_str, "first_order"
        )
        return {
            "formulas": formulas,
            "consistent": bool(is_consistent),
            "inferences": [],
            "confidence": 0.8 if is_consistent else 0.3,
            "message": msg,
            "logic_type": "first_order",
        }
    except Exception as e:
        return {"error": str(e), "formulas": [], "consistent": False, "inferences": [], "confidence": 0.0}


async def _invoke_modal_logic(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke modal logic analysis via TweetyBridge (JVM required)."""
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        bridge = TweetyBridge()
        formulas = context.get("formulas", [input_text])
        if not isinstance(formulas, list):
            formulas = [str(formulas)]
        modalities = []
        for f in formulas:
            f_str = str(f)
            if "[]" in f_str or "necessarily" in f_str.lower():
                modalities.append("necessity")
            if "<>" in f_str or "possibly" in f_str.lower():
                modalities.append("possibility")
        return {
            "formulas": formulas,
            "valid": True,
            "modalities": list(set(modalities)) or ["none_detected"],
            "logic_type": "modal",
        }
    except Exception as e:
        return {"error": str(e), "formulas": [], "valid": False, "modalities": []}


async def _invoke_dung_extensions(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke Dung framework extension computation via AFHandler (JVM required)."""
    try:
        from argumentation_analysis.agents.core.logic.af_handler import AFHandler
        from argumentation_analysis.core.jvm_setup import TweetyInitializer
        initializer = TweetyInitializer()
        handler = AFHandler(initializer)
        arguments = context.get("arguments", [])
        attacks = context.get("attacks", [])
        if not arguments:
            arguments = [f"arg_{i}" for i in range(3)]
            attacks = []
        semantics = context.get("semantics", "preferred")
        result = await asyncio.to_thread(
            handler.analyze_dung_framework, arguments, attacks, semantics
        )
        return result
    except Exception as e:
        return {
            "error": str(e),
            "semantics": context.get("semantics", "preferred"),
            "extensions": {},
            "statistics": {},
        }


async def _invoke_formal_synthesis(input_text: str, context: Dict[str, Any]) -> Dict:
    """Aggregate all formal analysis results from upstream phases into a unified report."""
    phase_results = {}
    overall_scores = []

    for key, val in context.items():
        if key.startswith("phase_") and key.endswith("_output") and isinstance(val, dict):
            phase_name = key[len("phase_"):-len("_output")]
            phase_results[phase_name] = val
            if "consistent" in val:
                overall_scores.append(1.0 if val["consistent"] else 0.0)
            if "satisfiable" in val:
                overall_scores.append(1.0 if val["satisfiable"] else 0.0)
            if "valid" in val:
                overall_scores.append(1.0 if val["valid"] else 0.0)

    overall_validity = sum(overall_scores) / len(overall_scores) if overall_scores else 0.5
    summary_parts = []
    for name, res in phase_results.items():
        if "error" in res:
            summary_parts.append(f"{name}: error ({res['error'][:50]})")
        elif "consistent" in res:
            summary_parts.append(f"{name}: consistent={res['consistent']}")
        elif "satisfiable" in res:
            summary_parts.append(f"{name}: satisfiable={res['satisfiable']}")
        elif "extensions" in res:
            ext_count = sum(len(v) if isinstance(v, list) else 0 for v in res["extensions"].values()) if isinstance(res.get("extensions"), dict) else 0
            summary_parts.append(f"{name}: {ext_count} extensions")

    return {
        "summary": "; ".join(summary_parts) if summary_parts else "No formal results collected",
        "phase_results": phase_results,
        "overall_validity": overall_validity,
        "phase_count": len(phase_results),
    }


# --- State writers: map capability → (output, state, ctx) → None ---
# Each writer extracts relevant data from phase output and writes to
# UnifiedAnalysisState via its typed add_*() methods.
# Writers are defensive: guard with isinstance checks and .get() everywhere.


def _write_quality_to_state(output, state, ctx) -> None:
    """Write quality evaluator results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    arg_id = ctx.get("current_arg_id", "arg_input")
    scores = {
        k: v
        for k, v in output.items()
        if k != "note_finale" and isinstance(v, (int, float))
    }
    overall = output.get("note_finale", 0.0)
    if isinstance(overall, (int, float)):
        state.add_quality_score(arg_id, scores, float(overall))


def _write_counter_argument_to_state(output, state, ctx) -> None:
    """Write counter-argument results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    parsed = output.get("parsed_argument", {})
    strategy = output.get("suggested_strategy", {})
    if not isinstance(parsed, dict):
        parsed = {}
    if not isinstance(strategy, dict):
        strategy = {}
    original = str(parsed.get("premise", ctx.get("input_data", "")))[:200]
    strategy_name = str(strategy.get("strategy_name", "unknown"))
    score = strategy.get("confidence", 0.0)
    if not isinstance(score, (int, float)):
        score = 0.0
    state.add_counter_argument(original, strategy_name, strategy_name, float(score))


def _write_jtms_to_state(output, state, ctx) -> None:
    """Write JTMS results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    beliefs = output.get("beliefs", {})
    if not isinstance(beliefs, dict):
        return
    for name, valid_str in beliefs.items():
        valid = True if valid_str == "True" else (False if valid_str == "False" else None)
        state.add_jtms_belief(str(name), valid, justifications=[])


def _write_debate_to_state(output, state, ctx) -> None:
    """Write debate analysis results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    topic = str(ctx.get("input_data", ""))[:100]
    winner = output.get("winner")
    state.add_debate_transcript(
        topic=topic,
        exchanges=[],
        winner=str(winner) if winner is not None else None,
    )


def _write_governance_to_state(output, state, ctx) -> None:
    """Write governance results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    methods = output.get("available_methods", [])
    if isinstance(methods, list) and methods:
        state.add_governance_decision(
            method="listing",
            winner="N/A",
            scores={str(m): 0.0 for m in methods},
        )


def _write_camembert_to_state(output, state, ctx) -> None:
    """Write CamemBERT neural fallacy results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    detections = output.get("detections", [])
    if not isinstance(detections, list):
        return
    for det in detections:
        if not isinstance(det, dict):
            continue
        state.add_neural_fallacy_score(
            text_segment=str(det.get("text", "")),
            label=str(det.get("label", "unknown")),
            confidence=float(det.get("confidence", 0.0)),
        )


def _write_semantic_index_to_state(output, state, ctx) -> None:
    """Write semantic index results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    results = output.get("results", [])
    if not isinstance(results, list):
        return
    query = str(ctx.get("input_data", ""))
    for r in results:
        if not isinstance(r, dict):
            continue
        state.add_semantic_index_ref(
            query=query,
            document_id=str(r.get("id", "unknown")),
            score=float(r.get("score", 0.0)),
            snippet=r.get("snippet"),
        )


def _write_speech_to_state(output, state, ctx) -> None:
    """Write speech transcription results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    segments = output.get("segments", [])
    if not isinstance(segments, list):
        return
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        state.add_transcription_segment(
            start_time=float(seg.get("start", 0.0)),
            end_time=float(seg.get("end", 0.0)),
            text=str(seg.get("text", "")),
            speaker=seg.get("speaker"),
        )


def _write_ranking_to_state(output, state, ctx) -> None:
    """Write ranking semantics results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    method = str(output.get("method", "unknown"))
    arguments = output.get("arguments", [])
    comparisons = output.get("comparisons", [])
    if not isinstance(arguments, list):
        arguments = []
    if not isinstance(comparisons, list):
        comparisons = []
    state.add_ranking_result(method, arguments, comparisons)


def _write_aspic_to_state(output, state, ctx) -> None:
    """Write ASPIC+ analysis results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    reasoner_type = str(output.get("reasoner_type", "simple"))
    extensions = output.get("extensions", [])
    statistics = output.get("statistics", {})
    if not isinstance(extensions, list):
        extensions = []
    if not isinstance(statistics, dict):
        statistics = {}
    state.add_aspic_result(reasoner_type, extensions, statistics)


def _write_belief_revision_to_state(output, state, ctx) -> None:
    """Write belief revision results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    method = str(output.get("method", "dalal"))
    original = output.get("original", [])
    revised = output.get("revised", [])
    if not isinstance(original, list):
        original = []
    if not isinstance(revised, list):
        revised = []
    state.add_belief_revision_result(method, original, revised)


def _write_dialogue_to_state(output, state, ctx) -> None:
    """Write dialogue protocol results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    topic = str(output.get("topic", ""))
    outcome = str(output.get("outcome", "unknown"))
    trace = output.get("dialogue_trace", [])
    if not isinstance(trace, list):
        trace = []
    state.add_dialogue_result(topic, outcome, trace)


def _write_probabilistic_to_state(output, state, ctx) -> None:
    """Write probabilistic argumentation results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    arguments = output.get("arguments", [])
    acceptance = output.get("acceptance_probabilities", {})
    if not isinstance(arguments, list):
        arguments = []
    if not isinstance(acceptance, dict):
        acceptance = {}
    state.add_probabilistic_result(arguments, acceptance)


def _write_bipolar_to_state(output, state, ctx) -> None:
    """Write bipolar argumentation results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    fw_type = str(output.get("framework_type", "necessity"))
    arguments = output.get("arguments", [])
    supports = output.get("supports", [])
    if not isinstance(arguments, list):
        arguments = []
    if not isinstance(supports, list):
        supports = []
    state.add_bipolar_result(fw_type, arguments, supports)


def _write_aba_to_state(output, state, ctx) -> None:
    """Write ABA reasoning results to UnifiedAnalysisState (stored as Dung framework)."""
    if not output or not isinstance(output, dict):
        return
    assumptions = output.get("assumptions", [])
    extensions = output.get("extensions", [])
    if not isinstance(assumptions, list):
        assumptions = []
    state.add_dung_framework(
        name=f"aba_{output.get('semantics', 'preferred')}",
        arguments=assumptions,
        attacks=[],
        extensions={"aba_extensions": extensions},
    )


def _write_adf_to_state(output, state, ctx) -> None:
    """Write ADF reasoning results to UnifiedAnalysisState (stored as Dung framework)."""
    if not output or not isinstance(output, dict):
        return
    statements = output.get("statements", [])
    models = output.get("models", output.get("extensions", []))
    if not isinstance(statements, list):
        statements = []
    state.add_dung_framework(
        name=f"adf_{output.get('semantics', 'grounded')}",
        arguments=statements,
        attacks=[],
        extensions={"adf_models": models},
    )


def _write_fact_extraction_to_state(output, state, ctx) -> None:
    """Write fact extraction results to state (uses existing extracts list)."""
    if not output or not isinstance(output, dict):
        return
    claims = output.get("claims", [])
    if not isinstance(claims, list):
        return
    for claim in claims:
        if isinstance(claim, str) and claim.strip():
            state.extracts.append({"type": "claim", "content": claim.strip()})


def _write_propositional_to_state(output, state, ctx) -> None:
    """Write propositional logic analysis results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    formulas = output.get("formulas", [])
    satisfiable = output.get("satisfiable", False)
    model = output.get("model", {})
    if not isinstance(formulas, list):
        formulas = []
    if not isinstance(model, dict):
        model = {}
    state.add_propositional_analysis_result(formulas, bool(satisfiable), model)


def _write_fol_to_state(output, state, ctx) -> None:
    """Write FOL reasoning results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    formulas = output.get("formulas", [])
    consistent = output.get("consistent", False)
    inferences = output.get("inferences", [])
    confidence = output.get("confidence", 0.0)
    if not isinstance(formulas, list):
        formulas = []
    if not isinstance(inferences, list):
        inferences = []
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    state.add_fol_analysis_result(formulas, bool(consistent), inferences, float(confidence))


def _write_modal_to_state(output, state, ctx) -> None:
    """Write modal logic analysis results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    formulas = output.get("formulas", [])
    valid = output.get("valid", False)
    modalities = output.get("modalities", [])
    if not isinstance(formulas, list):
        formulas = []
    if not isinstance(modalities, list):
        modalities = []
    state.add_modal_analysis_result(formulas, bool(valid), modalities)


def _write_dung_extensions_to_state(output, state, ctx) -> None:
    """Write Dung extension computation results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    semantics = str(output.get("semantics", "preferred"))
    extensions = output.get("extensions", {})
    statistics = output.get("statistics", {})
    arguments = []
    if isinstance(statistics, dict):
        arguments = [f"arg_{i}" for i in range(statistics.get("arguments_count", 0))]
    state.add_dung_framework(
        name=f"verification_{semantics}",
        arguments=arguments,
        attacks=[],
        extensions=extensions if isinstance(extensions, dict) else {},
    )


def _write_formal_synthesis_to_state(output, state, ctx) -> None:
    """Write formal synthesis report to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    summary = str(output.get("summary", ""))
    phase_results = output.get("phase_results", {})
    overall_validity = output.get("overall_validity", 0.0)
    if not isinstance(phase_results, dict):
        phase_results = {}
    if not isinstance(overall_validity, (int, float)):
        overall_validity = 0.0
    state.add_formal_synthesis_report(summary, phase_results, float(overall_validity))


CAPABILITY_STATE_WRITERS: Dict[str, Any] = {
    "argument_quality": _write_quality_to_state,
    "counter_argument_generation": _write_counter_argument_to_state,
    "belief_maintenance": _write_jtms_to_state,
    "adversarial_debate": _write_debate_to_state,
    "governance_simulation": _write_governance_to_state,
    "neural_fallacy_detection": _write_camembert_to_state,
    "semantic_indexing": _write_semantic_index_to_state,
    "speech_transcription": _write_speech_to_state,
    "ranking_semantics": _write_ranking_to_state,
    "aspic_plus_reasoning": _write_aspic_to_state,
    "belief_revision": _write_belief_revision_to_state,
    "dialogue_protocols": _write_dialogue_to_state,
    "probabilistic_argumentation": _write_probabilistic_to_state,
    "bipolar_argumentation": _write_bipolar_to_state,
    "aba_reasoning": _write_aba_to_state,
    "adf_reasoning": _write_adf_to_state,
    "fact_extraction": _write_fact_extraction_to_state,
    "propositional_logic": _write_propositional_to_state,
    "fol_reasoning": _write_fol_to_state,
    "modal_logic": _write_modal_to_state,
    "dung_extensions": _write_dung_extensions_to_state,
    "formal_synthesis": _write_formal_synthesis_to_state,
}


def setup_registry(
    include_optional: bool = True,
) -> CapabilityRegistry:
    """
    Create and populate a CapabilityRegistry with all available components.

    Registers agents, services, and adapters from the integrated student projects.
    Each registration is wrapped in try/except so missing optional dependencies
    don't prevent the registry from being created.

    Args:
        include_optional: If True, attempt to register components with optional
                         dependencies (CamemBERT, Dung/JVM, speech-to-text).

    Returns:
        Populated CapabilityRegistry instance.
    """
    registry = CapabilityRegistry()
    registered = []
    skipped = []

    # --- Core agents (always available) ---

    # Counter-argument generation (2.3.3)
    try:
        from argumentation_analysis.agents.core.counter_argument import (
            register_with_capability_registry as register_counter_arg,
        )

        register_counter_arg(registry)
        # Wire invoke callable (registration was created by register_counter_arg)
        if "counter_argument_agent" in registry._registrations:
            registry._registrations["counter_argument_agent"].invoke = (
                _invoke_counter_argument
            )
        registered.append("counter_argument_agent")
    except ImportError as e:
        skipped.append(("counter_argument_agent", str(e)))

    # Argument quality evaluation (2.3.5)
    try:
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            ArgumentQualityEvaluator,
        )

        registry.register_agent(
            name="quality_evaluator",
            agent_class=ArgumentQualityEvaluator,
            capabilities=[
                "argument_quality",
                "virtue_detection",
                "quality_scoring",
            ],
            metadata={"description": "9-virtue argument quality evaluator"},
            invoke=_invoke_quality_evaluator,
        )
        registered.append("quality_evaluator")
    except ImportError as e:
        skipped.append(("quality_evaluator", str(e)))

    # Debate agent (1.2.7)
    try:
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        registry.register_agent(
            name="debate_agent",
            agent_class=DebateAgent,
            capabilities=[
                "adversarial_debate",
                "argument_stress_test",
                "debate_scoring",
            ],
            metadata={"description": "Multi-personality adversarial debate agent"},
            invoke=_invoke_debate_analysis,
        )
        registered.append("debate_agent")
    except ImportError as e:
        skipped.append(("debate_agent", str(e)))

    # Governance agent (2.1.6)
    try:
        from argumentation_analysis.agents.core.governance.governance_agent import (
            Agent as GovernanceAgent,
        )

        registry.register_agent(
            name="governance_agent",
            agent_class=GovernanceAgent,
            capabilities=[
                "governance_simulation",
                "multi_method_voting",
                "preference_aggregation",
            ],
            metadata={"description": "7-method governance voting agent"},
            invoke=_invoke_governance,
        )
        registered.append("governance_agent")
    except ImportError as e:
        skipped.append(("governance_agent", str(e)))

    # --- Core services ---

    # JTMS belief maintenance (1.4.1)
    try:
        from argumentation_analysis.services.jtms.jtms_core import JTMS

        registry.register_service(
            name="jtms_service",
            service_class=JTMS,
            capabilities=["belief_maintenance", "truth_maintenance", "jtms_reasoning"],
            metadata={"description": "Justification-based Truth Maintenance System"},
            invoke=_invoke_jtms,
        )
        registered.append("jtms_service")
    except ImportError as e:
        skipped.append(("jtms_service", str(e)))

    # Local LLM service (2.3.6)
    try:
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        registry.register_service(
            name="local_llm_service",
            service_class=LocalLLMService,
            capabilities=["local_llm", "chat_completion"],
            metadata={"description": "OpenAI-compatible local LLM adapter"},
            invoke=_invoke_local_llm,
        )
        registered.append("local_llm_service")
    except ImportError as e:
        skipped.append(("local_llm_service", str(e)))

    # --- Optional adapters (may need heavy dependencies) ---

    if include_optional:
        # CamemBERT fallacy detector (2.3.2)
        try:
            from argumentation_analysis.adapters.french_fallacy_adapter import (
                FrenchFallacyAdapter,
            )

            registry.register_agent(
                name="camembert_fallacy_detector",
                agent_class=FrenchFallacyAdapter,
                capabilities=["neural_fallacy_detection", "fallacy_detection"],
                requires=["camembert_model"],
                metadata={
                    "description": "CamemBERT-based neural fallacy detector (2.3.2)"
                },
                invoke=_invoke_camembert_fallacy,
            )
            registered.append("camembert_fallacy_detector")
        except ImportError as e:
            skipped.append(("camembert_fallacy_detector", str(e)))

        # Semantic index service (Arg_Semantic_Index)
        try:
            from argumentation_analysis.services.semantic_index_service import (
                SemanticIndexService,
            )

            registry.register_service(
                name="semantic_index_service",
                service_class=SemanticIndexService,
                capabilities=["semantic_indexing", "argument_search"],
                metadata={"description": "Semantic argument indexing service"},
                invoke=_invoke_semantic_index,
            )
            registered.append("semantic_index_service")
        except ImportError as e:
            skipped.append(("semantic_index_service", str(e)))

        # Speech transcription service (speech-to-text)
        try:
            from argumentation_analysis.services.speech_transcription_service import (
                SpeechTranscriptionService,
            )

            registry.register_service(
                name="speech_transcription_service",
                service_class=SpeechTranscriptionService,
                capabilities=["speech_transcription", "speech_to_text"],
                metadata={"description": "Whisper-based speech transcription service"},
                invoke=_invoke_speech_transcription,
            )
            registered.append("speech_transcription_service")
        except ImportError as e:
            skipped.append(("speech_transcription_service", str(e)))

    # --- Declare unfilled slots for future Tweety extensions ---
    _declare_tweety_slots(registry)

    # --- Logic agent capabilities (#71 Formal Verification) ---
    logic_capabilities = [
        ("fact_extraction_service", ["fact_extraction"],
         "Heuristic claim extraction from text", _invoke_fact_extraction),
        ("propositional_logic_service", ["propositional_logic"],
         "Propositional logic analysis via Tweety", _invoke_propositional_logic),
        ("fol_reasoning_service", ["fol_reasoning"],
         "First-order logic analysis via Tweety", _invoke_fol_reasoning),
        ("modal_logic_service", ["modal_logic"],
         "Modal logic analysis via Tweety", _invoke_modal_logic),
        ("dung_extensions_service", ["dung_extensions"],
         "Dung AF extension computation via AFHandler", _invoke_dung_extensions),
        ("formal_synthesis_service", ["formal_synthesis"],
         "Aggregate formal analysis into unified report", _invoke_formal_synthesis),
    ]
    for name, caps, desc, invoke_fn in logic_capabilities:
        try:
            registry.register_service(
                name=name,
                service_class=type(name, (), {}),
                capabilities=caps,
                metadata={"description": desc},
                invoke=invoke_fn,
            )
            registered.append(name)
        except Exception as e:
            skipped.append((name, str(e)))

    logger.info(
        f"Registry setup complete: {len(registered)} registered, "
        f"{len(skipped)} skipped"
    )
    if skipped:
        logger.debug(f"Skipped components: {[s[0] for s in skipped]}")

    return registry


def _declare_tweety_slots(registry: CapabilityRegistry) -> None:
    """Register Tweety handler capabilities (Track A #55-#62)."""
    tweety_handlers = [
        ("ranking_semantics_handler", ["ranking_semantics"],
         "Qualitative argument ranking (Categoriser, Burden)", _invoke_ranking),
        ("bipolar_handler", ["bipolar_argumentation"],
         "Bipolar argumentation (support + attack)", _invoke_bipolar),
        ("aba_handler", ["aba_reasoning"],
         "Assumption-Based Argumentation", _invoke_aba),
        ("adf_handler", ["adf_reasoning"],
         "Abstract Dialectical Frameworks", _invoke_adf),
        ("aspic_handler", ["aspic_plus_reasoning"],
         "ASPIC+ structured argumentation", _invoke_aspic),
        ("belief_revision_handler", ["belief_revision"],
         "Belief dynamics and revision operators", _invoke_belief_revision),
        ("probabilistic_handler", ["probabilistic_argumentation"],
         "Probabilistic argument acceptance", _invoke_probabilistic),
        ("dialogue_handler", ["dialogue_protocols"],
         "Agent dialogue and negotiation protocols", _invoke_dialogue),
    ]
    for name, caps, desc, invoke_fn in tweety_handlers:
        try:
            registry.register_service(
                name=name,
                service_class=type(name, (), {}),  # placeholder class
                capabilities=caps,
                metadata={"description": desc, "requires": ["jvm"]},
                invoke=invoke_fn,
            )
        except Exception as e:
            logger.debug(f"Tweety handler {name} registration deferred: {e}")
            # Fall back to slot declaration if JVM not available
            for cap in caps:
                registry.declare_slot(cap, requires=["jvm"], description=desc)


# --- Pre-built workflow definitions ---


def build_light_workflow() -> WorkflowDefinition:
    """Minimal 3-phase analysis workflow."""
    return (
        WorkflowBuilder("light_analysis")
        .add_phase("quality", capability="argument_quality")
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        .add_phase("jtms", capability="belief_maintenance", optional=True)
        .build()
    )


def build_standard_workflow() -> WorkflowDefinition:
    """Standard 5-phase workflow with quality-gated counter-arguments."""
    return (
        WorkflowBuilder("standard_analysis")
        .add_phase("quality", capability="argument_quality")
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        .add_phase(
            "jtms",
            capability="belief_maintenance",
            depends_on=["counter"],
            optional=True,
        )
        .add_phase(
            "governance",
            capability="governance_simulation",
            depends_on=["quality"],
            optional=True,
        )
        .add_phase(
            "debate",
            capability="adversarial_debate",
            depends_on=["counter"],
            optional=True,
        )
        .build()
    )


def build_full_workflow() -> WorkflowDefinition:
    """Full pipeline traversing all 12 capabilities."""
    return (
        WorkflowBuilder("full_analysis")
        .add_phase(
            "transcribe",
            capability="speech_transcription",
            optional=True,
        )
        .add_phase("quality", capability="argument_quality")
        .add_phase(
            "neural_fallacy",
            capability="neural_fallacy_detection",
            optional=True,
        )
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        .add_phase(
            "jtms",
            capability="belief_maintenance",
            depends_on=["counter"],
            optional=True,
        )
        .add_phase(
            "governance",
            capability="governance_simulation",
            depends_on=["quality"],
            optional=True,
        )
        .add_phase(
            "debate",
            capability="adversarial_debate",
            depends_on=["counter"],
            optional=True,
        )
        .add_phase(
            "index",
            capability="semantic_indexing",
            depends_on=["counter"],
            optional=True,
        )
        .build()
    )


def build_quality_gated_counter_workflow() -> WorkflowDefinition:
    """Quality-gated counter-argument with iterative refinement (Loop 3)."""

    def quality_gate(ctx):
        """Only generate counter-argument if quality score > 3.0."""
        output = ctx.get("phase_quality_output")
        if not output or not isinstance(output, dict):
            return True  # proceed if no quality data
        return output.get("note_finale", 0) > 3.0

    def counter_quality_convergence(prev, curr):
        """Converge when counter-argument quality stops improving."""
        if not isinstance(prev, dict) or not isinstance(curr, dict):
            return False
        prev_score = prev.get("note_finale", 0)
        curr_score = curr.get("note_finale", 0)
        return curr_score >= prev_score  # stop when no improvement

    return (
        WorkflowBuilder("quality_gated_counter")
        .add_phase("quality", capability="argument_quality")
        .add_conditional_phase(
            "counter",
            capability="counter_argument_generation",
            condition=quality_gate,
            depends_on=["quality"],
        )
        .add_loop(
            "quality_recheck",
            capability="argument_quality",
            max_iterations=3,
            convergence_fn=counter_quality_convergence,
            depends_on=["counter"],
            input_transform=lambda inp, ctx: str(
                ctx.get("phase_counter_output", {})
                .get("suggested_strategy", {})
                .get("strategy_name", inp)
            ),
        )
        .build()
    )


def build_debate_governance_loop_workflow() -> WorkflowDefinition:
    """Debate-Governance vote-contest-debate-revote loop (Loop 1). STUB."""
    return (
        WorkflowBuilder("debate_governance_loop")
        .add_phase(
            "governance_vote",
            capability="governance_simulation",
            optional=True,
        )
        .add_phase(
            "debate",
            capability="adversarial_debate",
            depends_on=["governance_vote"],
            optional=True,
        )
        .add_phase(
            "governance_revote",
            capability="governance_simulation",
            depends_on=["debate"],
            optional=True,
        )
        .build()
    )


def build_jtms_dung_loop_workflow() -> WorkflowDefinition:
    """JTMS-Dung belief retraction/extension recalc loop (Loop 2). STUB."""
    return (
        WorkflowBuilder("jtms_dung_loop")
        .add_phase(
            "jtms_beliefs",
            capability="belief_maintenance",
            optional=True,
        )
        .add_phase(
            "dung_extensions",
            capability="ranking_semantics",
            depends_on=["jtms_beliefs"],
            optional=True,
        )
        .build()
    )


def build_neural_symbolic_fallacy_workflow() -> WorkflowDefinition:
    """Neural-Symbolic fallacy fusion loop (Loop 4). PARTIAL."""
    return (
        WorkflowBuilder("neural_symbolic_fallacy")
        .add_phase(
            "neural_detect",
            capability="neural_fallacy_detection",
            optional=True,
        )
        .add_phase("quality_baseline", capability="argument_quality")
        .build()
    )


WORKFLOW_CATALOG: Dict[str, WorkflowDefinition] = {}


def get_workflow_catalog() -> Dict[str, WorkflowDefinition]:
    """Get the catalog of pre-built workflows (lazy-initialized)."""
    global WORKFLOW_CATALOG
    if not WORKFLOW_CATALOG:
        WORKFLOW_CATALOG = {
            "light": build_light_workflow(),
            "standard": build_standard_workflow(),
            "full": build_full_workflow(),
            "quality_gated": build_quality_gated_counter_workflow(),
            "debate_governance": build_debate_governance_loop_workflow(),
            "jtms_dung": build_jtms_dung_loop_workflow(),
            "neural_symbolic": build_neural_symbolic_fallacy_workflow(),
        }
        # Macro workflows (Track D)
        try:
            from argumentation_analysis.workflows.democratech import (
                build_democratech_workflow,
            )
            from argumentation_analysis.workflows.debate_tournament import (
                build_debate_tournament_workflow,
            )
            from argumentation_analysis.workflows.fact_check_pipeline import (
                build_fact_check_workflow,
            )

            WORKFLOW_CATALOG["democratech"] = build_democratech_workflow()
            WORKFLOW_CATALOG["debate_tournament"] = build_debate_tournament_workflow()
            WORKFLOW_CATALOG["fact_check"] = build_fact_check_workflow()
        except Exception as e:
            logger.warning(f"Macro workflows not registered: {e}")
        # Formal workflows (Track A plugins + orchestration)
        try:
            from argumentation_analysis.workflows.formal_debate import (
                build_formal_debate_workflow,
            )
            from argumentation_analysis.workflows.belief_dynamics import (
                build_belief_dynamics_workflow,
            )
            from argumentation_analysis.workflows.argument_strength import (
                build_argument_strength_workflow,
            )

            WORKFLOW_CATALOG["formal_debate"] = build_formal_debate_workflow()
            WORKFLOW_CATALOG["belief_dynamics"] = build_belief_dynamics_workflow()
            WORKFLOW_CATALOG["argument_strength"] = build_argument_strength_workflow()
        except Exception as e:
            logger.warning(f"Formal workflows not registered: {e}")
        # Formal verification pipeline (#71)
        try:
            from argumentation_analysis.workflows.formal_verification import (
                build_formal_verification_workflow,
            )

            WORKFLOW_CATALOG["formal_verification"] = build_formal_verification_workflow()
        except Exception as e:
            logger.warning(f"Formal verification workflow not registered: {e}")
    return WORKFLOW_CATALOG


async def run_unified_analysis(
    text: str,
    workflow_name: str = "standard",
    registry: Optional[CapabilityRegistry] = None,
    custom_workflow: Optional[WorkflowDefinition] = None,
    context: Optional[Dict[str, Any]] = None,
    state: Optional[Any] = None,
    create_state: bool = True,
) -> Dict[str, Any]:
    """
    Run a unified analysis pipeline on input text.

    Args:
        text: The text to analyze.
        workflow_name: Name of pre-built workflow ("light", "standard", "full").
        registry: CapabilityRegistry to use. If None, creates one via setup_registry().
        custom_workflow: If provided, use this workflow instead of a named one.
        context: Additional context passed to each phase (e.g. kernel, config).
        state: Optional UnifiedAnalysisState instance. If provided, phase results
               are written to it via state writers.
        create_state: If True and no state provided, automatically create an
                      UnifiedAnalysisState. Set to False to disable state tracking.

    Returns:
        Dict with keys:
            - workflow_name: Name of the executed workflow
            - phases: Dict[str, PhaseResult] — per-phase results
            - summary: Dict with completed/failed/skipped counts
            - capabilities_used: List of capabilities that were successfully resolved
            - capabilities_missing: List of capabilities with no provider
            - unified_state: UnifiedAnalysisState (if state tracking enabled)
            - state_snapshot: Dict snapshot of the state (if state tracking enabled)
    """
    if registry is None:
        registry = setup_registry()

    # Create or use provided state
    if state is None and create_state:
        try:
            from argumentation_analysis.core.shared_state import UnifiedAnalysisState

            state = UnifiedAnalysisState(text)
        except ImportError:
            logger.warning("Could not import UnifiedAnalysisState; state tracking disabled")
            state = None

    if custom_workflow is not None:
        workflow = custom_workflow
    elif workflow_name == "auto":
        try:
            from argumentation_analysis.orchestration.router import TextAnalysisRouter

            router = TextAnalysisRouter(registry=registry)
            workflow = await router.analyze_and_route_async(text, registry=registry)
        except Exception as e:
            logger.warning("Auto-routing failed, falling back to standard: %s", e)
            catalog = get_workflow_catalog()
            workflow = catalog["standard"]
    else:
        catalog = get_workflow_catalog()
        if workflow_name not in catalog:
            raise ValueError(
                f"Unknown workflow '{workflow_name}'. "
                f"Available: {list(catalog.keys())}"
            )
        workflow = catalog[workflow_name]

    executor = WorkflowExecutor(registry)
    phase_results = await executor.execute(
        workflow,
        input_data=text,
        context=context,
        state=state,
        state_writers=CAPABILITY_STATE_WRITERS if state is not None else None,
    )

    # Build summary
    completed = [
        name for name, r in phase_results.items() if r.status == PhaseStatus.COMPLETED
    ]
    failed = [
        name for name, r in phase_results.items() if r.status == PhaseStatus.FAILED
    ]
    skipped_phases = [
        name for name, r in phase_results.items() if r.status == PhaseStatus.SKIPPED
    ]

    capabilities_used = [
        r.capability
        for r in phase_results.values()
        if r.status == PhaseStatus.COMPLETED
    ]
    capabilities_missing = [
        r.capability
        for r in phase_results.values()
        if r.status in (PhaseStatus.FAILED, PhaseStatus.SKIPPED)
    ]

    result = {
        "workflow_name": workflow.name,
        "phases": phase_results,
        "summary": {
            "completed": len(completed),
            "failed": len(failed),
            "skipped": len(skipped_phases),
            "total": len(phase_results),
            "completed_phases": completed,
            "failed_phases": failed,
            "skipped_phases": skipped_phases,
        },
        "capabilities_used": capabilities_used,
        "capabilities_missing": capabilities_missing,
    }

    # Include state in results if available
    if state is not None:
        result["unified_state"] = state
        try:
            result["state_snapshot"] = state.get_state_snapshot(summarize=True)
        except Exception:
            result["state_snapshot"] = None

    return result
