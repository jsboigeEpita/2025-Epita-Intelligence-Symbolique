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

import pytest

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


def make_panel_state(
    *,
    translations=None,
    fol_results=None,
    modal_results=None,
    fol_signature=None,
):
    """#3500 — the state AS THE PANEL RECORDS IT.

    Measured on the 10 recorded c4b states (R1156 review):
    ``nl_to_logic_translations`` is propositional only (52/52), while the FOL
    and modal formulas live in ``fol_analysis_results`` (93 formulas, 9/10
    states) and ``modal_analysis_results`` (52 formulas, 9/10 states), with
    the run's FOL signature in ``fol_shared_signature``. A test double richer
    than the recorded shape passed an arm that answers nothing on any panel
    document.
    """
    state = make_state(translations)
    state.fol_analysis_results = list(fol_results or [])
    state.modal_analysis_results = list(modal_results or [])
    state.fol_shared_signature = dict(fol_signature or {})
    return state


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


def _patch_lenses(
    monkeypatch, *, translated="[](p)", consistent=False, message="msg", kb_alone=True
):
    seen = {}
    calls = {"n": 0}

    async def translate(quote, lens, **kwargs):
        seen["translate"] = (quote, lens)
        seen["translate_kwargs"] = kwargs
        return {"status": "translated", "formula": translated, "logic_type": lens}

    async def check(formulas, lens):
        # R1157 — the probe is called on the KB ALONE first, then on the KB
        # plus the passage. The double answers each leg with its own verdict.
        calls["n"] += 1
        seen["check"] = (list(formulas), lens)
        seen["check_calls"] = calls["n"]
        verdict = kb_alone if calls["n"] == 1 else consistent
        return {"consistent": verdict, "message": message}

    monkeypatch.setattr(ic, "_coverage_translate_passage", translate)
    monkeypatch.setattr(ic, "_coverage_check_logic_kb", check)
    return seen


async def test_a_modal_item_reaches_the_modal_lens(monkeypatch):
    """The named absence becomes a solver answer, and the note says what it is.

    #3500: the passage's translation SHARES the KB's atom — under the shared-
    vocabulary rule a disjoint translation is a named absence, not a verdict,
    so the synthetic formulas must overlap for the solver leg to be pinned.
    """
    state = make_state(
        [{"logic_type": "modal", "formula": "[](rain)", "is_valid": True}]
    )
    _patch_persona(monkeypatch, reply(QUOTE, "modal"))
    seen = _patch_lenses(monkeypatch, translated="[](rain)", consistent=False)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    assert out["status"] == "ok"
    routed = out["items"][0]["routed"]
    assert routed["status"] == "answered"
    assert routed["finding"]["verdict"] == "contradicts_run_kb"
    assert routed["finding"]["consistent"] is False
    # The passage was translated once, by the class's lens, against the run's KB.
    assert seen["translate"] == (QUOTE, "modal")
    assert seen["check"] == (["[](rain)", "[](rain)"], "modal")

    state.coverage_review = out
    note = coverage_review_note(state)
    assert "CONTREDIT" in note
    assert "[](rain)" in note
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
    # R1157 — the finding speaks the TRANSLATOR's vocabulary ("fol"), never
    # the bridge's "first_order": that value silently selected the MODAL
    # system prompt for FOL passages.
    assert routed["finding"]["logic_type"] == "fol"
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
    checks = {"n": 0}

    async def translate(quote, lens, **kwargs):
        return {"status": "untranslatable", "reason": "parse error on the formula"}

    async def check(formulas, lens):
        # R1157 — the KB-ALONE control probe is legitimate and passes; the
        # KB-plus-passage probe must never run on an untranslatable passage.
        checks["n"] += 1
        if checks["n"] > 1:  # pragma: no cover - must not run
            raise AssertionError("a KB was probed without a translated passage")
        return {"consistent": True, "message": "readable alone"}

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


# --- #3500 — the KB is read where the phases record it, under the run's vocabulary


def test_the_kb_reads_the_fields_the_phases_record():
    """Born red on the pre-#3500 head: ``fol_analysis_results`` and
    ``modal_analysis_results`` were never read, so the arm answered nothing on
    any panel document. The ``is_valid`` exclusion applies where an entry
    carries it, and a non-list ``formulas`` is skipped, not crashed on."""
    state = make_panel_state(
        fol_results=[
            {"formulas": ["Rejete(a)", ""], "is_valid": False},
            {"formulas": ["Dirige(b)"]},
            "junk",
            {"formulas": "not-a-list"},
        ],
        modal_results=[{"formulas": ["[](pluie)"]}, {"formulas": []}],
    )
    assert ic._coverage_run_kb_formulas(state, "first_order") == ["Dirige(b)"]
    assert ic._coverage_run_kb_formulas(state, "modal") == ["[](pluie)"]


