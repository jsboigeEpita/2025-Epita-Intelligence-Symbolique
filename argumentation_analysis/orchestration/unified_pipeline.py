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
import os
from typing import Dict, Any, Optional, List, Tuple

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


# --- Invoke callables for registered components ---
# Each callable: async (input_text: str, context: Dict[str, Any]) -> Any


async def _invoke_quality_evaluator(input_text: str, context: Dict[str, Any]) -> Dict:
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

    if raw_args:
        results = {}
        for i, arg in enumerate(raw_args[:8]):  # Cap at 8 to avoid timeout
            arg_text = arg.get("text", str(arg)) if isinstance(arg, dict) else str(arg)
            if len(arg_text) < 10:
                continue
            arg_id = f"arg_{i+1}"
            result = await asyncio.to_thread(evaluator.evaluate, arg_text)
            if isinstance(result, dict):
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

            # LLM enrichment pass (#208-F): deeper qualitative analysis
            llm_enrichment = await _llm_enrich_quality(results, raw_args)

            output = {
                "per_argument_scores": results,
                "aggregate_score": round(aggregate_score, 2),
                "arguments_evaluated": len(results),
                # Keep top-level keys for state writer compatibility
                "note_finale": aggregate_score,
                "scores_par_vertu": _aggregate_virtue_scores(results),
            }
            if llm_enrichment:
                output["llm_enrichment"] = llm_enrichment
            return output
        # Fallback if no results
        return await asyncio.to_thread(evaluator.evaluate, input_text)
    else:
        return await asyncio.to_thread(evaluator.evaluate, input_text)


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


async def _llm_enrich_quality(
    heuristic_results: Dict[str, Any],
    raw_args: List,
) -> Optional[Dict[str, Any]]:
    """LLM enrichment pass for quality evaluation (#208-F).

    Sends heuristic scores + argument text to LLM for deeper analysis:
    implicit assumptions, reasoning strength, evidence quality.
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
            score_summary.append(
                f"[{arg_id}] score={note:.1f}/9, weakest={weakest}\n"
                f"  Text: {arg_text[:120]}"
            )

        if not score_summary:
            return None

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
                        "4. Suggest how the weakest virtue could be improved\n\n"
                        "Respond with ONLY a JSON object:\n"
                        '{"enrichments": [{"arg_id": "arg_1", '
                        '"implicit_assumptions": ["..."], '
                        '"reasoning_assessment": "strong/moderate/weak", '
                        '"evidence_quality": "strong/moderate/weak/none", '
                        '"improvement_suggestion": "..."}]}'
                    ),
                },
                {"role": "user", "content": "\n\n".join(score_summary)},
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
            return json.loads(text_content[start:end])
    except Exception as e:
        logger.debug(f"LLM quality enrichment skipped: {e}")
    return None


async def _invoke_counter_argument(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke counter-argument analysis via plugin + LLM enrichment."""
    from argumentation_analysis.agents.core.counter_argument.counter_agent import (
        CounterArgumentPlugin,
    )

    plugin = CounterArgumentPlugin()
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

            # Build targets: fallacious arguments first, then weakest
            targets = []
            for f in fallacies[:3]:  # Top 3 fallacies
                if isinstance(f, dict):
                    targets.append(
                        f"[FALLACY: {f.get('fallacy_type', '')}] "
                        f"{f.get('explanation', '')[:100]}"
                    )
            for a in arguments[:3]:  # Top 3 arguments if no fallacies
                text = a.get("text", str(a)) if isinstance(a, dict) else str(a)
                if text and len(targets) < 4:
                    targets.append(text)

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


