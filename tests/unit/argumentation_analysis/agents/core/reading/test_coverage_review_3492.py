"""#3492 — the coverage reviewer: what no lens read, pointed at the right one.

Three witnesses the issue asks for, plus the honesty rules around them:

* an unexamined support is named and routed to the lens of its class;
* a document whose supports were all examined leaves the acts' prompt
  byte-identical (``no_candidates``, empty note);
* the routed lens's answer reaches the ACTS' INPUT (``Act2Evidence``).

Every state here is synthetic: offsets are characters of a made-up document,
and the quotes are made-up too — no corpus text, no source name.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.reading.coverage_review import (
    DROP_CAPPED,
    DROP_UNKNOWN_CLASS,
    DROP_UNKNOWN_UNIT,
    DROP_UNPOSITIONED,
    DROP_QUOTE_NOT_VERBATIM,
    MAX_ITEMS,
    build_coverage_review,
    coverage_review_note,
    examined_unit_ids,
    unexamined_candidates,
)

DOCUMENT = (
    "Le texte ouvre sur une thèse simple. "
    "Un appui chiffré la soutient : trois taux sur quatre baissent. "
    "Une réserve épistémique suit, plus loin dans le document."
)

THESIS = "Le texte ouvre sur une thèse simple."
THESIS_OFFSET = 0
STAT_QUOTE = "trois taux sur quatre baissent"
STAT_OFFSET = DOCUMENT.index(STAT_QUOTE)
HEDGE_QUOTE = "Une réserve épistémique suit"
HEDGE_OFFSET = DOCUMENT.index(HEDGE_QUOTE)


def make_state(
    *,
    examined=(),
    coverage=None,
    units=None,
    thesis=True,
    record=None,
):
    """A synthetic state: extracted units, their provenance, the coverage record."""
    if units is None:
        units = {
            "arg_1": "Un appui chiffré la soutient.",
            "arg_2": "Une réserve épistémique suit, plus loin dans le document.",
        }
    provenance = {}
    for index, unit_id in enumerate(sorted(units)):
        provenance[unit_id] = {
            "producer": "llm_extract",
            "offset": STAT_OFFSET if index == 0 else HEDGE_OFFSET,
        }
    if coverage is None:
        coverage = {
            "fallacy_per_argument": {"k": 1, "N": 2, "unit_ids": list(examined)}
        }
    state = SimpleNamespace(
        raw_text=DOCUMENT,
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
    )
    if record is not None:
        state.coverage_review = record
    return state


def reply(*items):
    """A model reply naming the given (unit_id, quote, class) triples."""
    import json

    return json.dumps(
        {
            "items": [
                {"unit_id": u, "quote": q, "class": c, "reason": "synthetic"}
                for u, q, c in items
            ]
        }
    )


class FakeLLM:
    """Counts calls and returns a fixed reply — never a network call."""

    def __init__(self, content: str):
        self.content = content
        self.prompts = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.content


class FakeDispatcher:
    """Records the passages it is handed and answers each with its lens name."""

    def __init__(self, status: str = "answered"):
        self.calls = []
        self.status = status

    async def __call__(self, item):
        self.calls.append((item.unit_id, item.lens, item.quote))
        return {"status": self.status, "lens": item.lens}


# --- the examined set is derived from the record, never a phase allowlist ---


def test_examined_set_is_the_union_of_every_recorded_selection():
    state = make_state(
        coverage={
            "fallacy_per_argument": {"unit_ids": ["arg_1"]},
            "fol_reasoning_units": {"unit_ids": ["arg_2", "arg_1"]},
            "anchor_census": {"k": 0, "N": 2, "unanchored_ids": ["arg_1"]},
        }
    )
    examined, total = examined_unit_ids(state)
    assert examined == {"arg_1", "arg_2"}
    assert total == 2
    # anchor_census carries no unit_ids: it counts provenance, not a reading.
    assert unexamined_candidates(state, examined) == []


def test_a_phase_without_unit_ids_contributes_nothing():
    state = make_state(coverage={"some_phase": {"k": 3, "N": 9}})
    examined, total = examined_unit_ids(state)
    assert examined == set()
    assert total == 0
    assert len(unexamined_candidates(state, examined)) == 2


# --- witness 1: an unexamined support is named and routed by class ----------


async def test_unexamined_support_is_named_and_routed_to_its_lens():
    state = make_state(examined=["arg_1"])
    llm = FakeLLM(reply(("arg_2", HEDGE_QUOTE, "statistical")))
    dispatcher = FakeDispatcher()

    review = await build_coverage_review(state, llm, dispatcher)

    assert review.status == "ok"
    assert len(review.items) == 1
    item = review.items[0]
    assert item.unit_id == "arg_2"
    assert item.quote == HEDGE_QUOTE
    # The offset is a DOCUMENT offset: the candidate's own position plus the
    # quote's place inside it.
    assert item.offset == HEDGE_OFFSET
    assert item.kind == "statistical"
    assert item.lens == "fallacy_descent"
    assert dispatcher.calls == [("arg_2", "fallacy_descent", HEDGE_QUOTE)]
    assert review.items[0].routed["status"] == "answered"


async def test_each_class_points_at_its_own_lens():
    for kind, lens in (
        ("modal", "modal"),
        ("statistical", "fallacy_descent"),
        ("inferential", "fol"),
    ):
        state = make_state(examined=["arg_1"])
        llm = FakeLLM(reply(("arg_2", HEDGE_QUOTE, kind)))
        dispatcher = FakeDispatcher()
        review = await build_coverage_review(state, llm, dispatcher)
        assert len(review.items) == 1
        assert review.items[0].lens == lens
        assert dispatcher.calls[0][1] == lens


async def test_an_examined_unit_can_never_be_named():
    """The reviewer names what no lens read — a named examined unit is dropped."""
    state = make_state(examined=["arg_1", "arg_2"])
    llm = FakeLLM(reply(("arg_1", STAT_QUOTE, "statistical")))
    review = await build_coverage_review(state, llm, FakeDispatcher())
    # Every support was examined: the pass does not even call the model.
    assert review.status == "no_candidates"
    assert llm.prompts == []


async def test_a_named_unit_outside_the_candidates_is_dropped_and_counted():
    state = make_state(examined=["arg_1"])
    llm = FakeLLM(reply(("arg_9", "peu importe", "statistical")))
    review = await build_coverage_review(state, llm, FakeDispatcher())
    assert review.items == []
    assert review.dropped.get(DROP_UNKNOWN_UNIT) == 1


async def test_a_quote_the_passage_does_not_carry_is_dropped():
    state = make_state(examined=["arg_1"])
    llm = FakeLLM(reply(("arg_2", "une phrase que le candidat ne porte pas", "modal")))
    review = await build_coverage_review(state, llm, FakeDispatcher())
    assert review.items == []
    assert review.dropped.get(DROP_QUOTE_NOT_VERBATIM) == 1


async def test_an_unknown_class_is_dropped_never_routed_by_default():
    state = make_state(examined=["arg_1"])
    llm = FakeLLM(reply(("arg_2", HEDGE_QUOTE, "rhetorical")))
    review = await build_coverage_review(state, llm, FakeDispatcher())
    assert review.items == []
    assert review.dropped.get(DROP_UNKNOWN_CLASS) == 1


async def test_a_passage_with_no_position_is_not_reported_as_locatable():
    state = make_state(examined=["arg_1"])
    state.argument_provenance["arg_2"] = {"producer": "llm_extract", "offset": None}
    llm = FakeLLM(reply(("arg_2", HEDGE_QUOTE, "modal")))
    review = await build_coverage_review(state, llm, FakeDispatcher())
    assert review.items == []
    assert review.dropped.get(DROP_UNPOSITIONED) == 1


async def test_the_named_items_are_capped():
    units = {"arg_1": "examiné"}
    for index in range(2, 7):
        units[f"arg_{index}"] = f"passage numéro {index}"
    state = make_state(units=units, examined=["arg_1"])
    for index in range(2, 7):
        state.argument_provenance[f"arg_{index}"] = {
            "producer": "llm_extract",
            "offset": index * 10,
        }
    llm = FakeLLM(
        reply(*[(f"arg_{i}", f"passage numéro {i}", "modal") for i in range(2, 7)])
    )
    review = await build_coverage_review(state, llm, FakeDispatcher())
    assert len(review.items) == MAX_ITEMS
    assert review.dropped.get(DROP_CAPPED) == 2


async def test_no_llm_is_an_honest_empty_never_a_fabricated_review():
    state = make_state(examined=["arg_1"])
    review = await build_coverage_review(state, None, FakeDispatcher())
    assert review.status == "no_llm"
    assert review.items == []


async def test_without_a_thesis_the_pass_has_no_question():
    state = make_state(examined=["arg_1"], thesis=False)
    llm = FakeLLM(reply(("arg_2", HEDGE_QUOTE, "modal")))
    review = await build_coverage_review(state, llm, FakeDispatcher())
    assert review.status == "no_reading"
    assert llm.prompts == []


# --- witness 2: every support examined -> the acts' prompt is unchanged -----


async def test_all_examined_leaves_the_acts_prompt_byte_identical():
    state = make_state(examined=["arg_1", "arg_2"])
    llm = FakeLLM(reply(("arg_2", HEDGE_QUOTE, "modal")))
    review = await build_coverage_review(state, llm, FakeDispatcher())
    assert review.status == "no_candidates"
    assert review.to_state()["items"] == []
    # The note is the ONLY thing Act II appends: empty means the prompt is
    # the pre-#3492 one, byte for byte.
    state.coverage_review = review.to_state()
    assert coverage_review_note(state) == ""


def test_a_bare_state_renders_no_block():
    assert coverage_review_note(SimpleNamespace()) == ""
    assert coverage_review_note({"coverage_review": {"status": "no_llm"}}) == ""


# --- witness 3: the routed lens's answer reaches the acts' input ------------


async def test_the_routed_answer_reaches_the_acts_input():
    from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
        build_act2_evidence,
    )

    state = make_state(examined=["arg_1"])
    llm = FakeLLM(reply(("arg_2", HEDGE_QUOTE, "statistical")))
    review = await build_coverage_review(state, llm, FakeDispatcher())
    state.coverage_review = review.to_state()

    evidence = build_act2_evidence(state)
    assert HEDGE_QUOTE in evidence.coverage_review
    assert str(HEDGE_OFFSET) in evidence.coverage_review
    assert "fallacy_descent" in evidence.coverage_review
    assert "answered" in evidence.coverage_review


async def test_an_unwired_lens_reaches_the_acts_as_a_named_absence():
    """A class with no wired lens prints « nommé, non examiné », not a verdict."""
    from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
        build_act2_evidence,
    )

    class _NotWired:
        async def __call__(self, item):
            return {"status": "lens_not_wired", "reason": "synthetic"}

    state = make_state(examined=["arg_1"])
    llm = FakeLLM(reply(("arg_2", HEDGE_QUOTE, "modal")))
    review = await build_coverage_review(state, llm, _NotWired())
    state.coverage_review = review.to_state()

    note = coverage_review_note(state)
    assert "câblée" in note
    assert "verdict" in note
    assert HEDGE_QUOTE in build_act2_evidence(state).coverage_review


# --- the invoke layer: persona, wired walk, persisted record -----------------


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


async def test_the_invoke_walks_a_statistical_item_through_the_shared_walk(
    monkeypatch,
):
    """A statistical item reaches the SAME walk the winner reading uses."""
    walked = []

    async def walk(quote, unit_id, service, taxonomy_path):
        walked.append((unit_id, quote, taxonomy_path))
        return {"fallacies": [{"fallacy": "synthetic", "family": "synthetic"}]}

    ic = _patch_invoke(
        monkeypatch, FakeLLM(reply(("arg_2", HEDGE_QUOTE, "statistical"))), walk
    )
    state = make_state(examined=["arg_1"])

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    assert out["status"] == "ok"
    assert out["items"][0]["unit_id"] == "arg_2"
    assert out["items"][0]["routed"]["status"] == "answered"
    assert out["items"][0]["routed"]["finding"]["fallacies"] == [
        {"fallacy": "synthetic", "family": "synthetic"}
    ]
    assert len(walked) == 1
    assert walked[0][0] == "arg_2"
    assert walked[0][1] == HEDGE_QUOTE
    assert walked[0][2].endswith("argumentum_fallacies_taxonomy.csv")


async def test_the_invoke_names_a_modal_item_without_inventing_a_lens(monkeypatch):
    """The modal arm reads the run's population — its item stays a named gap."""
    walked = []

    async def walk(quote, unit_id, service, taxonomy_path):  # pragma: no cover
        walked.append(unit_id)
        return {"fallacies": []}

    ic = _patch_invoke(
        monkeypatch, FakeLLM(reply(("arg_2", HEDGE_QUOTE, "modal"))), walk
    )
    state = make_state(examined=["arg_1"])

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    assert out["status"] == "ok"
    routed = out["items"][0]["routed"]
    assert routed["status"] == "lens_not_wired"
    assert "population" in routed["finding"]["reason"]
    assert walked == []


async def test_the_invoke_without_a_state_is_unreachable_not_fabricated(monkeypatch):
    async def walk(*args, **kwargs):  # pragma: no cover
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

    async def _noop_walk(*args, **kwargs):
        return {"fallacies": []}

    ic = _patch_invoke(
        monkeypatch,
        FakeLLM(reply(("arg_2", HEDGE_QUOTE, "statistical"))),
        _noop_walk,
    )
    state = make_state(examined=["arg_1"], record={})

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})
    _write_coverage_review_to_state(out, state, {})

    assert state.coverage_review["status"] == "ok"
    assert state.coverage_review["basis"] == "coverage_review"
    assert state.coverage_review["items"][0]["unit_id"] == "arg_2"
    # The map entry is what the executor looks the writer up by.
    assert (
        CAPABILITY_STATE_WRITERS["coverage_review"] is _write_coverage_review_to_state
    )
