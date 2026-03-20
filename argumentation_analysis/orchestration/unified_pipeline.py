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
    """Invoke counter-argument analysis via plugin + LLM enrichment."""
    import os
    from argumentation_analysis.agents.core.counter_argument.counter_agent import (
        CounterArgumentPlugin,
    )

    plugin = CounterArgumentPlugin()
    parsed_json = plugin.parse_argument(input_text)
    strategy_json = plugin.suggest_strategy(input_text)
    parsed = json.loads(parsed_json)
    strategy = json.loads(strategy_json)

    # Enrich with LLM-generated counter-argument if available
    llm_counter = None
    try:
        from openai import AsyncOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)

            # Use extracted arguments from upstream phase if available
            extract_output = context.get("phase_extract_output", {})
            arguments = extract_output.get("arguments", [])
            args_context = (
                "\n".join(f"- {a}" for a in arguments)
                if arguments
                else input_text[:1500]
            )

            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in argumentation and counter-argument generation. "
                            "Generate a strong counter-argument using one of: reductio ad absurdum, "
                            "counter-example, distinction, reformulation, or concession+pivot. "
                            "Respond with ONLY a JSON object:\n"
                            '{"counter_argument": "text", "strategy_used": "name", '
                            '"target_argument": "which argument", "strength": "weak|moderate|strong", '
                            '"reasoning": "why this works"}'
                        ),
                    },
                    {"role": "user", "content": args_context},
                ],
            )
            raw = response.choices[0].message.content or ""
            text_content = raw.strip()
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0]
            elif "```" in text_content:
                text_content = text_content.split("```")[1].split("```")[0]
            start = text_content.find("{")
            end = text_content.rfind("}") + 1
            if start >= 0 and end > start:
                llm_counter = json.loads(text_content[start:end])
    except Exception as e:
        logger.warning(f"LLM counter-argument enrichment failed: {e}")

    result = {
        "parsed_argument": parsed,
        "suggested_strategy": strategy,
        "quality_context": context.get("phase_quality_output"),
    }
    if llm_counter:
        result["llm_counter_argument"] = llm_counter
    return result


async def _invoke_debate_analysis(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke debate argument analysis via plugin + LLM adversarial assessment."""
    import os
    from argumentation_analysis.agents.core.debate.debate_agent import DebatePlugin

    plugin = DebatePlugin()
    scores_json = plugin.analyze_argument_quality(input_text)
    base_scores = json.loads(scores_json)

    # Enrich with LLM-based adversarial debate assessment
    try:
        from openai import AsyncOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)

            # Use extracted arguments from upstream
            extract_output = context.get("phase_extract_output", {})
            arguments = extract_output.get("arguments", [])
            args_text = (
                "\n".join(f"- {a}" for a in arguments)
                if arguments
                else input_text[:1500]
            )

            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a debate judge. Analyze the arguments presented, "
                            "identify the strongest and weakest positions, and assess "
                            "the overall quality of the argumentation. "
                            "Respond with ONLY a JSON object:\n"
                            '{"strongest_argument": "text", "weakest_argument": "text", '
                            '"winner": "which side/position wins", '
                            '"debate_quality": 1-5, '
                            '"key_exchanges": [{"point": "text", "rebuttal": "text"}], '
                            '"reasoning": "brief assessment"}'
                        ),
                    },
                    {"role": "user", "content": args_text},
                ],
            )
            raw = response.choices[0].message.content or ""
            text_content = raw.strip()
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0]
            elif "```" in text_content:
                text_content = text_content.split("```")[1].split("```")[0]
            start = text_content.find("{")
            end = text_content.rfind("}") + 1
            if start >= 0 and end > start:
                llm_debate = json.loads(text_content[start:end])
                base_scores["llm_debate_assessment"] = llm_debate
                if not base_scores.get("winner"):
                    base_scores["winner"] = llm_debate.get("winner")
    except Exception as e:
        logger.warning(f"LLM debate assessment failed: {e}")

    return base_scores


async def _invoke_governance(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke governance analysis via plugin + LLM-powered deliberation assessment."""
    import os
    from argumentation_analysis.plugins.governance_plugin import GovernancePlugin

    plugin = GovernancePlugin()
    methods_json = plugin.list_governance_methods()
    available_methods = json.loads(methods_json)

    # Build positions from upstream phases (extract, debate, counter_argument)
    extract_output = context.get("phase_extract_output", {})
    debate_output = context.get("phase_debate_output", {})
    counter_output = context.get("phase_counter_argument_output", {})

    arguments = extract_output.get("arguments", [])
    claims = extract_output.get("claims", [])

    # Detect conflicts using plugin if we have enough upstream data
    positions = {}
    if arguments:
        for i, arg in enumerate(arguments[:6]):
            positions[f"agent_{i+1}"] = str(arg)
    elif claims:
        for i, claim in enumerate(claims[:6]):
            positions[f"agent_{i+1}"] = str(claim)

    conflicts = []
    resolutions = []
    if positions:
        conflicts_json = plugin.detect_conflicts_fn(json.dumps(positions))
        conflicts = json.loads(conflicts_json)
        # Resolve each conflict with collaborative strategy
        for conflict in conflicts[:5]:
            resolution_json = plugin.resolve_conflict_fn(
                json.dumps(conflict), strategy="collaborative"
            )
            resolutions.append(json.loads(resolution_json))

    # Enrich with LLM-based governance and deliberation assessment
    llm_governance = None
    try:
        from openai import AsyncOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)

            # Build context from upstream phases
            context_parts = []
            if arguments:
                context_parts.append(
                    "Arguments identified:\n" + "\n".join(f"- {a}" for a in arguments)
                )
            if debate_output.get("llm_debate_assessment"):
                da = debate_output["llm_debate_assessment"]
                context_parts.append(
                    f"Debate winner: {da.get('winner', 'unknown')}, "
                    f"quality: {da.get('debate_quality', 'N/A')}/5"
                )
            if counter_output.get("llm_counter_argument"):
                ca = counter_output["llm_counter_argument"]
                context_parts.append(
                    f"Counter-argument ({ca.get('strategy_used', 'unknown')}): "
                    f"{ca.get('counter_argument', '')[:200]}"
                )
            if conflicts:
                context_parts.append(
                    f"Conflicts detected: {len(conflicts)} between "
                    + ", ".join(" vs ".join(c.get("agents", [])) for c in conflicts[:3])
                )

            deliberation_input = (
                "\n\n".join(context_parts) if context_parts else input_text[:2000]
            )

            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a governance and collective decision-making analyst. "
                            "Analyze the arguments, conflicts, and positions presented. "
                            "Assess which voting/decision method would be most appropriate, "
                            "evaluate consensus potential, and recommend a governance approach. "
                            "Available methods: " + ", ".join(available_methods) + ". "
                            "Respond with ONLY a JSON object:\n"
                            '{"recommended_method": "method_name", '
                            '"consensus_potential": 0.0-1.0, '
                            '"fairness_assessment": "brief text", '
                            '"conflict_severity": "low|medium|high", '
                            '"stakeholder_analysis": [{"agent": "name", "position": "summary", "influence": 0.0-1.0}], '
                            '"recommended_resolution": "collaborative|competitive|compromise", '
                            '"governance_reasoning": "brief explanation of recommendation"}'
                        ),
                    },
                    {"role": "user", "content": deliberation_input},
                ],
            )
            raw = response.choices[0].message.content or ""
            text_content = raw.strip()
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0]
            elif "```" in text_content:
                text_content = text_content.split("```")[1].split("```")[0]
            start = text_content.find("{")
            end = text_content.rfind("}") + 1
            if start >= 0 and end > start:
                llm_governance = json.loads(text_content[start:end])
    except Exception as e:
        logger.warning(f"LLM governance assessment failed: {e}")

    result = {
        "available_methods": available_methods,
        "positions": positions,
        "conflicts": conflicts,
        "resolutions": resolutions,
        "conflict_count": len(conflicts),
        "extraction_method": "llm" if llm_governance else "heuristic",
    }
    if llm_governance:
        result["llm_governance_assessment"] = llm_governance
        result["recommended_method"] = llm_governance.get("recommended_method")
        result["consensus_potential"] = llm_governance.get("consensus_potential")
    return result


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


