"""#2763 — the semantic_indexing phase must index the fact-check run's real
upstream arguments.

The fact_check workflow names its phases ``quality_assessment`` and
``fallacy_screen`` and has no extract phase; the phase reader looked only
for ``phase_extract_output`` / ``phase_quality_output`` /
``phase_hierarchical_fallacy_output`` (the full workflow's names), so a
fact-check run indexed zero arguments and still answered ``status='ran'``.

The units a fact-check run actually produces are the belief phase's
premises — ``_invoke_jtms`` tracks them as ``arg_N:<text>`` beliefs, and
``indexing`` declares ``depends_on=["belief_tracking"]``. These witnesses
run the real phase against the fake Kernel Memory transport (reused from
the #2618 module) on fact-check-shaped contexts, plus one run of the real
``build_fact_check_workflow`` through a WorkflowExecutor.
"""

import pytest
from unittest.mock import patch

import argumentation_analysis.orchestration.invoke_callables as ic
from tests.unit.argumentation_analysis.orchestration.test_semantic_index_phase_2618 import (
    _FakeKMTransport,
    _first,
)


def _fact_check_context(premises=None, with_fallacy_screen=True):
    """Context shaped like a real fact_check run: no extract phase,
    quality_assessment output, fallacy_screen output, belief_tracking
    output whose premises are the run's units (``arg_N:<text>``)."""
    beliefs = {}
    for name, text in (premises or {}).items():
        beliefs[name] = {
            "valid": True,
            "content": name,
            "agent_source": "unified_pipeline",
            "confidence": 0.5,
            "context": {"belief_type": "premise", "index": 0, "text": name},
        }
    # Non-premise beliefs a real run also carries — never index units.
    beliefs["Claim générale de l'article"] = {
        "valid": True,
        "content": "Claim générale de l'article",
        "agent_source": "unified_pipeline",
        "confidence": 0.5,
        "context": {"belief_type": "claim", "index": 1, "text": "..."},
    }
    beliefs["defeat:appelautorite→argument un"] = {
        "valid": True,
        "content": "defeat:appelautorite→argument un",
        "agent_source": "fallacy_detector",
        "confidence": 0.8,
        "context": {"defeat_type": "fallacy_undermining", "fallacy": "appelautorite"},
    }
    ctx = {
        "phase_quality_assessment_output": {
            # Whole-text fallback shape (#2444): flat, no per_argument_scores.
            "note_finale": 0.55,
            "scores_par_vertu": {"clarte": 0.6},
        },
        "phase_belief_tracking_output": {"beliefs": beliefs},
    }
    if with_fallacy_screen:
        ctx["phase_fallacy_screen_output"] = {
            # Neural detector shape: type-keyed dict, no per-argument target.
            "detected_fallacies": {
                "appelautorite": {
                    "source": "self_hosted_llm",
                    "confidence": 0.7,
                    "description": "autorité invoquée sans preuve",
                }
            },
            "arguments": {},
            "tiers_used": ["self_hosted_llm"],
        }
    return ctx


_PREMISES = {
    "arg_1:premier argument synthetique du run": "premier argument synthetique du run",
    "arg_2:second argument synthetique du run": "second argument synthetique du run",
}


async def test_fact_check_premises_are_indexed():
    transport = _FakeKMTransport()
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        result = await ic._invoke_semantic_index(
            "texte a fact-checker", _fact_check_context(_PREMISES)
        )

    assert result["status"] == "ran"
    assert result["indexed_count"] == 2
    assert result["arguments_seen"] == 2
    run_name = result["source_name"]
    assert transport.docs[f"{run_name}__arg_1"]["text"] == (
        "premier argument synthetique du run"
    )
    assert transport.docs[f"{run_name}__arg_2"]["text"] == (
        "second argument synthetique du run"
    )
    # Claims and defeats are not argument units.
    assert len(transport.docs) == 2


async def test_premise_enumeration_orders_units_not_dict_order():
    """``arg_10`` is the tenth unit, not the second — the enumeration parsed
    from the belief names orders the indexed list, and the service re-mints
    positional ids (``arg_1``, ``arg_2``) over that order (#1633)."""
    premises = {
        "arg_10:dixieme unite synthetique du run": "dixieme unite synthetique du run",
        "arg_2:deuxieme unite synthetique du run": "deuxieme unite synthetique du run",
    }
    transport = _FakeKMTransport()
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        result = await ic._invoke_semantic_index(
            "texte a fact-checker", _fact_check_context(premises)
        )

    assert result["status"] == "ran"
    assert result["indexed_count"] == 2
    run_name = result["source_name"]
    assert transport.docs[f"{run_name}__arg_1"]["text"] == (
        "deuxieme unite synthetique du run"
    )
    assert transport.docs[f"{run_name}__arg_2"]["text"] == (
        "dixieme unite synthetique du run"
    )


