# -*- coding: utf-8 -*-
"""#1649 + #3377 — the PRODUCER tier of the counter lane's scope field.

The consumer wiring landed first (``test_aspic_undercut_wiring_1649.py``:
``_invoke_aspic`` turns an ``inference`` counter into one WK-undercut rule,
every non-emission path named on the payload). Its census finding was blunt:
0 of 38 counters carried ``attacked_component`` — "the producer field not
requested yet". This file is the producer: the prompt ASKS for the component
(premise / inference / conclusion), the stamped reply keeps only the
canonical trio, and the state entry carries it.

#3377 rides the same generator: the historian's labelled situation note is
appended to the counter system prompt AFTER the base contract — the same ONE
producer of the wording nl_to_logic already reads (``historian.context_note``);
no historian, no note, byte-identical prompt.

Born red on ``main`` (source edits stashed, this file alone): main's counter
prompt names neither the field nor the trio, no state entry ever carries
``attacked_component``, and the historian's note never reaches the counter
phase.

Privacy HARD: synthetic sentences only — no corpus text.
"""

import asyncio
import json

from argumentation_analysis.agents.core.context.historian import context_note
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration import invoke_callables
from argumentation_analysis.orchestration.invoke_callables import (
    _generate_counters_for_targets,
    _invoke_counter_argument,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_counter_argument_to_state,
)

_FAKE_KEY = "sk-fake-witness-zero-bill-1649"


def _units_state(historian: bool = False):
    """3 units; ``historian=True`` plants a historian read the note reads."""
    state = UnifiedAnalysisState("Source text for the counter producer witness.")
    state.identified_arguments = {
        "arg_1": "Unit 1 claims a 15 percent improvement and cites 2023 data.",
        "arg_2": "Unit 2 answers that the 15 percent figure omits the baseline.",
        "arg_3": "Unit 3 notes the 2023 dataset covers only 12 of 40 regions.",
    }
    state.argument_provenance = {
        "arg_1": {"producer": "test", "offset": 100},
        "arg_2": {"producer": "test", "offset": 1_600},
        "arg_3": {"producer": "test", "offset": 3_100},
    }
    if historian:
        state.historical_context = {
            "situation": "Débat budgétaire synthétique dans une assemblée fictive.",
            "items": [
                {"claim": "Le chiffre de 15 pour cent est contesté", "confidence": 0.9},
            ],
        }
    return state


def _context_for(state):
    return {
        "_state_object": state,
        "phase_extract_output": {"arguments": [], "claims": []},
        "phase_hierarchical_fallacy_output": {"fallacies": []},
        "phase_quality_output": {},
    }


def _fake_chat_factory(echoes, captured=None, component="inference"):
    """A fake LLM answering each offered target, carrying the component."""

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
        if captured is not None:
            captured["system"] = messages[0]["content"]
            captured["user"] = messages[-1]["content"]
        payload = [
            {
                "counter_argument": f"Counter {i + 1} rebuts the unit head-on.",
                "strategy_used": "reductio ad absurdum",
                "target_argument": echo,
                "strength": "moderate",
                "attacked_component": component,
                "reasoning": "witness",
            }
            for i, echo in enumerate(echoes)
        ]
        return _Resp(json.dumps(payload))

    return _fake


_KEYS = ["arg_1", "arg_2", "arg_3"]


class TestThePromptAsksForTheComponent:
    """#1649 — the producer's contract: the prompt OFFERS the field and its
    vocabulary. Born red on main: main's counter prompt names neither."""

    def test_schema_names_the_field_and_the_trio(self, monkeypatch):
        state = _units_state()
        captured: dict = {}
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(_KEYS, captured),
        )
        asyncio.run(_invoke_counter_argument(state.raw_text, _context_for(state)))
        system = captured.get("system", "")
        assert (
            '"attacked_component"' in system
        ), "the prompt must offer the field the ASPIC consumer reads"
        for word in ("premise", "inference", "conclusion"):
            assert word in system, f"the trio's vocabulary must be offered: {word}"


