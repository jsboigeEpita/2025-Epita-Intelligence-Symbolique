# -*- coding: utf-8 -*-
"""#1914 (criteria 2, 3, 4 — dispatch R1059, rework R1060) — post-render act
controls.

The card (c.5969933470) measured the shared gap: the three contracts are
held at prompt + evidence level, and NO test reads a rendered act. These
witnesses pin the mechanical half — each control finds its planted defect on
a synthetic faulty act (positive control), stays silent on a compliant one
(negative control), and the mutation test proves the witness depends on the
control.

R1060 (review c.5974319482) adds the false-positive-class witnesses: each
structural guard (negation scope, withdrawal, judgment step, virtue names,
badge counting shapes, Dung consigne formula, discourse citations, meta
axis enumeration, reader guidance, heading lines, uppercase act headings,
the not-evaluated envelope) has its own ± pair, so a future lexicon change
that quietly widens a guard reddens here.

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

# The faulty shapes — the badge without derivation (2), the piled labels
# without function (3).
_BAD_ACT2 = (
    "## Acte II — Récit dialectique\n\n"
    "La preuve formelle du mouvement est rappelée ici : "
    '"[pl] 3 inférence(s) PL consistantes — ancrage : solveur Tweety".\n\n'
    "L'orateur cumule la « généralité flatteuse », l'« ingratiation » et le "
    "« sophisme d'autorité » dans ce mouvement.\n"
)

# Change stated, tested not: the consigne's consistency formula around a raw
# badge — still a finding (the reader receives a counter, not a content).
_BAD_ACT2_CONFIRMED = (
    "## Acte II — Récit dialectique\n\n"
    "La cohérence du mouvement est confirmée par les solveurs : "
    '"[pl] 3 inférence(s) PL consistantes — ancrage : solveur Tweety".\n'
)

_BAD_ACT3_FLAT = "## Acte III — Conclusion actionnable\n\n" + "".join(
    f"Le propos contient un sophisme de type n°{i}.\n\n" for i in range(1, 8)
)

_GOOD_ACT3 = (
    "## Acte III — Conclusion actionnable\n\n"
    "Trouver décisif (P1) : la réfutation formelle des propositions "
    "d'attribution, qui change le jugement porté sur la thèse.\n\n"
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

    def test_change_without_tested_is_found(self):
        """R1060: the consigne's confirm formula around a raw badge is still
        a finding — the badge's counting shape is not a tested content."""
        findings = check_act_reader_contract(_body(_BAD_ACT2_CONFIRMED, _GOOD_ACT3))
        c2 = [f for f in findings if f.criterion == 2]
        assert c2, "confirmée + badge must still produce a criterion-2 finding"
        assert c2[0].kind == "formal_citation_without_tested"

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

    def test_dung_consigne_formula_is_clean(self):
        """R1060: « le cadre de Dung isole cette revendication comme
        rejetée » is the Act III consigne's own derivation formula — tested
        (revendication) and change (isolée comme rejetée) both carried."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "Le cadre de Dung isole cette revendication comme rejetée, ce "
            "qui oblige à reconsidérer la thèse centrale du mouvement.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 2]

    def test_virtue_names_are_not_formal_citations(self):
        """R1060: the nine quality virtues are not solver verdicts —
        « réfutation constructive » (and its snake_case leak) must not arm
        the citation control."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "L'argument montre de la clarté, de la pertinence et une "
            "réfutation constructive, avec un score refutation_constructive "
            "élevé sur ce mouvement.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 2]

    def test_prose_inférence_is_tested_but_the_badge_count_is_not(self):
        """R1060: « inférence » in prose names the tested object; the badge
        counting shape (« 3 inférence(s) ») does not."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "Le solveur Tweety confirme la consistance des inférences issues "
            "de ces soutiens, ce qui valide qu'ils tiennent ensemble.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 2]


class TestCriterion3LabelWithoutFunction:
    def test_piled_labels_are_found(self):
        findings = check_act_reader_contract(_body(_BAD_ACT2, _GOOD_ACT3))
        c3 = [f for f in findings if f.criterion == 3]
        assert c3, "the piled-labels sentence must produce a criterion-3 finding"
        assert c3[0].kind == "label_without_function"

    def test_function_clause_is_clean(self):
        findings = check_act_reader_contract(_body(_GOOD_ACT2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3]

    def test_negated_cue_is_compliant(self):
        """R1060: « sans procédé identifiable » DENIES a device — the cue
        under a negation is not a label."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "Ce passage reste descriptif, sans procédé identifiable ni "
            "figure marquée.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3]

    def test_withdrawal_is_compliant(self):
        """R1060: withdrawing labels (« ne sont pas établies ») is the honest
        move the issue praises, not a pile."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "Les étiquettes « pente glissante » et « homme de paille » ne "
            "sont pas établies par les vérifications de ce run.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3]

    def test_judgment_step_is_compliant(self):
        """R1060: judging whether the device weakens the reasoning is the
        consigne's SECOND step — a judging sentence is not a bare label."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "Le contre-argument borne la portée de ce procédé et juge s'il "
            "fragilise le raisonnement du mouvement.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3]

    def test_discourse_quotes_are_not_a_label_pile(self):
        """R1060: quotes carried by a discourse verb / a discourse subject
        are citations of what was said, not device labels."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "Le discours présente « la victoire finale » et « la renaissance "
            "nationale » comme promesses centrales du programme.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3]

    def test_meta_axis_enumeration_is_compliant(self):
        """R1060: enumerating the analysis's own axes describes the
        analysis, not the discourse."""
        act3 = (
            "## Acte III — Conclusion actionnable\n\n"
            "D'abord, le point décisif : l'analyse croise sophismes, "
            "qualité et contre-arguments pour ce corpus, et cela change le "
            "jugement.\n"
        )
        findings = check_act_reader_contract(_body(_GOOD_ACT2, act3))
        assert not [f for f in findings if f.criterion == 3]

    def test_reader_guidance_imperative_is_compliant(self):
        """R1060: the third beat's reader guidance (« recevez avec prudence
        ... ») is the asked-for shape, not a label pile."""
        act3 = (
            "## Acte III — Conclusion actionnable\n\n"
            "D'abord le point décisif du jugement. Recevez avec prudence les "
            "passages « flatteur » et « alarmiste » du discours.\n"
        )
        findings = check_act_reader_contract(_body(_GOOD_ACT2, act3))
        assert not [f for f in findings if f.criterion == 3]

    def test_plural_accomplissent_carries_the_function(self):
        """R1061 (d): the consigne's own function verb in the PLURAL — « ces
        procédés accomplissent... » — states the function as surely as the
        singular the lexicon carries; a plural must not arm the control."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "Ces procédés accomplissent un déplacement de l'attention vers "
            "le passé du locuteur.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3], (
            "« accomplissent » is the consigne's function verb in the plural — "
            "the sentence carries its function, no finding"
        )

    def test_withdrawal_with_adverb_is_compliant(self):
        """R1061 (d): the honest withdrawal survives an adverb — « ne sont
        pas davantage établies » withdraws exactly like « ne sont pas
        établies »."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "Les étiquettes « pente glissante » et « homme de paille » ne "
            "sont pas davantage établies par les vérifications de ce run.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3], (
            "withdrawal with an adverb is still the honest withdrawal the "
            "issue praises, not a pile"
        )

    def test_not_fallacieux_judgment_is_compliant(self):
        """R1061 (d): « n'est pas fallacieux » is the consigne's second step
        (judging whether the device weakens) — a negated judgment, not a
        label; the elided « n' » escapes the negation guard, so the judgment
        lexicon must carry it."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "La répétition soulignée par l'analyse n'est pas fallacieuse au "
            "sens strict du terme.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 3], (
            "a sentence that judges « pas fallacieux » is the consigne's "
            "second step, not a piling label"
        )

    def test_heading_label_line_is_not_prose(self):
        """R1060: a subsection heading naming a movement is structure, not a
        piling sentence."""
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "### Le mouvement « sophisme d'origine »\n\n"
            "Le propos tient ici par la filiation qu'il instaure.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
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

    def test_consigne_ranking_markers_are_clean(self):
        """R1060: the Act III consigne's own order vocabulary — « les P1
        d'abord », « l'argument arrivé en tête », the P1 superlative —
        counts as a ranking marker."""
        for marker in (
            "Les P1 d'abord, puis les tensions accompagnent le jugement.",
            "L'argument arrivé en tête porte le verdict de ce run.",
            "Le point le plus sérieux concerne la causalité affirmée.",
        ):
            act3 = "## Acte III — Conclusion actionnable\n\n" + marker + "\n"
            findings = check_act_reader_contract(_body(_GOOD_ACT2, act3))
            assert not [
                f for f in findings if f.kind == "no_ranked_marker"
            ], f"marker {marker!r} must count as ranking"

    def test_no_acte_three_skips_honestly(self):
        """A missing Act III is the renderer's own loud degradation — the
        control does not pile a finding on it."""
        findings = check_act_reader_contract(
            "## Acte I — Mise en situation\n\nLe contexte.\n\n" + _GOOD_ACT2
        )
        assert not [f for f in findings if f.criterion == 4]


