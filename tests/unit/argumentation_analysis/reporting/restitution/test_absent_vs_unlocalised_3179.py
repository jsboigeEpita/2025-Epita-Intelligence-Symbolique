"""#3179 — « content absent » and « conflict not localised » are two absences.

`extract_tested_content` returns ``None`` in two unrelated situations, and the
Act II anchor rendered both with « contenu testé non disponible dans l'état
(compteur seul) »:

1. the selected records carry **no real formula** (placeholder-only or empty) —
   here « compteur seul » is true;
2. the records carry **real formulas** but the conflict does not localise (no
   recorded core, no complementary unit pair — e.g. a conflict spread over
   compound formulas). Since #2960 the decisive role must not fire against a
   specific inference there, and that part stays: what was wrong is telling
   the reader the content is absent when the state holds it.

Both witnesses below read the Act II anchor line for the FOL axis, never the
whole prompt (the conductor's consigne quotes the honest-absence wording by
design).
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act_reader_contract_check import (
    check_act_reader_contract,
)

from .test_act_reader_contract_check_1914 import _GOOD_ACT3, _body

_COMPOUND = [
    "forall x (humain(x) -> mortel(x))",
    "humain(socrate) & sage(socrate)",
    "mortel(socrate) -> !immortel(socrate)",
    "forall x (sage(x) -> respecte(x, socrate))",
    "respecte(platon, socrate) | !respecte(platon, socrate)",
    "exists y (disciple(y, socrate) & jeune(y))",
    "disciple(platon, socrate) -> jeune(platon)",
    "!jeune(platon) -> !disciple(platon, socrate)",
    "forall x (jeune(x) -> !sage(x))",
    "sage(platon) | !sage(platon)",
    "mortel(platon) & humain(platon)",
    "humain(platon) -> existe_esprit(platon)",
    "!(existe_esprit(platon) & mortel(platon))",
    "existe_esprit(platon) -> !mortel(platon)",
    "forall x (mortel(x) -> fini(x))",
    "fini(platon) | infini(platon)",
    "!(fini(platon) & infini(platon))",
    "infini(platon) -> !fini(platon)",
]

assert len(_COMPOUND) == 18


def _state(fol_records):
    return SimpleNamespace(
        identified_arguments={"arg_1": "these A"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=fol_records,
        modal_analysis_results=[],
        workflow_results={},
    )


def _fol_anchor(prompt: str) -> str:
    """The Act II anchor line of the FOL axis — the surface #1914 governs."""
    prefix = "  - logique du premier ordre :"
    lines = [ln for ln in prompt.splitlines() if ln.startswith(prefix)]
    assert lines, "the FOL axis must render one anchor line"
    return lines[0]


class TestNotLocalised:
    """Real formulas, no localisable conflict: the anchor says so."""

    def _prompt(self) -> str:
        records = [
            {
                "consistent": False,
                "message": "inconsistent",
                "consistency_cause": {"cause": "undetermined"},
                "formulas": list(_COMPOUND),
            }
        ]
        return build_act2_prompt(build_act2_evidence(_state(records)))

    def test_anchor_does_not_claim_the_content_is_absent(self):
        anchor = _fol_anchor(self._prompt())
        assert "non disponible" not in anchor, (
            "the state carries 18 formulas — claiming the content is absent "
            f"is false: {anchor!r}"
        )
        assert "compteur seul" not in anchor, anchor

    def test_anchor_states_the_number_of_formulas_tested(self):
        anchor = _fol_anchor(self._prompt())
        assert (
            "18" in anchor
        ), f"the anchor must state how many formulas were tested: {anchor!r}"

    def test_anchor_names_the_not_localised_conflict(self):
        anchor = _fol_anchor(self._prompt()).lower()
        assert (
            "localis" in anchor
        ), f"the anchor must say the conflict is not localised: {anchor!r}"


class TestAbsent:
    """Placeholder-only records keep the original honest absence."""

    def test_placeholder_only_keeps_the_counter_wording(self):
        records = [
            {
                "consistent": False,
                "message": "inconsistent",
                "formulas": ["CL(0 conditionals): no clause recorded"],
            }
        ]
        anchor = _fol_anchor(build_act2_prompt(build_act2_evidence(_state(records))))
        assert "non disponible" in anchor or "compteur seul" in anchor, anchor
        assert "18" not in anchor


class TestReaderContract:
    """#3189 rework (R1109): the reader-side criterion 2 exempts the #3179
    anchor's own wording, exactly like « non disponible » before it — a
    sentence restating « conflit non localisé » without a change-verb is the
    honest absence the anchor teaches, not a badge."""

    # Mirrors what a writer following the anchor's teaching produces: a formal
    # citation, a named tested content, the #3179 absence wording — and NO
    # change-verb (the verdict rightly does not localise on any inference).
    _NOT_LOCALISED = (
        "## Acte II — Récit dialectique\n\n"
        "Le solveur Tweety a éprouvé les formules de l'axe FOL, mais le "
        "conflit est non localisé : aucune paire de formules ne porte la "
        "contradiction.\n"
    )

    def test_the_anchor_wording_without_a_change_verb_is_compliant(self):
        findings = check_act_reader_contract(_body(self._NOT_LOCALISED, _GOOD_ACT3))
        assert not [f for f in findings if f.criterion == 2], findings

    def test_the_same_citation_without_the_absence_wording_is_flagged(self):
        act2 = (
            "## Acte II — Récit dialectique\n\n"
            "Le solveur Tweety a éprouvé les formules de l'axe FOL pour ce "
            "mouvement.\n"
        )
        findings = check_act_reader_contract(_body(act2, _GOOD_ACT3))
        c2 = [f for f in findings if f.criterion == 2]
        assert c2, "the same citation without an absence is still a badge"
        assert c2[0].kind == "formal_citation_without_change", findings
