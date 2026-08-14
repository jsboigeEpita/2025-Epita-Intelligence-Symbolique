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


class TestUnknownRequestFailsLoud:
    """#1747 — an unhonoured request must not produce a plausible report.

    Before this, ``--modes <typo>`` was a ``logger.warning`` + ``continue``:
    the run wrote a complete, well-formed ``.md``/``.json`` with exit 0 and the
    requested mode simply absent. For a comparison instrument that is the worst
    failure shape — an absence in the table is indistinguishable from "that mode
    was never asked for", and only the ``.log`` carried the truth.

    The two states these tests keep apart:

    * **skipped** (pre-flight) — the key does not exist ⇒ ``ValueError``, no
      artifact, non-zero exit. Nothing ran.
    * **failed** (runtime) — the key exists, the runner raised ⇒ a real
      ``ModeResult`` row with ``success=False``. Something ran and lost.

    Collapsing them into one boolean is what erased the first case.
    """

    def test_unknown_mode_raises_instead_of_skipping(self):
        from compare_orchestration_modes import run_all

        with pytest.raises(ValueError) as exc:
            asyncio.run(run_all(modes=["pipeline_standrad"], corpora=["corpus_A"]))
        # The message must name the valid keys — a caller fixing a typo should
        # not have to read the source.
        assert "pipeline_standrad" in str(exc.value)
        assert "pipeline_standard" in str(exc.value)

    def test_unknown_corpus_raises_instead_of_skipping(self):
        from compare_orchestration_modes import run_all

        with pytest.raises(ValueError) as exc:
            asyncio.run(run_all(modes=["pipeline_standard"], corpora=["corpus_Z"]))
        assert "corpus_Z" in str(exc.value)
        assert "corpus_A" in str(exc.value)

    def test_unknown_mode_writes_no_report(self, tmp_path):
        """The decisive property: no artifact that *looks* complete."""
        from compare_orchestration_modes import run_all

        out = tmp_path / "should_not_exist"
        with pytest.raises(ValueError):
            asyncio.run(
                run_all(modes=["nope"], corpora=["corpus_A"], output_file=str(out))
            )
        assert not out.with_suffix(".md").exists()
        assert not out.with_suffix(".json").exists()

    def test_a_raising_runner_still_yields_a_failed_row(self, monkeypatch):
        """Counterpart: a KNOWN mode whose runner blows up is NOT a skip.

        Without this control the fix above could be satisfied by making every
        problem fatal, which would erase the honest ``success=False`` row that
        #1480 established.
        """
        import compare_orchestration_modes as harness

        async def _boom(text, cid, max_wall_seconds=None):
            raise RuntimeError("solver unavailable")

        monkeypatch.setitem(harness.MODE_RUNNERS, "pipeline_standard", _boom)
        monkeypatch.setattr(harness, "initialize_jvm", lambda: None, raising=False)

        results = asyncio.run(
            harness.run_all(modes=["pipeline_standard"], corpora=["corpus_A"])
        )
        assert len(results) == 1
        assert results[0].mode == "pipeline_standard"
        assert results[0].success is False
        assert "solver unavailable" in (results[0].error or "")


class TestPipelineStandardIsTypable:
    """#1747 — the label a report shows must be a key ``--modes`` accepts.

    ``run_pipeline_mode`` self-labels ``pipeline_{workflow_name}``, so the
    flagship mode rendered as ``pipeline_standard`` while the only key that
    dispatched it was ``pipeline``. Copying a label out of the baseline into
    ``--modes`` therefore failed — silently, before the fix above.
    """

    def test_canonical_key_matches_the_emitted_label(self):
        from compare_orchestration_modes import MODE_RUNNERS, default_modes

        assert "pipeline_standard" in MODE_RUNNERS
        assert "pipeline_standard" in default_modes()

    def test_bare_pipeline_stays_dispatchable_but_out_of_the_default_sweep(self):
        """Convention #1740: aliases dispatch, but never inflate the sweep.

        ``pipeline`` and ``pipeline_standard`` run the SAME workflow and emit
        the SAME label, so keeping both in the default sweep would double-count
        the flagship mode exactly as ``hierarchical`` double-counted the bridge.
        """
        from compare_orchestration_modes import (
            _DEPRECATED_MODE_ALIASES,
            MODE_RUNNERS,
            default_modes,
        )

        assert "pipeline" in MODE_RUNNERS
        assert "pipeline" in _DEPRECATED_MODE_ALIASES
        assert "pipeline" not in default_modes()

    def test_no_default_mode_is_an_alias(self):
        """The general property, not the two instances of it."""
        from compare_orchestration_modes import _DEPRECATED_MODE_ALIASES, default_modes

        assert not (set(default_modes()) & _DEPRECATED_MODE_ALIASES)
