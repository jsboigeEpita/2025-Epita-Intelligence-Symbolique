"""Tests for orchestration mode comparison harness."""
import asyncio
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
HARNESS_PATH = SCRIPT_DIR / "compare_orchestration_modes.py"


class TestOrchestrationModeHarness:
    """Tests for the compare_orchestration_modes.py harness."""

    def test_benchmark_texts_contain_three_corpora(self):
        """Verify all 3 benchmark corpora are defined."""
        from compare_orchestration_modes import BENCHMARK_TEXTS

        assert set(BENCHMARK_TEXTS.keys()) == {"corpus_A", "corpus_B", "corpus_C"}
        for cid, text in BENCHMARK_TEXTS.items():
            assert len(text) > 100, f"{cid} too short"
            # No raw source names in corpus IDs (privacy check)
            assert "extract" not in cid.lower()
            assert "source" not in cid.lower()

    def test_mode_runners_cover_all_documented_modes(self):
        """Verify all BO-4 modes have registered runners.

        Post-#1480 contract: cluedo_baseline/cluedo_extended were REMOVED
        from the registry (anti-pendule — they were dead-code ``success=False``
        stubs, not real comparable modes). hierarchical_bridge and
        hierarchical_delegation are the new post-#1474 sub-modes replacing
        the single ``hierarchical`` slot (which is now kept as a backward-
        compat alias to bridge).
        """
        from compare_orchestration_modes import MODE_RUNNERS

        expected = {
            "pipeline",
            "pipeline_light",
            "pipeline_full",
            "conversational",
            "conversation_deterministic",
            "hierarchical",
            "hierarchical_bridge",
            "hierarchical_delegation",
        }
        assert expected.issubset(set(MODE_RUNNERS.keys()))

    def test_cluedo_runners_are_removed(self):
        """Anti-pendule: cluedo stubs were dead-code ``success=False``
        placeholders. BO-4 #1480 removed them from the registry so they
        cannot be confused with real comparable modes.
        """
        from compare_orchestration_modes import MODE_RUNNERS

        assert "cluedo_baseline" not in MODE_RUNNERS
        assert "cluedo_extended" not in MODE_RUNNERS

    @pytest.mark.asyncio
    async def test_conversation_deterministic_produces_result(self):
        """Conversation deterministic mode should succeed without LLM."""
        from compare_orchestration_modes import run_conversation_deterministic_mode

        result = await run_conversation_deterministic_mode(
            "Un argument simple pour tester.", "test_corpus"
        )
        assert result.success
        assert result.mode == "conversation_deterministic"
        assert result.duration_seconds >= 0
        assert result.phases_completed == 3

    @pytest.mark.asyncio
    async def test_hierarchical_submodes_are_registered(self):
        """Post-#1480: hierarchical_bridge and hierarchical_delegation are
        the real 3-tier orchestrator entry-points (post-#1474). They must
        be wired in MODE_RUNNERS so the harness can compare the M2 (bridge)
        and M3 (delegation) sub-modes that BO-1 #1471 just made real.

        We assert registry presence without invoking the runners because
        the local JVM is broken on ``lib.GEN_EMAIL`` (Tweety 1.28+ removed
        the constant — pre-existing bug, out of scope for BO-4).
        """
        from compare_orchestration_modes import MODE_RUNNERS

        assert "hierarchical_bridge" in MODE_RUNNERS
        assert "hierarchical_delegation" in MODE_RUNNERS

    def test_generate_report_handles_mixed_results(self):
        """Report generation handles success + failure mix."""
        from compare_orchestration_modes import ModeResult, generate_report

        results = [
            ModeResult(
                mode="pipeline",
                corpus_id="corpus_A",
                success=True,
                duration_seconds=2.5,
                state_fill_rate=0.16,
                fallacy_count=0,
                phases_completed=3,
                phases_total=3,
            ),
            ModeResult(
                mode="hierarchical",
                corpus_id="corpus_A",
                success=False,
                error="not available",
            ),
        ]
        report = generate_report(results)
        assert "pipeline" in report
        assert "hierarchical" in report
        assert "✅" in report
        assert "❌" in report
