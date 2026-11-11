"""#3505 part 2 — a fallacy the coverage walk retained reaches the channel the writer names.

The coordinator's measure (R1160, on part 1): 0 of 21 coverage-only labels are
named, while about 40 % of the deep labels are. The cause is the channel, not
the content — the review's labels ride at the tail of the long « Examen de
couverture » sentence; the deep detections reach the prose through their own
« Procédé : » lines (label, detector confidence, justification), the channel the
writer already names. Part 2 gives each retained fallacy its OWN procédé line on
its argument — same label producer (``fallacy_taxonomy_label``), same standing
rule (``detector_confidence_note``), its explanation, and the attribution inside
the line — and takes the labels out of the « Examen de couverture » line: one
home per label. No consigne sentence is added (anti-pendulum: the binding is
structural or it does not hold).

Witnesses, per the issue:

* (a) an argument with a deep detection of family A and a coverage-retained
  fallacy of family B carries ONE « Procédé : » line for A, unchanged, and ONE
  attributed procédé line for B beside it;
* (b) an item with no retained fallacy adds no procédé line;
* (c) an empty review leaves the prompt byte-identical (the #3492 control,
  kept);
* the « Examen de couverture » line keeps passage, reason and lens status, and
  stops carrying the labels;
* an orphan keeps its labels in the block — the only home a label has when no
  movement carries its passage.

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
PASSAGE = "Ce retournement du chiffre vise l'émotion, jamais la mesure."
UNANCHORED = "Un passage qu'aucune unité extraite ne porte dans son span."
CLOSING = "Le document se referme sur une question ouverte."
DOCUMENT = f"{OPENING} {FILLER} {PASSAGE} {UNANCHORED} {CLOSING}"

PASSAGE_OFFSET = DOCUMENT.index(PASSAGE)
UNANCHORED_OFFSET = DOCUMENT.index(UNANCHORED)

UNITS = {
    "arg_1": "Une unité qui reformule la thèse en ses propres mots.",
    "arg_2": "Une unité qui reformule l'appui retourné en ses propres mots.",
}
PROVENANCE = {
    "arg_1": {"producer": "llm_extract", "offset": DOCUMENT.index(OPENING)},
    "arg_2": {"producer": "llm_extract", "offset": PASSAGE_OFFSET},
}

FALLACY_SAMPLE = {"fallacy_per_argument": {"unit_ids": ["arg_1", "arg_2"]}}

#: A deep detection of family A on arg_2 — the shape the state writer persists.
DEEP_TYPE = "Attaque indirecte"
DEEP_FAMILY = "Pertinence"
DEEP_FALLACIES = {
    "fall_1": {
        "target_argument_id": "arg_2",
        "type": DEEP_TYPE,
        "family": DEEP_FAMILY,
        "justification": "la phase profonde fonde sa lecture sur ce détour",
        "confidence": 0.8,
    }
}

#: A fallacy the coverage walk retained on the same argument — family B, the
#: ``IdentifiedFallacy`` dict the descent returns under ``finding.fallacies``.
WALK_TYPE = "Appel à la peur"
WALK_FAMILY = "Émotionnel"
WALK_EXPLANATION = "la marche retient ce que le chiffre doit à l'inquiétude"


def walk_fallacy() -> dict:
    return {
        "fallacy_type": WALK_TYPE,
        "family": WALK_FAMILY,
        "taxonomy_path": "",
        "confidence": 0.6,
        "explanation": WALK_EXPLANATION,
        "move_author": "speaker",
        "problematic_quote": PASSAGE[:60],
    }


def coverage_item(
    *,
    quote: str,
    offset: int,
    kind: str = "persuasion",
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
        or {
            "lens": lens,
            "status": "answered",
            "finding": {"status": "answered", "fallacies": [walk_fallacy()]},
        },
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


def make_state(
    coverage_review: dict | None = None,
    identified_fallacies: dict | None = None,
) -> SimpleNamespace:
    state = SimpleNamespace(
        raw_text=DOCUMENT,
        identified_arguments=dict(UNITS),
        argument_provenance={k: dict(v) for k, v in PROVENANCE.items()},
        analysis_coverage={k: dict(v) for k, v in FALLACY_SAMPLE.items()},
        identified_fallacies=dict(identified_fallacies or {}),
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
    appears in exactly one movement block.
    """
    for block in prompt.split("\n\n"):
        if unit_text in block:
            return block
    return ""


