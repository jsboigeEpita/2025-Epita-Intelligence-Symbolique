# -*- coding: utf-8 -*-
"""#1914 (criteria 2, 3, 4 — dispatch R1059) — post-render act controls.

The card (c.5969933470) measured the shared gap: the three contracts are
held at prompt + evidence level, and NO test reads a rendered act. These
witnesses pin the mechanical half — each control finds its planted defect on
a synthetic faulty act (positive control), stays silent on a compliant one
(negative control), and the mutation test proves the witness depends on the
control.

Synthetic French acts only — no corpus content (privacy HARD). The controls
are diagnostics for the folded appendix: they never fail a render, so the
witnesses assert FINDINGS, never bands.
"""

import unittest.mock as um

from argumentation_analysis.reporting.restitution.act_reader_contract_check import (
    ContractFinding,
    check_act_reader_contract,
)

# A compliant Act II: the formal citation carries, in the same sentence, what
# was tested and what it changes; the device carries its function.
_GOOD_ACT2 = (
    "## Acte II — Récit dialectique\n\n"
    "Le mouvement central réfute la théorie FOL testée : le solveur Tweety a "
    "éprouvé les propositions d'action et d'attribution, et cet échec remet en "
    "cause toute affirmation qui dépend des mêmes relations factuelles.\n\n"
    "Le slogan rythmé, procédé visant à créer l'adhésion par la répétition "
    "plutôt que par la preuve, fragilise le passage.\n"
)

# The faulty shapes, one per criterion — the badge without derivation (2),
# the piled labels without function (3), the flat unranked replay (4).
_BAD_ACT2 = (
    "## Acte II — Récit dialectique\n\n"
    "La lisibilité formelle du propos est confirmée par les solveurs : "
    '"[pl] 3 inférence(s) PL consistantes — ancrage : solveur Tweety".\n\n'
    "L'orateur cumule la « généralité flatteuse », l'« ingratiation » et le "
    "« sophisme d'autorité » dans ce mouvement.\n"
)

_BAD_ACT3_FLAT = "## Acte III — Conclusion actionnable\n\n" + "".join(
    f"Le propos contient un sophisme de type n°{i}.\n\n" for i in range(1, 8)
)

_GOOD_ACT3 = (
    "## Acte III — Conclusion actionnable\n\n"
    "Trouver décisif (P1) : la réfutation formelle de l'attribution, qui "
    "change le jugement porté sur la thèse.\n\n"
    "En second, la répétition du slogan fragilise la conclusion inverse.\n"
)


def _body(act2, act3, act1=None):
    preamble = act1 or "## Acte I — Mise en situation\n\nLe contexte.\n"
    return f"{preamble}\n{act2}\n{act3}"


