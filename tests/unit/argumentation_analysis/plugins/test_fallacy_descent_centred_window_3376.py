"""#3376 — the descent reads WHERE the wide net found the candidate, not the head.

What is measured (Epic #3374, paid pass R1137a): at document level the wide net
reads 8,000 characters and returns taxonomy PKs only — no quote, no offset —
and every descent prompt then judges those candidates against
``argument_text[:500]``. A candidate found at character 5,000 is confirmed or
refused against a text that does not contain it.

This witness plants one fallacious sentence at character 5,000 of a synthetic
document and drives the real funnel with a fake model. On ``main`` the descent
prompt carries the opening 500 characters and the planted sentence is absent —
that is the red. After the repair the wide net returns a verbatim quote and the
descent reads a window of the SAME size centred on it.

Anti-pendulum, pinned here so a later rework cannot drift:

- the window is not lifted to the whole text (#2908: the one-shot fallback read
  it unbounded and the cost multiplies by every branch);
- the window size does not move in this PR — 500 stays the bound, and its value
  is a panel A/B decision;
- the head is not dropped: an unlocated quote falls back to it, flagged.

Synthetic text only, opaque identifiers only.
"""

import json
from unittest.mock import create_autospec

import pytest
from semantic_kernel.kernel import Kernel

from argumentation_analysis.core import reading_window as rw
from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)

# --- synthetic document -------------------------------------------------

_FILLER = (
    "le rapport décrit, étape par étape; la procédure suit son cours, sans détour. "
)
_DOC_CHARS = 12_000
_PLANT_CHAR = 5_000
# One fallacious move, planted deep in the document. The filler never contains
# it, so its presence in a prompt can only come from a window that reached it.
_PLANTED = (
    "Ceux qui contestent le projet n'ont bâti aucune école, "
    "donc leur avis ne pèse rien dans ce débat."
)

# Deepest bound the descent may ever read, restated here so a lifted window
# reddens instead of passing quietly.
_DESCENT_BOUND = 500


