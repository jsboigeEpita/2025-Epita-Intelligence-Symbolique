"""#1914 (Acte III slice) — THE self-contained né-rouge.

The sister file ``test_conclusion_salience_1914.py`` imports
``conclusion_salience`` module-level and therefore fails wholesale on
``ImportError`` before the fix exists — it discriminates nothing. This file
imports ONLY ``act3_conclusion_plugin`` (present on main long before this
PR): pre-fix it reddens with ``AttributeError`` (the evidence bundle has no
``salience`` field) and on the missing prompt sections — red for the RIGHT
reason either way.

Replay recipe (the stash discipline from #1914 Acte II): stash ONLY the
``act3_conclusion_plugin.py`` wiring; this file must go red on the two
assertions below while the suite's other greens are untouched.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)


def _state() -> SimpleNamespace:
    return SimpleNamespace(
        identified_arguments={"arg_1": "these A", "arg_9": "these C"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[{"consistent": False, "message": "incoherent"}],
        modal_analysis_results=[],
        workflow_results={},
    )


def test_act3_evidence_carries_the_salience_channel():
    evidence = build_act3_evidence(_state())
    assert (
        evidence.salience is not None
    ), "the conclusion evidence must carry the salience ranking + surplus"
    assert (
        evidence.salience.surplus.established
    ), "a refuted FOL theory on this fixture is established zero-shot surplus"


def test_act3_prompt_renders_hierarchy_and_surplus_sections():
    prompt = build_act3_prompt(build_act3_evidence(_state()))
    assert "HIÉRARCHIE DU VERDICT" in prompt
    assert "SURPLUS MULTI-AGENTS" in prompt
    assert "QUATRE ORDRES DE JUGEMENT" in prompt
