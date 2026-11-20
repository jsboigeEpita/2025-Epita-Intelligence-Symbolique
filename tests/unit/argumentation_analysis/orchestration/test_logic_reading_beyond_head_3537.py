"""#3537 — the logic lenses read the WHOLE document, in k calls that tile it.

Measured before this fix: on a document longer than the window,
``_invoke_propositional_logic``'s atom inventory and ``_invoke_fol_reasoning``
read only the first 4,000 characters (``LOGIC_READING_WINDOW``, through
``select_reading_head`` → offset 0 on ordinary prose). A 60,000-character
document's last two thirds never reached the lenses, and ``pl_metrics``
said ``reading_window_chars == 4000``.

The fix (issue ask 1, coordinator decision: tiled in full, no cap on k)
keeps the head-first order — ``LOGIC_READING_WINDOW`` is NOT raised — and
tiles the document at the measured per-call capacity (``WHOLE_TEXT_CALL_CAPACITY``
= 6,016) from the selector's offset, exactly as #2850 lot 10 does for fact
extraction. Below one capacity the plan is the single head call: the prompt
is byte-identical, no cassette key moves (ask 3).

Witnesses (all free: no key, no network, no corpus — loopback fake):

- the atom-inventory prompts together hold all three thirds' markers
  (born red on main: only the first third's marker appears);
- the FOL signature prompts likewise;
- the reading record and ``pl_metrics``/``fol_metrics`` say how much was
  read: k calls and the union of characters, next to k of N;
- a 3,500-character document still costs ONE call with today's entry
  (control — green before and after);
- mutation: the tiling disabled (``chunked_reading_offsets`` pinned to the
  head only), the witness's own assertion goes red.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.core.reading_window import WHOLE_TEXT_CALL_CAPACITY
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# ---------------------------------------------------------------------------
# Synthetic, corpus-free: three exact thirds, each opening on its marker.
# ---------------------------------------------------------------------------

_MARK_1 = "Repere du premier tiers : le marche ouvre tot sans bruit."
_MARK_2 = "Repere du deuxieme tiers : le conseil vote le budget communal."
_MARK_3 = "Repere du troisieme tiers : la riviere quitte lentement son lit."
_PAD = "Cette phrase de remplissage ne porte aucune information du temoin. "
_THIRD = 20_000


def _third(marker: str) -> str:
    body = (_PAD * (_THIRD // len(_PAD) + 1))[: _THIRD - len(marker)]
    return marker + body


_TEXT = _third(_MARK_1) + _third(_MARK_2) + _third(_MARK_3)
_SHORT_TEXT = _third(_MARK_1)[:3500]

_PL_ATOM_PROMPT = "atomic propositions (basic facts)"
_FOL_SIG_PROMPT = "first-order logic signature"

_PROMPTS: List[str] = []


def _reply_for(prompt: str) -> Any:
    if _PL_ATOM_PROMPT in prompt:
        content = json.dumps({"propositions": ["fait_general"]})
    elif _FOL_SIG_PROMPT in prompt:
        content = json.dumps(
            {
                "sorts": {"Chose": ["alpha", "beta"]},
                "predicates": {"Pred": ["Chose"]},
                "constants": {"alpha": "premier", "beta": "second"},
            }
        )
    else:
        content = json.dumps({"formulas": []})
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


async def _fake_llm_call(client: Any, **kwargs: Any) -> Any:
    # The last message is the user turn on both doors (pass-1 sends a single
    # user message; NL-to-logic sends system then user).
    prompt = kwargs["messages"][-1]["content"]
    _PROMPTS.append(prompt)
    return _reply_for(prompt)


async def _fake_nl_translation(client: Any, **kwargs: Any) -> Any:
    """Neutralise the NL-to-logic door without recording anything.

    Measured on main (probe, 2026-11-20): when pass 1/2 produce no formula,
    PL falls back to ``NLToLogicTranslator``, which calls
    ``nl_to_logic.cached_raw_chat_completion`` DIRECTLY — bypassing
    ``_guarded_chat_completion`` — with 2 attempts per target. The first
    version of this witness patched only the guarded funnel and made
    6 live 401 requests (3 targets x 2 retries), which the hermeticity
    guard (#3069) caught. Same door on the FOL side.
    """
    return _reply_for("")


def _wire_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    import argumentation_analysis.services.nl_to_logic as nl2l

    monkeypatch.setattr(ic, "_get_openai_client", lambda: (object(), "loopback-model"))
    monkeypatch.setattr(ic, "_guarded_chat_completion", _fake_llm_call)
    monkeypatch.setattr(nl2l, "cached_raw_chat_completion", _fake_nl_translation)


def _state(text: str) -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("logic-reading-beyond-head-3537 synthetic probe")
    state.raw_text = text
    state.identified_arguments = {
        "arg_1": text[100:220],
        "arg_2": text[20_100:20_220],
        "arg_3": text[40_100:40_220],
    }
    return state


def _calls_containing(fragment: str) -> List[str]:
    return [p for p in _PROMPTS if fragment in p]


def _all_hold(prompts: List[str], marks: List[str]) -> List[str]:
    joined = "\n".join(prompts)
    return [m for m in marks if m not in joined]


class TestPropositionalLogicReadsTheWholeDocument:
    async def test_the_atom_inventory_sees_all_three_thirds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state(_TEXT)

        await ic._invoke_propositional_logic(_TEXT, {"_state_object": state})

        atom_prompts = _calls_containing(_PL_ATOM_PROMPT)
        assert atom_prompts, "no atom-inventory prompt was sent"
        missing = _all_hold(atom_prompts, [_MARK_1, _MARK_2, _MARK_3])
        assert not missing, (
            f"the atom inventory never read {missing!r} — the lens still "
            f"reads the head only (#3537)"
        )

    async def test_the_record_and_metrics_say_how_much_was_read(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state(_TEXT)

        out = await ic._invoke_propositional_logic(_TEXT, {"_state_object": state})

        metrics = out.get("pl_metrics", {})
        expected_k = -(-len(_TEXT) // WHOLE_TEXT_CALL_CAPACITY)
        assert metrics.get("reading_window_chars") == len(_TEXT), (
            f"pl_metrics still reports {metrics.get('reading_window_chars')!r} "
            f"of {len(_TEXT)} — the k of N does not cover the text"
        )
        assert metrics.get("reading_calls") == expected_k

        entry = state.reading_window_status.get("propositional_logic", {})
        assert entry.get("windows") == expected_k
        assert entry.get("chars_read") == len(_TEXT)


class TestFolReadsTheWholeDocument:
    async def test_the_signature_sees_all_three_thirds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state(_TEXT)

        await ic._invoke_fol_reasoning(_TEXT, {"_state_object": state})

        sig_prompts = _calls_containing(_FOL_SIG_PROMPT)
        assert sig_prompts, "no FOL signature prompt was sent"
        missing = _all_hold(sig_prompts, [_MARK_1, _MARK_2, _MARK_3])
        assert not missing, (
            f"the FOL reading never saw {missing!r} — the lens still reads "
            f"the head only (#3537)"
        )

    async def test_the_fol_record_and_metrics_say_how_much_was_read(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state(_TEXT)

        out = await ic._invoke_fol_reasoning(_TEXT, {"_state_object": state})

        metrics = out.get("fol_metrics", {})
        expected_k = -(-len(_TEXT) // WHOLE_TEXT_CALL_CAPACITY)
        assert metrics.get("reading_window_chars") == len(_TEXT)
        assert metrics.get("reading_calls") == expected_k

        entry = state.reading_window_status.get("fol_reasoning", {})
        assert entry.get("windows") == expected_k
        assert entry.get("chars_read") == len(_TEXT)


class TestShortDocumentUnchanged:
    """Ask 3: at or under one call's capacity, today's prompt and entry."""

    async def test_a_short_document_still_costs_one_call(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state(_SHORT_TEXT)

        out = await ic._invoke_propositional_logic(
            _SHORT_TEXT, {"_state_object": state}
        )

        atom_prompts = _calls_containing(_PL_ATOM_PROMPT)
        assert len(atom_prompts) == 1, (
            f"{len(atom_prompts)} atom-inventory prompts on a short document — "
            f"the single-call path must stay single"
        )
        metrics = out.get("pl_metrics", {})
        assert metrics.get("reading_window_chars") == len(_SHORT_TEXT)
        entry = state.reading_window_status.get("propositional_logic", {})
        assert (
            "windows" not in entry
        ), "a one-call read must keep today's entry shape (#2850 lot 10)"


class TestMutationControl:
    async def test_tiling_disabled_goes_red(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mutation: the plan pinned to the head only — the witness reddens."""
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        monkeypatch.setattr(
            ic,
            "chunked_reading_offsets",
            lambda length, capacity, start=0: [start],
        )
        state = _state(_TEXT)

        await ic._invoke_propositional_logic(_TEXT, {"_state_object": state})

        atom_prompts = _calls_containing(_PL_ATOM_PROMPT)
        missing = _all_hold(atom_prompts, [_MARK_1, _MARK_2, _MARK_3])
        assert missing, (
            "the witness would stay green with the tiling disabled — it does "
            "not depend on the fix"
        )
