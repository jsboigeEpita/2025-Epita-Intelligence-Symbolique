# -*- coding: utf-8 -*-
"""#3296 — the writer's inputs carry no bare ``arg_N``: per-act label tables.

The census (issue comment 6525864773) measured 15 input blocks handing the
conductor a bare machine id; the readability gate (#2980) counts every
printed id as jargon and the renders echoed them (5 of 41, R1125a). PR #3303
removed the directives that ORDERED the id; this witness pins the second
half (R1126 arbitration): the ids the DATA blocks SUPPLY are designated by a
per-act Greek-letter table whose legend carries the referent — the
#2896/#2965 precedent, generalised from the thread to the whole act.

Born red: every fixture below arms a path the census named, and on main each
one prints a bare id. Non-vacuity is asserted, never assumed — a fixture
that stops arming its path (e.g. the salience branch, which needs BOTH the
``scores`` key and ``analysis_coverage["fallacy_per_argument"]["unit_ids"]``,
measured in c. 6531974201) must redden on the label-count assertion, not
pass silently on an empty prompt.
"""

import re
from types import SimpleNamespace

from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    _build_prose_prompt,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    Act2Evidence,
    ArgEvidence,
    MovementEvidence,
    ROLE_ORDER,
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)
from argumentation_analysis.reporting.restitution.global_projection import (
    GlobalFinding,
)
from argumentation_analysis.reporting.restitution.specialist_roles import (
    RoleAssignment,
)

_RAW_ID = re.compile(r"\barg_\d+\b")
_GREEK = set("αβγδεζηθικλμνξοπρστυφχψω")
_LEGEND_HEADING = "LÉGENDE DES DÉSIGNATIONS"


def _letters_in(text: str) -> set:
    return {c for c in text if c in _GREEK}


# --- Acte III: a state that arms the measured paths --------------------------
# The salience branch (``arg_N tient : qualité mesurée solide`` — the id is
# IN the statement, conclusion_salience) needs the quality ``scores`` key AND
# the fallacy coverage record; without either, the branch stays silent and a
# prompt with no id proves nothing (c. 6531974201).


def _act3_state() -> SimpleNamespace:
    return SimpleNamespace(
        identified_arguments={
            "arg_1": "these A — première unité mesurée",
            "arg_9": "these C — unité mesurée aussi",
        },
        identified_fallacies={},
        argument_quality_scores={
            "arg_1": {"overall": 1.9, "scores": {"clarte": 0.95, "pertinence": 0.95}},
            "arg_9": {"overall": 1.7, "scores": {"clarte": 0.85, "pertinence": 0.85}},
        },
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
        analysis_coverage={"fallacy_per_argument": {"unit_ids": ["arg_1", "arg_9"]}},
    )


def test_act3_prompt_carries_no_bare_unit_id():
    evidence = build_act3_evidence(_act3_state())
    prompt = build_act3_prompt(evidence)
    hits = _RAW_ID.findall(prompt)
    assert not hits, f"the Act III prompt still hands the writer bare ids: {hits}"
    # Non-vacuity: the fixture must have armed the salience branch (the
    # census's worst block) — a Greek letter must be in the prompt.
    assert _letters_in(
        prompt
    ), "no label in the Act III prompt — the fixture armed nothing"
    assert _LEGEND_HEADING in prompt, "the per-act legend is missing"
    # The legend binds a letter to the unit TEXT (the referent travels).
    assert re.search(
        r"•\s*\S+\s*:.*these A", prompt
    ), "the legend carries no referent text — a letter with nothing to read"
    # Mixed vocabulary: method cites (``qualite``) are readable referents of
    # their own and must survive untranslated.
    assert "qualite" in prompt, "the method cite `qualite` was consumed by the table"


