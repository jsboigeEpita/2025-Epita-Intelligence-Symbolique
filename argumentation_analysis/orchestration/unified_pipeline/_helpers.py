"""Shared helpers for unified_pipeline sub-package."""
import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

# Ensure .env is loaded so OPENAI_API_KEY is available for all invoke callables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional in CI environments

logger = logging.getLogger("UnifiedPipeline")

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

def _aggregate_virtue_scores(per_arg_results: Dict) -> Dict[str, float]:
    """Average virtue scores across all evaluated arguments."""
    all_virtues: Dict[str, list] = {}
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

def _evaluate_counter_arguments(
    llm_counters: List[Dict], input_text: str
) -> List[Dict]:
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

    evaluator = CounterArgumentEvaluator()
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
            # The fallacy undermines an argument — find closest match
            target_idx = min(i, len(arguments) - 1) if arguments else -1
            if target_idx >= 0 and target_idx < len(arguments):
                # "fallacy detection" attacks the argument it exposes
                fallacy_label = f.get("type", f.get("fallacy_type", f"fallacy_{i}"))
                if fallacy_label in arguments:
                    attacks.append([fallacy_label, arguments[target_idx]])
                elif len(arguments) > target_idx + 1:
                    # Adjacent arguments with different positions attack each other
                    attacks.append([arguments[target_idx], arguments[target_idx + 1]])

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


def _normalize_items_with_quotes(items: list) -> list:
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


def _normalize_fallacies_with_quotes(items: list) -> list:
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

def _should_rerun_fallacy(context: Dict[str, Any]) -> bool:
    """Check whether the fallacy detection phase should be re-run after JTMS.

    Returns True when JTMS retracted beliefs AND we haven't exceeded the
    maximum number of fallacy reruns (2). This prevents infinite loops while
    allowing iterative enrichment when formal analysis invalidates beliefs.

    Args:
        context: Workflow execution context containing phase outputs.

    Returns:
        True if a fallacy re-run is warranted.
    """
    # Check rerun count limit
    rerun_count = context.get("_fallacy_rerun_count", 0)
    if rerun_count >= 2:
        return False

    # Check if JTMS phase produced retracted beliefs
    jtms_output = context.get("phase_jtms_output", {})
    if not isinstance(jtms_output, dict):
        return False

    # Method 1: explicit undermined_count field
    undermined = jtms_output.get("undermined_count", 0)
    if undermined > 0:
        return True

    # Method 2: scan beliefs dict for invalid entries
    beliefs = jtms_output.get("beliefs", {})
    if isinstance(beliefs, dict):
        retracted = [name for name, bdata in beliefs.items()
                     if isinstance(bdata, dict) and bdata.get("valid") is False]
        if retracted:
            return True

    return False


def _increment_fallacy_rerun(context: Dict[str, Any]) -> None:
    """Increment the fallacy rerun counter in context."""
    context["_fallacy_rerun_count"] = context.get("_fallacy_rerun_count", 0) + 1