async def _invoke_debate_analysis(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke debate argument analysis via plugin + LLM adversarial assessment."""
    from argumentation_analysis.agents.core.debate.debate_agent import DebatePlugin

    plugin = DebatePlugin()
    scores_json = plugin.analyze_argument_quality(input_text)
    base_scores = json.loads(scores_json)

    # Enrich with LLM-based adversarial debate assessment
    try:
        client, model_id = _get_openai_client()
        if client:

            # Build adversarial debate from upstream analysis
            extract_output = context.get("phase_extract_output", {})
            raw_arguments = extract_output.get("arguments", [])
            raw_fallacies = extract_output.get("fallacies", [])
            counter_output = context.get("phase_counter_output", {})
            raw_cas = (
                counter_output.get("llm_counter_arguments", [])
                if isinstance(counter_output, dict)
                else []
            )

            def _txt(item):
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

    return base_scores


async def _invoke_governance(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke governance analysis via plugin + LLM-powered deliberation assessment."""
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
    """Invoke JTMS belief maintenance with real dependency network (#208-G, #214).

    Builds a proper belief network from upstream phase outputs:
    - Arguments → beliefs (IN premises, supported claims)
    - Fallacies → retract undermined beliefs via OUT-list
    - Counter-arguments → create competing OUT-list entries
    - Quality scores → modulate justification strength

    Uses JTMSSession with ExtendedBelief for agent source tracking and confidence (#214).
    """
    from argumentation_analysis.services.jtms.extended_belief import JTMSSession

    session = JTMSSession(session_id="pipeline_jtms", owner_agent="unified_pipeline")
    jtms = session.jtms

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
        fallacy_output.get("fallacies", [])
        if isinstance(fallacy_output, dict)
        else []
    )

    # Counter-arguments
    counter_output = context.get("phase_counter_output", {})
    counter_args = (
        counter_output.get("llm_counter_arguments", [])
        if isinstance(counter_output, dict)
        else []
    )

    # ── Build belief names ───────────────────────────────────────────
    def _text(item):
        return (item.get("text", str(item)) if isinstance(item, dict) else str(item))[:80]

    arg_beliefs = [_text(a) for a in raw_args[:10]]
    claim_beliefs = [_text(c) for c in raw_claims[:6]]

    if not arg_beliefs and not claim_beliefs:
        sentences = [s.strip() for s in input_text.split(".") if len(s.strip()) > 10]
        arg_beliefs = [s[:80] for s in sentences[:8]]

    # ── Step 1: Add argument and claim beliefs with agent metadata ────
    for name in arg_beliefs:
        session.add_belief(name, agent_source="extract", confidence=0.7)
    for name in claim_beliefs:
        session.add_belief(name, agent_source="extract", confidence=0.6)

    # ── Step 2: Arguments support claims (dependency network) ────────
    if arg_beliefs and claim_beliefs:
        for claim in claim_beliefs:
            session.add_justification(arg_beliefs, [], claim, agent_source="pipeline")
    elif arg_beliefs:
        conclusion = "overall_argument_validity"
        session.add_belief(conclusion, agent_source="pipeline", confidence=0.5)
        session.add_justification(arg_beliefs, [], conclusion, agent_source="pipeline")

    # ── Step 3: Accept premises (set initial validity) ───────────────
    for name in arg_beliefs:
        session.set_fact(name, True)

    # ── Step 4: Fallacies → retract undermined beliefs + propagation ─
    fallacy_beliefs = []
    for i, f in enumerate(detected_fallacies[:6]):
        if not isinstance(f, dict):
            continue
        fallacy_type = f.get("fallacy_type", f"fallacy_{i+1}")
        fallacy_name = f"FALLACY:{fallacy_type}"[:80]
        session.add_belief(fallacy_name, agent_source="informal", confidence=0.8)
        session.set_fact(fallacy_name, True)
        fallacy_beliefs.append(fallacy_name)

        target_idx = min(i, len(arg_beliefs) - 1) if arg_beliefs else -1
        if target_idx >= 0:
            target_arg = arg_beliefs[target_idx]
            defeat_name = f"defeat:{fallacy_type}→{target_arg[:30]}"[:80]
            session.add_belief(defeat_name, agent_source="informal")
            session.add_justification(
                [fallacy_name], [target_arg], defeat_name, agent_source="informal"
            )
            jtms.set_belief_validity(target_arg, False)

    # ── Step 5: Counter-arguments → competing beliefs ────────────────
    for i, ca in enumerate(counter_args[:4]):
        if not isinstance(ca, dict):
            continue
        ca_text = ca.get("counter_argument", f"counter_arg_{i+1}")[:80]
        target = ca.get("target_argument", "")[:40]
        session.add_belief(ca_text, agent_source="counter", confidence=0.7)
        session.set_fact(ca_text, True)

        if target and any(target.lower() in ab.lower() for ab in arg_beliefs):
            matched = next(
                (ab for ab in arg_beliefs if target.lower() in ab.lower()), None
            )
            if matched:
                rebuttal_name = f"rebuttal:{ca_text[:20]}→{matched[:20]}"[:80]
                session.add_belief(rebuttal_name, agent_source="counter")
                session.add_justification(
                    [ca_text], [matched], rebuttal_name, agent_source="counter"
                )

    # ── Step 6: Quality scores → update belief confidence ─────────────
    for arg_id, scores in per_arg_scores.items():
        if not isinstance(scores, dict):
            continue
        idx = int(arg_id.split("_")[-1]) - 1 if "_" in arg_id else -1
        if 0 <= idx < len(arg_beliefs):
            belief_name = arg_beliefs[idx]
            quality_score = scores.get("note_finale", 0)
            if belief_name in session.extended_beliefs:
                eb = session.extended_beliefs[belief_name]
                eb.confidence = max(eb.confidence, quality_score / 10.0)
                eb.context["quality_score"] = quality_score
                eb.context["weakest_virtue"] = min(
                    scores.get("scores_par_vertu", {"?": 0}),
                    key=scores.get("scores_par_vertu", {"?": 0}).get,
                )

    # ── Build output (backward-compatible + extended metadata) ────────
    beliefs_output = {}
    for name, b in jtms.beliefs.items():
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
        }
        # Add extended metadata from JTMSSession (#214)
        if name in session.extended_beliefs:
            eb = session.extended_beliefs[name]
            entry["agent_source"] = eb.agent_source
            entry["confidence"] = eb.confidence
            if eb.context:
                entry["quality"] = {
                    k: v for k, v in eb.context.items()
                    if k in ("quality_score", "weakest_virtue")
                } or None
                if entry["quality"] is None:
                    del entry["quality"]
        beliefs_output[name] = entry

    # Session consistency check
    consistency = session.check_consistency()

    return {
        "beliefs": beliefs_output,
        "belief_count": len(jtms.beliefs),
        "justified_count": sum(1 for b in jtms.beliefs.values() if b.justifications),
        "valid_count": sum(1 for b in jtms.beliefs.values() if b.valid is True),
        "undermined_count": sum(1 for b in jtms.beliefs.values() if b.valid is False),
        "fallacy_count": len(fallacy_beliefs),
        "counter_argument_count": len([ca for ca in counter_args[:4] if isinstance(ca, dict)]),
        "has_real_dependencies": bool(arg_beliefs and (claim_beliefs or fallacy_beliefs)),
        "session_summary": session.get_session_summary(),
        "consistency": consistency,
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
                fallacy_label = f.get("fallacy_type", f"fallacy_{i}")
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


async def _invoke_ranking(input_text: str, context: Dict[str, Any]) -> Dict:
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

        handler = RankingHandler()
        result = await asyncio.to_thread(handler.rank_arguments, args, attacks, method)
        # Enrich Tweety result with strength justification
        if isinstance(result, dict) and "ranking" in result:
            result = _enrich_ranking_with_justification(result, args, attacks, context)
        return result
    except Exception as e:
        logger.info(f"Ranking handler unavailable ({e}), using Python fallback")
        result = _python_ranking_fallback(args, attacks, method)
        return _enrich_ranking_with_justification(result, args, attacks, context)


async def _invoke_bipolar(input_text: str, context: Dict[str, Any]) -> Dict:
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


def _python_aspic_fallback(
    args: List[str],
    strict: List[str],
    defeasible: List[str],
    fallacies: List,
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
            matching_fallacies = [
                f.get("fallacy_type", "unknown")
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


async def _invoke_aspic(input_text: str, context: Dict[str, Any]) -> Dict:
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
                ft = f.get("fallacy_type", "unknown")
                defeasible.append(f"detected({ft[:30]}) => undermined_{j+1}")

    axioms = context.get("axioms")

    try:
        from argumentation_analysis.agents.core.logic.aspic_handler import ASPICHandler

        handler = ASPICHandler()
        return await asyncio.to_thread(
            handler.analyze_aspic_framework, strict, defeasible, axioms
        )
    except Exception as e:
        logger.info(f"ASPIC+ handler unavailable ({e}), using Python fallback")
        return _python_aspic_fallback(args, strict, defeasible, fallacies, context)


async def _invoke_belief_revision(input_text: str, context: Dict[str, Any]) -> Dict:
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
                    ft = fallacies[0].get("fallacy_type", "")
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

        handler = BeliefRevisionHandler()
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


async def _invoke_probabilistic(input_text: str, context: Dict[str, Any]) -> Dict:
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
        # Build substantive dialogue using fallacies as attack moves
        extract_output = context.get("phase_extract_output", {})
        raw_fallacies = extract_output.get("fallacies", [])

        # Enrich opponent moves with fallacy-based attacks
        fallacy_attacks = []
        for f in raw_fallacies[:5]:
            if isinstance(f, dict):
                ftype = f.get("type", "unknown")
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

        initializer = TweetyInitializer()
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
    votes: Dict,
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
                ftype = f.get("fallacy_type", "unknown")
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
    epistemic = {}
    believed_args = []
    disbelieved_args = []
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


async def _invoke_eaf(input_text: str, context: Dict[str, Any]) -> Dict:
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

        initializer = TweetyInitializer()
        handler = EAFHandler(initializer)
        return await asyncio.to_thread(
            handler.analyze_epistemic_framework, args, attacks, beliefs, semantics
        )
    except Exception as e:
        logger.info(f"EAF handler unavailable ({e}), using Python fallback")
        return _python_eaf_fallback(args, attacks, semantics, context)


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


# --- Hierarchical taxonomy-guided fallacy detection (#84) ---


async def _invoke_hierarchical_fallacy(
    input_text: str, context: Dict[str, Any]
) -> Dict:
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


async def _invoke_fact_extraction(input_text: str, context: Dict[str, Any]) -> Dict:
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
            nl_output.get("translations", [])
            if isinstance(nl_output, dict)
            else []
        )
        pl_translations = [
            t for t in nl_translations
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
            "argument_mapping": argument_mapping or {f"p{i+1}": a[:60] for i, a in enumerate(args)},
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
            "argument_mapping": argument_mapping or {f"p{i+1}": a[:60] for i, a in enumerate(args)},
            "fallback": "python",
        }


async def _invoke_fol_reasoning(input_text: str, context: Dict[str, Any]) -> Dict:
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
            nl_output.get("translations", [])
            if isinstance(nl_output, dict)
            else []
        )
        fol_translations = [
            t for t in nl_translations
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
                    for t in valid:
                        for f in t.formula.split(";"):
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

    inferences = []
    # Derive inferences from the structure
    fallacy_output = context.get("phase_hierarchical_fallacy_output", {})
    fallacies = (
        fallacy_output.get("fallacies", []) if isinstance(fallacy_output, dict) else []
    )
    for f in fallacies:
        if isinstance(f, dict):
            inferences.append(
                f"Argument undermined by {f.get('fallacy_type', 'unknown')} fallacy"
            )

    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge()
        belief_set_str = "\n".join(str(f) for f in formulas)
        is_consistent, msg = await asyncio.to_thread(
            bridge.check_consistency, belief_set_str, "first_order"
        )
        return {
            "formulas": formulas,
            "consistent": bool(is_consistent),
            "inferences": inferences,
            "confidence": 0.8 if is_consistent else 0.4,
            "message": msg,
            "logic_type": "first_order",
            "argument_count": len(args),
        }
    except Exception:
        # Fallback: check for contradiction in generated formulas
        has_fallacious = any("Fallacious" in f for f in formulas)
        return {
            "formulas": formulas,
            "consistent": not has_fallacious,
            "inferences": inferences,
            "confidence": 0.6 if not has_fallacious else 0.3,
            "logic_type": "first_order",
            "argument_count": len(args),
            "fallback": "python",
        }


async def _invoke_nl_to_logic(input_text: str, context: Dict[str, Any]) -> Dict:
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
        translations.append({
            "original_text": t.original_text[:200],
            "formula": t.formula,
            "logic_type": t.logic_type,
            "is_valid": t.is_valid,
            "validation_message": t.validation_message,
            "attempts": t.attempts,
            "variables": t.variables,
            "confidence": t.confidence,
        })

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
            if isinstance(overall, (int, float)) and (scores or overall > 0):
                state.add_quality_score(str(arg_id), scores, float(overall))
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
            registry._registrations[
                "counter_argument_agent"
            ].invoke = _invoke_counter_argument
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
        # NL-to-formal-logic translation (#173)
        (
            "nl_to_logic_service",
            ["nl_to_logic_translation"],
            "NL→formal logic with LLM + Tweety validation",
            _invoke_nl_to_logic,
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

    # --- Collaborative multi-agent debate (#175) ---
    try:
        from argumentation_analysis.orchestration.collaborative_debate import (
            _invoke_collaborative_analysis,
        )

        registry.register_service(
            name="collaborative_debate_service",
            service_class=type("collaborative_debate_service", (), {}),
            capabilities=["collaborative_analysis"],
            metadata={
                "description": (
                    "Multi-agent collaborative debate with 4 distinct roles "
                    "(critic, validator, devil's advocate, synthesizer)"
                )
            },
            invoke=_invoke_collaborative_analysis,
        )
        registered.append("collaborative_debate_service")
    except ImportError as e:
        skipped.append(("collaborative_debate_service", str(e)))

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
    """Standard workflow with fact extraction, fallacy detection, and quality-gated counter-arguments.

    CamemBERT Tier 2.5 and hierarchical fallacy detection run as optional
    phases after extraction (#208-J). Downstream phases (quality, counter,
    JTMS) read fallacy results via context['phase_hierarchical_fallacy_output'].
    """
    return (
        WorkflowBuilder("standard_analysis")
        .add_phase("extract", capability="fact_extraction")
        .add_phase(
            "neural_detect",
            capability="neural_fallacy_detection",
            depends_on=["extract"],
            optional=True,
        )
        .add_phase(
            "hierarchical_fallacy",
            capability="hierarchical_fallacy_detection",
            depends_on=["extract"],
            optional=True,
        )
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
        .add_phase(
            "nl_to_logic",
            capability="nl_to_logic_translation",
            depends_on=["extract"],
            optional=True,
        )
        .build()
    )


def build_nl_to_logic_workflow() -> WorkflowDefinition:
    """NL-to-formal-logic pipeline: extract → translate → validate → reason (#173).

    Bridges informal NL analysis and formal reasoning by translating
    extracted arguments into propositional/FOL formulas with Tweety validation.
    """
    return (
        WorkflowBuilder("nl_to_logic_analysis")
        .add_phase("extract", capability="fact_extraction")
        .add_phase(
            "nl_to_logic",
            capability="nl_to_logic_translation",
            depends_on=["extract"],
        )
        .add_phase(
            "pl",
            capability="propositional_logic",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        .add_phase(
            "fol",
            capability="fol_reasoning",
            depends_on=["nl_to_logic"],
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
        .add_phase("extract", capability="fact_extraction")
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
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
            "nl_to_logic": build_nl_to_logic_workflow(),
        }
        # Collaborative multi-agent debate (#175)
        try:
            from argumentation_analysis.orchestration.collaborative_debate import (
                build_collaborative_analysis_workflow,
            )

            WORKFLOW_CATALOG["collaborative"] = build_collaborative_analysis_workflow()
        except Exception as e:
            logger.warning(f"Collaborative workflow not registered: {e}")
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

            WORKFLOW_CATALOG[
                "formal_verification"
            ] = build_formal_verification_workflow()
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
    elif workflow_name == "conversational":
        # Special mode: use ConversationalOrchestrator (#208-L)
        try:
            from argumentation_analysis.orchestration.conversational_orchestrator import (
                run_conversational_analysis,
            )

            conv_result = await run_conversational_analysis(text)

            # Normalize result format for benchmark compatibility (#208-L)
            # Conversational returns {phases: [names], conversation_log, total_messages}
            # Benchmark expects {phases: {dict}, summary: {completed, total, ...}}
            phase_names = conv_result.get("phases", [])
            total_msgs = conv_result.get("total_messages", 0)
            conv_result["summary"] = {
                "completed": len(phase_names),
                "failed": 0,
                "skipped": 0,
                "total": len(phase_names),
                "total_messages": total_msgs,
            }
            conv_result["workflow_name"] = "conversational"
            return conv_result
        except Exception as e:
            logger.warning(
                f"Conversational mode failed ({e}), falling back to standard"
            )
            catalog = get_workflow_catalog()
            workflow = catalog["standard"]
    else:
        catalog = get_workflow_catalog()
        if workflow_name not in catalog:
            raise ValueError(
                f"Unknown workflow '{workflow_name}'. "
                f"Available: {list(catalog.keys()) + ['conversational']}"
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
