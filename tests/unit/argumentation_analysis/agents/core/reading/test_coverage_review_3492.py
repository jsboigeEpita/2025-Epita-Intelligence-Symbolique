"""#3492 reprise — the coverage reviewer enumerates, then code filters.

The coordinator's replay of the recorded c4b states measured **0 of 3 anchors**
reaching the reviewer's prompt, then why: the coverage map made every belief
verb eligible, and a reviewer asked for the thesis's SUPPORTS does not look for
what the zero-shot finds — an ARGUMENT WITH ITS OWN CONCLUSION. Two more
measures settled the design: on long documents the per-class filter cuts almost
nothing (1 of 44), and the three anchors rank 11, 3 and 8 of 15.

These witnesses pin the rework:

* the reviewer is asked the zero-shot's own question — the arguments a complete
  analysis would examine one by one — over the WHOLE document, including a
  passage no extraction produced, and the coverage map is GONE from the prompt;
* the budget is 15 (the rank ceiling of the measured map), and the three
  measured anchors survive at their own ranks;
* "examined" is decided PER CLASS in code: a stakes record does not examine a
  statistical support, and a modal question has no coverage key at all;
* a fourth class (``persuasion``) has a home — the descent — because one
  measured anchor was a manipulation move and fitted none of the three;
* a quote is verified against ``raw_text``, so a paraphrase of the extractor's
  is dropped and counted rather than printed as the speaker's words;
* the acts print the reviewer's own reading, attributed, ONE line per item, and
  the fallacies the class's lens retained under the writer's generic label
  (#3493).

The document and its passages are made up: no corpus text, no source name. The
taxonomy leaf used for the label witness is the repository's own vendored data.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.reading.coverage_review import (
    COVERAGE_KEYS_BY_CLASS,
    DROP_CAPPED,
    DROP_EXAMINED_BY_CLASS,
    DROP_QUOTE_NOT_IN_DOCUMENT,
    DROP_UNKNOWN_CLASS,
    LENS_BY_CLASS,
    MAX_ITEMS,
    build_coverage_review,
    coverage_review_note,
    examined_unit_ids,
    examined_unit_ids_for_class,
    unit_id_at_offset,
)

# --- a synthetic document, long enough for "whole document" to mean something

OPENING = "Le texte ouvre sur une thèse simple."
FILLER = " ".join(
    f"Phrase de liaison numéro {index} sur le contexte du débat."
    for index in range(1, 121)
)
ANCHOR = "Ce chiffre, trois taux sur quatre, n'apparaît dans aucune lecture profonde."
INFER = "Si la mesure tient, alors la conclusion suit nécessairement."
UNEXTRACTED = "Un passage que l'extraction n'a jamais isolé en unité."
CLOSING = "Le document se referme sur une question ouverte."
DOCUMENT = f"{OPENING} {FILLER} {ANCHOR} {INFER} {UNEXTRACTED} {CLOSING}"

THESIS = OPENING
THESIS_OFFSET = 0
FILLER_OFFSET = DOCUMENT.index(FILLER[:40])
ANCHOR_OFFSET = DOCUMENT.index(ANCHOR)
INFER_OFFSET = DOCUMENT.index(INFER)
UNEXTRACTED_OFFSET = DOCUMENT.index(UNEXTRACTED)

DEFAULT_UNITS = {
    "arg_1": FILLER[:40],
    "arg_2": ANCHOR,
    "arg_3": INFER,
}
DEFAULT_PROVENANCE = {
    "arg_1": {"producer": "llm_extract", "offset": FILLER_OFFSET},
    "arg_2": {"producer": "llm_extract", "offset": ANCHOR_OFFSET},
    "arg_3": {"producer": "llm_extract", "offset": INFER_OFFSET},
}

#: The M2 leaf of #3493: its name embeds an example in guillemets, and its
#: ``desc_fr`` is the generic procedure. Measured on the vendored CSV.
SLOGAN_LEAF = "Appel à « la France qui se lève tôt »"
SLOGAN_PATH = "2.2.1.2.2.1"
SLOGAN_INNER = "la France qui se lève tôt"
SLOGAN_GENERIC = (
    "Vous utilisez la valeur du travail pour légitimer une idée, en "
    "ciblant une classe sociale précise."
)


def make_state(
    *,
    coverage=None,
    units=None,
    provenance=None,
    thesis=True,
    raw_text=DOCUMENT,
    record=None,
):
    """A synthetic state: the document, its units, the coverage record."""
    if units is None:
        units = dict(DEFAULT_UNITS)
    if provenance is None:
        provenance = {
            key: dict(value)
            for key, value in DEFAULT_PROVENANCE.items()
            if key in units
        }
    if coverage is None:
        coverage = {}
    state = SimpleNamespace(
        raw_text=raw_text,
        identified_arguments=dict(units),
        argument_provenance=provenance,
        analysis_coverage=coverage,
        defining_moves={
            "moves": (
                [{"slot": "thesis", "quote": THESIS, "offset": THESIS_OFFSET}]
                if thesis
                else []
            ),
            "status": "ok",
            "basis": "first_reading",
        },
        # Act II's own inputs, so the render witness reads the real prompt.
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
    )
    if record is not None:
        state.coverage_review = record
    return state


def reply(*items):
    """A model reply naming (quote, class[, reason[, conclusion]]) tuples."""
    payload = []
    for item in items:
        quote, kind = item[0], item[1]
        reason = item[2] if len(item) > 2 else "raison synthétique"
        entry = {"quote": quote, "class": kind, "reason": reason}
        if len(item) > 3:
            entry["conclusion"] = item[3]
        payload.append(entry)
    return json.dumps({"items": payload})


class FakeLLM:
    """Records the prompt and returns a fixed reply — never a network call."""

    def __init__(self, content: str):
        self.content = content
        self.prompts = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.content


class FakeDispatcher:
    """Records the items it is handed and answers each with its lens name."""

    def __init__(self, status: str = "answered", fallacies=None):
        self.calls = []
        self.status = status
        self.fallacies = list(fallacies or [])

    async def __call__(self, item):
        self.calls.append((item.unit_id, item.lens, item.quote))
        if self.status == "answered":
            return {"status": "answered", "fallacies": list(self.fallacies)}
        return {"status": self.status, "reason": "synthetic"}


# --- ask 1: the pass reads the document, not a sample ----------------------


async def test_the_reviewer_reads_the_whole_document():
    """The zero-shot found these passages BY READING — so does the reviewer.

    ``UNEXTRACTED`` belongs to no extracted unit: v1's candidate prompt could
    never carry it, whatever the sample size.
    """
    state = make_state()
    llm = FakeLLM(reply((UNEXTRACTED, "modal")))

    review = await build_coverage_review(state, llm, FakeDispatcher())

    prompt = llm.prompts[0]
    assert len(DOCUMENT) > 4_000  # a sample-of-candidates prompt would shrink
    assert OPENING in prompt and CLOSING in prompt
    assert ANCHOR in prompt and UNEXTRACTED in prompt
    assert review.status == "ok"
    assert [item.quote for item in review.items] == [UNEXTRACTED]
    # Its offset is the DOCUMENT's, not a unit's local one.
    assert review.items[0].offset == UNEXTRACTED_OFFSET
    assert review.document_chars == len(DOCUMENT)


async def test_a_passage_no_unit_carries_is_named_without_borrowing_an_id():
    """The reading's rule: no span, no id — never a neighbour's."""
    state = make_state()
    review = await build_coverage_review(
        state, FakeLLM(reply((UNEXTRACTED, "modal"))), FakeDispatcher()
    )
    assert review.items[0].unit_id == ""


async def test_the_prompt_asks_for_an_enumeration_and_carries_no_coverage_map():
    """R1155 — the map made every belief verb eligible and named no anchor."""
    state = make_state(
        coverage={
            "fallacy_per_argument": {"unit_ids": ["arg_2"]},
            "stakes": {"unit_ids": ["arg_3"]},
        }
    )
    llm = FakeLLM(reply((UNEXTRACTED, "modal")))

    await build_coverage_review(state, llm, FakeDispatcher())

    prompt = llm.prompts[0]
    # The reader's own question: arguments, each with its own conclusion.
    assert "conclusion" in prompt
    assert "PAR" in prompt and "LUI-MÊME" in prompt
    # The four classes, and the budget, are stated to the model.
    for kind in ("modal", "statistical", "inferential", "persuasion"):
        assert f'"{kind}"' in prompt
    assert f"Au plus {MAX_ITEMS} arguments" in prompt
    # The coverage map is GONE: no per-class record, no unit id, no offset.
    assert "question «" not in prompt
    assert "aucune couverture enregistrée" not in prompt
    assert f"arg_2 (position {ANCHOR_OFFSET})" not in prompt
    assert "arg_3 (position" not in prompt


# --- ask 2: examined is decided per class, never as the union --------------


def test_the_class_table_says_what_each_question_counts():
    assert COVERAGE_KEYS_BY_CLASS["modal"] == ()
    assert COVERAGE_KEYS_BY_CLASS["statistical"] == ("fallacy_per_argument",)
    assert "fol_reasoning" in COVERAGE_KEYS_BY_CLASS["inferential"]
    assert "aspic" in COVERAGE_KEYS_BY_CLASS["inferential"]
    # R1155 — the fourth class shares the descent's record: that is the lens
    # that reads a passage for manipulative moves today.
    assert COVERAGE_KEYS_BY_CLASS["persuasion"] == ("fallacy_per_argument",)


def test_the_four_classes_are_the_closed_vocabulary_and_each_has_a_lens():
    expected = {"modal", "statistical", "inferential", "persuasion"}
    assert set(COVERAGE_KEYS_BY_CLASS) == expected
    assert set(LENS_BY_CLASS) == expected


def test_the_per_class_set_ignores_every_other_phase():
    state = make_state(
        coverage={
            "fallacy_per_argument": {"unit_ids": ["arg_2"]},
            "stakes": {"unit_ids": ["arg_3"]},
            "fol_reasoning": {"unit_ids": ["arg_1"]},
            "anchor_census": {"k": 0, "N": 3, "unanchored_ids": ["arg_1"]},
        }
    )
    assert examined_unit_ids_for_class(state, "statistical") == {"arg_2"}
    assert examined_unit_ids_for_class(state, "inferential") == {"arg_1"}
    # No key ⇒ nothing examined — not the union of what other phases read.
    assert examined_unit_ids_for_class(state, "modal") == set()
    # The union is still reported, as information.
    assert examined_unit_ids(state)[0] == {"arg_1", "arg_2", "arg_3"}


async def test_a_passage_its_own_lens_read_is_dropped_and_counted():
    state = make_state(coverage={"fallacy_per_argument": {"unit_ids": ["arg_2"]}})
    review = await build_coverage_review(
        state, FakeLLM(reply((ANCHOR, "statistical"))), FakeDispatcher()
    )
    assert review.items == []
    assert review.dropped.get(DROP_EXAMINED_BY_CLASS) == 1


async def test_the_same_passage_stays_nameable_for_another_question():
    """`arg_2` was read by the statistical lens; the MODAL question is unread."""
    state = make_state(coverage={"fallacy_per_argument": {"unit_ids": ["arg_2"]}})
    review = await build_coverage_review(
        state, FakeLLM(reply((ANCHOR, "modal"))), FakeDispatcher()
    )
    assert len(review.items) == 1
    assert review.items[0].lens == "modal"


async def test_a_stakes_record_does_not_examine_a_statistical_support():
    """#3492's own measurement: 8 phases, and none asked the question."""
    state = make_state(coverage={"stakes": {"unit_ids": ["arg_2"]}})
    review = await build_coverage_review(
        state, FakeLLM(reply((ANCHOR, "statistical"))), FakeDispatcher()
    )
    assert len(review.items) == 1


