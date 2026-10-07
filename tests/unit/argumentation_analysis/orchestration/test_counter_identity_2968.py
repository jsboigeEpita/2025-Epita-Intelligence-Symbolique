# -*- coding: utf-8 -*-
"""#2968 — the counter-argument's target is an ID that travels, never a
position or a substring match.

Measured on the authorized 06/10 pass (doc_A): 0 of 48 counters pointed at
the unit they answer — 21 stored ``None`` and 27 a WRONG unit. The producer
numbered its targets ("1", "2", … per batch), asked for free text back, and
the writer resolved that echo by substring: the needle "1" matched the first
description containing a "1".

The identity now travels as an opaque key: each offered target carries its
``unit_id``, the prompt asks for the key back, and the echoed key is accepted
ONLY if the batch offered it. Everything else resolves to ``None`` with a
recorded reason — no substring, no first-match, no positional guess (#1019).
"""

import asyncio
import json
from types import SimpleNamespace

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration import invoke_callables
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_counter_argument,
)
from argumentation_analysis.orchestration.state_writers import (
    _resolve_target_arg_id,
    _write_counter_argument_to_state,
)


def _units_state():
    """3 units whose descriptions contain digits — on main the needle "1"
    substring-matched the first one (the measured defect's shape)."""
    state = UnifiedAnalysisState("Source text for the counter identity witness.")
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
    return state


def _context_for(state):
    return {
        "_state_object": state,
        "phase_extract_output": {"arguments": [], "claims": []},
        "phase_hierarchical_fallacy_output": {"fallacies": []},
        "phase_quality_output": {},
    }


def _fake_chat_factory(echoes, captured=None):
    """A fake LLM answering each offered target with ``echoes[i]``."""

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
            captured["user"] = messages[-1]["content"]
        payload = [
            {
                "counter_argument": f"Counter {i + 1} rebuts the unit head-on.",
                "strategy_used": "reductio ad absurdum",
                "target_argument": echo,
                "strength": "moderate",
                "reasoning": "witness",
            }
            for i, echo in enumerate(echoes)
        ]
        return _Resp(json.dumps(payload))

    return _fake


class TestNumberedEchoDoesNotResolve:
    def test_digit_echo_yields_none_with_reason(self, monkeypatch):
        """The measured shape: the model answers "1", "2", "3" — the old
        prompt's numbering. Born red on main: the substring resolver bound
        each to the first description containing the digit."""
        state = _units_state()
        captured: dict = {}
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-witness-zero-bill-2968")
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(["1", "2", "3"], captured),
        )
        result = asyncio.run(
            _invoke_counter_argument(state.raw_text, _context_for(state))
        )
        _write_counter_argument_to_state(result, state, {})
        stored = state.counter_arguments
        assert len(stored) == 3
        for ca in stored:
            assert ca.get("target_arg_id") is None, (
                f"a digit echo resolved to {ca.get('target_arg_id')!r} — "
                "no substring, no first-match (#2968)"
            )
            assert ca.get("target_unresolved_reason"), (
                "an unlinked counter is a measured fact — the reason must "
                "be recorded, not silent"
            )


class TestOfferedKeyTravels:
    def test_prompt_carries_the_opaque_keys(self, monkeypatch):
        """The offered targets are prefixed with their unit ids — the model
        answers a key, not a number."""
        state = _units_state()
        captured: dict = {}
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-witness-zero-bill-2968")
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(["arg_1", "arg_2", "arg_3"], captured),
        )
        asyncio.run(_invoke_counter_argument(state.raw_text, _context_for(state)))
        user = captured.get("user", "")
        assert "[arg_1]" in user and "[arg_2]" in user and "[arg_3]" in user

    def test_echoed_key_binds_the_unit(self, monkeypatch):
        """Positive control: the model answers the offered keys verbatim —
        the stored ids are the units' own, BEFORE this fix and after (the
        exact-id branch already resolved them). A fix that stamps every
        target None reddens here."""
        state = _units_state()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-witness-zero-bill-2968")
        monkeypatch.setattr(
            invoke_callables,
            "_guarded_chat_completion",
            _fake_chat_factory(["arg_1", "arg_2", "arg_3"]),
        )
        result = asyncio.run(
            _invoke_counter_argument(state.raw_text, _context_for(state))
        )
        _write_counter_argument_to_state(result, state, {})
        stored = state.counter_arguments
        assert len(stored) == 3
        assert [ca.get("target_arg_id") for ca in stored] == [
            "arg_1",
            "arg_2",
            "arg_3",
        ]
        assert all(not ca.get("target_unresolved_reason") for ca in stored)


class TestWriterMembershipGuard:
    def test_stamped_id_outside_the_run_is_dropped(self):
        """The writer accepts the id only if the run's identified arguments
        know it — an id from another batch is a dangling reference."""
        state = _units_state()
        output = {
            "llm_counter_arguments": [
                {
                    "counter_argument": "Counter X",
                    "strategy_used": "reductio ad absurdum",
                    "target_argument": "arg_99",
                    "target_unit_id": "arg_99",
                    "target_text": "[quality=…] Unit 99 claim",
                }
            ]
        }
        _write_counter_argument_to_state(output, state, {})
        ca = state.counter_arguments[0]
        assert "target_arg_id" not in ca
        assert ca.get("target_unresolved_reason")

    def test_valid_stamped_id_is_kept_with_the_offered_text(self):
        state = _units_state()
        output = {
            "llm_counter_arguments": [
                {
                    "counter_argument": "Counter Y",
                    "strategy_used": "counter-example",
                    "target_argument": "arg_2",
                    "target_unit_id": "arg_2",
                    "target_text": "[quality=50%] Unit 2 answers the figure",
                }
            ]
        }
        _write_counter_argument_to_state(output, state, {})
        ca = state.counter_arguments[0]
        assert ca.get("target_arg_id") == "arg_2"
        assert "Unit 2 answers" in ca["original_argument"]
        assert "target_unresolved_reason" not in ca


class TestResolverRestriction:
    def test_short_needle_never_resolves(self):
        """The needle "1" resolved to the first description containing a
        "1" on main (born red). Short needles resolve to None."""
        state = _units_state()
        assert _resolve_target_arg_id(state, "1") is None
        assert _resolve_target_arg_id(state, "2") is None

    def test_long_unique_needle_still_resolves(self):
        """Wide-net fallacy payloads carry no id; a problematic_quote long
        enough to be unique grounds the link (#1167 D1a) — the restriction
        must not destroy that."""
        state = _units_state()
        quote = "the 15 percent figure omits the baseline"
        assert _resolve_target_arg_id(state, quote) == "arg_2"

    def test_long_ambiguous_needle_resolves_to_none(self):
        state = _units_state()
        state.identified_arguments["arg_4"] = (
            "Unit 4 repeats that the 15 percent figure omits the baseline."
        )
        quote = "the 15 percent figure omits the baseline"
        assert _resolve_target_arg_id(state, quote) is None

    def test_exact_id_still_resolves(self):
        state = _units_state()
        assert _resolve_target_arg_id(state, "arg_3") == "arg_3"
