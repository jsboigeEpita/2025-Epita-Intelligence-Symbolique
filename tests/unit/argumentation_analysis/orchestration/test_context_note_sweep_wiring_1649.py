# -*- coding: utf-8 -*-
"""#1649 + #3377 — the historian's note at the conversational sweep and at its retry.

#3571 (merged ``df760fa48``) gave ``_generate_counters_for_targets`` a
``context_note`` and wired it at three call sites: the production counter
phase, the conversational sweep (``_generate_counter_arguments_from_state``)
and the sweep's coverage retry. Only the production site was pinned by a
test, so dropping the note at the sweep, or at its retry, reddened nothing.

This file pins the two unwired sites. Each test watches ONE call site: the
fake model records the system prompt of every call, and the sweep's coverage
retry is made to fire by an empty answer (no counter covers a target, so the
sweep calls the generator a second time). The first recorded prompt belongs
to the sweep, the second to the retry.

The third class pins the docstring of ``historian.context_note``: it used to
say the consumer PREPENDS the note, while both consumers APPEND it after
their own contract. The drift is a docstring-only defect — the wording of the
one producer, not the behaviour of its readers.

Privacy HARD: synthetic sentences only — no corpus text, no document id.
"""

import asyncio

from argumentation_analysis.agents.core.context.historian import context_note
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration import invoke_callables
from argumentation_analysis.orchestration.invoke_callables import (
    _generate_counter_arguments_from_state,
)

_FAKE_KEY = "sk-fake-witness-zero-bill-1649d"


def _sweep_state(historian: bool = False):
    """3 identified units; ``historian=True`` plants a read the note reads."""
    state = UnifiedAnalysisState("Synthetic source text for the sweep witness.")
    state.identified_arguments = {
        "arg_1": "Unit 1 claims a 15 percent improvement and cites a 2023 study.",
        "arg_2": "Unit 2 answers that the 15 percent figure omits the baseline.",
        "arg_3": "Unit 3 notes the study covers only 12 of 40 regions.",
    }
    if historian:
        state.historical_context = {
            "situation": "Debate budgétaire synthétique dans une assemblée fictive.",
            "items": [
                {"claim": "Le chiffre de 15 pour cent est contesté", "confidence": 0.9},
            ],
            "status": "ok",
            "basis": "model_knowledge",
        }
    return state


def _recording_empty_chat(captured):
    """A fake model that records each system prompt and answers no counter.

    An empty answer leaves every target uncovered, so the sweep calls the
    generator a second time — that second call is the retry call site.
    """

    class _Msg:
        def __init__(self, content):
            self.content = content

    class _Choice:
        def __init__(self, content):
            self.message = _Msg(content)

    class _Resp:
        def __init__(self, content):
            self.choices = [_Choice(content)]

    async def _fake(client, model, messages, **kwargs):
        captured.append(
            {"system": messages[0]["content"], "user": messages[-1]["content"]}
        )
        return _Resp("[]")

    return _fake


class TestTheSweepCarriesTheNote:
    """#3377 — the sweep's own call to the generator carries the note."""

    def test_sweep_prompt_carries_the_note(self, monkeypatch):
        state = _sweep_state(historian=True)
        note = context_note(state)
        assert note, "the planted historian read must produce a note"
        captured: list = []
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _recording_empty_chat(captured),
        )
        asyncio.run(_generate_counter_arguments_from_state(state))
        assert captured, "the sweep must have asked the model"
        system = captured[0]["system"]
        assert (
            "SITUATION HISTORIQUE" in system
        ), "the historian's labelled block must reach the sweep's counter prompt"
        assert note in system, "the note must reach the prompt byte for byte"
        assert system.index(note) > system.index(
            '"attacked_component"'
        ), "the note is appended AFTER the base contract"

    def test_sweep_without_historian_keeps_the_prompt_clean(self, monkeypatch):
        """Positive control: no historian read, no note header — the
        provenance is never advertised where there is nothing to say."""
        state = _sweep_state()
        captured: list = []
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _recording_empty_chat(captured),
        )
        asyncio.run(_generate_counter_arguments_from_state(state))
        assert captured, "the sweep must have asked the model"
        assert "SITUATION HISTORIQUE" not in captured[0]["system"]


class TestTheSweepRetryCarriesTheNote:
    """#3377 — the sweep's coverage RETRY carries the note too. The retry is
    the second call to the generator, reached when the first answer leaves a
    target uncovered."""

    def test_retry_prompt_carries_the_note(self, monkeypatch):
        state = _sweep_state(historian=True)
        note = context_note(state)
        assert note, "the planted historian read must produce a note"
        captured: list = []
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _recording_empty_chat(captured),
        )
        asyncio.run(_generate_counter_arguments_from_state(state))
        assert (
            len(captured) == 2
        ), f"the coverage retry must have fired: {len(captured)} model calls"
        system = captured[1]["system"]
        assert (
            "SITUATION HISTORIQUE" in system
        ), "the historian's labelled block must reach the retry's counter prompt"
        assert note in system, "the note must reach the prompt byte for byte"

    def test_retry_without_historian_keeps_the_prompt_clean(self, monkeypatch):
        state = _sweep_state()
        captured: list = []
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _recording_empty_chat(captured),
        )
        asyncio.run(_generate_counter_arguments_from_state(state))
        assert (
            len(captured) == 2
        ), f"the coverage retry must have fired: {len(captured)} model calls"
        assert "SITUATION HISTORIQUE" not in captured[1]["system"]


class TestTheDocstringNamesTheDirection:
    """#3377 — ``historian.context_note``'s docstring said the consumer
    prepends the note; both consumers APPEND it, after their own contract
    (the counter generator and the NL→KB translator)."""

    def test_docstring_does_not_say_prepend(self):
        doc = context_note.__doc__ or ""
        assert (
            "prepend" not in doc.lower()
        ), "the docstring must not say the consumer prepends the note"

    def test_docstring_says_append(self):
        doc = context_note.__doc__ or ""
        assert (
            "append" in doc.lower()
        ), "the docstring must name the direction the consumers use: append"