@pytest.mark.parametrize("key", ["fol_reasoning", "aspic"])
async def test_both_inferential_records_count(key):
    state = make_state(coverage={key: {"unit_ids": ["arg_3"]}})
    review = await build_coverage_review(
        state, FakeLLM(reply((INFER, "inferential"))), FakeDispatcher()
    )
    assert review.items == []
    assert review.dropped.get(DROP_EXAMINED_BY_CLASS) == 1


# --- ask 3: quotes are verified against the document ----------------------


async def test_a_paraphrase_of_the_extractor_is_dropped_not_printed():
    """336 of 1 406 unit texts are verbatim; the rest are paraphrases."""
    paraphrase = "Une reformulation de l'extracteur, absente du document."
    state = make_state(
        units={"arg_9": paraphrase},
        provenance={"arg_9": {"producer": "llm_extract", "offset": ANCHOR_OFFSET}},
    )
    review = await build_coverage_review(
        state, FakeLLM(reply((paraphrase, "statistical"))), FakeDispatcher()
    )
    assert review.items == []
    assert review.dropped.get(DROP_QUOTE_NOT_IN_DOCUMENT) == 1


async def test_a_document_quote_is_placed_at_its_document_offset():
    """A paraphrase unit still routes: the DOCUMENT position maps it."""
    paraphrase = (
        "Une reformulation de l'extracteur, absente du document, mais assez "
        "longue pour couvrir la citation que la revue nomme."
    )
    state = make_state(
        units={"arg_9": paraphrase},
        provenance={"arg_9": {"producer": "llm_extract", "offset": ANCHOR_OFFSET}},
    )
    review = await build_coverage_review(
        state, FakeLLM(reply((ANCHOR, "statistical"))), FakeDispatcher()
    )
    assert len(review.items) == 1
    assert review.items[0].quote == ANCHOR
    assert review.items[0].offset == ANCHOR_OFFSET
    # The span carries it, so the route gets an id — the reading's overlap rule.
    assert review.items[0].unit_id == "arg_9"


