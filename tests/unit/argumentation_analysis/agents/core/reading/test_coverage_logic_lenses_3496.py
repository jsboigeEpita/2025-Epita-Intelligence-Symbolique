"""#3496 — the modal and FOL lenses reach a PASSAGE, not only the run's KB.

The coverage pass (#3492) named a passage per class and routed it. Only the
fallacy descent had a passage-level entry point: the modal and FOL arms read
the run's translated population, so those items were recorded
``lens_not_wired`` — honest, but an absence. This file pins the entry points
that close it:

* one passage is translated by the SAME translator the phases use, and probed
  against the run's OWN formulas of that logic (never a re-translation of the
  document);
* the verdict is a CONSISTENCY one, tri-state, and the render says so: it
  never borrows the vocabulary of a fallacy verdict or of an entailment;
* an empty run KB, an untranslatable passage and an undecided solver each
  stay a named absence, never a vacuous "consistent".

Everything here is synthetic (invented prose, no corpus text, no paid call):
the translator and the consistency probe are injected, so the witnesses pin
the WIRING, not the solvers — those are the phases' own and are measured
where they live.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from argumentation_analysis.agents.core.reading.coverage_review import (
    coverage_review_note,
)
from argumentation_analysis.orchestration import invoke_callables as ic

OPENING = "Le texte ouvre sur une constatation simple."
FILLER = (
    "La commission a siégé longtemps et le rapport circule depuis plusieurs "
    "semaines dans les couloirs."
)
QUOTE = "Les chiffres du rapport disent que non."
CLOSING = "Une autre lecture du dossier suit cette remarque."
DOCUMENT = f"{OPENING} {FILLER} {QUOTE} {CLOSING}"
THESIS = OPENING
QUOTE_OFFSET = DOCUMENT.index(QUOTE)


def make_state(translations=None):
    """A synthetic state: the document, one thesis move, the run's formulas."""
    return SimpleNamespace(
        raw_text=DOCUMENT,
        identified_arguments={"arg_1": QUOTE},
        argument_provenance={
            "arg_1": {"producer": "llm_extract", "offset": QUOTE_OFFSET}
        },
        analysis_coverage={},
        defining_moves={
            "moves": [{"slot": "thesis", "quote": THESIS, "offset": 0}],
            "status": "ok",
            "basis": "first_reading",
        },
        nl_to_logic_translations=list(translations or []),
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
    )


def reply(quote, kind):
    return json.dumps(
        {"items": [{"quote": quote, "class": kind, "reason": "raison synthétique"}]}
    )


class FakeLLM:
    def __init__(self, content):
        self.content = content
        self.prompts = []

    async def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.content


def _patch_persona(monkeypatch, content):
    monkeypatch.setattr(
        ic, "_build_persona_callable", lambda persona: (FakeLLM(content), "")
    )


def _patch_lenses(monkeypatch, *, translated="[](p)", consistent=False, message="msg"):
    seen = {}

    async def translate(quote, lens):
        seen["translate"] = (quote, lens)
        return {"status": "translated", "formula": translated, "logic_type": lens}

    async def check(formulas, lens):
        seen["check"] = (list(formulas), lens)
        return {"consistent": consistent, "message": message}

    monkeypatch.setattr(ic, "_coverage_translate_passage", translate)
    monkeypatch.setattr(ic, "_coverage_check_logic_kb", check)
    return seen


async def test_a_modal_item_reaches_the_modal_lens(monkeypatch):
    """The named absence becomes a solver answer, and the note says what it is."""
    state = make_state(
        [{"logic_type": "modal", "formula": "[](rain)", "is_valid": True}]
    )
    _patch_persona(monkeypatch, reply(QUOTE, "modal"))
    seen = _patch_lenses(monkeypatch, translated="[](p)", consistent=False)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    assert out["status"] == "ok"
    routed = out["items"][0]["routed"]
    assert routed["status"] == "answered"
    assert routed["finding"]["verdict"] == "contradicts_run_kb"
    assert routed["finding"]["consistent"] is False
    # The passage was translated once, by the class's lens, against the run's KB.
    assert seen["translate"] == (QUOTE, "modal")
    assert seen["check"] == (["[](rain)", "[](p)"], "modal")

    state.coverage_review = out
    note = coverage_review_note(state)
    assert "CONTREDIT" in note
    assert "[](p)" in note
    # A logic lens is NOT a fallacy lens: the note must not speak its language.
    assert "sophisme" not in note