async def test_targetless_neural_fallacies_tag_nothing():
    """The neural detector's type-keyed records carry no per-argument
    target: no argument is tagged fallacious (#1019 — no guess)."""
    transport = _FakeKMTransport()
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        await ic._invoke_semantic_index(
            "texte a fact-checker", _fact_check_context(_PREMISES)
        )

    joined_tags = " ".join(transport._uploaded_tags)
    assert "has_fallacy:true" not in joined_tags
    assert "fallacy_type:" not in joined_tags


async def test_extract_arguments_take_precedence_over_beliefs():
    """In the full workflow both sources exist: the extract arguments
    (untruncated texts) are indexed, never the truncated belief names."""
    ctx = _fact_check_context(_PREMISES)
    ctx["phase_extract_output"] = {
        "arguments": [
            {
                "text": "argument complet non tronque du workflow full",
                "source_quote": "q1",
            }
        ]
    }
    transport = _FakeKMTransport()
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        result = await ic._invoke_semantic_index("requete", ctx)

    assert result["status"] == "ran"
    assert result["indexed_count"] == 1
    run_name = result["source_name"]
    assert transport.docs[f"{run_name}__arg_1"]["text"] == (
        "argument complet non tronque du workflow full"
    )


async def test_no_input_arguments_is_explicit_not_ran():
    """Nothing to index must not read as a successful empty run (#1019):
    no upload, no search, an explicit skipped status."""
    transport = _FakeKMTransport()
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        result = await ic._invoke_semantic_index(
            "texte court", {"phase_quality_output": {"per_argument_scores": {}}}
        )

    assert result["status"] == "skipped: no_input_arguments"
    assert _first(transport, "POST", "/upload") is None
    assert _first(transport, "POST", "/search") is None


async def test_real_fact_check_workflow_feeds_the_indexing_phase():
    """The production workflow end to end: quality_assessment writes its
    output under its own phase name, belief_tracking tracks the run's units,
    and the REAL indexing phase (fake transport) receives them."""
    from argumentation_analysis.core.capability_registry import (
        CapabilityRegistry,
        ComponentType,
    )
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor
    from argumentation_analysis.workflows.fact_check_pipeline import (
        build_fact_check_workflow,
    )

    async def quality_invoke(text, ctx):
        return {"note_finale": 0.55, "scores_par_vertu": {"clarte": 0.6}}

    async def belief_invoke(text, ctx):
        assert "phase_quality_assessment_output" in ctx
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 10]
        beliefs = {}
        for i, s in enumerate(sentences[:2]):
            name = f"arg_{i+1}:{s[:66]}"
            beliefs[name] = {
                "valid": True,
                "content": name,
                "agent_source": "unified_pipeline",
                "confidence": 0.5,
                "context": {"belief_type": "premise", "index": i, "text": name},
            }
        return {"beliefs": beliefs, "belief_count": len(beliefs)}

    async def counter_invoke(text, ctx):
        return {"llm_counter_arguments": []}

    registry = CapabilityRegistry()
    registry.register(
        "quality",
        ComponentType.AGENT,
        capabilities=["argument_quality"],
        invoke=quality_invoke,
    )
    registry.register(
        "jtms",
        ComponentType.SERVICE,
        capabilities=["belief_maintenance"],
        invoke=belief_invoke,
    )
    registry.register(
        "counter",
        ComponentType.AGENT,
        capabilities=["counter_argument_generation"],
        invoke=counter_invoke,
    )
    registry.register(
        "semantic_index",
        ComponentType.SERVICE,
        capabilities=["semantic_indexing"],
        invoke=ic._invoke_semantic_index,
    )

    transport = _FakeKMTransport()
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        executor = WorkflowExecutor(registry)
        await executor.execute(
            build_fact_check_workflow(),
            "Premiere affirmation a verifier. Deuxieme affirmation a verifier.",
        )

    assert (
        len(transport.docs) == 2
    ), "le workflow fact_check de production n'a pas indexe ses unites"
    texts = sorted(d["text"] for d in transport.docs.values())
    assert texts == [
        "Deuxieme affirmation a verifier",
        "Premiere affirmation a verifier",
    ]
