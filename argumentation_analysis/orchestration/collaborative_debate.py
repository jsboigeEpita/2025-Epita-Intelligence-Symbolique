"""
Collaborative multi-agent debate pipeline.

Addresses #175 finding that multi-round repetition does NOT improve quality
(single-pass 3.33 vs multi-round 3.27). Instead, quality comes from
**inter-agent collaboration** with distinct roles:

1. Extractor: Identifies claims, premises, arguments (fact_extraction)
2. Critic (Skeptic): Challenges each argument, identifies weaknesses
3. Validator (Scholar): Checks logic, finds supporting evidence
4. Devil's Advocate: Generates strongest counter-arguments
5. Synthesizer: Resolves disagreements, produces final assessment

Each agent reads and responds to previous agents' outputs, creating genuine
dialogue instead of independent parallel analysis.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("CollaborativeDebate")


# --- Agent role definitions ---

COLLABORATIVE_ROLES = {
    "critic": {
        "name": "Critic (Skeptic)",
        "system_prompt": (
            "You are a Skeptic analyst. Your role is to critically examine arguments "
            "and identify weaknesses, hidden assumptions, logical gaps, and potential "
            "fallacies. Be rigorous but fair. For each argument, provide:\n"
            "- weakness: what's wrong or missing\n"
            "- severity: low/medium/high\n"
            "- suggestion: how the argument could be strengthened\n"
            "Respond with ONLY a JSON object:\n"
            '{"critiques": [{"argument": "which", "weakness": "text", '
            '"severity": "low|medium|high", "suggestion": "text"}], '
            '"overall_rigor": 1-5, "reasoning": "brief assessment"}'
        ),
    },
    "validator": {
        "name": "Validator (Scholar)",
        "system_prompt": (
            "You are a Scholar validator. Your role is to verify arguments against "
            "known evidence, check logical consistency, and find supporting or "
            "contradicting evidence. You have access to the Critic's assessment. "
            "For each argument, assess:\n"
            "- evidence_status: supported/unsupported/mixed\n"
            "- logical_validity: valid/invalid/partial\n"
            "- confidence: 0.0-1.0\n"
            "Respond with ONLY a JSON object:\n"
            '{"validations": [{"argument": "which", "evidence_status": "status", '
            '"logical_validity": "validity", "confidence": 0.0-1.0, '
            '"evidence_notes": "supporting/contradicting info"}], '
            '"overall_validity": 0.0-1.0, "reasoning": "brief assessment"}'
        ),
    },
    "devils_advocate": {
        "name": "Devil's Advocate",
        "system_prompt": (
            "You are a Devil's Advocate. Your role is to generate the strongest "
            "possible counter-arguments, considering the Critic's weaknesses and "
            "the Validator's evidence assessment. Target the most vulnerable "
            "arguments first. Use strategies: reductio ad absurdum, counter-example, "
            "distinction, reformulation, or concession+pivot.\n"
            "Respond with ONLY a JSON object:\n"
            '{"counter_arguments": [{"target": "which argument", '
            '"strategy": "strategy name", "counter": "the counter-argument", '
            '"strength": "weak|moderate|strong"}], '
            '"most_vulnerable": "which argument is weakest", '
            '"reasoning": "brief assessment"}'
        ),
    },
    "synthesizer": {
        "name": "Synthesizer",
        "system_prompt": (
            "You are a Synthesis moderator. You have read the outputs of the "
            "Critic, Validator, and Devil's Advocate. Your role is to:\n"
            "1. Resolve disagreements between agents\n"
            "2. Identify arguments that survived all challenges\n"
            "3. Note new insights that emerged from the debate\n"
            "4. Produce a final quality assessment\n"
            "Respond with ONLY a JSON object:\n"
            '{"surviving_arguments": [{"argument": "text", "confidence": 0.0-1.0, '
            '"survived_challenges": ["list of challenges it survived"]}], '
            '"defeated_arguments": [{"argument": "text", "defeated_by": "who/what"}], '
            '"new_insights": ["insight not obvious from initial analysis"], '
            '"consensus_areas": ["where all agents agreed"], '
            '"unresolved_disputes": ["where agents still disagree"], '
            '"final_quality_score": 1-5, '
            '"reasoning": "overall synthesis assessment"}'
        ),
    },
}


async def _invoke_collaborative_analysis(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Run a collaborative multi-agent analysis with 4 distinct agent roles.

    Each agent reads previous agents' outputs, creating genuine inter-agent
    dialogue. Uses the LLM to simulate each agent role sequentially.

    Returns a dict with per-role outputs and final synthesis.
    """
    from openai import AsyncOpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return _fallback_collaborative(input_text, context)

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    # Gather upstream context
    extract_output = context.get("phase_extract_output", {})
    quality_output = context.get("phase_quality_output", {})
    arguments = (
        extract_output.get("arguments", []) if isinstance(extract_output, dict) else []
    )
    claims = (
        extract_output.get("claims", []) if isinstance(extract_output, dict) else []
    )

    # Build argument summary for agents
    arg_lines = []
    for i, a in enumerate(arguments[:8]):
        text = a.get("text", str(a)) if isinstance(a, dict) else str(a)
        arg_lines.append(f"A{i + 1}. {text}")
    if not arg_lines:
        for i, c in enumerate(claims[:8]):
            text = c.get("text", str(c)) if isinstance(c, dict) else str(c)
            arg_lines.append(f"C{i + 1}. {text}")
    if not arg_lines:
        # Sentence split fallback
        sentences = [s.strip() for s in input_text.split(".") if len(s.strip()) > 15]
        for i, s in enumerate(sentences[:6]):
            arg_lines.append(f"S{i + 1}. {s}")

    argument_text = "\n".join(arg_lines) if arg_lines else input_text[:1500]

    # Quality context if available
    quality_summary = ""
    if isinstance(quality_output, dict):
        per_arg = quality_output.get("per_argument_scores", {})
        if per_arg:
            quality_lines = []
            for arg_id, scores in per_arg.items():
                overall = scores.get("note_finale", 0)
                quality_lines.append(f"  {arg_id}: {overall:.1f}/10")
            quality_summary = "\nQuality scores:\n" + "\n".join(quality_lines)

    results = {}
    accumulated_context = f"ARGUMENTS to analyze:\n{argument_text}{quality_summary}"

    # --- Phase 1: Critic ---
    critic_output = await _run_agent_role(
        client, model_id, "critic", accumulated_context
    )
    results["critic"] = critic_output
    accumulated_context += (
        f"\n\nCRITIC ASSESSMENT:\n{json.dumps(critic_output, default=str)[:1500]}"
    )

    # --- Phase 2: Validator ---
    validator_output = await _run_agent_role(
        client, model_id, "validator", accumulated_context
    )
    results["validator"] = validator_output
    accumulated_context += (
        f"\n\nVALIDATOR ASSESSMENT:\n{json.dumps(validator_output, default=str)[:1500]}"
    )

    # --- Phase 3: Devil's Advocate ---
    da_output = await _run_agent_role(
        client, model_id, "devils_advocate", accumulated_context
    )
    results["devils_advocate"] = da_output
    accumulated_context += (
        f"\n\nDEVIL'S ADVOCATE:\n{json.dumps(da_output, default=str)[:1500]}"
    )

    # --- Phase 4: Synthesizer ---
    synthesis_output = await _run_agent_role(
        client, model_id, "synthesizer", accumulated_context
    )
    results["synthesis"] = synthesis_output

    # Build final result
    final_score = 3.0
    if isinstance(synthesis_output, dict):
        final_score = float(synthesis_output.get("final_quality_score", 3.0))

    new_insights = []
    if isinstance(synthesis_output, dict):
        new_insights = synthesis_output.get("new_insights", [])

    surviving = []
    if isinstance(synthesis_output, dict):
        surviving = synthesis_output.get("surviving_arguments", [])

    defeated = []
    if isinstance(synthesis_output, dict):
        defeated = synthesis_output.get("defeated_arguments", [])

    return {
        "agent_outputs": results,
        "final_quality_score": final_score,
        "new_insights": new_insights,
        "surviving_arguments": surviving,
        "defeated_arguments": defeated,
        "agents_involved": list(COLLABORATIVE_ROLES.keys()),
        "interaction_type": "sequential_collaborative",
    }


