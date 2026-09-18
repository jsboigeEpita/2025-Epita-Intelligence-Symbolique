"""#2307 — a contentless refutation is not a decisive finding.

Measured on the #2298 negative control (no-JVM canary, 11 formal phases
failed): the run still earned a ``decisif_formel`` surplus item anchored
``("PL", "solveur Tweety")`` while the solver physically never ran — the
Acte III prompt said it verbatim: « L'axe PL a réfuté 1 inférence :
contenu testé non disponible dans l'état ». ``classify_specialist_roles``
promotes any ``counts["false"] > 0`` to ROLE_DECISIF; when the records are
placeholder-only, ``extract_tested_content`` returns None and the statement
admits the absence — but the ROLE (and the surplus item, and the ranked P1)
still claims a decisive formal refutation. An outage flatters the #1644
gate (measured: the dead-JVM run carries one MORE established item than
the healthy control).

Tri-state (#1019): a refutation without tested content is not a refutation
— the axis established nothing citable, so it earns no role. The honest
absence lives in the role's absence, not in a decisive statement that
apologizes for itself.
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import conclusion_salience as cs
from argumentation_analysis.reporting.restitution.specialist_roles import (
    ROLE_DECISIF,
    classify_specialist_roles,
)


def _state(pl_records):
    return SimpleNamespace(
        identified_arguments={"arg_1": "these A"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=pl_records,
        fol_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
    )


class TestContentlessRefutationIsNotDecisive:
    def test_placeholder_refutation_earns_no_decisive_role(self):
        # The dead-JVM shape: a false verdict over placeholder-only records.
        state = _state(
            [{"satisfiable": False, "formulas": ["KB analysis unavailable"]}]
        )
        roles = classify_specialist_roles(state)
        decisif = [r for r in roles if r.role == ROLE_DECISIF]
        assert decisif == [], (
            "#2307: a refutation whose tested content is unavailable "
            "(placeholder-only records, solver never ran) must not earn the "
            "decisive role"
        )

    def test_placeholder_refutation_earns_no_decisif_formel_surplus(self):
        state = _state(
            [{"satisfiable": False, "formulas": ["KB analysis unavailable"]}]
        )
        sal = cs.assess_conclusion_salience(state)
        assert sal.surplus.established == [], (
            "an outage must not flatter the #1644 gate with a phantom "
            "decisif_formel item"
        )

    def test_no_formula_key_refutation_earns_no_decisive_role(self):
        # Same shape without the formulas key at all (the #1914 fixture
        # historically pinned this as decisive — the defect's own shape).
        state = _state([{"satisfiable": False, "message": "incoherent"}])
        roles = classify_specialist_roles(state)
        assert [r for r in roles if r.role == ROLE_DECISIF] == []


class TestRealRefutationStaysDecisive:
    def test_formulas_backed_refutation_is_decisive(self):
        # Non-vacuity: the classifier still knows a REAL refutation when it
        # sees one — a false verdict over real formulas stays decisive.
        state = _state([{"satisfiable": False, "formulas": ["mortal(socrates)"]}])
        roles = classify_specialist_roles(state)
        decisif = [r for r in roles if r.role == ROLE_DECISIF]
        assert decisif, "a content-backed refutation must stay decisive"
        assert "PL" in decisif[0].cites
        assert "mortal" in decisif[0].statement.lower() or "«" in decisif[0].statement

    def test_real_refutation_still_reaches_the_surplus(self):
        state = _state([{"satisfiable": False, "formulas": ["mortal(socrates)"]}])
        sal = cs.assess_conclusion_salience(state)
        decisif_formel = [
            s for s in sal.surplus.established if s.cites and "PL" in s.cites
        ]
        assert decisif_formel, "the healthy decisive finding must still count"
