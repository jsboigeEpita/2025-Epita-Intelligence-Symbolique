"""#1909: a valid non-argumentative input is a NAMED terminal success.

The #1894 document completed all 39 spectacular phases on a substrate the
extraction itself had classified as factual-but-not-argumentative (zero
``identified_arguments``, material found). The behavior was honest but
operationally wrong: argument-dependent specialists ran anyway, and the
summary read as a full success.

These tests pin the two-sense contract the coordinator named on the issue:
an early stop on a non-argumentative input is a SUCCESS with its reason
named, while an upstream failure keeps failing (#1913). Both produce
``completed == low`` shapes — only the named status discriminates them, so
a test that carries only one sense does not.

All fixtures are synthetic (privacy HARD): an administrative header, never
dataset content. Providers are stubbed at the registry level — zero network,
zero LLM, zero JVM.
"""

import pytest

from argumentation_analysis.core.capability_registry import CapabilityRegistry
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseResult,
    PhaseStatus,
    WorkflowBuilder,
    WorkflowExecutor,
)

ADMIN_HEADER_TEXT = (
    "Session 42 — proces-verbal administratif. Ordre du jour, item 3. "
    "Le secretariat a verifie le quorum et l'ensemble des convocations. "
    "Le document est archive sous la cote 12A. "
    "Prochaine reunion prevue le 15 du mois prochain, meme lieu."
)

NON_ARGUMENTATIVE_EXTRACTION = {
    "arguments": [],
    "claims": [
        "Le secretariat a verifie le quorum et l'ensemble des convocations.",
        "Le document est archive sous la cote 12A.",
        "Prochaine reunion prevue le 15 du mois prochain, meme lieu.",
    ],
    "fallacies": [],
    "summary": "Proces-verbal administratif : materiel factuel, aucun enonce argumentatif.",
    "claim_count": 3,
    "argument_count": 0,
    "extraction_method": "llm",
    "extraction_status": "ok",
}

SUBSTANTIVE_EXTRACTION = {
    "arguments": [
        {
            "text": "La reforme est necessaire car le cout actuel du systeme est insoutenable."
        }
    ],
    "claims": ["Le cout actuel du systeme est insoutenable."],
    "fallacies": [],
    "summary": "Un argument consecutif avec preuve factuelle.",
    "claim_count": 1,
    "argument_count": 1,
    "extraction_method": "llm",
    "extraction_status": "ok",
}

FAILED_EXTRACTION = {
    "arguments": [],
    "claims": ["diagnostic claim"],
    "fallacies": [],
    "summary": "",
    "claim_count": 1,
    "argument_count": 0,
    "extraction_method": "heuristic",
    "extraction_status": "failed:synthetic-auth-error",
}

EXPLICIT_NON_ARGUMENTATIVE = {
    **NON_ARGUMENTATIVE_EXTRACTION,
    "extraction_status": "non_argumentative",
}


def _make_registry(extraction_output, spy):
    async def extract_invoke(text, context):
        return dict(extraction_output)

    async def quality_invoke(text, context):
        spy.append("quality")
        return {"score": 0.5}

    async def counter_invoke(text, context):
        spy.append("counter")
        return {"counter_argument": "synthetic"}

    registry = CapabilityRegistry()
    registry.register_agent(
        name="synthetic_extractor",
        agent_class=type("FE", (), {}),
        capabilities=["fact_extraction"],
        invoke=extract_invoke,
    )
    registry.register_agent(
        name="synthetic_quality",
        agent_class=type("QA", (), {}),
        capabilities=["argument_quality"],
        invoke=quality_invoke,
    )
    registry.register_agent(
        name="synthetic_counter",
        agent_class=type("CA", (), {}),
        capabilities=["counter_argument_generation"],
        invoke=counter_invoke,
    )
    return registry


def _workflow():
    return (
        WorkflowBuilder("nonarg_1909")
        .add_phase("extract", capability="fact_extraction")
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        .build()
    )


# --- sense 1: the early stop is a NAMED terminal success ---------------------


