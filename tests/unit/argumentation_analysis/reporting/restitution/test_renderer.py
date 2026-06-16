"""Tests for the restitution report renderer (Epic #1134 / R6).

Covers assembly, fail-loud behaviour on missing acts, degradation provenance,
verdict transparency, appendix folding, and privacy. No JVM/LLM/network — the
gate and fixtures are deterministic.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.reporting.restitution import (
    RenderedReport,
    RestitutionActs,
    RestitutionReportRenderer,
)

# Reuse the woven bodies from the gate tests (single source of truth for the
# "well-woven" shape).
_WOVEN = {
    1: (
        "Le discours analysé (source doc_A) est un propos politique à visée "
        "persuasive. L'orateur cherche à mobiliser l'auditoire sur une décision "
        "controversée; l'asymétrie d'information joue en sa faveur. Un auditeur "
        "averti doit guetter l'appel à l'autorité typique de ce genre. Les "
        "joueurs sont l'orateur et un adversaire implicite."
    ),
    2: (
        "Le premier mouvement appuie la thèse sur une autorité externe. Cette "
        "autorité ne satisfait pas la question critique de fiabilité: c'est une "
        "exception au scheme ExpertOpinion (ancrage AIF/Walton), et le solveur "
        "Tweety confirme l'inconsistance de l'inférence sous-jacente. Le cadre "
        "de Dung isole ensuite cette attaque comme défaillante."
    ),
    3: (
        "L'analyse conclut à un discours structurellement fragile sur l'axe "
        "formel. La synthèse honnête, gated par les dimensions non-triviales, "
        "caractérise un propos qui cède sur la logique. Pour contrer: viser la "
        "question critique de fiabilité. À attendre ensuite: un glissement vers "
        "l'ad hominem."
    ),
}


def _woven_acts() -> RestitutionActs:
    return RestitutionActs(
        act1_framing=_WOVEN[1],
        act2_narrative=_WOVEN[2],
        act3_conclusion=_WOVEN[3],
        source_id="doc_A",
    )


class TestAssembly:

    def test_three_acts_assembled_with_header_and_verdict(self):
        report = RestitutionReportRenderer().render(_woven_acts())
        assert isinstance(report, RenderedReport)
        md = report.markdown
        assert md.startswith("# Rapport de restitution — doc_A")
        assert "## Acte I — Mise en situation" in md
        assert "## Acte II — Récit dialectique" in md
        assert "## Acte III — Conclusion actionnable" in md
        # the woven body survived verbatim
        assert "solveur Tweety confirme" in md
        # verdict surfaced for transparency
        assert "Gate lisibilité" in md
        assert report.verdict.band == "PASS"

    def test_appendix_folded_present(self):
        report = RestitutionReportRenderer().render(
            _woven_acts(), state={"identified_arguments": {"arg_1": "x"}}
        )
        assert "<details>" in report.markdown
        assert "<summary>" in report.markdown


class TestFailLoudOnMissing:

    def test_missing_act_named_not_omitted(self):
        acts = _woven_acts()
        acts.act2_narrative = ""  # the narrative core is missing
        report = RestitutionReportRenderer().render(acts)
        # the report names the missing act honestly — no silent gap
        assert "Acte II indisponible" in report.markdown
        assert report.verdict.band == "FAIL"
        assert any("Acte II absent" in r for r in report.verdict.reasons)

    def test_missing_act1_named(self):
        acts = _woven_acts()
        acts.act1_framing = ""
        report = RestitutionReportRenderer().render(acts)
        assert "Acte I indisponible" in report.markdown


class TestDegradationProvenance:

    def test_degraded_act_note_surfaced(self):
        acts = _woven_acts()
        acts.degraded = {"act3_conclusion": "portes G1–G4 partiellement échouées (G2)."}
        report = RestitutionReportRenderer().render(acts)
        assert "Acte dégradé" in report.markdown
        assert "G1–G4 partiellement échouées" in report.markdown


class TestThinActWarning:

    def test_thin_act_warns(self):
        acts = _woven_acts()
        # act3 present but suspiciously short (stub)
        acts.act3_conclusion = "Conclusion courte."
        report = RestitutionReportRenderer().render(acts)
        assert report.verdict.band == "WARN"
        assert any("anormalement court" in r for r in report.verdict.reasons)


class TestPrivacy:

    def test_source_id_in_header_only(self):
        report = RestitutionReportRenderer().render(_woven_acts())
        assert "doc_A" in report.markdown  # opaque id in header

    def test_no_raw_text_in_appendix(self):
        report = RestitutionReportRenderer().render(
            _woven_acts(),
            state={"raw_text": "SECRET CORPUS", "identified_arguments": {"a": "b"}},
        )
        assert "SECRET" not in report.markdown
        assert "<details>" in report.markdown

    def test_full_state_json_opt_in_is_leak_free(self):
        report = RestitutionReportRenderer().render(
            _woven_acts(),
            state={"raw_text": "SECRET", "identified_arguments": {"a": "b"}},
            include_full_state_json=True,
        )
        assert "```json" in report.markdown
        assert "SECRET" not in report.markdown
