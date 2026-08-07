"""State writers for the unified pipeline.

Each _write_*_to_state function transfers invoke callable output to the
UnifiedAnalysisState. CAPABILITY_STATE_WRITERS maps capability names to
their corresponding writer functions.

Split from unified_pipeline.py (#310).
"""

import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("UnifiedPipeline")


# FP-17 (#1236): the structured-argumentation formalisms below have NO
# text→structured translator wired (translation-gap, FP-4 #1201). On real
# corpora the pipeline feeds them AUTO-SHAPED synthetic input (rules / attacks /
# supports derived from the bare argument graph), so an empty extension list
# means "never genuinely evaluated", NOT "evaluated, found nothing". A
# capability is genuinely fed structured input only when the caller supplies the
# formalism-specific artifact via context — the keys below (a future,
# user/coord-gated translator would populate them). Until then the honest status
# is "absent_no_translator", surfaced explicitly, never a silent [] (#1019).
_STRUCTURED_ARG_INPUT_KEYS: Dict[str, Tuple[str, ...]] = {
    "aspic_plus_reasoning": ("strict_rules", "defeasible_rules"),
    "aba_reasoning": ("contraries",),
    "setaf_reasoning": ("set_attacks",),
    "weighted_argumentation": ("weighted_attacks",),
    "bipolar_argumentation": ("supports",),
}

# Per-formalism display name (used to build the discriminated reason strings).
_STRUCTURED_ARG_FORMALISM_NAME: Dict[str, str] = {
    "aspic_plus_reasoning": "ASPIC+",
    "aba_reasoning": "ABA",
    "setaf_reasoning": "SetAF",
    "weighted_argumentation": "Weighted AF",
    "bipolar_argumentation": "Bipolar AF",
}

# Per-formalism reason string for the ``absent_no_translator`` fallback (#1608).
# Reformulated to describe what was *observed* (ran on auto-shaped synthetic
# input) rather than the #1236-era claim "no translator extracts …" — which was
# falsified once ``structured_arg_translator`` existed and a translator could
# raise, run empty, or skip for want of a key. The discriminated statuses
# (``translator_failed`` / ``no_genuine_relations`` / ``translator_unconfigured``)
# now carry the precise cause; this string only backs the rare legacy path where
# no cause was recorded (nothing wired).
_STRUCTURED_ARG_ABSENT_REASON: Dict[str, str] = {
    "aspic_plus_reasoning": (
        "ASPIC+ ran on auto-shaped synthetic rules: no genuine defeasible/"
        "strict rules + preferences were supplied from the source. Not "
        "fabricated, but not a genuine ASPIC+ analysis of the text."
    ),
    "aba_reasoning": (
        "ABA ran on auto-shaped synthetic rules: no genuine assumptions + "
        "their contraries were supplied from the source."
    ),
    "setaf_reasoning": (
        "SetAF ran on auto-shaped synthetic pairwise attacks lifted to "
        "singletons: no genuine collective (joint) attacks were supplied "
        "from the source."
    ),
    "weighted_argumentation": (
        "Weighted AF ran on auto-shaped synthetic attacks with neutral "
        "placeholder weights: no genuine attack weights were supplied from "
        "the source."
    ),
    "bipolar_argumentation": (
        "Bipolar AF ran on auto-shaped synthetic attacks with no genuine "
        "supports: no genuine support relations were supplied from the source."
    ),
}


def _translation_cause_key(capability: str) -> str:
    """Context key carrying the discriminated translation cause (#1608).

    The invoke callable that ran the translator writes the cause here; the
    recorder reads it. Namespaced by capability so the five translators do not
    overwrite each other in the shared pipeline context.
    """
    return f"_structured_arg_cause:{capability}"


def _translation_error_key(capability: str) -> str:
    """Context key carrying the exception type for a ``translator_failed`` cause."""
    return f"_structured_arg_error:{capability}"


def _resolve_absent_status(
    capability: str, cause: Optional[str], error: str
) -> tuple[str, bool, str]:
    """Map a translation cause to ``(status, degraded, reason)`` (#1608).

    Used when no genuine structured input was supplied. Anti-pendule: cause 3
    (``no_genuine_relations`` — the translator ran and found nothing) is an
    analytical RESULT, not a failure; it must NOT be marked ``degraded``.
    Making it red would be the symmetrical error of the current bug.
    """
    formalism = _STRUCTURED_ARG_FORMALISM_NAME.get(capability, capability)
    synthetic = "The framework ran on auto-shaped synthetic input."
    if cause == "translator_failed":
        return (
            "translator_failed",
            True,
            f"{formalism} translator raised {error or 'an exception'} — genuine "
            f"structured input could not be obtained. {synthetic}",
        )
    if cause == "no_genuine_relations":
        return (
            "no_genuine_relations",
            False,
            f"{formalism} translator ran and found no genuine structured "
            f"relations in the source — an analytical result, not a failure. "
            f"{synthetic}",
        )
    if cause == "translator_unconfigured":
        return (
            "translator_unconfigured",
            True,
            f"{formalism} translator could not run: no LLM API key configured. "
            f"{synthetic}",
        )
    # No cause recorded (nothing wired / legacy path) — honest-absent #1236.
    return (
        "absent_no_translator",
        True,
        _STRUCTURED_ARG_ABSENT_REASON.get(
            capability,
            "No text→structured translator wired; ran on auto-shaped synthetic "
            "input (translation-gap FP-4 #1201).",
        ),
    )


def _structured_arg_substantive_members(output: Any) -> int:
    """Count the NON-EMPTY result sets a structured-arg handler returned (#1671).

    ``extension_count`` answers "how many result sets came back", and ``[[]]``
    genuinely *is* one extension — so that field is correct as it stands. What it
    cannot do is decide anything: a framework returning a single EMPTY extension
    has accepted nothing, excluded nothing and arbitrated nothing. Measured on
    real state artefacts, four of the five axes come back as ``[[]]`` — one
    result set, empty — which ``len()`` reports as ``1``.

    This counts what the members *contain* rather than how many there are, and
    is used only to decide the status label, never recorded as a metric of its
    own (counting is not deciding).
    """
    if not isinstance(output, dict):
        return 0
    members = output.get("extensions")
    if members is None:
        members = output.get("supports")
    if not isinstance(members, list):
        return 0
    return sum(1 for member in members if member)