@pytest.mark.asyncio
async def test_non_argumentative_input_stops_argument_dependent_phases():
    """DoD 1: after a non-argumentative extraction, no argument-dependent
    provider is invoked; the stop is named, not a failure block."""
    spy: list = []
    registry = _make_registry(NON_ARGUMENTATIVE_EXTRACTION, spy)
    executor = WorkflowExecutor(registry)
    results = await executor.execute(_workflow(), input_data=ADMIN_HEADER_TEXT)

    assert results["extract"].status == PhaseStatus.COMPLETED
    assert results["extract"].terminal is True
    assert results["extract"].output["extraction_status"] == "non_argumentative"
    assert results["quality"].status == PhaseStatus.SKIPPED
    assert results["counter"].status == PhaseStatus.SKIPPED
    assert spy == [], "no argument-dependent provider may run after the stop"
    assert "non-argumentative" in (results["quality"].error or ""), (
        "the skip reason must NAME the classification — the #1913 failure "
        "wording would make the two senses indistinguishable in the log"
    )


@pytest.mark.asyncio
async def test_non_argumentative_stop_is_a_named_success_not_a_failure():
    """DoD 2 + the coordinator's trap: the pipeline outcome is a named
    non-argumentative status — not failed, not a full success count."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    spy: list = []
    registry = _make_registry(NON_ARGUMENTATIVE_EXTRACTION, spy)
    result = await run_unified_analysis(
        ADMIN_HEADER_TEXT, registry=registry, custom_workflow=_workflow()
    )

    assert result["analysis_outcome"] == {
        "status": "non_argumentative",
        "phase": "extract",
    }
    assert result["summary"]["failed"] == 0
    assert result["summary"]["completed"] == 1
    assert result["summary"]["skipped"] == 2
    workflow_result = result["unified_state"].workflow_results["nonarg_1909"]
    assert workflow_result["document_classification"] == "non_argumentative"


@pytest.mark.asyncio
async def test_explicit_producer_classification_is_honored():
    """A producer that already emits ``non_argumentative`` explicitly (the
    future LLM classifier) gets the same terminal stop — the executor must
    honor the explicit status, not only infer from shape."""
    spy: list = []
    registry = _make_registry(EXPLICIT_NON_ARGUMENTATIVE, spy)
    executor = WorkflowExecutor(registry)
    results = await executor.execute(_workflow(), input_data=ADMIN_HEADER_TEXT)

    assert results["extract"].status == PhaseStatus.COMPLETED
    assert results["extract"].terminal is True
    assert spy == []
    assert results["counter"].status == PhaseStatus.SKIPPED


# --- sense 2: an upstream failure keeps failing (#1913 preserved) ------------


@pytest.mark.asyncio
async def test_extraction_failure_is_not_relabelled_non_argumentative():
    """DoD 3: a foundational extraction failure stays a failure — the zero-args
    shape it shares with the valid classification must not launder it."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    spy: list = []
    registry = _make_registry(FAILED_EXTRACTION, spy)
    result = await run_unified_analysis(
        ADMIN_HEADER_TEXT, registry=registry, custom_workflow=_workflow()
    )

    assert result["analysis_outcome"]["status"] == "failed"
    assert "synthetic-auth-error" in result["analysis_outcome"]["reason"]
    assert result["summary"]["failed"] >= 1


def test_analysis_outcome_terminal_completed_is_not_failure():
    """The outcome normalizer: a COMPLETED+terminal extraction is the
    non-argumentative sense; only FAILED (+ explicit failed: status) fails."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        _analysis_outcome,
    )

    terminal_success = PhaseResult(
        phase_name="extract",
        status=PhaseStatus.COMPLETED,
        capability="fact_extraction",
        output={"extraction_status": "non_argumentative"},
        terminal=True,
    )
    assert _analysis_outcome({"extract": terminal_success}) == {
        "status": "non_argumentative",
        "phase": "extract",
    }


# --- sense 3: a substantive input still gets the complete DAG -----------------


@pytest.mark.asyncio
async def test_substantive_input_runs_the_complete_dag():
    """DoD 6: an extraction that found arguments changes nothing — every
    phase runs, nothing is terminal."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    spy: list = []
    registry = _make_registry(SUBSTANTIVE_EXTRACTION, spy)
    result = await run_unified_analysis(
        ADMIN_HEADER_TEXT, registry=registry, custom_workflow=_workflow()
    )

    assert spy == ["quality", "counter"]
    assert result["analysis_outcome"] == {"status": "ok"}
    assert result["summary"]["completed"] == 3
    assert result["summary"]["failed"] == 0
    assert result["phases"]["extract"].terminal is False
