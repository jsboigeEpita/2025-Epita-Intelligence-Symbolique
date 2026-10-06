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
        fol_analysis_results=[
            {
                "consistent": False,
                "message": "incoherent",
                "formulas": ["mortal(socrates)", "!mortal(socrates)"],
            },
        ],
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
    """#1914 criterion 5 — anchor each section on a line only the *data* emits.

    Measured on ``main`` (2026-09-29): deleting either data f-string from
    ``build_act3_prompt`` left this test **green**, because ``HIÉRARCHIE DU
    VERDICT`` and ``SURPLUS MULTI-AGENTS`` also appear in the consigne below the
    data, and ``QUATRE ORDRES DE JUGEMENT`` occurs only there. Naming a section
    asserted a constant, not its presence — so this file, named for the salience
    channel, could not detect the channel leaving the prompt. The anchors below
    are emitted by the blocks themselves.
    """
    prompt = build_act3_prompt(build_act3_evidence(_state()))
    assert "  - P1 [" in prompt, "the ranking itself must reach the Act III prompt"
    assert "ÉTABLI (ce qu'une lecture simple ne peut pas produire)" in prompt
    assert "PUREMENT PROCÉDURAL (contexte, jamais un surplus)" in prompt
    assert "QUATRE ORDRES DE JUGEMENT" in prompt  # the consigne pin, named as such