async def test_an_inferential_item_reaches_the_fol_lens(monkeypatch):
    state = make_state([{"logic_type": "fol", "formula": "P(a)", "is_valid": True}])
    _patch_persona(monkeypatch, reply(QUOTE, "inferential"))
    seen = _patch_lenses(monkeypatch, translated="Q(a)", consistent=True)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    routed = out["items"][0]["routed"]
    assert routed["status"] == "answered"
    assert routed["finding"]["verdict"] == "consistent_with_run_kb"
    assert routed["finding"]["logic_type"] == "first_order"
    assert seen["translate"] == (QUOTE, "fol")
    assert seen["check"] == (["P(a)", "Q(a)"], "fol")

    state.coverage_review = out
    note = coverage_review_note(state)
    # Consistency, never entailment: the wording must say what it is.
    assert "ne contredit pas" in note
    assert "implication" in note
    assert "sophisme" not in note


async def test_an_empty_run_kb_is_a_named_absence_never_a_vacuous_consistent(
    monkeypatch,
):
    """A KB of one formula is trivially consistent — so it is not a verdict."""
    state = make_state([])
    _patch_persona(monkeypatch, reply(QUOTE, "modal"))
    seen = _patch_lenses(monkeypatch)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    routed = out["items"][0]["routed"]
    assert routed["status"] == "lens_no_finding"
    assert "cannot be contradicted" in routed["finding"]["reason"]
    assert "translate" not in seen  # nothing was translated for nothing

    state.coverage_review = out
    note = coverage_review_note(state)
    assert "non concluante" in note
    assert "verdict indécis" not in note


async def test_an_untranslatable_passage_is_named_not_verdicted(monkeypatch):
    state = make_state(
        [{"logic_type": "modal", "formula": "[](rain)", "is_valid": True}]
    )
    _patch_persona(monkeypatch, reply(QUOTE, "modal"))

    async def translate(quote, lens):
        return {"status": "untranslatable", "reason": "parse error on the formula"}

    async def check(formulas, lens):  # pragma: no cover - must not run
        raise AssertionError("a KB was probed without a translated passage")

    monkeypatch.setattr(ic, "_coverage_translate_passage", translate)
    monkeypatch.setattr(ic, "_coverage_check_logic_kb", check)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    routed = out["items"][0]["routed"]
    assert routed["status"] == "lens_no_finding"
    assert routed["finding"]["untranslatable"] is True

    state.coverage_review = out
    note = coverage_review_note(state)
    assert "aucune traduction formelle valide" in note
    assert "parse error on the formula" in note


async def test_an_undecided_solver_says_undecided(monkeypatch):
    state = make_state([{"logic_type": "fol", "formula": "P(a)", "is_valid": True}])
    _patch_persona(monkeypatch, reply(QUOTE, "inferential"))
    _patch_lenses(
        monkeypatch,
        translated="Q(a)",
        consistent=None,
        message="Degraded: reasoner absent",
    )

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    routed = out["items"][0]["routed"]
    assert routed["finding"]["verdict"] == "undecided"

    state.coverage_review = out
    note = coverage_review_note(state)
    assert "verdict indécis" in note
    assert "Degraded" in note


def test_the_run_kb_reads_only_its_own_logic_and_only_valid_formulas():
    state = make_state(
        [
            {"logic_type": "modal", "formula": "[](rain)", "is_valid": True},
            {"logic_type": "modal", "formula": "[](bad)", "is_valid": False},
            {"logic_type": "modal", "formula": "", "is_valid": True},
            {"logic_type": "fol", "formula": "P(a)", "is_valid": True},
            {"logic_type": "first_order", "formula": "Q(b)", "is_valid": None},
            {"logic_type": "propositional", "formula": "p", "is_valid": True},
            "not-a-dict",
        ]
    )
    assert ic._coverage_run_kb_formulas(state, "modal") == ["[](rain)"]
    assert ic._coverage_run_kb_formulas(state, "first_order") == ["P(a)", "Q(b)"]
    assert ic._coverage_run_kb_formulas(SimpleNamespace(), "modal") == []


async def test_a_penalty_free_absence_of_state_is_unchanged(monkeypatch):
    """The pre-#3496 surface: no shared state stays unreachable."""
    out = await ic._invoke_coverage_review(DOCUMENT, {})
    assert out["status"] == "unreachable"
    assert out["reason"] == "no_shared_state"
