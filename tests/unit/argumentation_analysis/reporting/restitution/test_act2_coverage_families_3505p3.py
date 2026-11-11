"""#3505 part 3 — an argument the review retained a fallacy on leaves « non examinés ».

The part-2 measure (R1161): all fallacy-bearing items sat in ``non examinés``
— arguments no deep detection reached, which the writer sums up in one
sentence (« no reader examined these »). For an argument the coverage walk
examined and retained a fallacy on, that sentence is false. So:

- an argument with NO deep detection, outside the deep sample, carrying a
  review-retained fallacy of family B joins movement B (created if absent)
  — by the deep rule: sorted families, the first; « hors taxonomie » when
  the fallacy has no family;
- an argument with a deep detection of family A and a review fallacy of
  family B stays in A (the deep family keeps the theme);
- an argument outside the sample with no retained fallacy stays in
  « non examinés »; so does one with a lens-only item and no fallacy;
- an empty review leaves the prompt byte-identical (the #3492 control);
- the procédé line's free-text fields go through ``_one_line`` (#3504).

The document and its passages are made up: no corpus text, no source name.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.reading.coverage_review import LENS_BY_CLASS
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from tests.unit.argumentation_analysis.reporting.restitution.test_act2_coverage_procedes_3505 import (
    ATTRIBUTION,
    DEEP_FALLACIES,
    DOCUMENT,
    PASSAGE,
    PASSAGE_OFFSET,
    UNITS,
    WALK_EXPLANATION,
    WALK_FAMILY,
    WALK_TYPE,
    coverage_item,
    make_state,
    movement_block_of,
    record,
    walk_fallacy,
)

#: The deep sample holds ONLY arg_1 — arg_2 is outside the deep sample, the
#: exact case the coordinator measured (all 9 items in « non examinés »).
OUTSIDE_SAMPLE = {"fallacy_per_argument": {"unit_ids": ["arg_1"]}}


def state_outside_sample(items, identified_fallacies=None):
    state = make_state(record(*items), identified_fallacies=identified_fallacies)
    state.analysis_coverage = {k: dict(v) for k, v in OUTSIDE_SAMPLE.items()}
    return state


def test_an_argument_the_review_flagged_leaves_non_examines():
    """No deep detection, outside the sample, review fallacy family B:
    the argument sits in movement B, not in « non examinés », and carries
    its attributed procédé line; the movement says what, the line says who."""
    bound = coverage_item(quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2")
    state = state_outside_sample([bound])

    prompt = build_act2_prompt(build_act2_evidence(state))
    block = movement_block_of(prompt, UNITS["arg_2"])

    assert f"MOUVEMENT « {WALK_FAMILY} »" in block
    assert "non examinés" not in block
    assert block.count(ATTRIBUTION) == 1
    assert f"{ATTRIBUTION}« {WALK_TYPE} » (famille {WALK_FAMILY})" in block


def test_a_deep_detection_keeps_its_family_as_the_theme():
    """Deep family A + review family B: the argument stays in A."""
    bound = coverage_item(quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2")
    state = state_outside_sample([bound], identified_fallacies=DEEP_FALLACIES)

    prompt = build_act2_prompt(build_act2_evidence(state))
    block = movement_block_of(prompt, UNITS["arg_2"])

    assert "MOUVEMENT « Pertinence »" in block
    assert f"MOUVEMENT « {WALK_FAMILY} »" not in prompt
    # Both lines still render, in the deep family's movement.
    assert block.count("Procédé : ") == 1
    assert block.count(ATTRIBUTION) == 1


def test_an_unflagged_argument_outside_the_sample_stays_non_examines():
    """No deep detection, outside the sample, nothing retained: unchanged."""
    routed = {
        "lens": "fallacy_descent",
        "status": "answered",
        "finding": {"status": "answered", "fallacies": []},
    }
    bound = coverage_item(
        quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2", routed=routed
    )
    state = state_outside_sample([bound])

    prompt = build_act2_prompt(build_act2_evidence(state))
    block = movement_block_of(prompt, UNITS["arg_2"])

    assert "MOUVEMENT « non examinés »" in block
    assert "MOUVEMENT « " + WALK_FAMILY + " »" not in prompt


def test_a_lens_only_item_moves_nothing():
    """An item that carries only a lens answer and no fallacy: no movement."""
    lens = LENS_BY_CLASS["modal"]
    routed = {
        "lens": lens,
        "status": "answered",
        "finding": {
            "status": "answered",
            "verdict": "consistent_with_run_kb",
            "formula": "◇p",
            "reason": "le passage est cohérent avec la base modale du run",
        },
    }
    bound = coverage_item(
        quote=PASSAGE,
        offset=PASSAGE_OFFSET,
        kind="modal",
        unit_id="arg_2",
        routed=routed,
    )
    state = state_outside_sample([bound])

    prompt = build_act2_prompt(build_act2_evidence(state))
    block = movement_block_of(prompt, UNITS["arg_2"])

    assert "MOUVEMENT « non examinés »" in block
    assert ATTRIBUTION not in prompt


def test_an_empty_review_leaves_the_prompt_byte_identical():
    """The #3492 control, kept: nothing named, nothing moved, nothing added."""
    with_empty_review = make_state(record())
    with_empty_review.analysis_coverage = {
        k: dict(v) for k, v in OUTSIDE_SAMPLE.items()
    }
    without_record = make_state()
    without_record.analysis_coverage = {k: dict(v) for k, v in OUTSIDE_SAMPLE.items()}

    prompt_empty = build_act2_prompt(build_act2_evidence(with_empty_review))
    prompt_bare = build_act2_prompt(build_act2_evidence(without_record))

    assert prompt_empty == prompt_bare


