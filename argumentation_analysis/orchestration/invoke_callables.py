"""Invoke callables for the unified pipeline.

Each _invoke_* function implements a single pipeline capability.
They are registered in the CapabilityRegistry by setup_registry().

Split from unified_pipeline.py (#310).
"""

import asyncio
import contextvars
import shutil
import json
import logging
import os
import re
from contextlib import contextmanager
from typing import Dict, Any, Iterator, Optional, List, Tuple

logger = logging.getLogger("UnifiedPipeline")

# #1019: Preflight solver availability check (module-level, runs once)
_SOLVER_PREFLIGHT_CHECKED = False


def _preflight_solver_check() -> None:
    """Log a one-time WARNING if external theorem provers are absent."""
    global _SOLVER_PREFLIGHT_CHECKED
    if _SOLVER_PREFLIGHT_CHECKED:
        return
    _SOLVER_PREFLIGHT_CHECKED = True
    missing = []
    if shutil.which("eprover") is None:
        missing.append("eprover (FOL)")
    if shutil.which("SPASS") is None:
        missing.append("SPASS (modal)")
    if missing:
        logger.warning(
            "External solvers not found on PATH: %s. "
            "Pipeline will use TweetyBridge (JVM) for FOL/modal reasoning. "
            "Install solvers for optimal performance.",
            ", ".join(missing),
        )


# ---------------------------------------------------------------------------
# RA-4 #1049 item 3 — Strategic objective consumption by tactical callables
# ---------------------------------------------------------------------------


