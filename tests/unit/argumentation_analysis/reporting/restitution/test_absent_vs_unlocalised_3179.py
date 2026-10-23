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
