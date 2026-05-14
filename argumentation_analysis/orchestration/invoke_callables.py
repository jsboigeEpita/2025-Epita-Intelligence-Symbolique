"""Invoke callables for the unified pipeline.

Each _invoke_* function implements a single pipeline capability.
They are registered in the CapabilityRegistry by setup_registry().

Split from unified_pipeline.py (#310).
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("UnifiedPipeline")

# Ensure .env is loaded so OPENAI_API_KEY is available for all invoke callables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Export all underscore-prefixed functions for star-import in unified_pipeline facade
__all__ = [
    "_get_openai_client",
    "_invoke_quality_evaluator",
    "_aggregate_virtue_scores",
    "_llm_enrich_quality",
    "_invoke_counter_argument",
    "_evaluate_counter_arguments",
    "_invoke_debate_analysis",
    "_invoke_governance",
    "_invoke_jtms",
    "_invoke_atms",
    "_generate_hypotheses",
    "_invoke_camembert_fallacy",
    "_invoke_local_llm",
    "_invoke_semantic_index",
    "_invoke_speech_transcription",
    "_extract_arguments_from_context",
    "_generate_attacks_from_args",
    "_python_ranking_fallback",
    "_enrich_ranking_with_justification",
    "_invoke_ranking",
    "_invoke_bipolar",
    "_invoke_aba",
    "_invoke_adf",
    "_python_aspic_fallback",
    "_invoke_aspic",
    "_invoke_belief_revision",
    "_invoke_probabilistic",
    "_invoke_dialogue",
    "_invoke_dl",
    "_invoke_cl",
    "_invoke_sat",
    "_invoke_setaf",
    "_invoke_weighted",
    "_invoke_social",
    "_python_social_fallback",
    "_python_eaf_fallback",
    "_invoke_eaf",
    "_invoke_delp",
    "_invoke_qbf",
    "_invoke_asp_reasoning",
    "_invoke_hierarchical_fallacy",
    "_normalize_items_with_quotes",
    "_normalize_fallacies_with_quotes",
    "_invoke_fact_extraction",
    "_invoke_propositional_logic",
    "_invoke_fol_reasoning",
    "_invoke_nl_to_logic",
    "_invoke_modal_logic",
    "_invoke_dung_extensions",
    "_python_dung_fallback",
    "_invoke_formal_synthesis",
    "_invoke_narrative_synthesis",
]


def _get_openai_client() -> Tuple[Any, str]:
    """Create an AsyncOpenAI client from environment variables.

    Returns (client, model_id) or (None, "") if API key unavailable.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None, ""
    try:
        from openai import AsyncOpenAI

        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
        return AsyncOpenAI(api_key=api_key, base_url=base_url), model_id
    except ImportError:
        return None, ""


# --- Invoke callables for registered components ---
# Each callable: async (input_text: str, context: Dict[str, Any]) -> Any


async def _invoke_quality_evaluator(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke 9-virtue argument quality evaluator on each extracted argument.

    Evaluates individual arguments from upstream fact_extraction rather than
    the entire raw text, producing per-argument quality scores.
    """
    from argumentation_analysis.agents.core.quality.quality_evaluator import (
        ArgumentQualityEvaluator,
    )

    evaluator = ArgumentQualityEvaluator()

    # Get individual arguments from upstream
    extract_output = context.get("phase_extract_output", {})
    raw_args = (
        extract_output.get("arguments", []) if isinstance(extract_output, dict) else []
    )

    # (#289) Read fallacy output to penalize arguments affected by fallacies
    fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
    detected_fallacies = (
        fallacy_output.get("fallacies", []) if isinstance(fallacy_output, dict) else []
    )
    # Build a map: arg_index → list of fallacy types targeting that argument
    fallacy_targets: Dict[int, list[str]] = {}
    for f in detected_fallacies:
        if not isinstance(f, dict):
            continue
        target_text = f.get("target_argument", "")
        fallacy_type = f.get("type", f.get("fallacy_type", "unknown"))
        if target_text and raw_args:
            target_lower = target_text.lower()[:80]
            for idx, a in enumerate(raw_args[:8]):
                a_text = (
                    a.get("text", str(a)) if isinstance(a, dict) else str(a)
                ).lower()
                if target_lower in a_text or a_text[:40] in target_lower:
                    fallacy_targets.setdefault(idx, []).append(str(fallacy_type))
                    break

    if raw_args:
        results = {}
        for i, arg in enumerate(raw_args[:8]):  # Cap at 8 to avoid timeout
            arg_text = arg.get("text", str(arg)) if isinstance(arg, dict) else str(arg)
            if len(arg_text) < 10:
                continue
            arg_id = f"arg_{i+1}"
            result = await asyncio.to_thread(evaluator.evaluate, arg_text)
            if isinstance(result, dict):
                # (#289) Penalize score if argument is targeted by a fallacy
                if i in fallacy_targets:
                    penalty = min(0.3 * len(fallacy_targets[i]), 0.6)
                    original_score = result.get("note_finale", 0)
                    result["note_finale"] = max(
                        0, original_score - original_score * penalty
                    )
                    result["fallacy_penalty"] = {
                        "applied": True,
                        "fallacies": fallacy_targets[i],
                        "penalty_factor": penalty,
                        "original_score": original_score,
                    }
                results[arg_id] = result
        # Also compute aggregate
        if results:
            all_overalls = [
                r.get("note_finale", 0)
                for r in results.values()
                if isinstance(r.get("note_finale"), (int, float))
            ]
            aggregate_score = (
                sum(all_overalls) / len(all_overalls) if all_overalls else 0
            )

            # LLM enrichment pass (#290): deeper qualitative analysis with fallacy context
            llm_enrichment = await _llm_enrich_quality(
                results, raw_args, detected_fallacies
            )

            # (#290) Merge per-argument LLM assessments back into results
            if llm_enrichment and isinstance(llm_enrichment.get("enrichments"), list):
                for enr in llm_enrichment["enrichments"]:
                    if not isinstance(enr, dict):
                        continue
                    eid = enr.get("arg_id", "")
                    if eid in results and isinstance(results[eid], dict):
                        results[eid]["llm_assessment"] = enr.get("llm_assessment", "")
                        results[eid]["reasoning_assessment"] = enr.get(
                            "reasoning_assessment", ""
                        )
                        results[eid]["evidence_quality"] = enr.get(
                            "evidence_quality", ""
                        )
                        results[eid]["bias_indicators"] = enr.get("bias_indicators", [])

            output = {
                "per_argument_scores": results,
                "aggregate_score": round(aggregate_score, 2),
                "arguments_evaluated": len(results),
                # Keep top-level keys for state writer compatibility
                "note_finale": aggregate_score,
                "scores_par_vertu": _aggregate_virtue_scores(results),
            }
            if detected_fallacies:
                output["fallacy_cross_reference"] = {
                    "fallacies_found": len(detected_fallacies),
                    "arguments_penalized": len(fallacy_targets),
                }
            if llm_enrichment:
                output["llm_enrichment"] = llm_enrichment
            return output
        # Fallback if no results
        return await asyncio.to_thread(evaluator.evaluate, input_text)
    else:
        return await asyncio.to_thread(evaluator.evaluate, input_text)


def _aggregate_virtue_scores(per_arg_results: Dict[str, Any]) -> Dict[str, float]:
    """Average virtue scores across all evaluated arguments."""
    all_virtues: Dict[str, list[float]] = {}
    for result in per_arg_results.values():
        if not isinstance(result, dict):
            continue
        scores = result.get("scores_par_vertu", {})
        if not isinstance(scores, dict):
            continue
        for virtue, score in scores.items():
            if isinstance(score, (int, float)):
                all_virtues.setdefault(virtue, []).append(score)
    return {
        v: round(sum(vals) / len(vals), 2) for v, vals in all_virtues.items() if vals
    }


async def _llm_enrich_quality(
    heuristic_results: Dict[str, Any],
    raw_args: List[Any],
    detected_fallacies: Optional[List[Any]] = None,
) -> Optional[Dict[str, Any]]:
    """LLM enrichment pass for quality evaluation (#290).

    Sends heuristic scores + argument text + fallacy context to LLM for
    deeper qualitative analysis: implicit assumptions, reasoning strength,
    evidence quality, bias indicators.
    The LLM enriches — it does NOT replace heuristic scores.

    Returns None if LLM is unavailable or fails.
    """
    try:
        client, model_id = _get_openai_client()
        if not client:
            return None

        # Build summary of heuristic scores for LLM context
        score_summary = []
        for arg_id, scores in list(heuristic_results.items())[:4]:
            if not isinstance(scores, dict):
                continue
            virtues = scores.get("scores_par_vertu", {})
            note = scores.get("note_finale", 0)
            # Find the corresponding argument text
            idx = int(arg_id.split("_")[-1]) - 1 if "_" in arg_id else 0
            arg_text = ""
            if idx < len(raw_args):
                a = raw_args[idx]
                arg_text = a.get("text", str(a)) if isinstance(a, dict) else str(a)
            weakest = min(virtues, key=virtues.get) if virtues else "unknown"
            penalty_info = ""
            fallacy_penalty = scores.get("fallacy_penalty", {})
            if fallacy_penalty.get("applied"):
                penalty_info = (
                    f"\n  FALLACY PENALTY: {fallacy_penalty.get('fallacies', [])}, "
                    f"penalty={fallacy_penalty.get('penalty_factor', 0):.0%}"
                )
            score_summary.append(
                f"[{arg_id}] score={note:.1f}/9, weakest={weakest}\n"
                f"  Text: {arg_text[:200]}{penalty_info}"
            )

        if not score_summary:
            return None

        # (#290) Include fallacy context in prompt
        fallacy_context = ""
        if detected_fallacies:
            fallacy_lines = []
            for f in detected_fallacies[:6]:
                if not isinstance(f, dict):
                    continue
                ftype = f.get("type", f.get("fallacy_type", "unknown"))
                target = f.get("target_argument", "")[:80]
                fallacy_lines.append(f'  - {ftype}: "{target}"')
            if fallacy_lines:
                fallacy_context = (
                    "\n\nDETECTED FALLACIES in this text:\n"
                    + "\n".join(fallacy_lines)
                    + "\n\nFactor these fallacies into your quality assessment. "
                    "Arguments affected by fallacies should receive harsher assessments "
                    "on reasoning_assessment and evidence_quality."
                )

        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an argument quality expert. Given heuristic quality scores "
                        "for arguments, provide deeper qualitative analysis. For each argument:\n"
                        "1. Identify implicit assumptions\n"
                        "2. Assess reasoning strength (beyond what regex can detect)\n"
                        "3. Evaluate evidence quality\n"
                        "4. Note any bias indicators\n"
                        "5. Suggest how the weakest virtue could be improved\n"
                        "6. Write a brief qualitative assessment (2-3 sentences)\n\n"
                        "Respond with ONLY a JSON object:\n"
                        '{"enrichments": [{"arg_id": "arg_1", '
                        '"implicit_assumptions": ["..."], '
                        '"reasoning_assessment": "strong/moderate/weak", '
                        '"evidence_quality": "strong/moderate/weak/none", '
                        '"bias_indicators": ["..."], '
                        '"improvement_suggestion": "...", '
                        '"llm_assessment": "Brief qualitative narrative..."}]}'
                    ),
                },
                {
                    "role": "user",
                    "content": "\n\n".join(score_summary) + fallacy_context,
                },
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
            return json.loads(text_content[start:end])  # type: ignore[no-any-return]
    except Exception as e:
        logger.debug(f"LLM quality enrichment skipped: {e}")
    return None


async def _invoke_counter_argument(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke counter-argument analysis via plugin + LLM enrichment."""
    from argumentation_analysis.agents.core.counter_argument.counter_agent import (
        CounterArgumentPlugin,
    )

    plugin = CounterArgumentPlugin()  # type: ignore[no-untyped-call]
    parsed_json = plugin.parse_argument(input_text)
    strategy_json = plugin.suggest_strategy(input_text)
    parsed = json.loads(parsed_json)
    strategy = json.loads(strategy_json)

    # Enrich with LLM-generated counter-arguments for fallacious/weak arguments
    llm_counters = []
    try:
        client, model_id = _get_openai_client()
        if client:
            # Collect fallacious arguments + weakest arguments for targeted CAs
            extract_output = context.get("phase_extract_output", {})
            arguments = extract_output.get("arguments", [])
            fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
            fallacies = (
                fallacy_output.get("fallacies", [])
                if isinstance(fallacy_output, dict)
                else []
            )

            # (#289) Read quality scores to prioritize weakest arguments
            quality_output = context.get("phase_quality_output", {})
            per_arg_scores = (
                quality_output.get("per_argument_scores", {})
                if isinstance(quality_output, dict)
                else {}
            )

            # Build targets: fallacious arguments first, then weakest by quality
            targets = []
            for f in fallacies[:3]:  # Top 3 fallacies
                if isinstance(f, dict):
                    targets.append(
                        f"[FALLACY: {f.get('type', f.get('fallacy_type', ''))}] "
                        f"{f.get('explanation', '')[:100]}"
                    )

            # Sort arguments by quality score (ascending = weakest first)
            scored_args = []
            for i, a in enumerate(arguments):
                text = a.get("text", str(a)) if isinstance(a, dict) else str(a)
                score_key = f"arg_{i+1}"
                score = per_arg_scores.get(score_key, {}).get("note_finale", 5.0)
                scored_args.append((score, text))
            scored_args.sort(key=lambda x: x[0])  # weakest first

            for score, text in scored_args:
                if text and len(targets) < 5:
                    targets.append(f"[quality={score:.1f}/10] {text}")

            if not targets:
                targets = [input_text[:500]]

            # Ask for counter-arguments for ALL targets at once
            targets_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(targets))
            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in argumentation and counter-argument generation. "
                            "For EACH argument/fallacy listed, generate a targeted counter-argument "
                            "using the most appropriate strategy: reductio ad absurdum, "
                            "counter-example, distinction, reformulation, or concession+pivot. "
                            "Respond with ONLY a JSON array:\n"
                            '[{"counter_argument": "text", "strategy_used": "name", '
                            '"target_argument": "which argument", "strength": "weak|moderate|strong", '
                            '"reasoning": "why this works"}, ...]'
                        ),
                    },
                    {"role": "user", "content": targets_text},
                ],
            )
            raw = response.choices[0].message.content or ""
            text_content = raw.strip()
            if "```json" in text_content:
                text_content = text_content.split("```json")[1].split("```")[0]
            elif "```" in text_content:
                text_content = text_content.split("```")[1].split("```")[0]
            # Try to parse as array first, then single object
            start_arr = text_content.find("[")
            end_arr = text_content.rfind("]") + 1
            if start_arr >= 0 and end_arr > start_arr:
                llm_counters = json.loads(text_content[start_arr:end_arr])
            else:
                start = text_content.find("{")
                end = text_content.rfind("}") + 1
                if start >= 0 and end > start:
                    llm_counters = [json.loads(text_content[start:end])]
    except Exception as e:
        logger.warning(f"LLM counter-argument enrichment failed: {e}")

    # (#294) Auto-evaluate each LLM counter-argument
    if llm_counters:
        llm_counters = _evaluate_counter_arguments(llm_counters, input_text)

    result = {
        "parsed_argument": parsed,
        "suggested_strategy": strategy,
        "quality_context": context.get("phase_quality_output"),
    }
    if llm_counters:
        # Keep first as llm_counter_argument for backward compat
        result["llm_counter_argument"] = llm_counters[0] if llm_counters else None
        result["llm_counter_arguments"] = llm_counters
    return result