def _document_with_planted_fallacy() -> str:
    text = _FILLER * (_DOC_CHARS // len(_FILLER) + 1)
    text = text[:_PLANT_CHAR] + _PLANTED + text[_PLANT_CHAR:]
    return text[:_DOC_CHARS]


def _document_without_plant() -> str:
    return (_FILLER * (_DOC_CHARS // len(_FILLER) + 1))[:_DOC_CHARS]


# Minimal two-level taxonomy: one root (has a child → navigation prompt) and
# one leaf (no child → leaf confirmation prompt). Both prompts are sites.
_TAXONOMY = [
    {
        "PK": "10",
        "path": "2",
        "depth": "1",
        "text_fr": "Hors sujet",
        "text_en": "Irrelevance",
        "desc_fr": "Arguments sans rapport",
        "desc_en": "Unrelated arguments",
        "example_fr": "",
        "example_en": "",
        "nom_vulgarisé": "Hors sujet",
    },
    {
        "PK": "11",
        "path": "2.1",
        "depth": "2",
        "text_fr": "Ad Hominem",
        "text_en": "Ad Hominem",
        "desc_fr": "Attaque la personne",
        "desc_en": "Attacks the person",
        "example_fr": "",
        "example_en": "",
        "nom_vulgarisé": "Ad Hominem",
    },
]


class _CapturingLLM:
    """A fake model that records every prompt it is handed.

    Two surfaces, as the funnel uses them: ``get_chat_message_content`` (one
    reply, the wide net) and ``get_chat_message_contents`` (a list of messages,
    the descent). The descent replies with no function call — the branch
    exhausts — which keeps the witness on the prompt, not on taxonomy plumbing.
    """

    # The slave kernel registers the service by id (SK 1.x, Kernel.add_service).
    service_id = "capturing-fake-llm"

    def __init__(self, wide_net_reply: str = "[]"):
        self.wide_net_reply = wide_net_reply
        self.descent_prompts = []
        self.wide_net_prompts = []

    async def get_chat_message_content(self, chat_history, settings=None, kernel=None):
        self.wide_net_prompts.append(chat_history.messages[-1].content)
        return self.wide_net_reply

    async def get_chat_message_contents(self, chat_history, settings=None, kernel=None):
        self.descent_prompts.append(chat_history.messages[-1].content)
        return []


class _RecordingState:
    """Mirrors ``UnifiedAnalysisState.record_reading_window`` (shared_state.py).

    Same entry shape including ``extra`` (#3105) — the assertions read the real
    contract, not a convenient fake.
    """

    def __init__(self):
        self.reading_window_status = {}

    def record_reading_window(self, site, selection, extra=None):
        entry = {
            "status": getattr(selection, "status", str(selection)),
            "offset": getattr(selection, "offset", 0),
            "window": getattr(selection, "window", 0),
        }
        if extra:
            entry.update(extra)
        self.reading_window_status[site] = entry


def _wide_net_reply(quote: str = _PLANTED, with_quote: bool = True) -> str:
    """A wide-net reply naming the planted move, with or without evidence."""
    candidate = {
        "fallacy_name": "Ad Hominem",
        "root_category": "Hors sujet",
        "confidence": 0.9,
    }
    if with_quote:
        candidate["quote"] = quote
    return json.dumps([candidate])


def _plugin(llm, state=None) -> FallacyWorkflowPlugin:
    plugin = FallacyWorkflowPlugin(
        master_kernel=create_autospec(Kernel, instance=True),
        llm_service=llm,
        taxonomy_data=_TAXONOMY,
        reading_state=state,
    )
    # One branch after the other: the witness reads prompts deterministically.
    plugin.descent_sequential = True
    return plugin


def _descent_windows(llm) -> list:
    """The text each descent prompt put under « Text to analyze ».

    Returns the raw quoted span, so a test can say how much of the document a
    branch actually read — and whether the planted sentence is inside it.
    """
    spans = []
    for prompt in llm.descent_prompts:
        start = prompt.find('Text to analyze: "')
        if start < 0:
            continue
        start += len('Text to analyze: "')
        end = prompt.find('"', start)
        spans.append(prompt[start:end] if end > start else "")
    return spans


# --- the witness --------------------------------------------------------


class TestTheDescentReadsWhereTheCandidateIs:
    async def test_the_descent_prompt_contains_the_planted_sentence(self):
        """RED on main: the wide net saw the sentence at char 5,000, the descent
        judges the candidate against the first 500 chars — the sentence the
        candidate was found on is not in the prompt that confirms it."""
        llm = _CapturingLLM(_wide_net_reply())
        await _plugin(llm).run_guided_analysis(_document_with_planted_fallacy())

        assert llm.descent_prompts, (
            "no descent prompt was issued — the wide net produced no candidate "
            "and the funnel fell back to one-shot; this witness cannot speak"
        )
        assert any(_PLANTED in prompt for prompt in llm.descent_prompts), (
            "every descent prompt judged the candidate against text that does "
            "not contain the evidence the wide net found (#3376) — the "
            "quote the wide net returned never reached the descent window"
        )

    async def test_the_window_is_centred_on_the_quote(self):
        """RED on main: a centred window starts near the quote, so the sentence
        sits inside it with margin on both sides."""
        doc = _document_with_planted_fallacy()
        llm = _CapturingLLM(_wide_net_reply())
        await _plugin(llm).run_guided_analysis(doc)

        spans = _descent_windows(llm)
        assert spans, "no « Text to analyze » span reached a descent prompt"
        assert any(_PLANTED in span for span in spans), (
            "the planted sentence at char %d is outside every descent window"
            % _PLANT_CHAR
        )
        carrying = [span for span in spans if _PLANTED in span]
        for span in carrying:
            assert len(span) <= _DESCENT_BOUND, (
                "the descent window is %d chars for a %d-char bound — the "
                "window size is a panel A/B decision, not a repair side effect "
                "(#3376 anti-pendulum, #2908)" % (len(span), _DESCENT_BOUND)
            )

    async def test_the_window_size_is_not_lifted_to_the_text(self):
        """Anti-pendulum (#2908): the descent never reads the whole document."""
        doc = _document_with_planted_fallacy()
        llm = _CapturingLLM(_wide_net_reply())
        await _plugin(llm).run_guided_analysis(doc)

        for span in _descent_windows(llm):
            assert len(span) < len(doc), (
                "a descent prompt carried the whole document — #2908 bounded "
                "the one-shot read precisely because this cost multiplies by "
                "every branch"
            )

    def test_the_descent_bound_is_the_named_constant(self):
        """RED on main: the 500 was a literal at three sites; #3376 names it in
        ``core/reading_window.py`` so the value has one home and an A/B can
        move it."""
        assert getattr(rw, "DESCENT_WINDOW", None) == _DESCENT_BOUND, (
            "reading_window.DESCENT_WINDOW must exist and hold the descent "
            "bound (500) — the literal has one home now (#3376)"
        )


class TestTheHeadRemainsTheSignalledFallback:
    async def test_an_unlocated_quote_falls_back_to_the_head(self):
        """CONTROL — green on main by construction: a wide net that returns no
        quote (or one the text does not contain) leaves today's behaviour
        intact, head read, and the record says the fallback happened."""
        state = _RecordingState()
        llm = _CapturingLLM(_wide_net_reply(with_quote=False))
        await _plugin(llm, state).run_guided_analysis(_document_with_planted_fallacy())

        spans = _descent_windows(llm)
        assert spans, "the fallback branch read nothing"
        doc = _document_with_planted_fallacy()
        assert all(
            span in doc[: len(span)] or doc.startswith(span) for span in spans
        ), (
            "an unquoted candidate must read the head — the head stays the "
            "fallback (#3376 anti-pendulum)"
        )
        entry = state.reading_window_status["fallacy_descent"]
        assert "fallback" in str(entry.get("status", "")) or entry.get("offsets") == [
            0
        ], f"the record does not say the descent fell back to the head: {entry}"

    async def test_a_quote_the_text_does_not_hold_is_not_trusted(self):
        """A model can invent a quote. An unlocatable one is not sliced around —
        the descent falls back to the head instead of centring on garbage."""
        doc = _document_with_planted_fallacy()
        llm = _CapturingLLM(_wide_net_reply(quote="phrase absente du document, " * 3))
        await _plugin(llm).run_guided_analysis(doc)

        spans = _descent_windows(llm)
        assert spans, "the branch read nothing"
        for span in spans:
            assert doc.startswith(span), (
                "a window was centred on a quote the document does not "
                "contain — an unlocated quote must fall back to the head"
            )


class TestEachBranchSaysHowItEnded:
    async def test_the_result_records_every_branch_outcome(self):
        """RED on main: 7 branches ran, 1 fallacy came back, and the record kept
        no reason for the other six (#3376 DoD 1)."""
        llm = _CapturingLLM(_wide_net_reply())
        raw = await _plugin(llm).run_guided_analysis(_document_with_planted_fallacy())
        payload = json.loads(raw)

        assert "branch_outcomes" in payload, (
            "the result carries no branch_outcomes — a branch that ends without "
            "a confirmed fallacy leaves no trace of WHY (#3376 DoD 1)"
        )
        outcomes = payload["branch_outcomes"]
        assert outcomes, "branch_outcomes is empty although branches ran"
        for outcome in outcomes:
            assert outcome.get("start_pk"), f"an outcome names no branch: {outcome}"
            assert outcome.get(
                "action"
            ), f"a branch ended without a stated terminal action: {outcome}"
            assert (
                "reason" in outcome
            ), f"a branch ended without its reason field: {outcome}"

    async def test_an_exhausted_branch_is_named_not_silent(self):
        """The fake model never calls a function: the honest outcome is
        « no function call », said, not an unrecorded disappearance."""
        llm = _CapturingLLM(_wide_net_reply())
        raw = await _plugin(llm).run_guided_analysis(_document_with_planted_fallacy())
        actions = {o.get("action") for o in json.loads(raw)["branch_outcomes"]}
        assert "no_function_call" in actions, (
            f"expected the exhausted branches to say « no_function_call », got "
            f"{sorted(a for a in actions if a)}"
        )


class TestTheRecordListsTheOffsetsRead:
    async def test_one_offset_per_branch_reaches_the_reading_record(self):
        """RED on main: the record said a single (0, 500) whatever the branches
        read; #3376 DoD 3 asks for the offsets actually read, one per branch."""
        state = _RecordingState()
        llm = _CapturingLLM(_wide_net_reply())
        await _plugin(llm, state).run_guided_analysis(_document_with_planted_fallacy())

        entry = state.reading_window_status["fallacy_descent"]
        offsets = entry.get("offsets")
        assert (
            isinstance(offsets, list) and offsets
        ), f"the descent entry lists no per-branch offsets: {entry}"
        assert len(offsets) == len(llm.descent_prompts) or len(offsets) == len(
            {id(p) for p in llm.descent_prompts}
        ), "one offset per descent read was recorded as %d for %d prompts" % (
            len(offsets),
            len(llm.descent_prompts),
        )
        assert (
            entry.get("window") == _DESCENT_BOUND
        ), f"the recorded window is {entry.get('window')}, not the bound"

    async def test_a_head_only_run_renders_the_old_sentence(self):
        """CONTROL — the restitution sentence « 500 des N » must survive a run
        whose branches all read the head: the record changes only where the
        read changed (#3376 DoD 3)."""
        state = _RecordingState()
        llm = _CapturingLLM(_wide_net_reply(with_quote=False))
        await _plugin(llm, state).run_guided_analysis(_document_with_planted_fallacy())

        entry = state.reading_window_status["fallacy_descent"]
        assert entry["offset"] == 0, (
            f"a head read must record offset 0 — the restitution sentence "
            f"quotes the 500-char bound (#3134): {entry}"
        )
        assert entry["window"] == _DESCENT_BOUND
