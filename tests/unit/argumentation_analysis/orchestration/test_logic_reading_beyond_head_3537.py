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
- **per-window yield** (R1199 decision): ``reading_yields`` carries, plan
  order, the atoms (PL) / predicates (FOL) each call RETURNED — ``None``
  for a call that never answered — so a panel cycle reads what the extra
  windows bring from the state, not from an estimate;
- a 3,500-character document still costs ONE call with today's entry
  (control — green before and after);
- mutation: the tiling disabled (``chunked_reading_offsets`` pinned to the
  head only), the witness's own assertion goes red.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.core.reading_window import (
    WHOLE_TEXT_CALL_CAPACITY,
    chunked_reading_offsets,
)
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

# R1199 per-window yield — the fake answers a count DERIVED from the window
# it was shown, so the witness can tell one window's slot from another's.
_YIELD_BY_MARKER = {_MARK_1: 1, _MARK_2: 2, _MARK_3: 3}
# Set by the failure-semantics test: a prompt carrying this marker makes the
# call FAIL, as a stalled or errored window does.
_RAISE_MARKER: Optional[str] = None


def _yield_of(text: str) -> int:
    return sum(count for mark, count in _YIELD_BY_MARKER.items() if mark in text)


def _reply_for(prompt: str) -> Any:
    if _PL_ATOM_PROMPT in prompt:
        count = _yield_of(prompt)
        content = json.dumps(
            {"propositions": [f"atome_fenetre_{i}" for i in range(count)]}
        )
    elif _FOL_SIG_PROMPT in prompt:
        count = _yield_of(prompt)
        content = json.dumps(
            {
                "sorts": {"Chose": ["alpha", "beta"]},
                "predicates": {f"Pred{i}": ["Chose"] for i in range(1, count + 1)},
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
    if _RAISE_MARKER is not None and _RAISE_MARKER in prompt:
        raise RuntimeError("loopback window failure (witness-controlled)")
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
    global _RAISE_MARKER
    _RAISE_MARKER = None
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


class TestPerWindowYield:
    """R1199 decision on #3537 — ``reading_yields`` beside ``reading_calls``.

    ``reading_calls`` says the whole text was SENT; the yields say what each
    window brought BACK, in plan order, one slot per issued call — ``None``
    for a call that never answered (a failed window read nothing; counting
    it as 0 would claim it found no atom when it never looked). RED on main:
    the field does not exist there, so the yields cannot be read at all.
    """

    def _expected_yields(
        self, text: str, none_when: Optional[str] = None
    ) -> List[Optional[int]]:
        """The plan's spans mapped to the count the fake derives from each
        window's own text — the attribution the field must reproduce."""
        spans = [
            (o, min(o + WHOLE_TEXT_CALL_CAPACITY, len(text)))
            for o in chunked_reading_offsets(len(text), WHOLE_TEXT_CALL_CAPACITY)
        ]
        out: List[Optional[int]] = []
        for _lo, _hi in spans:
            window = text[_lo:_hi]
            if none_when is not None and none_when in window:
                out.append(None)
            else:
                out.append(_yield_of(window))
        return out

    async def test_pl_metrics_carry_the_yield_of_each_call(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state(_TEXT)

        out = await ic._invoke_propositional_logic(_TEXT, {"_state_object": state})

        metrics = out.get("pl_metrics", {})
        expected = self._expected_yields(_TEXT)
        assert metrics.get("reading_yields") == expected, (
            f"pl_metrics reading_yields is {metrics.get('reading_yields')!r}, "
            f"expected {expected!r} — a window's slot must hold that window's "
            f"atoms, not another's (#3537 R1199)"
        )
        assert len(metrics.get("reading_yields") or []) == metrics.get("reading_calls")

    async def test_a_window_that_never_answers_yields_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        global _RAISE_MARKER
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        _RAISE_MARKER = _MARK_2
        state = _state(_TEXT)

        out = await ic._invoke_propositional_logic(_TEXT, {"_state_object": state})

        metrics = out.get("pl_metrics", {})
        yields = metrics.get("reading_yields")
        expected = self._expected_yields(_TEXT, none_when=_MARK_2)
        assert yields == expected, (
            f"reading_yields is {yields!r}, expected {expected!r} — a failed "
            f"call must read as None, never as 0 (#3537 R1199)"
        )
        assert None in yields

    async def test_fol_metrics_carry_the_yield_of_each_call(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state(_TEXT)

        out = await ic._invoke_fol_reasoning(_TEXT, {"_state_object": state})

        metrics = out.get("fol_metrics", {})
        expected = self._expected_yields(_TEXT)
        assert metrics.get("reading_yields") == expected, (
            f"fol_metrics reading_yields is {metrics.get('reading_yields')!r}, "
            f"expected {expected!r} — the FOL arm must carry its predicates' "
            f"per-window counts (#3537 R1199)"
        )

    async def test_a_short_document_yields_a_one_slot_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Control (ask 3's shape): one call, one slot — the yields list
        never claims more windows than the plan issued."""
        _PROMPTS.clear()
        _wire_loopback(monkeypatch)
        state = _state(_SHORT_TEXT)

        out = await ic._invoke_propositional_logic(
            _SHORT_TEXT, {"_state_object": state}
        )

        metrics = out.get("pl_metrics", {})
        assert metrics.get("reading_yields") == [1]


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