def test_unit_id_at_offset_follows_the_reading_overlap_rule():
    rows = [
        {"unit_id": "arg_1", "text": "x" * 10, "offset": 0},
        {"unit_id": "arg_2", "text": "y" * 10, "offset": 100},
    ]
    assert unit_id_at_offset(rows, 5) == "arg_1"
    assert unit_id_at_offset(rows, 100) == "arg_2"
    assert unit_id_at_offset(rows, 109) == "arg_2"
    # Between spans, and before the first: no id rather than a neighbour's.
    assert unit_id_at_offset(rows, 50) == ""
    assert (
        unit_id_at_offset([{"unit_id": "arg_2", "text": "y" * 10, "offset": 100}], 5)
        == ""
    )


# --- the honesty rules around the naming ----------------------------------


async def test_the_named_items_are_capped_and_the_overflow_counted():
    state = make_state()
    sentences = [
        f"Passage numéro {index} du document." for index in range(1, MAX_ITEMS + 3)
    ]
    state.raw_text = DOCUMENT + " " + " ".join(sentences)
    review = await build_coverage_review(
        state,
        FakeLLM(reply(*[(text, "modal") for text in sentences])),
        FakeDispatcher(),
    )
    assert len(review.items) == MAX_ITEMS
    assert review.dropped.get(DROP_CAPPED) == 2