def _get_strategic_directives(context: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Extract active strategic objectives from state and format as NL directives.

    Returns:
        Tuple of (formatted_directives_text, list_of_objective_ids).
        The text is empty string if no objectives are available.
    """
    state = context.get("_state_object")
    if state is None:
        return "", []

    objectives = getattr(state, "strategic_objectives", [])
    if not objectives:
        return "", []

    active = [
        obj
        for obj in objectives
        if isinstance(obj, dict)
        and obj.get("status", "active") in ("active", "in_progress")
    ]
    if not active:
        return "", []

    lines = []
    obj_ids: List[str] = []
    for obj in active[:5]:  # Cap at 5 to avoid prompt bloat
        oid = obj.get("objective_id", obj.get("id", f"obj_{len(obj_ids)+1}"))
        desc = obj.get("description", obj.get("text", ""))
        priority = obj.get("priority", "normal")
        if desc:
            lines.append(f"[{oid}] (priority: {priority}) {desc}")
            obj_ids.append(str(oid))

    if not lines:
        return "", []

    header = "STRATEGIC DIRECTIVES — the PM has identified these long-term analysis goals. Prioritize detection and analysis aligned with these objectives:"
    return f"{header}\n" + "\n".join(lines), obj_ids


# Ensure .env is loaded so OPENAI_API_KEY is available for all invoke callables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Export all underscore-prefixed functions for star-import in unified_pipeline facade
__all__ = [
    "_get_openai_client",
    "_guarded_chat_completion",
    "llm_budget_scope",
    "LLMBudgetExceeded",
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
    "_invoke_hierarchical_fallacy_per_argument",
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
    "_invoke_text_to_kb",
    "_invoke_kb_to_tweety",
    "_invoke_tweety_interpretation",
    "_invoke_analysis_synthesis",
    "_invoke_external_fol_solver",
    "_invoke_external_modal_solver",
    "_invoke_deep_synthesis",
    "_invoke_stakes_extractor",
    "_invoke_ai_shield",
]


_REASONING_MODEL_PREFIXES: Tuple[str, ...] = (
    "gpt-5",
    "o1",
    "o3",
    "openai/gpt-5",
    "openai/o1",
    "openai/o3",
)


def _resolve_model_id() -> str:
    """Resolve the active chat model id from environment (mirrors _get_openai_client)."""
    openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_base_url and openrouter_api_key:
        return os.environ.get(
            "OPENROUTER_CHAT_MODEL_ID",
            os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini"),
        )
    return os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")


def _is_reasoning_model(model_id: str) -> bool:
    """Return True if *model_id* belongs to a known reasoning-model family."""
    lower = model_id.lower()
    return any(lower.startswith(p) for p in _REASONING_MODEL_PREFIXES)


def _get_determinism_params() -> Dict[str, Any]:
    """Read determinism settings from environment variables.

    Supports two modes:
    - LLM_DETERMINISTIC_MODE=1: shorthand for temperature=0, seed=42
    - LLM_TEMPERATURE / LLM_SEED: fine-grained overrides (take precedence)

    When the active chat model is a known reasoning model (gpt-5*, o1*, o3*),
    temperature/seed are suppressed unless ``LLM_FORCE_SAMPLING_PARAMS=1`` is set,
    because reasoning models typically reject those parameters with a 400 BadRequest.

    Returns a dict suitable for merging into ``client.chat.completions.create()``.
    """
    params: Dict[str, Any] = {}
    if os.environ.get("LLM_DETERMINISTIC_MODE"):
        params["temperature"] = 0.0
        params["seed"] = 42
    temp_str = os.environ.get("LLM_TEMPERATURE")
    if temp_str is not None:
        try:
            params["temperature"] = float(temp_str)
        except ValueError:
            pass
    seed_str = os.environ.get("LLM_SEED")
    if seed_str is not None:
        try:
            params["seed"] = int(seed_str)
        except ValueError:
            pass

    if params and _is_reasoning_model(_resolve_model_id()):
        if os.environ.get("LLM_FORCE_SAMPLING_PARAMS"):
            logger.warning(
                "Determinism params forced on reasoning model '%s' — may 400.",
                _resolve_model_id(),
            )
        else:
            logger.warning(
                "Determinism requested but reasoning model '%s' does not support "
                "temperature/seed — params suppressed. Set LLM_FORCE_SAMPLING_PARAMS=1 "
                "to override.",
                _resolve_model_id(),
            )
            params = {}

    return params


def _get_openai_client() -> Tuple[Any, str]:
    """Create an AsyncOpenAI client + model id from environment variables.

    Honors the OpenRouter toggle (mirrors create_llm_service): if
    OPENROUTER_BASE_URL + OPENROUTER_API_KEY are set, the client targets
    OpenRouter (OpenAI-compatible) with the provider-prefixed
    OPENROUTER_CHAT_MODEL_ID; otherwise the official OpenAI endpoint is used.
    This routes every raw-SDK caller through the same provider, so they no
    longer hit OpenAI's quota when OpenRouter is configured.

    Returns (client, model_id) or (None, "") if no API key is available.
    """
    openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_base_url and openrouter_api_key:
        api_key = openrouter_api_key
        base_url = openrouter_base_url
        model_id = os.environ.get(
            "OPENROUTER_CHAT_MODEL_ID",
            os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini"),
        )
    else:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

    if not api_key:
        return None, ""
    try:
        from openai import AsyncOpenAI

        return AsyncOpenAI(api_key=api_key, base_url=base_url), model_id
    except ImportError:
        return None, ""


# --- Global per-run LLM-call circuit breaker (issue #708, Track LL-bis) ---
#
# A single analysis run funnels EVERY LLM chat-completion through
# ``_guarded_chat_completion``, which counts the call against a per-run budget.
# This is the only backstop that covers *every* phase: the counter-argument
# chain (``_extract_arguments_from_context`` → ``_invoke_counter_argument`` →
# ``_generate_counters_for_targets``) is otherwise uncapped and scales with the
# upstream argument count, which is what produced the 8h / ~12,417-call DAG
# runaway. Anti-pendulum: the ceiling is generous-but-finite (a healthy
# ``spectacular`` run is ~60-100 calls), so it never bites a real run but stops
# a runaway dead. It does NOT re-introduce a small per-phase cap (that would
# undo the GG #696 volume win).


class LLMBudgetExceeded(RuntimeError):
    """Raised when one analysis run exceeds its global LLM-call ceiling (#708).

    Caught per-phase by the workflow executor / each ``_invoke_*`` try/except,
    so it degrades a runaway into a graceful fallback rather than propagating.
    """


class _LLMBudget:
    """Mutable per-run LLM-call counter shared across phase sub-tasks.

    Stored in a ``ContextVar`` set once at the start of a run. asyncio copies
    the *context* (the var binding) into every child task spawned via
    ``asyncio.gather`` / ``asyncio.wait_for``, but the bound object is shared by
    reference — so incrementing ``count`` from any phase task aggregates into one
    global per-run total. (A plain int in a ContextVar would NOT aggregate,
    because each task gets its own binding.)
    """

    __slots__ = ("count", "ceiling")

    def __init__(self, ceiling: int) -> None:
        self.count = 0
        self.ceiling = ceiling


def _default_llm_call_budget() -> int:
    """Generous per-run LLM-call ceiling (override via ``LLM_CALL_BUDGET``).

    Healthy ``spectacular`` run ~60-100 calls; the default 500 never bites a
    healthy run but stops a 12K-call runaway.
    """
    try:
        return max(1, int(os.environ.get("LLM_CALL_BUDGET", "500")))
    except (TypeError, ValueError):
        return 500


_llm_budget: "contextvars.ContextVar[Optional[_LLMBudget]]" = contextvars.ContextVar(
    "llm_call_budget", default=None
)


@contextmanager
def llm_budget_scope(ceiling: Optional[int] = None) -> Iterator["_LLMBudget"]:
    """Activate a per-run LLM-call circuit breaker for the duration of the block.

    Every ``_guarded_chat_completion`` call made within (including in child
    asyncio tasks) counts against one shared ceiling; exceeding it raises
    ``LLMBudgetExceeded``. Re-entrant: a nested scope reuses the already-active
    budget so the count stays global across the whole run.
    """
    existing = _llm_budget.get()
    if existing is not None:
        # Already inside a budget scope — keep one global count, don't reset it.
        yield existing
        return
    budget = _LLMBudget(ceiling if ceiling is not None else _default_llm_call_budget())
    token = _llm_budget.set(budget)
    try:
        yield budget
    finally:
        _llm_budget.reset(token)


def _bump_sk_budget(n: int = 1) -> None:
    """Increment the LLM budget counter for SK-native agent calls (#1029).

    SK's ``AgentGroupChat.invoke()`` and ``ChatCompletionAgent.invoke()``
    call the OpenAI API directly, bypassing ``_guarded_chat_completion``.
    This helper closes that gap by manually incrementing the shared
    ``_LLMBudget`` counter (stored in a ``ContextVar``), so that the
    ceiling check fires even for SK-native calls.

    No-op when no budget scope is active (e.g. unit tests, standalone calls).
    """
    budget = _llm_budget.get()
    if budget is not None:
        budget.count += n
        if budget.count > budget.ceiling:
            raise LLMBudgetExceeded(
                f"Global LLM-call budget exceeded "
                f"({budget.count} > {budget.ceiling}) "
                f"— runaway guard (issue #708)."
            )


# Defense-in-depth (#730-bis): hard per-call wall-clock cap so a single stalled
# network round-trip cannot hang an entire analysis run. Observed live: the
# conversational-spectacular path hung ~50 min on one unbounded call. Generous
# default (300s) — far above a legitimate reasoning-model call (<2 min) but well
# below a pathological hang. Set LLM_CALL_TIMEOUT_S=0 to disable.
def _safe_float_env(key: str, default: float) -> float:
    """Read a float from an env var, falling back to *default* on bad input."""
    try:
        return float(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


_LLM_CALL_TIMEOUT_S = _safe_float_env("LLM_CALL_TIMEOUT_S", 300.0)

# Dung extension computation timeout (seconds). Preferred/stable semantics on
# large attack graphs can hang indefinitely.  On timeout, falls back to
# pure-Python grounded-only computation with degraded=True.  Set
# DUNG_TIMEOUT_S=0 to disable timeout (not recommended).
_DUNG_TIMEOUT_S = _safe_float_env("DUNG_TIMEOUT_S", 180.0)


async def _guarded_chat_completion(client: Any, **kwargs: Any) -> Any:
    """Single funnel for every LLM chat-completion call (#708 runaway guard).

    Increments the active per-run budget (if any) and raises
    ``LLMBudgetExceeded`` past the ceiling *before* issuing the network call, so
    a degenerate upstream (e.g. a large argument list feeding the uncapped
    counter sweep) cannot run away into thousands of round-trips. Inert when no
    budget scope is active, so a direct unit-test call of a single callable is
    unaffected.

    Each call is also bounded by ``_LLM_CALL_TIMEOUT_S`` (#730-bis): on a stalled
    round-trip an ``asyncio.TimeoutError`` propagates and is handled by the
    callers' existing ``except`` blocks (batch dropped / coverage retry) instead
    of hanging the whole run.
    """
    budget = _llm_budget.get()
    if budget is not None:
        budget.count += 1
        if budget.count > budget.ceiling:
            raise LLMBudgetExceeded(
                f"Global LLM-call budget exceeded "
                f"({budget.count} > {budget.ceiling}) in a single analysis run "
                f"— runaway guard (issue #708)."
            )
    if _LLM_CALL_TIMEOUT_S > 0:
        return await asyncio.wait_for(
            client.chat.completions.create(**kwargs),
            timeout=_LLM_CALL_TIMEOUT_S,
        )
    return await client.chat.completions.create(**kwargs)


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
            # Trace entry for quality evaluation specialist
            _state = context.get("_state_object")
            if _state is not None and output.get("per_argument_scores"):
                _n_eval = output.get("arguments_evaluated", 0)
                _avg_q = output.get("aggregate_score", 0.0)
                _state.add_trace_entry(
                    phase="quality",
                    agent="QualityScorer",
                    reacts_to=["extract", "hierarchical_fallacy"],
                    summary=f"Évaluation qualité de {_n_eval} arguments — score moyen: {_avg_q:.1f}/10. Détection par vertus rhétoriques.",
                )
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

        det_params = _get_determinism_params()
        response = await _guarded_chat_completion(
            client,
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
            **det_params,
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


def _parse_counter_array(raw: str) -> List[Dict[str, Any]]:
    """Extract a JSON array of counter-argument dicts from an LLM response."""
    text_content = (raw or "").strip()
    if "```json" in text_content:
        text_content = text_content.split("```json")[1].split("```")[0]
    elif "```" in text_content:
        text_content = text_content.split("```")[1].split("```")[0]
    start_arr = text_content.find("[")
    end_arr = text_content.rfind("]") + 1
    if start_arr >= 0 and end_arr > start_arr:
        try:
            parsed = json.loads(text_content[start_arr:end_arr])
            if isinstance(parsed, list):
                return [c for c in parsed if isinstance(c, dict)]
        except Exception:
            pass
    start = text_content.find("{")
    end = text_content.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            obj = json.loads(text_content[start:end])
            if isinstance(obj, dict):
                return [obj]
        except Exception:
            pass
    return []


async def _generate_counters_for_targets(
    client: Any,
    model_id: str,
    targets: List[str],
    batch_size: int = 12,
    k_per_target: int = 1,
) -> List[Dict[str, Any]]:
    """Generate ``k_per_target`` counter-arguments per target via the LLM.

    GG #696 introduced one-CA-per-target sweep; GG-bis #709 added retry on thin
    batches. Track YY #730 observed that ``args_count + 1`` total CAs (the floor
    of one-per-arg + retry overflow) under-shoots zero-shot baselines on smaller
    corpora — on corpus_C with 12 args, the CONV path produced 13 CAs vs 18 from
    the zero-shot reference. Defaulting ``k_per_target=2`` and asking the LLM to
    use DIFFERENT rhetorical strategies per CA brings the CONV volume above the
    zero-shot baseline on every observed corpus without raising ``batch_size``
    (no mega-prompt drop-off) or relaxing the per-target coverage guarantee.
    """
    counters: List[Dict[str, Any]] = []
    det_params = _get_determinism_params()
    k = max(1, int(k_per_target))
    if k == 1:
        prompt_count_clause = (
            "Return EXACTLY one counter-argument per listed item, "
            "using the most appropriate strategy."
        )
    else:
        prompt_count_clause = (
            f"For EACH listed item, generate {k} DISTINCT counter-arguments "
            f"using DIFFERENT strategies "
            f"(reductio ad absurdum, counter-example, distinction, "
            f"reformulation, concession+pivot — pick {k} different ones). "
            f"Total = {k} × (number of items). Each CA must target the same "
            f"item but via a different rhetorical move."
        )
    system_prompt = (
        "You are an expert in argumentation and counter-argument generation. "
        + prompt_count_clause
        + " Respond with ONLY a JSON array:\n"
        '[{"counter_argument": "text", "strategy_used": "name", '
        '"target_argument": "which argument", "strength": "weak|moderate|strong", '
        '"reasoning": "why this works"}, ...]'
    )
    for start in range(0, len(targets), batch_size):
        batch = targets[start : start + batch_size]
        targets_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(batch))
        expected = k * len(batch)
        try:
            response = await _guarded_chat_completion(
                client,
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": targets_text},
                ],
                **det_params,
            )
            raw = response.choices[0].message.content or ""
            parsed = _parse_counter_array(raw)
            counters.extend(parsed)
            # GG-bis #709: retry once if the batch returned fewer CAs than the
            # k-per-target floor (k * batch_len). #730 raises the threshold to
            # the k floor instead of the one-per-target floor.
            if parsed and len(parsed) < expected:
                logger.info(
                    f"Counter-argument batch [{start}:{start + batch_size}] "
                    f"thin ({len(parsed)}/{expected} with k={k}), retrying"
                )
                try:
                    retry = await _guarded_chat_completion(
                        client,
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": targets_text},
                        ],
                        **det_params,
                    )
                    retry_raw = retry.choices[0].message.content or ""
                    retry_parsed = _parse_counter_array(retry_raw)
                    counters.extend(retry_parsed)
                except Exception as retry_err:
                    logger.warning(f"Counter-argument retry failed: {retry_err}")
        except Exception as e:
            logger.warning(
                f"Counter-argument batch [{start}:{start + batch_size}] failed: {e}"
            )
    return counters


async def _generate_counter_arguments_from_state(state: Any) -> Dict[str, Any]:
    """Ensure >=k counter-arguments per identified argument (GG #696 + YY #730).

    The conversational path under-produces counter-arguments (the agent emits a
    handful before its turn budget runs out), so the collaborative path loses to
    the zero-shot baseline on volume. This deterministic post-processor mirrors
    the Dung/modal/ASPIC post-processors: after the dialogue, it sweeps every
    identified argument and generates targeted counter-arguments, written back
    via ``state.add_counter_argument``.

    YY #730: defaults to ``k_per_target=2`` so total CA = ``2 × args`` beats the
    zero-shot baseline on the observed A/B/C corpora (max 0-shot=18, min
    args=12 ⇒ 24 ≥ 18+marge). If the state exposes ``zero_shot_reference``,
    calibrate k dynamically with a +1 safety margin.
    """
    args = getattr(state, "identified_arguments", []) or []
    targets: List[str] = []
    for a in args:
        if isinstance(a, dict):
            text = a.get("text") or a.get("description") or a.get("content") or ""
        else:
            text = str(a)
        text = str(text).strip()
        if text:
            targets.append(text)
    if not targets:
        return {"added": 0, "targets": 0}

    client, model_id = _get_openai_client()
    if not client:
        return {"added": 0, "targets": len(targets)}

    # YY #730: calibrate k_per_target. Default k=2 covers the observed corpora
    # without raising batch_size. If the state exposes a zero-shot reference,
    # bump k just enough to clear it with a +1 safety margin.
    k_per_target = 2
    zs_ref = getattr(state, "zero_shot_reference", None)
    if isinstance(zs_ref, dict):
        zs_ca = zs_ref.get("counter_arguments", 0) or 0
        try:
            zs_ca_int = int(zs_ca)
            target_total = max(2 * len(targets), zs_ca_int + 1)
            k_per_target = max(2, -(-target_total // len(targets)))  # ceil div
        except (TypeError, ValueError):
            pass

    counters = await _generate_counters_for_targets(
        client, model_id, targets, k_per_target=k_per_target
    )

    added = 0
    for ca in counters:
        if not isinstance(ca, dict):
            continue
        content = ca.get("counter_argument", "")
        if not content:
            continue
        score = float(ca.get("evaluation_score", ca.get("score", 0.0)) or 0.0)
        try:
            state.add_counter_argument(
                original_arg=str(ca.get("target_argument", ""))[:300],
                counter_content=str(content),
                strategy=str(ca.get("strategy_used", "")),
                score=score,
            )
            added += 1
        except Exception as e:
            logger.debug(f"add_counter_argument failed: {e}")

    # GG-bis #709: guarantee >=1 CA per argument — retry uncovered targets once.
    # YY #730: retry still requests k_per_target CAs per uncovered item so total
    # CA count stays ≥ k × args even when the first batch missed targets.
    if added < len(targets) and client:
        covered_indices: set[int] = set()
        for ca in counters:
            if not isinstance(ca, dict):
                continue
            target_arg = str(ca.get("target_argument", ""))
            for i, t in enumerate(targets):
                if i not in covered_indices and t[:80] in target_arg:
                    covered_indices.add(i)
        uncovered = [t for i, t in enumerate(targets) if i not in covered_indices]
        if uncovered:
            logger.info(
                f"GG-bis: {len(uncovered)} targets uncovered "
                f"({len(covered_indices)}/{len(targets)}), retrying with k={k_per_target}"
            )
            try:
                retry_counters = await _generate_counters_for_targets(
                    client, model_id, uncovered, k_per_target=k_per_target
                )
                for ca in retry_counters:
                    if not isinstance(ca, dict):
                        continue
                    content = ca.get("counter_argument", "")
                    if not content:
                        continue
                    score = float(
                        ca.get("evaluation_score", ca.get("score", 0.0)) or 0.0
                    )
                    try:
                        state.add_counter_argument(
                            original_arg=str(ca.get("target_argument", ""))[:300],
                            counter_content=str(content),
                            strategy=str(ca.get("strategy_used", "")),
                            score=score,
                        )
                        added += 1
                    except Exception as e:
                        logger.debug(f"add_counter_argument retry failed: {e}")
            except Exception as e:
                logger.warning(f"GG-bis coverage retry failed: {e}")

    return {"added": added, "targets": len(targets)}


async def _run_formal_logic_from_state(
    state: Any, input_text: str = ""
) -> Dict[str, int]:
    """Populate PL/FOL volet-1 writers on the conversational path (HH #697).

    The conversational dialogue routes formal logic to ``belief_sets`` and never
    calls the volet-1 writers, so ``propositional_analysis_results`` /
    ``fol_analysis_results`` stay empty (PL/FOL = 0) — losing the quantitative
    axis vs the zero-shot baseline. This deterministic post-processor mirrors the
    Dung/modal/ASPIC ones: it reuses ``_invoke_propositional_logic`` /
    ``_invoke_fol_reasoning`` so the formulas are Tweety-verified exactly as on
    the sequential path, then writes them back via the state's add_* methods.
    """
    result = {"pl_added": 0, "fol_added": 0}

    ident = getattr(state, "identified_arguments", None)
    if isinstance(ident, dict):
        arg_texts = [str(v).strip() for v in ident.values() if v]
    elif isinstance(ident, list):
        arg_texts = [
            (
                str(
                    a.get("text") or a.get("description") or a.get("content") or ""
                ).strip()
                if isinstance(a, dict)
                else str(a).strip()
            )
            for a in ident
        ]
    else:
        return result
    arg_texts = [t for t in arg_texts if t]
    if not arg_texts:
        return result

    context: Dict[str, Any] = {
        "_state_object": state,
        "phase_extract_output": {"arguments": [{"text": t} for t in arg_texts]},
        "source_metadata": {"opaque_id": getattr(state, "source_id", "conversational")},
    }

    # Propositional logic — only if not already populated.
    if hasattr(state, "add_propositional_analysis_result") and not getattr(
        state, "propositional_analysis_results", None
    ):
        try:
            pl_out = await _invoke_propositional_logic(input_text, context)
            formulas = pl_out.get("formulas", []) if isinstance(pl_out, dict) else []
            if formulas:
                state.add_propositional_analysis_result(
                    formulas,
                    bool(pl_out.get("satisfiable", False)),
                    pl_out.get("model", {}) or {},
                )
                result["pl_added"] = len(formulas)
        except Exception as e:
            logger.warning(f"Conversational PL enrichment failed: {e}")

    # First-order logic — only if not already populated.
    if hasattr(state, "add_fol_analysis_result") and not getattr(
        state, "fol_analysis_results", None
    ):
        try:
            fol_out = await _invoke_fol_reasoning(input_text, context)
            formulas = fol_out.get("formulas", []) if isinstance(fol_out, dict) else []
            if formulas:
                state.add_fol_analysis_result(
                    formulas,
                    fol_out.get(
                        "consistent"
                    ),  # None=unverified, True/False=verified (#1019)
                    fol_out.get("inferences", []) or [],
                    float(fol_out.get("confidence", 0.0) or 0.0),
                )
                sig = fol_out.get("fol_signature", [])
                if isinstance(sig, list) and sig:
                    state.fol_signature = sig
                result["fol_added"] = len(formulas)
        except Exception as e:
            logger.warning(f"Conversational FOL enrichment failed: {e}")

    return result


async def _run_quality_sweep_from_state(state: Any) -> Dict[str, int]:
    """Score every identified argument's quality on the conversational path (JJ #699).

    The conversational ``QualityAgent`` depends on the agent turn budget; when the
    budget runs out the dialogue emits 0 quality scores, so the collaborative path
    is non-deterministic and some corpora end with quality = 0. This deterministic
    post-processor mirrors the Dung/modal/ASPIC/PL/FOL ones: it reuses the robust
    sequential ``_invoke_quality_evaluator`` (9-virtue evaluator, deterministic —
    the LLM enrichment pass is optional) over ``state.identified_arguments`` and
    writes every score back via ``state.add_quality_score``. Gated by the caller on
    under-production, so it only fills gaps — it never overwrites agent scores.
    """
    result = {"added": 0}

    ident = getattr(state, "identified_arguments", None)
    if isinstance(ident, dict):
        arg_texts = [str(v).strip() for v in ident.values() if v]
    elif isinstance(ident, list):
        arg_texts = [
            (
                str(
                    a.get("text") or a.get("description") or a.get("content") or ""
                ).strip()
                if isinstance(a, dict)
                else str(a).strip()
            )
            for a in ident
        ]
    else:
        return result
    arg_texts = [t for t in arg_texts if t]
    if not arg_texts:
        return result

    if not hasattr(state, "add_quality_score"):
        return result

    context: Dict[str, Any] = {
        "phase_extract_output": {"arguments": [{"text": t} for t in arg_texts]},
    }
    try:
        q_out = await _invoke_quality_evaluator("", context)
    except Exception as e:
        logger.warning(f"Conversational quality sweep failed: {e}")
        return result

    if not isinstance(q_out, dict):
        return result

    per_arg = q_out.get("per_argument_scores")
    if isinstance(per_arg, dict) and per_arg:
        already = set(getattr(state, "argument_quality_scores", {}) or {})
        for arg_id, scored in per_arg.items():
            if arg_id in already or not isinstance(scored, dict):
                continue
            try:
                state.add_quality_score(
                    arg_id,
                    scored.get("scores_par_vertu", {}) or {},
                    float(scored.get("note_finale", 0.0) or 0.0),
                    llm_assessment=scored.get("llm_assessment"),
                )
                result["added"] += 1
            except Exception as e:
                logger.debug(f"add_quality_score failed for {arg_id}: {e}")
    return result


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

    # #904: Override strategy when forced via --counter-strategy parametric selector
    # CLI uses short aliases (socratic, reductio, …); internal state uses RhetoricalStrategy
    # enum values (socratic_questioning, reductio_ad_absurdum, …) for comparability.
    _COUNTER_STRATEGY_ALIASES = {
        "socratic": "socratic_questioning",
        "reductio": "reductio_ad_absurdum",
        "analogy": "analogical_counter",
        "authority": "authority_appeal",
        "statistical": "statistical_evidence",
    }
    forced_strategy = context.get("counter_strategy", "auto")
    if forced_strategy != "auto":
        enum_value = _COUNTER_STRATEGY_ALIASES.get(forced_strategy, forced_strategy)
        strategy = {"strategy": enum_value}
        logger.info(
            f"Counter-argument strategy forced: {forced_strategy} → {enum_value} (parametric selector)"
        )

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

            # Build targets: ALL fallacious arguments + ALL arguments by quality.
            # GG #696: the previous top-3 fallacies + 5-total caps held output to
            # <=5 counter-arguments, losing to the zero-shot baseline on volume.
            # Sweep every target; _generate_counters_for_targets batches the
            # LLM calls so coverage stays reliable on dense corpora.
            targets = []
            for f in fallacies:
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
                if text:
                    targets.append(f"[quality={score:.1f}/10] {text}")

            if not targets:
                targets = [input_text[:500]]

            llm_counters = await _generate_counters_for_targets(
                client, model_id, targets
            )
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
    # Trace entry for counter-argument specialist (Track UU #724)
    _state = context.get("_state_object")
    if _state is not None and llm_counters:
        _n_ca = len(llm_counters)
        _top_strat = ""
        if _n_ca > 0 and isinstance(llm_counters[0], dict):
            _top_strat = str(llm_counters[0].get("strategy_used", ""))
        _state.add_trace_entry(
            phase="counter",
            agent="CounterArgumentAgent",
            reacts_to=["extract", "quality"],
            summary=f"{_n_ca} contre-arguments générés — stratégie dominante: {_top_strat or 'mixte'}. Analyse par 5 stratégies rhétoriques.",
        )
    return result


def _build_counter_argument_validation(
    overall_score: float,
    logical_strength: float,
) -> Dict[str, Any]:
    """Populate a counter-argument ``validation`` dict (G6 #1180, Epic #1165).

    The unified ``ValidationResult`` (``counter_argument/definitions.py:94``)
    was defined + exported but never populated in the pipeline — the 4 boolean
    fields (``is_valid_attack``/``original_survives``/``counter_succeeds``/
    ``logical_consistency``) came, in the original student deliverable
    (``counter_agent/logic/tweety_bridge.py``), from a Dung-theory attack
    graph built per counter-argument. That formal bridge was dropped during
    the #35 unification (β audit gap G6).

    Anti-pendule / fail-loud (#1019): we do NOT fabricate a formal Dung
    verdict here. We surface the *already-computed* 5-criteria evaluation
    (the evaluator's real output) into the validation shape, with thresholds
    derived from the original student fallback
    (``tweety_bridge._fallback_validation``), which itself mapped strength
    labels → booleans. The unified evaluator produces a continuous
    ``overall_score`` ∈ [0,1] (weighted sum of 5 criteria, each ∈ [0,1]),
    a richer signal than the student's categorical strength — so we map the
    score onto the boolean fields with documented thresholds, and we label
    ``formal_representation`` honestly as a heuristic (NOT a Tweety check):

      - ``counter_succeeds``: overall_score ≥ 0.5 (the counter lands).
      - ``original_survives``: overall_score < 0.6 (the original still holds
        below a strong counter). Asymmetric vs ``counter_succeeds`` by design:
        a mid-range counter both lands and leaves the original partially
        standing (a real dynamic in argumentation).
      - ``is_valid_attack``: counter_succeeds AND logical_strength ≥ 0.4
        (a landing counter that is also internally coherent).
      - ``logical_consistency``: logical_strength ≥ 0.4 (the counter's own
        internal logic is coherent — not a cross-argument Dung check).

    Returns a plain dict (not the dataclass) so it serializes into the state
    entry without an import dependency at write time.
    """
    counter_succeeds = overall_score >= 0.5
    original_survives = overall_score < 0.6
    is_valid_attack = counter_succeeds and logical_strength >= 0.4
    logical_consistency = logical_strength >= 0.4
    return {
        "is_valid_attack": is_valid_attack,
        "original_survives": original_survives,
        "counter_succeeds": counter_succeeds,
        "logical_consistency": logical_consistency,
        "formal_representation": (
            "heuristic (5-criteria weighted score; not a Tweety/Dung "
            "formal verification)"
        ),
    }


def _evaluate_counter_arguments(
    llm_counters: List[Dict[str, Any]], input_text: str
) -> List[Dict[str, Any]]:
    """Auto-evaluate each LLM counter-argument using CounterArgumentEvaluator (#294).

    Wraps each LLM-generated dict into proper Argument/CounterArgument dataclass
    objects, runs the 5-criteria evaluator, and attaches the evaluation_score.

    G6 (#1180): also populates a ``validation`` dict (``ValidationResult`` shape)
    from the already-computed evaluation, so the counter-argument *validity*
    verdict reaches the state and the restitution report can cite it — not
    just that counter-arguments exist. Surface-only (no fabricated formal
    signal); see ``_build_counter_argument_validation``.
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
            # G6 (#1180): surface the validation verdict from the computed
            # evaluation. Anti-pendule: built from the real overall_score +
            # logical_strength, never fabricated. Fail-loud: if this branch
            # runs, evaluation succeeded; the validation dict is always set.
            ca_dict["validation"] = _build_counter_argument_validation(
                float(evaluation.overall_score),
                float(evaluation.logical_strength),
            )
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

            det_params = _get_determinism_params()
            # G8 (#1184): hand the LLM the restored Walton scheme table so
            # exchanges can be scheme-grounded. The scheme classification is
            # re-checked deterministically at write-time (classify_scheme) — this
            # prompt block nudges the LLM toward scheme-shaped exchanges but the
            # authoritative scheme label comes from the deterministic matcher
            # (anti-pendule: no fabricated scheme if the LLM hallucinates one).
            try:
                from argumentation_analysis.agents.core.debate.argumentation_schemes import (
                    schemes_as_prompt_context,
                )

                scheme_kb = schemes_as_prompt_context()
            except ImportError:
                scheme_kb = ""
            scheme_directive = (
                (
                    "\n\nGROUNDED SCHEMES (Walton-Krabbe, restored engine G8):\n"
                    f"{scheme_kb}\n"
                    "Each Agent A point should resemble one of these schemes; Agent B's "
                    "rebuttal should stress its critical question. Name the scheme the "
                    "point relies on inside agent_a_point when clearly applicable — do "
                    "NOT force a scheme label where none fits (honest absence > fake label).\n"
                )
                if scheme_kb
                else ""
            )
            response = await _guarded_chat_completion(
                client,
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
                            + scheme_directive
                        ),
                    },
                    {"role": "user", "content": debate_material},
                ],
                **det_params,
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

    # Trace entry for debate analysis specialist
    _state = context.get("_state_object")
    if _state is not None and base_scores:
        _winner = base_scores.get("winner", "indéterminé")
        _quality = base_scores.get("debate_quality", 0)
        _completed = (
            "oui" if base_scores.get("llm_debate_assessment") else "heuristique"
        )
        _state.add_trace_entry(
            phase="debate",
            agent="DebateAgent",
            reacts_to=["counter", "quality", "jtms"],
            summary=f"Débat complété ({_completed}) — vainqueur: {_winner}, qualité: {_quality}/5. Évaluation adversariale multi-agent.",
        )
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
                    "method": context.get("vote_method", "copeland"),
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

            det_params = _get_determinism_params()
            response = await _guarded_chat_completion(
                client,
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
                **det_params,
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
    # Consensus threshold check (parametric selector --consensus-threshold, #899)
    consensus_threshold = context.get("consensus_threshold", 0.7)
    if positions and vote_result:
        try:
            metrics_json = plugin.compute_consensus_metrics(json.dumps(vote_result))
            consensus_metrics = json.loads(metrics_json)
            consensus_rate = consensus_metrics.get("consensus_rate", 0.0)
            result["consensus_metrics"] = consensus_metrics
            result["consensus_met"] = consensus_rate >= consensus_threshold
            result["consensus_threshold_used"] = consensus_threshold
        except Exception as e:
            logger.debug(f"Consensus metrics computation skipped: {e}")
    if llm_governance:
        result["llm_governance_assessment"] = llm_governance
        result["recommended_method"] = llm_governance.get("recommended_method")
        result["consensus_potential"] = llm_governance.get("consensus_potential")
    # Trace entry for governance specialist
    _state = context.get("_state_object")
    if _state is not None and result.get("conflict_count", 0) > 0:
        _n_conflicts = result.get("conflict_count", 0)
        _vote = result.get("vote_result", {})
        _consensus = result.get("consensus_potential", "N/A")
        _method = result.get("recommended_method", "copeland")
        _state.add_trace_entry(
            phase="governance",
            agent="GovernanceModule",
            reacts_to=["quality", "hierarchical_fallacy", "jtms"],
            summary=f"{_n_conflicts} conflits détectés — méthode: {_method}, consensus: {_consensus}. Vote social-choice appliqué.",
        )
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

    _raw_arg_texts = [_text(a) for a in raw_args[:10]]
    claim_beliefs = [_text(c) for c in raw_claims[:6]]

    if not _raw_arg_texts and not claim_beliefs:
        sentences = [s.strip() for s in input_text.split(".") if len(s.strip()) > 10]
        _raw_arg_texts = [s[:73] for s in sentences[:8]]

    # Prefix each belief name with its arg_id so compute_argument_convergence
    # can index JTMS signals by arg_id (startswith "arg_N:").  Without the
    # prefix, names are raw text excerpts and the arg_id substring check never
    # matches, silently dropping the JTMS convergence signal for every corpus.
    arg_beliefs = [f"arg_{i+1}:{t[:66]}" for i, t in enumerate(_raw_arg_texts)]

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
        # Fallback: try problematic_quote (exact text from source)
        if target_idx < 0 and arg_beliefs:
            quote_text = f.get("problematic_quote", "")
            if quote_text:
                quote_lower = quote_text.lower()[:80]
                for idx, ab in enumerate(arg_beliefs):
                    if quote_lower in ab.lower() or ab.lower() in quote_lower:
                        target_idx = idx
                        break
        # Fallback: try explanation text
        if target_idx < 0 and arg_beliefs:
            expl_text = f.get("explanation", "")
            if expl_text:
                expl_lower = expl_text.lower()[:80]
                for idx, ab in enumerate(arg_beliefs):
                    if expl_lower in ab.lower() or ab.lower() in expl_lower:
                        target_idx = idx
                        break
        # Final fallback: index-based matching
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

    _jtms_result = {
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
    # Trace entry for JTMS specialist
    _state = context.get("_state_object")
    _n_beliefs_raw = _jtms_result.get("belief_count", 0)
    if _state is not None and isinstance(_n_beliefs_raw, int) and _n_beliefs_raw > 0:
        _n_beliefs = _n_beliefs_raw
        _n_retracted = (
            _jtms_result.get("undermined_count", 0)
            if isinstance(_jtms_result.get("undermined_count"), int)
            else 0
        )
        _state.add_trace_entry(
            phase="jtms",
            agent="JTMSAgent",
            reacts_to=["hierarchical_fallacy"],
            summary=f"{_n_beliefs} croyances ajoutées — {_n_retracted} rétractées par sophismes. Réseau de dépendances JTMS propagé.",
        )
    return _jtms_result


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
        # Build positional mapping: arg_names[i] -> canonical key "arg_{i+1}"
        # per_arg_scores is keyed by canonical arg_id, arg_names are free text.
        for idx, arg_name in enumerate(arg_names):
            canonical = f"arg_{idx + 1}"
            scores = per_arg_scores.get(canonical)
            if not isinstance(scores, dict):
                scores = per_arg_scores.get(arg_name)
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
        # Fail-loud (#1019): report unavailability explicitly so the empty
        # result is NOT misread as "analysis ran and found 0 fallacies".
        return {
            "detected_fallacies": {},
            "arguments": {},
            "tiers_used": ["none"],
            "status": "unavailable",
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

        # RA-4 #1049 item 3: inject strategic directives into LLM prompt
        _strat_text_cam, _strat_ids_cam = _get_strategic_directives(context)
        _effective_text_cam = (
            f"{_strat_text_cam}\n\n{input_text}" if _strat_text_cam else input_text
        )

        # Bounded wide-net descent (#1087) — same backstop as the main path above:
        # the camembert wide-net is unbounded and explodes on dense corpora. The
        # per-arg enrichment below (already bounded) is a real fallback method.
        try:
            result_json = await asyncio.wait_for(
                plugin.run_guided_analysis(argument_text=_effective_text_cam),
                timeout=300.0,
            )
            result = json.loads(result_json)
        except asyncio.TimeoutError:
            logger.warning(
                "Camembert wide-net fallacy descent timed out (>300s) on %d chars "
                "— continuing with per-argument enrichment only (#1087)",
                len(_effective_text_cam),
            )
            result = {
                "fallacies": [],
                "exploration_method": "widenet_timeout_camembert",
                "wide_net_timed_out": True,
            }

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

        _ret = {
            "detected_fallacies": detected,
            "arguments": {},
            "tiers_used": ["self_hosted_llm"],
            "explanation": f"Self-hosted LLM ({model_id}): {len(detected)} fallacy(ies) detected",
            "total_fallacies": len(detected),
            "extraction_method": result.get("exploration_method", "self_hosted"),
        }
        if _strat_ids_cam:
            _ret["strategic_objective_ids"] = _strat_ids_cam
        return _ret

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
    """Invoke local LLM service for text analysis (#834).

    Enriched with state writing: persists results to state.local_llm_results
    and adds a trace entry. Falls back gracefully when local LLM endpoint
    is unavailable (returns status=skipped, not an error).
    """
    from argumentation_analysis.services.local_llm_service import LocalLLMService

    service = LocalLLMService()

    # Check availability first
    try:
        available = await service.is_available()
    except Exception:
        available = False
    if not available:
        logger.info("Local LLM endpoint unavailable — skipping")
        result = {
            "status": "skipped: endpoint_unavailable",
            "model": getattr(service, "model", "unknown"),
        }
        _state = context.get("_state_object")
        if _state is not None and hasattr(_state, "local_llm_results"):
            _state.local_llm_results.append(result)
        return result

    # Build prompt — optionally include upstream extract results for context
    extract_output = context.get("phase_extract_output", {})
    system_prompt = (
        "You are an argument analysis assistant. "
        "Analyze the text for arguments, fallacies, and logical structure."
    )
    user_content = input_text

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        response = await service.chat_completion(messages)
    except Exception as exc:
        logger.warning(f"Local LLM call failed: {exc}")
        result = {
            "status": "error",
            "error": str(exc),
        }
        _state = context.get("_state_object")
        if _state is not None and hasattr(_state, "local_llm_results"):
            _state.local_llm_results.append(result)
        return result

    result = {
        "status": "completed",
        "response": response if isinstance(response, str) else str(response),
        "model": getattr(service, "model", "local"),
        "input_length": len(input_text),
    }

    # Write to shared state
    _state = context.get("_state_object")
    if _state is not None:
        if hasattr(_state, "local_llm_results"):
            _state.local_llm_results.append(result)
        _state.add_trace_entry(
            phase="local_llm",
            agent="LocalLLM",
            reacts_to=["extract"],
            summary=f"Local LLM: {result['status']} ({result.get('input_length', 0)} chars input)",
        )

    logger.info(
        f"Local LLM: {result['status']} ({result.get('input_length', 0)} chars)"
    )
    return result


async def _invoke_semantic_index(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke semantic index service for argument search.

    KK #700: consults ``is_available()`` before attempting indexing.
    Returns explicit status: ``ran`` (endpoint up, indexed) or
    ``skipped: endpoint_unavailable`` (no silent optional skip).
    """
    from argumentation_analysis.services.semantic_index_service import (
        SemanticIndexService,
    )

    service = SemanticIndexService()
    if not service.is_available():
        return {
            "status": "skipped: endpoint_unavailable",
            "reason": "SemanticIndexService at 127.0.0.1:9001 is not reachable",
        }

    results = await asyncio.to_thread(service.search, input_text)
    return {"status": "ran", "results": results}


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
            # Primary: explicit arguments list (from fact_extraction LLM).
            # Generous cap [:40] (#708, anti-pendulum): this list feeds the
            # uncapped counter sweep; bounding it stops a degenerate upstream
            # from driving thousands of LLM calls, while 40 still far exceeds
            # the 0-shot argument volume (the GG #696 volume win is preserved).
            if "arguments" in phase_out:
                args = phase_out["arguments"]
                if isinstance(args, list) and args:
                    return [
                        a.get("text", str(a)) if isinstance(a, dict) else str(a)
                        for a in args[:40]
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


# --- Input-shaping helpers for dormant Dung-family reasoners (#1169 W1) ---
#
# These map spectacular's canonical context (arguments: List[str],
# attacks: List[List[str]] pairs from _generate_attacks_from_args) into the
# typed structures each Tweety handler expects. Without this shaping the
# handlers raise on signature/type mismatch (same bug family as E1b #1168
# layer-2: invokeables feeding the wrong input shape). The mapping is
# deterministic and lossless for the attack graph; weights/beliefs default
# to neutral values when upstream provides none (#1019: no fabricated signal).


def _setaf_attacks_from_pairs(
    attacks: List[List[str]],
) -> List[Dict[str, Any]]:
    """Convert ``[attacker, target]`` pairs into SetAF attack specs.

    SetAF allows a *set* of attackers jointly attacking a target; for the
    pairwise graph produced by ``_generate_attacks_from_args`` each pair
    becomes a singleton-attacker set.
    """
    specs: List[Dict[str, Any]] = []
    for pair in attacks:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            specs.append({"attackers": [str(pair[0])], "target": str(pair[1])})
    return specs


def _weighted_attacks_from_pairs(
    attacks: List[List[str]],
    weights: Optional[Dict[str, float]] = None,
    default_weight: float = 0.5,
) -> List[Tuple[str, str, float]]:
    """Convert ``[source, target]`` pairs into weighted-attack triples.

    Weights are looked up by ``"source->target"`` key when upstream provides
    them (e.g. derived from fallacy confidence); otherwise the neutral
    ``default_weight`` is used (no fabricated confidence signal, #1019).
    """
    triples: List[Tuple[str, str, float]] = []
    for pair in attacks:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            src, tgt = str(pair[0]), str(pair[1])
            w = default_weight
            if weights and f"{src}->{tgt}" in weights:
                w = float(weights[f"{src}->{tgt}"])
            triples.append((src, tgt, w))
    return triples


def _aba_rules_from_context(
    arguments: List[str],
    context: Dict[str, Any],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Derive ABA assumptions + rules from spectacular's argument graph.

    Assumptions = the first few arguments (the open premises to defend).
    Rules = each non-assumption argument is supported by the assumption(s)
    preceding it (``head=arg, body=[assumption]``). When upstream provides
    explicit ``assumptions``/``rules`` in context, those win.
    """
    assumptions = context.get("assumptions")
    if not isinstance(assumptions, list) or not assumptions:
        # Take up to 3 leading arguments as the assumptions to test.
        assumptions = [str(a) for a in arguments[: min(3, len(arguments))]]
    else:
        assumptions = [str(a) for a in assumptions]

    rules = context.get("rules")
    if isinstance(rules, list) and rules:
        shaped = [
            {
                "head": str(r.get("head", "")),
                "body": [str(b) for b in r.get("body", [])],
            }
            for r in rules
            if isinstance(r, dict)
        ]
        if shaped:
            return assumptions, shaped

    # Derive: each non-assumption argument is concluded from an assumption.
    derived: List[Dict[str, Any]] = []
    for arg in arguments:
        arg_s = str(arg)
        if arg_s in assumptions:
            continue
        # Support this argument from the first assumption (a real premise link).
        derived.append({"head": arg_s, "body": [assumptions[0]]})
    if not derived and assumptions:
        # At least one rule so the theory is non-empty.
        derived.append({"head": assumptions[0], "body": [assumptions[0]]})
    return assumptions, derived


def _adf_conditions_from_context(
    arguments: List[str],
    context: Dict[str, Any],
) -> Tuple[List[str], Dict[str, str]]:
    """Derive ADF statements + acceptance conditions from spectacular arguments.

    Each statement gets a verum/falsum condition derived from whether the
    argument appears as a supporter or attacker in the attack graph.
    Upstream ``statements``/``acceptance_conditions`` in context override.
    """
    statements = context.get("statements")
    if isinstance(statements, list) and statements:
        statements = [str(s) for s in statements]
    else:
        statements = [str(a) for a in arguments]

    conds_in = context.get("acceptance_conditions")
    if isinstance(conds_in, dict) and conds_in:
        return statements, {str(k): str(v) for k, v in conds_in.items()}

    # Derive conditions from attack graph: attacked args → contradiction-ish.
    attacks = context.get("attacks") or []
    attacked = set()
    for pair in attacks:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            attacked.add(str(pair[1]))
    # Tweety ADF acceptance condition strings: "T" (tautology/accepted),
    # "F" (contradiction), or a propositional formula over other statements.
    conditions: Dict[str, str] = {}
    for s in statements:
        conditions[s] = "F" if s in attacked else "T"
    if not conditions and statements:
        conditions[statements[0]] = "T"
    return statements, conditions


def _eaf_beliefs_from_context(
    arguments: List[str],
    context: Dict[str, Any],
) -> Optional[Dict[str, List[str]]]:
    """Derive EAF epistemic beliefs (agent → believed args) from context.

    EAF expects ``Dict[agent_name, List[arg_name]]`` — NOT floats. Returns
    None when no agent structure is derivable (handler defaults to "all
    arguments believed by all agents" — a valid non-fabricated baseline).
    """
    beliefs_in = context.get("epistemic_beliefs")
    if isinstance(beliefs_in, dict) and beliefs_in:
        # Already the right shape (agent → list of args)?
        sample = next(iter(beliefs_in.values()))
        if isinstance(sample, (list, tuple)):
            return {str(k): [str(x) for x in v] for k, v in beliefs_in.items()}
        # Float-valued (probability per arg): treat as a single agent's beliefs
        # above a neutral 0.5 threshold — no fabricated multi-agent structure.
        believed = [str(k) for k, v in beliefs_in.items() if float(v) >= 0.5]
        if believed:
            return {"agent_0": believed}
    return None


def _python_ranking_fallback(
    arguments: List[str], attacks: List[List[str]], method: str
) -> Dict[str, Any]:
    """Fail-loud stub — ranking semantics requires JVM/Tweety (#1019, RA-8 #1053).

    Previous pure-Python fallback produced synthetic scores that entered state
    as authentic formal results (anti-theater violation). Now raises instead.
    """
    raise RuntimeError(
        f"Ranking semantics ({method}) unavailable: JVM/Tweety required. "
        "Install JVM and ensure Tweety JARs are on the classpath."
    )


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
        logger.warning(
            "Bipolar analysis unavailable: no JVM/Tweety handler could be loaded. "
            "Reporting unverified status. (%s)",
            e,
        )
        raise RuntimeError(
            f"Bipolar analysis ({fw_type}) unavailable: JVM/Tweety required. "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


async def _invoke_aba(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke ABA handler with JVM fallback."""
    args = _extract_arguments_from_context(input_text, context)
    # ABA rules come as {head, body} dicts. Shape from the argument graph
    # when upstream provides none (bug family E1b #1168: handler rejected the
    # old string rules ``"a => valid"``).
    assumptions, rules = _aba_rules_from_context(args, context)
    contraries = context.get("contraries")
    semantics = context.get("semantics", "preferred")

    try:
        from argumentation_analysis.agents.core.logic.aba_handler import ABAHandler

        handler = ABAHandler()  # type: ignore[no-untyped-call]
        return await asyncio.to_thread(
            handler.analyze_aba_framework, assumptions, rules, contraries, semantics
        )
    except Exception as e:
        raise RuntimeError(
            f"ABA reasoning unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


async def _invoke_adf(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke ADF handler with JVM fallback."""
    args = _extract_arguments_from_context(input_text, context)
    # ADF acceptance conditions map statement → propositional formula string.
    # Shape from the attack graph when upstream provides none.
    statements, conditions = _adf_conditions_from_context(args, context)
    semantics = context.get("semantics", "grounded")

    try:
        from argumentation_analysis.agents.core.logic.adf_handler import ADFHandler

        handler = ADFHandler()  # type: ignore[no-untyped-call]
        return await asyncio.to_thread(
            handler.analyze_adf, statements, conditions, semantics
        )
    except Exception as e:
        raise RuntimeError(
            f"ADF reasoning unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


def _pl_atom(text: str, prefix: str = "p") -> str:
    """Sanitize free text into a valid propositional-logic atom.

    Tweety's ``PlParser.parseFormula`` rejects atoms containing anything
    outside ``[A-Za-z0-9_]`` (e.g. ``Unknown object teleprompteranecdote``
    when raw corpus text leaked into a belief set / ASPIC rule). Upstream
    pipeline data (extracted arguments, fallacy types) is free-form text —
    it must be reduced to a stable alphanumeric atom before PL parsing.

    The mapping is lossy by design (PL atoms are opaque labels, not
    semantics): we keep up to 24 leading alnum chars of the text, lowercased,
    non-alnum collapsed to ``_``. A short hash suffix disambiguates distinct
    inputs that collapse to the same prefix (avoids false collisions that
    would merge distinct beliefs). Deterministic (no Math.random).
    """
    import re as _re
    import hashlib as _hashlib

    if not text:
        return f"{prefix}_0"
    cleaned = _re.sub(r"[^A-Za-z0-9]+", "_", str(text)).strip("_").lower()[:24]
    if not cleaned:
        cleaned = "x"
    digest = _hashlib.md5(str(text).encode("utf-8")).hexdigest()[:6]
    return f"{prefix}_{cleaned}_{digest}"


def _python_aspic_fallback(
    args: List[str],
    strict: List[str],
    defeasible: List[str],
    fallacies: List[Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Fail-loud stub — ASPIC+ analysis requires JVM/Tweety (#1019, RA-8 #1053).

    Previous pure-Python fallback produced synthetic defensibility scores that
    entered state as authentic formal results (anti-theater violation).
    """
    raise RuntimeError(
        "ASPIC+ analysis unavailable: JVM/Tweety required. "
        "Install JVM and ensure Tweety JARs are on the classpath."
    )


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
        # Strict rules: factual claims support conclusions. The ASPIC handler
        # expects dicts {head, body} with PL-atom heads/bodies (not raw rule
        # strings — the handler builds StrictRule/DefeasibleRule itself).
        # Atoms are sanitized via _pl_atom (Tweety's Proposition rejects
        # non-alphanumeric names).
        extract_output = context.get("phase_extract_output", {})
        claims = (
            extract_output.get("claims", []) if isinstance(extract_output, dict) else []
        )
        for i, claim in enumerate(claims[:4]):
            text = (
                claim.get("text", str(claim)) if isinstance(claim, dict) else str(claim)
            )
            strict.append(
                {"head": f"supported_{i+1}", "body": [_pl_atom(text, prefix="claim")]}
            )
        # If claims feed into arguments, chain them.
        if len(args) >= 2:
            strict.append(
                {"head": "argument_chain", "body": ["supported_1", "supported_2"]}
            )

    defeasible = context.get("defeasible_rules")
    if not defeasible:
        defeasible = []
        # Defeasible rules: arguments that could be undermined.
        for i, arg in enumerate(args[:4]):
            defeasible.append(
                {
                    "head": f"plausible_conclusion_{i+1}",
                    "body": [_pl_atom(arg, prefix="arg")],
                    "name": f"def_arg_{i+1}",
                }
            )
        # Fallacy-based defeat: a detected fallacy undermines an argument.
        for j, f in enumerate(fallacies[:3]):
            if isinstance(f, dict):
                ft = str(f.get("type", f.get("fallacy_type", "unknown")))
                defeasible.append(
                    {
                        "head": f"undermined_{j+1}",
                        "body": [_pl_atom(ft, prefix="fallacy")],
                        "name": f"defeater_{j+1}",
                    }
                )

    axioms_raw = context.get("axioms")
    # Sanitize axioms too (list of proposition names).
    axioms = None
    if axioms_raw:
        axioms = [_pl_atom(a, prefix="ax") for a in axioms_raw if isinstance(a, str)]

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

        # Sanitize free-form beliefs/new_belief into valid PL atoms.
        # Upstream data (extracted args, fallacy types, LLM counter-arguments)
        # is free text — Tweety's PlParser rejects non-alphanumeric atoms
        # (ParserException: Unknown object ...). Reduce to stable atoms.
        safe_beliefs = [_pl_atom(b) for b in beliefs if b and isinstance(b, str)]
        safe_new_belief = _pl_atom(new_belief, prefix="n")
        if not safe_beliefs:
            safe_beliefs = [_pl_atom("initial_belief", prefix="b")]

        handler = BeliefRevisionHandler()  # type: ignore[no-untyped-call]
        return await asyncio.to_thread(
            handler.revise, safe_beliefs, safe_new_belief, method
        )
    except Exception as e:
        raise RuntimeError(
            f"Belief revision ({method}) unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


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
        raise RuntimeError(
            f"Probabilistic argumentation unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


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
        raise RuntimeError(
            f"Dialogue protocol unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


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
        raise RuntimeError(
            f"Description Logic unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


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
        raise RuntimeError(
            f"Conditional Logic unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


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
    # SetAF attacks come as {attackers, target} dicts. Upstream may provide
    # them directly, else shape from the canonical pairwise attack graph.
    raw_attacks = context.get("set_attacks")
    if (
        isinstance(raw_attacks, list)
        and raw_attacks
        and isinstance(raw_attacks[0], dict)
    ):
        attacks = raw_attacks
    else:
        pairs = context.get("attacks") or _generate_attacks_from_args(args, context)
        attacks = _setaf_attacks_from_pairs(pairs)
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
        raise RuntimeError(
            f"SetAF analysis unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


async def _invoke_weighted(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Weighted AF handler (#87) with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    # Weighted attacks come as (source, target, weight) triples. Upstream may
    # provide them directly, else shape from the canonical pairwise graph with
    # neutral weight 0.5 (#1019: no fabricated confidence).
    raw_attacks = context.get("weighted_attacks")
    if (
        isinstance(raw_attacks, list)
        and raw_attacks
        and isinstance(raw_attacks[0], (list, tuple))
        and len(raw_attacks[0]) >= 3
    ):
        attacks = [
            (str(t[0]), str(t[1]), float(t[2]))
            for t in raw_attacks
            if isinstance(t, (list, tuple)) and len(t) >= 3
        ]
    else:
        pairs = context.get("attacks") or _generate_attacks_from_args(args, context)
        attacks = _weighted_attacks_from_pairs(pairs)
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
        raise RuntimeError(
            f"Weighted AF analysis unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


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
    """Fail-loud stub — Social AF requires JVM/Tweety (#1019, RA-8 #1053).

    Previous pure-Python fallback produced synthetic social scores that entered
    state as authentic formal results (anti-theater violation).
    """
    raise RuntimeError(
        "Social argumentation unavailable: JVM/Tweety required. "
        "Install JVM and ensure Tweety JARs are on the classpath."
    )


def _python_eaf_fallback(
    args: List[str],
    attacks: List[List[str]],
    semantics: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Fail-loud stub — EAF analysis requires JVM/Tweety (#1019, RA-8 #1053).

    Previous pure-Python fallback produced synthetic epistemic states that entered
    state as authentic formal results (anti-theater violation).
    """
    raise RuntimeError(
        f"Epistemic AF analysis ({semantics}) unavailable: JVM/Tweety required. "
        "Install JVM and ensure Tweety JARs are on the classpath."
    )


# --- EAF / DeLP / QBF invoke functions (#88, #89, #90) ---


async def _invoke_eaf(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Epistemic AF handler (#88) with JVM fallback."""
    args = context.get("arguments") or _extract_arguments_from_context(
        input_text, context
    )
    attacks = context.get("attacks") or _generate_attacks_from_args(args, context)
    # EAF expects Dict[agent, List[arg]] beliefs, NOT float probabilities.
    # Shape/validate; None lets the handler default to "all believed" (valid
    # non-fabricated baseline, #1019).
    beliefs = _eaf_beliefs_from_context(args, context)
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
    """Invoke DeLP handler (#89) with JVM fallback.

    #1215 (FP-12): requires an explicit ``program`` in context. Never feeds raw
    text to ``DelpParser`` — DeLP syntax (facts / strict rules / defeasible
    rules) is not prose; the old ``input_text[:500]`` default guaranteed a parse
    failure AND leaked corpus text into the parser (correctness + privacy).
    Honest-absent when no program is supplied, not a fake parse.
    """
    program_text = context.get("program")
    queries = context.get("queries", [])
    criterion = context.get("criterion", "generalized_specificity")

    if not program_text:
        return {
            "status": "unavailable",
            "message": (
                "DeLP analysis requires an explicit 'program' in context "
                "(DeLP syntax: 'fact.', 'head <- body.' strict, "
                "'head -< body.' defeasible). Raw text is not a valid program."
            ),
            "queries": queries,
        }

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
        raise RuntimeError(
            f"DeLP analysis unavailable: JVM/Tweety required ({e}). "
            "Install JVM and ensure Tweety JARs are on the classpath."
        )


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
            Program = jpype.JClass("org.tweetyproject.lp.asp.syntax.Program")
            ASPRule = jpype.JClass("org.tweetyproject.lp.asp.syntax.ASPRule")
            ASPAtom = jpype.JClass("org.tweetyproject.lp.asp.syntax.ASPAtom")

            # Parse simple rules: "a :- b." format
            rules = []
            for line in str(program).strip().splitlines():
                line = line.strip().rstrip(".")
                if not line or line.startswith("%"):
                    continue
                if ":-" in line:
                    head, body = line.split(":-", 1)
                    head_atoms = [
                        ASPAtom(h.strip()) for h in head.split(",") if h.strip()
                    ]
                    body_atoms = [
                        ASPAtom(b.strip()) for b in body.split(",") if b.strip()
                    ]
                    rule = ASPRule()
                    for a in head_atoms:
                        rule.getHead().add(a)
                    for a in body_atoms:
                        rule.getBody().add(a)
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
        import clingo as clingo_py  # type: ignore[import-untyped,unused-ignore]

        py_models: list[list[str]] = []
        ctl = clingo_py.Control(
            arguments=[f"--models={max_models}" if max_models else "--models=0"]
        )
        ctl.add("base", [], str(program))
        ctl.ground([("base", [])])

        def on_model(model: Any) -> None:
            py_models.append([str(s) for s in model.symbols(shown=True)])

        ctl.solve(on_model=on_model)
        return {
            "answer_sets": py_models,
            "num_models": len(py_models),
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
    rules = [
        l.strip().rstrip(".")
        for l in lines
        if ":-" in l and not l.strip().startswith("%")
    ]
    facts = [
        l.strip().rstrip(".")
        for l in lines
        if ":-" not in l and l.strip() and not l.strip().startswith("%")
    ]

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

    After the wide-net pass, runs per-argument enrichment to lift recall on
    dense text. Results are merged and deduplicated by taxonomy_pk, keeping
    the highest-confidence entry for each unique fallacy.

    The ``fallacy_tier`` context key selects the detection depth:
      - ``taxonomy``: lexical-only via TaxonomySophismDetector (no LLM, CI-safe)
      - ``hybrid``: FrenchFallacyAdapter with LLM disabled (neural+symbolic)
      - ``llm``: full LLM iterative deepening (default, current behavior)
      - ``full``: LLM pass + hybrid pass, merged
    """
    # Tier dispatch — select detection depth via context parameter
    tier = context.get("fallacy_tier", "llm")

    if tier == "taxonomy":
        return await _invoke_taxonomy_only_fallacy(input_text, context)
    elif tier == "hybrid":
        return await _invoke_hybrid_fallacy(input_text, context)
    elif tier == "full":
        return await _invoke_full_fallacy(input_text, context)
    # else: "llm" (default) — continue with existing LLM-based detection below

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
        from semantic_kernel.kernel import Kernel
        from argumentation_analysis.core.llm_service import create_llm_service
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        # Route through create_llm_service so the OpenRouter toggle applies:
        # OPENROUTER_BASE_URL + OPENROUTER_API_KEY -> OpenRouter (OpenAI-compatible),
        # else the official OpenAI endpoint. Building OpenAIChatCompletion directly
        # here bypassed the toggle and kept hitting OpenAI's quota even when
        # OpenRouter was configured. force_authentic=True preserves the prior
        # always-real-service behavior (never a mock under PYTEST_CURRENT_TEST).
        llm_service = create_llm_service(
            service_id="fallacy_widenet",
            force_authentic=True,
        )
        master_kernel = Kernel()
        master_kernel.add_service(llm_service)

        plugin = FallacyWorkflowPlugin(
            master_kernel=master_kernel,
            llm_service=llm_service,
            taxonomy_file_path=taxonomy_path,
        )

        # RA-4 #1049 item 3: inject strategic directives into LLM prompt
        _strat_text, _strat_ids = _get_strategic_directives(context)
        _effective_text = (
            f"{_strat_text}\n\n{input_text}" if _strat_text else input_text
        )

        # Bounded wide-net descent (#1087). The wide-net ``run_guided_analysis``
        # on the FULL source text is unbounded here — on a dense corpus it explodes
        # (iterative deepening over the taxonomy with no wall-clock cap) and the
        # per-run LLM budget does not count SK-kernel calls made inside the plugin,
        # so the only backstop is this timeout. 300s is generous: a healthy
        # wide-net completes in ~250s on a 46K corpus; on timeout we fall back to
        # the per-argument enrichment below (already bounded: 10 args x 165s) — a
        # REAL alternate method, not a heuristic. ``wide_net_timed_out`` flags the
        # partial so the report is honest (anti-theater #1019): the run completes,
        # but wide-net coverage is absent for that corpus.
        try:
            result_json = await asyncio.wait_for(
                plugin.run_guided_analysis(argument_text=_effective_text),
                timeout=300.0,
            )
            result = json.loads(result_json)
        except asyncio.TimeoutError:
            logger.warning(
                "Wide-net fallacy descent timed out (>300s) on input of %d chars "
                "— falling back to per-argument enrichment only (#1087)",
                len(_effective_text),
            )
            result = {
                "fallacies": [],
                "exploration_method": "widenet_timeout",
                "wide_net_timed_out": True,
            }
        result["extraction_method"] = result.get("exploration_method", "unknown")
        if _strat_ids:
            result["strategic_objective_ids"] = _strat_ids

        # Per-argument enrichment pass: run _invoke_hierarchical_fallacy_per_argument
        # and merge extras into the wide-net results to lift recall on dense text.
        try:
            per_arg_result = await _invoke_hierarchical_fallacy_per_argument(
                input_text, context
            )
            wide_fallacies = result.get("fallacies", [])
            per_arg_fallacies = per_arg_result.get("fallacies", [])
            merged = _merge_fallacy_results(wide_fallacies, per_arg_fallacies)
            result["fallacies"] = merged
            # FB-36 (#1123): label honestly. When the per-argument pass was
            # skipped fail-loud (no extractable arguments — recursion fix), this
            # is wide-net-only, NOT a union; surface the skip at the result
            # level too so the report/state layer sees the per-arg lift was
            # lost (fail-loud, anti-theater #1019).
            if per_arg_result.get("per_argument_skipped"):
                result["extraction_method"] = "widenet_only_no_perarg_args"
                result["degraded"] = True
                _existing_err = result.get("last_error")
                result["last_error"] = (
                    ("; " + _existing_err if _existing_err else "")
                    + "per-argument fallacy lift skipped (no extractable arguments)"
                ).lstrip("; ")
                logger.warning(
                    "Per-argument fallacy lift skipped (FB-36 #1123): no "
                    "extractable arguments — wide-net result only, per-arg "
                    "recall lift lost (widenet=%d fallacies retained)",
                    len(wide_fallacies),
                )
            else:
                result["extraction_method"] = "widenet+perarg_union"
            logger.info(
                "Fallacy recall lift: widenet=%d, perarg=%d, merged=%d",
                len(wide_fallacies),
                len(per_arg_fallacies),
                len(merged),
            )
        except Exception as enrich_err:
            logger.warning(
                "Per-argument enrichment failed, keeping wide-net results only: %s",
                enrich_err,
            )

        # FB-35 (#1121): translate the descent budget-exceeded marker (from the
        # wide-net run and/or the per-argument enrichment) into the canonical
        # degraded/last_error signal so the report + state layer marks the phase
        # degraded. Fail-loud (anti-theater #1019): the fallacy list may be
        # PARTIAL — the agentic descent was cost-capped, never silently truncated.
        _widenet_capped = bool(result.get("descent_budget_exceeded"))
        _perarg_capped = bool(
            "per_arg_result" in locals()
            and isinstance(per_arg_result, dict)
            and per_arg_result.get("descent_budget_exceeded")
        )
        if _widenet_capped or _perarg_capped:
            result["degraded"] = True
            _capped_sources = []
            if _widenet_capped:
                _capped_sources.append("wide-net")
            if _perarg_capped:
                _capped_sources.append("per-argument")
            result["last_error"] = (
                "descent budget exceeded (" + "+".join(_capped_sources) + " capped)"
            )
            logger.warning(
                "Fallacy descent cost-capped (FB-35 #1121): %s — results are partial",
                "+".join(_capped_sources),
            )

        # Trace entry for hierarchical fallacy specialist
        _state = context.get("_state_object")
        if _state is not None and result.get("fallacies"):
            _fallacies = result.get("fallacies", [])
            _top_family = ""
            if _fallacies and isinstance(_fallacies[0], dict):
                _top_family = str(
                    _fallacies[0].get("fallacy_type", _fallacies[0].get("type", ""))
                )
            _degraded_note = (
                " [DEGRADED: descent budget exceeded — partial coverage]"
                if result.get("degraded")
                else ""
            )
            _state.add_trace_entry(
                phase="hierarchical_fallacy",
                agent="FallacyDetector",
                reacts_to=["extract"],
                summary=f"{len(_fallacies)} sophismes détectés — famille dominante: {_top_family or 'mixte'}. Analyse taxonomique hiérarchique avec enrichissement per-argument.{_degraded_note}",
            )
        return result  # type: ignore[no-any-return]

    except (ImportError, RuntimeError, ValueError) as e:
        # Anti-theater mandate (#1019 / RA-1 #1046): fail loud, do NOT silently
        # return empty results that look like "no fallacies found". Callers must
        # handle the absence explicitly (skip the phase, mark degraded, etc.)
        # rather than treating an empty list as a legitimate analysis outcome.
        logger.error(
            "Hierarchical fallacy detection unavailable (tier=%s): %s — FAILING LOUD per #1019/#1046",
            context.get("fallacy_tier", "llm"),
            e,
        )
        raise RuntimeError(
            f"FALLACY_DETECTION_UNAVAILABLE: tier={context.get('fallacy_tier', 'llm')}, reason={e}"
        ) from e
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


def _merge_fallacy_results(
    wide_fallacies: List[Dict[str, Any]],
    per_arg_fallacies: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge wide-net and per-argument fallacy results, deduplicating by taxonomy_pk.

    Keeps the highest-confidence entry for each unique taxonomy_pk.
    Wide-net results are kept as the floor; per-argument extras are added
    only if their taxonomy_pk is not already present.
    """
    seen: Dict[str, Dict[str, Any]] = {}
    for f in wide_fallacies:
        if not isinstance(f, dict):
            continue
        pk = str(f.get("taxonomy_pk") or f.get("fallacy_type") or "")
        if pk and pk not in seen:
            seen[pk] = f
        elif pk and f.get("confidence", 0) > seen.get(pk, {}).get("confidence", 0):
            seen[pk] = f

    for f in per_arg_fallacies:
        if not isinstance(f, dict):
            continue
        pk = str(f.get("taxonomy_pk") or f.get("fallacy_type") or "")
        if not pk:
            continue
        if pk not in seen:
            seen[pk] = f
        elif f.get("confidence", 0) > seen.get(pk, {}).get("confidence", 0):
            seen[pk] = f

    return list(seen.values())


# ---------------------------------------------------------------------------
# Fallacy-tier invoke callables (taxonomy / hybrid / full)
# ---------------------------------------------------------------------------


async def _invoke_taxonomy_only_fallacy(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Taxonomy-only fallacy detection — no LLM, CI-safe.

    Uses TaxonomySophismDetector for lexical matching against the 400-entry
    CSV taxonomy. Zero API cost. Suitable for quick scans and CI pipelines.
    """
    taxonomy_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "argumentum_fallacies_taxonomy.csv",
    )
    if not os.path.isfile(taxonomy_path):
        return {
            "fallacies": [],
            "extraction_method": "skipped",
            "reason": "taxonomy file not found",
        }

    try:
        from argumentation_analysis.agents.core.informal.taxonomy_sophism_detector import (
            get_global_detector,
        )

        detector = get_global_detector()
        sophisms = detector.detect_sophisms_from_taxonomy(input_text)

        fallacies = []
        for s in sophisms:
            fallacies.append(
                {
                    "fallacy_type": s.get("nom_vulgarise", s.get("type", "unknown")),
                    "type": s.get("nom_vulgarise", s.get("type", "unknown")),
                    "confidence": s.get("confidence", 0.0),
                    "description": s.get("description", ""),
                    "taxonomy_pk": s.get("key", s.get("nom_vulgarise", "")),
                }
            )

        return {
            "fallacies": fallacies,
            "extraction_method": "taxonomy_lexical",
            "tier": "taxonomy",
        }

    except Exception as e:
        logger.warning("Taxonomy-only fallacy detection failed: %s", e)
        return {
            "fallacies": [],
            "extraction_method": "unavailable",
            "error": str(e),
        }


async def _invoke_hybrid_fallacy(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Hybrid fallacy detection — neural+symbolic, optional NLI, no OpenAI.

    Uses FrenchFallacyAdapter with LLM layers disabled. Leverages symbolic
    pattern matching (spaCy) and optionally the NLI zero-shot model.
    """
    try:
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True,
            enable_nli=False,  # NLI needs model download — keep off for CI
            enable_llm=False,
            enable_self_hosted_llm=False,
            enable_camembert=False,
        )
        result = adapter.detect(input_text)

        fallacies = []
        if isinstance(result, dict):
            for f in result.get("fallacies", result.get("detections", [])):
                if isinstance(f, dict):
                    fallacies.append(
                        {
                            "fallacy_type": f.get(
                                "type", f.get("fallacy_type", "unknown")
                            ),
                            "type": f.get("type", f.get("fallacy_type", "unknown")),
                            "confidence": f.get("confidence", 0.0),
                            "description": f.get(
                                "description", f.get("explanation", "")
                            ),
                            "source_tier": f.get("tier", "hybrid"),
                        }
                    )
        elif isinstance(result, list):
            for f in result:
                if isinstance(f, dict):
                    fallacies.append(
                        {
                            "fallacy_type": f.get(
                                "type", f.get("fallacy_type", "unknown")
                            ),
                            "type": f.get("type", f.get("fallacy_type", "unknown")),
                            "confidence": f.get("confidence", 0.0),
                            "description": f.get(
                                "description", f.get("explanation", "")
                            ),
                            "source_tier": f.get("tier", "hybrid"),
                        }
                    )

        return {
            "fallacies": fallacies,
            "extraction_method": "hybrid_neural_symbolic",
            "tier": "hybrid",
        }

    except ImportError as e:
        logger.warning("FrenchFallacyAdapter unavailable: %s", e)
        return {
            "fallacies": [],
            "extraction_method": "unavailable",
            "error": str(e),
        }
    except Exception as e:
        logger.warning("Hybrid fallacy detection failed: %s", e)
        return {
            "fallacies": [],
            "extraction_method": "unavailable",
            "error": str(e),
        }


async def _invoke_full_fallacy(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Full fallacy detection — all strategies merged, deduplicated.

    Runs the LLM iterative deepening pass (default) + hybrid pass, then
    merges results by taxonomy_pk, keeping highest confidence per unique
    fallacy. Maximum recall at maximum cost.
    """
    # Run LLM pass (default tier) — may raise RuntimeError if unavailable
    llm_context = {**context, "fallacy_tier": "llm"}
    llm_result: Dict[str, Any] = {}
    try:
        llm_result = await _invoke_hierarchical_fallacy(input_text, llm_context)
        llm_fallacies = llm_result.get("fallacies", [])
    except RuntimeError:
        logger.warning(
            "LLM tier unavailable in full merge — proceeding with hybrid only"
        )
        llm_fallacies = []

    # Run hybrid pass
    hybrid_result = await _invoke_hybrid_fallacy(input_text, context)
    hybrid_fallacies = hybrid_result.get("fallacies", [])

    # Merge by taxonomy_pk (or fallacy_type as fallback), keep highest confidence
    merged = _merge_fallacy_results(llm_fallacies, hybrid_fallacies)

    logger.info(
        "Full fallacy merge: llm=%d, hybrid=%d, merged=%d",
        len(llm_fallacies),
        len(hybrid_fallacies),
        len(merged),
    )

    # FB-35 (#1121): propagate the descent budget-exceeded / degraded signal
    # from the LLM tier into the full-merged result so the report + state layer
    # sees it (the hybrid pass is bounded and cannot trip the agentic descent
    # breaker; only the LLM tier can).
    full_result: Dict[str, Any] = {
        "fallacies": merged,
        "extraction_method": "full_merged",
        "tier": "full",
        "llm_count": len(llm_fallacies),
        "hybrid_count": len(hybrid_fallacies),
    }
    if llm_result.get("descent_budget_exceeded") or llm_result.get("degraded"):
        full_result["descent_budget_exceeded"] = bool(
            llm_result.get("descent_budget_exceeded")
        )
        full_result["degraded"] = True
        full_result["last_error"] = llm_result.get(
            "last_error", "descent budget exceeded"
        )
    # FB-35 (#1121): propagate the descent-call diagnostic so verification can
    # confirm the breaker's margin on normal corpora (calls made vs budget).
    if "descent_calls_made" in llm_result:
        full_result["descent_calls_made"] = llm_result["descent_calls_made"]
    return full_result


async def _invoke_hierarchical_fallacy_per_argument(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Parent harness: run hierarchical fallacy detection per-argument in parallel (#578 tier 3).

    Extracts individual arguments from the input text, then invokes
    FallacyWorkflowPlugin.run_guided_analysis() in parallel via asyncio.gather
    for each argument. This is the tier 3 parent harness that complements
    tier 1 (wide-net Phase 1) and tier 2 (parallel deepening Phase 2) inside
    the plugin itself.

    Falls back to single-text analysis if argument extraction is unavailable.
    """
    taxonomy_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "argumentum_fallacies_taxonomy.csv",
    )
    if not os.path.isfile(taxonomy_path):
        logger.warning(
            "Taxonomy CSV not found at %s — per-argument fallacy detection skipped",
            taxonomy_path,
        )
        return {
            "fallacies": [],
            "exploration_method": "skipped",
            "reason": "taxonomy file not found",
        }

    try:
        from semantic_kernel.kernel import Kernel
        from argumentation_analysis.core.llm_service import create_llm_service
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        # Extract individual arguments from context or input text
        arguments = _extract_arguments_for_parallel(input_text, context)

        if not arguments:
            # FB-36 (#1123): do NOT recurse into _invoke_hierarchical_fallacy
            # here. This per-argument pass is invoked AFTER the wide-net "llm"
            # descent already ran (its results are merged by the caller at the
            # ``_merge_fallacy_results`` site), so re-entering the wide-net path
            # is redundant — and worse, that path calls THIS function again, so
            # with no extractable arguments (no state args, no
            # ``phase_extract_output``, no ``\n\n`` paragraph breaks — e.g. an
            # encrypted corpus loaded as a single block) it recurses
            # indefinitely. That infinite loop is the doc_A spectacular+full
            # >2h hang (ruled out of the descent by FB-35, isolated here).
            # Return fail-loud instead: the caller keeps the wide-net fallacies
            # and the per-arg pass is marked degraded (anti-theater #1019).
            logger.warning(
                "Per-argument fallacy harness found no extractable arguments "
                "(no state args / no phase_extract_output / no \\n\\n paragraph "
                "breaks) — skipping per-argument pass fail-loud (FB-36 #1123, "
                "no recursion). In a full pipeline this means the extract "
                "phase produced no splittable arguments for this input; the "
                "wide-net result is retained by the caller."
            )
            return {
                "fallacies": [],
                "exploration_method": "per_argument_skipped_no_args",
                "per_argument_skipped": True,
                "degraded": True,
                "last_error": (
                    "no arguments extracted for per-argument fallacy "
                    "(wide-net result retained by caller)"
                ),
            }

        logger.info(
            "Parent harness: running parallel fallacy detection on %d arguments",
            len(arguments),
        )

        # Route through create_llm_service so the OpenRouter toggle applies (see
        # _invoke_hierarchical_fallacy). Build the service once and share it across
        # the per-argument plugin instances; each keeps its own master_kernel for
        # isolation. force_authentic=True preserves the always-real behavior.
        shared_llm_service = create_llm_service(
            service_id="fallacy_widenet_perarg",
            force_authentic=True,
        )

        # Create plugin instances — one per argument for isolation
        async def _analyze_single_arg(arg_text: str, arg_id: str) -> Dict[str, Any]:
            """Analyze a single argument with its own plugin instance.

            On timeout, retry once with the fast one-shot path before giving
            up (#652 Track II). The full guided analysis (wide-net + iterative
            deepening) is several LLM calls and exceeds budget under API
            latency; returning empty here directly starves the report's fallacy
            section AND the convergence layer (fallacy is one of its inputs).
            The one-shot is a single taxonomy-mapped call, so it recovers
            recall cheaply when the API is slow.

            D1a (#1167): enrich every emitted fallacy with the grounded arg
            link so the state writer (_write_hierarchical_fallacy_to_state)
            can attach it to arg_1..N. The plugin's IdentifiedFallacy model
            has ``problematic_quote`` but the descent never populates it and
            the confirm_fallacy tool emits no quote; without this enrichment
            the fallacies arrive orphaned ({type, justification} only) and
            the writer's text-match fallbacks cannot link them. We attach:
              - ``target_argument`` = arg_id (a real id from state.identified_
                arguments, or "arg_N" from the extract phase) — the writer
                resolves it by direct ID match;
              - ``problematic_quote`` = a verbatim span capped from the
                argument text (privacy: stays in-memory in the state, results
                are gitignored) — the writer's text-match fallback anchor.
            This surfaces what the descent already grounded (which argument
            it analyzed) — it does NOT fabricate family/target (anti-pendule).
            """

            def _enrich_fallacies(res: Dict[str, Any]) -> None:
                """Attach grounded arg link to each fallacy dict in-place."""
                fallacies = res.get("fallacies")
                if not isinstance(fallacies, list):
                    return
                # Verbatim span: cap to keep the quote a tight anchor (privacy +
                # match precision — the writer matches on desc[:60] prefixes).
                # NB: the field name ``problematic_quote`` matches the
                # IdentifiedFallacy schema, but here it is NOT the exact
                # fallacious phrase — it is a match anchor (the argument's
                # leading text) used by the writer for ID resolution only, and
                # is never persisted into the narrated report.
                quote_span = arg_text.strip()[:200]
                for f in fallacies:
                    if not isinstance(f, dict):
                        continue
                    # Do not overwrite an explicit plugin-provided target.
                    if not f.get("target_argument"):
                        f["target_argument"] = arg_id
                    if not f.get("problematic_quote") and quote_span:
                        f["problematic_quote"] = quote_span

            plugin = None
            try:
                master_kernel = Kernel()
                master_kernel.add_service(shared_llm_service)

                plugin = FallacyWorkflowPlugin(
                    master_kernel=master_kernel,
                    llm_service=shared_llm_service,
                    taxonomy_file_path=taxonomy_path,
                )

                result_json = await asyncio.wait_for(
                    plugin.run_guided_analysis(argument_text=arg_text),
                    timeout=120.0,
                )
                result: Dict[str, Any] = json.loads(result_json)
                result["source_arg_id"] = arg_id
                _enrich_fallacies(result)
                return result
            except asyncio.TimeoutError:
                logger.warning(
                    "Timeout analyzing argument %s — retrying with fast one-shot",
                    arg_id,
                )
                if plugin is not None:
                    try:
                        oneshot_json = await asyncio.wait_for(
                            plugin.run_guided_analysis(
                                argument_text=arg_text, use_one_shot=True
                            ),
                            timeout=45.0,
                        )
                        oneshot: Dict[str, Any] = json.loads(oneshot_json)
                        oneshot["source_arg_id"] = arg_id
                        oneshot["timed_out_fallback"] = True
                        _enrich_fallacies(oneshot)
                        return oneshot
                    except Exception as e:
                        logger.warning(
                            "One-shot fallback also failed for argument %s: %s",
                            arg_id,
                            e,
                        )
                return {"fallacies": [], "source_arg_id": arg_id, "timed_out": True}
            except Exception as e:
                logger.warning("Error analyzing argument %s: %s", arg_id, e)
                return {"fallacies": [], "source_arg_id": arg_id, "error": str(e)}

        # Parallel execution via asyncio.gather
        tasks = [
            _analyze_single_arg(arg_text, arg_id) for arg_id, arg_text in arguments
        ]
        per_arg_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate: collect all fallacies with source arg metadata
        all_fallacies = []
        total_iterations = 0
        methods_used = set()
        # FB-35 (#1121): surface if ANY per-argument descent tripped the global
        # call budget (each per-arg plugin instance has its own budget).
        any_descent_budget_exceeded = False
        for result in per_arg_results:
            if isinstance(result, Exception):
                logger.warning("Per-argument analysis error: %s", result)
                continue
            if isinstance(result, dict):
                if result.get("descent_budget_exceeded"):
                    any_descent_budget_exceeded = True
                fallacies = result.get("fallacies", [])
                source_arg_id = result.get("source_arg_id", "unknown")
                for f in fallacies:
                    if isinstance(f, dict):
                        f["source_arg_id"] = source_arg_id
                all_fallacies.extend(fallacies)
                total_iterations += result.get("total_iterations", 0)
                method = result.get("exploration_method", "")
                if method:
                    methods_used.add(method)

        # Dedup by (taxonomy_pk, source_arg_id) — keep highest confidence
        seen: Dict[tuple[str, str], Dict[str, Any]] = {}
        deduped: List[Dict[str, Any]] = []
        for f in all_fallacies:
            if not isinstance(f, dict):
                continue
            key: tuple[str, str] = (
                str(f.get("taxonomy_pk") or f.get("fallacy_type") or ""),
                str(f.get("source_arg_id") or ""),
            )
            if key in seen and seen[key].get("confidence", 0) >= f.get("confidence", 0):
                continue
            seen[key] = f
            deduped = [
                x
                for x in deduped
                if (
                    str(x.get("taxonomy_pk") or x.get("fallacy_type") or ""),
                    str(x.get("source_arg_id") or ""),
                )
                != key
            ]
            deduped.append(f)

        exploration_method = (
            "+".join(sorted(methods_used)) if methods_used else "per_argument_parallel"
        )

        logger.info(
            "Parent harness: %d fallacies from %d arguments (deduped to %d)",
            len(all_fallacies),
            len(arguments),
            len(deduped),
        )

        return {
            "fallacies": deduped,
            "total_iterations": total_iterations,
            "exploration_method": exploration_method,
            "extraction_method": exploration_method,
            "per_argument_count": len(arguments),
            "parallel_executed": True,
            "descent_budget_exceeded": any_descent_budget_exceeded,
        }

    except (ImportError, RuntimeError, ValueError) as e:
        # Anti-theater (#1019/#1046): fail loud. The caller (wide-net merge)
        # handles this gracefully — do not return empty that looks like "found nothing".
        logger.error(
            "Per-argument hierarchical fallacy unavailable (tier=%s): %s — FAILING LOUD",
            context.get("fallacy_tier", "llm"),
            e,
        )
        raise RuntimeError(
            f"PER_ARG_FALLACY_UNAVAILABLE: tier={context.get('fallacy_tier', 'llm')}, reason={e}"
        ) from e
    except Exception as e:
        import traceback

        logger.error(
            "Per-argument hierarchical fallacy detection failed:\n%s",
            traceback.format_exc(),
        )
        raise


def _extract_arguments_for_parallel(
    input_text: str, context: Dict[str, Any]
) -> List[tuple[str, str]]:
    """Extract individual argument texts from context for parallel processing.

    Looks for arguments in:
    1. context['_state_object'].identified_arguments (from pipeline state)
    2. context['extracted_arguments'] (from extraction phase output)
    3. Falls back to splitting input_text by paragraph breaks

    Returns list of (arg_id, arg_text) tuples. Max 10 arguments.
    """
    # Source 1: pipeline state object with identified_arguments
    state_obj = context.get("_state_object")
    if state_obj and hasattr(state_obj, "identified_arguments"):
        args = state_obj.identified_arguments
        if isinstance(args, dict) and args:
            result = []
            for arg_id, desc in list(args.items())[:10]:
                text = desc if isinstance(desc, str) else str(desc)
                if text and len(text.strip()) > 20:
                    result.append((arg_id, text.strip()))
            if result:
                return result

    # Source 2: extraction phase output (key matches phase_extract_output used by all other callables)
    extraction_output = context.get("phase_extract_output")
    if extraction_output and isinstance(extraction_output, dict):
        arguments = extraction_output.get("arguments", [])
        if arguments:
            result = []
            for i, arg in enumerate(arguments[:10]):
                text = arg.get("text", str(arg)) if isinstance(arg, dict) else str(arg)
                if text and len(text.strip()) > 20:
                    result.append((f"arg_{i+1}", text.strip()))
            if result:
                return result

    # Source 3: split by paragraph breaks (heuristic fallback)
    paragraphs = [p.strip() for p in input_text.split("\n\n") if p.strip()]
    if len(paragraphs) >= 2:
        return [
            (f"paragraph_{i+1}", p)
            for i, p in enumerate(paragraphs[:10])
            if len(p) > 20
        ]

    return []


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
            det_params = _get_determinism_params()
            # JJ #699: non-English dense text under-recalls (corpus B/DE extracts
            # ~2 args vs ~7/5 for A/C-EN), starving every downstream layer. The
            # English-only prompt gives the model no cue to analyze in the source
            # language. Detect the language (reusing the tested heuristic) and add
            # a language-aware instruction so non-English extraction reaches parity.
            lang_clause = ""
            try:
                from argumentation_analysis.orchestration.conversational_orchestrator import (
                    _detect_language,
                )

                _lang = _detect_language(input_text)
                _lang_names = {"de": "German", "fr": "French", "en": "English"}
                if _lang in _lang_names and _lang != "en":
                    lang_clause = (
                        f" The source text is in {_lang_names[_lang]}. Analyze it in "
                        f"its original language and extract ALL distinct arguments and "
                        f"claims with the SAME thoroughness as you would for English — "
                        f"do not under-extract because the text is non-English. Keep "
                        f"the 'text' descriptions in {_lang_names[_lang]}."
                    )
            except Exception:
                lang_clause = ""
            response = await _guarded_chat_completion(
                client,
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
                            + lang_clause
                            + " Respond with ONLY a JSON object:\n"
                            '{"arguments": [{"text": "arg description", "source_quote": "exact quote..."}], '
                            '"claims": [{"text": "claim description", "source_quote": "exact quote..."}], '
                            '"summary": "brief analysis summary"}'
                        ),
                    },
                    {"role": "user", "content": input_text[:3000]},
                ],
                **det_params,
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
                _extract_result = {
                    "arguments": arguments,
                    "claims": claims,
                    "fallacies": fallacies,
                    "summary": data.get("summary", ""),
                    "claim_count": len(claims),
                    "argument_count": len(arguments),
                    "source_length": len(input_text),
                    "extraction_method": "llm",
                }
                # Trace entry for fact extraction specialist
                _state = context.get("_state_object")
                if _state is not None:
                    _n_args = _extract_result.get("argument_count", 0)
                    _n_claims = _extract_result.get("claim_count", 0)
                    _state.add_trace_entry(
                        phase="extract",
                        agent="FactExtractor",
                        reacts_to=[],
                        summary=f"{_n_args} arguments et {_n_claims} claims identifiés — extraction LLM. Phase fondatrice du pipeline.",
                    )
                return _extract_result
    except Exception as e:
        logger.warning(f"LLM fact extraction failed, falling back to heuristic: {e}")

    # Heuristic fallback
    sentences = re.split(r"(?<=[.!?])\s+", input_text.strip())
    claims = [s.strip() for s in sentences if len(s.strip()) > 20]  # type: ignore[misc]
    _heuristic_result = {
        "arguments": [],
        "claims": claims,
        "fallacies": [],
        "summary": "",
        "claim_count": len(claims),
        "argument_count": 0,
        "source_length": len(input_text),
        "extraction_method": "heuristic",
    }
    # Trace entry for heuristic fact extraction
    _state = context.get("_state_object")
    if _state is not None and claims:
        _n_claims = len(claims)
        _state.add_trace_entry(
            phase="extract",
            agent="FactExtractor",
            reacts_to=[],
            summary=f"0 arguments, {_n_claims} claims — extraction heuristique (fallback). Pipeline initialisé sans LLM.",
        )
    return _heuristic_result


def _parse_json_from_llm(raw: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, handling markdown fences and noise."""
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            parsed: Dict[str, Any] = json.loads(text[start:end])
            return parsed
        except json.JSONDecodeError:
            pass
    return {}


async def _invoke_propositional_logic(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke propositional logic analysis — translate arguments to propositions.

    Uses a 2-pass coordinated pipeline when possible (#547):
      Pass 1: Extract shared atom inventory from full source text
      Pass 2: Generate per-argument formulas using ONLY shared atoms
    Falls back to on-the-fly NL translation, then template variables.

    If NL-to-logic translations are available from an upstream phase, uses
    those validated formulas. Otherwise falls back to template generation.
    (#208-H: wire NL-to-logic as pre-processing)
    """
    # Build propositional formulas from upstream arguments
    args = _extract_arguments_from_context(input_text, context)
    # #705 Track LL: upstream formulas (DAG path: context["formulas"] or the
    # nl_to_logic phase) are whole-text/complex and frequently fail Tweety. We
    # capture them separately and run the robust 2-pass coordinated generator
    # ALWAYS, then UNION the upstream extras on top — instead of letting the
    # upstream formulas short-circuit the generator. That short-circuit was the
    # asymmetry that made the sequential/DAG path lose PL/FOL to the zero-shot
    # baseline; the conversational path already wins because it always runs the
    # 2-pass. Per-formula Tweety isolation below keeps only parseable survivors,
    # so unioning the upstream extras can only add verified count, never lower it.
    upstream_formulas: List[str] = [
        str(f).strip() for f in (context.get("formulas") or []) if f
    ]
    formulas: Optional[List[str]] = None
    argument_mapping: Dict[str, str] = {}
    shared_atoms: List[str] = []

    # Retrieve state object for atomic_propositions storage
    state_obj = context.get("_state_object")

    # Track formula pipeline metrics (#655 Track MM)
    pl_metrics: Dict[str, int] = {
        "upstream_nl": 0,
        "pass1_atoms": 0,
        "pass2_candidates": 0,
        "fallback_nl": 0,
        "template": 0,
        "pre_sanitize": 0,
        "post_sanitize": 0,
        "post_tweety": 0,
        "wide_net_extras": 0,
        "isolation_survivors": 0,
    }

    if not formulas:
        # Ensure formulas is a list for mypy
        formulas = []
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
            # #705: capture upstream NL-to-logic formulas; do NOT short-circuit
            # the 2-pass — they are unioned in after the robust generator runs.
            upstream_formulas.extend(
                t["formula"].strip() for t in pl_translations if t.get("formula")
            )
            argument_mapping.update(
                {
                    t["formula"][:30]: t.get("original_text", "")[:60]
                    for t in pl_translations
                }
            )
            pl_metrics["upstream_nl"] = len(upstream_formulas)
            logger.info(
                f"Captured {len(upstream_formulas)} upstream NL-to-logic PL "
                f"formulas (unioned after 2-pass) (#705)"
            )
        # ── 2-pass coordinated pipeline (#547) — always runs now (#705 LL).
        # Pass 1 (atom inventory) → Pass 2 (formulas using only shared atoms).
        if not formulas:
            try:
                import json as _json

                # Honors the OpenRouter toggle via _get_openai_client.
                client, model_id = _get_openai_client()
                if client is not None and input_text and len(input_text) > 100:

                    # ── Pass 1: Atom inventory from full source text ──
                    pass1_prompt = (
                        "You are an expert in propositional logic. Your task is to identify "
                        "atomic propositions (basic facts) in the given text.\n\n"
                        "Output a JSON object with a single key 'propositions' mapping to a "
                        "list of strings. Each string is an atomic proposition name in "
                        "lowercase snake_case (e.g. 'is_mortal', 'foreign_threat').\n\n"
                        f"Text:\n{input_text[:4000]}"
                    )
                    det_params = _get_determinism_params()
                    pass1_resp = await _guarded_chat_completion(
                        client,
                        model=model_id,
                        messages=[{"role": "user", "content": pass1_prompt}],
                        **det_params,
                    )
                    pass1_raw = pass1_resp.choices[0].message.content or ""

                    # Parse propositions
                    props_data = _parse_json_from_llm(pass1_raw)
                    raw_atoms = props_data.get("propositions", [])

                    # Validate atoms: must be alphanumeric + underscore
                    valid_atoms = [
                        a for a in raw_atoms if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", a)
                    ]
                    if valid_atoms:
                        shared_atoms = valid_atoms
                        pl_metrics["pass1_atoms"] = len(shared_atoms)
                        logger.info(
                            f"PL 2-pass Pass 1: {len(shared_atoms)} atoms extracted from full text"
                        )

                        # Store in state
                        if state_obj is not None and hasattr(
                            state_obj, "atomic_propositions"
                        ):
                            source_id = context.get("source_metadata", {}).get(
                                "opaque_id", "default"
                            )
                            state_obj.atomic_propositions[source_id] = shared_atoms

                    # ── Pass 2: Parallel batched formula generation (#729 Track XX) ──
                    if shared_atoms and args:
                        atoms_json = _json.dumps(
                            {"propositions": shared_atoms}, indent=2
                        )
                        _pl_batch_size = 3
                        _pl_targets = args[:10]

                        async def _pl_batch_coro(_batch: list[str]) -> list[str]:
                            if len(_batch) == 1:
                                _texts_block = f"Text:\n{_batch[0][:2000]}"
                            else:
                                _parts = [
                                    f"Text {_i+1}:\n{_a[:1500]}"
                                    for _i, _a in enumerate(_batch)
                                ]
                                _texts_block = "\n\n".join(_parts)
                            _prompt = (
                                "You are an expert in propositional logic. Translate the "
                                f"{'texts' if len(_batch) > 1 else 'text'} below into logical "
                                "formulas using ONLY the provided atomic propositions.\n\n"
                                "Rules:\n"
                                "- Use ONLY the propositions from the list below. Do NOT invent new ones.\n"
                                "- Operators: ! (not), && (and), || (or), => (implies), <=> (iff)\n"
                                "- Output a JSON object with a single key 'formulas' mapping to a "
                                "list of formula strings.\n\n"
                                f"{_texts_block}\n\n"
                                f"Allowed propositions:\n{atoms_json}"
                            )
                            _resp = await _guarded_chat_completion(
                                client,
                                model=model_id,
                                messages=[{"role": "user", "content": _prompt}],
                                **det_params,
                            )
                            _raw = _resp.choices[0].message.content or ""
                            _pl_out: list[str] = _parse_json_from_llm(_raw).get(
                                "formulas", []
                            )
                            return _pl_out

                        _pl_coros = [
                            _pl_batch_coro(_pl_targets[_bi : _bi + _pl_batch_size])
                            for _bi in range(0, len(_pl_targets), _pl_batch_size)
                        ]
                        _pl_results = await asyncio.gather(
                            *_pl_coros, return_exceptions=True
                        )
                        for _idx, _res in enumerate(_pl_results):
                            if isinstance(_res, BaseException):
                                logger.debug(f"PL Pass 2 batch {_idx} failed: {_res}")
                                continue
                            for f in _res:
                                if f and f not in formulas:
                                    formulas.append(f)
                                    _src = _pl_targets[_idx * _pl_batch_size][:60]
                                    argument_mapping[f[:30]] = _src

                        if formulas:
                            pl_metrics["pass2_candidates"] = len(formulas)
                            logger.info(
                                f"PL 2-pass Pass 2: {len(formulas)} formulas generated "
                                f"with {len(shared_atoms)} shared atoms"
                            )

                        # ── Whole-text formula pass (wide-net) ──
                        # Generate formulas from full text to capture
                        # structural/tonal patterns missed by per-arg analysis.
                        per_arg_set = set(formulas)
                        try:
                            wt_prompt = (
                                "You are an expert in propositional logic. "
                                "Translate the FULL text below into logical formulas "
                                "using ONLY the provided atomic propositions.\n\n"
                                "Focus on overarching logical structure: implications "
                                "between major claims, contradictions, conditional chains.\n"
                                "Rules:\n"
                                "- Use ONLY the propositions from the list below.\n"
                                "- Operators: ! (not), && (and), || (or), => (implies), <=> (iff)\n"
                                "- Output JSON with key 'formulas' (list of strings).\n\n"
                                f"Text:\n{input_text[:4000]}\n\n"
                                f"Allowed propositions:\n{_json.dumps({'propositions': shared_atoms}, indent=2)}"
                            )
                            wt_resp = await _guarded_chat_completion(
                                client,
                                model=model_id,
                                messages=[{"role": "user", "content": wt_prompt}],
                                **det_params,
                            )
                            wt_raw = wt_resp.choices[0].message.content or ""
                            wt_data = _parse_json_from_llm(wt_raw)
                            wt_formulas = wt_data.get("formulas", [])
                            wide_net_extras = 0
                            for f in wt_formulas:
                                if f and f not in per_arg_set and f not in formulas:
                                    formulas.append(f)
                                    argument_mapping[f[:30]] = input_text[:60]
                                    wide_net_extras += 1
                            if wide_net_extras:
                                pl_metrics["wide_net_extras"] = wide_net_extras
                                logger.info(
                                    f"PL whole-text pass: {wide_net_extras} extra formulas"
                                )
                        except Exception as wt_err:
                            logger.debug(f"PL whole-text pass unavailable: {wt_err}")
            except Exception as e:
                logger.debug(f"PL 2-pass pipeline unavailable: {e}")

            # #705 Track LL: union upstream complex formulas (nl_to_logic /
            # context["formulas"]) on top of the robust 2-pass formulas. The
            # per-formula Tweety isolation below keeps only parseable ones, so
            # this can only add verified survivors, never lower the count.
            if formulas is None:
                formulas = []
            for f in upstream_formulas:
                if f and f not in formulas:
                    formulas.append(f)

            # Fallback: on-the-fly NL translation only if nothing produced yet
            if not formulas:
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
                        pl_metrics["fallback_nl"] = len(valid)
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
            pl_metrics["template"] = len(prop_vars)
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

    # Sanitize formulas for Tweety compatibility (#537)
    pl_metrics["pre_sanitize"] = len(formulas)
    try:
        from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
            PLFormulaSanitizer,
        )

        sanitizer = PLFormulaSanitizer()
        san_result = sanitizer.sanitize_batch(formulas)
        if san_result.sanitized_formulas:
            pl_metrics["post_sanitize"] = len(san_result.sanitized_formulas)
            logger.info(
                f"PL sanitizer: {san_result.total_sanitized}/{san_result.total_input} "
                f"formulas sanitized"
            )
            formulas = san_result.sanitized_formulas
            # Store symbol mapping for interpretation
            if san_result.symbol_mapping:
                argument_mapping.update(
                    {v: k for k, v in san_result.symbol_mapping.items()}
                )
    except Exception as san_err:
        logger.debug(f"PL sanitizer unavailable ({san_err}), using raw formulas")

    # Bind bridge outside the try so the except isolation loop can reference it
    # even if TweetyBridge import/construction itself raises (#697 Track HH).
    bridge = None
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge()
        belief_set_str = "\n".join(str(f) for f in formulas)
        # #1208 (FP-10): use the detailed consistency API so the REAL PySAT
        # model (named proposition -> bool assignment) is persisted, not the
        # fabricated ``{p1: True, ...}`` placeholder that silently dropped the
        # solver witness. Also exposes the axiom/query counts the state
        # contract expects.
        is_consistent, sat_model, msg = await asyncio.to_thread(
            bridge.check_consistency_detailed, belief_set_str, "propositional"
        )
        pl_metrics["post_tweety"] = len(formulas)
        # Fallback model only when PySAT returned no structured witness (e.g.
        # Tweety-fallback path or UNSAT). Empty dict is honest for UNSAT.
        persisted_model = sat_model if isinstance(sat_model, dict) else {}
        return {
            "formulas": formulas,
            "satisfiable": bool(is_consistent),
            "model": persisted_model,
            "axiom_count": len(formulas),
            "query_count": 0,  # PL consistency is a satisfiability check (no entailment query)
            "message": msg,
            "logic_type": "propositional",
            "argument_mapping": argument_mapping
            or {f"p{i+1}": a[:60] for i, a in enumerate(args)},
            "pl_metrics": pl_metrics,
        }
    except Exception as e:
        # Per-formula isolation retry: one bad formula should not kill the batch.
        # Parse each formula individually and keep only those accepted by Tweety.
        logger.warning(
            f"PL Tweety batch parse failed ({e}). "
            f"Attempting per-formula isolation with {len(formulas)} formulas."
        )
        valid_formulas = []
        if bridge is not None:
            for formula in formulas:
                try:
                    single_bs = str(formula)
                    await asyncio.to_thread(
                        bridge.check_consistency, single_bs, "propositional"
                    )
                    valid_formulas.append(formula)
                except Exception:
                    logger.debug(f"PL formula rejected by Tweety: {formula}")

        if valid_formulas:
            pl_metrics["post_tweety"] = len(valid_formulas)
            pl_metrics["isolation_survivors"] = len(valid_formulas)
            logger.info(
                f"PL per-formula isolation: {len(valid_formulas)}/{len(formulas)} "
                f"formulas accepted by Tweety"
            )
            return {
                "formulas": valid_formulas,
                "satisfiable": True,
                "model": {f"p{i+1}": True for i in range(len(args))},
                "logic_type": "propositional",
                "argument_mapping": argument_mapping
                or {f"p{i+1}": a[:60] for i, a in enumerate(args)},
                "isolation_retry": True,
                "rejected_count": len(formulas) - len(valid_formulas),
                "pl_metrics": pl_metrics,
            }

        # All formulas failed — fail-loud (#1019, RA-8 #1053)
        pl_metrics["post_tweety"] = 0
        raise RuntimeError(
            "Propositional logic analysis unavailable: all Tweety solvers failed "
            f"for {len(formulas)} formulas. JVM/Tweety required."
        )


async def _invoke_fol_reasoning(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke first-order logic analysis — translate arguments to FOL predicates.

    If NL-to-logic translations are available from an upstream phase, uses
    those validated formulas. Otherwise falls back to template generation.
    (#208-H: wire NL-to-logic as pre-processing)
    """
    # RA-4 #1049 item 3: inject strategic directives for LLM-guided FOL translation
    _strat_text_fol, _strat_ids_fol = _get_strategic_directives(context)
    if _strat_text_fol:
        input_text = f"{_strat_text_fol}\n\n{input_text}"

    args = _extract_arguments_from_context(input_text, context)
    # #705 Track LL: capture upstream FOL formulas (DAG nl_to_logic /
    # context["formulas"]) separately and run the robust 2-pass generator
    # ALWAYS, then UNION the upstream extras — mirrors the PL fix so the
    # sequential/DAG path stops losing FOL to the zero-shot baseline. Per-formula
    # Tweety isolation keeps only parseable survivors.
    upstream_formulas: List[str] = [
        str(f).strip() for f in (context.get("formulas") or []) if f
    ]
    formulas: Optional[List[str]] = None
    fol_metadata_shared: Dict[str, Any] = {}
    # #900/#939: Default to eprover (robust), tweety is fallback of last resort
    fol_solver_choice = context.get("fol_solver", "eprover")
    fol_metadata_shared["fol_solver"] = fol_solver_choice
    if fol_solver_choice != "eprover":
        logger.info(
            f"FOL solver override: {fol_solver_choice} (parametric selector --fol-solver)"
        )

    # Retrieve state object for fol_shared_signature storage
    state_obj = context.get("_state_object")

    # Track FOL formula pipeline metrics (#655 Track MM)
    fol_metrics: Dict[str, int] = {
        "upstream_nl": 0,
        "pass1_sorts": 0,
        "pass1_predicates": 0,
        "pass2_candidates": 0,
        "fallback_nl": 0,
        "template": 0,
        "pre_sanitize": 0,
        "post_sanitize": 0,
        "pre_tweety": 0,
        "post_tweety": 0,
        "isolation_survivors": 0,
    }

    if not formulas:
        # Ensure formulas is a list for mypy
        formulas = []
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
            # #705: capture upstream NL-to-logic formulas; do NOT short-circuit
            # the 2-pass — they are unioned in after the robust generator runs.
            for t in fol_translations:
                # FOL formulas may be semicolon-separated
                for f in t["formula"].split(";"):
                    f = f.strip()
                    if f and f not in upstream_formulas:
                        upstream_formulas.append(f)
            logger.info(
                f"Captured {len(upstream_formulas)} upstream NL-to-logic FOL "
                f"formulas (unioned after 2-pass) (#705)"
            )
        # ── FOL 2-pass coordinated pipeline (#544) — always runs (#705 LL).
        # Pass 1: shared signature (sorts/predicates/constants) from full text.
        # Pass 2: per-argument formulas using ONLY the shared signature.
        if not formulas:
            try:
                # Honors the OpenRouter toggle via _get_openai_client.
                client, model_id = _get_openai_client()
                if client is not None and input_text and len(input_text) > 100:

                    # ── Pass 1: Shared FOL signature from full text ──
                    pass1_prompt = (
                        "You are a formal logic expert. Analyze the text and extract a "
                        "first-order logic signature.\n\n"
                        "Output a JSON object with:\n"
                        '- "sorts": dict mapping sort_name -> list of constant names '
                        '(e.g. {"Person": ["socrates", "plato"]})\n'
                        '- "predicates": dict mapping pred_name -> list of arg sort names '
                        '(e.g. {"Mortal": ["Person"], "Human": ["Person"]})\n'
                        '- "constants": dict mapping const_name -> description '
                        '(e.g. {"socrates": "the philosopher"})\n\n'
                        "Rules:\n"
                        "- Sorts: group related constants (Person, Country, etc.)\n"
                        "- Predicates: CamelCase, list arg sorts\n"
                        "- Constants: lowercase\n"
                        '- If unsure about sort, use "Thing"\n\n'
                        f"Text:\n{input_text[:4000]}"
                    )
                    det_params = _get_determinism_params()
                    pass1_resp = await _guarded_chat_completion(
                        client,
                        model=model_id,
                        messages=[{"role": "user", "content": pass1_prompt}],
                        **det_params,
                    )
                    pass1_raw = pass1_resp.choices[0].message.content or ""

                    sig_data = _parse_json_from_llm(pass1_raw)
                    sorts = sig_data.get("sorts", {})
                    predicates = sig_data.get("predicates", {})
                    constants_raw = sig_data.get("constants", {})

                    if sorts or constants_raw:
                        if not sorts and constants_raw:
                            sorts = {"Thing": list(constants_raw.keys())}
                        fol_metrics["pass1_sorts"] = len(sorts)
                        fol_metrics["pass1_predicates"] = len(predicates)
                        fol_metadata_shared = {
                            "sorts": sorts,
                            "predicates": predicates,
                            "constants_raw": constants_raw,
                            "fol_solver": fol_solver_choice,
                        }
                        logger.info(
                            f"FOL 2-pass Pass 1: {len(sorts)} sorts, "
                            f"{len(predicates)} predicates, "
                            f"{sum(len(v) for v in sorts.values())} constants extracted"
                        )

                        # Store in state
                        if state_obj is not None and hasattr(
                            state_obj, "fol_shared_signature"
                        ):
                            source_id = context.get("source_metadata", {}).get(
                                "opaque_id", "default"
                            )
                            state_obj.fol_shared_signature[source_id] = (
                                fol_metadata_shared
                            )

                        # ── Pass 2: Parallel batched FOL formula generation (#729) ──
                        if args:
                            sig_json = json.dumps(sig_data, indent=2)
                            _fol_batch_size = 3
                            _fol_targets = args[:10]

                            async def _fol_batch_coro(_batch: list[str]) -> list[str]:
                                if len(_batch) == 1:
                                    _texts_block = f"Text:\n{_batch[0][:2000]}"
                                else:
                                    _parts = [
                                        f"Text {_i+1}:\n{_a[:1500]}"
                                        for _i, _a in enumerate(_batch)
                                    ]
                                    _texts_block = "\n\n".join(_parts)
                                _prompt = (
                                    "You are a formal logic expert. Translate the "
                                    f"{'texts' if len(_batch) > 1 else 'text'} below into "
                                    "first-order logic formulas using ONLY the "
                                    "provided signature.\n\n"
                                    "Rules:\n"
                                    "- Use ONLY the predicates and constants from the signature\n"
                                    "- Predicates: CamelCase, constants: lowercase\n"
                                    "- Quantifiers: forall X: (...), exists X: (...)\n"
                                    "- Operators: ! (not), && (and), || (or), => (implies)\n"
                                    "- Output JSON with key 'formulas' (list of formula strings)\n\n"
                                    f"{_texts_block}\n\n"
                                    f"Signature:\n{sig_json}"
                                )
                                _resp = await _guarded_chat_completion(
                                    client,
                                    model=model_id,
                                    messages=[{"role": "user", "content": _prompt}],
                                    **det_params,
                                )
                                _raw = _resp.choices[0].message.content or ""
                                _fol_out: list[str] = _parse_json_from_llm(_raw).get(
                                    "formulas", []
                                )
                                return _fol_out

                            _fol_coros = [
                                _fol_batch_coro(
                                    _fol_targets[_bi : _bi + _fol_batch_size]
                                )
                                for _bi in range(0, len(_fol_targets), _fol_batch_size)
                            ]
                            _fol_results = await asyncio.gather(
                                *_fol_coros, return_exceptions=True
                            )
                            for _idx, _res in enumerate(_fol_results):
                                if isinstance(_res, BaseException):
                                    logger.debug(
                                        f"FOL Pass 2 batch {_idx} failed: {_res}"
                                    )
                                    continue
                                for f in _res:
                                    f = (
                                        f.strip()
                                        if isinstance(f, str)
                                        else str(f).strip()
                                    )
                                    if f and f not in formulas:
                                        formulas.append(f)

                            if formulas:
                                fol_metrics["pass2_candidates"] = len(formulas)
                                logger.info(
                                    f"FOL 2-pass Pass 2: {len(formulas)} formulas generated "
                                    f"with shared signature"
                                )
            except Exception as e:
                logger.debug(f"FOL 2-pass pipeline unavailable: {e}")

            # #705 Track LL: union upstream complex FOL formulas on top of the
            # robust 2-pass formulas. Per-formula Tweety isolation (below) keeps
            # only parseable survivors, so this can only add verified count.
            if formulas is None:
                formulas = []
            for f in upstream_formulas:
                if f and f not in formulas:
                    formulas.append(f)

            # Fallback: on-the-fly NL translation only if nothing produced yet
            if not formulas:
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
            fol_metrics["template"] = len(args)
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

    # Bind bridge outside the try so the except isolation loop can reference it
    # even if TweetyBridge import/construction itself raises (#697 Track HH).
    bridge = None
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        bridge = TweetyBridge()

        # Convert Unicode FOL operators to ASCII before signature extraction (#677)
        fol_metrics["pre_sanitize"] = len(formulas)
        formulas = [FOLLogicAgent.unicode_to_ascii_fol(f) for f in formulas]

        # Sanitize formula identifiers to match signature naming (#677)
        # extract_fol_metadata builds sanitized constant_map/predicate_map;
        # apply those mappings to the raw formulas so identifiers match.
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        fol_signature = meta.get("signature_lines", [])
        constant_map = meta.get("constant_map", {})
        predicate_map = meta.get("predicate_map", {})
        if constant_map or predicate_map:
            sanitized_formulas = []
            for f in formulas:
                sf = f
                # Replace predicates first (longer names first to avoid partial matches)
                for orig, safe in sorted(
                    predicate_map.items(), key=lambda x: -len(x[0])
                ):
                    sf = re.sub(r"\b" + re.escape(orig) + r"\b", safe, sf)
                # Replace constants (longer names first)
                for orig, safe in sorted(
                    constant_map.items(), key=lambda x: -len(x[0])
                ):
                    sf = re.sub(r"\b" + re.escape(orig) + r"\b", safe, sf)
                sanitized_formulas.append(sf)
            formulas = sanitized_formulas
        fol_metrics["post_sanitize"] = len(formulas)

        belief_set_str = "\n".join(str(f) for f in fol_signature + [""] + formulas)
        fol_metrics["pre_tweety"] = len(formulas)
        is_consistent, msg = await asyncio.to_thread(
            bridge.check_consistency, belief_set_str, "first_order"
        )
        fol_metrics["post_tweety"] = len(formulas)
        # FP-6 #1197: pass the handler's tri-state through unchanged. The handler
        # (fol_handler.check_consistency, FP-3 #1192) returns None on reasoner OOM /
        # failure = "could not compute". `bool(None)` would fabricate that into a
        # definite `consistent: False` ("KB is inconsistent") — théâtre regrowing one
        # layer above the handler (R405). None ⇒ unverified (confidence 0.0), True ⇒
        # consistent (0.8), False ⇒ a real inconsistency verdict (0.4). (#1019 fail-loud)
        return {
            "formulas": formulas,
            "fol_signature": fol_signature,
            "fol_metadata": meta,
            "consistent": is_consistent,
            "inferences": inferences,
            "confidence": (
                0.8
                if is_consistent is True
                else (0.0 if is_consistent is None else 0.4)
            ),
            "message": msg,
            "logic_type": "first_order",
            "argument_count": len(args),
            "fol_metrics": fol_metrics,
            **({"strategic_objective_ids": _strat_ids_fol} if _strat_ids_fol else {}),
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
        if bridge is not None:
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
            fol_metrics["isolation_survivors"] = len(valid_formulas)
            logger.info(
                f"FOL per-formula isolation: {len(valid_formulas)}/{len(formulas)} "
                f"formulas accepted by Tweety"
            )
            # FP-6 #1197: the per-formula loop only proved each formula PARSES — it
            # discarded the consistency verdicts. Hardcoding `consistent: True` here
            # fabricated a consistency verdict out of parse-success (théâtre, R405 /
            # #1019). Run a real combined consistency check on the survivors and pass
            # the tri-state through; if the combined check itself fails/OOMs, that is
            # `None` (unverified), never a fabricated True.
            iso_consistent: Optional[bool] = None
            iso_msg = "combined consistency unverified"
            # bridge is non-None whenever valid_formulas is non-empty (the loop
            # above is guarded by `if bridge is not None`), but narrow explicitly
            # for the type checker; None ⇒ stay unverified (never fabricate True).
            if bridge is not None:
                try:
                    combined_bs = "\n".join(
                        str(f) for f in fol_signature + [""] + valid_formulas
                    )
                    iso_consistent, iso_msg = await asyncio.to_thread(
                        bridge.check_consistency, combined_bs, "first_order"
                    )
                except Exception as iso_err:  # combined check failed → unverified
                    logger.warning(
                        "FOL isolation: combined consistency check failed (%s) — "
                        "reporting unverified (None), not fabricated True.",
                        iso_err,
                    )
                    iso_consistent = None
            return {
                "formulas": valid_formulas,
                "fol_signature": fol_signature,
                "fol_metadata": meta,
                "consistent": iso_consistent,
                "inferences": inferences,
                "confidence": (
                    0.6
                    if iso_consistent is True
                    else (0.0 if iso_consistent is None else 0.4)
                ),
                "message": iso_msg,
                "logic_type": "first_order",
                "argument_count": len(args),
                "isolation_retry": True,
                "rejected_count": len(formulas) - len(valid_formulas),
                "fol_metrics": fol_metrics,
                **(
                    {"strategic_objective_ids": _strat_ids_fol}
                    if _strat_ids_fol
                    else {}
                ),
            }

        # All formulas failed — no heuristic fallback (#1019)
        # Tweety is the solver; if it cannot parse the formulas, report
        # honest failure rather than fabricating a consistency result.
        fol_signature = []
        fol_metrics["post_tweety"] = 0
        fol_metrics["isolation_survivors"] = 0
        try:
            meta = FOLLogicAgent.extract_fol_metadata(formulas)
            fol_signature = meta.get("signature_lines", [])
        except Exception:
            pass
        logger.warning(
            "FOL reasoning: all formulas failed Tweety parsing (%s). "
            "Reporting unverified status (no heuristic fallback).",
            tweety_err,
        )
        return {
            "formulas": formulas,
            "fol_signature": fol_signature,
            "consistent": None,
            "inferences": inferences,
            "confidence": 0.0,
            "logic_type": "first_order",
            "argument_count": len(args),
            "solver": "none",
            "diagnostic": str(tweety_err),
            "fol_metrics": fol_metrics,
            **({"strategic_objective_ids": _strat_ids_fol} if _strat_ids_fol else {}),
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
    """Invoke modal logic consistency via the configured Tweety reasoner.

    Primary path: ``ModalHandler.is_modal_kb_consistent`` — the #1212
    query-based consistency probe (the KB is inconsistent iff it entails a
    ground contradiction), run with the **configured** modal solver. The
    default ``settings.modal_solver`` is ``TWEETY`` → ``SimpleMlReasoner``
    (pure Java, decides without any external binary — #1205, firsthand-
    verified). SPASS remains opt-in via ``settings.modal_solver = SPASS``
    (honored by ``ModalHandler._get_active_reasoner``), useful once a real
    SPASS CLI build is vendored.

    #1219 (anti-pendule): the previous implementation force-set
    ``settings.modal_solver = SPASS`` *unconditionally* on every call. With
    the SPASS binary absent (the current state), ``_get_active_reasoner``
    raised ``RuntimeError`` *before* ``is_modal_kb_consistent`` could run,
    so the #1212 ``SimpleMlReasoner`` fix — proven in unit tests
    (``test_fp11_modal_kb_roundtrip``) — was **never reached in the
    pipeline**: every spectacular ``modal`` phase fell through to the
    no-solver path (``valid=None``). The force-set was the bug; subtracting
    it lets the configured ``TWEETY`` default decide. ``ModalSolverChoice``
    is no longer imported here (no per-call override → config is the single
    source of truth, mirroring ``ModalHandler``'s own design).

    ``valid`` is ``Optional[bool]``: a real ``True``/``False`` when the
    solver decided, ``None`` when it could not (parse error, undecidable
    signature) — honest, never fabricated (#1019). Falls back to
    ``TweetyBridge.execute_modal_query`` then to an honest ``unavailable``
    report (#961) — no heuristic that fabricates a verdict.
    """
    # #1224: build the modal KB from the nl_to_logic translations (as PL/FOL
    # do), NOT from the raw corpus. The spectacular DAG executor never populates
    # ``context["formulas"]`` (``_store_phase_result`` sets only
    # ``phase_*_output``/``_result`` and does not merge output keys), so the
    # prior ``context.get("formulas", [input_text])`` fallback fed ``MlParser``
    # the raw corpus paragraph → ``ParserException`` on URL fragments /
    # prose-as-sort-declarations → ``valid=None`` (degraded) on every corpus.
    # When nl_to_logic produced formulas, mirror PL: keep the valid ones,
    # sanitize them to clean propositional atoms (``PLFormulaSanitizer``,
    # #537), and declare ``type(<atom>)`` per FP-11 #1214 so the modal parser
    # (an extension of FOL) accepts the KB. The hand-written-KB / direct
    # ``formulas`` path (tests, pre-typed KBs) stays as-is — never re-declare
    # atoms an existing KB already declared (MlParser rejects duplicates).
    nl_out = context.get("phase_nl_to_logic_output") or {}
    nl_translations = nl_out.get("translations", []) if isinstance(nl_out, dict) else []
    nl_formulas = [
        str(t["formula"])
        for t in nl_translations
        if isinstance(t, dict) and t.get("is_valid") and t.get("formula")
    ]

    if nl_formulas:
        # Real-pipeline path (#1224): the modal KB comes from nl_to_logic.
        # Sanitize to clean propositional atoms, then declare type(prop) per
        # atom so MlParser accepts the KB. Fail-loud: if the sanitized KB still
        # does not parse, ``is_modal_kb_consistent`` honestly returns
        # ``(None, "parse error")`` → degraded, never a fabricated verdict
        # (#1019). nl_to_logic formulas never carry ``type(...)`` so there is
        # no duplicate-declaration risk here.
        formulas = nl_formulas
        kb_formulas: List[str] = list(nl_formulas)
        try:
            from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
                PLFormulaSanitizer,
            )

            sanitizer = PLFormulaSanitizer()
            san_result = sanitizer.sanitize_batch(nl_formulas)
            if san_result.sanitized_formulas:
                kb_formulas = san_result.sanitized_formulas
        except Exception as san_err:
            logger.debug(
                f"Modal sanitizer unavailable ({san_err}), using raw nl formulas"
            )
        # FP-11 #1214: declare type(prop) for each atomic predicate the modal
        # parser will reference (connectives/keywords are not atoms).
        # #1227: MlParser predicate identifiers must match ``[a-zA-Z][a-zA-Z0-9]*``
        # — NO underscores (stricter than Tweety PL, whose grammar is
        # ``[a-zA-Z_][a-zA-Z0-9_]*`` and which ``PLFormulaSanitizer`` targets).
        # Real ``nl_to_logic`` extraction emits COMPOUND atoms with underscores
        # (e.g. ``heavy_rain``); the sanitizer only symbolizes atoms it deems
        # NL-like (>30 chars / punctuation / accents), so a short compound atom
        # passes through underscored and ``type(heavy_rain)`` raises
        # ``ParserException: Illegal characters in predicate definition``. Subtract
        # the illegal chars: map every MlParser-illegal atom to a fresh legal
        # symbol (``mp1, mp2, ...``), applied CONSISTENTLY to both the
        # declarations and the formula bodies so the KB stays sound (no two
        # distinct atoms collapse to one symbol). Already-legal atoms are kept
        # verbatim — minimal change, anti-pendule.
        _keyword_atoms = {
            "forall",
            "exists",
            "true",
            "false",
            "type",
            "prop",
            "and",
            "or",
            "not",
            "implies",
        }
        _atom_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
        _mlparser_legal_re = re.compile(r"^[a-zA-Z][a-zA-Z0-9]*$")
        # Reserve the already-legal atom names so generated ``mpN`` symbols never
        # collide with a real atom that is already MlParser-legal.
        _legal_atoms = {
            tok
            for f in kb_formulas
            for tok in _atom_re.findall(str(f))
            if tok not in _keyword_atoms and _mlparser_legal_re.match(tok)
        }
        _atom_symbol: Dict[str, str] = {}
        _symbol_counter = 0

        def _legal_symbol(atom: str) -> str:
            """Map a modal atom to an MlParser-legal identifier (memoized)."""
            nonlocal _symbol_counter
            if atom in _keyword_atoms or _mlparser_legal_re.match(atom):
                return atom
            if atom not in _atom_symbol:
                _symbol_counter += 1
                candidate = f"mp{_symbol_counter}"
                while candidate in _legal_atoms:
                    _symbol_counter += 1
                    candidate = f"mp{_symbol_counter}"
                _atom_symbol[atom] = candidate
            return _atom_symbol[atom]

        kb_formulas = [
            _atom_re.sub(lambda m: _legal_symbol(m.group(0)), str(f))
            for f in kb_formulas
        ]
        _seen_atoms: Dict[str, None] = {}
        for f in kb_formulas:
            for tok in _atom_re.findall(str(f)):
                if tok not in _keyword_atoms and tok not in _seen_atoms:
                    _seen_atoms[tok] = None
        _declarations = [f"type({atom})" for atom in _seen_atoms]
        belief_set_str = "\n".join(_declarations + [str(f) for f in kb_formulas])
    else:
        # Direct-formulas / hand-written-KB path (tests, pre-typed KBs like
        # ``type(rain), [](rain => wet), rain``): use the formulas verbatim so
        # existing declarations/modal operators are not duplicated. Falls back
        # to ``[input_text]`` only when neither path yields formulas — the parse
        # below then fail-louds to ``degraded`` if that content is raw corpus.
        formulas = context.get("formulas", [input_text])
        if not isinstance(formulas, list):
            formulas = [str(formulas)]
        belief_set_str = "\n".join(str(f) for f in formulas)

    # Modality detection runs on the source formulas: modal operators ([]/<>)
    # live in the untranslated input, not in sanitized propositional atoms.
    modalities = []
    for f in formulas:
        f_str = str(f)
        if "[]" in f_str or "necessarily" in f_str.lower():
            modalities.append("necessity")
        if "<>" in f_str or "possibly" in f_str.lower():
            modalities.append("possibility")
    modalities = list(set(modalities)) or ["none_detected"]

    # Primary: ModalHandler.is_modal_kb_consistent (#1212 query-based
    # consistency) via the CONFIGURED solver (default TWEETY = SimpleMlReasoner).
    # #1219: do NOT force SPASS — forcing it bypassed the fix when the binary
    # was absent. valid is Optional[bool] (None = undecidable, honest).
    try:
        from argumentation_analysis.core.config import settings
        from argumentation_analysis.agents.core.logic.modal_handler import (
            ModalHandler,
        )
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
        # #1219: bare TweetyInitializer() does NOT initialize the modal parser/
        # reasoner — those are class attrs that start None and are set only by
        # ``initialize_modal_components`` (which ``TweetyBridge.__init__`` calls
        # via ``ensure_jvm_and_components_are_ready``). Without this call,
        # ``ModalHandler.__init__`` raises "Modal Parser not initialized" and the
        # #1212 ``SimpleMlReasoner`` fix is never reached. The original code
        # masked this construction bug behind the SPASS force-set cascade.
        initializer.initialize_modal_components()  # type: ignore[no-untyped-call]
        handler = ModalHandler(initializer_instance=initializer)
        is_consistent, msg = await asyncio.to_thread(
            handler.is_modal_kb_consistent, belief_set_str
        )
        return {
            "formulas": formulas,
            "valid": is_consistent,
            "modalities": modalities,
            "logic_type": "modal",
            "solver": settings.modal_solver.value,
            "message": msg,
        }
    except Exception as e:
        logger.info(f"ModalHandler unavailable ({e}), falling back to TweetyBridge")

    # Fallback: TweetyBridge.execute_modal_query (genuine modal query via JVM)
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge()
        logic_type = context.get("modal_logic_type", "K")
        accepted, msg = await asyncio.to_thread(
            bridge.execute_modal_query,
            belief_set_str,
            belief_set_str,
            logic_type=logic_type,
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
        logger.debug(f"Modal TweetyBridge unavailable ({e})")

    # No solver available — report honest failure (#1019, #961).
    # No heuristic fallback that could fabricate a verdict.
    logger.warning(
        "Modal analysis unavailable: no solver (Tweety/SPASS) could be loaded. "
        "Reporting unverified status (no heuristic fallback)."
    )
    return {
        "formulas": formulas,
        "valid": None,
        "modalities": modalities,
        "logic_type": "modal",
        "solver": "unavailable",
        "message": "Modal analysis unavailable: no solver could be loaded.",
    }


async def _invoke_dung_extensions(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke Dung framework extension computation via AFHandler (JVM required).

    Builds attack graph from extracted arguments and detected fallacies,
    then computes all available Dung semantics via Tweety: grounded, preferred,
    stable, complete, admissible, conflict_free, semi_stable, stage, ideal,
    naive. (cf2 is NOT shipped in the vendored Tweety build — #1215.)
    Falls back to pure-Python computation when JVM is unavailable.

    #908: If ``context["dung_provider_hint"]`` is set to
    ``"abs_arg_dung_student"``, delegates to the student Dung provider
    instead of the native AFHandler.
    """
    # 1. Extract arguments from upstream phases
    arguments = _extract_arguments_from_context(input_text, context)

    # 2. Build attack relations from fallacies and counter-arguments
    attacks = _generate_attacks_from_args(arguments, context)

    # #908: Provider selection — delegate to student provider if hinted
    provider_hint = context.get("dung_provider_hint")
    if provider_hint == "abs_arg_dung_student":
        try:
            from argumentation_analysis.adapters.dung_student_provider import (
                DungStudentProvider,
            )

            student_provider = DungStudentProvider()  # type: ignore[no-untyped-call]
            # attacks is List[List[str]] from _generate_attacks_from_args;
            # compute_extensions expects List[Tuple[str, str]] — convert
            _typed_attacks = [(a[0], a[1]) for a in attacks if len(a) >= 2]
            result = await student_provider.compute_extensions(
                arguments, _typed_attacks
            )
            if result.get("status") == "unavailable":
                logger.warning(
                    "DungStudentProvider unavailable, falling back to native AFHandler"
                )
            else:
                # Add trace entry for student provider
                _state = context.get("_state_object")
                if _state is not None and result.get("arguments"):
                    _n_args = len(result.get("arguments", []))
                    _stats = result.get("statistics", {})
                    _n_sem = (
                        _stats.get("semantics_computed", 0)
                        if isinstance(_stats, dict)
                        else 0
                    )
                    _state.add_trace_entry(
                        phase="dung",
                        agent="DungStudentProvider",
                        reacts_to=["extract", "counter"],
                        summary=f"Cadre Dung (student provider): {_n_args} arguments. {_n_sem} sémantiques calculées.",
                    )
                logger.info(
                    "Dung extensions computed via abs_arg_dung_student provider"
                )
                return result
        except Exception as e:
            logger.warning(f"DungStudentProvider failed ({e}), falling back to native")

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

        # Compute all 11 semantics in one pass (framework built once).
        # Timeout protection (#992): preferred/stable on large graphs can hang
        # indefinitely — fall back to grounded-only Python on timeout.
        all_semantics = list(SEMANTICS_REASONERS.keys())
        try:
            if _DUNG_TIMEOUT_S > 0:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        handler.analyze_multi_semantics,
                        arguments,
                        attacks,
                        all_semantics,
                    ),
                    timeout=_DUNG_TIMEOUT_S,
                )
            else:
                result = await asyncio.to_thread(
                    handler.analyze_multi_semantics, arguments, attacks, all_semantics
                )
        except asyncio.TimeoutError:
            logger.warning(
                f"Dung Tweety computation timed out after {_DUNG_TIMEOUT_S}s "
                f"({len(arguments)} args, {len(attacks)} attacks) — "
                f"using pure-Python 4-semantics computation (#1019)"
            )
            _python_result = _python_dung_fallback(arguments, attacks)
            # Trace entry for Python Dung compute
            _state = context.get("_state_object")
            if _state is not None and _python_result.get("arguments"):
                _n_args = len(_python_result.get("arguments", []))
                _sem_count = _python_result.get("statistics", {}).get(
                    "semantics_computed", 0
                )
                _state.add_trace_entry(
                    phase="dung",
                    agent="DungAnalyzer",
                    reacts_to=["extract", "counter"],
                    summary=f"Cadre Dung (Python, Tweety timeout): {_n_args} arguments. {_sem_count} sémantiques calculées.",
                )
            return _python_result

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

        _dung_result = {
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
        # Trace entry for Dung extensions specialist
        _state = context.get("_state_object")
        _dung_args = _dung_result.get("arguments")
        if _state is not None and _dung_args:
            _n_args = len(_dung_args)
            _stats = _dung_result.get("statistics")
            _n_attacks = (
                _stats.get("attacks_count", 0) if isinstance(_stats, dict) else 0
            )
            _ext_block = _dung_result.get("extensions")
            _grounded = (
                _ext_block.get("extensions", []) if isinstance(_ext_block, dict) else []
            )
            _g_size = len(_grounded[0]) if _grounded else 0
            _state.add_trace_entry(
                phase="dung",
                agent="DungAnalyzer",
                reacts_to=["extract", "counter"],
                summary=f"Cadre Dung: {_n_args} arguments, {_n_attacks} attaques — extension fondée: {_g_size} arguments acceptés. 11 sémantiques calculées.",
            )
        return _dung_result
    except Exception as e:
        logger.info(
            f"Dung AFHandler unavailable ({e}), using Python 4-semantics compute"
        )
        _python_result = _python_dung_fallback(arguments, attacks)
        # Trace entry for Python Dung compute
        _state = context.get("_state_object")
        if _state is not None and _python_result.get("arguments"):
            _n_args = len(_python_result.get("arguments", []))
            _sem_count = _python_result.get("statistics", {}).get(
                "semantics_computed", 0
            )
            _state.add_trace_entry(
                phase="dung",
                agent="DungAnalyzer",
                reacts_to=["extract", "counter"],
                summary=f"Cadre Dung (Python, AFHandler unavailable): {_n_args} arguments. {_sem_count} sémantiques calculées.",
            )
        return _python_result


def _python_dung_fallback(
    arguments: List[str], attacks: List[List[str]]
) -> Dict[str, Any]:
    """Pure-Python Dung extension computation when JVM/Tweety is unavailable (#1019).

    Computes grounded, complete, preferred, and stable extensions using
    exact combinatorial enumeration. Suitable for argument graphs with ≤50
    arguments (exponential in worst case, but practical for this project's
    input sizes).

    Each extension is a conflict-free set:
    - Grounded:    the ⊆-minimal complete extension (iterative fixpoint)
    - Complete:    all conflict-free sets that defend every member
    - Preferred:   ⊆-maximal complete extensions
    - Stable:      conflict-free sets that attack every non-member
    """
    if not arguments:
        return {
            "semantics": "python",
            "extensions": {},
            "arguments": [],
            "attacks": [],
            "statistics": {"arguments_count": 0, "attacks_count": 0},
        }

    arg_set = set(arguments)
    # Build attack maps
    attack_map: Dict[str, set[str]] = {a: set() for a in arg_set}
    for attacker, target in attacks:
        if attacker in arg_set and target in arg_set:
            attack_map[attacker].add(target)

    def _attacks(attacker: str, target: str) -> bool:
        return target in attack_map.get(attacker, set())

    def _is_conflict_free(s: frozenset[str]) -> bool:
        for a in s:
            for b in s:
                if _attacks(a, b):
                    return False
        return True

    def _defends(s: frozenset[str], arg: str) -> bool:
        """s defends arg iff for every attacker b of arg, some c in s attacks b."""
        for b in arg_set:
            if _attacks(b, arg):
                if not any(_attacks(c, b) for c in s):
                    return False
        return True

    def _is_admissible(s: frozenset[str]) -> bool:
        if not _is_conflict_free(s):
            return False
        return all(_defends(s, a) for a in s)

    def _is_complete(s: frozenset[str]) -> bool:
        """Complete = admissible + every defended argument is in s."""
        if not _is_admissible(s):
            return False
        for arg in arg_set - s:
            if _defends(s, arg):
                return False
        return True

    def _is_stable(s: frozenset[str]) -> bool:
        """Stable = conflict-free + attacks every argument outside s."""
        if not _is_conflict_free(s):
            return False
        outside = arg_set - s
        for b in outside:
            if not any(_attacks(a, b) for a in s):
                return False
        return True

    # ── Grounded extension: iterative fixpoint (polynomial) ──
    grounded: set[str] = set()
    changed = True
    while changed:
        changed = False
        for arg in arg_set:
            if arg in grounded:
                continue
            defended = all(
                any(att in attack_map.get(g, set()) for g in grounded)
                for att in arg_set
                if _attacks(att, arg)
            )
            if defended and not any(_attacks(arg, ga) for ga in grounded):
                grounded.add(arg)
                changed = True

    extensions: Dict[str, Any] = {}
    extensions["grounded"] = [sorted(grounded)]

    # ── Enumerate complete, preferred, stable via power set ──
    # Cap at 25 arguments: power-set enumeration is O(2^n); at n=40 this is
    # ~10^12 operations (infeasible).  Grounded is always computed (polynomial).
    _DUNG_ENUM_CAP = 25
    if len(arg_set) > _DUNG_ENUM_CAP:
        logger.warning(
            "Dung power-set enumeration skipped: %d arguments > cap %d. "
            "Only grounded extension computed.",
            len(arg_set),
            _DUNG_ENUM_CAP,
        )
    if len(arg_set) <= _DUNG_ENUM_CAP:
        complete_exts: List[List[str]] = []
        preferred_exts: List[List[str]] = []
        stable_exts: List[List[str]] = []

        from itertools import combinations

        for size in range(len(arg_set), -1, -1):
            for subset in combinations(sorted(arg_set), size):
                s = frozenset(subset)
                if _is_complete(s):
                    ext_sorted = sorted(s)
                    if ext_sorted not in complete_exts:
                        complete_exts.append(ext_sorted)

        # Preferred = ⊆-maximal complete extensions
        complete_sets = [frozenset(e) for e in complete_exts]
        for e in complete_sets:
            is_maximal = not any(e < other for other in complete_sets if other != e)
            if is_maximal:
                preferred_exts.append(sorted(e))

        # Stable = conflict-free + attacks everything outside
        for e in complete_sets:
            if _is_stable(e):
                stable_exts.append(sorted(e))

        extensions["complete"] = complete_exts
        extensions["preferred"] = preferred_exts
        extensions["stable"] = stable_exts

    return {
        "semantics": "python",
        "extensions": extensions,
        "arguments": arguments,
        "attacks": attacks,
        "statistics": {
            "arguments_count": len(arguments),
            "attacks_count": len(attacks),
            "semantics_computed": len(extensions),
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
                v = val["consistent"]
                if v is True:
                    overall_scores.append(1.0)
                elif v is False:
                    overall_scores.append(0.0)
                # None (unverified) — excluded from scoring (#1019)
            if "satisfiable" in val:
                v = val["satisfiable"]
                if v is True:
                    overall_scores.append(1.0)
                elif v is False:
                    overall_scores.append(0.0)
            if "valid" in val:
                v = val["valid"]
                if v is True:
                    overall_scores.append(1.0)
                elif v is False:
                    overall_scores.append(0.0)
                # None (unverified) — excluded from scoring (#1019)

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

    #1019: No template-rebuild fallback.  If the state is empty, the
    narrative phase returns the sentinel as-is — the root cause (missing
    state, phase failures) must be fixed upstream, not papered over.
    """
    from argumentation_analysis.plugins.narrative_synthesis_plugin import (
        build_narrative,
    )
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.state_writers import (
        CAPABILITY_STATE_WRITERS,
    )

    _FALLBACK_SENTINEL = (
        "L'analyse n'a pas produit suffisamment de donnees pour generer "
        "une synthese narrative"
    )

    # Resolve state: prefer _state_object (set by WorkflowExecutor since
    # workflow_dsl.py writes both unified_state and _state_object), then
    # fall back to unified_state for backward compatibility.
    state = context.get("_state_object") or context.get("unified_state")

    if not isinstance(state, UnifiedAnalysisState):
        # No state was passed — reconstruct from context phase outputs
        # so that build_narrative() has something to work with.
        state = UnifiedAnalysisState(input_text[:200])
        populated = 0
        for key, value in context.items():
            if key.startswith("phase_") and key.endswith("_output"):
                cap = key[len("phase_") : -len("_output")]
                writer = CAPABILITY_STATE_WRITERS.get(cap)
                if writer and isinstance(value, dict):
                    try:
                        writer(value, state, context)
                        populated += 1
                    except Exception:
                        logger.warning(
                            "State writer for '%s' failed during narrative reconstruction",
                            cap,
                            exc_info=True,
                        )
        logger.info(
            "Narrative: no UnifiedAnalysisState in context, reconstructed "
            "from %d phase outputs",
            populated,
        )

    narrative = build_narrative(state)

    if not narrative or _FALLBACK_SENTINEL in narrative:
        # #1019: Fail explicit — no template rebuild.
        # Log diagnostic info so the root cause can be identified.
        phase_keys = [
            k for k in context if k.startswith("phase_") and k.endswith("_output")
        ]
        state_fields = [
            attr
            for attr in (
                "argument_quality_scores",
                "identified_fallacies",
                "counter_arguments",
                "jtms_beliefs",
                "dung_frameworks",
                "fol_analysis_results",
                "propositional_analysis_results",
                "modal_analysis_results",
                "atms_contexts",
            )
            if getattr(state, attr, None)
        ]
        logger.warning(
            "Narrative synthesis produced empty/fallback result. "
            "Available phase outputs: %s. Populated state fields: %s. "
            "Root cause: upstream phases did not produce enough data "
            "for narrative synthesis.",
            phase_keys,
            state_fields,
        )

    paragraph_count = (narrative.count("\n\n") + 1) if narrative else 0

    return {
        "narrative": narrative,
        "paragraph_count": paragraph_count,
        "referenced_fields": _count_referenced_fields(state),
    }


async def _invoke_act2_narrative(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke the Acte II dialectical-narrative generator (Epic #1134 / R3 #1137).

    Builds the deterministic movement evidence from the shared state, then
    conducts the narrative via the LLM (fail-loud, no template — #1108/#405).
    The result populates ``state.act2_narrative``, the key the R6 renderer
    consumes for ``RestitutionActs.act2_narrative``.

    The LLM is resolved into an async callable from a kernel + default service
    (same idiom as ``_invoke_deep_synthesis``). If no service is available the
    generator returns ``status="unavailable"`` fail-loud — the renderer reports
    the gap honestly (anti-pendule #1019/#369).
    """
    from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
        Act2Result,
        build_act2_narrative,
    )
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.state_writers import (
        CAPABILITY_STATE_WRITERS,
    )

    # Resolve state (same precedence as _invoke_narrative_synthesis).
    state = context.get("_state_object") or context.get("unified_state")
    if not isinstance(state, UnifiedAnalysisState):
        state = UnifiedAnalysisState(input_text[:200])
        populated = 0
        for key, value in context.items():
            if key.startswith("phase_") and key.endswith("_output"):
                cap = key[len("phase_") : -len("_output")]
                writer = CAPABILITY_STATE_WRITERS.get(cap)
                if writer and isinstance(value, dict):
                    try:
                        writer(value, state, context)
                        populated += 1
                    except Exception:
                        logger.warning(
                            "State writer for '%s' failed during Acte II "
                            "reconstruction",
                            cap,
                            exc_info=True,
                        )
        logger.info(
            "Acte II: no UnifiedAnalysisState in context, reconstructed from "
            "%d phase outputs",
            populated,
        )

    # Resolve an async LLM callable from a kernel + default service (FB-32
    # idiom: service_id="default" activates the LLM path). Absent service →
    # fail-loud unavailable (passed as None → generator records the status).
    llm_service_id: Optional[str] = None
    kernel: Any = None
    try:
        from semantic_kernel import Kernel

        kernel = Kernel()
        try:
            from argumentation_analysis.core.llm_service import create_llm_service

            llm = create_llm_service(service_id="default")
            if llm:
                kernel.add_service(llm)
                llm_service_id = "default"
        except Exception:
            llm_service_id = None
    except Exception:
        llm_service_id = None

    async def _llm(prompt: str) -> str:
        # Conducted LLM call bound to the resolved kernel/service.
        if not llm_service_id or kernel is None:
            return ""
        settings = kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        result = await kernel.invoke_prompt(
            function_name="act2_narrative_conducted",
            plugin_name="restitution",
            prompt=prompt,
            settings=settings,
        )
        return str(result) if result else ""

    result: Act2Result = await build_act2_narrative(
        state, llm_callable=_llm if llm_service_id else None
    )

    gate_band = result.gate_verdict.band if result.gate_verdict is not None else None
    if result.status != "woven":
        state_fields = [
            attr
            for attr in (
                "identified_arguments",
                "argument_quality_scores",
                "identified_fallacies",
                "counter_arguments",
                "dung_frameworks",
                "fol_analysis_results",
                "propositional_analysis_results",
            )
            if getattr(state, attr, None)
        ]
        logger.warning(
            "Acte II narrative status=%s (fail-loud). llm_service_id=%s. "
            "Populated state fields: %s.",
            result.status,
            llm_service_id,
            state_fields,
        )

    return {
        "act2_narrative": result.narrative,
        "status": result.status,
        "gate_band": gate_band,
        "degraded": result.degraded,
    }


async def _invoke_act1_framing(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke the Acte I framing generator (Epic #1134 / R2 #1136).

    Builds the deterministic framing evidence (metadata + enjeux + derived
    spectrum + game-theoretic read), then conducts the narrative via the LLM
    (fail-loud, no template — #1108/#405). The result populates
    ``state.act1_framing``, the key the R6 renderer consumes for
    ``RestitutionActs.act1_framing``.

    Mirrors ``_invoke_act2_narrative``: the LLM is resolved into an async
    callable from a kernel + default service. Absent service → fail-loud
    unavailable (anti-pendule #1019/#369).
    """
    from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
        Act1Result,
        build_act1_framing,
    )
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.state_writers import (
        CAPABILITY_STATE_WRITERS,
    )

    state = context.get("_state_object") or context.get("unified_state")
    if not isinstance(state, UnifiedAnalysisState):
        state = UnifiedAnalysisState(input_text[:200])
        populated = 0
        for key, value in context.items():
            if key.startswith("phase_") and key.endswith("_output"):
                cap = key[len("phase_") : -len("_output")]
                writer = CAPABILITY_STATE_WRITERS.get(cap)
                if writer and isinstance(value, dict):
                    try:
                        writer(value, state, context)
                        populated += 1
                    except Exception:
                        logger.warning(
                            "State writer for '%s' failed during Acte I "
                            "reconstruction",
                            cap,
                            exc_info=True,
                        )
        logger.info(
            "Acte I: no UnifiedAnalysisState in context, reconstructed from "
            "%d phase outputs",
            populated,
        )

    llm_service_id: Optional[str] = None
    kernel: Any = None
    try:
        from semantic_kernel import Kernel

        kernel = Kernel()
        try:
            from argumentation_analysis.core.llm_service import create_llm_service

            llm = create_llm_service(service_id="default")
            if llm:
                kernel.add_service(llm)
                llm_service_id = "default"
        except Exception:
            llm_service_id = None
    except Exception:
        llm_service_id = None

    async def _llm(prompt: str) -> str:
        if not llm_service_id or kernel is None:
            return ""
        settings = kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        result = await kernel.invoke_prompt(
            function_name="act1_framing_conducted",
            plugin_name="restitution",
            prompt=prompt,
            settings=settings,
        )
        return str(result) if result else ""

    result: Act1Result = await build_act1_framing(
        state, llm_callable=_llm if llm_service_id else None
    )

    gate_band = result.gate_verdict.band if result.gate_verdict is not None else None
    if result.status != "woven":
        logger.warning(
            "Acte I framing status=%s (fail-loud). llm_service_id=%s.",
            result.status,
            llm_service_id,
        )

    return {
        "act1_framing": result.narrative,
        "status": result.status,
        "gate_band": gate_band,
        "degraded": result.degraded,
    }


async def _invoke_act3_conclusion(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke the Acte III conclusion generator (Epic #1134 / R4 #1138).

    Builds the deterministic conclusion evidence (gated verdict band + balanced
    appréciations + actionable que-faire: counters / structuring weak points /
    game-theoretic what-next), then conducts it via the LLM (fail-loud, no
    template — #1108/#405). Gated on G1–G4 (#1008 §3). The result populates
    ``state.act3_conclusion``, the key the R6 renderer consumes for
    ``RestitutionActs.act3_conclusion``.

    Mirrors ``_invoke_act2_narrative`` / ``_invoke_act1_framing``: the LLM is
    resolved into an async callable from a kernel + default service (FB-32
    idiom). Absent service → fail-loud unavailable (anti-pendule #1019/#369).
    """
    from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
        Act3Result,
        build_act3_conclusion,
    )
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration.state_writers import (
        CAPABILITY_STATE_WRITERS,
    )

    state = context.get("_state_object") or context.get("unified_state")
    if not isinstance(state, UnifiedAnalysisState):
        state = UnifiedAnalysisState(input_text[:200])
        populated = 0
        for key, value in context.items():
            if key.startswith("phase_") and key.endswith("_output"):
                cap = key[len("phase_") : -len("_output")]
                writer = CAPABILITY_STATE_WRITERS.get(cap)
                if writer and isinstance(value, dict):
                    try:
                        writer(value, state, context)
                        populated += 1
                    except Exception:
                        logger.warning(
                            "State writer for '%s' failed during Acte III "
                            "reconstruction",
                            cap,
                            exc_info=True,
                        )
        logger.info(
            "Acte III: no UnifiedAnalysisState in context, reconstructed from "
            "%d phase outputs",
            populated,
        )

    llm_service_id: Optional[str] = None
    kernel: Any = None
    try:
        from semantic_kernel import Kernel

        kernel = Kernel()
        try:
            from argumentation_analysis.core.llm_service import create_llm_service

            llm = create_llm_service(service_id="default")
            if llm:
                kernel.add_service(llm)
                llm_service_id = "default"
        except Exception:
            llm_service_id = None
    except Exception:
        llm_service_id = None

    async def _llm(prompt: str) -> str:
        if not llm_service_id or kernel is None:
            return ""
        settings = kernel.get_prompt_execution_settings_from_service_id(llm_service_id)
        result = await kernel.invoke_prompt(
            function_name="act3_conclusion_conducted",
            plugin_name="restitution",
            prompt=prompt,
            settings=settings,
        )
        return str(result) if result else ""

    result: Act3Result = await build_act3_conclusion(
        state, llm_callable=_llm if llm_service_id else None
    )

    gate_band = result.gate_verdict.band if result.gate_verdict is not None else None
    if result.status != "woven":
        logger.warning(
            "Acte III conclusion status=%s (fail-loud). llm_service_id=%s.",
            result.status,
            llm_service_id,
        )

    return {
        "act3_conclusion": result.narrative,
        "status": result.status,
        "gate_band": gate_band,
        "degraded": result.degraded,
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


# ---------------------------------------------------------------------------
# Analysis synthesis invoke callable (#508)
# ---------------------------------------------------------------------------


async def _invoke_analysis_synthesis(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Aggregate all analysis phase outputs into a structured synthesis (#508).

    Collects results from quality, fallacy, counter-argument, debate,
    governance, and formal phases (from context), and produces a
    structured summary with scores and key findings.
    """
    state = context.get("_state_object")
    phase_results = {}

    # Collect phase outputs from context
    for key, val in context.items():
        if (
            key.startswith("phase_")
            and key.endswith("_output")
            and isinstance(val, dict)
        ):
            phase_name = key[len("phase_") : -len("_output")]
            phase_results[phase_name] = val

    # Build structured synthesis from state if available
    sections = {}

    # Quality summary
    quality_scores = getattr(state, "argument_quality_scores", None) if state else None
    if quality_scores and isinstance(quality_scores, (list, dict)):
        sections["quality"] = {
            "evaluated": (
                len(quality_scores)
                if isinstance(quality_scores, list)
                else len(quality_scores)
            ),
            "summary": f"{len(quality_scores)} arguments evaluated",
        }

    # Fallacy summary
    fallacies = getattr(state, "identified_fallacies", None) if state else None
    if fallacies and isinstance(fallacies, list):
        sections["fallacies"] = {
            "count": len(fallacies),
            "types": list(
                set(f.get("type", "unknown") for f in fallacies if isinstance(f, dict))
            ),
        }

    # Counter-argument summary
    counter_args = getattr(state, "counter_arguments", None) if state else None
    if counter_args and isinstance(counter_args, list):
        sections["counter_arguments"] = {
            "generated": len(counter_args),
        }

    # JTMS beliefs
    jtms_beliefs = getattr(state, "jtms_beliefs", None) if state else None
    if jtms_beliefs and isinstance(jtms_beliefs, (list, dict)):
        sections["beliefs"] = {
            "tracked": (
                len(jtms_beliefs)
                if isinstance(jtms_beliefs, list)
                else len(jtms_beliefs)
            ),
        }

    # Formal results
    for field_name in [
        "dung_frameworks",
        "fol_analysis_results",
        "propositional_analysis_results",
        "modal_analysis_results",
    ]:
        formal = getattr(state, field_name, None) if state else None
        if formal and isinstance(formal, (list, dict)):
            sections[field_name] = {"present": True, "size": len(formal)}

    # Overall assessment
    total_phases = len(phase_results)
    sections_count = len(sections)
    overall_completeness = (
        sections_count / max(total_phases, 1) if total_phases > 0 else 0.0
    )

    return {
        "synthesis": sections,
        "phase_count": total_phases,
        "sections_count": sections_count,
        "overall_completeness": round(overall_completeness, 2),
        "phase_results_summary": {
            name: "completed" if "error" not in res else f"error: {res['error'][:50]}"
            for name, res in phase_results.items()
        },
    }


# --- State writers: map capability → (output, state, ctx) → None ---
# Each writer extracts relevant data from phase output and writes to
# UnifiedAnalysisState via its typed add_*() methods.
# Writers are defensive: guard with isinstance checks and .get() everywhere.


# ---------------------------------------------------------------------------
# TextToKB / KBToTweety / TweetyInterpretation invoke callables (#506)
# ---------------------------------------------------------------------------


async def _invoke_text_to_kb(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract a knowledge base from NL text via TextToKBPlugin (#474).

    Uses extract_kb for structured extraction (arguments, beliefs, FOL signature).
    Falls back to extract_arguments_only if LLM unavailable.
    """
    if not input_text or not input_text.strip():
        return {"error": "empty input", "arguments": [], "belief_candidates": []}

    try:
        from argumentation_analysis.plugins.text_to_kb_plugin import TextToKBPlugin

        plugin = TextToKBPlugin()
        result_json = await plugin.extract_kb(input_text, target_logic="fol")
        result = (
            json.loads(result_json) if isinstance(result_json, str) else result_json
        )

        arguments = result.get("arguments", [])
        belief_candidates = result.get("belief_candidates", [])
        fol_signature = result.get("fol_signature")

        return {
            "arguments": arguments,
            "belief_candidates": belief_candidates,
            "fol_signature": fol_signature,
            "count": result.get("count", len(arguments)),
            "source_length": len(input_text),
        }
    except Exception as e:
        logger.warning(f"TextToKB extraction failed: {e}")
        return {"error": str(e), "arguments": [], "belief_candidates": []}


async def _invoke_kb_to_tweety(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Translate KB entries to Tweety formulas via KBToTweetyPlugin (#475).

    Reads upstream text_to_kb output from context and translates each
    belief candidate into a Tweety-compatible formula.
    """
    if not input_text or not input_text.strip():
        return {"error": "empty input", "formulas": []}

    try:
        from argumentation_analysis.plugins.kb_to_tweety_plugin import KBToTweetyPlugin

        plugin = KBToTweetyPlugin()

        # Try batch translation first (more efficient)
        batch_json = await plugin.translate_batch_to_tweety(input_text)
        batch_result = (
            json.loads(batch_json) if isinstance(batch_json, str) else batch_json
        )

        formulas = batch_result.get("results", [])

        # Also try Dung and ASPIC if the input looks like it has structure
        dung_result = None
        aspic_result = None
        try:
            dung_json = await plugin.translate_dung(input_text)
            dung_result = (
                json.loads(dung_json) if isinstance(dung_json, str) else dung_json
            )
        except Exception:
            pass
        try:
            aspic_json = await plugin.translate_aspic(input_text)
            aspic_result = (
                json.loads(aspic_json) if isinstance(aspic_json, str) else aspic_json
            )
        except Exception:
            pass

        result = {
            "formulas": formulas,
            "formula_count": len(formulas),
        }
        if dung_result:
            result["dung_framework"] = dung_result
        if aspic_result:
            result["aspic_system"] = aspic_result

        return result
    except Exception as e:
        logger.warning(f"KBToTweety translation failed: {e}")
        return {"error": str(e), "formulas": []}


async def _invoke_tweety_interpretation(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Interpret formal results as NL via TweetyResultInterpretationPlugin (#476).

    Uses interpret_full_analysis for a comprehensive multi-section synthesis.
    Falls back to individual interpreters based on available data.
    """
    if not input_text or not input_text.strip():
        return {"error": "empty input", "interpretation": ""}

    try:
        from argumentation_analysis.plugins.tweety_result_interpretation_plugin import (
            TweetyResultInterpretationPlugin,
        )

        plugin = TweetyResultInterpretationPlugin()

        # Try full analysis interpretation first
        try:
            full_json = await plugin.interpret_full_analysis(input_text)
            full_result = (
                json.loads(full_json) if isinstance(full_json, str) else full_json
            )
            interpretation = (
                full_result
                if isinstance(full_result, str)
                else full_result.get("interpretation", str(full_result))
            )

            if interpretation:
                return {"interpretation": interpretation}
        except Exception:
            pass

        # Fallback: try individual interpreters based on context data
        parts = []
        state = context.get("state")

        # Dung extensions
        dung_data = getattr(state, "dung_frameworks", None) if state else None
        if dung_data:
            try:
                dung_json = await plugin.interpret_dung_results(
                    json.dumps(dung_data)
                    if isinstance(dung_data, dict)
                    else str(dung_data)
                )
                dung_interp = (
                    json.loads(dung_json) if isinstance(dung_json, str) else dung_json
                )
                parts.append(str(dung_interp))
            except Exception:
                pass

        # FOL results
        fol_data = getattr(state, "fol_analysis_results", None) if state else None
        if fol_data:
            try:
                fol_json = await plugin.interpret_fol_results(
                    json.dumps(fol_data)
                    if isinstance(fol_data, dict)
                    else str(fol_data)
                )
                fol_interp = (
                    json.loads(fol_json) if isinstance(fol_json, str) else fol_json
                )
                parts.append(str(fol_interp))
            except Exception:
                pass

        combined = " ".join(parts) if parts else ""
        if not combined:
            # Fail-loud (#1019): the placeholder is NOT a real interpretation.
            # Mark status so consumers do not present it as an authentic result.
            return {
                "interpretation": "",
                "status": "unavailable",
                "reason": "insufficient_upstream_formal_data",
            }

        return {"interpretation": combined, "status": "ok"}
    except Exception as e:
        logger.warning(f"TweetyInterpretation failed: {e}")
        return {"error": str(e), "interpretation": ""}


# ---------------------------------------------------------------------------
# External solver routing — FOL → EProver/Prover9, Modal → SPASS (#504)
# ---------------------------------------------------------------------------


async def _invoke_external_fol_solver(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Route FOL formulas to external solver (EProver/Prover9) with fallback (#504).

    Picks up formulas from the FOL phase output. Tries EProver via Tweety
    EFOLReasoner first, then Prover9 subprocess. Falls back to TweetyBridge
    (the default FOL path) when neither external solver is available.

    #1019: No degraded flag. TweetyBridge is a genuine FOL reasoner.
    External solvers are optional performance enhancers, not prerequisites.
    """
    _preflight_solver_check()

    fol_output = context.get("phase_fol_output", {})
    if not isinstance(fol_output, dict):
        fol_output = {}
    formulas = fol_output.get("formulas", [input_text])
    if not isinstance(formulas, list):
        formulas = [str(formulas)]

    fol_signature = fol_output.get("fol_signature", [])

    # Resolve solver choice: context override > settings > default (#900)
    fol_solver = context.get("fol_solver", None)
    if fol_solver is None:
        try:
            from argumentation_analysis.core.config import settings

            fol_solver = str(settings.solver)  # SolverChoice enum → str
        except Exception:
            fol_solver = "eprover"  # #939: eprover default, not tweety

    # #982: Probe for EProver binary before claiming external solver
    eprover_available = shutil.which("eprover") is not None

    # Try EProver via Tweety EFOLReasoner (only if binary present)
    if eprover_available and fol_solver == "eprover":
        try:
            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )
            from argumentation_analysis.agents.core.logic.fol_logic_agent import (
                FOLLogicAgent,
            )

            bridge = TweetyBridge()
            meta = FOLLogicAgent.extract_fol_metadata(formulas)
            sig = meta.get("signature_lines", fol_signature)
            belief_set_str = "\n".join(str(f) for f in sig + [""] + formulas)
            is_consistent, msg = await asyncio.to_thread(
                bridge.check_consistency, belief_set_str, "first_order"
            )
            return {
                "formulas": formulas,
                "consistent": bool(is_consistent),
                "solver": "eprover",
                "degraded": False,
                "message": msg,
                "logic_type": "first_order",
            }
        except Exception as e:
            logger.info(f"EProver unavailable ({e}), trying Prover9")
    elif fol_solver == "eprover":
        logger.info("EProver binary not found on PATH (shutil.which), skipping")

    # Try Prover9 subprocess (only if requested)
    prover9_available = False
    if fol_solver == "prover9":
        try:
            from pathlib import Path as _Path

            _prover9_bat = _Path("libs/prover9/bin/prover9.bat")
            prover9_available = _prover9_bat.is_file()
        except Exception:
            pass
        if prover9_available:
            try:
                from argumentation_analysis.core.prover9_runner import run_prover9

                belief_set_str = "\n".join(
                    str(f) for f in fol_signature + [""] + formulas
                )
                prover9_input = f"formulas(sos).\n{belief_set_str}\nend_of_list.\n"
                result = await asyncio.to_thread(run_prover9, prover9_input)
                proved = "THEOREM PROVED" in result or "Proof found" in result
                return {
                    "formulas": formulas,
                    "consistent": proved,
                    "solver": "prover9",
                    "degraded": False,
                    "raw_output": result[:500],
                    "logic_type": "first_order",
                }
            except FileNotFoundError:
                logger.info("Prover9 binary not found, falling back to TweetyBridge")
            except Exception as e:
                logger.info(f"Prover9 failed ({e}), falling back to TweetyBridge")
        else:
            logger.info("Prover9 binary not bundled, falling back to TweetyBridge")

    # Fallback: TweetyBridge (default path) — genuine FOL reasoning via JVM
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import (
            TweetyBridge,
        )
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent,
        )

        bridge = TweetyBridge()
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        sig = meta.get("signature_lines", fol_signature)
        belief_set_str = "\n".join(str(f) for f in sig + [""] + formulas)
        is_consistent, msg = await asyncio.to_thread(
            bridge.check_consistency, belief_set_str, "first_order"
        )
        return {
            "formulas": formulas,
            "consistent": bool(is_consistent),
            "solver": "tweety",
            "message": msg,
            "logic_type": "first_order",
        }
    except Exception as e:
        return {
            "formulas": formulas,
            "consistent": None,
            "solver": "none",
            "error": str(e),
            "logic_type": "first_order",
        }


async def _invoke_external_modal_solver(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Route modal formulas to SPASS with TweetyBridge fallback (#504).

    Picks up formulas from the modal phase output. Tries SPASS via
    SPASSMlReasoner first. Falls back to TweetyBridge when SPASS is
    not available.

    #1019: No degraded flag. TweetyBridge is a genuine modal reasoner.
    External solvers are optional performance enhancers, not prerequisites.
    """
    _preflight_solver_check()
    modal_output = context.get("phase_modal_output", {})
    if not isinstance(modal_output, dict):
        modal_output = {}
    formulas = modal_output.get("formulas", [input_text])
    if not isinstance(formulas, list):
        formulas = [str(formulas)]

    modalities = modal_output.get("modalities", ["none_detected"])

    # #982: Probe for SPASS binary before claiming external solver
    spass_available = shutil.which("SPASS") is not None

    # Try SPASS via ModalHandler (only if binary present)
    if spass_available:
        try:
            from argumentation_analysis.core.config import settings, ModalSolverChoice
            from argumentation_analysis.agents.core.logic.modal_handler import (
                ModalHandler,
            )
            from argumentation_analysis.agents.core.logic.tweety_initializer import (
                TweetyInitializer,
            )

            if not settings.modal_solver == ModalSolverChoice.SPASS:
                object.__setattr__(settings, "modal_solver", ModalSolverChoice.SPASS)
            initializer = TweetyInitializer()  # type: ignore[no-untyped-call]
            handler = ModalHandler(initializer_instance=initializer)
            belief_set_str = "\n".join(str(f) for f in formulas)
            is_consistent, msg = await asyncio.to_thread(
                handler.is_modal_kb_consistent, belief_set_str
            )
            return {
                "formulas": formulas,
                "valid": bool(is_consistent),
                "modalities": modalities,
                "solver": "spass",
                "degraded": False,
                "message": msg,
                "logic_type": "modal",
            }
        except Exception as e:
            logger.info(f"SPASS modal solver unavailable ({e}), falling back to Tweety")
    else:
        logger.info(
            "SPASS binary not found on PATH (shutil.which), using TweetyBridge fallback"
        )

    # Fallback: TweetyBridge — genuine modal reasoning via JVM
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import (
            TweetyBridge,
        )

        bridge = TweetyBridge()
        belief_set_str = "\n".join(str(f) for f in formulas)
        logic_type = context.get("modal_logic_type", "K")
        accepted, msg = await asyncio.to_thread(
            bridge.execute_modal_query,
            belief_set_str,
            belief_set_str,
            logic_type=logic_type,
        )
        return {
            "formulas": formulas,
            "valid": accepted,
            "modalities": modalities,
            "solver": "tweety",
            "message": msg,
            "logic_type": "modal",
        }
    except Exception as e:
        return {
            "formulas": formulas,
            "valid": None,
            "modalities": modalities,
            "solver": "none",
            "error": str(e),
            "logic_type": "modal",
        }


async def _invoke_deep_synthesis(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke DeepSynthesisAgent on the current shared state (#532).

    Reads the full UnifiedAnalysisState from context, runs the 9-section
    synthesis (sections 1-8 grounded over state artifacts; Section 9
    ``final_synthesis`` LLM-conducted and fail-loud per FB-31 #1108, NOT a
    template), and returns both the report object and the rendered markdown.

    FB-18 Mode A (#1039): fails explicitly when fewer than 3 artifact fields
    are populated (VG-2 state guard), and attaches the grounded transversal
    synthesis plus its value-gate verdicts to the result.
    """
    state = context.get("_state_object")
    if state is None:
        return {"error": "No shared state available for deep synthesis"}

    from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
        DeepSynthesisAgent,
    )
    from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
        DeepSynthesisReport,
    )

    # FB-18 VG-2 — state-empty guard: a near-empty state can only yield
    # boilerplate, so fail explicitly instead (#1019 fail-loud).
    populated = DeepSynthesisAgent.count_populated_artifact_fields(state)
    if populated < 3:
        return {
            "error": (
                f"Insufficient artifacts for grounded deep synthesis: only "
                f"{populated}/3 required artifact fields are populated — "
                f"upstream analysis phases produced too little verified "
                f"material (FB-18 VG-2 state guard)"
            ),
            "fail_explicit": True,
            "populated_artifact_fields": populated,
        }

    try:
        # Try full agent instantiation (with LLM for section 9)
        from semantic_kernel import Kernel

        kernel = Kernel()
        try:
            from argumentation_analysis.core.llm_service import create_llm_service

            llm = create_llm_service(service_id="default")
            if llm:
                kernel.add_service(llm)
        except Exception:
            pass

        try:
            # FB-32 #1112: pass service_id so the agent activates its 3 LLM paths
            # (_llm_briefing, _llm_synthesis Section 9, FB-18 grounded). Without it,
            # ``_llm_service_id`` stays None and all three early-return None, so
            # Section 9 came back "unavailable" even with an LLM registered in the
            # kernel (the de-castrated path was correct but never wired — last
            # structural castration site, same class as FB-30/FB-31). Anti-pendule:
            # activate the existing path, no counterweight.
            agent = DeepSynthesisAgent(kernel=kernel, service_id="default")
            source_meta = context.get("source_metadata", {})
            report = await agent.synthesize(state, source_metadata=source_meta)
        except (ValueError, Exception) as agent_err:
            # Agent init failed (no LLM service) — use static builders directly
            logger.info(
                f"Agent instantiation failed ({agent_err}), using static builders"
            )
            source_meta = context.get("source_metadata", {})
            report = DeepSynthesisReport(
                source_overview=DeepSynthesisAgent._build_source_overview(
                    state, source_meta
                ),
                argument_map=DeepSynthesisAgent._build_argument_map(state),
                fallacy_diagnoses=DeepSynthesisAgent._build_fallacy_diagnoses(state),
                formal_findings=DeepSynthesisAgent._build_formal_findings(state),
                dung_structure=DeepSynthesisAgent._build_dung_structure(state),
                belief_retractions=DeepSynthesisAgent._build_belief_retractions(state),
                counter_arguments=DeepSynthesisAgent._build_counter_arguments(state),
                cross_text_parallels=DeepSynthesisAgent._build_cross_text_parallels(
                    state
                ),
            )
            # FB-31 #1108: no LLM in the static-builder path → Section 9 is
            # fail-loud. final_synthesis stays empty and the status says
            # "unavailable" explicitly — NOT a count-template masquerading as
            # the synthesis (the determinization residue #1109/#1019 removes).
            report.final_synthesis = ""
            report.final_synthesis_status = "unavailable"
            report.total_state_fields = DeepSynthesisAgent._count_state_fields(state)
            report.sections_populated = DeepSynthesisAgent._count_populated_sections(
                report
            )
            # FB-18: no LLM in the static-builder path — record that honestly
            # rather than passing template output off as grounded synthesis.
            report.populated_artifact_fields = populated
            report.grounded_synthesis_status = "unavailable"
            report.value_gates = DeepSynthesisAgent.validate_value_gates("", populated)

        markdown = DeepSynthesisAgent.render_markdown(report)

        # Write markdown to gitignored output if path provided
        output_path = context.get("deep_synthesis_output_path")
        if output_path:
            from pathlib import Path

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(markdown, encoding="utf-8")
            logger.info(f"Deep synthesis report written to {output_path}")

        return {
            "report": report.to_dict(),
            "markdown": markdown,
            "sections_populated": report.sections_populated,
            "total_state_fields": report.total_state_fields,
            "grounded_synthesis": report.grounded_synthesis,
            "grounded_synthesis_status": report.grounded_synthesis_status,
            "value_gates": report.value_gates,
            "populated_artifact_fields": report.populated_artifact_fields,
            "summary": (
                f"Deep synthesis: {report.sections_populated}/9 sections, "
                f"{report.total_state_fields} state fields consumed, "
                f"grounded synthesis: "
                f"{report.grounded_synthesis_status or 'not attempted'}"
            ),
        }
    except Exception as e:
        logger.error(f"Deep synthesis failed: {e}", exc_info=True)
        return {"error": str(e)}


async def _invoke_stakes_extractor(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract stakes, stakeholders, register, and arena (Track TT #723).

    Reads arguments from state, calls the StakesExtractor specialist,
    writes results to state.stakes_and_stakeholders.
    """
    state = context.get("_state_object")
    if state is None:
        return {"error": "No shared state available for stakes extraction"}

    from argumentation_analysis.agents.core.political.stakes_extractor import (
        StakesExtractor,
    )

    extractor = StakesExtractor()

    # Gather arguments from state.
    # Writer schema (shared_state.add_argument): identified_arguments is a
    # dict {arg_id: description}. StakesExtractor.extract expects a list of
    # argument dicts with a "text"/"description" key. The previous
    # ``list(dict)`` passed bare arg_id keys (strings), which crashed
    # ``arg.get("text", ...)`` inside extract on real (LLM-on) runs — masked
    # by unit tests that mock LLM=None (extract short-circuits before the
    # loop). Audit #1151 §3(b). Convert the dict-of-strings into the
    # list-of-dicts the consumer's contract specifies (anti-pendule: feed the
    # consumer what it asked for, no counterweight).
    raw_args = getattr(state, "identified_arguments", {}) or {}
    if isinstance(raw_args, dict):
        arguments = [
            {"text": desc} for desc in raw_args.values() if isinstance(desc, str)
        ]
    else:  # defensive: already a sequence of argument dicts (legacy/fixture)
        arguments = list(raw_args)

    # Source metadata
    source_metadata = getattr(state, "source_metadata", {})
    if not source_metadata:
        source_metadata = context.get("source_metadata", {})

    # Get LLM client
    llm_client = None
    determinism_params = {}
    try:
        client = _get_openai_client()
        if client:
            llm_client = client
            determinism_params = _get_determinism_params()
    except Exception:
        pass

    raw_text = getattr(state, "raw_text", "") or input_text

    result = extractor.extract(
        arguments=arguments,
        source_metadata=source_metadata,
        raw_text=raw_text,
        llm_client=llm_client,
        determinism_params=determinism_params,
    )

    # Write to state
    state.stakes_and_stakeholders = result

    n_stakes = len(result.get("stakes", []))
    n_stakeholders = len(result.get("stakeholders", []))
    register = result.get("rhetorical_register", "")
    arena = result.get("discursive_arena", "")

    logger.info(
        f"Stakes extraction: {n_stakes} stakes, {n_stakeholders} stakeholders, "
        f"register={register}, arena={arena}"
    )

    return {
        "stakes": result.get("stakes", []),
        "stakeholders": result.get("stakeholders", []),
        "rhetorical_register": register,
        "discursive_arena": arena,
        "summary": (
            f"Extracted {n_stakes} stakes, {n_stakeholders} stakeholders, "
            f"register={register}"
        ),
    }


async def _invoke_ai_shield(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """AI Shield - adversarial input/output validation (#841).

    Runs the AI Shield pipeline on the input text to detect injection,
    jailbreak, bias, and output leaks. Optional phase that runs early
    in the workflow to guard downstream LLM calls.

    Writes results to state.ai_shield_results and adds a trace entry.
    """
    try:
        from argumentation_analysis.services.ai_shield import load_preset
    except ImportError as exc:
        logger.debug(f"AI Shield not available (import failed: {exc})")
        return {"shield_available": False, "blocked": False, "error": str(exc)}

    # Configure from context or use default preset
    shield_config = context.get("shield_config", {})
    preset_name = shield_config.get("preset", "basic")
    fail_open = shield_config.get("fail_open", True)

    # LLM validator needs API key — pass through if available
    api_key = os.environ.get("OPENAI_API_KEY")
    try:
        shield = load_preset(preset_name, api_key=api_key, fail_open=fail_open)
    except Exception as exc:
        logger.warning(f"AI Shield preset load failed: {exc}")
        return {"shield_available": False, "blocked": False, "error": str(exc)}

    # Validate input (runs all enabled layers)
    result = shield.validate_input(input_text)

    output = {
        "shield_available": True,
        "blocked": result.blocked,
        "overall_score": result.overall_score,
        "passed": result.passed,
        "reason": result.reason,
        "layer_results": [
            {
                "layer": lr.layer_name,
                "score": lr.score,
                "passed": lr.passed,
                "reason": lr.reason,
            }
            for lr in result.layer_results
        ],
    }

    # Write to shared state if available
    _state = context.get("_state_object")
    if _state is not None and hasattr(_state, "ai_shield_results"):
        _state.ai_shield_results.append(output)
        _state.add_trace_entry(
            phase="shield",
            agent="AIShield",
            reacts_to=[],
            summary=(
                f"Shield: {'BLOCKED' if result.blocked else 'PASSED'} "
                f"(score={result.overall_score:.2f}, {len(result.layer_results)} layers)"
            ),
        )

    logger.info(
        f"AI Shield: {'BLOCKED' if result.blocked else 'PASSED'} "
        f"(score={result.overall_score:.2f}, reason={result.reason})"
    )

    return output