async def test_a_modal_item_reads_the_kb_the_phases_recorded(monkeypatch):
    """The recorded shape reaches the solver, not only the test double's."""
    state = make_panel_state(
        translations=[
            {"logic_type": "propositional", "formula": "p", "is_valid": True}
        ],
        modal_results=[
            {
                "id": "modal_1",
                "formulas": ["[](pluie)"],
                "valid": True,
                "modalities": [],
            }
        ],
    )
    _patch_persona(monkeypatch, reply(QUOTE, "modal"))
    seen = _patch_lenses(monkeypatch, translated="[](pluie)", consistent=False)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    routed = out["items"][0]["routed"]
    assert routed["status"] == "answered"
    # The solver probed the RECORDED formula plus the passage's.
    assert seen["check"][0] == ["[](pluie)", "[](pluie)"]
    assert routed["finding"]["shared_symbols"] == 1


async def test_the_passage_is_translated_under_the_runs_vocabulary(monkeypatch):
    """Without a shared vocabulary the consistency verdict holds by
    construction — so the translation is CONSTRAINED to the run's own symbols:
    the modal arm passes the KB's atoms, the FOL arm carries the run's
    signature in the system prompt."""
    modal_state = make_panel_state(
        modal_results=[
            {
                "id": "modal_1",
                "formulas": ["[](pluie)"],
                "valid": True,
                "modalities": [],
            }
        ]
    )
    _patch_persona(monkeypatch, reply(QUOTE, "modal"))
    seen = _patch_lenses(monkeypatch, translated="[](pluie)", consistent=True)

    await ic._invoke_coverage_review(DOCUMENT, {"_state_object": modal_state})
    assert seen["translate_kwargs"].get("shared_atoms") == ["pluie"]

    fol_state = make_panel_state(
        fol_results=[
            {
                "id": "fol_1",
                "formulas": ["Dirige(a)"],
                "consistent": True,
                "inferences": [],
                "confidence": 0.0,
            }
        ],
        fol_signature={
            "default": {
                "sorts": {"Personne": ["a", "b"]},
                "predicates": {"Dirige": 1},
                "constants_raw": {"a": "person", "b": "person"},
            }
        },
    )
    _patch_persona(monkeypatch, reply(QUOTE, "inferential"))
    seen = _patch_lenses(monkeypatch, translated="Dirige(b)", consistent=True)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": fol_state})
    note_context = str(seen["translate_kwargs"].get("context_note") or "")
    assert "Dirige" in note_context
    assert "a" in note_context
    routed = out["items"][0]["routed"]
    assert routed["status"] == "answered"
    assert routed["finding"]["shared_symbols"] == 1


async def test_a_passage_sharing_no_symbol_is_a_named_absence(monkeypatch):
    """A formula with no symbol in common with the KB cannot contradict it:
    the solver would return « consistent » by construction. That vacuous truth
    is a NAMED absence, never a verdict — and the solver is not asked."""
    state = make_panel_state(
        modal_results=[
            {
                "id": "modal_1",
                "formulas": ["[](pluie)"],
                "valid": True,
                "modalities": [],
            }
        ]
    )
    _patch_persona(monkeypatch, reply(QUOTE, "modal"))
    seen = _patch_lenses(monkeypatch, translated="[](soleil)", consistent=True)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    routed = out["items"][0]["routed"]
    assert routed["status"] == "lens_no_finding"
    assert routed["finding"]["no_shared_symbols"] is True
    assert routed["finding"]["shared_symbols"] == 0
    assert "shares no symbol" in routed["finding"]["reason"]
    # The KB-alone control probe ran (once, on the KB only); the solver was
    # never asked the VACUOUS question — KB plus a disjoint passage.
    assert seen["check_calls"] == 1
    assert seen["check"][0] == ["[](pluie)"]

    state.coverage_review = out
    note = coverage_review_note(state)
    assert "ne partage aucun symbole" in note
    assert "ne contredit pas" not in note
    assert "CONTREDIT" not in note


# --- R1157 — the translator's own vocabulary, and the KB the run DECIDED ---