async def test_the_budget_carries_the_three_anchors_at_ranks_3_8_and_11():
    """R1155 — measured at ranks 11, 3 and 8 of 15: a cap of three kept one.

    The rank is the MODEL's own order, recorded as given: the budget was set
    from that measure, so the witness replays it rather than assuming it.
    """
    state = make_state()
    extra = [
        f"Passage secondaire numéro {index} du document." for index in range(1, 16)
    ]
    state.raw_text = DOCUMENT + " " + " ".join(extra)
    entries = list(extra)
    for rank, quote in {3: ANCHOR, 8: INFER, 11: UNEXTRACTED}.items():
        entries[rank - 1] = quote

    review = await build_coverage_review(
        state, FakeLLM(reply(*[(text, "modal") for text in entries])), FakeDispatcher()
    )

    by_rank = {item.rank: item.quote for item in review.items}
    assert by_rank[3] == ANCHOR
    assert by_rank[8] == INFER
    assert by_rank[11] == UNEXTRACTED
    assert len(review.items) == MAX_ITEMS
    assert not review.dropped.get(DROP_CAPPED)


async def test_a_persuasion_move_is_the_fourth_class_and_routes_to_the_descent():
    """R1155 — one measured anchor was a manipulation move with no home."""
    state = make_state()
    review = await build_coverage_review(
        state, FakeLLM(reply((UNEXTRACTED, "persuasion"))), FakeDispatcher()
    )
    assert len(review.items) == 1
    assert review.items[0].kind == "persuasion"
    assert review.items[0].lens == "fallacy_descent"