def _record_structured_arg_status(
    state: Any, capability: str, output: Any, ctx: dict[str, Any]
) -> None:
    """Surface the honest status of a structured-arg capability (#1236 / #1608).

    Records ``status="evaluated"`` when the context carried genuine
    formalism-specific structured input. Otherwise discriminates the cause via
    :func:`_resolve_absent_status` — reading the cause the invoke callable wrote
    into ``ctx`` — so the axis is labelled ``translator_failed`` /
    ``no_genuine_relations`` / ``translator_unconfigured`` rather than the
    #1236-era ``absent_no_translator`` catch-all that asserted a cause it had
    not observed. Only labels what happened; never fabricates extensions (#1019).
    No-op on states that predate ``add_structured_arg_status`` (defensive).

    #1671 — the ``has_genuine_input`` branch used to be the mirror image of the
    defect #1608 fixed on the other branch: it asserted *"framework evaluated on
    real structured artifacts"* while observing only that an INPUT key was
    present. Nothing in it looked at what came back. Measured on real state
    artefacts, four of the five axes reached that branch with
    ``extensions == [[]]`` — the handler had not failed, it had *succeeded on an
    empty theory* — and were filed ``evaluated / degraded=False``. Such an axis
    is then invisible in both directions: the absence ledger skips it (it is not
    degraded) and the presence channel finds nothing to project. The branch now
    reads the output and splits into ``evaluated`` (a non-empty result set came
    back) and ``evaluated_empty`` (the handler ran and returned nothing
    substantive, or reported itself degraded).

    Anti-pendulum: ``evaluated_empty`` is deliberately NOT the same thing as
    ``no_genuine_relations``. The latter is a statement about the *source* — the
    translator looked and found no such relations, an analytical result, hence
    ``degraded=False``. This one is a statement about the *reasoning step*: the
    translator did supply relations and the framework still produced nothing, so
    the axis contributed no analysis and must not be counted as used.
    """
    recorder = getattr(state, "add_structured_arg_status", None)
    if not callable(recorder):
        return
    keys = _STRUCTURED_ARG_INPUT_KEYS.get(capability, ())
    has_genuine_input = any(ctx.get(k) for k in keys)
    # Extension/support count from the handler output, 0-safe.
    ext_count = 0
    if isinstance(output, dict):
        exts = output.get("extensions")
        if exts is None:
            exts = output.get("supports")
        if isinstance(exts, list):
            ext_count = len(exts)
    if has_genuine_input:
        handler_degraded = bool(isinstance(output, dict) and output.get("degraded"))
        substantive = _structured_arg_substantive_members(output)
        if not handler_degraded and substantive:
            recorder(
                capability,
                "evaluated",
                False,
                "Genuine structured input supplied via context; the framework "
                f"returned {substantive} non-empty result set(s).",
                ext_count,
            )
            return
        formalism = _STRUCTURED_ARG_FORMALISM_NAME.get(capability, capability)
        if handler_degraded:
            reason = (
                f"Genuine structured input was supplied, but the {formalism} "
                "handler reported a degraded result — no reasoning was performed "
                "on that input."
            )
        else:
            reason = (
                f"Genuine structured input was supplied, but the {formalism} "
                f"framework returned no non-empty result set ({ext_count} "
                "returned, all empty) — nothing was accepted, excluded or "
                "arbitrated."
            )
        recorder(capability, "evaluated_empty", True, reason, ext_count)
        return
    # No genuine input — discriminate the cause (#1608). The invoke callable
    # that ran the translator wrote the cause into ctx. Falls back to
    # absent_no_translator only when no cause was recorded (nothing wired /
    # legacy paths), preserving the #1236 honest-absent label.
    cause = ctx.get(_translation_cause_key(capability))
    error = ctx.get(_translation_error_key(capability), "") or ""
    status, degraded, reason = _resolve_absent_status(capability, cause, error)
    recorder(capability, status, degraded, reason, ext_count)


__all__ = [
    "_write_quality_to_state",
    "_write_counter_argument_to_state",
    "_write_jtms_to_state",
    "_write_atms_to_state",
    "_write_debate_to_state",
    "_write_governance_to_state",
    "_write_camembert_to_state",
    "_write_hierarchical_fallacy_to_state",
    "_write_semantic_index_to_state",
    "_write_speech_to_state",
    "_write_ranking_to_state",
    "_write_aspic_to_state",
    "_write_belief_revision_to_state",
    "_write_dialogue_to_state",
    "_write_probabilistic_to_state",
    "_write_bipolar_to_state",
    "_write_aba_to_state",
    "_write_adf_to_state",
    "_write_fact_extraction_to_state",
    "_write_propositional_to_state",
    "_write_fol_to_state",
    "_write_modal_to_state",
    "_write_nl_to_logic_to_state",
    "_write_dung_extensions_to_state",
    "_write_formal_synthesis_to_state",
    "_write_dl_to_state",
    "_write_cl_to_state",
    "_write_sat_to_state",
    "_write_setaf_to_state",
    "_write_weighted_to_state",
    "_write_social_to_state",
    "_write_eaf_to_state",
    "_write_delp_to_state",
    "_write_qbf_to_state",
    "_write_collaborative_analysis_to_state",
    "_write_narrative_synthesis_to_state",
    "_write_external_fol_solver_to_state",
    "_write_external_modal_solver_to_state",
    "CAPABILITY_STATE_WRITERS",
]


def _write_quality_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write quality evaluator results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return

    # New format: per-argument scores
    per_arg = output.get("per_argument_scores", {})
    if isinstance(per_arg, dict) and per_arg:
        for arg_id, result in per_arg.items():
            if not isinstance(result, dict):
                continue
            scores = result.get("scores_par_vertu", {})
            if not isinstance(scores, dict):
                scores = {}
            overall = result.get("note_finale", 0.0)
            llm_assessment = result.get("llm_assessment")  # (#290)
            if isinstance(overall, (int, float)) and (scores or overall > 0):
                resolved = _resolve_target_arg_id(state, str(arg_id))
                state.add_quality_score(
                    str(arg_id),
                    scores,
                    float(overall),
                    llm_assessment=llm_assessment,
                    resolved_arg_id=resolved,
                )
        return

    # Legacy format: single evaluation
    arg_id = ctx.get("current_arg_id", "arg_input")
    scores = output.get("scores_par_vertu", {})
    if not scores:
        scores = {
            k: v
            for k, v in output.items()
            if k
            not in (
                "note_finale",
                "note_moyenne",
                "scores_par_vertu",
                "rapport_detaille",
                "per_argument_scores",
                "aggregate_score",
                "arguments_evaluated",
            )
            and isinstance(v, (int, float))
        }
    overall = output.get("note_finale", 0.0)
    if isinstance(overall, (int, float)) and (scores or overall > 0):
        resolved = _resolve_target_arg_id(state, arg_id)
        state.add_quality_score(
            arg_id, scores, float(overall), resolved_arg_id=resolved
        )