async def test_the_fol_coverage_translation_sends_the_fol_system_prompt(monkeypatch):
    """R1157 — born red on this head. NO injected translator: only the
    completion seam is patched, the REAL translator runs, and the messages it
    sends are captured. ``_COVERAGE_LENS_LOGIC['fol']`` was ``'first_order'``
    — a value outside the translator's vocabulary — so the prompt selection
    silently fell to the MODAL system prompt and the FOL validator rejected
    what came back: 35/35 untranslatable on the coordinator's paid replay."""
    import argumentation_analysis.services.nl_to_logic as ntl

    captured = []

    async def fake_completion(client, model=None, messages=None, **kwargs):
        captured.append([dict(m) for m in messages])
        # An EMPTY formula: the validator refuses it in one guard, no JVM,
        # no retry loop past the prompt this witness pins.
        message = SimpleNamespace(content=json.dumps({"formula": ""}))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(ntl, "cached_raw_chat_completion", fake_completion)
    monkeypatch.setattr(
        ntl, "resolve_chat_endpoint", lambda: ("key", "http://synthetic", "model")
    )
    import argumentation_analysis.core.utils.network_utils as network_utils

    monkeypatch.setattr(
        network_utils, "build_async_openai_client", lambda **kwargs: object()
    )

    out = await ic._coverage_translate_passage(QUOTE, "fol")

    assert captured, "the real translator made no completion call"
    system = captured[0][0]
    assert system["role"] == "system"
    assert ntl.FOL_SYSTEM_PROMPT in system["content"]
    assert ntl.MODAL_SYSTEM_PROMPT not in system["content"]
    # The empty formula is refused honestly — the witness pins the PROMPT,
    # and the status says the translation did not fake one.
    assert out["status"] == "untranslatable"


async def test_the_translator_raises_on_a_logic_type_outside_its_vocabulary():
    """R1157 — a value from calling code is never coerced into another
    logic's prompt: ``first_order`` (the bridge's vocabulary) silently
    selected the MODAL system prompt before; it now raises, at every entry
    the calling code can reach."""
    from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

    for supported in ("propositional", "fol", "modal"):
        NLToLogicTranslator(logic_type=supported)  # the three stay accepted
    with pytest.raises(ValueError, match="logic_type"):
        NLToLogicTranslator(logic_type="first_order")
    translator = NLToLogicTranslator()
    with pytest.raises(ValueError, match="logic_type"):
        await translator.translate("un argument", logic_type="first_order")
    with pytest.raises(ValueError, match="logic_type"):
        await translator.translate_batch(["un argument"], logic_type="first_order")


def test_an_entry_the_run_did_not_decide_stays_out_of_the_kb():
    """R1157 — one FOL entry whose recorded verdict is None ("Constant … has
    not been declared") carried its refusal into the whole concatenated KB:
    9/9 states rendered the FOL base undecided. Only the entries the run
    DECIDED enter (consistent True or False); an entry that records no
    verdict key (the modal shape) stays — its own probe decides."""
    state = make_panel_state(
        fol_results=[
            {"formulas": ["Dirige(a)"], "consistent": True},
            {"formulas": ["Rejete(b)"], "consistent": None},
            {"formulas": ["Tient(c)"], "consistent": False},
            {"formulas": ["Autre(d)"]},
            {"formulas": ["Vide(e)"], "is_valid": False},
        ]
    )
    assert ic._coverage_run_kb_formulas(state, "fol") == [
        "Dirige(a)",
        "Tient(c)",
        "Autre(d)",
    ]


async def test_an_inconsistent_kb_alone_never_yields_contradicts_run_kb(monkeypatch):
    """R1157 — a run KB inconsistent ON ITS OWN (one state: 26 formulas,
    recorded False) makes every passage "contradict" by construction. The
    control runs BEFORE any passage verdict: a named absence, and the passage
    is not even translated."""
    state = make_panel_state(
        fol_results=[{"formulas": ["Dirige(a)", "Rejete(a)"], "consistent": False}]
    )
    _patch_persona(monkeypatch, reply(QUOTE, "inferential"))
    seen = _patch_lenses(monkeypatch, kb_alone=False, consistent=False)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    routed = out["items"][0]["routed"]
    assert routed["status"] == "lens_no_finding"
    assert routed["finding"].get("kb_alone") == "inconsistent"
    assert routed["finding"].get("verdict") != "contradicts_run_kb"
    assert "translate" not in seen  # nothing was translated for nothing

    state.coverage_review = out
    note = coverage_review_note(state)
    assert "déjà incohérente à elle seule" in note
    assert "CONTREDIT" not in note


async def test_an_undecided_kb_alone_is_a_named_absence(monkeypatch):
    """The undecided twin: a base the solver cannot read answers nothing,
    whatever the passage says."""
    state = make_panel_state(
        fol_results=[{"formulas": ["Dirige(a)"], "consistent": True}]
    )
    _patch_persona(monkeypatch, reply(QUOTE, "inferential"))
    seen = _patch_lenses(monkeypatch, kb_alone=None, consistent=True)

    out = await ic._invoke_coverage_review(DOCUMENT, {"_state_object": state})

    routed = out["items"][0]["routed"]
    assert routed["status"] == "lens_no_finding"
    assert routed["finding"].get("kb_alone") == "undecided"
    assert "translate" not in seen

    state.coverage_review = out
    note = coverage_review_note(state)
    assert "indécise à elle seule" in note