class TestTheComponentTravelsToTheState:
    """#1649 — the stamped reply keeps the canonical trio only, the payload
    carries it (the consumer's input), and the state entry stores it. Born
    red on main: no param, no stamp, no state key."""

    def test_inference_reply_reaches_the_state_entry(self, monkeypatch):
        state = _units_state()
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(_KEYS),
        )
        result = asyncio.run(
            _invoke_counter_argument(state.raw_text, _context_for(state))
        )
        # The payload the ASPIC consumer reads carries the component.
        for ca in result["llm_counter_arguments"]:
            assert ca.get("attacked_component") == "inference"
        _write_counter_argument_to_state(result, state, {})
        stored = state.counter_arguments
        assert len(stored) == 3
        for ca in stored:
            assert (
                ca.get("attacked_component") == "inference"
            ), "the state entry must carry the scope the consumer keys on"

    def test_uppercase_reply_is_normalized_to_the_trio(self, monkeypatch):
        state = _units_state()
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(_KEYS, component="Premise"),
        )
        result = asyncio.run(
            _invoke_counter_argument(state.raw_text, _context_for(state))
        )
        for ca in result["llm_counter_arguments"]:
            assert ca.get("attacked_component") == "premise"

    def test_junk_component_is_dropped_not_guessed(self, monkeypatch):
        """Born red on main too: an off-trio reply travels UNSTAMPED there
        (the parse keeps every key) — the consumer would log it per-counter.
        The stamp keeps the trio only: junk carries NO component, never a
        nearest-vocabulary guess."""
        state = _units_state()
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(_KEYS, component="the facts themselves"),
        )
        result = asyncio.run(
            _invoke_counter_argument(state.raw_text, _context_for(state))
        )
        _write_counter_argument_to_state(result, state, {})
        for ca in result["llm_counter_arguments"]:
            assert "attacked_component" not in ca
        for ca in state.counter_arguments:
            assert "attacked_component" not in ca


class TestTheHistoriansNoteRidesTheCounterPrompt:
    """#3377 — the counter generator reads the historian's note: appended to
    the SYSTEM prompt after the base contract, the same ONE producer of the
    wording nl_to_logic reads; no historian = byte-identical prompt. The
    note-carrying tests are born red on main."""

    @staticmethod
    def _direct_prompt(monkeypatch, note: str) -> str:
        """The generator's system prompt under a fake model, isolated."""
        captured: dict = {}
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(["arg_1"], captured),
        )
        asyncio.run(
            _generate_counters_for_targets(
                None,
                "fake-model",
                ["one target"],
                target_ids=["arg_1"],
                context_note=note,
            )
        )
        return captured["system"]

    def test_note_is_appended_after_the_base_contract(self, monkeypatch):
        state = _units_state(historian=True)
        note = context_note(state)
        assert note, "the planted historian read must produce a note"
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        base = self._direct_prompt(monkeypatch, "")
        with_note = self._direct_prompt(monkeypatch, note)
        assert with_note == f"{base}\n\n{note}", (
            "the note rides AFTER the base contract, separated by a blank "
            "line — byte for byte"
        )

    def test_empty_note_is_byte_identical(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        first = self._direct_prompt(monkeypatch, "")
        second = self._direct_prompt(monkeypatch, "")
        assert first == second

    def test_production_phase_passes_the_note(self, monkeypatch):
        """The production counter phase computes the note from the state the
        historian wrote — born red on main (no persona field read)."""
        state = _units_state(historian=True)
        captured: dict = {}
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(_KEYS, captured),
        )
        asyncio.run(_invoke_counter_argument(state.raw_text, _context_for(state)))
        system = captured.get("system", "")
        assert (
            "SITUATION HISTORIQUE" in system
        ), "the historian's labelled block must reach the counter prompt"
        assert system.index("SITUATION HISTORIQUE") > system.index(
            '"attacked_component"'
        ), "the note is appended AFTER the base contract"

    def test_production_phase_without_historian_keeps_the_prompt_clean(
        self, monkeypatch
    ):
        """Positive control both sides: no historian read, no note header —
        the provenance is never advertised where there is nothing to say."""
        state = _units_state()
        captured: dict = {}
        monkeypatch.setenv("OPENAI_API_KEY", _FAKE_KEY)
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(_KEYS, captured),
        )
        asyncio.run(_invoke_counter_argument(state.raw_text, _context_for(state)))
        assert "SITUATION HISTORIQUE" not in captured.get("system", "")