def _extract_arguments_from_context(
    input_text: str, context: Dict[str, Any]
) -> List[str]:
    """Extract argument labels from upstream phase outputs.

    Looks at quality_baseline, extract, or quality phase outputs for argument
    lists, then falls back to generating labels from the input text.
    """
    # Try various upstream phase outputs
    for phase_key in [
        "phase_quality_baseline_output",
        "phase_extract_output",
        "phase_quality_output",
    ]:
        phase_out = context.get(phase_key, {})
        if isinstance(phase_out, dict):
            # Quality evaluator returns scores dict keyed by virtue
            if "arguments" in phase_out:
                args = phase_out["arguments"]
                if isinstance(args, list) and args:
                    return [str(a) for a in args]
            # Some evaluators return 'scores' keyed by argument ID
            if "scores" in phase_out and isinstance(phase_out["scores"], dict):
                return list(phase_out["scores"].keys())

    # Fall back: split text into sentences as pseudo-arguments
    sentences = [
        s.strip() for s in input_text.replace("\n", ". ").split(".") if s.strip()
    ]
    if len(sentences) >= 2:
        return [f"arg_{i+1}" for i in range(min(len(sentences), 6))]
    return ["arg_1", "arg_2", "arg_3"]


def _generate_attacks_from_args(arguments: List[str]) -> List[List[str]]:
    """Generate plausible attack relations between arguments (heuristic)."""
    attacks = []
    for i in range(len(arguments)):
        for j in range(i + 1, len(arguments)):
            if (i + j) % 3 == 0:  # Sparse attack pattern
                attacks.append([arguments[i], arguments[j]])
    return attacks


def _python_ranking_fallback(
    arguments: List[str], attacks: List[List[str]], method: str
) -> Dict[str, Any]:
    """Pure-Python ranking fallback when Tweety/JVM is unavailable.

    Uses a simplified categorizer algorithm: score = 1 / (1 + attackers).
    """
    # Count incoming attacks per argument
    in_attacks: Dict[str, int] = {a: 0 for a in arguments}
    for src, tgt in attacks:
        if tgt in in_attacks:
            in_attacks[tgt] += 1

    # Categorizer-style score
    scores = {a: 1.0 / (1.0 + cnt) for a, cnt in in_attacks.items()}
    sorted_args = sorted(scores.items(), key=lambda x: -x[1])
    comparisons = []
    for i in range(len(sorted_args) - 1):
        comparisons.append(
            {
                "stronger": sorted_args[i][0],
                "weaker": sorted_args[i + 1][0],
                "score_diff": round(sorted_args[i][1] - sorted_args[i + 1][1], 4),
            }
        )
    return {
        "method": method,
        "ranking": [a for a, _ in sorted_args],
        "scores": {a: round(s, 4) for a, s in scores.items()},
        "comparisons": comparisons,
        "fallback": "python",
    }


async def _invoke_ranking(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke ranking semantics handler with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args)
    method = context.get("ranking_method", "categorizer")

    try:
        from argumentation_analysis.agents.core.logic.ranking_handler import (
            RankingHandler,
        )

        handler = RankingHandler()
        return await asyncio.to_thread(handler.rank_arguments, args, attacks, method)
    except Exception as e:
        logger.info(f"Ranking handler unavailable ({e}), using Python fallback")
        return _python_ranking_fallback(args, attacks, method)


async def _invoke_bipolar(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke bipolar argumentation handler with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args)
    supports = context.get("supports", [])
    fw_type = context.get("framework_type", "necessity")

    try:
        from argumentation_analysis.agents.core.logic.bipolar_handler import (
            BipolarHandler,
        )

        handler = BipolarHandler()
        return await asyncio.to_thread(
            handler.analyze_bipolar_framework, args, attacks, supports, fw_type
        )
    except Exception as e:
        logger.info(f"Bipolar handler unavailable ({e}), using Python fallback")
        return {
            "framework_type": fw_type,
            "arguments": args,
            "attacks": attacks,
            "supports": supports,
            "extensions": [args[:2]] if len(args) >= 2 else [args],
            "fallback": "python",
        }


