"""#3505 — a coverage finding binds to the prose it was named for.

The coordinator's measure: 0 of 33 coverage-only labels reach Act II/III while
about half of the deep-phase labels do — the prompt CARRIES the review's block
but the consigne never binds it, and movements come from deep detections only.
The fix is structural: a finding whose span maps to an extracted unit enters
ITS movement's grouping (the review's own line, attribution riding the line);
the findings no movement carries stay in the block and receive one closing
beat. These witnesses pin that, per the issue:

* (a) a non-empty review BINDS — the movement block of the named unit carries
  the finding, once, and the consigne carries the rule; what no movement
  carries stays in the block;
* (b) an empty review leaves the prompt byte-identical — no channel line, no
  rule: the same prompt a state with NO record renders;
* (c) a state whose only detection comes from the coverage walk still gets a
  movement that NAMES it;
* a consistency verdict stays a consistency verdict on the movement's line;
* a named absence stays « nommé, non examiné » on the movement's line.

The document and its passages are made up: no corpus text, no source name.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.reading.coverage_review import LENS_BY_CLASS
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)

# --- a synthetic document and its units -------------------------------------

OPENING = "Le texte ouvre sur une thèse simple."
FILLER = " ".join(
    f"Phrase de liaison numéro {index} sur le contexte du débat."
    for index in range(1, 61)
)
PASSAGE = "Trois taux sur quatre appuient la mesure, sans jamais la qualifier."
UNANCHORED = "Un passage qu'aucune unité extraite ne porte dans son span."
CLOSING = "Le document se referme sur une question ouverte."
DOCUMENT = f"{OPENING} {FILLER} {PASSAGE} {UNANCHORED} {CLOSING}"

PASSAGE_OFFSET = DOCUMENT.index(PASSAGE)
UNANCHORED_OFFSET = DOCUMENT.index(UNANCHORED)

#: The unit texts are PARAPHRASES of the passages, so a prompt-wide count of a
#: quote can only come from the coverage line that carries it.
UNITS = {
    "arg_1": "Une unité qui reformule la thèse en ses propres mots.",
    "arg_2": "Une unité qui reformule l'appui chiffré en ses propres mots.",
}
PROVENANCE = {
    "arg_1": {"producer": "llm_extract", "offset": DOCUMENT.index(OPENING)},
    "arg_2": {"producer": "llm_extract", "offset": PASSAGE_OFFSET},
}

#: arg_2 went through the fallacy walk (nothing retained) — its movement is
#: the soutiens one; its STATISTICAL question was never asked by any lens.
FALLACY_SAMPLE = {"fallacy_per_argument": {"unit_ids": ["arg_1", "arg_2"]}}


def coverage_item(
    *,
    quote: str,
    offset: int,
    kind: str = "statistical",
    unit_id: str = "",
    rank: int = 1,
    routed: dict | None = None,
) -> dict:
    """One review item in the shape ``to_state()`` persists."""
    lens = LENS_BY_CLASS[kind]
    return {
        "unit_id": unit_id,
        "quote": quote,
        "offset": offset,
        "class": kind,
        "lens": lens,
        "reason": "le manquer coûterait au lecteur sa décision",
        "conclusion": "cet argument conclut par lui-même que la mesure tient",
        "rank": rank,
        "routed": routed
        or {"lens": lens, "status": "lens_not_wired", "reason": "synthetic"},
    }


def record(*items: dict) -> dict:
    return {
        "status": "ok",
        "items": list(items),
        "examined": 2,
        "examined_by_class": {},
        "document_chars": len(DOCUMENT),
        "dropped": {},
        "reason": "",
        "basis": "coverage_review",
    }


def make_state(coverage_review: dict | None = None) -> SimpleNamespace:
    state = SimpleNamespace(
        raw_text=DOCUMENT,
        identified_arguments=dict(UNITS),
        argument_provenance={k: dict(v) for k, v in PROVENANCE.items()},
        analysis_coverage={k: dict(v) for k, v in FALLACY_SAMPLE.items()},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
    )
    if coverage_review is not None:
        state.coverage_review = coverage_review
    return state


def movement_block_of(prompt: str, unit_text: str) -> str:
    """The movement block whose bullets carry the unit's text.

    #3296 relabels every ``arg_N`` to a Greek letter before the prompt leaves
    ``build_act2_prompt``, so ids cannot be searched; the unit's own text
    appears in exactly one movement block (blocks are blank-line separated,
    and the movement blocks precede the legend, which carries it too).
    """
    for block in prompt.split("\n\n"):
        if unit_text in block:
            return block
    return ""


# --- witness (a): a non-empty review BINDS ----------------------------------


def test_a_bound_finding_reaches_its_movements_line():
    """The passage's own movement carries the finding — once, attributed."""
    bound = coverage_item(quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2")
    orphan = coverage_item(
        quote=UNANCHORED, offset=UNANCHORED_OFFSET, unit_id="", rank=2
    )
    state = make_state(record(bound, orphan))

    prompt = build_act2_prompt(build_act2_evidence(state))

    block_arg2 = movement_block_of(prompt, UNITS["arg_2"])
    assert "Examen de couverture" in block_arg2
    assert PASSAGE in block_arg2
    # The line keeps its attribution: the review, never a lens.
    assert "pas une lentille" in block_arg2
    # Bound to the movement means DROPPED from the block: the quote appears
    # exactly once in the whole prompt.
    assert prompt.count(PASSAGE) == 1
    # What no movement carries stays in the block.
    assert "[ARGUMENTS QU'AUCUNE LENTILLE" in prompt
    assert UNANCHORED in prompt
    # And the consigne carries the binding rule.
    assert "battement de clôture" in prompt


def test_a_finding_no_argument_carries_stays_in_the_block_only():
    """An orphan does not leak onto any movement's line."""
    orphan = coverage_item(quote=UNANCHORED, offset=UNANCHORED_OFFSET, unit_id="")
    state = make_state(record(orphan))

    prompt = build_act2_prompt(build_act2_evidence(state))

    # The CHANNEL line is absent (the consigne may name the channel by its
    # label — only the channel line carries the colon and the passage).
    assert "Examen de couverture :" not in prompt
    assert UNANCHORED in prompt
    assert "battement de clôture" in prompt


# --- witness (b): an empty review leaves the prompt byte-identical ----------


def test_an_empty_review_leaves_the_prompt_byte_identical():
    """No channel line, no rule — the same prompt a bare state renders."""
    with_empty_review = make_state(record())
    without_record = make_state()

    prompt_empty = build_act2_prompt(build_act2_evidence(with_empty_review))
    prompt_bare = build_act2_prompt(build_act2_evidence(without_record))

    assert prompt_empty == prompt_bare
    assert "Examen de couverture" not in prompt_empty
    assert "battement de clôture" not in prompt_empty


# --- witness (c): the coverage walk's finding IS the movement ---------------


def test_the_only_detection_of_a_state_comes_from_the_coverage_walk():
    """No fallacy, no verdict — the walk's finding still has its movement."""
    bound = coverage_item(quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2")
    state = make_state(record(bound))

    prompt = build_act2_prompt(build_act2_evidence(state))

    # Every item is bound: the standalone block disappears (the consigne may
    # name the block — only the block itself carries the header's tail).
    assert (
        "revue de couverture, lecture du document entier, après les phases "
        "profondes]" not in prompt
    )
    # The movement names the finding — the quote, on the argument's own block.
    block_arg2 = movement_block_of(prompt, UNITS["arg_2"])
    assert PASSAGE in block_arg2
    assert "Examen de couverture" in block_arg2


# --- what a bound line says stays what it is --------------------------------


def test_a_consistency_verdict_stays_a_consistency_verdict():
    """Bound to a movement, the lens answer keeps its own vocabulary."""
    routed = {
        "lens": "fol",
        "status": "answered",
        "finding": {
            "status": "answered",
            "verdict": "consistent_with_run_kb",
            "formula": "p => q",
            "shared_symbols": 3,
        },
    }
    bound = coverage_item(
        quote=PASSAGE,
        offset=PASSAGE_OFFSET,
        kind="inferential",
        unit_id="arg_2",
        routed=routed,
    )
    state = make_state(record(bound))

    prompt = build_act2_prompt(build_act2_evidence(state))

    block_arg2 = movement_block_of(prompt, UNITS["arg_2"])
    assert "ne contredit pas la base formelle" in block_arg2
    assert "cohérence, pas implication" in block_arg2


def test_a_named_absence_stays_named_not_examined():
    """An unwired lens on a bound line is still an absence, never a verdict."""
    bound = coverage_item(
        quote=PASSAGE, offset=PASSAGE_OFFSET, kind="modal", unit_id="arg_2"
    )
    state = make_state(record(bound))

    prompt = build_act2_prompt(build_act2_evidence(state))

    block_arg2 = movement_block_of(prompt, UNITS["arg_2"])
    assert "nommé, non examiné" in block_arg2
    assert "ne lui prête pas de verdict" in block_arg2