class TestCriterion2FormalCitation:
    def test_badge_without_derivation_is_found(self):
        """Planted defect: the raw solver badge, no tested content, no
        consequence — the exact shape the real renders carry."""
        findings = check_act_reader_contract(_body(_BAD_ACT2, _GOOD_ACT3))
        c2 = [f for f in findings if f.criterion == 2]
        assert c2, "the badge sentence must produce a criterion-2 finding"
        assert c2[0].kind == "formal_citation_without_derivation"
        assert c2[0].act == "Acte II"
        assert "solveur" in c2[0].excerpt.lower()

    def test_compliant_derivation_is_clean(self):
        findings = check_act_reader_contract(_body(_GOOD_ACT2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 2]

    def test_honest_absence_is_compliant(self):
        """Naming the missing derivation (« contenu testé non disponible »)
        is the contract, not a violation."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "L'axe PL cite un contenu testé non disponible dans l'état "
            "(compteur seul) : preuve procédurale, sans dérivation.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 2]

    def test_acte_i_is_not_scanned(self):
        """The situation act carries no formal citation contract."""
        act1 = (
            "## Acte I — Mise en situation\n\nLe discours cite le solveur "
            "Tweety et trois inférences PL.\n"
        )
        findings = check_act_reader_contract(_body(_GOOD_ACT2, _GOOD_ACT3, act1))
        assert not [f for f in findings if f.criterion == 2 and f.act == "Acte I"]


class TestCriterion3LabelWithoutFunction:
    def test_piled_labels_are_found(self):
        findings = check_act_reader_contract(_body(_BAD_ACT2, _GOOD_ACT3))
        c3 = [f for f in findings if f.criterion == 3]
        assert c3, "the piled-labels sentence must produce a criterion-3 finding"
        assert c3[0].kind == "label_without_function"

    def test_function_clause_is_clean(self):
        findings = check_act_reader_contract(_body(_GOOD_ACT2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3]


class TestCriterion4RankedShape:
    def test_flat_replay_is_found_on_both_kinds(self):
        findings = check_act_reader_contract(_body(_GOOD_ACT2, _BAD_ACT3_FLAT))
        c4 = [f for f in findings if f.criterion == 4]
        kinds = {f.kind for f in c4}
        assert "no_ranked_marker" in kinds, "no ranking marker in the flat act"
        assert "label_replay" in kinds, "7 label sentences exceed the cap of 5"

    def test_short_ranked_act_is_clean(self):
        findings = check_act_reader_contract(_body(_GOOD_ACT2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 4]

    def test_no_acte_three_skips_honestly(self):
        """A missing Act III is the renderer's own loud degradation — the
        control does not pile a finding on it."""
        findings = check_act_reader_contract(
            "## Acte I — Mise en situation\n\nLe contexte.\n\n" + _GOOD_ACT2
        )
        assert not [f for f in findings if f.criterion == 4]


class TestPositions:
    def test_line_numbers_are_body_absolute(self):
        findings = check_act_reader_contract(_body(_BAD_ACT2, _GOOD_ACT3))
        c2 = [f for f in findings if f.criterion == 2][0]
        # Acte II heading sits on body line 5 (Acte I block = 4 lines), the
        # badge sentence two lines below the heading.
        assert c2.line == 7, f"expected body line 7, got {c2.line}"


class TestMutationTheControlCarriesTheWitness:
    """Dispatch DoD: removing the control reddens the witness."""

    def test_without_c2_the_c2_witness_fails(self):
        real = (
            "argumentation_analysis.reporting.restitution."
            "act_reader_contract_check._formal_findings"
        )
        with um.patch(real, return_value=[]):
            findings = check_act_reader_contract(_body(_BAD_ACT2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 2], (
            "the witness must depend on the control — with _formal_findings "
            "removed the planted badge goes undetected"
        )

    def test_without_c3_the_c3_witness_fails(self):
        real = (
            "argumentation_analysis.reporting.restitution."
            "act_reader_contract_check._label_findings"
        )
        with um.patch(real, return_value=[]):
            findings = check_act_reader_contract(_body(_BAD_ACT2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3]

    def test_without_c4_the_c4_witness_fails(self):
        real = (
            "argumentation_analysis.reporting.restitution."
            "act_reader_contract_check._ranked_findings"
        )
        with um.patch(real, return_value=[]):
            findings = check_act_reader_contract(_body(_GOOD_ACT2, _BAD_ACT3_FLAT))
        assert not [f for f in findings if f.criterion == 4]


class TestRendererWiring:
    """The findings ride into the folded appendix, and ONLY there: the acts
    are byte-identical with the control running or emptied (dispatch R1059,
    DoD 3 — renders identical to the byte outside the appendix)."""

    @staticmethod
    def _render(body_check=None):
        from argumentation_analysis.reporting.restitution.acts import (
            RestitutionActs,
        )
        from argumentation_analysis.reporting.restitution.renderer import (
            RestitutionReportRenderer,
        )

        acts = RestitutionActs(
            act1_framing="Le contexte du discours, ses circonstances et son "
            "enjeu central sont posés : une assemblée, une décision, une "
            "tension.",
            act2_narrative="Le mouvement central réfute la théorie FOL "
            "testée : le solveur Tweety a éprouvé les propositions d'action, "
            "et cet échec remet en cause toute affirmation qui dépend des "
            "mêmes relations. Le slogan rythmé, procédé visant à créer "
            "l'adhésion par la répétition, fragilise le passage.",
            act3_conclusion="Trouver décisif (P1) : la réfutation formelle "
            "de l'attribution, qui change le jugement porté sur la thèse. "
            "En second, la répétition du slogan fragilise la conclusion "
            "inverse.",
            source_id="corpus_anonyme",
        )
        renderer = RestitutionReportRenderer()
        target = (
            "argumentation_analysis.reporting.restitution.renderer."
            "check_act_reader_contract"
        )
        if body_check is not None:
            with um.patch(target, return_value=body_check):
                return renderer.render(acts)
        return renderer.render(acts)

    def test_findings_section_rides_in_the_fold(self):
        finding = ContractFinding(
            criterion=2,
            kind="formal_citation_without_derivation",
            act="Acte II",
            line=7,
            excerpt="badge",
            note="constat de test",
        )
        report = self._render(body_check=[finding])
        assert "Contrôles de contrat lecteur (#1914, critères 2-4)" in report.markdown
        assert "formal_citation_without_derivation" in report.markdown
        # the fold starts after the acts — the finding never leaks to the
        # reader surface
        fold_at = report.markdown.index("<details>")
        section_at = report.markdown.index("Contrôles de contrat lecteur")
        assert section_at > fold_at

    def test_acts_are_byte_identical_with_and_without_findings(self):
        with_findings = self._render(
            body_check=[
                ContractFinding(
                    criterion=3,
                    kind="label_without_function",
                    act="Acte II",
                    line=9,
                    excerpt="étiquette",
                    note="constat",
                )
            ]
        ).markdown
        without = self._render(body_check=[]).markdown
        # everything BEFORE the appendix fold is the reader surface — it must
        # not differ by one byte
        assert with_findings.split("<details>")[0] == without.split("<details>")[0]
        assert with_findings != without

    def test_compliant_acts_say_no_findings(self):
        report = self._render(body_check=None)  # the real control runs
        assert "Aucun constat" in report.markdown
