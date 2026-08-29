"""THE self-contained né-rouge for #1914 (named in the PR body).

This file deliberately imports ONLY modules that exist on main:
``act2_narrative_plugin`` predates the PR. Pre-fix, the assertion reddens
with ``AttributeError`` — the evidence dataclass has no ``role_assignments``
field — never ``ImportError``. That is what makes it the discriminating
né-rouge: the red proves the missing capability, not a missing module
(the R881 lesson: a guard that imports the module the PR creates reddens
for free and proves nothing).

The sister file ``test_specialist_roles_1914.py`` carries the full suite;
it cannot serve as the né-rouge because its module-level import of
``specialist_roles`` fails wholesale on pre-fix content.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
)


def test_act2_evidence_carries_role_assignments() -> None:
    """The Acte II evidence bundle carries the role classification."""
    state = SimpleNamespace(
        identified_arguments={"arg_1": "these"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        fol_analysis_results=[{"consistent": False, "message": "incoherent"}],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
    )
    evidence = build_act2_evidence(state)
    assert (
        evidence.role_assignments
    ), "the Acte II evidence bundle must carry the role classification"
