"""#1914 criteria 1+7 — the reader-surface vocabulary family.

The dispatch R1030 map (issue comment, DoD 1) measured the gap: the
fixed renderer surfaces are held (gate block folded, header clean,
#2046 spec-refs), the gate holds the machinery forms — but five token
classes had NO consumer on the rendered acts: arbitrary issue numbers,
spec pointers inside acts, serialized dict literals, gate-vocabulary
echoes, and the score-less specialist badge (measured R1029: « Verdict
FOL : théorie inconsistante » ×5 → PASS).

These tests pin the family, wired into ``renderer.render`` beside the
two other body consumers:

* each class reddens its token (the negatives);
* the ± pair — the token that FAILs on the reader surface SURVIVES
  folded in the appendix of the same report (criterion 6: that survival
  is the contract, so the family must scan the body only);
* a woven sentence citing a solver passes — the shape, not the
  framework mention, is the defect (#2046 scope guard);
* 1–2 residual badges WARN, ≥3 FAIL (gate-family banding).

Privacy HARD — opaque ids only. No JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import (
    RestitutionActs,
    RestitutionReportRenderer,
)
from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
    check_reader_vocabulary,
)
from argumentation_analysis.reporting.restitution.state_adapter import (
    state_to_appendix_mapping,
)

_ACT1 = (
    "Le discours analysé (source doc_C) défend une décision controversée "
    "devant un auditoire sceptique. Le locuteur empile des garanties "
    "d'autorité et des appels à la solidarité ; l'enjeu est l'adhésion, pas "
    "la démonstration. Un lecteur attentif doit démêler ce qui persuade de "
    "ce qui prouve."
)

_ACT2 = (
    "Le premier mouvement appuie la thèse centrale sur une autorité "
    "invérifiable ; le solveur Tweety confirme l'inconsistance de "
    "l'inférence sous-jacente, et le cadre de Dung isole l'attaque "
    "défaillante. Chaque mouvement gagne en efficacité ce qu'il perd en "
    "rigueur, et la trame argumentative se fragilise."
)

_CLEAN_ACT3 = (
    "L'analyse conclut à un propos persuasif mais fragile : l'autorité "
    "invoquée ne soutient pas la thèse, et la charge de la preuve reste "
    "déplacée. Le lecteur peut retenir un discours efficace dans sa "
    "forme et vulnérable dans son fonds."
)

# The coordinator's measured badge shapes (R1029) — score-less, invisible
# to the gate's scored bare-ref detector at any dose.
_BADGE_LINES = (
    "Verdict FOL : théorie inconsistante.\n"
    "PL : 3 inférences inconsistantes.\n"
    "Modal : la théorie est inconsistance."
)


def _acts(act3: str) -> RestitutionActs:
    return RestitutionActs(
        act1_framing=_ACT1,
        act2_narrative=_ACT2,
        act3_conclusion=act3,
        source_id="doc_C",
    )


def _fol_inconsistent_state() -> SimpleNamespace:
    """A state whose appendix MUST carry the FOL axis aggregate — the
    specialist inventory criterion 6 requires to survive folded."""
    return SimpleNamespace(
        identified_arguments={"arg_1": "these A", "arg_2": "these B"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[
            {"consistent": False, "message": "incoherent", "formulas": ["p(a)"]},
        ],
        modal_analysis_results=[],
    )


class TestEachClassReddensItsToken:
    def test_issue_number_reddens(self):
        verdict = check_reader_vocabulary(
            "La stratégie rhétorique suit le motif décrit en #1914 pour "
            "ce genre de discours."
        )
        assert verdict.band == "FAIL"
        assert any("numéro d'issue" in r for r in verdict.reasons)

    def test_spec_ref_reddens(self):
        verdict = check_reader_vocabulary(
            "Le récit respecte la règle de tissage (spec §4) sur ce mouvement."
        )
        assert verdict.band == "FAIL"
        assert any("spec interne" in r for r in verdict.reasons)

    def test_dict_literal_reddens(self):
        verdict = check_reader_vocabulary(
            "L'axe formel conclut {'consistent': False} sur la théorie testée."
        )
        assert verdict.band == "FAIL"
        assert any("dictionnaire brut" in r for r in verdict.reasons)

    def test_gate_echo_reddens(self):
        verdict = check_reader_vocabulary(
            "La prose passe le gate lisibilité sans réserve, non truqué."
        )
        assert verdict.band == "FAIL"
        assert any("gate" in r for r in verdict.reasons)

    def test_bare_badges_enumerate_to_fail(self):
        # The R1029 probe dose: 3 score-less badge lines → the manifest
        # enumeration band, invisible to the scored detector before.
        verdict = check_reader_vocabulary(_BADGE_LINES)
        assert verdict.band == "FAIL"
        assert any("Badge de spécialiste" in r for r in verdict.reasons)

    def test_single_bare_badge_warns(self):
        verdict = check_reader_vocabulary(
            "Un dernier relevé demeure.\nPL : 3 inférences inconsistantes."
        )
        assert verdict.band == "WARN"
        assert any("Badge de spécialiste" in r for r in verdict.reasons)


class TestWovenProsePasses:
    def test_woven_solver_citation_survives(self):
        # The #2046 scope guard: woven PROSE may cite a solver — the family
        # flags the badge SHAPE, never the framework mention.
        verdict = check_reader_vocabulary(_ACT2)
        assert verdict.band == "PASS"

    def test_clean_conclusion_passes(self):
        assert check_reader_vocabulary(_CLEAN_ACT3).band == "PASS"

    def test_heading_fence_is_not_an_issue_number(self):
        verdict = check_reader_vocabulary("### Le premier mouvement\n" + _ACT2)
        assert verdict.band == "PASS"


class TestTheAppendixHalf:
    """The ± pair: the token that fails on the surface survives folded."""

    def _render(self, act3: str):
        report = RestitutionReportRenderer().render(
            _acts(act3),
            state=state_to_appendix_mapping(_fol_inconsistent_state()),
        )
        fold = report.markdown.find("<details>")
        assert fold != -1
        return report, report.markdown[:fold], report.markdown[fold:]

    def test_badge_fails_but_appendix_keeps_the_inventory(self):
        report, surface, annex = self._render(_CLEAN_ACT3 + "\n" + _BADGE_LINES)
        assert report.verdict.band == "FAIL"
        assert any("Badge de spécialiste" in r for r in report.verdict.reasons)
        # the appendix half: the FOL aggregate survives folded — the
        # check must never bite the fold (criterion 6).
        assert "inconsist" in annex.lower()

    def test_clean_surface_with_rich_appendix_passes(self):
        report, surface, annex = self._render(_CLEAN_ACT3)
        assert report.verdict.band == "PASS"
        # the specialist inventory is still there, folded — punishing the
        # reader surface did not punish the audit surface.
        assert "inconsist" in annex.lower()


class TestRendererWiring:
    """The family is wired into ``renderer.render`` (born red before the
    wiring, like #2327)."""

    def test_render_flags_the_leaked_vocabulary(self):
        report = RestitutionReportRenderer().render(
            _acts(_CLEAN_ACT3 + "\n" + _BADGE_LINES),
            state=state_to_appendix_mapping(_fol_inconsistent_state()),
        )
        assert report.verdict.band == "FAIL"

    def test_render_clean_report_stays_pass(self):
        report = RestitutionReportRenderer().render(
            _acts(_CLEAN_ACT3),
            state=state_to_appendix_mapping(_fol_inconsistent_state()),
        )
        assert report.verdict.band == "PASS"