async def test_a_persuasion_passage_the_descent_read_is_dropped_and_counted():
    state = make_state(coverage={"fallacy_per_argument": {"unit_ids": ["arg_2"]}})
    review = await build_coverage_review(
        state, FakeLLM(reply((ANCHOR, "persuasion"))), FakeDispatcher()
    )
    assert review.items == []
    assert review.dropped.get(DROP_EXAMINED_BY_CLASS) == 1


async def test_an_unknown_class_is_dropped_never_routed_by_default():
    state = make_state()
    review = await build_coverage_review(
        state, FakeLLM(reply((UNEXTRACTED, "rhetorical"))), FakeDispatcher()
    )
    assert review.items == []
    assert review.dropped.get(DROP_UNKNOWN_CLASS) == 1


async def test_no_llm_is_an_honest_empty_never_a_fabricated_review():
    review = await build_coverage_review(make_state(), None, FakeDispatcher())
    assert review.status == "no_llm"
    assert review.items == []


async def test_without_a_thesis_the_pass_has_no_question():
    llm = FakeLLM(reply((UNEXTRACTED, "modal")))
    review = await build_coverage_review(
        make_state(thesis=False), llm, FakeDispatcher()
    )
    assert review.status == "no_reading"
    assert llm.prompts == []


async def test_without_a_document_the_quote_cannot_be_placed():
    """No document, no verification — and no review that pretends otherwise."""
    llm = FakeLLM(reply((UNEXTRACTED, "modal")))
    review = await build_coverage_review(make_state(raw_text=""), llm, FakeDispatcher())
    assert review.status == "no_document"
    assert review.items == []
    assert llm.prompts == []


async def test_an_empty_review_leaves_the_acts_prompt_byte_identical():
    state = make_state()
    review = await build_coverage_review(state, FakeLLM(reply()), FakeDispatcher())
    assert review.status == "ok"
    assert review.items == []
    state.coverage_review = review.to_state()
    assert coverage_review_note(state) == ""


def test_a_bare_state_renders_no_block():
    assert coverage_review_note(SimpleNamespace()) == ""
    assert coverage_review_note({"coverage_review": {"status": "no_llm"}}) == ""


# --- ask 4: what the review read reaches the act --------------------------


async def test_the_acts_print_the_retained_fallacy_under_the_generic_label():
    """The witness asserts CONTENT: a fallacy name and a reason, not a status."""
    from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
        build_act2_evidence,
        build_act2_prompt,
    )

    reading = "Ce passage chiffre l'appui sans jamais le qualifier."
    state = make_state()
    dispatcher = FakeDispatcher(
        fallacies=[
            {
                "fallacy_type": SLOGAN_LEAF,
                "taxonomy_path": SLOGAN_PATH,
                "family": "Influence",
            }
        ]
    )
    review = await build_coverage_review(
        state, FakeLLM(reply((ANCHOR, "statistical", reading))), dispatcher
    )
    state.coverage_review = review.to_state()

    prompt = build_act2_prompt(build_act2_evidence(state))

    assert SLOGAN_GENERIC in prompt
    assert SLOGAN_INNER not in prompt
    assert reading in prompt
    assert "pas une lentille" in prompt


async def test_an_unwired_lens_still_carries_the_reviewers_reading():
    """A named gap keeps its line AND its reason — the reading is not a verdict."""
    reading = "Ce passage oppose une croyance à un savoir."
    state = make_state()
    note_source = await build_coverage_review(
        state,
        FakeLLM(reply((ANCHOR, "modal", reading))),
        FakeDispatcher(status="lens_not_wired"),
    )
    state.coverage_review = note_source.to_state()

    note = coverage_review_note(state)

    assert reading in note
    assert "pas une lentille" in note
    assert "câblée" in note
    assert "verdict" in note