#: The attribution the issue asks the line to carry, verbatim.
ATTRIBUTION = (
    "Procédé relevé par la revue de couverture (lecture du document entier "
    "après les phases profondes), pas par les phases profondes : "
)


# --- witness (a): the review's fallacy reaches the procédé channel ----------


def test_a_walk_fallacy_gets_its_own_attributed_procede_line():
    """Deep A keeps its line; the review's B gets one beside it, attributed."""
    bound = coverage_item(quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2")
    state = make_state(record(bound), identified_fallacies=DEEP_FALLACIES)

    prompt = build_act2_prompt(build_act2_evidence(state))
    block = movement_block_of(prompt, UNITS["arg_2"])

    # The deep detection's line is untouched — same channel, same format.
    assert block.count("Procédé : ") == 1
    assert f"Procédé : « {DEEP_TYPE} »" in block
    # The review's fallacy: its OWN line, the attribution inside it, the label
    # the writer names for deep detections, the standing rule, the explanation.
    assert block.count(ATTRIBUTION) == 1
    assert f"{ATTRIBUTION}« {WALK_TYPE} » (famille {WALK_FAMILY})" in block
    assert "confiance du détecteur" in block
    assert WALK_EXPLANATION in block


def test_the_examen_line_keeps_reason_and_lens_status_drops_labels():
    """The binding sentence keeps what it is; the labels have one home."""
    bound = coverage_item(quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2")
    state = make_state(record(bound), identified_fallacies=DEEP_FALLACIES)

    prompt = build_act2_prompt(build_act2_evidence(state))

    examen = [
        line
        for line in prompt.splitlines()
        if line.startswith("      Examen de couverture : ")
    ]
    assert len(examen) == 1
    # Keeps: the passage, the reviewer's reason, the lens status.
    assert PASSAGE in examen[0]
    assert "le retient parce que" in examen[0]
    assert "sophisme(s) retenu(s)" in examen[0]
    # Drops: the labels' list clause, and the label itself.
    assert "sophismes retenus :" not in examen[0]
    assert WALK_TYPE not in examen[0]
    # One home per label: the label appears exactly once in the whole prompt —
    # on its procédé line.
    assert prompt.count(f"« {WALK_TYPE} »") == 1


# --- witness (b): no retained fallacy, no procédé line ----------------------


def test_an_item_without_retained_fallacies_adds_no_procede_line():
    """The channel carries findings, not passages: nothing retained, no line."""
    routed = {
        "lens": "fallacy_descent",
        "status": "answered",
        "finding": {"status": "answered", "fallacies": []},
    }
    bound = coverage_item(
        quote=PASSAGE, offset=PASSAGE_OFFSET, unit_id="arg_2", routed=routed
    )
    state = make_state(record(bound))

    prompt = build_act2_prompt(build_act2_evidence(state))
    block = movement_block_of(prompt, UNITS["arg_2"])

    assert "Examen de couverture : " in block
    assert ATTRIBUTION not in prompt
    assert "aucun sophisme retenu" in block


# --- witness (c): an empty review stays byte-identical ----------------------


def test_an_empty_review_leaves_the_prompt_byte_identical():
    """The #3492 control, kept: nothing named, nothing added anywhere."""
    with_empty_review = make_state(record())
    without_record = make_state()

    prompt_empty = build_act2_prompt(build_act2_evidence(with_empty_review))
    prompt_bare = build_act2_prompt(build_act2_evidence(without_record))

    assert prompt_empty == prompt_bare
    assert ATTRIBUTION not in prompt_empty


# --- an orphan's labels keep their only home --------------------------------


def test_an_orphan_keeps_its_labels_in_the_block():
    """No movement carries the passage: the block line is the labels' home."""
    routed = {
        "lens": "fallacy_descent",
        "status": "answered",
        "finding": {"status": "answered", "fallacies": [walk_fallacy()]},
    }
    orphan = coverage_item(
        quote=UNANCHORED, offset=UNANCHORED_OFFSET, unit_id="", rank=2, routed=routed
    )
    state = make_state(record(orphan))

    prompt = build_act2_prompt(build_act2_evidence(state))

    # The block line still carries the labels — their one and only home.
    assert "sophismes retenus :" in prompt
    assert f"« {WALK_TYPE} »" in prompt
    # And no procédé line was invented for a passage no argument carries.
    assert ATTRIBUTION not in prompt
    assert "Examen de couverture : " not in prompt