class TestEnvelope:
    """R1060 silent zeros: a body without act headings must SAY it was not
    evaluated — never look compliant."""

    def test_no_act_heading_yields_one_envelope_finding(self):
        findings = check_act_reader_contract(
            "# Rapport de restitution\n\nCorps sans titre d'acte.\n"
        )
        assert len(findings) == 1
        assert findings[0].criterion == 0
        assert findings[0].kind == "not_evaluated_no_act_heading"
        assert "aucun titre d'acte" in findings[0].note

    def test_uppercase_act_headings_split(self):
        """A real seat render writes « ## ACTE I — » — the split is
        case-insensitive and findings land in the right act."""
        body = (
            "## ACTE I — Mise en situation\n\nLe contexte.\n\n"
            "## ACTE II — Récit dialectique\n\n"
            'La preuve est rappelée : "[pl] 3 inférence(s) PL consistantes — '
            'ancrage : solveur Tweety".\n\n'
            "## ACTE III — Conclusion actionnable\n\n"
            "D'abord le point décisif, puis l'accompagnement.\n"
        )
        findings = check_act_reader_contract(body)
        c2 = [f for f in findings if f.criterion == 2]
        assert (
            c2 and c2[0].act == "Acte II"
        ), "the uppercase heading must still place findings in Acte II"


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
            "des propositions d'attribution, qui change le jugement porté "
            "sur la thèse. En second, la répétition du slogan fragilise la "
            "conclusion inverse.",
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

    def test_c3_findings_render_under_their_own_weak_line(self):
        """R1061 (d): criterion-3 findings ride under their own line — a
        measured-weak diagnostic to be checked by reading, with both seats'
        precision stated — never as an unqualified constat."""
        c2_finding = ContractFinding(
            criterion=2,
            kind="formal_citation_without_derivation",
            act="Acte II",
            line=7,
            excerpt="badge",
            note="constat de test",
        )
        c3_finding = ContractFinding(
            criterion=3,
            kind="label_without_function",
            act="Acte II",
            line=9,
            excerpt="étiquette",
            note="constat",
        )
        report = self._render(body_check=[c2_finding, c3_finding])
        md = report.markdown
        assert (
            "diagnostic faible mesuré" in md
        ), "c3 findings must render under their own measured-weak line"
        assert (
            "0/5" in md and "4/17" in md
        ), "the weak line states both seats' re-measured precision (R1062)"
        assert md.count("label_without_function") == 1, (
            "the c3 kind appears exactly once: rendered twice means the c3 "
            "bullet also sits in the unreserved list above the banner — the "
            "exact regression R1062's mutation measured (rindex only read "
            "the LAST occurrence)"
        )
        banner_at = md.index("diagnostic faible mesuré")
        c3_at = md.index("label_without_function")
        c2_at = md.index("formal_citation_without_derivation")
        assert c3_at > banner_at, "the FIRST c3 occurrence sits under its banner"
        assert c2_at < banner_at, "the c2 bullet stays above the banner"

    def test_empty_case_no_longer_claims_the_weak_control(self):
        """R1061 (d): the empty case may not assert « procédés porteurs de
        leur fonction » — that is the control whose precision is measured
        weak; a zero must not read as its compliance."""
        report = self._render(body_check=[])
        assert "Aucun constat" in report.markdown
        assert "porteurs de leur fonction" not in report.markdown, (
            "the empty case must not claim the measured-weak control as " "passed"
        )

    def test_envelope_renders_as_not_evaluated(self):
        """R1060: the criterion-0 envelope is rendered as an explicit
        not-evaluated line — never as « Aucun constat »."""
        envelope = ContractFinding(
            criterion=0,
            kind="not_evaluated_no_act_heading",
            act="—",
            line=1,
            excerpt="(aucun titre d'acte)",
            note="non évalué : aucun titre d'acte dans le corps rendu — "
            "les contrôles des critères 2-4 ne s'appliquent pas",
        )
        report = self._render(body_check=[envelope])
        assert "non évalué : aucun titre d'acte" in report.markdown
        assert "Aucun constat" not in report.markdown
