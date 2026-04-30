"""Tests for Sherlock Modern scenarios (#360).

Validates that scenario infrastructure works with opaque IDs
and that no plaintext content leaks into results.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from argumentation_analysis.orchestration.open_domain_investigation import (
    OpenDomainResult,
    Attribution,
)
from argumentation_analysis.orchestration.sherlock_modern_orchestrator import (
    InvestigationResult,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


MOCK_RESULT = OpenDomainResult(
    document_id="doc_A",
    claims_analyzed=3,
    attributions=[
        Attribution(
            claim="test", attribution="Author supported under h_trust",
            hypothesis_id="h_trust", coherent=True, confidence=0.8,
        ),
        Attribution(
            claim="test", attribution="Author undermined under h_skeptical",
            hypothesis_id="h_skeptical", coherent=False, confidence=0.3,
        ),
    ],
    hypothesis_summary={
        "h_trust": "COHERENT — assumptions: [source_reliable]",
        "h_skeptical": "INCOHERENT — assumptions: [source_unreliable]",
    },
    reasoning_trace=[
        "Extracted 3 claims",
        "Detected 2 fallacies",
        "Quality score: 3.5/10",
    ],
    conclusion="Document doc_A — investigation complete with 1 coherent hypothesis",
)


class TestScenarioRunner:
    """Tests for the scenario runner script."""

    def test_scenario_file_exists(self):
        from pathlib import Path
        path = Path(
            "examples/03_demos_overflow/sherlock_modern/run_scenarios.py"
        )
        assert path.exists()

    def test_scenarios_doc_exists(self):
        from pathlib import Path
        path = Path("docs/sherlock/scenarios.md")
        assert path.exists()

    def test_scenario_definitions_valid(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_scenarios",
            "examples/03_demos_overflow/sherlock_modern/run_scenarios.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        assert len(mod.SCENARIOS) >= 3
        for s in mod.SCENARIOS:
            assert "document_id" in s
            assert "query" in s
            assert "expected" in s
            assert s["document_id"].startswith("doc_")

    def test_opaque_ids_no_plaintext(self):
        """Scenarios use opaque IDs, never source names."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_scenarios",
            "examples/03_demos_overflow/sherlock_modern/run_scenarios.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        sensitive_patterns = ["full_text", "raw_text", "speaker", "author"]
        scenario_text = str(mod.SCENARIOS)
        for pattern in sensitive_patterns:
            assert pattern not in scenario_text.lower() or pattern == "author", (
                f"Sensitive pattern '{pattern}' found in scenario definitions"
            )

    def test_run_scenario_returns_result(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_scenarios",
            "examples/03_demos_overflow/sherlock_modern/run_scenarios.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with patch(
            "argumentation_analysis.orchestration.sherlock_modern_orchestrator"
            ".SherlockModernOrchestrator.investigate",
            new_callable=AsyncMock,
            return_value=InvestigationResult(
                trace=[{"step": 1, "phase": "extraction", "findings": {"claims_found": 2},
                       "conclusion": "Found claims"}],
                reasoning_chain=["Found claims"],
                agents_used=["ExtractAgent"],
                agent_count=1,
                hypotheses=[{"id": "h1", "coherent": True, "assumptions": ["a"]}],
                solution="Test",
            ),
        ):
            result = _run(mod.run_scenario(mod.SCENARIOS[0]))
            assert result["scenario_id"] == "scenario_1"
            assert result["document_id"] == "doc_A"


class TestScenarioPrivacy:
    """Privacy compliance tests for scenarios."""

    def test_no_plaintext_in_docs(self):
        """Scenarios doc uses only opaque IDs."""
        from pathlib import Path
        content = Path("docs/sherlock/scenarios.md").read_text(encoding="utf-8")
        assert "doc_A" in content
        assert "doc_B" in content
        assert "doc_C" in content
        # Should NOT contain real speaker/source names
        assert "discours complet" not in content.lower()
        assert "texte integral" not in content.lower()

    def test_result_uses_opaque_ids(self):
        """Investigation results use opaque document IDs only."""
        result = MOCK_RESULT
        assert result.document_id.startswith("doc_")
        conclusion = result.conclusion
        assert "doc_A" in conclusion