def _identified_arguments(state: Any) -> Dict[str, Any]:
    """The state's identified arguments, or ``{}`` on states that carry none.

    Shared by both fallacy-target resolvers (#1633 site 3). The conversational
    lane also runs against states exposing only ``add_identified_fallacy``
    (PhaseScopedState and friends), which have no ``identified_arguments`` at
    all — reaching for it directly there raises, and the harness's outer
    ``except`` turns that into a silent "no fallacies registered".
    """
    args = getattr(state, "identified_arguments", None)
    return args if isinstance(args, dict) else {}


def _resolve_target_arg_id(state: Any, target_text: str) -> Optional[str]:
    """Resolve target text to an arg_id from identified_arguments.

    Checks exact ID match first, then text-based matching.
    Returns None if no match found.
    """
    if not target_text:
        return None
    arguments = _identified_arguments(state)
    # Direct ID match
    if target_text in arguments:
        return str(target_text)
    # Text-based matching (same heuristic as get_enrichment_summary)
    for arg_id, desc in arguments.items():
        if not desc:
            continue
        match_prefix = desc[:60]
        if (
            target_text == desc
            or target_text[:60] == match_prefix
            or match_prefix in target_text
            or target_text in desc
        ):
            return str(arg_id)
    return None


def resolve_fallacy_target_arg_id(state: Any, fallacy: Dict[str, Any]) -> Optional[str]:
    """Resolve which identified argument a fallacy record attacks.

    Single resolution used by **both** lanes that register fallacies into state
    (#1633 site 3). It used to exist only here, in the pipeline writer; the
    conversational lane carried a one-line ``source_arg_id or
    target_argument_id`` that inverted the precedence and skipped the
    membership guard, so the two lanes assigned *different* targets to the same
    payload and produced different ASPIC survivor/defeated partitions.

    Resolution order (D1a #1167 — surface what the per-argument descent already
    grounded, do NOT invent a link):

    1. ``target_argument_id`` — an explicit arg_id carried by the plugin. It
       states which argument is *attacked*, so it outranks the id of whatever
       argument happened to be under analysis.
    2. ``source_arg_id`` — set by the per-argument harness to the arg_id the
       descent analyzed this fallacy against, **only when it names a real
       argument**. The wide-net whole-text pass stamps the sentinel
       ``"whole_text"`` here; accepting it would store a dangling reference
       that matches no argument and silently undermines nothing.
    3. text-match fallbacks (``target_argument`` / ``problematic_quote`` /
       ``explanation``) for wide-net fallacies with no grounded id.

    Returns ``None`` when nothing resolves — the caller must not guess (#1019).
    """
    target_arg_id = fallacy.get("target_argument_id")
    if not target_arg_id:
        source_arg_id = str(fallacy.get("source_arg_id") or "")
        if source_arg_id and source_arg_id in _identified_arguments(state):
            target_arg_id = source_arg_id
    for key in ("target_argument", "problematic_quote", "explanation"):
        if target_arg_id:
            break
        target_arg_id = _resolve_target_arg_id(state, fallacy.get(key, ""))
    return target_arg_id


def _write_counter_argument_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write counter-argument results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    strength_map = {"weak": 0.3, "moderate": 0.6, "strong": 0.9}

    # Write ALL LLM-generated counter-arguments
    llm_cas = output.get("llm_counter_arguments", [])
    if isinstance(llm_cas, list) and llm_cas:
        for llm_ca in llm_cas:
            if not isinstance(llm_ca, dict) or not llm_ca.get("counter_argument"):
                continue
            target = str(llm_ca.get("target_argument", ""))[:200]
            counter_text = str(llm_ca.get("counter_argument", ""))
            strategy_name = str(llm_ca.get("strategy_used", "unknown"))
            # (#294) Use evaluation score if available, else fallback to strength map
            evaluation = llm_ca.get("evaluation", {})
            if isinstance(evaluation, dict) and "overall_score" in evaluation:
                score = float(evaluation["overall_score"])
            else:
                score = strength_map.get(str(llm_ca.get("strength", "")).lower(), 0.5)
            # G6 (#1180): persist the validation verdict (ValidationResult shape)
            # when the evaluator populated it. Surface-only — absent if the
            # evaluator did not run (no fabrication).
            validation = llm_ca.get("validation")
            if not isinstance(validation, dict):
                validation = None
            arg_id = _resolve_target_arg_id(state, target)
            state.add_counter_argument(
                target,
                counter_text,
                strategy_name,
                score,
                target_arg_id=arg_id,
                validation=validation,
            )
        return

    # Backward compat: single LLM counter-argument
    llm_ca = output.get("llm_counter_argument")
    if isinstance(llm_ca, dict) and llm_ca.get("counter_argument"):
        target = str(llm_ca.get("target_argument", ""))[:200]
        counter_text = str(llm_ca.get("counter_argument", ""))
        strategy_name = str(llm_ca.get("strategy_used", "unknown"))
        score = strength_map.get(str(llm_ca.get("strength", "")).lower(), 0.5)
        validation = llm_ca.get("validation")
        if not isinstance(validation, dict):
            validation = None
        arg_id = _resolve_target_arg_id(state, target)
        state.add_counter_argument(
            target,
            counter_text,
            strategy_name,
            score,
            target_arg_id=arg_id,
            validation=validation,
        )
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
    arg_id = _resolve_target_arg_id(state, original)
    state.add_counter_argument(
        original, strategy_name, strategy_name, float(score), target_arg_id=arg_id
    )


def _write_jtms_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write JTMS results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    beliefs = output.get("beliefs", {})
    if not isinstance(beliefs, dict):
        return
    for name, belief_data in beliefs.items():
        if isinstance(belief_data, dict):
            valid = belief_data.get("valid")
            justifications = belief_data.get("justifications", [])
        else:
            # Legacy format: belief_data is a string like "True"/"False"/"None"
            valid_str = str(belief_data)
            valid = (
                True
                if valid_str == "True"
                else (False if valid_str == "False" else None)
            )
            justifications = []
        if not isinstance(justifications, list):
            justifications = []
        state.add_jtms_belief(str(name), valid, justifications=justifications)
    # Store retraction cascade chains (#350)
    retraction_chain = output.get("retraction_chain", [])
    if isinstance(retraction_chain, list):
        state.jtms_retraction_chain = retraction_chain


