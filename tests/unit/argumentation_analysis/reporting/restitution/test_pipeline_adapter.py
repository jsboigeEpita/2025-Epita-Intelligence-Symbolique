"""Tests for the R6-final pipeline wiring (Epic #1134 / #1140).

Pins the contract that a completed spectacular ``UnifiedAnalysisState`` becomes
the readable 3-act restitution report. The wiring is the *missing render path*
(the run previously returned only a ``state_snapshot`` dict — the unreadable
dump the owner flagged). These tests are deterministic — no JVM, no LLM, no
network: the state is a ``SimpleNamespace`` and the appendix/acts are stubbed.

Privacy HARD is asserted: ``source_id`` is opaque; ``raw_text`` never reaches
the rendered report.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import List

import pytest

from argumentation_analysis.reporting.restitution.acts import RestitutionActs
from argumentation_analysis.reporting.restitution.pipeline_adapter import (
    build_restitution_acts,
    render_spectacular_restitution,
)


# --- state stubs -------------------------------------------------------------


def _stub_state(**fields: object) -> SimpleNamespace:
    """A spectacular post-run state stub (3 acts + spec-§2 keys)."""
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


# Three honest, substantive acts (mirroring the LLM-conducted fixtures of the
# act-plugin tests). Each clears the renderer's min-act-chars threshold.
_ACT1 = (
    "### Le texte\n\n"
    "Le discours appartient au genre politique ; le locuteur y défend une thèse "
    "d'action devant une assemblée. Les enjeux sont l'adhésion et la légitimité."
)
_ACT2 = (
    "### Le mouvement ad hominem\n\n"
    "Le premier mouvement appuie la thèse en disqualifiant l'adversaire plutôt "
    "que sa position; le solveur Tweety confirme l'inconsistance de l'inférence "
    "sous-jacente. C'est un dérapage de la famille ad hominem."
)
_ACT3 = (
    "### Synthèse honnête\n\n"
    "L'analyse atteint une profondeur multi-axes: elle localise un dérapage et "
    "le solveur Tweety confirme l'inconsistance d'une inférence. La couverture "
    "est large, la caractérisation peut donc être assurée sans sur-claim."
)


# ============================================================================
# build_restitution_acts — state → RestitutionActs mapping
# ============================================================================


class TestBuildRestitutionActs:
    def test_reads_three_acts_from_state(self):
        state = _stub_state(act1_framing=_ACT1, act2_narrative=_ACT2, act3_conclusion=_ACT3)
        acts = build_restitution_acts(state)
        assert acts.act1_framing == _ACT1
        assert acts.act2_narrative == _ACT2
        assert acts.act3_conclusion == _ACT3
        assert not acts.is_missing(1)
        assert not acts.is_missing(2)
        assert not acts.is_missing(3)

    def test_empty_state_yields_all_missing(self):
        acts = build_restitution_acts(_stub_state())
        assert acts.is_missing(1)
        assert acts.is_missing(2)
        assert acts.is_missing(3)
        assert acts.act1_framing == ""

    def test_works_on_dict_state(self):
        state = {"act1_framing": _ACT1, "act2_narrative": _ACT2, "act3_conclusion": _ACT3}
        acts = build_restitution_acts(state, source_id="doc_A")
        assert acts.act1_framing == _ACT1
        assert acts.source_id == "doc_A"

    def test_non_string_act_coerced_to_empty(self):
        # A corrupted (non-string) act degrades to empty, not a crash.
        state = _stub_state(act2_narrative=None)  # type: ignore[arg-type]
        acts = build_restitution_acts(state)
        assert acts.act2_narrative == ""
        assert acts.is_missing(2)


# ============================================================================
# source_id derivation (opaque, privacy HARD)
# ============================================================================


class TestSourceId:
    def test_explicit_source_id_wins(self):
        state = _stub_state(source_metadata={"corpus_id": "doc_A"})
        acts = build_restitution_acts(state, source_id="doc_Z")
        assert acts.source_id == "doc_Z"

    def test_derived_from_metadata_corpus_id(self):
        state = _stub_state(source_metadata={"corpus_id": "doc_A"})
        acts = build_restitution_acts(state)
        assert acts.source_id == "doc_A"

    def test_fallback_when_no_metadata(self):
        acts = build_restitution_acts(_stub_state())
        assert acts.source_id == "corpus_anonyme"


# ============================================================================
# render_spectacular_restitution — the readable report
# ============================================================================


class TestRenderSpectacularRestitution:
    def test_full_state_renders_three_acts(self):
        state = _stub_state(
            act1_framing=_ACT1,
            act2_narrative=_ACT2,
            act3_conclusion=_ACT3,
            source_metadata={"corpus_id": "doc_A"},
        )
        report = render_spectacular_restitution(state)
        assert "Acte I" in report.markdown
        assert "Acte II" in report.markdown
        assert "Acte III" in report.markdown
        # the header names the opaque corpus
        assert "doc_A" in report.markdown
        # each act body is rendered verbatim
        assert _ACT1 in report.markdown
        assert _ACT2 in report.markdown

    def test_empty_state_reports_acts_indisponible(self):
        """DoD honesty: missing acts are named, never silently omitted (#1019)."""
        report = render_spectacular_restitution(_stub_state(), source_id="doc_B")
        assert "indisponible" in report.markdown.lower()
        # a missing act is a structural failure the gate must flag
        assert report.verdict.band == "FAIL"

    def test_gate_verdict_returned(self):
        state = _stub_state(act1_framing=_ACT1, act2_narrative=_ACT2, act3_conclusion=_ACT3)
        report = render_spectacular_restitution(state)
        assert report.verdict is not None
        assert report.verdict.band in ("PASS", "WARN", "FAIL")

    def test_output_path_writes_markdown(self, tmp_path):
        state = _stub_state(
            act1_framing=_ACT1,
            act2_narrative=_ACT2,
            act3_conclusion=_ACT3,
        )
        out = tmp_path / "nested" / "report.md"
        report = render_spectacular_restitution(state, output_path=str(out))
        assert out.exists()
        assert out.read_text(encoding="utf-8") == report.markdown

    def test_output_path_creates_missing_dir(self, tmp_path):
        state = _stub_state(act1_framing=_ACT1, act2_narrative=_ACT2, act3_conclusion=_ACT3)
        out = tmp_path / "deeply" / "nested" / "dir" / "report.md"
        render_spectacular_restitution(state, output_path=str(out))
        assert out.exists()


# ============================================================================
# Privacy HARD — no raw_text leak
# ============================================================================


class TestPrivacy:
    def test_raw_text_never_in_report(self):
        secret = "VERBATIM_SECRET_PHRASE_FROM_CORPUS_XYZ"
        state = _stub_state(
            act1_framing=_ACT1,
            act2_narrative=_ACT2,
            act3_conclusion=_ACT3,
            identified_arguments={"arg_1": secret},
            narrative_synthesis=secret,
        )
        report = render_spectacular_restitution(state)
        # the raw secret lives on the appendix source keys; it must NOT reach
        # the rendered report body (the appendix strips leak keys defensively).
        assert secret not in report.markdown

    def test_source_id_must_be_opaque(self):
        # a real speaker name passed explicitly is still rendered verbatim (the
        # contract trusts the caller) — but the *derived* path never invents one
        state = _stub_state()  # no metadata
        acts = build_restitution_acts(state)
        assert acts.source_id == "corpus_anonyme"
        assert "Speaker" not in acts.source_id


# ============================================================================
# Pipeline wiring contract — run_unified_analysis exposes render_restitution
# (DoD #1140: the readable report is reachable from the pipeline by default)
# ============================================================================


class TestPipelineWiringContract:
    def test_run_unified_analysis_has_render_restitution_param(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        sig = inspect.signature(run_unified_analysis)
        assert "render_restitution" in sig.parameters
        # default is False (opt-in, never changes existing callers' results)
        assert sig.parameters["render_restitution"].default is False

    def test_render_restitution_docstring_documents_result_key(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        doc = run_unified_analysis.__doc__ or ""
        assert "restitution_report" in doc
        assert "render_restitution" in doc
