"""State writers for the unified pipeline.

Each _write_*_to_state function transfers invoke callable output to the
UnifiedAnalysisState. CAPABILITY_STATE_WRITERS maps capability names to
their corresponding writer functions.

Split from unified_pipeline.py (#310).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("UnifiedPipeline")

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
    "CAPABILITY_STATE_WRITERS",
]


def _write_quality_to_state(output, state, ctx) -> None:
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
                state.add_quality_score(
                    str(arg_id), scores, float(overall),
                    llm_assessment=llm_assessment,
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
        state.add_quality_score(arg_id, scores, float(overall))


def _write_counter_argument_to_state(output, state, ctx) -> None:
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
            state.add_counter_argument(target, counter_text, strategy_name, score)
        return

    # Backward compat: single LLM counter-argument
    llm_ca = output.get("llm_counter_argument")
    if isinstance(llm_ca, dict) and llm_ca.get("counter_argument"):
        target = str(llm_ca.get("target_argument", ""))[:200]
        counter_text = str(llm_ca.get("counter_argument", ""))
        strategy_name = str(llm_ca.get("strategy_used", "unknown"))
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


def _write_atms_to_state(output, state, ctx) -> None:
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
        justifications = [
            f"assumption_env:{sorted(e)}" for e in env_list[:5]
        ]
        state.add_jtms_belief(
            f"ATMS:{name}", valid, justifications=justifications
        )
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
        fallacy_type = f.get("type", f.get("fallacy_type", "unknown"))
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
    # Store FOL signature metadata (#348)
    fol_signature = output.get("fol_signature", [])
    if isinstance(fol_signature, list) and fol_signature:
        if not hasattr(state, "fol_signature"):
            state.fol_signature = fol_signature
        else:
            state.fol_signature = fol_signature


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


def _write_nl_to_logic_to_state(output, state, ctx) -> None:
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


def _write_dung_extensions_to_state(output, state, ctx) -> None:
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


def _write_collaborative_analysis_to_state(output, state, ctx) -> None:
    """Write collaborative multi-agent debate results to state (#175)."""
    from argumentation_analysis.orchestration.collaborative_debate import (
        _write_collaborative_to_state,
    )

    _write_collaborative_to_state(output, state, ctx)


CAPABILITY_STATE_WRITERS: Dict[str, Any] = {
    "argument_quality": _write_quality_to_state,
    "counter_argument_generation": _write_counter_argument_to_state,
    "belief_maintenance": _write_jtms_to_state,
    "assumption_based_reasoning": _write_atms_to_state,
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
    "collaborative_analysis": _write_collaborative_analysis_to_state,
    "nl_to_logic_translation": _write_nl_to_logic_to_state,
}