async def test_the_note_renders_one_line_per_item_with_its_rank_and_conclusion():
    """R1155 — the Act II prompt grows by the items named, not per item."""
    state = make_state()
    review = await build_coverage_review(
        state,
        FakeLLM(
            reply(
                (ANCHOR, "statistical", "la raison A", "l'argument conclut B"),
                (UNEXTRACTED, "modal", "la raison C", "l'argument conclut D"),
            )
        ),
        FakeDispatcher(status="lens_not_wired"),
    )
    state.coverage_review = review.to_state()

    note = coverage_review_note(state)
    lines = [line for line in note.splitlines() if line.strip()]

    assert len(lines) == 1 + 2  # one header, then exactly one line per item
    assert "rang 1" in lines[1] and "rang 2" in lines[2]
    assert "conclut : l'argument conclut B" in lines[1]
    assert "la raison A" in lines[1]
    assert "position" in lines[1] and "classe statistical" in lines[1]


# --- ask 5 + the invoke layer: the walk reads the passage IN its frame ----


def _patch_invoke(monkeypatch, llm, walk):
    """Persona call returns the fake LLM; the fallacy walk is recorded."""
    import argumentation_analysis.core.llm_service as llm_service_module
    import argumentation_analysis.orchestration.invoke_callables as ic

    monkeypatch.setattr(ic, "_build_persona_callable", lambda persona: (llm, ""))
    monkeypatch.setattr(ic, "_walk_single_fallacy_unit", walk)
    monkeypatch.setattr(
        llm_service_module, "create_llm_service", lambda **kwargs: object()
    )
    return ic


async def test_the_invoke_walks_a_statistical_item_with_its_document_frame(
    monkeypatch,
):
    """The walk gets the #3428 frame around the passage, not the bare quote."""
    walked = []

    async def walk(quote, unit_id, service, taxonomy_path, document_frame=None):
        walked.append((unit_id, quote, document_frame))
        return {"fallacies": [{"fallacy_type": "synthetic", "family": "synthetic"}]}

    ic = _patch_invoke(monkeypatch, FakeLLM(reply((ANCHOR, "statistical"))), walk)
    state = make_state()

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    assert out["status"] == "ok"
    assert out["items"][0]["unit_id"] == "arg_2"
    assert out["items"][0]["routed"]["status"] == "answered"
    assert out["items"][0]["routed"]["finding"]["fallacies"] == [
        {"fallacy_type": "synthetic", "family": "synthetic"}
    ]
    assert len(walked) == 1
    unit_id, quote, frame = walked[0]
    assert unit_id == "arg_2"
    assert quote == ANCHOR
    # The frame is the document's own text around the passage.
    assert isinstance(frame, dict) and frame
    assert "before" in frame or "after" in frame


async def test_the_invoke_names_a_modal_item_without_inventing_a_lens(monkeypatch):
    """The modal arm reads the run's population — its item stays a named gap."""
    walked = []

    async def walk(*args, **kwargs):  # pragma: no cover - must not run
        walked.append(args)

    ic = _patch_invoke(monkeypatch, FakeLLM(reply((ANCHOR, "modal"))), walk)
    state = make_state()

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    assert out["status"] == "ok"
    assert out["items"][0]["routed"]["status"] == "lens_not_wired"
    assert walked == []


async def test_the_invoke_without_a_state_is_unreachable_not_fabricated(monkeypatch):
    async def walk(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("no walk may run without a state")

    ic = _patch_invoke(monkeypatch, FakeLLM(""), walk)
    out = await ic._invoke_coverage_review(DOCUMENT, {})
    assert out["status"] == "unreachable"
    assert out["reason"] == "no_shared_state"


async def test_the_writer_persists_the_review_as_computed(monkeypatch):
    """The writer keeps the payload as computed — it is not a second producer."""
    from argumentation_analysis.orchestration.state_writers import (
        CAPABILITY_STATE_WRITERS,
        _write_coverage_review_to_state,
    )

    async def walk(*args, **kwargs):
        return {"fallacies": []}

    ic = _patch_invoke(monkeypatch, FakeLLM(reply((ANCHOR, "statistical"))), walk)
    state = make_state(record={})

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})
    _write_coverage_review_to_state(out, state, {})

    assert state.coverage_review["status"] == "ok"
    assert state.coverage_review["basis"] == "coverage_review"
    assert state.coverage_review["items"][0]["offset"] == ANCHOR_OFFSET
    assert (
        CAPABILITY_STATE_WRITERS["coverage_review"] is _write_coverage_review_to_state
    )
