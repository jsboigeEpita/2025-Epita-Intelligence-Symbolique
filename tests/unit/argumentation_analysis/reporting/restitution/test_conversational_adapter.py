"""Tests for the CONV-D conversational wiring (Epic #1331 / #1335).

Pins the contract that a completed conversational ``UnifiedAnalysisState``
becomes the readable 3-act restitution report. The conversational path does not
run the act-generation phases (it runs Extraction/Formal/Synthesis macro-phases
via AgentGroupChat), so the adapter generates the acts from the completed state
then renders — closing the gap the #1335 body flagged ("render_restitution
absent from the conversational path").

These tests are deterministic — no JVM, no real LLM, no network: the state is a
``SimpleNamespace`` and the act generators are AsyncMocked (the LLM is an
injectable async callable per FB-29/38, so no kernel is needed). Privacy HARD
asserted: ``source_id`` stays opaque.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from argumentation_analysis.reporting.restitution.act1_framing_plugin import Act1Result
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import Act2Result
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import Act3Result
from argumentation_analysis.reporting.restitution.conversational_adapter import (
    generate_and_render_for_conversational_state,
)


# --- state stub (mirrors test_pipeline_adapter) ------------------------------


def _stub_state(**fields: object) -> SimpleNamespace:
    base = dict(
        act1_framing="",
        act2_narrative="",
        act3_conclusion="",
        source_metadata={},
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        narrative_synthesis="",
    )
    base.update(fields)
    return SimpleNamespace(**base)


_ACT1 = (
    "### Le texte\n\nLe discours appartient au genre politique ; le locuteur y "
    "défend une thèse d'action devant une assemblée. Les enjeux sont l'adhésion."
)
_ACT2 = (
    "### Le mouvement ad hominem\n\nLe premier mouvement disqualifie l'adversaire "
    "plutôt que sa position; le solveur confirme l'inconsistance. Dérapage ad hominem."
)
_ACT3 = (
    "### Synthèse honnête\n\nL'analyse localise un dérapage et le solveur confirme "
    "l'inconsistance d'une inférence. Couverture large, caractérisation assurée."
)


def _patched_act_builders(act1: str = _ACT1, act2: str = _ACT2, act3: str = _ACT3):
    """Patch the 3 build_act callables in the adapter with AsyncMocks."""
    return (
        patch(
            "argumentation_analysis.reporting.restitution.conversational_adapter."
            "build_act1_framing",
            new=AsyncMock(return_value=Act1Result(narrative=act1, status="woven")),
        ),
        patch(
            "argumentation_analysis.reporting.restitution.conversational_adapter."
            "build_act2_narrative",
            new=AsyncMock(return_value=Act2Result(narrative=act2, status="woven")),
        ),
        patch(
            "argumentation_analysis.reporting.restitution.conversational_adapter."
            "build_act3_conclusion",
            new=AsyncMock(return_value=Act3Result(narrative=act3, status="woven")),
        ),
    )


# ============================================================================
# generate_and_render_for_conversational_state — acts + render
# ============================================================================


class TestGenerateAndRender:
    async def test_generates_three_acts_and_renders(self):
        state = _stub_state(source_metadata={"corpus_id": "doc_A"})
        p1, p2, p3 = _patched_act_builders()
        with p1, p2, p3:
            report = await generate_and_render_for_conversational_state(
                state, "ignored text", llm_callable=AsyncMock(return_value="ok")
            )
        # acts were persisted onto the state (the renderer reads them back)
        assert state.act1_framing == _ACT1
        assert state.act2_narrative == _ACT2
        assert state.act3_conclusion == _ACT3
        # the report renders the 3 acts + names the opaque corpus
        assert "Acte I" in report.markdown
        assert "Acte II" in report.markdown
        assert "Acte III" in report.markdown
        assert "doc_A" in report.markdown

    async def test_uses_injected_llm_callable_for_all_three_acts(self):
        """One LLM closure is reused for all 3 acts (vs. 3 kernels)."""
        state = _stub_state()
        llm = AsyncMock(return_value="conducted narrative")
        p1, p2, p3 = _patched_act_builders()
        with p1 as m1, p2 as m2, p3 as m3:
            await generate_and_render_for_conversational_state(state, "t", llm_callable=llm)
            # each builder received the SAME injected llm_callable
            assert m1.call_args.kwargs.get("llm_callable") is llm
            assert m2.call_args.kwargs.get("llm_callable") is llm
            assert m3.call_args.kwargs.get("llm_callable") is llm

    async def test_output_path_writes_markdown(self, tmp_path):
        state = _stub_state()
        out = tmp_path / "nested" / "conv_report.md"
        p1, p2, p3 = _patched_act_builders()
        with p1, p2, p3:
            report = await generate_and_render_for_conversational_state(
                state, "t", llm_callable=AsyncMock(), output_path=str(out)
            )
        assert out.exists()
        assert out.read_text(encoding="utf-8") == report.markdown


# ============================================================================
# Fail-loud isolation — one act failing must not abort the others (#1019/#369)
# ============================================================================


class TestFailLoudIsolation:
    async def test_one_act_raising_others_still_render(self):
        state = _stub_state()
        # Acte II raises; Acte I + III succeed
        with (
            patch(
                "argumentation_analysis.reporting.restitution.conversational_adapter."
                "build_act1_framing",
                new=AsyncMock(return_value=Act1Result(narrative=_ACT1, status="woven")),
            ),
            patch(
                "argumentation_analysis.reporting.restitution.conversational_adapter."
                "build_act2_narrative",
                new=AsyncMock(side_effect=RuntimeError("acte II LLM down")),
            ),
            patch(
                "argumentation_analysis.reporting.restitution.conversational_adapter."
                "build_act3_conclusion",
                new=AsyncMock(return_value=Act3Result(narrative=_ACT3, status="woven")),
            ),
        ):
            report = await generate_and_render_for_conversational_state(
                state, "t", llm_callable=AsyncMock()
            )
        # Acte I + III persisted; Acte II left empty (honest, not a crash)
        assert state.act1_framing == _ACT1
        assert state.act2_narrative == ""
        assert state.act3_conclusion == _ACT3
        # the renderer names the missing act honestly, the run did not abort
        assert "indisponible" in report.markdown.lower()

    async def test_no_llm_callable_yields_unavailable_acts(self):
        """No llm_callable + no resolvable service → acts come back unavailable.

        The builder (mocked here) records status; the adapter persists whatever
        narrative it gets (empty for unavailable). The report names the gap.
        """
        state = _stub_state()
        with (
            patch(
                "argumentation_analysis.reporting.restitution.conversational_adapter."
                "build_act1_framing",
                new=AsyncMock(
                    return_value=Act1Result(narrative="", status="unavailable")
                ),
            ),
            patch(
                "argumentation_analysis.reporting.restitution.conversational_adapter."
                "build_act2_narrative",
                new=AsyncMock(
                    return_value=Act2Result(narrative="", status="unavailable")
                ),
            ),
            patch(
                "argumentation_analysis.reporting.restitution.conversational_adapter."
                "build_act3_conclusion",
                new=AsyncMock(
                    return_value=Act3Result(narrative="", status="unavailable")
                ),
            ),
        ):
            report = await generate_and_render_for_conversational_state(
                state, "t", llm_callable=None
            )
        assert state.act1_framing == ""
        assert "indisponible" in report.markdown.lower()


# ============================================================================
# Conversational wiring contract — run_conversational_analysis exposes the param
# (DoD #1335: the readable report is reachable from the conversational path)
# ============================================================================


class TestConversationalWiringContract:
    def test_run_conversational_analysis_has_render_restitution_param(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        sig = inspect.signature(run_conversational_analysis)
        assert "render_restitution" in sig.parameters
        # default False — opt-in, never changes existing callers' results
        assert sig.parameters["render_restitution"].default is False

    def test_inner_impl_passes_render_restitution_through(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_conversational_analysis_inner,
        )

        sig = inspect.signature(_run_conversational_analysis_inner)
        assert "render_restitution" in sig.parameters

    def test_docstring_documents_restitution_report_key(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        doc = run_conversational_analysis.__doc__ or ""
        assert "render_restitution" in doc
        assert "restitution_report" in doc
