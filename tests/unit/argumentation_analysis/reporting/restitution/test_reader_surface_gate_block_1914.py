"""#1914 residual tranche — gate self-diagnostics off the reader surface.

The #1914 acceptance criterion: reader-facing Acts I–III carry no issue
numbers, internal spec references, raw dictionaries or **gate
self-diagnostics**. The qualification (49 #2062 renders, builders at
``f95b7af2``) measured the violations at their source — both deterministic
renderer surfaces, not LLM echoes:

* the readability-gate verdict block ("## Gate lisibilité — WARN", the
  structural-control self-report, "(#1019)") renders UNFOLDED between the
  narrative and the appendix fold — 49/49 renders;
* the fixed report header names the toolchain ("Tweety, Dung/ASPIC,
  taxonomie, vertus") — 49/49 renders, position before "## Acte I".

The contract (issue body, Appendix section) lists gate diagnostics as
material that belongs in the folded appendix. The tranche moves the verdict
block INSIDE the ``<details>`` fold (first content on unfold — auditability
intact, position folded) and drops the toolchain enumeration from the
header. Prose may still cite a solver by name — that surface is the
conductor's, governed by the weaving consignes, not by this renderer fix.

No JVM, no LLM, no network — deterministic structural checks only.
"""

from __future__ import annotations

from argumentation_analysis.reporting.restitution import (
    RestitutionActs,
    RestitutionReportRenderer,
)

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
        "autorité ne satisfait pas la question critique de fiabilité: c'est "
        "une exception au scheme ExpertOpinion (ancrage AIF/Walton), et le "
        "solveur Tweety confirme l'inconsistance de l'inférence sous-jacente. "
        "Le cadre de Dung isole ensuite cette attaque comme défaillante."
    ),
    3: (
        "L'analyse conclut à un discours structurellement fragile sur l'axe "
        "formel. La synthèse honnête, gated par les dimensions non-triviales, "
        "caractérise un propos qui cède sur la logique. Pour contrer: viser la "
        "question critique de fiabilité. À attendre ensuite: un glissement "
        "vers l'ad hominem."
    ),
}

_MOTIF = "portes G1–G4 partiellement échouées (G2)."


def _woven_acts() -> RestitutionActs:
    return RestitutionActs(
        act1_framing=_WOVEN[1],
        act2_narrative=_WOVEN[2],
        act3_conclusion=_WOVEN[3],
        source_id="doc_A",
    )


def _split_at_fold(report) -> tuple[str, str]:
    md = report.markdown
    fold = md.find("<details>")
    assert fold != -1, "appendix fold missing from rendered report"
    return md[:fold], md[fold:]


class TestGateDiagnosticsOffReaderSurface:
    def test_gate_block_lives_inside_the_fold(self):
        # WARN verdict (degraded act) — the exact shape the qualification
        # measured 49/49: a degraded run puts the self-diagnostic block on
        # the reader surface. State given so the dimensional table exists
        # and the fold-order assertion is meaningful.
        acts = _woven_acts()
        acts.degraded = {"act3_conclusion": _MOTIF}
        report = RestitutionReportRenderer().render(
            acts, state={"identified_arguments": {"arg_1": "x"}}
        )
        surface, annex = _split_at_fold(report)

        # reader surface: no gate self-diagnostic, no issue number
        assert "Gate lisibilité" not in surface
        assert "#1019" not in surface
        assert "non truqué" not in surface
        assert "Contrôles structurels" not in surface

        # auditability intact: the block is folded, first thing on unfold,
        # still carrying the band, the reasons and the honesty marker.
        assert "Gate lisibilité" in annex
        assert "#1019" in annex
        assert "non truqué" in annex
        assert _MOTIF in annex
        assert annex.find("Gate lisibilité") < annex.find("| Dimension |")

    def test_pass_verdict_also_folded(self):
        # the fold is not conditional on degradation — a PASS run must not
        # surface the self-diagnostic either (same criterion, other band).
        report = RestitutionReportRenderer().render(_woven_acts())
        surface, annex = _split_at_fold(report)
        assert report.verdict.band == "PASS"
        assert "Gate lisibilité" not in surface
        assert "Gate lisibilité" in annex

    def test_gate_block_folded_even_without_state(self):
        # no shared-state → honest "annexe indisponible" fold; the verdict
        # must still be folded, not dropped back to the surface.
        report = RestitutionReportRenderer().render(_woven_acts(), state=None)
        surface, annex = _split_at_fold(report)
        assert "Gate lisibilité" not in surface
        assert "Gate lisibilité" in annex


class TestHeaderNamesNoToolchain:
    def test_preamble_carries_no_toolchain_enumeration(self):
        report = RestitutionReportRenderer().render(_woven_acts())
        md = report.markdown
        act1 = md.find("## Acte I")
        assert act1 != -1
        preamble = md[:act1]
        # the enumeration form only the old fixed header carried
        assert "Dung/ASPIC" not in md
        assert "Tweety" not in preamble
        assert "taxonomie, vertus" not in preamble
        # the header still orients the reader (shape intact, vocabulary gone)
        assert md.startswith("# Rapport de restitution — doc_A")
        assert "Récit en trois actes" in preamble
        # and it points the audit-minded reader at the fold
        assert "annexe" in preamble.lower()

    def test_prose_solver_citation_survives(self):
        # scope guard: woven PROSE may cite a solver (fixture act 2 does) —
        # this tranche cleans the renderer's fixed surfaces, it does not
        # censor the conductor's narrative.
        report = RestitutionReportRenderer().render(_woven_acts())
        assert "solveur Tweety confirme" in report.markdown