async def _run_agent_role(
    client: Any,
    model_id: str,
    role: str,
    accumulated_context: str,
) -> Dict[str, Any]:
    """Run a single agent role via LLM and parse JSON response."""
    role_def = COLLABORATIVE_ROLES[role]
    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": role_def["system_prompt"]},
                {"role": "user", "content": accumulated_context},
            ],
        )
        raw = response.choices[0].message.content or ""
        return _parse_json_response(raw, role)
    except Exception as e:
        logger.warning(f"Agent role '{role}' failed: {e}")
        return {"error": str(e), "role": role}


def _parse_json_response(raw: str, role: str) -> Dict[str, Any]:
    """Parse a JSON response from an LLM, handling markdown fences."""
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed for {role}: {e}")
    return {"raw_response": raw[:500], "role": role, "parse_error": True}


def _fallback_collaborative(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback when no API key is available — heuristic-only analysis."""
    extract_output = context.get("phase_extract_output", {})
    arguments = (
        extract_output.get("arguments", []) if isinstance(extract_output, dict) else []
    )

    surviving = []
    for a in arguments[:6]:
        text = a.get("text", str(a)) if isinstance(a, dict) else str(a)
        surviving.append(
            {"argument": text, "confidence": 0.5, "survived_challenges": []}
        )

    return {
        "agent_outputs": {},
        "final_quality_score": 3.0,
        "new_insights": ["No API key available — heuristic fallback used"],
        "surviving_arguments": surviving,
        "defeated_arguments": [],
        "agents_involved": [],
        "interaction_type": "fallback_heuristic",
    }


def _write_collaborative_to_state(output: Any, state: Any, ctx: Dict[str, Any]) -> None:
    """Write collaborative debate results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return

    # Store as a debate transcript with collaborative metadata
    exchanges = []
    agent_outputs = output.get("agent_outputs", {})
    for role_name, role_output in agent_outputs.items():
        if isinstance(role_output, dict) and not role_output.get("error"):
            exchanges.append(
                {
                    "agent": role_name,
                    "assessment": json.dumps(role_output, default=str)[:500],
                }
            )

    if hasattr(state, "add_debate_transcript"):
        state.add_debate_transcript(
            topic="collaborative_multi_agent_analysis",
            exchanges=exchanges,
            winner=None,
        )

    # Store new insights as workflow results
    if hasattr(state, "set_workflow_results"):
        state.set_workflow_results(
            "collaborative_analysis",
            {
                "final_quality_score": output.get("final_quality_score", 0),
                "new_insights": output.get("new_insights", []),
                "surviving_count": len(output.get("surviving_arguments", [])),
                "defeated_count": len(output.get("defeated_arguments", [])),
                "agents_involved": output.get("agents_involved", []),
            },
        )


def build_collaborative_analysis_workflow():
    """Build the collaborative multi-agent analysis workflow.

    Pipeline:
        extract → quality → collaborative_analysis

    The collaborative_analysis phase internally runs 4 agent roles
    (critic, validator, devil's advocate, synthesizer) sequentially,
    with each reading the previous agents' outputs.
    """
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

    return (
        WorkflowBuilder("collaborative_analysis")
        .add_phase("extract", capability="fact_extraction", depends_on=[])
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        .add_phase(
            "collaborative",
            capability="collaborative_analysis",
            depends_on=["quality"],
        )
        .build()
    )