def _evaluate_counter_arguments(
    llm_counters: List[Dict[str, Any]], input_text: str
) -> List[Dict[str, Any]]:
    """Auto-evaluate each LLM counter-argument using CounterArgumentEvaluator (#294).

    Wraps each LLM-generated dict into proper Argument/CounterArgument dataclass
    objects, runs the 5-criteria evaluator, and attaches the evaluation_score.
    """
    try:
        from argumentation_analysis.agents.core.counter_argument.evaluator import (
            CounterArgumentEvaluator,
        )
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            Argument,
            CounterArgument as CADataclass,
            CounterArgumentType,
            ArgumentStrength,
        )
    except ImportError:
        return llm_counters

    evaluator = CounterArgumentEvaluator()  # type: ignore[no-untyped-call]
    strength_map = {
        "weak": ArgumentStrength.WEAK,
        "moderate": ArgumentStrength.MODERATE,
        "strong": ArgumentStrength.STRONG,
        "decisive": ArgumentStrength.DECISIVE,
    }
    strategy_to_type = {
        "reductio ad absurdum": CounterArgumentType.REDUCTIO_AD_ABSURDUM,
        "counter-example": CounterArgumentType.COUNTER_EXAMPLE,
        "distinction": CounterArgumentType.ALTERNATIVE_EXPLANATION,
        "reformulation": CounterArgumentType.ALTERNATIVE_EXPLANATION,
        "concession": CounterArgumentType.PREMISE_CHALLENGE,
    }

    for ca_dict in llm_counters:
        if not isinstance(ca_dict, dict) or not ca_dict.get("counter_argument"):
            continue
        try:
            target_text = ca_dict.get("target_argument", input_text[:200])
            original = Argument(
                content=str(target_text),
                premises=[str(target_text)],
                conclusion=str(target_text)[:100],
                argument_type="claim",
                confidence=0.5,
            )
            strategy_used = str(ca_dict.get("strategy_used", "")).lower()
            ca_type = CounterArgumentType.DIRECT_REFUTATION
            for key, val in strategy_to_type.items():
                if key in strategy_used:
                    ca_type = val
                    break
            ca_obj = CADataclass(
                original_argument=original,
                counter_type=ca_type,
                counter_content=str(ca_dict["counter_argument"]),
                target_component="premise",
                strength=strength_map.get(
                    str(ca_dict.get("strength", "moderate")).lower(),
                    ArgumentStrength.MODERATE,
                ),
                confidence=0.5,
                rhetorical_strategy=strategy_used,
            )
            evaluation = evaluator.evaluate(original, ca_obj)
            ca_dict["evaluation"] = {
                "overall_score": round(evaluation.overall_score, 3),
                "relevance": round(evaluation.relevance, 3),
                "logical_strength": round(evaluation.logical_strength, 3),
                "persuasiveness": round(evaluation.persuasiveness, 3),
                "originality": round(evaluation.originality, 3),
                "clarity": round(evaluation.clarity, 3),
                "recommendations": evaluation.recommendations,
            }
        except Exception as e:
            logger.debug(f"Counter-argument evaluation skipped: {e}")
    return llm_counters


