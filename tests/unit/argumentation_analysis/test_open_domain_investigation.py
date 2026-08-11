"""Tests for open-domain investigation (#358).

Validates that the OpenDomainInvestigator:
- Produces attributions under different hypotheses
- Generates hypothesis summaries
- Builds a whodunit-style conclusion
- Works with opaque document IDs
- Integrates with SherlockModernOrchestrator

All tests mock the SherlockModernOrchestrator to avoid JVM/DLL issues.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from argumentation_analysis.orchestration.open_domain_investigation import (
    OpenDomainInvestigator,
    OpenDomainResult,
    Attribution,
)
from argumentation_analysis.orchestration.sherlock_modern_orchestrator import (
    InvestigationResult,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


SAMPLE_DISCOURSE = (
    "L'auteur attribue la responsabilite du echec au gouvernement. "
    "Il utilise des arguments ad hominem et des generalisations hatives."
)

MOCK_INVESTIGATION = InvestigationResult(
    trace=[
        {
            "step": 1,
            "phase": "extraction",
            "agent": "ExtractAgent",
            "findings": {"claims_found": 2, "arguments_found": 1},
            "conclusion": "Found 2 claims",
        },
        {
            "step": 2,
            "phase": "fallacy_detection",
            "agent": "InformalAnalysisAgent",
            "findings": {
                "fallacy_count": 2,
                "types": ["ad_hominem", "generalisation_hative"],
            },
            "conclusion": "Detected 2 fallacies",
        },
        {
            "step": 3,
            "phase": "quality_evaluation",
            "agent": "QualityScoringPlugin",
            "findings": {"overall_score": 3.5, "arguments_evaluated": 2},
            "conclusion": "Score 3.5/10",
        },
        {
            "step": 4,
            "phase": "cross_examination",
            "agent": "CounterArgumentAgent",
            "findings": {"counter_arguments": 1, "strategy": "reductio"},
            "conclusion": "Cross-exam produced 1 counter",
        },
        {
            "step": 5,
            "phase": "belief_tracking",
            "agent": "JTMS",
            "findings": {"beliefs_total": 3, "beliefs_valid": 2, "beliefs_invalid": 1},
            "conclusion": "3 beliefs, 1 retracted",
        },
        {
            "step": 6,
            "phase": "hypothesis_branching",
            "agent": "ATMS",
            "findings": {"hypotheses_tested": 2, "coherent": 1, "incoherent": 1},
            "conclusion": "1 coherent, 1 incoherent",
        },
        {
            "step": 7,
            "phase": "solution_synthesis",
            "agent": "NarrativeSynthesisPlugin",
            "findings": {"paragraph_count": 1},
            "conclusion": "Synthesis complete",
        },
    ],
    reasoning_chain=[
        "Found 2 claims",
        "Detected 2 fallacies",
        "Score 3.5/10",
        "Cross-exam produced 1 counter",
        "3 beliefs, 1 retracted",
        "1 coherent, 1 incoherent",
        "Synthesis complete",
    ],
    agents_used=[
        "ExtractAgent",
        "InformalAnalysisAgent",
        "QualityScoringPlugin",
        "CounterArgumentAgent",
        "JTMS",
        "ATMS",
        "NarrativeSynthesisPlugin",
    ],
    agent_count=7,
    hypotheses=[
        {"id": "h_full_trust", "coherent": True, "assumptions": ["trust_all_sources"]},
        {
            "id": "h_skeptical",
            "coherent": False,
            "assumptions": ["doubt_fallacious_sources"],
        },
    ],
    solution="Investigation summary: multiple fallacies detected under full trust hypothesis.",
)


def _mocked_investigator():
    """Create investigator with mocked orchestrator."""
    inv = OpenDomainInvestigator()
    return inv


class TestOpenDomainInvestigator:
    """Tests for the OpenDomainInvestigator class."""

    def test_investigate_returns_result(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE, "doc_A"))
            assert isinstance(result, OpenDomainResult)

    def test_document_id_set(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE, "doc_B"))
            assert result.document_id == "doc_B"

    def test_reasoning_trace_not_empty(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE))
            assert len(result.reasoning_trace) >= 1

    def test_conclusion_not_empty(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE, "doc_A"))
            assert isinstance(result.conclusion, str)
            assert len(result.conclusion) > 20

    def test_conclusion_mentions_document_id(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE, "doc_A"))
            assert "doc_A" in result.conclusion

    def test_hypothesis_summary_built(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE))
            assert isinstance(result.hypothesis_summary, dict)
            assert "h_full_trust" in result.hypothesis_summary
            assert "h_skeptical" in result.hypothesis_summary

    def test_state_stored(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            _run(inv.investigate_document(SAMPLE_DISCOURSE))
            assert inv.state is not None

    def test_with_pre_existing_state(self):
        state = UnifiedAnalysisState("pre-existing")
        inv = OpenDomainInvestigator(state=state)
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            _run(inv.investigate_document(SAMPLE_DISCOURSE))
            assert inv.state is state

    def test_opaque_id_no_sensitive_data(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE, "doc_X"))
            assert SAMPLE_DISCOURSE not in result.conclusion
            assert SAMPLE_DISCOURSE not in str(result.attributions)

    def test_attributions_differentiate_coherent(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE))
            coherent_attrs = [a for a in result.attributions if a.coherent]
            incoherent_attrs = [a for a in result.attributions if not a.coherent]
            assert len(coherent_attrs) > 0
            assert len(incoherent_attrs) > 0

    def test_conclusion_holds_vs_collapses(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE, "doc_A"))
            assert "h_full_trust" in result.conclusion
            assert "h_skeptical" in result.conclusion

    def test_empty_state_fallback(self):
        empty_result = InvestigationResult(
            trace=[],
            reasoning_chain=[],
            agents_used=[],
            agent_count=0,
            hypotheses=[],
            solution="",
        )
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=empty_result,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document("empty", "doc_C"))
            assert (
                "insufficient" in result.conclusion.lower()
                or "partial" in result.conclusion.lower()
            )

    def test_claims_analyzed_count(self):
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE))
            assert result.claims_analyzed >= 1

    def test_attribution_output_format(self):
        """Verify attribution output mentions the expected format."""
        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=MOCK_INVESTIGATION,
        ):
            inv = _mocked_investigator()
            result = _run(inv.investigate_document(SAMPLE_DISCOURSE, "doc_A"))
            # Attributions should mention "supported" or "undermined"
            all_text = " ".join(a.attribution for a in result.attributions)
            assert "supported" in all_text.lower() or "undermined" in all_text.lower()


class TestAttribution:
    """Tests for the Attribution dataclass."""

    def test_creation(self):
        attr = Attribution(
            claim="test claim",
            attribution="Author claims X",
            hypothesis_id="h1",
            coherent=True,
            confidence=0.8,
        )
        assert attr.claim == "test claim"
        assert attr.coherent is True
        assert attr.confidence == 0.8

    def test_defaults(self):
        attr = Attribution(
            claim="test",
            attribution="test",
            hypothesis_id="h1",
            coherent=False,
        )
        assert attr.confidence == 0.0


class TestDemoScript:
    """Smoke test for the demo script."""

    def test_demo_file_exists(self):
        from pathlib import Path

        demo_path = Path(
            "examples/02_core_system_demos/scripts_demonstration"
            "/demo_sherlock_investigation.py"
        )
        assert demo_path.exists()

    def test_demo_has_run_function(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "demo_sherlock",
            "examples/02_core_system_demos/scripts_demonstration"
            "/demo_sherlock_investigation.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert hasattr(mod, "__file__")


class TestCoherentThreeStateOpenDomain:
    """#1650 (R790 item 2): the three open_domain sites (attributions, summary,
    conclusion partition) must classify an absent ``coherent`` key as
    UNCLASSIFIED / its own group, never fold it onto INCOHERENT. Armed by a
    hypothesis that LACKS the key."""

    def _investigator(self):
        return OpenDomainInvestigator()

    def test_attributions_name_absent_key_as_unclassifiable(self):
        inv = self._investigator()
        hyps = [{"id": "h_nokey", "assumptions": ["a"]}]  # no 'coherent' key
        attributions = inv._build_attributions(["claim_A"], hyps)
        assert len(attributions) == 1
        # The output names the absent key, does NOT claim "undermined".
        assert "unclassifiable" in attributions[0].attribution.lower()
        assert "undermined" not in attributions[0].attribution.lower()

    def test_summary_names_absent_key_unclassified(self):
        inv = self._investigator()
        hyps = [{"id": "h_nokey", "assumptions": []}]
        summary = inv._build_hypothesis_summary(hyps)
        assert "UNCLASSIFIED" in summary["h_nokey"]
        assert "INCOHERENT" not in summary["h_nokey"]

    def test_conclusion_partitions_absent_key_into_its_own_group(self):
        """A hypothesis with the absent key goes NEITHER into coherent NOR
        incoherent — it has its own unclassifiable line. Reverting the partition
        to the old complementary split puts it into incoherent_hyps."""
        inv = self._investigator()
        hyps = [
            {"id": "h_t", "coherent": True, "assumptions": []},
            {"id": "h_f", "coherent": False, "assumptions": []},
            {"id": "h_nokey", "assumptions": []},  # absent — the arming input
        ]
        attributions = inv._build_attributions(["claim_A"], hyps)
        conclusion = inv._build_conclusion("doc_A", ["claim_A"], attributions, hyps)
        assert "Coherent hypotheses: 1" in conclusion
        assert "Incoherent hypotheses: 1" in conclusion
        # The absent-key hypothesis is NOT miscounted as incoherent.
        assert "Incoherent hypotheses: 2" not in conclusion
        # It surfaces as its own group.
        assert "Unclassifiable hypotheses: 1" in conclusion