def test_act2_prompt_carries_no_bare_unit_id():
    evidence = Act2Evidence(
        movements=[
            MovementEvidence(
                movement_id="m1",
                theme="soutiens",
                arguments=[
                    ArgEvidence(
                        arg_id="arg_2", description="l'ouverture mesurée du discours"
                    )
                ],
            )
        ],
        quality_ranking="Classement qualité (base : 3 unités évaluées sur 9) : arg_2 (9.1), arg_5 (8.0), arg_7 (7.2).",
        role_assignments=[
            RoleAssignment(
                role=ROLE_ORDER[0],
                statement="un résultat decisif sur arg_2",
                cites=("arg_2", "qualite"),
            )
        ],
        global_findings=[
            GlobalFinding(
                kind="convergence",
                statement="arg_5 : 2 méthodes indépendantes convergent (fallacy, quality)",
                cites=("arg_5", "fallacy", "quality"),
            )
        ],
        unit_texts={
            "arg_2": "l'ouverture mesurée du discours",
            "arg_5": "un développement appuyé par deux axes",
        },
        args_total=9,
    )
    prompt = build_act2_prompt(evidence)
    hits = _RAW_ID.findall(prompt)
    assert not hits, f"the Act II prompt still hands the writer bare ids: {hits}"
    assert _letters_in(
        prompt
    ), "no label in the Act II prompt — the fixture armed nothing"
    assert _LEGEND_HEADING in prompt
    assert (
        "l'ouverture mesurée du discours" in prompt
    ), "the legend carries no referent text — a letter with nothing to read"
    assert "qualite" in prompt, "the method cite `qualite` was consumed by the table"


def test_prose_prompt_carries_no_bare_unit_id():
    prompt = _build_prose_prompt(
        {
            "convergent_verdicts": {
                "arg_12": {
                    "score": 3,
                    "signals": [
                        ("fallacy", "appel à l'autorité relevé"),
                        ("quality", "clarté mesurée haute"),
                    ],
                },
                "arg_3": {
                    "score": 2,
                    "signals": [("fallacy", "glissement sémantique relevé")],
                },
            },
            "conclusion": "les axes convergent sur deux unités",
        }
    )
    hits = _RAW_ID.findall(prompt)
    assert not hits, f"the convergence-prose prompt still hands bare ids: {hits}"
    assert _letters_in(
        prompt
    ), "no label in the prose prompt — the fixture armed nothing"


def test_one_letter_one_argument_across_blocks():
    """The thread and the data blocks share ONE vocabulary — the #3296
    generalisation of #2896. Before it, the sequence block owned a private
    letter map (α for its first actor) while the movement bullets printed
    bare ids: two designations for one corpus, and a collision the moment
    both surfaces used letters."""
    evidence = Act2Evidence(
        movements=[
            MovementEvidence(
                movement_id="m1",
                theme="soutiens",
                arguments=[ArgEvidence(arg_id="arg_2", description="l'ouverture")],
            )
        ],
        unit_texts={"arg_2": "l'ouverture", "arg_40": "une retracte plus loin"},
        args_total=2,
        text_sequence=None,
    )
    prompt = build_act2_prompt(evidence)
    # arg_2 appears in the movement bullet AND (were the sequence present)
    # would appear in the thread: one id, one letter, everywhere.
    assert not _RAW_ID.search(prompt)
    legend = prompt[prompt.index(_LEGEND_HEADING) :]
    assert legend.count("•") >= 1


def test_state_built_evidence_carries_the_unit_texts():
    """The plumbing: the evidence builders fill ``unit_texts`` from the
    state's identified arguments (capped) — the legend's referent source."""
    act2 = build_act2_evidence(_act3_state())
    assert act2.unit_texts.get("arg_1", "").startswith(
        "these A"
    ), "Act II evidence carries no unit text for the legend"
    act3 = build_act3_evidence(_act3_state())
    assert act3.unit_texts.get("arg_1", "").startswith(
        "these A"
    ), "Act III evidence carries no unit text for the legend"