async def _invoke_debate_analysis(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke debate argument analysis via plugin + LLM adversarial assessment."""
    from argumentation_analysis.agents.core.debate.debate_agent import DebatePlugin

    plugin = DebatePlugin()  # type: ignore[no-untyped-call]
    scores_json = plugin.analyze_argument_quality(input_text)
    base_scores = json.loads(scores_json)

    # Enrich with LLM-based adversarial debate assessment
    try:
        client, model_id = _get_openai_client()
        if client:
            # Build adversarial debate from upstream analysis
            extract_output = context.get("phase_extract_output", {})
            raw_arguments = extract_output.get("arguments", [])
            # (#289) Read fallacies from hierarchical fallacy phase, not extract
            fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
            raw_fallacies = (
                fallacy_output.get("fallacies", [])
                if isinstance(fallacy_output, dict)
                else []
            )
            counter_output = context.get("phase_counter_output", {})
            raw_cas = (
                counter_output.get("llm_counter_arguments", [])
                if isinstance(counter_output, dict)
                else []
            )
            # (#289) Cross-KB: quality scores + JTMS beliefs inform debate
            quality_output = context.get("phase_quality_output", {})
            per_arg_scores = (
                quality_output.get("per_argument_scores", {})
                if isinstance(quality_output, dict)
                else {}
            )
            jtms_output = context.get("phase_jtms_output", {})

            def _txt(item: Any) -> str:
                return (
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                )

            # Build structured debate material
            debate_parts = []
            if raw_arguments:
                debate_parts.append(
                    "ARGUMENTS identified:\n"
                    + "\n".join(
                        f"  A{i+1}. {_txt(a)}" for i, a in enumerate(raw_arguments[:6])
                    )
                )
            if raw_fallacies:
                debate_parts.append(
                    "FALLACIES detected:\n"
                    + "\n".join(
                        f"  F{i+1}. {_txt(f)} — {f.get('justification', '')[:80] if isinstance(f, dict) else ''}"
                        for i, f in enumerate(raw_fallacies[:5])
                    )
                )
            if raw_cas:
                debate_parts.append(
                    "COUNTER-ARGUMENTS available:\n"
                    + "\n".join(
                        f"  CA{i+1}. [{ca.get('strategy_used', '?')}] {ca.get('counter_argument', '')[:100]}"
                        for i, ca in enumerate(raw_cas[:5])
                        if isinstance(ca, dict)
                    )
                )
            # (#289) Cross-KB: quality scores tell debate which args are strong/weak
            if per_arg_scores:
                quality_lines = []
                for key, scores in list(per_arg_scores.items())[:6]:
                    if isinstance(scores, dict):
                        note = scores.get("note_finale", "?")
                        penalty = scores.get("fallacy_penalty", {})
                        suffix = (
                            " [PENALIZED by fallacy]" if penalty.get("applied") else ""
                        )
                        quality_lines.append(f"  {key}: {note}/10{suffix}")
                if quality_lines:
                    debate_parts.append("QUALITY SCORES:\n" + "\n".join(quality_lines))
            # (#289) Cross-KB: JTMS beliefs inform debate about retracted claims
            if isinstance(jtms_output, dict) and jtms_output.get("beliefs"):
                retracted = [
                    k
                    for k, v in jtms_output["beliefs"].items()
                    if isinstance(v, dict) and not v.get("valid", True)
                ]
                if retracted:
                    debate_parts.append(
                        f"RETRACTED BELIEFS (JTMS): {', '.join(retracted[:5])}"
                    )
                if not jtms_output.get("formal_consistency", True):
                    debate_parts.append(
                        "WARNING: Formal inconsistency detected in PL/FOL analysis"
                    )

            debate_material = (
                "\n\n".join(debate_parts) if debate_parts else input_text[:1500]
            )

            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a debate moderator running an adversarial analysis. "
                            "Agent A DEFENDS the strongest arguments. "
                            "Agent B ATTACKS using detected fallacies and counter-arguments. "
                            "Produce a structured debate with new analytical insights "
                            "(perspectives the raw extraction alone doesn't reveal). "
                            "Respond with ONLY a JSON object:\n"
                            '{"strongest_argument": "which argument Agent A defends", '
                            '"weakest_argument": "which argument Agent B targets", '
                            '"winner": "Agent A|Agent B|draw", '
                            '"debate_quality": 1-5, '
                            '"key_exchanges": [{"agent_a_point": "text", "agent_b_rebuttal": "text", "judge_note": "text"}], '
                            '"new_insights": ["insight 1 not obvious from extraction alone", ...], '
                            '"reasoning": "assessment of argumentative quality"}'
                        ),
                    },
                    {"role": "user", "content": debate_material},
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

    return base_scores  # type: ignore[no-any-return]


async def _invoke_governance(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke governance analysis via plugin + LLM-powered deliberation assessment."""
    from argumentation_analysis.plugins.governance_plugin import GovernancePlugin

    plugin = GovernancePlugin()
    methods_json = plugin.list_governance_methods()
    available_methods = json.loads(methods_json)

    # (#289) Build positions from upstream phases (extract, debate, counter, quality, fallacy, jtms)
    extract_output = context.get("phase_extract_output", {})
    debate_output = context.get("phase_debate_output", {})
    counter_output = context.get("phase_counter_output", {})
    quality_output = context.get("phase_quality_output", {})
    fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
    jtms_output = context.get("phase_jtms_output", {})

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

    # (#294) Auto-run social choice vote when we have enough positions
    vote_result = None
    if len(positions) >= 2:
        try:
            options = list(positions.keys())
            # Build preference ballots: each agent ranks others based on position order
            ballots = []
            for agent in options:
                pref = [a for a in options if a != agent] + [agent]
                ballots.append(pref)
            vote_input = json.dumps(
                {
                    "method": "copeland",
                    "ballots": ballots,
                    "options": options,
                }
            )
            vote_result = json.loads(plugin.social_choice_vote(vote_input))
        except Exception as e:
            logger.debug(f"Social choice vote skipped: {e}")

    # Enrich with LLM-based governance and deliberation assessment
    llm_governance = None
    try:
        client, model_id = _get_openai_client()
        if client:
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
            cas = counter_output.get("llm_counter_arguments", [])
            if isinstance(cas, list) and cas:
                ca_lines = []
                for ca in cas[:5]:
                    if isinstance(ca, dict):
                        ca_lines.append(
                            f"  - [{ca.get('strategy_used', '?')}] "
                            f"{ca.get('counter_argument', '')[:150]}"
                        )
                context_parts.append(
                    f"Counter-arguments ({len(ca_lines)}):\n" + "\n".join(ca_lines)
                )
            elif counter_output.get("llm_counter_argument"):
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
            # (#289) Cross-KB: quality scores, fallacies, JTMS inform governance
            per_arg_scores = (
                quality_output.get("per_argument_scores", {})
                if isinstance(quality_output, dict)
                else {}
            )
            if per_arg_scores:
                avg_score = sum(
                    s.get("note_finale", 0)
                    for s in per_arg_scores.values()
                    if isinstance(s, dict)
                ) / max(len(per_arg_scores), 1)
                penalized = sum(
                    1
                    for s in per_arg_scores.values()
                    if isinstance(s, dict)
                    and s.get("fallacy_penalty", {}).get("applied")
                )
                context_parts.append(
                    f"Quality assessment: avg score {avg_score:.1f}/10, "
                    f"{penalized} argument(s) penalized by fallacies"
                )
            raw_fallacies = (
                fallacy_output.get("fallacies", [])
                if isinstance(fallacy_output, dict)
                else []
            )
            if raw_fallacies:
                ftypes: list[str] = [
                    str(f.get("type", f.get("fallacy_type", "unknown")))
                    for f in raw_fallacies[:5]
                    if isinstance(f, dict)
                ]
                context_parts.append(f"Fallacies detected: {', '.join(ftypes)}")
            if isinstance(jtms_output, dict):
                retracted = [
                    k
                    for k, v in jtms_output.get("beliefs", {}).items()
                    if isinstance(v, dict) and not v.get("valid", True)
                ]
                if retracted:
                    context_parts.append(
                        f"JTMS retracted beliefs: {', '.join(retracted[:5])}"
                    )
                if not jtms_output.get("formal_consistency", True):
                    context_parts.append("Formal inconsistency detected in PL/FOL")

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
    if vote_result:
        result["vote_result"] = vote_result
    if llm_governance:
        result["llm_governance_assessment"] = llm_governance
        result["recommended_method"] = llm_governance.get("recommended_method")
        result["consensus_potential"] = llm_governance.get("consensus_potential")
    return result


async def _invoke_jtms(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke JTMS belief maintenance with ExtendedBelief and agent metadata (#214).

    Builds a proper belief network from upstream phase outputs:
    - Arguments → beliefs (IN premises, supported claims)
    - Fallacies → retract undermined beliefs via OUT-list
    - Counter-arguments → create competing OUT-list entries
    - Quality scores → modulate justification strength

    Uses JTMSSession with ExtendedBelief for agent source tracking and confidence (#214).
    """
    from argumentation_analysis.services.jtms.extended_belief import JTMSSession

    session = JTMSSession(session_id="pipeline_jtms", owner_agent="unified_pipeline")

    # ── Collect upstream data ────────────────────────────────────────
    extract_output = context.get("phase_extract_output", {})
    raw_args = (
        extract_output.get("arguments", []) if isinstance(extract_output, dict) else []
    )
    raw_claims = (
        extract_output.get("claims", []) if isinstance(extract_output, dict) else []
    )

    # Quality scores for justification strength
    quality_output = context.get("phase_quality_output", {})
    per_arg_scores = (
        quality_output.get("per_argument_scores", {})
        if isinstance(quality_output, dict)
        else {}
    )

    # Fallacies
    fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
    detected_fallacies = (
        fallacy_output.get("fallacies", []) if isinstance(fallacy_output, dict) else []
    )

    # Counter-arguments
    counter_output = context.get("phase_counter_output", {})
    counter_args = (
        counter_output.get("llm_counter_arguments", [])
        if isinstance(counter_output, dict)
        else []
    )

    # Formal reasoning results (#285 — cross-KB: formal feeds JTMS)
    pl_output = context.get("phase_pl_output", {})
    fol_output = context.get("phase_fol_output", {})
    formal_consistency = (
        pl_output.get("satisfiable", True) if isinstance(pl_output, dict) else True
    )

    # ── Build belief names ───────────────────────────────────────────
    def _text(item: Any) -> str:
        return (item.get("text", str(item)) if isinstance(item, dict) else str(item))[
            :80
        ]

    arg_beliefs = [_text(a) for a in raw_args[:10]]
    claim_beliefs = [_text(c) for c in raw_claims[:6]]

    if not arg_beliefs and not claim_beliefs:
        sentences = [s.strip() for s in input_text.split(".") if len(s.strip()) > 10]
        arg_beliefs = [s[:80] for s in sentences[:8]]

    # ── Step 1: Add argument and claim beliefs (with ExtendedBelief metadata) ─
    for i, name in enumerate(arg_beliefs + claim_beliefs):
        is_arg = i < len(arg_beliefs)
        belief_type = "premise" if is_arg else "claim"
        confidence: float = float(
            per_arg_scores.get(
                f"arg_{i+1}", per_arg_scores.get(f"argument_{i+1}", {})
            ).get("note_finale", 0.5)
        )
        session.add_belief(
            name,
            agent_source="unified_pipeline",
            context={"belief_type": belief_type, "index": i, "text": name},
            confidence=confidence,
        )

    # ── Step 2: Arguments support claims (dependency network) ────────
    # Each argument supports related claims (not sequential chain)
    if arg_beliefs and claim_beliefs:
        # Arguments collectively support each claim
        for claim in claim_beliefs:
            # All arguments are IN-list for each claim
            session.add_justification(
                arg_beliefs, [], claim, agent_source="unified_pipeline"
            )
    elif arg_beliefs:
        # No separate claims — arguments support a synthetic conclusion
        conclusion = "overall_argument_validity"
        session.add_belief(
            conclusion,
            agent_source="unified_pipeline",
            context={"belief_type": "synthetic_conclusion"},
            confidence=0.5,
        )
        session.add_justification(
            arg_beliefs, [], conclusion, agent_source="unified_pipeline"
        )

    # ── Step 3: Accept premises (set initial validity) ───────────────
    for name in arg_beliefs:
        session.set_fact(name, is_true=True)

    # ── Step 4: Fallacies → retract undermined beliefs + propagation ─
    fallacy_beliefs = []
    session.jtms.enable_tracing()  # type: ignore[no-untyped-call]  # Track retraction cascades (#350)
    for i, f in enumerate(detected_fallacies[:6]):
        if not isinstance(f, dict):
            continue
        fallacy_type = f.get("type", f.get("fallacy_type", f"fallacy_{i+1}"))
        fallacy_name = f"FALLACY:{fallacy_type}"[:80]
        confidence = float(f.get("confidence", f.get("severity", 0.7)))  # type: ignore[arg-type]
        session.add_belief(
            fallacy_name,
            agent_source="fallacy_detector",
            context={
                "fallacy_type": fallacy_type,
                "explanation": f.get("explanation", ""),
            },
            confidence=confidence,
        )
        session.set_fact(fallacy_name, is_true=True)  # Fallacy is confirmed
        fallacy_beliefs.append(fallacy_name)

        # Find which argument the fallacy undermines
        target_idx = -1
        target_arg_text = f.get("target_argument", "")
        if target_arg_text and arg_beliefs:
            # Try substring matching against belief names
            target_lower = target_arg_text.lower()[:80]
            for idx, ab in enumerate(arg_beliefs):
                if target_lower in ab.lower() or ab.lower() in target_lower:
                    target_idx = idx
                    break
        # Fallback: index-based matching
        if target_idx < 0 and arg_beliefs:
            target_idx = min(i, len(arg_beliefs) - 1)

        if target_idx >= 0:
            target_arg = arg_beliefs[target_idx]
            # Create a DEFEAT justification: fallacy OUT-lists the argument
            defeat_name = f"defeat:{fallacy_type}→{target_arg[:30]}"[:80]
            session.add_belief(
                defeat_name,
                agent_source="fallacy_detector",
                context={"defeat_type": "fallacy_undermining", "fallacy": fallacy_type},
                confidence=confidence,
            )
            # The defeat holds when the fallacy is IN and the argument is OUT
            session.add_justification(
                [fallacy_name],
                [target_arg],
                defeat_name,
                agent_source="fallacy_detector",
            )
            # Retract the undermined argument
            session.jtms.set_belief_validity(target_arg, False)

    # ── Step 5: Counter-arguments → competing beliefs ────────────────
    for i, ca in enumerate(counter_args[:4]):
        if not isinstance(ca, dict):
            continue
        ca_text = ca.get("counter_argument", f"counter_arg_{i+1}")[:80]
        target = ca.get("target_argument", "")[:40]
        confidence = float(ca.get("confidence", 0.6))
        session.add_belief(
            ca_text,
            agent_source="counter_argument_generator",
            context={"target": target, "index": i},
            confidence=confidence,
        )
        session.set_fact(ca_text, is_true=True)

        # Counter-argument weakens its target via OUT-list
        if target and any(target.lower() in ab.lower() for ab in arg_beliefs):
            matched = next(
                (ab for ab in arg_beliefs if target.lower() in ab.lower()),
                None,
            )
            if matched:
                rebuttal_name = f"rebuttal:{ca_text[:20]}→{matched[:20]}"[:80]
                session.add_belief(
                    rebuttal_name,
                    agent_source="counter_argument_generator",
                    context={"counter_text": ca_text, "target": matched},
                    confidence=confidence,
                )
                session.add_justification(
                    [ca_text],
                    [matched],
                    rebuttal_name,
                    agent_source="counter_argument_generator",
                )

    # ── Step 5b: Formal inconsistency → flag in belief network (#285) ─
    if not formal_consistency and arg_beliefs:
        inconsistency_name = "FORMAL_INCONSISTENCY"
        session.add_belief(
            inconsistency_name,
            agent_source="formal_logic",
            context={
                "pl_satisfiable": (
                    pl_output.get("satisfiable")
                    if isinstance(pl_output, dict)
                    else None
                ),
                "fol_satisfiable": (
                    fol_output.get("satisfiable")
                    if isinstance(fol_output, dict)
                    else None
                ),
            },
            confidence=0.9,
        )
        session.set_fact(inconsistency_name, is_true=True)

    # ── Step 6: Quality scores → annotate belief metadata ────────────
    quality_annotations = {}
    for arg_id, scores in per_arg_scores.items():
        if not isinstance(scores, dict):
            continue
        idx = int(arg_id.split("_")[-1]) - 1 if "_" in arg_id else -1
        if 0 <= idx < len(arg_beliefs):
            quality_annotations[arg_beliefs[idx]] = {
                "quality_score": scores.get("note_finale", 0),
                "weakest_virtue": min(
                    scores.get("scores_par_vertu", {"?": 0}),
                    key=scores.get("scores_par_vertu", {"?": 0}).get,
                ),
            }

    # ── Build output with ExtendedBelief metadata ────────────────────
    beliefs_output = {}
    for name, ext_belief in session.extended_beliefs.items():
        # Use JTMS belief (has justifications) not ExtendedBelief wrapper
        b = session.jtms.beliefs.get(name, ext_belief._jtms_belief)
        entry = {
            "valid": b.valid,
            "justifications": [
                {
                    "in_list": [ib.name[:40] for ib in j.in_list],
                    "out_list": [ob.name[:40] for ob in j.out_list],
                }
                for j in b.justifications
            ],
            "content": name,
            # ExtendedBelief metadata (#214)
            "agent_source": ext_belief.agent_source,
            "confidence": ext_belief.confidence,
            "context": ext_belief.context,
            "creation_timestamp": ext_belief.creation_timestamp.isoformat(),
            "modification_count": len(ext_belief.modification_history),
        }
        if name in quality_annotations:
            entry["quality"] = quality_annotations[name]
        beliefs_output[name] = entry

    return {
        "beliefs": beliefs_output,
        "belief_count": len(session.extended_beliefs),
        "justified_count": sum(
            1 for b in session.jtms.beliefs.values() if b.justifications
        ),
        "valid_count": sum(1 for b in session.jtms.beliefs.values() if b.valid is True),
        "undermined_count": sum(
            1 for b in session.jtms.beliefs.values() if b.valid is False
        ),
        "fallacy_count": len(fallacy_beliefs),
        "counter_argument_count": len(
            [ca for ca in counter_args[:4] if isinstance(ca, dict)]
        ),
        "has_real_dependencies": bool(
            arg_beliefs and (claim_beliefs or fallacy_beliefs)
        ),
        "formal_consistency": formal_consistency,
        "session_version": session.version,
        "consistency_checks": session.consistency_checks,
        "retraction_chain": session.jtms.get_retraction_chain(),
    }


async def _invoke_atms(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke ATMS assumption-based reasoning (#292).

    Builds an ATMS from upstream outputs: arguments and claims become assumption
    nodes, fallacies create contradiction-environments, formal-logic results
    constrain consistency. Returns minimal assumption environments per node.
    """
    from argumentation_analysis.services.jtms.atms_core import ATMS

    atms = ATMS()

    # ── Collect upstream data ────────────────────────────────────────
    extract_output = context.get("phase_extract_output", {})
    raw_args = (
        extract_output.get("arguments", []) if isinstance(extract_output, dict) else []
    )
    raw_claims = (
        extract_output.get("claims", []) if isinstance(extract_output, dict) else []
    )

    fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
    detected_fallacies = (
        fallacy_output.get("fallacies", []) if isinstance(fallacy_output, dict) else []
    )

    quality_output = context.get("phase_quality_output", {})
    per_arg_scores = (
        quality_output.get("per_argument_scores", {})
        if isinstance(quality_output, dict)
        else {}
    )

    # ── Helper ───────────────────────────────────────────────────────
    def _text(item: Any) -> str:
        return (item.get("text", str(item)) if isinstance(item, dict) else str(item))[
            :60
        ]

    # ── Step 1: Arguments → assumptions ──────────────────────────────
    arg_names: list[str] = []
    for a in raw_args[:8]:
        name = _text(a)
        atms.add_assumption(name)
        arg_names.append(name)

    if not arg_names:
        sentences = [s.strip() for s in input_text.split(".") if len(s.strip()) > 10]
        for s in sentences[:6]:
            atms.add_assumption(s[:60])
            arg_names.append(s[:60])

    # ── Step 2: Claims → derived nodes with justifications ───────────
    claim_names = []
    for i, c in enumerate(raw_claims[:4]):
        name = _text(c)
        atms.add_node(name)
        claim_names.append(name)
        # Derive claim from supporting arguments
        supporting = arg_names[: min(i + 2, len(arg_names))]
        if supporting:
            atms.add_justification(supporting, [], name)

    # ── Step 3: Fallacies → contradictions ───────────────────────────
    for i, f in enumerate(detected_fallacies[:4]):
        if not isinstance(f, dict):
            continue
        fallacy_type = f.get("type", f.get("fallacy_type", f"fallacy_{i+1}"))
        contra_name = f"CONTRA:{fallacy_type}"[:60]
        atms.add_node(contra_name)
        target_arg = (
            arg_names[i] if i < len(arg_names) else arg_names[0] if arg_names else None
        )
        if target_arg:
            atms.add_justification([target_arg], [], contra_name)
            # Mark as contradiction — the assumption leads to inconsistency
            atms.add_justification([contra_name], [], "\u22a5")  # ⊥

    # ── Step 4: Build result ─────────────────────────────────────────
    environments: Dict[str, Dict[str, Any]] = {}
    for name in arg_names + claim_names:
        if name in atms.nodes:
            envs = atms.get_environments(name)
            environments[name] = {
                "is_assumption": atms.nodes[name].is_assumption,
                "environments": [sorted(e) for e in envs],
                "env_count": len(envs),
            }

    assumptions = atms.get_assumptions()
    consistent_envs: list[Dict[str, Any]] = []
    for node_name, node_data in environments.items():
        if not node_data["is_assumption"]:
            for env in node_data["environments"]:
                if atms.is_consistent(frozenset(env)):
                    consistent_envs.append({"belief": node_name, "environment": env})

    # ── Step 5: Multi-context hypothesis testing (#349) ──────────────
    hypotheses = _generate_hypotheses(
        arg_names, claim_names, detected_fallacies, per_arg_scores
    )

    atms_contexts = []
    for hyp in hypotheses:
        hyp_assumptions = frozenset(hyp["assumptions"])
        is_consistent = atms.is_consistent(hyp_assumptions)

        derivable_beliefs = []
        for name, node in atms.nodes.items():
            if node.is_assumption or name == "⊥":
                continue
            for env in node.label:
                if env.issubset(hyp_assumptions):
                    derivable_beliefs.append(name)
                    break

        contradicting_beliefs = []
        for name, node in atms.nodes.items():
            if not name.startswith("CONTRA:"):
                continue
            for env in node.label:
                if env.issubset(hyp_assumptions):
                    contradicting_beliefs.append(name)
                    break

        atms_contexts.append(
            {
                "hypothesis_id": hyp["id"],
                "label": hyp["label"],
                "assumptions": sorted(hyp_assumptions),
                "coherent": is_consistent,
                "derivable_beliefs": sorted(set(derivable_beliefs)),
                "contradicting_beliefs": sorted(set(contradicting_beliefs)),
                "derivation_count": len(derivable_beliefs),
                "contradiction_count": len(contradicting_beliefs),
            }
        )

    return {
        "assumption_count": len(assumptions),
        "assumptions": assumptions,
        "node_count": len(atms.nodes) - 1,  # exclude ⊥
        "environments": environments,
        "consistent_derivations": consistent_envs,
        "has_contradictions": any(
            len(n.label) > 0 for name, n in atms.nodes.items() if name == "⊥"
        ),
        "atms_contexts": atms_contexts,
    }


def _generate_hypotheses(
    arg_names: List[str],
    claim_names: List[str],
    fallacies: List[Any],
    per_arg_scores: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate 3-4 testable hypotheses from analysis data for ATMS multi-context.

    Each hypothesis is a named set of assumptions representing a possible
    world. Hypotheses vary in which arguments they accept as true, producing
    contexts where some beliefs are coherent and others are not.
    """
    hypotheses = []

    # Hypothesis 1: Accept all arguments (full trust context)
    hypotheses.append(
        {
            "id": "h_full_trust",
            "label": "All arguments accepted",
            "assumptions": list(arg_names),
        }
    )

    # Hypothesis 2: Exclude arguments implicated in fallacies
    fallacy_targets = set()
    for f in fallacies[:6]:
        if isinstance(f, dict):
            target = f.get("target_argument", f.get("argument", ""))
            if target:
                fallacy_targets.add(str(target))
    # Match against arg_names truncated to the same length to avoid silently
    # missing fallacy-implicated arguments longer than the target string
    # (review #376).
    clean_args = [
        a
        for a in arg_names
        if not any(
            t and (a == t or a.startswith(t) or t.startswith(a))
            for t in fallacy_targets
        )
    ]
    if clean_args and set(clean_args) != set(arg_names):
        hypotheses.append(
            {
                "id": "h_fallacy_excluded",
                "label": "Arguments implicated in fallacies excluded",
                "assumptions": list(clean_args),
            }
        )
    elif len(arg_names) >= 2:
        hypotheses.append(
            {
                "id": "h_partial_accept",
                "label": "Partial acceptance (last argument excluded)",
                "assumptions": list(arg_names[:-1]),
            }
        )

    # Hypothesis 3: Only high-quality arguments (if quality data available)
    if per_arg_scores:
        high_quality = []
        for arg_name in arg_names:
            # Direct lookup first; fall back to exact-match against str(arg_id).
            # Avoid arg_name[:30] in str(arg_id) — it falsely matched unrelated
            # IDs like "counter_argument" / "target_argument" (review #376).
            scores = per_arg_scores.get(arg_name)
            if not isinstance(scores, dict):
                for arg_id, candidate in per_arg_scores.items():
                    if isinstance(candidate, dict) and str(arg_id) == arg_name:
                        scores = candidate
                        break
            if isinstance(scores, dict):
                if (
                    float(str(scores.get("overall", scores.get("note_finale", 0))))
                    >= 3.0
                ):
                    high_quality.append(arg_name)
        if high_quality and set(high_quality) != set(arg_names):
            hypotheses.append(
                {
                    "id": "h_high_quality",
                    "label": "Only high-quality arguments",
                    "assumptions": list(high_quality),
                }
            )

    # Hypothesis 4: Minimal set -- first argument only (skeptical context)
    if len(arg_names) >= 2:
        hypotheses.append(
            {
                "id": "h_skeptical",
                "label": "Skeptical: single argument only",
                "assumptions": [arg_names[0]],
            }
        )

    # Ensure at least 3 hypotheses
    if len(hypotheses) < 3 and len(arg_names) >= 3:
        mid = len(arg_names) // 2
        hypotheses.append(
            {
                "id": "h_first_half",
                "label": "First half of arguments",
                "assumptions": list(arg_names[:mid]),
            }
        )

    return hypotheses[:4]


async def _invoke_camembert_fallacy(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke self-hosted LLM fallacy detector via SK function calling (#297).

    Replaces the dead CamemBERT Tier 2.5 with a self-hosted LLM endpoint
    using the same FallacyWorkflowPlugin infrastructure (function calling
    for structured output). Falls back to symbolic-only if endpoint unavailable.
    """
    endpoint = os.environ.get("SELF_HOSTED_LLM_ENDPOINT", "")
    api_key = os.environ.get("SELF_HOSTED_LLM_API_KEY", "not-needed")
    model_id = os.environ.get("SELF_HOSTED_LLM_MODEL", "")

    if not endpoint or not model_id:
        return {
            "detected_fallacies": {},
            "arguments": {},
            "tiers_used": ["none"],
            "explanation": "Self-hosted LLM endpoint not configured",
            "total_fallacies": 0,
        }

    try:
        from openai import AsyncOpenAI
        from semantic_kernel.kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        async_client = AsyncOpenAI(api_key=api_key, base_url=endpoint)
        llm_service = OpenAIChatCompletion(
            ai_model_id=model_id,
            async_client=async_client,
        )
        master_kernel = Kernel()
        master_kernel.add_service(llm_service)

        plugin = FallacyWorkflowPlugin(
            master_kernel=master_kernel,
            llm_service=llm_service,
        )

        result_json = await plugin.run_guided_analysis(argument_text=input_text)
        result = json.loads(result_json)

        # Map hierarchical result to adapter format
        fallacies = result.get("fallacies", [])
        detected = {}
        for f in fallacies:
            if isinstance(f, dict):
                ftype = f.get("fallacy_type", f.get("fallacy_name", "unknown"))
                detected[ftype] = {
                    "source": "self_hosted_llm",
                    "confidence": f.get("confidence", 0.5),
                    "description": f.get("explanation", ""),
                    "taxonomy_pk": f.get("taxonomy_pk", ""),
                }

        return {
            "detected_fallacies": detected,
            "arguments": {},
            "tiers_used": ["self_hosted_llm"],
            "explanation": f"Self-hosted LLM ({model_id}): {len(detected)} fallacy(ies) detected",
            "total_fallacies": len(detected),
            "extraction_method": result.get("exploration_method", "self_hosted"),
        }

    except Exception as e:
        logger.warning("Self-hosted LLM fallacy detection failed: %s", e)
        return {
            "detected_fallacies": {},
            "arguments": {},
            "tiers_used": ["none"],
            "explanation": f"Self-hosted LLM unavailable: {e}",
            "total_fallacies": 0,
            "error": str(e),
        }


async def _invoke_local_llm(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke local LLM service for text analysis."""
    from argumentation_analysis.services.local_llm_service import LocalLLMService

    service = LocalLLMService()
    messages = [{"role": "user", "content": input_text}]
    return await service.chat_completion(messages)


async def _invoke_semantic_index(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke semantic index service for argument search."""
    from argumentation_analysis.services.semantic_index_service import (
        SemanticIndexService,
    )

    service = SemanticIndexService()
    results = await asyncio.to_thread(service.search, input_text)
    return {"results": results}


async def _invoke_speech_transcription(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
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

    Priority order:
    1. ``arguments`` list from extract/quality phases (LLM-extracted, best quality)
    2. ``claims`` list from extract phase (heuristic fallback, still real text)
    3. Sentence splitting from input_text (last resort before placeholder)
    """
    # Try various upstream phase outputs — check extract first (best source)
    for phase_key in [
        "phase_extract_output",
        "phase_quality_baseline_output",
        "phase_quality_output",
    ]:
        phase_out = context.get(phase_key, {})
        if isinstance(phase_out, dict):
            # Primary: explicit arguments list (from fact_extraction LLM)
            if "arguments" in phase_out:
                args = phase_out["arguments"]
                if isinstance(args, list) and args:
                    return [
                        a.get("text", str(a)) if isinstance(a, dict) else str(a)
                        for a in args
                    ]
            # Secondary: claims list (from fact_extraction heuristic fallback)
            if "claims" in phase_out:
                claims = phase_out["claims"]
                if isinstance(claims, list) and claims:
                    return [
                        c.get("text", str(c)) if isinstance(c, dict) else str(c)
                        for c in claims[:8]
                    ]
            # Tertiary: scores dict keyed by argument ID
            if "scores" in phase_out and isinstance(phase_out["scores"], dict):
                return list(phase_out["scores"].keys())

    # Fall back: use actual text sentences as argument content (not opaque labels)
    sentences = [
        s.strip()
        for s in input_text.replace("\n", ". ").split(".")
        if len(s.strip()) > 10
    ]
    if len(sentences) >= 2:
        # Use truncated real sentences so downstream consumers have meaningful content
        return [s[:120] for s in sentences[: min(len(sentences), 6)]]
    # Absolute fallback: use the input text itself as a single argument
    return [input_text[:200] if len(input_text) > 10 else "argument_placeholder"]


def _generate_attacks_from_args(
    arguments: List[str], context: Optional[Dict[str, Any]] = None
) -> List[List[str]]:
    """Generate attack relations between arguments based on detected fallacies.

    Uses upstream fallacy detections to create meaningful attacks:
    - A fallacy undermines the argument it targets
    - Counter-arguments attack the arguments they rebut
    Falls back to sparse heuristic if no upstream data available.
    """
    attacks = []

    if context:
        # Use fallacies to generate attacks: fallacious arg attacks its target
        fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
        fallacies = (
            fallacy_output.get("fallacies", [])
            if isinstance(fallacy_output, dict)
            else []
        )
        for i, f in enumerate(fallacies):
            if not isinstance(f, dict):
                continue
            fallacy_label = f.get("type", f.get("fallacy_type", f"fallacy_{i}"))
            # Try to match fallacy to argument by text content
            target_text = str(
                f.get("target_text", f.get("argument", f.get("text", "")))
            ).lower()[:60]
            target_arg = None
            # Strategy 1: exact text overlap between fallacy target and argument
            if target_text:
                best_overlap = 0
                for arg in arguments:
                    overlap = len(set(target_text.split()) & set(arg.lower().split()))
                    if overlap > best_overlap:
                        best_overlap = overlap
                        target_arg = arg
                # Require at least 2 words overlap for a meaningful match
                if best_overlap < 2:
                    target_arg = None
            # Strategy 2: index-based fallback
            if target_arg is None and arguments:
                target_idx = min(i, len(arguments) - 1)
                target_arg = arguments[target_idx]

            if target_arg:
                # The fallacious argument attacks the argument it undermines
                attacks.append([f"fallacy_{i}_{fallacy_label}", target_arg])

        # Use counter-arguments to generate attacks
        ca_output = context.get("phase_counter_output", {})
        if isinstance(ca_output, dict):
            cas = ca_output.get("llm_counter_arguments", [])
            if isinstance(cas, list):
                for ca in cas:
                    if not isinstance(ca, dict):
                        continue
                    target = ca.get("target_argument", "")
                    # Find the target argument in our list
                    for arg in arguments:
                        if target and target.lower()[:30] in arg.lower():
                            attacks.append(
                                [f"CA: {ca.get('counter_argument', '')[:50]}", arg]
                            )
                            break

    # Fallback: sparse heuristic if no meaningful attacks generated
    if not attacks:
        for i in range(len(arguments)):
            for j in range(i + 1, len(arguments)):
                if (i + j) % 3 == 0:
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
        "arguments": arguments,
        "ranking": [a for a, _ in sorted_args],
        "scores": {a: round(s, 4) for a, s in scores.items()},
        "comparisons": comparisons,
        "fallback": "python",
    }


def _enrich_ranking_with_justification(
    result: Dict[str, Any],
    args: List[str],
    attacks: List[List[str]],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Enrich ranking output with strength justification based on upstream data.

    Uses Dung extensions, quality scores, and fallacy data to explain
    WHY each argument is ranked where it is.
    """
    scores = result.get("scores", {})
    ranking = result.get("ranking", [])

    # Gather upstream quality scores
    quality_output = context.get("phase_quality_output", {})
    quality_scores = {}
    if isinstance(quality_output, dict):
        qs = quality_output.get("quality_scores", quality_output.get("scores", {}))
        if isinstance(qs, dict):
            quality_scores = qs

    # Gather fallacy targets
    fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
    fallacy_targets = set()
    if isinstance(fallacy_output, dict):
        for f in fallacy_output.get("fallacies", []):
            if isinstance(f, dict):
                target = f.get("target_argument", "")
                if target:
                    fallacy_targets.add(target.lower()[:30])

    # Build per-argument strength justification
    strength_analysis = []
    for rank_pos, arg in enumerate(ranking):
        arg_score = scores.get(arg, 0.0)
        # Count attacks on this argument
        incoming = sum(1 for src, tgt in attacks if tgt == arg)
        outgoing = sum(1 for src, tgt in attacks if src == arg)

        reasons = []
        if incoming == 0:
            reasons.append("unattacked (no incoming attacks)")
        elif incoming >= 2:
            reasons.append(f"heavily attacked ({incoming} incoming)")
        else:
            reasons.append(f"{incoming} incoming attack(s)")

        if outgoing > 0:
            reasons.append(f"attacks {outgoing} other argument(s)")

        # Check if targeted by fallacy
        is_fallacious = any(ft in arg.lower()[:30] for ft in fallacy_targets)
        if is_fallacious:
            reasons.append("targeted by detected fallacy (weakened)")

        # Check quality score
        arg_quality = quality_scores.get(arg)
        if isinstance(arg_quality, (int, float)):
            reasons.append(f"quality score: {arg_quality:.2f}")
        elif isinstance(arg_quality, dict) and "overall" in arg_quality:
            reasons.append(f"quality score: {arg_quality['overall']:.2f}")

        strength_analysis.append(
            {
                "rank": rank_pos + 1,
                "argument": arg[:80],
                "score": round(arg_score, 4),
                "reasons": reasons,
            }
        )

    result["strength_analysis"] = strength_analysis
    if not result.get("comparisons"):
        # Generate comparisons from ranking
        comparisons = []
        for i in range(len(ranking) - 1):
            s1 = scores.get(ranking[i], 0)
            s2 = scores.get(ranking[i + 1], 0)
            comparisons.append(
                {
                    "stronger": ranking[i][:60],
                    "weaker": ranking[i + 1][:60],
                    "score_diff": round(s1 - s2, 4),
                }
            )
        result["comparisons"] = comparisons
    return result


async def _invoke_ranking(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke ranking semantics handler with JVM fallback.

    Enriches ranking with Dung extension data and strength justification.
    """
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args, context)
    method = context.get("ranking_method", "categorizer")

    try:
        from argumentation_analysis.agents.core.logic.ranking_handler import (
            RankingHandler,
        )

        handler = RankingHandler()  # type: ignore[no-untyped-call]
        result = await asyncio.to_thread(handler.rank_arguments, args, attacks, method)
        # Enrich Tweety result with strength justification
        if isinstance(result, dict) and "ranking" in result:
            result = _enrich_ranking_with_justification(result, args, attacks, context)
        return result
    except Exception as e:
        logger.info(f"Ranking handler unavailable ({e}), using Python fallback")
        result = _python_ranking_fallback(args, attacks, method)
        return _enrich_ranking_with_justification(result, args, attacks, context)


async def _invoke_bipolar(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke bipolar argumentation handler with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args, context)
    supports = context.get("supports", [])
    fw_type = context.get("framework_type", "necessity")

    try:
        from argumentation_analysis.agents.core.logic.bipolar_handler import (
            BipolarHandler,
        )

        handler = BipolarHandler()  # type: ignore[no-untyped-call]
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


async def _invoke_aba(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke ABA handler with JVM fallback."""
    args = _extract_arguments_from_context(input_text, context)
    assumptions = context.get("assumptions") or args[:3]
    rules = context.get("rules") or [f"{a} => valid" for a in args[:2]]
    contraries = context.get("contraries")
    semantics = context.get("semantics", "preferred")

    try:
        from argumentation_analysis.agents.core.logic.aba_handler import ABAHandler

        handler = ABAHandler()  # type: ignore[no-untyped-call]
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


async def _invoke_adf(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke ADF handler with JVM fallback."""
    args = _extract_arguments_from_context(input_text, context)
    statements = context.get("statements") or args
    conditions = context.get("acceptance_conditions") or {
        a: "and(c(v))" for a in args[:3]
    }
    semantics = context.get("semantics", "grounded")

    try:
        from argumentation_analysis.agents.core.logic.adf_handler import ADFHandler

        handler = ADFHandler()  # type: ignore[no-untyped-call]
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


def _python_aspic_fallback(
    args: List[str],
    strict: List[str],
    defeasible: List[str],
    fallacies: List[Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Pure-Python ASPIC+ fallback that interprets defensibility.

    Determines which arguments survive based on whether they are undermined
    by detected fallacies or successfully rebutted by counter-arguments.
    """
    # Identify undermined arguments (targeted by fallacies)
    undermined_indices = set()
    for f in fallacies:
        if isinstance(f, dict):
            target = f.get("target_argument", "")
            for i, arg in enumerate(args):
                if target and target.lower()[:30] in arg.lower():
                    undermined_indices.add(i)
                    break
            else:
                # Fallacy without explicit target: assign to positional index
                idx = min(len(undermined_indices), len(args) - 1)
                if idx not in undermined_indices:
                    undermined_indices.add(idx)

    # Check counter-arguments for rebuttal
    ca_output = context.get("phase_counter_output", {})
    rebutted_indices = set()
    if isinstance(ca_output, dict):
        cas = ca_output.get("llm_counter_arguments", [])
        if isinstance(cas, list):
            for ca in cas:
                if not isinstance(ca, dict):
                    continue
                target = ca.get("target_argument", "")
                for i, arg in enumerate(args):
                    if target and target.lower()[:30] in arg.lower():
                        rebutted_indices.add(i)
                        break

    # Compute defensibility for each argument
    defensibility = []
    surviving = []
    defeated = []
    for i, arg in enumerate(args):
        is_undermined = i in undermined_indices
        is_rebutted = i in rebutted_indices
        has_strict_support = any(
            f"claim_{i+1}" in r or f"supported_{i+1}" in r for r in strict
        )
        status = "accepted"
        reasons = []
        if is_undermined:
            status = "undermined"
            matching_fallacies: list[str] = [
                str(f.get("type", f.get("fallacy_type", "unknown")))
                for f in fallacies
                if isinstance(f, dict)
            ]
            reasons.append(
                f"undermined by fallacy: {', '.join(matching_fallacies[:2])}"
            )
        if is_rebutted:
            status = "defeated" if is_undermined else "challenged"
            reasons.append("rebutted by counter-argument")
        if has_strict_support and not is_undermined:
            status = "strictly_supported"
            reasons.append("backed by strict rule (factual claim)")

        defensibility.append(
            {
                "argument": arg[:80],
                "status": status,
                "reasons": reasons or ["no attack detected"],
            }
        )
        if status in ("accepted", "strictly_supported"):
            surviving.append(arg[:80])
        else:
            defeated.append(arg[:80])

    return {
        "strict_rules": strict,
        "defeasible_rules": defeasible,
        "extensions": [surviving] if surviving else [args[:1]],
        "defensibility_analysis": defensibility,
        "surviving_arguments": surviving,
        "defeated_arguments": defeated,
        "statistics": {
            "total_arguments": len(args),
            "surviving": len(surviving),
            "defeated": len(defeated),
            "strict_rules": len(strict),
            "defeasible_rules": len(defeasible),
            "fallacies_applied": len(fallacies),
        },
        "fallback": "python",
    }


async def _invoke_aspic(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke ASPIC+ handler with JVM fallback.

    Generates meaningful strict and defeasible rules from the argument structure:
    - Strict rules: factual claims support conclusions
    - Defeasible rules: arguments that may be undermined by fallacies
    """
    args = _extract_arguments_from_context(input_text, context)

    # Build meaningful rules from upstream data
    fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
    fallacies = (
        fallacy_output.get("fallacies", []) if isinstance(fallacy_output, dict) else []
    )

    strict = context.get("strict_rules")
    if not strict:
        strict = []
        # Strict rules: factual claims that are uncontested
        extract_output = context.get("phase_extract_output", {})
        claims = (
            extract_output.get("claims", []) if isinstance(extract_output, dict) else []
        )
        for i, claim in enumerate(claims[:4]):
            text = (
                claim.get("text", str(claim)) if isinstance(claim, dict) else str(claim)
            )
            strict.append(f"claim_{i+1}({text[:40]}) -> supported_{i+1}")
        # If claims feed into arguments
        if len(args) >= 2:
            strict.append(f"supported_1, supported_2 -> argument_chain")

    defeasible = context.get("defeasible_rules")
    if not defeasible:
        defeasible = []
        # Defeasible rules: arguments that could be undermined
        for i, arg in enumerate(args[:4]):
            defeasible.append(f"{arg[:40]} => plausible_conclusion_{i+1}")
        # Fallacy-based defeat: if a fallacy targets an argument, it's defeasible
        for j, f in enumerate(fallacies[:3]):
            if isinstance(f, dict):
                ft = str(f.get("type", f.get("fallacy_type", "unknown")))
                defeasible.append(f"detected({ft[:30]}) => undermined_{j+1}")

    axioms = context.get("axioms")

    try:
        from argumentation_analysis.agents.core.logic.aspic_handler import ASPICHandler

        handler = ASPICHandler()  # type: ignore[no-untyped-call]
        return await asyncio.to_thread(
            handler.analyze_aspic_framework, strict, defeasible, axioms
        )
    except Exception as e:
        logger.info(f"ASPIC+ handler unavailable ({e}), using Python fallback")
        return _python_aspic_fallback(args, strict, defeasible, fallacies, context)


async def _invoke_belief_revision(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke belief revision — revise beliefs based on counter-arguments and fallacies.

    Uses upstream counter-arguments or fallacy detections as new evidence that
    forces actual revision of the original belief set.
    """
    args = _extract_arguments_from_context(input_text, context)
    beliefs = context.get("belief_set") or args
    method = context.get("revision_method", "dalal")

    # Derive new_belief from upstream counter-arguments or fallacies (not from args!)
    new_belief = context.get("new_belief")
    if not new_belief:
        # Try counter-argument output
        ca_output = context.get("phase_counter_output", {})
        if isinstance(ca_output, dict):
            llm_ca = ca_output.get("llm_counter_argument", {})
            if isinstance(llm_ca, dict) and llm_ca.get("counter_argument"):
                new_belief = f"NOT({llm_ca.get('target_argument', 'unknown')[:60]})"

        # Try fallacy output — a detected fallacy undermines a belief
        if not new_belief:
            fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
            if isinstance(fallacy_output, dict):
                fallacies = fallacy_output.get("fallacies", [])
                if fallacies and isinstance(fallacies[0], dict):
                    ft = fallacies[0].get("type", fallacies[0].get("fallacy_type", ""))
                    new_belief = (
                        f"Fallacy detected: {ft} — undermines argument credibility"
                    )

        # Last resort: generate a revision-triggering belief
        if not new_belief:
            new_belief = "New evidence contradicts one of the original claims"

    try:
        from argumentation_analysis.agents.core.logic.belief_revision_handler import (
            BeliefRevisionHandler,
        )

        handler = BeliefRevisionHandler()  # type: ignore[no-untyped-call]
        return await asyncio.to_thread(handler.revise, beliefs, new_belief, method)
    except Exception as e:
        logger.info(f"Belief revision handler unavailable ({e}), using Python fallback")
        # Real revision: add new belief, remove the belief it contradicts
        revised = list(beliefs)
        removed = []

        # If new_belief negates an existing belief, remove the negated one
        if new_belief.startswith("NOT("):
            target = new_belief[4:].rstrip(")")
            for b in beliefs:
                if target.lower() in b.lower():
                    revised.remove(b)
                    removed.append(b)
                    break

        if new_belief not in revised:
            revised.append(new_belief)

        return {
            "method": method,
            "original": list(beliefs),
            "new_belief": new_belief,
            "revised": revised,
            "removed": removed,
            "revision_triggered": new_belief != beliefs[-1] if beliefs else True,
            "fallback": "python",
        }


async def _invoke_probabilistic(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke probabilistic argumentation handler with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args, context)
    probs = context.get("probabilities") or {a: 0.5 for a in args}

    try:
        from argumentation_analysis.agents.core.logic.probabilistic_handler import (
            ProbabilisticHandler,
        )

        handler = ProbabilisticHandler()  # type: ignore[no-untyped-call]
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


async def _invoke_dialogue(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke dialogue protocol handler with JVM fallback.

    Organizes arguments into proponent/opponent positions using upstream data:
    - Counter-arguments become opponent moves
    - Original arguments become proponent moves
    """
    args = _extract_arguments_from_context(input_text, context)

    # Use counter-arguments as opponent position if available
    ca_output = context.get("phase_counter_output", {})
    ca_list = []
    if isinstance(ca_output, dict):
        cas = ca_output.get("llm_counter_arguments", [])
        if isinstance(cas, list):
            ca_list = [
                ca.get("counter_argument", "")[:100]
                for ca in cas
                if isinstance(ca, dict) and ca.get("counter_argument")
            ]

    if ca_list:
        pro_args = context.get("proponent_args") or args
        opp_args = context.get("opponent_args") or ca_list
    else:
        mid = max(1, len(args) // 2)
        pro_args = context.get("proponent_args") or args[:mid]
        opp_args = context.get("opponent_args") or args[mid:]
    pro_attacks = context.get("proponent_attacks") or _generate_attacks_from_args(
        pro_args, context
    )
    opp_attacks = context.get("opponent_attacks") or _generate_attacks_from_args(
        opp_args, context
    )
    topic = context.get("topic", input_text[:200])

    try:
        from argumentation_analysis.agents.core.logic.dialogue_handler import (
            DialogueHandler,
        )

        handler = DialogueHandler()  # type: ignore[no-untyped-call]
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
        # Build substantive dialogue using fallacies as attack moves
        extract_output = context.get("phase_extract_output", {})
        raw_fallacies = extract_output.get("fallacies", [])

        # Enrich opponent moves with fallacy-based attacks
        fallacy_attacks = []
        for f in raw_fallacies[:5]:
            if isinstance(f, dict):
                ftype = f.get("type", f.get("fallacy_type", "unknown"))
                justification = f.get("justification", "")
                fallacy_attacks.append(f"[CHALLENGE: {ftype}] {justification[:120]}")

        trace = []
        turn = 1
        for i, arg in enumerate(pro_args):
            trace.append(
                {
                    "turn": turn,
                    "speaker": "proponent",
                    "move_type": "assert",
                    "move": arg,
                }
            )
            turn += 1
            # Opponent responds with CA if available, fallacy attack, or counter-arg
            if i < len(opp_args):
                trace.append(
                    {
                        "turn": turn,
                        "speaker": "opponent",
                        "move_type": "counter",
                        "move": opp_args[i],
                    }
                )
                turn += 1
            if i < len(fallacy_attacks):
                trace.append(
                    {
                        "turn": turn,
                        "speaker": "opponent",
                        "move_type": "challenge",
                        "move": fallacy_attacks[i],
                    }
                )
                turn += 1

        # Determine winner based on move balance
        pro_moves = sum(1 for t in trace if t["speaker"] == "proponent")
        opp_moves = sum(1 for t in trace if t["speaker"] == "opponent")
        winner = (
            "proponent"
            if pro_moves > opp_moves
            else ("opponent" if opp_moves > pro_moves else "draw")
        )

        return {
            "topic": topic[:100],
            "proponent_args": pro_args,
            "opponent_args": opp_args,
            "fallacy_attacks": fallacy_attacks,
            "dialogue_trace": trace,
            "outcome": winner,
            "turns": len(trace),
            "fallback": "python",
        }


async def _invoke_dl(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Description Logic handler (#86) with JVM fallback."""
    tbox = context.get("tbox", [])
    abox_concepts = context.get("abox_concepts", [])
    abox_roles = context.get("abox_roles", [])

    try:
        from argumentation_analysis.agents.core.logic.dl_handler import DLHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
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


async def _invoke_cl(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Conditional Logic handler (#86) with JVM fallback."""
    conditionals = context.get("conditionals", [])
    query_conclusion = context.get("query_conclusion")
    query_premise = context.get("query_premise")

    try:
        from argumentation_analysis.agents.core.logic.cl_handler import CLHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
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


async def _invoke_sat(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
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


async def _invoke_setaf(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
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

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
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


async def _invoke_weighted(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
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

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
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


async def _invoke_social(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Social AF handler (#87) with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args, context)
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

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
        handler = SocialHandler(initializer)
        return await asyncio.to_thread(
            handler.analyze_social_framework, args, attacks, votes
        )
    except Exception as e:
        logger.info(f"Social handler unavailable ({e}), using Python fallback")
        return _python_social_fallback(args, attacks, votes, context)


def _python_social_fallback(
    args: List[str],
    attacks: List[List[str]],
    votes: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Pure-Python Social AF fallback using upstream data as social votes.

    Derives social acceptability from:
    - Governance decisions (if available): voting results as social preference
    - Quality scores: higher quality = more social support
    - Counter-argument effectiveness: arguments that survive CAs are socially stronger
    """
    # Derive votes from upstream governance if available
    gov_output = context.get("phase_governance_output", {})
    if isinstance(gov_output, dict) and not votes:
        decisions = gov_output.get("governance_decisions", [])
        if isinstance(decisions, list):
            for d in decisions:
                if isinstance(d, dict) and "scores" in d:
                    for arg_id, score in d["scores"].items():
                        if isinstance(score, (int, float)):
                            votes[arg_id] = (score, 1.0 - score)

    # Derive social scores from quality scores and attack resilience
    quality_output = context.get("phase_quality_output", {})
    quality_scores = {}
    if isinstance(quality_output, dict):
        qs = quality_output.get("quality_scores", quality_output.get("scores", {}))
        if isinstance(qs, dict):
            quality_scores = qs

    # Compute social scores combining multiple signals
    social_scores = {}
    for i, arg in enumerate(args):
        base_score = 0.5
        # Signal 1: votes (if available)
        if arg in votes:
            v = votes[arg]
            base_score = (
                v[0] / (v[0] + v[1]) if isinstance(v, tuple) and sum(v) > 0 else 0.5
            )
        # Signal 2: quality score boost
        q = quality_scores.get(arg)
        quality_boost = 0.0
        if isinstance(q, (int, float)):
            quality_boost = q * 0.3  # quality contributes 30%
        elif isinstance(q, dict) and "overall" in q:
            quality_boost = q["overall"] * 0.3
        # Signal 3: attack resilience (fewer incoming attacks = stronger)
        incoming = sum(1 for src, tgt in attacks if tgt == arg)
        resilience = 1.0 / (1.0 + incoming) * 0.2  # resilience contributes 20%

        social_scores[arg] = round(base_score + quality_boost + resilience, 4)

    sorted_args = sorted(social_scores, key=lambda a: -social_scores[a])

    return {
        "arguments": args,
        "attacks": attacks,
        "votes": votes,
        "social_ranking": sorted_args,
        "social_scores": social_scores,
        "social_analysis": [
            {
                "argument": arg[:80],
                "social_score": social_scores.get(arg, 0),
                "rank": rank + 1,
            }
            for rank, arg in enumerate(sorted_args)
        ],
        "fallback": "python",
    }


def _python_eaf_fallback(
    args: List[str],
    attacks: List[List[str]],
    semantics: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Pure-Python Epistemic AF fallback using upstream data for belief states.

    Computes epistemic confidence for each argument based on:
    - Whether it was identified as fallacious (lower confidence)
    - Quality scores (higher quality = higher confidence)
    - Whether it survived counter-arguments (higher confidence)
    - Whether it has strict support (ASPIC+)
    """
    # Gather fallacy data
    fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
    fallacy_targets = {}
    if isinstance(fallacy_output, dict):
        for f in fallacy_output.get("fallacies", []):
            if isinstance(f, dict):
                target = f.get("target_argument", "")
                ftype = f.get("type", f.get("fallacy_type", "unknown"))
                if target:
                    fallacy_targets[target.lower()[:30]] = ftype

    # Gather quality scores
    quality_output = context.get("phase_quality_output", {})
    quality_scores = {}
    if isinstance(quality_output, dict):
        qs = quality_output.get("quality_scores", quality_output.get("scores", {}))
        if isinstance(qs, dict):
            quality_scores = qs

    # Gather ASPIC defensibility
    aspic_output = context.get("phase_aspic_output", {})
    surviving = set()
    if isinstance(aspic_output, dict):
        for a in aspic_output.get("surviving_arguments", []):
            surviving.add(str(a).lower()[:30])

    # Compute epistemic states
    epistemic: Dict[str, Dict[str, Any]] = {}
    believed_args: list[str] = []
    disbelieved_args: list[str] = []
    for arg in args:
        confidence = 0.6  # base confidence
        believed = True
        reasons = []

        # Check fallacy targeting
        is_fallacious = any(ft in arg.lower()[:30] for ft in fallacy_targets)
        if is_fallacious:
            confidence -= 0.3
            reasons.append("targeted by fallacy")

        # Check quality score
        q = quality_scores.get(arg)
        if isinstance(q, (int, float)):
            confidence += (q - 0.5) * 0.4  # quality shifts confidence
            reasons.append(f"quality={q:.2f}")
        elif isinstance(q, dict) and "overall" in q:
            confidence += (q["overall"] - 0.5) * 0.4
            reasons.append(f"quality={q['overall']:.2f}")

        # Check ASPIC survival
        if arg.lower()[:30] in surviving:
            confidence += 0.15
            reasons.append("survives ASPIC+ analysis")

        # Check attack count
        incoming = sum(1 for src, tgt in attacks if tgt == arg)
        if incoming >= 2:
            confidence -= 0.15
            reasons.append(f"heavily attacked ({incoming}x)")

        confidence = max(0.0, min(1.0, confidence))
        believed = confidence >= 0.4

        epistemic[arg] = {
            "believed": believed,
            "confidence": round(confidence, 3),
            "reasons": reasons or ["no specific evidence"],
        }
        if believed:
            believed_args.append(arg)
        else:
            disbelieved_args.append(arg)

    # Compute extensions based on epistemic states
    extensions = [believed_args] if believed_args else [args[:1]]

    return {
        "arguments": args,
        "attacks": attacks,
        "semantics": semantics,
        "epistemic_states": epistemic,
        "extensions": extensions,
        "believed_arguments": believed_args,
        "disbelieved_arguments": disbelieved_args,
        "epistemic_summary": {
            "total": len(args),
            "believed": len(believed_args),
            "disbelieved": len(disbelieved_args),
            "avg_confidence": round(
                sum(e["confidence"] for e in epistemic.values())
                / max(len(epistemic), 1),
                3,
            ),
        },
        "fallback": "python",
    }


# --- EAF / DeLP / QBF invoke functions (#88, #89, #90) ---


async def _invoke_eaf(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Epistemic AF handler (#88) with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args, context)
    beliefs = context.get("epistemic_beliefs")
    semantics = context.get("semantics", "grounded")

    try:
        from argumentation_analysis.agents.core.logic.eaf_handler import EAFHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
        handler = EAFHandler(initializer)
        return await asyncio.to_thread(
            handler.analyze_epistemic_framework, args, attacks, beliefs, semantics
        )
    except Exception as e:
        logger.info(f"EAF handler unavailable ({e}), using Python fallback")
        return _python_eaf_fallback(args, attacks, semantics, context)


async def _invoke_delp(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke DeLP handler (#89) with JVM fallback."""
    program_text = context.get("program", input_text[:500])
    queries = context.get("queries", [])
    criterion = context.get("criterion", "generalized_specificity")

    try:
        from argumentation_analysis.agents.core.logic.delp_handler import DeLPHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
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


async def _invoke_qbf(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke QBF handler (#90) with JVM fallback."""
    quantifiers = context.get("quantifiers", [])
    formula = context.get("formula", input_text[:200])

    try:
        from argumentation_analysis.agents.core.logic.qbf_handler import QBFHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
        handler = QBFHandler(initializer)
        return await asyncio.to_thread(handler.analyze_qbf, quantifiers, formula)
    except Exception as e:
        logger.info(f"QBF JVM handler unavailable ({e}), using native Python fallback")
        try:
            from argumentation_analysis.agents.core.logic.qbf_native import analyze_qbf

            return await asyncio.to_thread(analyze_qbf, quantifiers, formula)
        except Exception as e2:
            logger.warning(f"QBF native fallback also failed: {e2}")
            return {
                "quantifiers": quantifiers,
                "formula": formula[:100],
                "valid": False,
                "message": f"QBF unavailable: {e2}",
                "fallback": "error",
            }


async def _invoke_asp_reasoning(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke Clingo ASP solver for Answer Set Programming (#479).

    Uses Tweety's ClingoSolver when JVM+Clingo are available.
    Falls back to Python clingo package or pure-Python heuristic.
    """
    program = context.get("program", input_text)
    max_models = context.get("max_models", 0)  # 0 = all models

    # Try JVM + Tweety ClingoSolver first
    try:
        from argumentation_analysis.core.jvm_setup import is_jvm_started
        if is_jvm_started():
            import jpype
            JString = jpype.JClass("java.lang.String")
            ClingoSolver = jpype.JClass(
                "org.tweetyproject.lp.asp.reasoner.ClingoSolver"
            )
            Program = jpype.JClass(
                "org.tweetyproject.lp.asp.syntax.Program"
            )
            ASPRule = jpype.JClass(
                "org.tweetyproject.lp.asp.syntax.ASPRule"
            )
            ASPAtom = jpype.JClass(
                "org.tweetyproject.lp.asp.syntax.ASPAtom"
            )

            # Parse simple rules: "a :- b." format
            rules = []
            for line in str(program).strip().splitlines():
                line = line.strip().rstrip(".")
                if not line or line.startswith("%"):
                    continue
                if ":-" in line:
                    head, body = line.split(":-", 1)
                    head_atoms = [ASPAtom(h.strip()) for h in head.split(",") if h.strip()]
                    body_atoms = [ASPAtom(b.strip()) for b in body.split(",") if b.strip()]
                    rule = ASPRule()
                    for a in head_atoms:
                        rule.getHead().add(a)
                    for a in body_atoms:
                        rule.getBody().add(a)  # type: ignore[attr-defined]
                    rules.append(rule)
                else:
                    rules.append(ASPRule([ASPAtom(line)], []))

            prog = Program()
            for r in rules:
                prog.add(r)

            solver = ClingoSolver()
            answer_sets = solver.getModels(prog, max_models)

            models = []
            for i in range(answer_sets.size()):
                aset = answer_sets.get(i)
                atoms = []
                for j in range(aset.size()):
                    atoms.append(str(aset.get(j)))
                models.append(atoms)

            return {
                "answer_sets": models,
                "num_models": len(models),
                "solver": "clingo_jvm",
                "program": str(program)[:500],
            }
    except Exception as e:
        logger.info(f"Clingo JVM solver unavailable ({e}), trying Python fallback")

    # Try Python clingo package
    try:
        import clingo as clingo_py  # type: ignore[import-untyped]

        models = []
        ctl = clingo_py.Control(arguments=[f"--models={max_models}" if max_models else "--models=0"])
        ctl.add("base", [], str(program))
        ctl.ground([("base", [])])

        def on_model(model):
            models.append([str(s) for s in model.symbols(shown=True)])

        ctl.solve(on_model=on_model)
        return {
            "answer_sets": models,
            "num_models": len(models),
            "solver": "clingo_python",
            "program": str(program)[:500],
        }
    except ImportError:
        logger.debug("Python clingo package not available")
    except Exception as e:
        logger.info(f"Clingo Python solve failed ({e})")

    # Pure Python heuristic fallback
    logger.warning("ASP reasoning: Clingo unavailable, using heuristic fallback")
    lines = str(program).strip().splitlines()
    rules = [l.strip().rstrip(".") for l in lines if ":-" in l and not l.strip().startswith("%")]
    facts = [l.strip().rstrip(".") for l in lines if ":-" not in l and l.strip() and not l.strip().startswith("%")]

    return {
        "answer_sets": [facts] if facts else [],
        "num_models": 1 if facts else 0,
        "solver": "heuristic",
        "program": str(program)[:500],
        "rules_parsed": len(rules),
        "facts_parsed": len(facts),
        "fallback": "python_heuristic",
    }


# --- Hierarchical taxonomy-guided fallacy detection (#84) ---


async def _invoke_hierarchical_fallacy(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke hierarchical taxonomy-guided fallacy detection.

    Uses FallacyWorkflowPlugin with iterative deepening (master-slave kernel)
    and one-shot fallback. Requires a Semantic Kernel service + taxonomy CSV.
    Falls back to heuristic extraction if SK/API is unavailable.
    """
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
        return result  # type: ignore[no-any-return]

    except (ImportError, RuntimeError) as e:
        # Expected failures: missing dependencies or API key — return empty gracefully
        logger.warning("Hierarchical fallacy detection unavailable: %s", e)
        return {
            "fallacies": [],
            "exploration_method": "unavailable",
            "error": str(e),
            "extraction_method": "unavailable",
        }
    except Exception as e:
        # Unexpected failures: log full traceback and re-raise so the executor
        # marks this phase as FAILED instead of silently returning empty results.
        # This makes debugging possible when the phase produces 0 fallacies.
        import traceback

        logger.error(
            "Hierarchical fallacy detection failed with unexpected error:\n%s",
            traceback.format_exc(),
        )
        raise


# --- Invoke callables for logic agent capabilities (#71 Formal Verification) ---


def _normalize_items_with_quotes(items: list[Any]) -> list[Dict[str, Any]]:
    """Normalize argument/claim items: accept both str and dict with source_quote."""
    result = []
    for item in items:
        if isinstance(item, str):
            result.append({"text": item, "source_quote": ""})
        elif isinstance(item, dict):
            result.append(
                {
                    "text": str(item.get("text", item.get("content", ""))),
                    "source_quote": str(item.get("source_quote", "")),
                }
            )
    return result


def _normalize_fallacies_with_quotes(items: list[Any]) -> list[Dict[str, Any]]:
    """Normalize fallacy items to include source_quote."""
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(
                {
                    "type": str(item.get("type", "unknown")),
                    "justification": str(item.get("justification", "")),
                    "source_quote": str(item.get("source_quote", "")),
                }
            )
        elif isinstance(item, str):
            result.append({"type": item, "justification": "", "source_quote": ""})
    return result


async def _invoke_fact_extraction(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract verifiable claims and arguments from text using LLM with heuristic fallback."""
    import re

    # Try LLM-based extraction first
    try:
        client, model_id = _get_openai_client()

        if client:
            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert argument analyst. Extract the key arguments "
                            "and verifiable claims from the text. "
                            "For each argument and claim, include the exact quote from the "
                            "source text that supports it (verbatim, max 150 chars). "
                            "Do NOT detect fallacies — that is handled by a separate specialist. "
                            "Focus on: (1) identifying distinct argumentative positions, "
                            "(2) extracting factual claims that can be verified, "
                            "(3) noting rhetorical strategies used (without labeling them as fallacies). "
                            "Respond with ONLY a JSON object:\n"
                            '{"arguments": [{"text": "arg description", "source_quote": "exact quote..."}], '
                            '"claims": [{"text": "claim description", "source_quote": "exact quote..."}], '
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
                # Normalize arguments/claims: accept both str and dict formats
                raw_args = data.get("arguments", [])
                raw_claims = data.get("claims", [])
                raw_fallacies = data.get("fallacies", [])
                arguments = _normalize_items_with_quotes(raw_args)
                claims = _normalize_items_with_quotes(raw_claims)
                fallacies = _normalize_fallacies_with_quotes(raw_fallacies)
                return {
                    "arguments": arguments,
                    "claims": claims,
                    "fallacies": fallacies,
                    "summary": data.get("summary", ""),
                    "claim_count": len(claims),
                    "argument_count": len(arguments),
                    "source_length": len(input_text),
                    "extraction_method": "llm",
                }
    except Exception as e:
        logger.warning(f"LLM fact extraction failed, falling back to heuristic: {e}")

    # Heuristic fallback
    sentences = re.split(r"(?<=[.!?])\s+", input_text.strip())
    claims = [s.strip() for s in sentences if len(s.strip()) > 20]  # type: ignore[misc]
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


async def _invoke_propositional_logic(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke propositional logic analysis — translate arguments to propositions.

    If NL-to-logic translations are available from an upstream phase, uses
    those validated formulas. Otherwise falls back to template generation.
    (#208-H: wire NL-to-logic as pre-processing)
    """
    # Build propositional formulas from upstream arguments
    args = _extract_arguments_from_context(input_text, context)
    formulas = context.get("formulas")
    argument_mapping = {}

    if not formulas:
        # (#208-H) Check if NL-to-logic phase already produced PL translations
        nl_output = context.get("phase_nl_to_logic_output", {})
        nl_translations = (
            nl_output.get("translations", []) if isinstance(nl_output, dict) else []
        )
        pl_translations = [
            t
            for t in nl_translations
            if isinstance(t, dict)
            and t.get("logic_type") == "propositional"
            and t.get("is_valid")
        ]

        if pl_translations:
            # Use validated NL-to-logic formulas
            formulas = [t["formula"] for t in pl_translations]
            argument_mapping = {
                t["formula"][:30]: t.get("original_text", "")[:60]
                for t in pl_translations
            }
            logger.info(
                f"Using {len(formulas)} NL-to-logic PL translations "
                f"(from upstream phase)"
            )
        else:
            # Fallback: try on-the-fly NL translation if LLM available
            try:
                from argumentation_analysis.services.nl_to_logic import (
                    NLToLogicTranslator,
                )

                translator = NLToLogicTranslator(
                    max_retries=2, logic_type="propositional"
                )
                batch = await translator.translate_batch(
                    args[:4], logic_type="propositional", check_consistency=False
                )
                valid = [t for t in batch.translations if t.is_valid]
                if valid:
                    formulas = [t.formula for t in valid]
                    argument_mapping = {
                        t.formula[:30]: t.original_text[:60] for t in valid
                    }
                    logger.info(
                        f"NL-to-logic translated {len(valid)}/{len(args)} "
                        f"arguments to PL"
                    )
            except Exception as e:
                logger.debug(f"NL-to-logic PL translation unavailable: {e}")

        if not formulas:
            # Final fallback: template-based variables
            prop_vars = [f"p{i+1}" for i in range(len(args))]
            formulas = list(prop_vars)
            argument_mapping = {f"p{i+1}": a[:60] for i, a in enumerate(args)}
            fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
            fallacies = (
                fallacy_output.get("fallacies", [])
                if isinstance(fallacy_output, dict)
                else []
            )
            if fallacies and len(prop_vars) >= 2:
                formulas.append(f"!{prop_vars[-1]}")

    if not isinstance(formulas, list):
        formulas = [str(formulas)]

    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge()
        belief_set_str = "\n".join(str(f) for f in formulas)
        is_consistent, msg = await asyncio.to_thread(
            bridge.check_consistency, belief_set_str, "propositional"
        )
        return {
            "formulas": formulas,
            "satisfiable": bool(is_consistent),
            "model": {f"p{i+1}": True for i in range(len(args))},
            "message": msg,
            "logic_type": "propositional",
            "argument_mapping": argument_mapping
            or {f"p{i+1}": a[:60] for i, a in enumerate(args)},
        }
    except Exception as e:
        # Fallback: basic consistency check
        has_contradiction = any(f.startswith("!") for f in formulas) and any(
            f == f2.lstrip("!")
            for f in formulas
            for f2 in formulas
            if f2.startswith("!")
        )
        return {
            "formulas": formulas,
            "satisfiable": not has_contradiction,
            "model": {f"p{i+1}": True for i in range(len(args))},
            "logic_type": "propositional",
            "argument_mapping": argument_mapping
            or {f"p{i+1}": a[:60] for i, a in enumerate(args)},
            "fallback": "python",
        }


async def _invoke_fol_reasoning(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke first-order logic analysis — translate arguments to FOL predicates.

    If NL-to-logic translations are available from an upstream phase, uses
    those validated formulas. Otherwise falls back to template generation.
    (#208-H: wire NL-to-logic as pre-processing)
    """
    args = _extract_arguments_from_context(input_text, context)
    formulas = context.get("formulas")
    if not formulas:
        # (#208-H) Check if NL-to-logic phase already produced FOL translations
        nl_output = context.get("phase_nl_to_logic_output", {})
        nl_translations = (
            nl_output.get("translations", []) if isinstance(nl_output, dict) else []
        )
        fol_translations = [
            t
            for t in nl_translations
            if isinstance(t, dict)
            and t.get("logic_type") == "fol"
            and t.get("is_valid")
        ]

        if fol_translations:
            formulas = []
            for t in fol_translations:
                # FOL formulas may be semicolon-separated
                for f in t["formula"].split(";"):
                    f = f.strip()
                    if f:
                        formulas.append(f)
            logger.info(
                f"Using {len(formulas)} NL-to-logic FOL translations "
                f"(from upstream phase)"
            )
        else:
            # Fallback: try on-the-fly NL translation
            try:
                from argumentation_analysis.services.nl_to_logic import (
                    NLToLogicTranslator,
                )

                translator = NLToLogicTranslator(max_retries=2, logic_type="fol")
                batch = await translator.translate_batch(
                    args[:4], logic_type="fol", check_consistency=False
                )
                valid = [t for t in batch.translations if t.is_valid]
                if valid:
                    formulas = []
                    for t in valid:  # type: ignore[assignment]
                        for f in t.formula.split(";"):  # type: ignore[attr-defined]
                            f = f.strip()
                            if f:
                                formulas.append(f)
                    logger.info(
                        f"NL-to-logic translated {len(valid)}/{len(args)} "
                        f"arguments to FOL"
                    )
            except Exception as e:
                logger.debug(f"NL-to-logic FOL translation unavailable: {e}")

        if not formulas:
            # Final fallback: template-based FOL predicates
            formulas = []
            for i in range(len(args)):
                formulas.append(f"Asserted(arg{i+1})")
            fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
            fallacies = (
                fallacy_output.get("fallacies", [])
                if isinstance(fallacy_output, dict)
                else []
            )
            for j, f in enumerate(fallacies):
                if isinstance(f, dict):
                    target_idx = min(j, len(args) - 1) if args else 0
                    formulas.append(f"Undermines(fallacy{j+1}, arg{target_idx+1})")
                    formulas.append(f"Fallacious(arg{target_idx+1})")
            if fallacies:
                formulas.append("forall X: (Fallacious(X) -> !FullySupported(X))")

    if not isinstance(formulas, list):
        formulas = [str(formulas)]

    # External solver routing (#479): EProver or Prover9 for FOL
    fol_solver = context.get("fol_solver", "tweety")  # tweety, eprover, prover9
    if fol_solver in ("eprover", "prover9"):
        try:
            from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler

            handler = FOLHandler()
            belief_set_str = "\n".join(str(f) for f in formulas)
            if fol_solver == "eprover":
                is_consistent, msg = await asyncio.to_thread(
                    handler._fol_check_consistency_with_eprover, belief_set_str
                )
            else:
                is_consistent, msg = await asyncio.to_thread(
                    handler._fol_check_consistency_with_prover9, belief_set_str
                )
            return {
                "formulas": formulas,
                "consistent": bool(is_consistent),
                "inferences": inferences,
                "confidence": 0.85 if is_consistent else 0.4,
                "message": msg,
                "logic_type": "first_order",
                "argument_count": len(args),
                "solver": fol_solver,
            }
        except Exception as e:
            logger.info(
                f"External solver '{fol_solver}' unavailable ({e}), "
                f"falling back to Tweety"
            )

    inferences = []
    # Derive inferences from the structure
    fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
    fallacies = (
        fallacy_output.get("fallacies", []) if isinstance(fallacy_output, dict) else []
    )
    for f in fallacies:
        if isinstance(f, dict):
            inferences.append(
                f"Argument undermined by {f.get('type', f.get('fallacy_type', 'unknown'))} fallacy"
            )

    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        bridge = TweetyBridge()
        # Pre-declare signature (sorts + types) for Tweety FolParser (#348)
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        fol_signature = meta.get("signature_lines", [])
        belief_set_str = "\n".join(str(f) for f in fol_signature + [""] + formulas)
        is_consistent, msg = await asyncio.to_thread(
            bridge.check_consistency, belief_set_str, "first_order"
        )
        return {
            "formulas": formulas,
            "fol_signature": fol_signature,
            "fol_metadata": meta,
            "consistent": bool(is_consistent),
            "inferences": inferences,
            "confidence": 0.8 if is_consistent else 0.4,
            "message": msg,
            "logic_type": "first_order",
            "argument_count": len(args),
        }
    except Exception as tweety_err:
        logger.warning(
            f"FOL Tweety parse failed ({tweety_err}). "
            f"Attempting per-formula isolation with {len(formulas)} formulas."
        )
        # Retry: isolate valid formulas by parsing each individually.
        # This handles the case where one bad formula causes the entire
        # batch to fail in Tweety's parser.
        valid_formulas = []
        for formula in formulas:
            try:
                single_meta = FOLLogicAgent.extract_fol_metadata([formula])
                single_sig = single_meta.get("signature_lines", [])
                single_bs = "\n".join(str(f) for f in single_sig + [""] + [formula])
                await asyncio.to_thread(
                    bridge.check_consistency, single_bs, "first_order"
                )
                valid_formulas.append(formula)
            except Exception:
                logger.debug(f"FOL formula rejected by Tweety: {formula}")

        if valid_formulas:
            meta = FOLLogicAgent.extract_fol_metadata(valid_formulas)
            fol_signature = meta.get("signature_lines", [])
            logger.info(
                f"FOL per-formula isolation: {len(valid_formulas)}/{len(formulas)} "
                f"formulas accepted by Tweety"
            )
            return {
                "formulas": valid_formulas,
                "fol_signature": fol_signature,
                "fol_metadata": meta,
                "consistent": True,
                "inferences": inferences,
                "confidence": 0.6,
                "logic_type": "first_order",
                "argument_count": len(args),
                "isolation_retry": True,
                "rejected_count": len(formulas) - len(valid_formulas),
            }

        # All formulas failed — use Python fallback
        has_fallacious = any("Fallacious" in f for f in formulas)
        fol_signature = []
        try:
            meta = FOLLogicAgent.extract_fol_metadata(formulas)
            fol_signature = meta.get("signature_lines", [])
        except Exception:
            pass
        return {
            "formulas": formulas,
            "fol_signature": fol_signature,
            "consistent": not has_fallacious,
            "inferences": inferences,
            "confidence": 0.6 if not has_fallacious else 0.3,
            "logic_type": "first_order",
            "argument_count": len(args),
            "fallback": "python",
            "diagnostic": str(tweety_err),
        }


async def _invoke_nl_to_logic(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Translate extracted NL arguments to formal logic with validation (#173).

    Uses LLM to generate propositional/FOL formulas, validates via Tweety
    (or Python fallback), and retries on failure with error feedback.
    Bridges the gap between informal LLM analysis and formal reasoning.
    """
    from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

    args = _extract_arguments_from_context(input_text, context)
    logic_type = context.get("logic_type", "propositional")

    translator = NLToLogicTranslator(max_retries=3, logic_type=logic_type)
    batch_result = await translator.translate_batch(
        args[:6], logic_type=logic_type, check_consistency=True
    )

    translations = []
    for t in batch_result.translations:
        translations.append(
            {
                "original_text": t.original_text[:200],
                "formula": t.formula,
                "logic_type": t.logic_type,
                "is_valid": t.is_valid,
                "validation_message": t.validation_message,
                "attempts": t.attempts,
                "variables": t.variables,
                "confidence": t.confidence,
            }
        )

    valid_count = sum(1 for t in translations if t["is_valid"])
    return {
        "translations": translations,
        "total": len(translations),
        "valid_count": valid_count,
        "overall_consistency": batch_result.overall_consistency,
        "consistency_message": batch_result.consistency_message,
        "method": batch_result.method,
        "logic_type": logic_type,
    }


async def _invoke_modal_logic(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke modal logic analysis via TweetyBridge or external SPASS solver.

    Routes to SPASS when context["modal_solver"] == "spass" (#479).
    Falls back to TweetyBridge or pure-Python heuristic.
    """
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
    modalities = list(set(modalities)) or ["none_detected"]

    modal_solver = context.get("modal_solver", "tweety")  # tweety, spass

    # SPASS routing (#479)
    if modal_solver == "spass":
        try:
            from argumentation_analysis.agents.core.logic.modal_handler import (
                ModalHandler,
                ModalSolverChoice,
            )

            handler = ModalHandler(modal_solver=ModalSolverChoice.SPASS)
            belief_set_str = "\n".join(str(f) for f in formulas)
            logic_type = context.get("modal_logic_type", "K")
            is_consistent, msg = await asyncio.to_thread(
                handler._modal_check_consistency_with_spass, belief_set_str, logic_type
            )
            return {
                "formulas": formulas,
                "valid": bool(is_consistent),
                "modalities": modalities,
                "logic_type": "modal",
                "solver": "spass",
                "message": msg,
            }
        except Exception as e:
            logger.info(
                f"SPASS modal solver unavailable ({e}), falling back to Tweety"
            )

    # TweetyBridge routing
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge()
        belief_set_str = "\n".join(str(f) for f in formulas)
        logic_type = context.get("modal_logic_type", "K")
        accepted, msg = await asyncio.to_thread(
            bridge.execute_modal_query, belief_set_str, belief_set_str, logic_type=logic_type
        )
        return {
            "formulas": formulas,
            "valid": accepted,
            "modalities": modalities,
            "logic_type": "modal",
            "solver": "tweety",
            "message": msg,
        }
    except Exception as e:
        logger.debug(f"Modal TweetyBridge unavailable ({e}), using heuristic")

    # Pure heuristic fallback
    return {
        "formulas": formulas,
        "valid": True,
        "modalities": modalities,
        "logic_type": "modal",
        "solver": "heuristic",
        "fallback": "python",
    }


async def _invoke_dung_extensions(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke Dung framework extension computation via AFHandler (JVM required).

    Builds attack graph from extracted arguments and detected fallacies,
    then computes all 11 Dung semantics via Tweety: grounded, preferred,
    stable, complete, admissible, conflict_free, semi_stable, stage, cf2,
    ideal, naive.
    Falls back to pure-Python computation when JVM is unavailable.
    """
    # 1. Extract arguments from upstream phases
    arguments = _extract_arguments_from_context(input_text, context)

    # 2. Build attack relations from fallacies and counter-arguments
    attacks = _generate_attacks_from_args(arguments, context)

    # 3. Compute extensions via Tweety (or Python fallback)
    try:
        from argumentation_analysis.agents.core.logic.af_handler import (
            AFHandler,
            SEMANTICS_REASONERS,
        )
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
        handler = AFHandler(initializer)

        # Compute all 11 semantics in one pass (framework built once)
        all_semantics = list(SEMANTICS_REASONERS.keys())
        result = await asyncio.to_thread(
            handler.analyze_multi_semantics, arguments, attacks, all_semantics
        )

        raw_extensions = result.get("extensions", {})

        # Enrich: for each semantics, add sizes and argument membership
        enriched_extensions = {}
        for sem, ext_data in raw_extensions.items():
            if isinstance(ext_data, dict) and "error" in ext_data:
                enriched_extensions[sem] = ext_data
                continue
            extensions_list = ext_data if isinstance(ext_data, list) else []
            enriched_extensions[sem] = {
                "extensions": extensions_list,
                "count": len(extensions_list),
                "sizes": [len(ext) for ext in extensions_list],
                "all_members": sorted({arg for ext in extensions_list for arg in ext}),
            }

        # Use preferred as primary, fallback to grounded
        primary = enriched_extensions.get(
            "preferred", enriched_extensions.get("grounded", {})
        )

        return {
            "semantics": "multi",
            "extensions": primary,
            "all_extensions": enriched_extensions,
            "arguments": arguments,
            "attacks": attacks,
            "statistics": {
                "arguments_count": len(arguments),
                "attacks_count": len(attacks),
                "semantics_computed": len(
                    [v for v in enriched_extensions.values() if "count" in v]
                ),
            },
        }
    except Exception as e:
        logger.info(f"Dung AFHandler unavailable ({e}), using Python fallback")
        return _python_dung_fallback(arguments, attacks)


def _python_dung_fallback(
    arguments: List[str], attacks: List[List[str]]
) -> Dict[str, Any]:
    """Pure-Python Dung extension computation when JVM/Tweety is unavailable.

    Computes grounded extension using iterative fixpoint: start from empty set,
    repeatedly add arguments that are defended against all attacks.
    """
    if not arguments:
        return {
            "semantics": "python_fallback",
            "extensions": {},
            "arguments": [],
            "attacks": [],
            "statistics": {"arguments_count": 0, "attacks_count": 0},
        }

    # Build attack maps
    arg_set = set(arguments)
    attack_map: Dict[str, list[str]] = {a: [] for a in arg_set}  # attacker -> targets
    attacked_by: Dict[str, list[str]] = {a: [] for a in arg_set}  # target -> attackers
    for attacker, target in attacks:
        if attacker in arg_set and target in arg_set:
            attack_map[attacker].append(target)
            attacked_by[target].append(attacker)

    # Grounded extension: iterative fixpoint
    grounded: set[str] = set()
    changed = True
    while changed:
        changed = False
        for arg in arg_set:
            if arg in grounded:
                continue
            # arg is defended if all its attackers are attacked by grounded
            defended = all(
                any(att in attack_map.get(g, []) for g in grounded)
                for att in attacked_by[arg]
            )
            if defended and all(att not in grounded for att in attack_map.get(arg, [])):
                # Also check: arg doesn't attack itself (conflict-free)
                grounded.add(arg)
                changed = True

    extensions = {}
    if grounded:
        extensions["grounded"] = list(grounded)

    return {
        "semantics": "python_fallback",
        "extensions": extensions,
        "arguments": arguments,
        "attacks": attacks,
        "statistics": {
            "arguments_count": len(arguments),
            "attacks_count": len(attacks),
        },
    }


async def _invoke_formal_synthesis(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
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


async def _invoke_narrative_synthesis(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke narrative synthesis to produce readable prose from all phase outputs (#351).

    Reads state from context (populated by prior phases) and calls
    build_narrative to generate 1-2 paragraphs weaving together quality,
    fallacies, JTMS, ATMS, Dung, and formal logic results.
    """
    from argumentation_analysis.plugins.narrative_synthesis_plugin import (
        build_narrative,
    )
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.state_writers import (
        CAPABILITY_STATE_WRITERS,
    )

    # Reconstruct state from context if possible
    state = context.get("_state_object")
    if not isinstance(state, UnifiedAnalysisState):
        state = UnifiedAnalysisState(input_text[:200])
        # Populate from context outputs
        for key, value in context.items():
            if key.startswith("phase_") and key.endswith("_output"):
                cap = key[len("phase_") : -len("_output")]
                writer = CAPABILITY_STATE_WRITERS.get(cap)
                if writer and isinstance(value, dict):
                    try:
                        writer(value, state, context)
                    except Exception:
                        logger.warning(
                            "State writer for '%s' failed during narrative reconstruction",
                            cap,
                            exc_info=True,
                        )

    narrative = build_narrative(state)
    paragraph_count = (narrative.count("\n\n") + 1) if narrative else 0

    return {
        "narrative": narrative,
        "paragraph_count": paragraph_count,
        "referenced_fields": _count_referenced_fields(state),
    }


def _count_referenced_fields(state: Any) -> int:
    """Count how many state fields have data (used as references in narrative)."""
    count = 0
    for field_name in [
        "argument_quality_scores",
        "identified_fallacies",
        "neural_fallacy_scores",
        "counter_arguments",
        "jtms_beliefs",
        "jtms_retraction_chain",
        "atms_contexts",
        "dung_frameworks",
        "fol_analysis_results",
        "propositional_analysis_results",
        "modal_analysis_results",
    ]:
        val = getattr(state, field_name, None)
        if val and (isinstance(val, (list, dict)) and len(val) > 0):
            count += 1
    return count


# --- State writers: map capability → (output, state, ctx) → None ---
# Each writer extracts relevant data from phase output and writes to
# UnifiedAnalysisState via its typed add_*() methods.
# Writers are defensive: guard with isinstance checks and .get() everywhere.