def test_a_fallacy_without_a_family_invents_none():
    """The deep rule applies: no family → « hors taxonomie », never invented."""
    fallacy = walk_fallacy()
    fallacy["family"] = ""
    routed = {
        "lens": "fallacy_descent",
        "status": "answered",
        "finding": {"status": "answered", "fallacies": [fallacy]},
    }
    bound = coverage_item(
        quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2", routed=routed
    )
    state = state_outside_sample([bound])

    prompt = build_act2_prompt(build_act2_evidence(state))
    block = movement_block_of(prompt, UNITS["arg_2"])

    assert "MOUVEMENT « hors taxonomie »" in block
    assert block.count(ATTRIBUTION) == 1


def test_a_line_break_in_the_explanation_renders_as_one_line():
    """#3504's rule reaches the new line: label and explanation collapsed."""
    fallacy = walk_fallacy()
    fallacy["explanation"] = "première ligne du motif\nseconde ligne du motif"
    routed = {
        "lens": "fallacy_descent",
        "status": "answered",
        "finding": {"status": "answered", "fallacies": [fallacy]},
    }
    bound = coverage_item(
        quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2", routed=routed
    )
    state = state_outside_sample([bound])

    prompt = build_act2_prompt(build_act2_evidence(state))
    block = movement_block_of(prompt, UNITS["arg_2"])

    procede_lines = [line for line in block.splitlines() if ATTRIBUTION in line]
    assert len(procede_lines) == 1
    assert "première ligne du motif seconde ligne du motif" in procede_lines[0]


def test_coverage_family_by_unit_is_empty_on_a_lens_only_review():
    """The producer itself: no retained fallacy anywhere → no assignment."""
    from argumentation_analysis.agents.core.reading.coverage_review import (
        coverage_family_by_unit,
    )

    bound = coverage_item(
        quote=PASSAGE,
        offset=PASSAGE_OFFSET,
        unit_id="arg_2",
        routed={
            "lens": "fallacy_descent",
            "status": "answered",
            "finding": {"status": "answered", "fallacies": []},
        },
    )
    state = state_outside_sample([bound])
    assert coverage_family_by_unit(state) == {}