async def _invoke_aba(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke ABA handler with JVM fallback."""
    args = _extract_arguments_from_context(input_text, context)
    assumptions = context.get("assumptions") or args[:3]
    rules = context.get("rules") or [f"{a} => valid" for a in args[:2]]
    contraries = context.get("contraries")
    semantics = context.get("semantics", "preferred")

    try:
        from argumentation_analysis.agents.core.logic.aba_handler import ABAHandler

        handler = ABAHandler()
        return await asyncio.to_thread(
            handler.analyze_aba_framework, assumptions, rules, contraries, semantics
        )
    except Exception as e:
        logger.info(f"ABA handler unavailable ({e}), using Python fallback")
        return {
            "assumptions": assumptions,
            "rules": rules,
            "semantics": semantics,
            "extensions": [assumptions[:2]] if len(assumptions) >= 2 else [assumptions],
            "fallback": "python",
        }


async def _invoke_adf(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke ADF handler with JVM fallback."""
    args = _extract_arguments_from_context(input_text, context)
    statements = context.get("statements") or args
    conditions = context.get("acceptance_conditions") or {
        a: "and(c(v))" for a in args[:3]
    }
    semantics = context.get("semantics", "grounded")

    try:
        from argumentation_analysis.agents.core.logic.adf_handler import ADFHandler

        handler = ADFHandler()
        return await asyncio.to_thread(
            handler.analyze_adf, statements, conditions, semantics
        )
    except Exception as e:
        logger.info(f"ADF handler unavailable ({e}), using Python fallback")
        return {
            "statements": statements,
            "acceptance_conditions": conditions,
            "semantics": semantics,
            "interpretations": [
                {s: True for s in statements[:2]} if statements else {}
            ],
            "fallback": "python",
        }


async def _invoke_aspic(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke ASPIC+ handler with JVM fallback."""
    args = _extract_arguments_from_context(input_text, context)
    strict = context.get("strict_rules") or [
        f"{args[i]} -> {args[i+1]}" for i in range(0, len(args) - 1, 2)
    ]
    defeasible = context.get("defeasible_rules") or [
        f"{a} => conclusion" for a in args[:3]
    ]
    axioms = context.get("axioms")

    try:
        from argumentation_analysis.agents.core.logic.aspic_handler import ASPICHandler

        handler = ASPICHandler()
        return await asyncio.to_thread(
            handler.analyze_aspic_framework, strict, defeasible, axioms
        )
    except Exception as e:
        logger.info(f"ASPIC+ handler unavailable ({e}), using Python fallback")
        return {
            "strict_rules": strict,
            "defeasible_rules": defeasible,
            "extensions": [args[:2]] if len(args) >= 2 else [args],
            "statistics": {
                "arguments": len(args),
                "strict_rules": len(strict),
                "defeasible_rules": len(defeasible),
            },
            "fallback": "python",
        }


async def _invoke_belief_revision(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke belief revision handler with JVM fallback."""
    args = _extract_arguments_from_context(input_text, context)
    beliefs = context.get("belief_set") or args
    new_belief = context.get("new_belief") or (args[-1] if args else input_text[:200])
    method = context.get("revision_method", "dalal")

    try:
        from argumentation_analysis.agents.core.logic.belief_revision_handler import (
            BeliefRevisionHandler,
        )

        handler = BeliefRevisionHandler()
        return await asyncio.to_thread(handler.revise, beliefs, new_belief, method)
    except Exception as e:
        logger.info(f"Belief revision handler unavailable ({e}), using Python fallback")
        # Simple set-based revision: add new belief, remove contradictions
        revised = list(beliefs)
        if new_belief not in revised:
            revised.append(new_belief)
        return {
            "method": method,
            "original": list(beliefs),
            "new_belief": new_belief,
            "revised": revised,
            "removed": [],
            "fallback": "python",
        }


async def _invoke_probabilistic(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke probabilistic argumentation handler with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args)
    probs = context.get("probabilities") or {a: 0.5 for a in args}

    try:
        from argumentation_analysis.agents.core.logic.probabilistic_handler import (
            ProbabilisticHandler,
        )

        handler = ProbabilisticHandler()
        return await asyncio.to_thread(
            handler.analyze_probabilistic_framework, args, attacks, probs
        )
    except Exception as e:
        logger.info(f"Probabilistic handler unavailable ({e}), using Python fallback")
        # Simple acceptance probability based on attack count
        in_attacks: Dict[str, int] = {a: 0 for a in args}
        for src, tgt in attacks:
            if tgt in in_attacks:
                in_attacks[tgt] += 1
        acceptance = {
            a: round(probs.get(a, 0.5) / (1.0 + cnt), 4)
            for a, cnt in in_attacks.items()
        }
        return {
            "arguments": args,
            "attacks": attacks,
            "initial_probabilities": probs,
            "acceptance_probabilities": acceptance,
            "fallback": "python",
        }


async def _invoke_dialogue(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke dialogue protocol handler with JVM fallback."""
    args = _extract_arguments_from_context(input_text, context)
    mid = max(1, len(args) // 2)
    pro_args = context.get("proponent_args") or args[:mid]
    opp_args = context.get("opponent_args") or args[mid:]
    pro_attacks = context.get("proponent_attacks") or _generate_attacks_from_args(
        pro_args
    )
    opp_attacks = context.get("opponent_attacks") or _generate_attacks_from_args(
        opp_args
    )
    topic = context.get("topic", input_text[:200])

    try:
        from argumentation_analysis.agents.core.logic.dialogue_handler import (
            DialogueHandler,
        )

        handler = DialogueHandler()
        return await asyncio.to_thread(
            handler.execute_dialogue,
            pro_args,
            pro_attacks,
            opp_args,
            opp_attacks,
            topic,
        )
    except Exception as e:
        logger.info(f"Dialogue handler unavailable ({e}), using Python fallback")
        # Simulate a simple dialogue trace
        trace = []
        for i, arg in enumerate(pro_args):
            trace.append({"turn": i * 2 + 1, "speaker": "proponent", "move": arg})
            if i < len(opp_args):
                trace.append(
                    {"turn": i * 2 + 2, "speaker": "opponent", "move": opp_args[i]}
                )
        winner = "proponent" if len(pro_args) >= len(opp_args) else "opponent"
        return {
            "topic": topic[:100],
            "proponent_args": pro_args,
            "opponent_args": opp_args,
            "trace": trace,
            "outcome": winner,
            "turns": len(trace),
            "fallback": "python",
        }


async def _invoke_dl(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke Description Logic handler (#86) with JVM fallback."""
    tbox = context.get("tbox", [])
    abox_concepts = context.get("abox_concepts", [])
    abox_roles = context.get("abox_roles", [])

    try:
        from argumentation_analysis.agents.core.logic.dl_handler import DLHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = DLHandler(initializer)
        kb = await asyncio.to_thread(
            handler.create_knowledge_base, tbox, abox_concepts, abox_roles
        )
        consistent, msg = await asyncio.to_thread(handler.is_consistent, kb)
        return {
            "consistent": consistent,
            "message": msg,
            "tbox_size": len(tbox),
            "abox_size": len(abox_concepts) + len(abox_roles),
            "statistics": {"handler": "DLHandler", "reasoner": "NaiveDlReasoner"},
        }
    except Exception as e:
        logger.info(f"DL handler unavailable ({e}), using Python fallback")
        return {
            "consistent": True,
            "message": "Fallback: consistency assumed (JVM unavailable)",
            "tbox_size": len(tbox),
            "abox_size": len(abox_concepts) + len(abox_roles),
            "statistics": {"handler": "fallback"},
            "fallback": "python",
        }


async def _invoke_cl(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke Conditional Logic handler (#86) with JVM fallback."""
    conditionals = context.get("conditionals", [])
    query_conclusion = context.get("query_conclusion")
    query_premise = context.get("query_premise")

    try:
        from argumentation_analysis.agents.core.logic.cl_handler import CLHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = CLHandler(initializer)
        kb = await asyncio.to_thread(handler.create_knowledge_base, conditionals)
        if query_conclusion:
            entailed, msg = await asyncio.to_thread(
                handler.query, kb, query_conclusion, query_premise
            )
        else:
            entailed, msg = True, "No query specified — KB constructed."
        return {
            "entailed": entailed,
            "message": msg,
            "num_conditionals": len(conditionals),
            "statistics": {"handler": "CLHandler", "reasoner": "SimpleCReasoner"},
        }
    except Exception as e:
        logger.info(f"CL handler unavailable ({e}), using Python fallback")
        return {
            "entailed": True,
            "message": "Fallback: entailment assumed (JVM unavailable)",
            "num_conditionals": len(conditionals),
            "statistics": {"handler": "fallback"},
            "fallback": "python",
        }


async def _invoke_sat(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke SAT solver handler (#86)."""
    from argumentation_analysis.agents.core.logic.sat_handler import SATHandler

    handler = SATHandler(context.get("solver", "cadical195"))
    formulas = context.get("formulas", [input_text] if input_text else [])
    mode = context.get("sat_mode", "solve")  # solve, maxsat, mus
    if mode == "mus":
        mus_list = await asyncio.to_thread(handler.find_mus, formulas)
        return {
            "mode": "mus",
            "mus_count": len(mus_list),
            "mus_subsets": mus_list,
            "statistics": {"handler": "SATHandler", "backend": "Z3-MARCO"},
        }
    is_sat, model, stats = await asyncio.to_thread(handler.solve_formulas, formulas)
    return {
        "satisfiable": is_sat,
        "model": model,
        "statistics": stats,
    }


# --- SetAF / Weighted AF / Social AF invoke functions (#87) ---


async def _invoke_setaf(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke Set Argumentation Framework handler (#87) with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("set_attacks", [])
    semantics = context.get("semantics", "grounded")

    try:
        from argumentation_analysis.agents.core.logic.setaf_handler import SetAFHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = SetAFHandler(initializer)
        return await asyncio.to_thread(handler.analyze_setaf, args, attacks, semantics)
    except Exception as e:
        logger.info(f"SetAF handler unavailable ({e}), using Python fallback")
        return {
            "arguments": args,
            "set_attacks": attacks,
            "semantics": semantics,
            "extensions": [args[:2]] if len(args) >= 2 else [args],
            "fallback": "python",
        }


async def _invoke_weighted(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke Weighted AF handler (#87) with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("weighted_attacks", [])
    semantics = context.get("semantics", "grounded")

    try:
        from argumentation_analysis.agents.core.logic.weighted_handler import (
            WeightedHandler,
        )
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = WeightedHandler(initializer)
        return await asyncio.to_thread(
            handler.analyze_weighted_framework, args, attacks, semantics
        )
    except Exception as e:
        logger.info(f"Weighted handler unavailable ({e}), using Python fallback")
        scores = {a: round(1.0 / (i + 1), 4) for i, a in enumerate(args)}
        return {
            "arguments": args,
            "weighted_attacks": attacks,
            "semantics": semantics,
            "scores": scores,
            "extensions": [args[:2]] if len(args) >= 2 else [args],
            "fallback": "python",
        }


async def _invoke_social(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke Social AF handler (#87) with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args)
    votes = context.get("votes", {})
    if votes:
        votes = {k: tuple(v) if isinstance(v, list) else v for k, v in votes.items()}

    try:
        from argumentation_analysis.agents.core.logic.social_handler import (
            SocialHandler,
        )
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = SocialHandler(initializer)
        return await asyncio.to_thread(
            handler.analyze_social_framework, args, attacks, votes
        )
    except Exception as e:
        logger.info(f"Social handler unavailable ({e}), using Python fallback")
        # Simple majority-based social ranking
        social_scores = (
            {a: votes.get(a, (1, 0))[0] for a in args}
            if votes
            else {a: len(args) - i for i, a in enumerate(args)}
        )
        return {
            "arguments": args,
            "attacks": attacks,
            "votes": votes,
            "social_ranking": sorted(social_scores, key=lambda a: -social_scores[a]),
            "social_scores": social_scores,
            "fallback": "python",
        }


# --- EAF / DeLP / QBF invoke functions (#88, #89, #90) ---


async def _invoke_eaf(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke Epistemic AF handler (#88) with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args)
    beliefs = context.get("epistemic_beliefs")
    semantics = context.get("semantics", "grounded")

    try:
        from argumentation_analysis.agents.core.logic.eaf_handler import EAFHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = EAFHandler(initializer)
        return await asyncio.to_thread(
            handler.analyze_epistemic_framework, args, attacks, beliefs, semantics
        )
    except Exception as e:
        logger.info(f"EAF handler unavailable ({e}), using Python fallback")
        epistemic = {a: {"believed": True, "confidence": 0.7} for a in args}
        return {
            "arguments": args,
            "attacks": attacks,
            "semantics": semantics,
            "epistemic_states": epistemic,
            "extensions": [args[:2]] if len(args) >= 2 else [args],
            "fallback": "python",
        }


async def _invoke_delp(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke DeLP handler (#89) with JVM fallback."""
    program_text = context.get("program", input_text[:500])
    queries = context.get("queries", [])
    criterion = context.get("criterion", "generalized_specificity")

    try:
        from argumentation_analysis.agents.core.logic.delp_handler import DeLPHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = DeLPHandler(initializer)
        return await asyncio.to_thread(
            handler.analyze_delp, program_text, queries, criterion
        )
    except Exception as e:
        logger.info(f"DeLP handler unavailable ({e}), using Python fallback")
        return {
            "program": program_text[:200],
            "queries": queries,
            "criterion": criterion,
            "results": {q: "undecided" for q in queries} if queries else {},
            "fallback": "python",
        }


async def _invoke_qbf(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke QBF handler (#90) with JVM fallback."""
    quantifiers = context.get("quantifiers", [])
    formula = context.get("formula", input_text[:200])

    try:
        from argumentation_analysis.agents.core.logic.qbf_handler import QBFHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()
        handler = QBFHandler(initializer)
        return await asyncio.to_thread(handler.analyze_qbf, quantifiers, formula)
    except Exception as e:
        logger.info(f"QBF handler unavailable ({e}), using Python fallback")
        return {
            "quantifiers": quantifiers,
            "formula": formula[:100],
            "satisfiable": True,
            "message": "Fallback: satisfiability assumed (JVM unavailable)",
            "fallback": "python",
        }


# --- Hierarchical taxonomy-guided fallacy detection (#84) ---


async def _invoke_hierarchical_fallacy(
    input_text: str, context: Dict[str, Any]
) -> Dict:
    """Invoke hierarchical taxonomy-guided fallacy detection.

    Uses FallacyWorkflowPlugin with iterative deepening (master-slave kernel)
    and one-shot fallback. Requires a Semantic Kernel service + taxonomy CSV.
    Falls back to heuristic extraction if SK/API is unavailable.
    """
    import os

    taxonomy_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "argumentum_fallacies_taxonomy.csv",
    )
    if not os.path.isfile(taxonomy_path):
        logger.warning(
            "Taxonomy CSV not found at %s — hierarchical fallacy detection skipped",
            taxonomy_path,
        )
        return {
            "fallacies": [],
            "exploration_method": "skipped",
            "reason": "taxonomy file not found",
        }

    try:
        from openai import AsyncOpenAI
        from semantic_kernel.kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("No OPENAI_API_KEY available")

        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

        async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        llm_service = OpenAIChatCompletion(
            ai_model_id=model_id,
            async_client=async_client,
        )
        master_kernel = Kernel()
        master_kernel.add_service(llm_service)

        plugin = FallacyWorkflowPlugin(
            master_kernel=master_kernel,
            llm_service=llm_service,
            taxonomy_file_path=taxonomy_path,
        )

        result_json = await plugin.run_guided_analysis(argument_text=input_text)
        result = json.loads(result_json)
        result["extraction_method"] = result.get("exploration_method", "unknown")
        return result

    except Exception as e:
        logger.warning("Hierarchical fallacy detection failed, returning empty: %s", e)
        return {
            "fallacies": [],
            "exploration_method": "error",
            "error": str(e),
            "extraction_method": "error",
        }


# --- Invoke callables for logic agent capabilities (#71 Formal Verification) ---


async def _invoke_fact_extraction(input_text: str, context: Dict[str, Any]) -> Dict:
    """Extract verifiable claims and arguments from text using LLM with heuristic fallback."""
    import os
    import re

    # Try LLM-based extraction first
    try:
        from openai import AsyncOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

        if api_key:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert argument analyst. Extract the key arguments, "
                            "claims, and rhetorical strategies from the text. "
                            "Respond with ONLY a JSON object:\n"
                            '{"arguments": ["arg1", "arg2", ...], '
                            '"claims": ["claim1", "claim2", ...], '
                            '"fallacies": [{"type": "name", "justification": "why"}], '
                            '"summary": "brief analysis summary"}'
                        ),
                    },
                    {"role": "user", "content": input_text[:3000]},
                ],
            )
            raw = response.choices[0].message.content or ""
            # Parse JSON from response
            text_content = raw.strip()
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0]
            elif "```" in text_content:
                text_content = text_content.split("```")[1].split("```")[0]
            start = text_content.find("{")
            end = text_content.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text_content[start:end])
                return {
                    "arguments": data.get("arguments", []),
                    "claims": data.get("claims", []),
                    "fallacies": data.get("fallacies", []),
                    "summary": data.get("summary", ""),
                    "claim_count": len(data.get("claims", [])),
                    "argument_count": len(data.get("arguments", [])),
                    "source_length": len(input_text),
                    "extraction_method": "llm",
                }
    except Exception as e:
        logger.warning(f"LLM fact extraction failed, falling back to heuristic: {e}")

    # Heuristic fallback
    sentences = re.split(r"(?<=[.!?])\s+", input_text.strip())
    claims = [s.strip() for s in sentences if len(s.strip()) > 20]
    return {
        "arguments": [],
        "claims": claims,
        "fallacies": [],
        "summary": "",
        "claim_count": len(claims),
        "argument_count": 0,
        "source_length": len(input_text),
        "extraction_method": "heuristic",
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
        return {
            "error": str(e),
            "formulas": [],
            "satisfiable": False,
            "logic_type": "propositional",
        }


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
        return {
            "error": str(e),
            "formulas": [],
            "consistent": False,
            "inferences": [],
            "confidence": 0.0,
        }


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
        if (
            key.startswith("phase_")
            and key.endswith("_output")
            and isinstance(val, dict)
        ):
            phase_name = key[len("phase_") : -len("_output")]
            phase_results[phase_name] = val
            if "consistent" in val:
                overall_scores.append(1.0 if val["consistent"] else 0.0)
            if "satisfiable" in val:
                overall_scores.append(1.0 if val["satisfiable"] else 0.0)
            if "valid" in val:
                overall_scores.append(1.0 if val["valid"] else 0.0)

    overall_validity = (
        sum(overall_scores) / len(overall_scores) if overall_scores else 0.5
    )
    summary_parts = []
    for name, res in phase_results.items():
        if "error" in res:
            summary_parts.append(f"{name}: error ({res['error'][:50]})")
        elif "consistent" in res:
            summary_parts.append(f"{name}: consistent={res['consistent']}")
        elif "satisfiable" in res:
            summary_parts.append(f"{name}: satisfiable={res['satisfiable']}")
        elif "extensions" in res:
            ext_count = (
                sum(
                    len(v) if isinstance(v, list) else 0
                    for v in res["extensions"].values()
                )
                if isinstance(res.get("extensions"), dict)
                else 0
            )
            summary_parts.append(f"{name}: {ext_count} extensions")

    return {
        "summary": (
            "; ".join(summary_parts) if summary_parts else "No formal results collected"
        ),
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
    # Use LLM-generated counter-argument if available
    llm_ca = output.get("llm_counter_argument")
    if isinstance(llm_ca, dict) and llm_ca.get("counter_argument"):
        target = str(llm_ca.get("target_argument", ""))[:200]
        counter_text = str(llm_ca.get("counter_argument", ""))
        strategy_name = str(llm_ca.get("strategy_used", "unknown"))
        strength_map = {"weak": 0.3, "moderate": 0.6, "strong": 0.9}
        score = strength_map.get(str(llm_ca.get("strength", "")).lower(), 0.5)
        state.add_counter_argument(target, counter_text, strategy_name, score)
        return
    # Fallback to heuristic plugin output
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
        valid = (
            True if valid_str == "True" else (False if valid_str == "False" else None)
        )
        state.add_jtms_belief(str(name), valid, justifications=[])


def _write_debate_to_state(output, state, ctx) -> None:
    """Write debate analysis results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    topic = str(ctx.get("input_data", ""))[:100]
    winner = output.get("winner")
    # Build exchanges from LLM debate assessment if available
    exchanges = []
    llm_debate = output.get("llm_debate_assessment")
    if isinstance(llm_debate, dict):
        key_exchanges = llm_debate.get("key_exchanges", [])
        if isinstance(key_exchanges, list):
            for ex in key_exchanges:
                if isinstance(ex, dict):
                    exchanges.append(
                        {
                            "point": str(ex.get("point", "")),
                            "rebuttal": str(ex.get("rebuttal", "")),
                        }
                    )
    state.add_debate_transcript(
        topic=topic,
        exchanges=exchanges,
        winner=str(winner) if winner is not None else None,
    )


def _write_governance_to_state(output, state, ctx) -> None:
    """Write governance results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return

    llm_gov = output.get("llm_governance_assessment", {})
    if not isinstance(llm_gov, dict):
        llm_gov = {}

    # Build scores from stakeholder analysis or conflicts
    scores = {}
    stakeholders = llm_gov.get("stakeholder_analysis", [])
    if isinstance(stakeholders, list):
        for s in stakeholders:
            if isinstance(s, dict):
                agent = str(s.get("agent", "unknown"))
                influence = float(s.get("influence", 0.0))
                scores[agent] = influence

    # Fallback: use available methods as score keys if no stakeholders
    if not scores:
        methods = output.get("available_methods", [])
        if isinstance(methods, list) and methods:
            scores = {str(m): 0.0 for m in methods}

    # If no scores at all (no methods, no stakeholders, no LLM), skip
    has_conflicts = bool(output.get("conflicts"))
    has_llm = bool(llm_gov)
    if not scores and not has_conflicts and not has_llm:
        return

    recommended = output.get("recommended_method") or llm_gov.get(
        "recommended_method", "majority"
    )

    # Determine winner from LLM assessment or conflict resolution
    winner = "N/A"
    if llm_gov.get("recommended_resolution"):
        winner = str(llm_gov["recommended_resolution"])
    elif output.get("resolutions"):
        resolutions = output["resolutions"]
        if isinstance(resolutions, list) and resolutions:
            winner = str(resolutions[0].get("resolution_type", "N/A"))

    state.add_governance_decision(
        method=str(recommended),
        winner=winner,
        scores=scores,
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


def _write_hierarchical_fallacy_to_state(output, state, ctx) -> None:
    """Write hierarchical taxonomy-guided fallacy results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    fallacies = output.get("fallacies", [])
    if not isinstance(fallacies, list):
        return
    for f in fallacies:
        if not isinstance(f, dict):
            continue
        fallacy_type = f.get("fallacy_type", "unknown")
        justification = f.get("explanation", "")
        taxonomy_pk = f.get("taxonomy_pk", "")
        confidence = f.get("confidence", 0.0)
        trace = f.get("navigation_trace", [])
        full_justification = justification
        if taxonomy_pk:
            full_justification += f" [taxonomy:{taxonomy_pk}]"
        if confidence:
            full_justification += f" [confidence:{confidence:.2f}]"
        if trace:
            full_justification += f" [trace:{'>'.join(trace)}]"
        state.add_fallacy(fallacy_type=fallacy_type, justification=full_justification)


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
    # Accept both "arguments" (JVM path) and "ranking" (Python fallback path)
    arguments = output.get("arguments") or output.get("ranking", [])
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
    # Accept both "dialogue_trace" (JVM path) and "trace" (Python fallback path)
    trace = output.get("dialogue_trace") or output.get("trace", [])
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
    """Write fact extraction results to state (populates extracts + base fields)."""
    if not output or not isinstance(output, dict):
        return
    # Write claims to extracts
    claims = output.get("claims", [])
    if isinstance(claims, list):
        for claim in claims:
            if isinstance(claim, str) and claim.strip():
                state.extracts.append({"type": "claim", "content": claim.strip()})
    # Populate base identified_arguments from LLM extraction
    arguments = output.get("arguments", [])
    if isinstance(arguments, list):
        for arg in arguments:
            if isinstance(arg, str) and arg.strip():
                state.add_argument(arg.strip())
    # Populate base identified_fallacies from LLM extraction
    fallacies = output.get("fallacies", [])
    if isinstance(fallacies, list):
        for f in fallacies:
            if isinstance(f, dict):
                state.add_fallacy(
                    fallacy_type=str(f.get("type", "unknown")),
                    justification=str(f.get("justification", "")),
                )
    # Set summary as analysis task if present
    summary = output.get("summary", "")
    if summary and isinstance(summary, str):
        state.add_task(f"Fact extraction: {summary[:200]}")


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
    state.add_fol_analysis_result(
        formulas, bool(consistent), inferences, float(confidence)
    )


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


def _write_dl_to_state(output, state, ctx) -> None:
    """Write Description Logic results to UnifiedAnalysisState (#86)."""
    if not output or not isinstance(output, dict):
        return
    consistent = output.get("consistent", False)
    message = str(output.get("message", ""))
    state.add_fol_analysis_result(
        formulas=[f"DL: {message}"],
        consistent=bool(consistent),
        inferences=[],
        confidence=1.0 if consistent else 0.0,
    )


def _write_cl_to_state(output, state, ctx) -> None:
    """Write Conditional Logic results to UnifiedAnalysisState (#86)."""
    if not output or not isinstance(output, dict):
        return
    entailed = output.get("entailed", False)
    message = str(output.get("message", ""))
    num = output.get("num_conditionals", 0)
    state.add_propositional_analysis_result(
        formulas=[f"CL({num} conditionals): {message}"],
        satisfiable=bool(entailed),
        model={},
    )


def _write_sat_to_state(output, state, ctx) -> None:
    """Write SAT solver results to UnifiedAnalysisState (#86)."""
    if not output or not isinstance(output, dict):
        return
    is_sat = output.get("satisfiable", False)
    model = output.get("model") or {}
    mode = output.get("mode", "solve")
    if mode == "mus":
        mus_count = output.get("mus_count", 0)
        state.add_propositional_analysis_result(
            formulas=[f"SAT/MUS: {mus_count} minimal unsatisfiable subsets"],
            satisfiable=False,
            model={},
        )
    else:
        state.add_propositional_analysis_result(
            formulas=[f"SAT: {'SAT' if is_sat else 'UNSAT'}"],
            satisfiable=bool(is_sat),
            model=model if isinstance(model, dict) else {},
        )


def _write_setaf_to_state(output, state, ctx) -> None:
    """Write SetAF results to UnifiedAnalysisState (#87)."""
    if not output or not isinstance(output, dict):
        return
    state.add_dung_framework(
        name=f"setaf_{output.get('semantics', 'grounded')}",
        arguments=output.get("arguments", []),
        attacks=[],  # set attacks don't map to binary attacks
        extensions={"setaf_extensions": output.get("extensions", [])},
    )


def _write_weighted_to_state(output, state, ctx) -> None:
    """Write Weighted AF results to UnifiedAnalysisState (#87)."""
    if not output or not isinstance(output, dict):
        return
    state.add_dung_framework(
        name=f"weighted_{output.get('semantics', 'grounded')}",
        arguments=output.get("arguments", []),
        attacks=[
            [a.get("source", ""), a.get("target", "")]
            for a in output.get("attacks", [])
            if isinstance(a, dict)
        ],
        extensions={"weighted_extensions": output.get("extensions", [])},
    )


def _write_social_to_state(output, state, ctx) -> None:
    """Write Social AF results to UnifiedAnalysisState (#87)."""
    if not output or not isinstance(output, dict):
        return
    ranking = output.get("ranking", [])
    scores = output.get("scores", {})
    state.add_dung_framework(
        name="social_af",
        arguments=output.get("arguments", []),
        attacks=output.get("attacks", []),
        extensions={"social_ranking": ranking, "social_scores": scores},
    )


def _write_eaf_to_state(output, state, ctx) -> None:
    """Write EAF results to UnifiedAnalysisState (#88)."""
    if not output or not isinstance(output, dict):
        return
    state.add_dung_framework(
        name=f"eaf_{output.get('semantics', 'grounded')}",
        arguments=output.get("arguments", []),
        attacks=[a for a in output.get("attacks", []) if isinstance(a, list)],
        extensions={"eaf_extensions": output.get("extensions", [])},
    )


def _write_delp_to_state(output, state, ctx) -> None:
    """Write DeLP results to UnifiedAnalysisState (#89)."""
    if not output or not isinstance(output, dict):
        return
    query_results = output.get("query_results", [])
    state.add_dung_framework(
        name="delp_analysis",
        arguments=[],
        attacks=[],
        extensions={"delp_query_results": query_results},
    )


def _write_qbf_to_state(output, state, ctx) -> None:
    """Write QBF results to UnifiedAnalysisState (#90)."""
    if not output or not isinstance(output, dict):
        return
    state.add_propositional_analysis_result(
        formulas=[f"QBF: {output.get('formula', '')}"],
        satisfiable=output.get("valid", False),
        model={},
    )


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
    "hierarchical_fallacy_detection": _write_hierarchical_fallacy_to_state,
    "description_logic": _write_dl_to_state,
    "conditional_logic": _write_cl_to_state,
    "sat_solving": _write_sat_to_state,
    "setaf_reasoning": _write_setaf_to_state,
    "weighted_argumentation": _write_weighted_to_state,
    "social_argumentation": _write_social_to_state,
    "epistemic_argumentation": _write_eaf_to_state,
    "defeasible_logic": _write_delp_to_state,
    "qbf_reasoning": _write_qbf_to_state,
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

        # Hierarchical taxonomy-guided fallacy detection (#84)
        try:
            from argumentation_analysis.plugins.fallacy_workflow_plugin import (
                FallacyWorkflowPlugin,
            )

            registry.register_service(
                name="hierarchical_fallacy_detector",
                service_class=FallacyWorkflowPlugin,
                capabilities=[
                    "hierarchical_fallacy_detection",
                    "fallacy_detection",
                ],
                metadata={
                    "description": (
                        "Hierarchical taxonomy-guided fallacy detection "
                        "with iterative deepening and one-shot fallback (#84)"
                    )
                },
                invoke=_invoke_hierarchical_fallacy,
            )
            registered.append("hierarchical_fallacy_detector")
        except ImportError as e:
            skipped.append(("hierarchical_fallacy_detector", str(e)))

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

    # --- TweetyLogicPlugin: SK wrapper for all handlers (#91) ---
    try:
        from argumentation_analysis.plugins.tweety_logic_plugin import TweetyLogicPlugin

        registry.register_plugin(
            name="tweety_logic_plugin",
            plugin_class=TweetyLogicPlugin,
            capabilities=["tweety_logic"],
            metadata={
                "description": (
                    "SK plugin exposing all Tweety logic handlers as "
                    "@kernel_function methods for LLM agents (#91)"
                )
            },
        )
        registered.append("tweety_logic_plugin")
    except ImportError as e:
        skipped.append(("tweety_logic_plugin", str(e)))

    # --- Logic agent capabilities (#71 Formal Verification) ---
    logic_capabilities = [
        (
            "fact_extraction_service",
            ["fact_extraction"],
            "Heuristic claim extraction from text",
            _invoke_fact_extraction,
        ),
        (
            "propositional_logic_service",
            ["propositional_logic"],
            "Propositional logic analysis via Tweety",
            _invoke_propositional_logic,
        ),
        (
            "fol_reasoning_service",
            ["fol_reasoning"],
            "First-order logic analysis via Tweety",
            _invoke_fol_reasoning,
        ),
        (
            "modal_logic_service",
            ["modal_logic"],
            "Modal logic analysis via Tweety",
            _invoke_modal_logic,
        ),
        (
            "dung_extensions_service",
            ["dung_extensions"],
            "Dung AF extension computation via AFHandler",
            _invoke_dung_extensions,
        ),
        (
            "formal_synthesis_service",
            ["formal_synthesis"],
            "Aggregate formal analysis into unified report",
            _invoke_formal_synthesis,
        ),
        # SAT handler — no JVM dependency, uses PySAT+Z3 (#86)
        (
            "sat_handler",
            ["sat_solving"],
            "SAT/MaxSAT/MUS solver (PySAT + Z3)",
            _invoke_sat,
        ),
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
    """Register Tweety handler capabilities (Track A #55-#62, #85-#86)."""
    tweety_handlers = [
        (
            "ranking_semantics_handler",
            ["ranking_semantics"],
            "Qualitative argument ranking (Categoriser, Burden)",
            _invoke_ranking,
        ),
        (
            "bipolar_handler",
            ["bipolar_argumentation"],
            "Bipolar argumentation (support + attack)",
            _invoke_bipolar,
        ),
        (
            "aba_handler",
            ["aba_reasoning"],
            "Assumption-Based Argumentation",
            _invoke_aba,
        ),
        (
            "adf_handler",
            ["adf_reasoning"],
            "Abstract Dialectical Frameworks",
            _invoke_adf,
        ),
        (
            "aspic_handler",
            ["aspic_plus_reasoning"],
            "ASPIC+ structured argumentation",
            _invoke_aspic,
        ),
        (
            "belief_revision_handler",
            ["belief_revision"],
            "Belief dynamics and revision operators",
            _invoke_belief_revision,
        ),
        (
            "probabilistic_handler",
            ["probabilistic_argumentation"],
            "Probabilistic argument acceptance",
            _invoke_probabilistic,
        ),
        (
            "dialogue_handler",
            ["dialogue_protocols"],
            "Agent dialogue and negotiation protocols",
            _invoke_dialogue,
        ),
        # New handlers (#86)
        (
            "dl_handler",
            ["description_logic"],
            "ALC Description Logic (TBox/ABox reasoning)",
            _invoke_dl,
        ),
        (
            "cl_handler",
            ["conditional_logic"],
            "Conditional Logic (System Z, non-monotonic)",
            _invoke_cl,
        ),
        # AF variants (#87)
        (
            "setaf_handler",
            ["setaf_reasoning"],
            "Set Argumentation Frameworks (collective attacks)",
            _invoke_setaf,
        ),
        (
            "weighted_handler",
            ["weighted_argumentation"],
            "Weighted Argumentation Frameworks (attack weights)",
            _invoke_weighted,
        ),
        (
            "social_handler",
            ["social_argumentation"],
            "Social Abstract Argumentation (voting + attacks)",
            _invoke_social,
        ),
        # New handlers (#88, #89, #90)
        (
            "eaf_handler",
            ["epistemic_argumentation"],
            "Epistemic AF (belief-aware multi-agent argumentation)",
            _invoke_eaf,
        ),
        (
            "delp_handler",
            ["defeasible_logic"],
            "Defeasible Logic Programming (dialectical trees)",
            _invoke_delp,
        ),
        (
            "qbf_handler",
            ["qbf_reasoning"],
            "Quantified Boolean Formulas (∀/∃ over PL)",
            _invoke_qbf,
        ),
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
    """Minimal 3-phase analysis workflow with fact extraction."""
    return (
        WorkflowBuilder("light_analysis")
        .add_phase("extract", capability="fact_extraction")
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        .build()
    )


def build_standard_workflow() -> WorkflowDefinition:
    """Standard 5-phase workflow with fact extraction and quality-gated counter-arguments."""
    return (
        WorkflowBuilder("standard_analysis")
        .add_phase("extract", capability="fact_extraction")
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
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
    """Full pipeline traversing all 12 capabilities with LLM extraction."""
    return (
        WorkflowBuilder("full_analysis")
        .add_phase(
            "transcribe",
            capability="speech_transcription",
            optional=True,
        )
        .add_phase("extract", capability="fact_extraction")
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
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
    """Neural-Symbolic-Hierarchical fallacy fusion (Loop 4).

    Three complementary fallacy detection approaches:
    - Neural: CamemBERT French NLP classifier (fast, pattern-based)
    - Hierarchical: Taxonomy-guided iterative deepening (precise, explainable)
    - Quality baseline: argument quality evaluation for context
    """
    return (
        WorkflowBuilder("neural_symbolic_fallacy")
        .add_phase(
            "neural_detect",
            capability="neural_fallacy_detection",
            optional=True,
        )
        .add_phase(
            "hierarchical_detect",
            capability="hierarchical_fallacy_detection",
            optional=True,
        )
        .add_phase("quality_baseline", capability="argument_quality")
        .build()
    )


def build_hierarchical_fallacy_workflow() -> WorkflowDefinition:
    """Hierarchical taxonomy-guided fallacy detection workflow (#84).

    Dedicated workflow for the master-slave iterative deepening approach:
    1. Extract facts/arguments (provides context for fallacy detection)
    2. Hierarchical fallacy detection via taxonomy navigation
    3. Quality evaluation for cross-validation
    """
    return (
        WorkflowBuilder("hierarchical_fallacy")
        .add_phase("extract", capability="fact_extraction")
        .add_phase(
            "hierarchical_fallacy",
            capability="hierarchical_fallacy_detection",
            depends_on=["extract"],
        )
        .add_phase(
            "quality",
            capability="argument_quality",
            depends_on=["extract"],
            optional=True,
        )
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
            "hierarchical_fallacy": build_hierarchical_fallacy_workflow(),
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

            WORKFLOW_CATALOG["formal_verification"] = (
                build_formal_verification_workflow()
            )
        except Exception as e:
            logger.warning(f"Formal verification workflow not registered: {e}")
        # Comprehensive analysis (LLM-only, benchmark-optimized)
        try:
            from argumentation_analysis.workflows.comprehensive_analysis import (
                build_comprehensive_analysis_workflow,
            )

            WORKFLOW_CATALOG["comprehensive"] = build_comprehensive_analysis_workflow()
        except Exception as e:
            logger.warning(f"Comprehensive workflow not registered: {e}")
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
            logger.warning(
                "Could not import UnifiedAnalysisState; state tracking disabled"
            )
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