def _write_atms_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write ATMS assumption-based reasoning results to UnifiedAnalysisState (#292).

    Stores each node's environment info as a JTMS belief for compatibility.
    Also stores multi-context hypotheses in state.atms_contexts (#349).
    """
    if not output or not isinstance(output, dict):
        return
    environments = output.get("environments", {})
    if not isinstance(environments, dict):
        return
    for name, env_data in environments.items():
        if not isinstance(env_data, dict):
            continue
        is_assumption = env_data.get("is_assumption", False)
        env_list = env_data.get("environments", [])
        # For ATMS, "valid" = has at least one consistent environment
        valid = len(env_list) > 0
        justifications = [f"assumption_env:{sorted(e)}" for e in env_list[:5]]
        state.add_jtms_belief(f"ATMS:{name}", valid, justifications=justifications)
    # Store summary metadata
    state.add_jtms_belief(
        "ATMS:summary",
        True,
        justifications=[
            f"assumptions={output.get('assumption_count', 0)}",
            f"nodes={output.get('node_count', 0)}",
            f"consistent_derivations={len(output.get('consistent_derivations', []))}",
            f"contradictions={'yes' if output.get('has_contradictions') else 'no'}",
        ],
    )
    # Store multi-context hypotheses (#349)
    atms_contexts = output.get("atms_contexts", [])
    if isinstance(atms_contexts, list):
        state.atms_contexts = atms_contexts


def _write_debate_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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
            # G8 (#1184): scheme-ground each exchange. The LLM produces point/
            # rebuttal; we attach a deterministic Walton-scheme classification
            # (fail-loud: no match → scheme stays None, never fabricated #1019).
            # The debatable claim is the POINT (what Agent A defends) — that is
            # what the scheme classifies.
            try:
                from argumentation_analysis.agents.core.debate.argumentation_schemes import (
                    classify_scheme,
                )
            except ImportError:
                classify_scheme = None  # type: ignore[assignment]
            for ex in key_exchanges:
                if isinstance(ex, dict):
                    point = str(ex.get("point", ""))
                    rebuttal = str(ex.get("rebuttal", ""))
                    entry: dict[str, Any] = {"point": point, "rebuttal": rebuttal}
                    if classify_scheme is not None:
                        scheme = classify_scheme(point or rebuttal)
                        if scheme is not None:
                            entry["scheme"] = scheme.label
                            entry["scheme_key"] = scheme.key
                            entry["critical_question"] = (
                                scheme.critical_questions[0]
                                if scheme.critical_questions
                                else ""
                            )
                    exchanges.append(entry)
    state.add_debate_transcript(
        topic=topic,
        exchanges=exchanges,
        winner=str(winner) if winner is not None else None,
    )


def _write_governance_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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

    # Determine winner from vote result, LLM assessment, or conflict resolution
    winner = "N/A"
    vote_result = output.get("vote_result", {})
    if isinstance(vote_result, dict) and vote_result.get("winner"):
        winner = str(vote_result["winner"])
        # (#294) Merge Copeland scores into scores dict
        copeland_scores = vote_result.get("copeland_scores", {})
        if isinstance(copeland_scores, dict):
            for agent, cscore in copeland_scores.items():
                scores[str(agent)] = float(cscore)
    elif llm_gov.get("recommended_resolution"):
        winner = str(llm_gov["recommended_resolution"])
    elif output.get("resolutions"):
        resolutions = output["resolutions"]
        if isinstance(resolutions, list) and resolutions:
            winner = str(resolutions[0].get("resolution_type", "N/A"))

    # Track E #1281 — propagate the honest origin signal: an LLM-assessed
    # verdict is not a genuine multi-agent deliberation, and the restitution
    # must not dress it as procedural legitimacy. extraction_method is computed
    # by _invoke_governance (invoke_callables.py:1746) as "llm" | "heuristic".
    extraction_method = output.get("extraction_method")
    if not isinstance(extraction_method, str):
        extraction_method = None

    state.add_governance_decision(
        method=str(recommended),
        winner=winner,
        scores=scores,
        extraction_method=extraction_method,
    )


def _write_camembert_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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


def _write_hierarchical_fallacy_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write hierarchical taxonomy-guided fallacy results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    fallacies = output.get("fallacies", [])
    if not isinstance(fallacies, list):
        return
    for f in fallacies:
        if not isinstance(f, dict):
            continue
        fallacy_type = f.get("type", f.get("fallacy_type", "unknown"))
        # G5 (#1186): per-family FR explanation. The LLM descent often returns
        # an empty explanation; resolve the family template here rather than
        # leaving a bare/generic line. Fail-loud (#1019): unknown families keep
        # whatever the LLM produced (possibly "") — never a fabricated template.
        justification = f.get("explanation", "")
        if not justification:
            try:
                from argumentation_analysis.adapters.french_fallacy_adapter import (
                    justify_fallacy,
                )

                template = justify_fallacy(str(fallacy_type))
                if template:
                    justification = template
            except ImportError:
                pass  # adapter unavailable — keep LLM explanation as-is
        taxonomy_pk = f.get("taxonomy_pk", "")
        confidence = f.get("confidence", 0.0)
        trace = f.get("navigation_trace", [])
        family = f.get("family", "")
        taxonomy_path = f.get("taxonomy_path", "")
        full_justification = justification
        if taxonomy_pk:
            full_justification += f" [taxonomy:{taxonomy_pk}]"
        if confidence:
            full_justification += f" [confidence:{confidence:.2f}]"
        if trace:
            full_justification += f" [trace:{'>'.join(trace)}]"
        # Resolve target argument through the resolution shared with the
        # conversational lane (#1633 site 3) — see
        # ``resolve_fallacy_target_arg_id`` for the order and its rationale.
        target_arg_id = resolve_fallacy_target_arg_id(state, f)
        state.add_fallacy(
            fallacy_type=fallacy_type,
            justification=full_justification,
            target_arg_id=target_arg_id,
            family=family,
            taxonomy_path=taxonomy_path,
        )

    # FB-35 (#1121): state-level fail-loud marker when the agentic descent was
    # cost-capped (partial fallacy coverage). The phase output carries
    # degraded/last_error from the invoke layer; surface it on the state trace
    # so the spectacular report + convergence layer see the degradation
    # (anti-theater #1019: never a silent partial/truncated outcome).
    if output.get("degraded"):
        state.add_trace_entry(
            phase="hierarchical_fallacy",
            agent="FallacyDetector",
            reacts_to=["extract"],
            summary=(
                "DEGRADED: "
                + str(output.get("last_error", "descent budget exceeded"))
                + " — fallacy coverage is PARTIAL (descent cost-capped)."
            ),
        )


def _write_semantic_index_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
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


def _write_speech_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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


def _write_ranking_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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


def _write_aspic_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write ASPIC+ analysis results to UnifiedAnalysisState."""
    _record_structured_arg_status(state, "aspic_plus_reasoning", output, ctx)
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


def _write_belief_revision_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
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


def _write_dialogue_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write dialogue protocol results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    topic = str(output.get("topic", ""))
    outcome = str(output.get("outcome", "unknown"))
    trace = output.get("dialogue_trace", [])
    if not isinstance(trace, list):
        trace = []
    state.add_dialogue_result(topic, outcome, trace)


def _write_probabilistic_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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


def _write_bipolar_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write bipolar argumentation results to UnifiedAnalysisState."""
    _record_structured_arg_status(state, "bipolar_argumentation", output, ctx)
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


def _write_aba_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write ABA reasoning results to UnifiedAnalysisState (stored as Dung framework).

    #1648 Wave-2 site 1: ABA has a distinctive piece of data — the
    ``contraries`` mapping (assumption → its contrary) — that the handler
    computes and the writer used to drop on the floor. The native Dung
    projection has no slot for it, so we attach a strictly-additive
    ``formalism_specific`` sidecar to the entry dict without touching the
    ``attacks`` / ``extensions`` / ``arguments`` projections. The 12 readers
    of ``dung_frameworks`` (pattern_mining, deep_synthesis_agent, act2/3
    restitution, visualization, …) are not migrated: a downstream reader
    that wants the contraries reads ``entry["formalism_specific"]["contraries"]``.
    """
    _record_structured_arg_status(state, "aba_reasoning", output, ctx)
    if not output or not isinstance(output, dict):
        return
    assumptions = output.get("assumptions", [])
    extensions = output.get("extensions", [])
    if not isinstance(assumptions, list):
        assumptions = []
    df_id = state.add_dung_framework(
        name=f"aba_{output.get('semantics', 'preferred')}",
        arguments=assumptions,
        attacks=[],
        extensions={"aba_extensions": extensions},
    )
    # #1648 Wave-2 sidecar: preserve the contraries the handler echoes
    # under ``output["contraries"]``. Empty mapping ⇒ sidecar still present
    # but with empty dict (so readers can detect "handler ran, contraries
    # not supplied" vs. "writer dropped the field").
    contraries = output.get("contraries")
    if isinstance(contraries, dict) and contraries:
        state.dung_frameworks[df_id]["formalism_specific"] = {
            "contraries": dict(contraries),
        }


def _write_adf_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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


def _write_fact_extraction_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write fact extraction results to state (populates extracts + base fields)."""
    if not output or not isinstance(output, dict):
        return
    # Write claims to extracts (with source quotes when available)
    claims = output.get("claims", [])
    if isinstance(claims, list):
        for claim in claims:
            if isinstance(claim, dict):
                text = claim.get("text", "").strip()
                quote = claim.get("source_quote", "")
                if text:
                    entry = {"type": "claim", "content": text}
                    if quote:
                        entry["source_quote"] = quote
                    state.extracts.append(entry)
            elif isinstance(claim, str) and claim.strip():
                state.extracts.append({"type": "claim", "content": claim.strip()})
    # Populate base identified_arguments from LLM extraction
    arguments = output.get("arguments", [])
    if isinstance(arguments, list):
        for arg in arguments:
            if isinstance(arg, dict):
                text = arg.get("text", "").strip()
                quote = arg.get("source_quote", "")
                if text:
                    arg_text = text
                    if quote:
                        arg_text = f'{text} [quote: "{quote[:100]}"]'
                    state.add_argument(arg_text)
            elif isinstance(arg, str) and arg.strip():
                state.add_argument(arg.strip())
    # NOTE: Fallacy detection removed from fact_extraction (issue #179).
    # Fallacies are the sole responsibility of hierarchical_fallacy_detection,
    # which uses deep taxonomy navigation for precise identification.
    # #1290 — surface the explicit extraction status so the pipeline and
    # restitution can tell a genuine "LLM succeeded, found 0 args" from a
    # "LLM failed after retries, heuristic-claims fallback". A silent ``[]``
    # starves downstream (FOL/Dung/Modal/Acte II/III) masquerading as an empty
    # corpus (#1019). Method "llm" + status "ok" = real extraction; method
    # "heuristic" + status "failed:<reason>" = loud failure.
    extraction_status = output.get("extraction_status")
    if isinstance(extraction_status, str) and extraction_status:
        state.add_task(f"[extraction_status] {extraction_status}")
    # Set summary as analysis task if present
    summary = output.get("summary", "")
    if summary and isinstance(summary, str):
        state.add_task(f"Fact extraction: {summary[:200]}")


def _write_propositional_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write propositional logic analysis results to UnifiedAnalysisState.

    #1208 (FP-10): forward the real PySAT model + axiom/query counts so the
    persisted entry carries a genuine solver witness (not a fabricated
    ``{p1: True}`` placeholder).
    """
    if not output or not isinstance(output, dict):
        return
    formulas = output.get("formulas", [])
    satisfiable = output.get("satisfiable", False)
    model = output.get("model", {})
    if not isinstance(formulas, list):
        formulas = []
    if not isinstance(model, dict):
        model = {}
    kwargs: dict[str, Any] = {}
    if "axiom_count" in output:
        kwargs["axiom_count"] = output["axiom_count"]
    if "query_count" in output:
        kwargs["query_count"] = output["query_count"]
    if output.get("message"):
        kwargs["message"] = output["message"]
    state.add_propositional_analysis_result(
        formulas, bool(satisfiable), model, **kwargs
    )


def _write_fol_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write FOL reasoning results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    formulas = output.get("formulas", [])
    consistent = output.get("consistent")  # None = unverified, True/False = verified
    inferences = output.get("inferences", [])
    confidence = output.get("confidence", 0.0)
    if not isinstance(formulas, list):
        formulas = []
    if not isinstance(inferences, list):
        inferences = []
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    # Preserve None (unverified) vs True (consistent) vs False (inconsistent).
    # bool(None) == False would silently conflate "unknown" with "inconsistent" (#1019).
    fol_status = output.get("fol_status")
    raw_msg = output.get("message")
    # Track B #1278: surface the honest status token when the FOL axis is
    # unavailable (no-translation / parse-fail), so the restitution can mark
    # it honestly instead of silence or a fabricated "consistent" finding
    # (#1019). Decided/unverified keep the prover's own message.
    if isinstance(fol_status, str) and fol_status.startswith("unavailable:"):
        status_message: Optional[str] = fol_status
    elif isinstance(raw_msg, str):
        status_message = raw_msg
    else:
        status_message = None
    state.add_fol_analysis_result(
        formulas,
        consistent if consistent is not None else None,
        inferences,
        float(confidence),
        message=status_message,
    )
    # Store FOL signature metadata (#348)
    fol_signature = output.get("fol_signature", [])
    if isinstance(fol_signature, list) and fol_signature:
        if not hasattr(state, "fol_signature"):
            state.fol_signature = fol_signature
        else:
            state.fol_signature = fol_signature


def _write_modal_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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
    # Track C #1279: surface the honest status token when the modal axis is
    # unavailable (no-translation / no-solver OOM), mirroring the FOL writer
    # (#1278). A decided/unverified verdict keeps the solver's own message.
    modal_status = output.get("modal_status")
    raw_msg = output.get("message")
    if isinstance(modal_status, str) and modal_status.startswith("unavailable:"):
        status_message: Optional[str] = modal_status
    elif isinstance(raw_msg, str):
        status_message = raw_msg
    else:
        status_message = None
    state.add_modal_analysis_result(
        formulas,
        valid if valid is not None else None,
        modalities,
        message=status_message,
    )


def _write_nl_to_logic_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write NL-to-formal-logic translation results to UnifiedAnalysisState (#173)."""
    if not output or not isinstance(output, dict):
        return
    translations = output.get("translations", [])
    if not isinstance(translations, list):
        return
    for t in translations:
        if isinstance(t, dict) and t.get("formula"):
            state.add_nl_to_logic_translation(
                original_text=t.get("original_text", ""),
                formula=t.get("formula", ""),
                logic_type=t.get("logic_type", "propositional"),
                is_valid=bool(t.get("is_valid", False)),
                variables=t.get("variables", {}),
                confidence=float(t.get("confidence", 0.0)),
            )


def _write_dung_extensions_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write Dung extension computation results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    semantics = str(output.get("semantics", "preferred"))
    extensions = output.get("extensions", {})
    all_extensions = output.get("all_extensions", {})
    arguments = output.get("arguments", [])
    attacks = output.get("attacks", [])
    # Store primary framework with actual arguments and attacks
    state.add_dung_framework(
        name=f"verification_{semantics}",
        arguments=arguments if isinstance(arguments, list) else [],
        attacks=attacks if isinstance(attacks, list) else [],
        extensions=extensions if isinstance(extensions, dict) else {},
    )
    # Store additional semantics if computed
    if isinstance(all_extensions, dict):
        for sem, ext in all_extensions.items():
            if sem != semantics and isinstance(ext, dict) and ext:
                state.add_dung_framework(
                    name=f"verification_{sem}",
                    arguments=arguments if isinstance(arguments, list) else [],
                    attacks=attacks if isinstance(attacks, list) else [],
                    extensions=ext,
                )


def _write_dung_arbitration_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write the Dung-arbitration verdict to UnifiedAnalysisState (#1501 PR2, DoD #4).

    The formal verdict (surviving / eliminated candidates + grounded attacks) is
    stored as a Dung framework named ``dung_arbitration`` via the existing
    ``add_dung_framework`` hook — the sibling pattern used by the SetAF/ABA/Dung
    writers, where formalism-specifics are stuffed into the ``extensions`` dict.
    A trace entry is added so the verdict is auditable in the analysis timeline.

    Passthrough (``enabled=False``) and honest-absent verdicts are still recorded
    (the stage RAN), but carry ``honest_absent=True`` so a downstream report can
    tell "arbitration found nothing genuine to decide" from "arbitration altered
    nothing because it was off".
    """
    if not output or not isinstance(output, dict):
        return
    verdict = output.get("verdict")
    if not isinstance(verdict, dict):
        return
    surviving = verdict.get("surviving_ids") or []
    eliminated = verdict.get("eliminated_ids") or {}
    attacks = verdict.get("attacks") or []
    # Opaque candidate ids are the AF's arguments; attacks are [src, tgt] pairs.
    arguments = [str(c) for c in surviving] + [str(c) for c in eliminated]
    attack_pairs = [
        [str(pair[0]), str(pair[1])]
        for pair in attacks
        if isinstance(pair, (list, tuple)) and len(pair) >= 2
    ]
    state.add_dung_framework(
        name="dung_arbitration",
        arguments=arguments,
        attacks=attack_pairs,
        extensions={
            "surviving_ids": [str(c) for c in surviving],
            "eliminated_ids": {str(k): str(v) for k, v in eliminated.items()},
            "honest_absent": bool(verdict.get("honest_absent", False)),
            "enabled": bool(verdict.get("enabled", False)),
            "input_count": int(verdict.get("input_count", 0)),
            "surviving_count": int(verdict.get("surviving_count", 0)),
        },
    )
    if verdict.get("enabled"):
        state.add_trace_entry(
            phase="dung_arbitration",
            agent="DungArbitrationStage",
            reacts_to=["hierarchical_fallacy"],
            summary=(
                f"Grounded arbitration: {len(surviving)} surviving, "
                f"{len(eliminated)} eliminated"
                + (
                    " (honest-absent: no genuine attack)"
                    if verdict.get("honest_absent")
                    else ""
                )
            ),
        )


def _write_formal_synthesis_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
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


def _write_dl_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write Description Logic results to UnifiedAnalysisState (#86)."""
    if not output or not isinstance(output, dict):
        return
    consistent = output.get("consistent")  # None = unverified (#1019)
    message = str(output.get("message", ""))
    # Preserve None (unverified) vs True (consistent) vs False (inconsistent).
    if consistent is None:
        confidence = 0.0
    else:
        confidence = 1.0 if consistent else 0.0
    state.add_fol_analysis_result(
        formulas=[f"DL: {message}"],
        consistent=consistent,
        inferences=[],
        confidence=confidence,
    )


def _write_cl_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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


def _write_sat_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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


def _write_setaf_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write SetAF results to UnifiedAnalysisState (#87)."""
    _record_structured_arg_status(state, "setaf_reasoning", output, ctx)
    if not output or not isinstance(output, dict):
        return
    state.add_dung_framework(
        name=f"setaf_{output.get('semantics', 'grounded')}",
        arguments=output.get("arguments", []),
        attacks=[],  # set attacks don't map to binary attacks
        extensions={"setaf_extensions": output.get("extensions", [])},
    )


def _write_weighted_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write Weighted AF results to UnifiedAnalysisState (#87)."""
    _record_structured_arg_status(state, "weighted_argumentation", output, ctx)
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


def _write_social_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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


def _write_eaf_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write EAF results to UnifiedAnalysisState (#88)."""
    if not output or not isinstance(output, dict):
        return
    state.add_dung_framework(
        name=f"eaf_{output.get('semantics', 'grounded')}",
        arguments=output.get("arguments", []),
        attacks=[a for a in output.get("attacks", []) if isinstance(a, list)],
        extensions={"eaf_extensions": output.get("extensions", [])},
    )


def _write_delp_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
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


def _write_qbf_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write QBF results to UnifiedAnalysisState (#90)."""
    if not output or not isinstance(output, dict):
        return
    state.add_propositional_analysis_result(
        formulas=[f"QBF: {output.get('formula', '')}"],
        satisfiable=output.get("valid", False),
        model={},
    )


def _write_collaborative_analysis_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write collaborative multi-agent debate results to state (#175)."""
    from argumentation_analysis.orchestration.collaborative_debate import (
        _write_collaborative_to_state,
    )

    _write_collaborative_to_state(output, state, ctx)


def _write_narrative_synthesis_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write narrative synthesis results to UnifiedAnalysisState (#351)."""
    if not output or not isinstance(output, dict):
        return
    narrative = output.get("narrative", "")
    if isinstance(narrative, str) and narrative:
        state.narrative_synthesis = narrative


def _write_deep_synthesis_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write the DeepSynthesisAgent grounded synthesis to UnifiedAnalysisState.

    D1b (#1167 / Epic #1165): the spectacular workflow runs the
    ``deep_synthesis`` phase (DeepSynthesisAgent, ~74s, LLM-conducted grounded
    FB-18 synthesis with [artifact:] citations + value-gates) but no writer
    existed in ``CAPABILITY_STATE_WRITERS`` — the output was dropped and
    ``state.narrative_synthesis`` stayed empty, so Acte III (which reads it
    via ``getattr(state, "narrative_synthesis", None)``) never saw the most
    global component. This writer surfaces it.

    The agent output (see ``_invoke_deep_synthesis``) carries:
      - ``grounded_synthesis`` — the grounded FB-18 prose (the headline);
      - ``value_gates`` — VG1-4 dict (persisted onto workflow_results when
        present, the state has no dedicated attr);
      - ``report`` — the full structured report (kept available on the state
        trace for downstream consumers).
    Empty/unavailable results are left as the empty default so the gap is
    reported honestly (fail-loud, #1108/#1019 — never fabricate here).

    Workflow disjointness (double-writer note): both this writer and
    ``_write_narrative_synthesis_to_state`` (the ``full`` path) set
    ``state.narrative_synthesis``. They are never active in the same run —
    ``narrative_synthesis`` was removed from the ``spectacular`` workflow
    (#1119, replaced by this ``deep_synthesis`` successor), while ``full``
    keeps the sequential ``narrative_synthesis`` phase. So at most one writer
    fires per workflow. No execution guard is added: the disjointness lives
    in the workflow phase sets, and a guard here would duplicate that
    contract (anti-pendule).
    """
    if not output or not isinstance(output, dict):
        return
    grounded = output.get("grounded_synthesis", "")
    if isinstance(grounded, str) and grounded.strip():
        state.narrative_synthesis = grounded
    # Persist the value-gates verdict where the state supports it. The state
    # has no dedicated value_gates attr; workflow_results is the generic bag.
    value_gates = output.get("value_gates")
    if isinstance(value_gates, dict) and value_gates:
        try:
            existing = getattr(state, "workflow_results", None)
            if isinstance(existing, dict):
                existing["deep_synthesis_value_gates"] = value_gates
        except Exception:  # noqa: BLE001 — non-fatal: state may lock the attr
            # Side-channel only (narrative_synthesis is the headline and is
            # already set above); trace at debug so a state-lock regression
            # stays diagnosable rather than silently swallowed.
            logger.debug(
                "deep_synthesis value_gates persistence skipped", exc_info=True
            )


def _write_act2_narrative_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write the Acte II dialectical narrative to UnifiedAnalysisState (#1137).

    Populates ``state.act2_narrative`` — the key the R6 renderer consumes for
    ``RestitutionActs.act2_narrative``. Empty/unavailable results are left as
    the empty default so the renderer reports the gap honestly (fail-loud,
    #1108/#1019 — never fabricate a narrative here).
    """
    if not output or not isinstance(output, dict):
        return
    narrative = output.get("act2_narrative", "")
    if isinstance(narrative, str) and narrative:
        state.act2_narrative = narrative
    # #1608 — persist the degradation motifs so they reach the state instead
    # of dying in the return value (the acts return ``degraded`` as a dict;
    # the invoker surfaces it as ``degraded_reasons``).
    _persist_act_degraded_reasons(state, "act2_narrative", output)


def _persist_act_degraded_reasons(state: Any, capability: str, output: Any) -> None:
    """Persist an act's degradation motifs into ``restitution_acts_degraded``.

    Anti-pendule (#1608): only populated when the act genuinely recorded
    motifs (non-empty dict) — an act that succeeded is never marked degraded
    by default. No-op on states that predate the field (defensive).
    """
    if not isinstance(output, dict):
        return
    reasons = output.get("degraded_reasons")
    if not isinstance(reasons, dict) or not reasons:
        return
    rstd = getattr(state, "restitution_acts_degraded", None)
    if isinstance(rstd, dict):
        rstd[capability] = dict(reasons)


def _write_act1_framing_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write the Acte I framing narrative to UnifiedAnalysisState (#1136).

    Populates ``state.act1_framing`` — the key the R6 renderer consumes for
    ``RestitutionActs.act1_framing``. Empty/unavailable results are left as the
    empty default so the renderer reports the gap honestly (fail-loud,
    #1108/#1019 — never fabricate a framing here).
    """
    if not output or not isinstance(output, dict):
        return
    narrative = output.get("act1_framing", "")
    if isinstance(narrative, str) and narrative:
        state.act1_framing = narrative
    _persist_act_degraded_reasons(state, "act1_framing", output)  # #1608 motifs


def _write_act3_conclusion_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write the Acte III actionable conclusion to UnifiedAnalysisState (#1138).

    Populates ``state.act3_conclusion`` — the key the R6 renderer consumes for
    ``RestitutionActs.act3_conclusion``. Empty/unavailable results are left as
    the empty default so the renderer reports the gap honestly (fail-loud,
    #1108/#1019 — never fabricate a conclusion here).
    """
    if not output or not isinstance(output, dict):
        return
    narrative = output.get("act3_conclusion", "")
    if isinstance(narrative, str) and narrative:
        state.act3_conclusion = narrative
    _persist_act_degraded_reasons(state, "act3_conclusion", output)  # #1608 motifs


def _write_text_to_kb_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write TextToKB extraction results to UnifiedAnalysisState (#506)."""
    if not output or not isinstance(output, dict):
        return

    arguments = output.get("arguments", [])
    belief_candidates = output.get("belief_candidates", [])

    add_arg = getattr(state, "add_argument", None)
    if callable(add_arg):
        for arg_data in arguments:
            text = (
                arg_data.get("text", "")
                if isinstance(arg_data, dict)
                else str(arg_data)
            )
            if text:
                add_arg(text)

    add_bs = getattr(state, "add_belief_set", None)
    if callable(add_bs):
        for belief_text in belief_candidates:
            if isinstance(belief_text, str) and belief_text.strip():
                add_bs("fol", belief_text)

    if hasattr(state, "knowledge_base"):
        kb = {"arguments": arguments, "belief_candidates": belief_candidates}
        fol_sig = output.get("fol_signature")
        if fol_sig:
            kb["fol_signature"] = fol_sig
        state.knowledge_base = kb


def _write_kb_to_tweety_to_state(output: Any, state: Any, ctx: dict[str, Any]) -> None:
    """Write KBToTweety translation results to UnifiedAnalysisState (#506, #1643).

    The previous version (#506) silently stored whatever ``dung_framework`` and
    ``aspic_system`` it found in the callable output — which, on every real run,
    was the plugin's ``{"error": "Invalid JSON input"}`` dict (#1643 R761,
    defect 3). Errors serialized in the domain vocabulary are
    indistinguishable from real frameworks downstream; that is the same family
    as #1634, and the writer participated in the failure by storing them.

    New contract (#1643): the callable emits a ``status`` field. We only write
    ``dung_framework`` / ``aspic_system`` into state when the callable returned
    a real framework (``status == "ok"`` and the field is not an error dict).
    Errors are surfaced under ``_*_error`` keys, and the writer preserves
    that distinction instead of folding it into the success path.
    """
    if not output or not isinstance(output, dict):
        return

    status = output.get("status")
    formulas = output.get("formulas", [])

    # Belief-set population is safe — formula dicts are validated by the plugin
    # upstream, so we only need the shape check.
    add_bs = getattr(state, "add_belief_set", None)
    if callable(add_bs):
        for f in formulas:
            formula = f.get("formula", "") if isinstance(f, dict) else str(f)
            logic_type = (
                f.get("logic_type", "propositional")
                if isinstance(f, dict)
                else "propositional"
            )
            if formula:
                add_bs(logic_type, formula)

    if not hasattr(state, "tweety_formulas_from_kb"):
        return

    # Defect-3 fix: refuse to store error dicts in domain-vocabulary fields.
    # Anything coming back as {"error": ...} or absent on a non-ok status is
    # surfaced explicitly via *_error keys, NOT folded into dung_framework /
    # aspic_system.
    is_ok = status == "ok"
    dung_raw = output.get("dung_framework") if is_ok else None
    aspic_raw = output.get("aspic_system") if is_ok else None
    dung_framework = (
        dung_raw if isinstance(dung_raw, dict) and "error" not in dung_raw else None
    )
    aspic_system = (
        aspic_raw if isinstance(aspic_raw, dict) and "error" not in aspic_raw else None
    )

    payload: Dict[str, Any] = {
        "formulas": formulas,
        "formula_count": output.get("formula_count", len(formulas)),
        "status": status,
    }
    if dung_framework is not None:
        payload["dung_framework"] = dung_framework
    else:
        dung_error = output.get("dung_error")
        if dung_error:
            payload["dung_error"] = dung_error
    if aspic_system is not None:
        payload["aspic_system"] = aspic_system
    else:
        aspic_error = output.get("aspic_error")
        if aspic_error:
            payload["aspic_error"] = aspic_error
    batch_error = output.get("batch_error")
    if batch_error:
        payload["batch_error"] = batch_error

    state.tweety_formulas_from_kb = payload


def _write_tweety_interpretation_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write TweetyInterpretation NL results to UnifiedAnalysisState (#506)."""
    if not output or not isinstance(output, dict):
        return

    interpretation = output.get("interpretation", "")
    if isinstance(interpretation, str) and interpretation:
        add_extract = getattr(state, "add_extract", None)
        if callable(add_extract):
            add_extract("formal_interpretation", interpretation)
        elif hasattr(state, "formal_interpretation"):
            state.formal_interpretation = interpretation


def _write_external_fol_solver_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write external FOL solver results to UnifiedAnalysisState (#504, #982)."""
    if not output or not isinstance(output, dict):
        return
    solver = output.get("solver", "none")
    consistent = output.get("consistent")
    degraded = output.get("degraded", False)
    if isinstance(state, dict):
        state["external_fol_solver"] = {
            "solver": solver,
            "consistent": consistent,
            "degraded": degraded,
        }
    else:
        if hasattr(state, "fol_analysis_results") and isinstance(
            state.fol_analysis_results, dict
        ):
            state.fol_analysis_results["external_solver"] = solver
            state.fol_analysis_results["external_consistent"] = consistent
            state.fol_analysis_results["external_degraded"] = degraded


def _write_external_modal_solver_to_state(
    output: Any, state: Any, ctx: dict[str, Any]
) -> None:
    """Write external modal solver results to UnifiedAnalysisState (#504, #982)."""
    if not output or not isinstance(output, dict):
        return
    solver = output.get("solver", "none")
    valid = output.get("valid")
    degraded = output.get("degraded", False)
    if isinstance(state, dict):
        state["external_modal_solver"] = {
            "solver": solver,
            "valid": valid,
            "degraded": degraded,
        }
    else:
        if hasattr(state, "modal_analysis_results") and isinstance(
            state.modal_analysis_results, dict
        ):
            state.modal_analysis_results["external_solver"] = solver
            state.modal_analysis_results["external_valid"] = valid
            state.modal_analysis_results["external_degraded"] = degraded


CAPABILITY_STATE_WRITERS: Dict[str, Any] = {
    "argument_quality": _write_quality_to_state,
    "counter_argument_generation": _write_counter_argument_to_state,
    "belief_maintenance": _write_jtms_to_state,
    "atms_reasoning": _write_atms_to_state,
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
    "dung_arbitration": _write_dung_arbitration_to_state,
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
    "collaborative_analysis": _write_collaborative_analysis_to_state,
    "nl_to_logic_translation": _write_nl_to_logic_to_state,
    "narrative_synthesis": _write_narrative_synthesis_to_state,
    "deep_synthesis": _write_deep_synthesis_to_state,
    "act2_narrative": _write_act2_narrative_to_state,
    "act1_framing": _write_act1_framing_to_state,
    "act3_conclusion": _write_act3_conclusion_to_state,
    "nl_extraction": _write_text_to_kb_to_state,
    "kb_to_tweety": _write_kb_to_tweety_to_state,
    "formal_result_interpretation": _write_tweety_interpretation_to_state,
    "external_fol_solving": _write_external_fol_solver_to_state,
    "external_modal_solving": _write_external_modal_solver_to_state,
}
