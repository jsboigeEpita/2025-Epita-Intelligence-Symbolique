# tests/unit/argumentation_analysis/agents/core/test_triage_2137_withdrawals.py
"""Né-rouge guard for the #2137 agents/core triage.

Every absence assertion below names something the arbitration comment
(issuecomment-5701131504) ordered withdrawn — this file reddens if any of
them comes back undeclared. Every presence assertion is a negative control
naming a survivor the same arbitration explicitly kept (the JVM
dialogue_handler, the inlined oracle prompt copy, the agentic module and its
`llm=` injection point, the debate vocabulary, the internally-consumed
governance metrics, the abstract `get_agent_capabilities` contract).
"""

import importlib
import importlib.util
import inspect

import pytest

# --- withdrawn modules (whole files) ----------------------------------------


@pytest.mark.parametrize(
    "module_name",
    [
        "argumentation_analysis.agents.core.governance.simulation",
        "argumentation_analysis.agents.core.debate.knowledge_base",
        "argumentation_analysis.agents.core.oracle.hypothesis_tracker",
    ],
)
def test_withdrawn_modules_are_gone(module_name):
    assert (
        importlib.util.find_spec(module_name) is None
    ), f"{module_name} was withdrawn (#2137) — restoring it needs a new triage"


# --- withdrawn symbols -------------------------------------------------------


def test_counter_argument_validation_result_gone():
    import argumentation_analysis.agents.core.counter_argument as pkg
    from argumentation_analysis.agents.core.counter_argument import definitions

    assert not hasattr(definitions, "ValidationResult")
    assert "ValidationResult" not in pkg.__all__


def test_counter_argument_parser_helpers_gone():
    from argumentation_analysis.agents.core.counter_argument import parser

    assert not hasattr(parser, "parse_llm_response")
    assert not hasattr(parser, "parse_structured_text")


def test_abc_get_agent_info_gone():
    from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent

    assert not hasattr(BaseAgent, "get_agent_info")


def test_governance_reexports_and_metrics_gone():
    import argumentation_analysis.agents.core.governance as pkg
    from argumentation_analysis.agents.core.governance import metrics

    for name in (
        "BDIAgent",
        "ReactiveAgent",
        "AgentFactory",
        "simulate_governance",
        "manipulability_analysis",
    ):
        assert not hasattr(pkg, name), f"{name} re-export withdrawn (#2137)"
        assert name not in pkg.__all__
    assert not hasattr(metrics, "per_agent_satisfaction")
    assert not hasattr(metrics, "validate_scenario")


def test_oracle_prompt_classvar_gone():
    from argumentation_analysis.agents.core.oracle.oracle_base_agent import (
        OracleBaseAgent,
    )

    assert not hasattr(OracleBaseAgent, "BASE_ORACLE_SYSTEM_PROMPT")


def test_debate_protocol_classes_and_kb_gone():
    import argumentation_analysis.agents.core.debate as pkg
    from argumentation_analysis.agents.core.debate import protocols

    for name in ("DialogueProtocol", "InquiryProtocol", "PersuasionProtocol"):
        assert not hasattr(protocols, name), f"{name} withdrawn (#2137)"
        assert name not in pkg.__all__
    assert not hasattr(pkg, "KnowledgeBase")


def test_debate_personalities_fields_gone():
    from argumentation_analysis.agents.core.debate.debate_definitions import (
        AGENT_PERSONALITIES,
    )

    assert len(AGENT_PERSONALITIES) == 8
    for name, profile in AGENT_PERSONALITIES.items():
        assert "strengths" not in profile, f"{name} strengths withdrawn (#2137)"
        assert "weaknesses" not in profile, f"{name} weaknesses withdrawn (#2137)"


def test_quality_default_llm_setter_gone():
    from argumentation_analysis.agents.core.quality import agentic_virtue_detectors

    assert not hasattr(agentic_virtue_detectors, "set_default_llm_callable")
    assert not hasattr(agentic_virtue_detectors, "_DEFAULT_LLM")


# --- negative controls: survivors the same arbitration kept ------------------


def test_jvm_dialogue_handler_survives():
    importlib.import_module("argumentation_analysis.agents.core.logic.dialogue_handler")


def test_oracle_inlined_prompt_copy_survives():
    from argumentation_analysis.agents.core.oracle.oracle_base_agent import (
        OracleBaseAgent,
    )

    source = inspect.getsource(OracleBaseAgent.__init__)
    assert "Vous êtes un Agent Oracle, gardien des données" in source, (
        "the inlined prompt copy (the text actually served) must survive "
        "the ClassVar withdrawal"
    )


def test_agentic_module_and_llm_injection_survive():
    from argumentation_analysis.agents.core.quality.agentic_virtue_detectors import (
        AgenticDetectorError,
        detect_refutation_constructive_agentic,
    )

    with pytest.raises(AgenticDetectorError, match="no LLM callable"):
        detect_refutation_constructive_agentic("texte", llm=None)
    score, _ = detect_refutation_constructive_agentic(
        "texte",
        llm=lambda prompt: (
            '{"has_opposing_claim": false, "opposing_claim": "", "main_thesis": "t"}'
        ),
    )
    assert score == 0.0


def test_debate_vocabulary_survives():
    from argumentation_analysis.agents.core.debate import protocols

    assert len(protocols.DialogueType) == 6
    assert len(protocols.SpeechAct) == 9
    for name in ("Proposition", "FormalArgument", "DialogueMove"):
        assert hasattr(protocols, name)


def test_governance_internally_consumed_metrics_survive():
    from argumentation_analysis.agents.core.governance import metrics

    # gini is consumed by fairness_index, efficiency/stability by
    # summarize_results — the 12-09 relevé called them orphans; re-measure
    # showed live intra-module readers.
    assert metrics.fairness_index({"satisfaction": [1.0, 1.0, 1.0]}) > 0.9
    summary = metrics.summarize_results(
        {
            "votes": ["A", "A", "B"],
            "winner": "A",
            "satisfaction": [1.0, 0.5, 0.5],
            "rounds": 1,
        }
    )
    assert "efficiency" in summary


def test_governance_agent_classes_survive_in_defining_module():
    from argumentation_analysis.agents.core.governance.governance_agent import (
        Agent,
        AgentFactory,
        BDIAgent,
        ReactiveAgent,
    )

    assert callable(Agent) and callable(AgentFactory)
    assert issubclass(BDIAgent, Agent) and issubclass(ReactiveAgent, Agent)


def test_base_agent_capabilities_contract_survives():
    from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent

    assert "get_agent_capabilities" in BaseAgent.__abstractmethods__


def test_oracle_kept_modules_survive():
    # error_handling is live since #2139 (permissions imports
    # CluedoIntegrityError from it); interfaces has 3 tool importers.
    importlib.import_module("argumentation_analysis.agents.core.oracle.error_handling")
    importlib.import_module("argumentation_analysis.agents.core.oracle.interfaces")
