"""#2965 → #3296 — the thread's letters designate something, act-wide.

``_actor_letters`` gave each distinct ``arg_ref`` a stable Greek letter so the
narrative thread would stop printing raw ``arg_N`` ids (#2896 (d): the paid run
printed « arg_40 tente de… » into the prose). #2965 added a private legend so
the letter would designate its referent. #3296 generalises both: ONE per-act
letter table at the prompt's assembly seam relabels every block — the thread,
the movements, the rankings — and ONE legend binds each letter to its referent.
The private map is subtracted (two letter vocabularies in one prompt would
collide: the thread's α is not the table's α).

The guarantees #2965 witnessed survive at their new address: the letter
becomes joinable (legend referent), the block prints no ``arg_N``, an
unresolvable referent says so instead of borrowing a text, and the legend
stays capped.

Privacy: synthetic opaque ids and invented French filler only. Deterministic:
no JVM, no LLM, no network.
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any, Dict, List

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)

_SOURCE = 400
_DESC_A = "Première unité : une revendication causale explicite, développée."
_DESC_B = "Deuxième unité : une objection qui contredit la revendication initiale."
_DESC_C = "Troisième unité : une concession partielle qui déplace le débat."
_DESC_LONG = "Quatrième unité : " + ("un développement très long, " * 40)

_LEGEND_HEADING = "LÉGENDE DES DÉSIGNATIONS"


def _entry(arg_ref: str, offset: int, move: str = "assert") -> Dict[str, Any]:
    return {
        "phase": "extract",
        "agent": "FactExtractionAgent",
        "reacts_to": [arg_ref],
        "summary": f"{move} {arg_ref}",
        "timestamp": "2026-10-06T00:00:00Z",
        "move": move,
        "anchor": {"offset": offset, "length": 5},
    }


def _state(
    entries: List[Dict[str, Any]], args: Dict[str, str] | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        analysis_trace=list(entries),
        identified_arguments=(
            args
            if args is not None
            else {"arg_1": _DESC_A, "arg_2": _DESC_B, "arg_3": _DESC_C}
        ),
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        governance_decisions=[],
        debate_transcripts=[],
        raw_text="x" * _SOURCE,
    )


def _sequence_block(prompt: str) -> str:
    m = re.search(r"SÉQUENCE DU TEXTE.*?(?=\n\n)", prompt, re.DOTALL)
    assert m is not None, "prompt carries no sequence block"
    return m.group(0)


def _legend_lines(prompt: str) -> List[str]:
    """The per-act legend's binding lines — ``• <letter> : <referent>``."""
    assert _LEGEND_HEADING in prompt, "prompt carries no per-act legend"
    tail = prompt.split(_LEGEND_HEADING, 1)[1]
    return [ln for ln in tail.splitlines() if ln.strip().startswith("•")]


def _legend_keys(prompt: str) -> set:
    return {
        m.group(1)
        for ln in _legend_lines(prompt)
        for m in [re.match(r"\s*• (\S+) :", ln)]
        if m
    }


class TestLettersBecomeJoinable:
    """The issue's witness: three distinct arg_refs, three joinable letters."""

    def _prompt(self) -> str:
        state = _state(
            [
                _entry("arg_1", 40),
                _entry("arg_2", 5),
                _entry("arg_3", 70),
            ]
        )
        return build_act2_prompt(build_act2_evidence(state))

    def test_every_letter_carries_the_referent_it_designates(self) -> None:
        prompt = self._prompt()
        legend = _legend_lines(prompt)
        assert len(legend) == 3, f"expected one legend line per actor: {legend}"
        for desc in (_DESC_A, _DESC_B, _DESC_C):
            assert any(
                desc in ln for ln in legend
            ), f"no legend line carries this unit's referent: {desc[:40]!r}"

    def test_legend_repeats_the_description_the_writer_already_read(self) -> None:
        """The join must be to the unit the movement blocks describe — the
        legend referent and the movement description are renders of the SAME
        unit text (here short enough that both carry it whole; past the legend
        cap they stay prefix-siblings of the same text, joined on their head)."""
        ev = build_act2_evidence(
            _state([_entry("arg_1", 40), _entry("arg_2", 5), _entry("arg_3", 70)])
        )
        prompt = build_act2_prompt(ev)
        by_id = {a.arg_id: a.description for m in ev.movements for a in m.arguments}
        for arg_id in ("arg_1", "arg_2", "arg_3"):
            assert any(by_id[arg_id] in ln for ln in _legend_lines(prompt)), arg_id

    def test_letters_are_distinct_and_all_appear_in_the_legend(self) -> None:
        prompt = self._prompt()
        block = _sequence_block(prompt)
        letters = set(re.findall(r"l'argument (\S+) —", block))
        assert len(letters) == 3, f"three actors must read as three letters: {letters}"
        # every letter the thread uses, the legend binds — one shared table
        assert letters <= _legend_keys(
            prompt
        ), f"thread letters with no legend binding: {letters - _legend_keys(prompt)}"
        # one letter per distinct referent: assert-then-retract by ONE argument
        # stays readable as one actor
        moves = [_entry("arg_1", 10), _entry("arg_1", 90, "retract")]
        prompt2 = build_act2_prompt(build_act2_evidence(_state(moves)))
        block2 = _sequence_block(prompt2)
        assert len(set(re.findall(r"l'argument (\S+) —", block2))) == 1
        assert "l'argument α" in block2


class TestOpacityIsStillHeld:
    """#2896 (d) stays green: the referent travels, the id is not printed."""

    def test_legend_prints_no_raw_arg_id(self) -> None:
        prompt = build_act2_prompt(
            build_act2_evidence(_state([_entry("arg_1", 40), _entry("arg_2", 5)]))
        )
        assert not re.search(r"arg_\d+", prompt), "a raw id reached the writer"

    def test_unresolved_referent_says_so_instead_of_borrowing_a_text(self) -> None:
        """A move's referent is often a PHASE (``reacts_to=["extract"]``), not a
        unit: no argument carries it, so the line must not hand the writer a
        text it cannot ground — nor print the phase's raw name. The old private
        legend said this in a side line; #3296 says it on the line itself."""
        state = _state([_entry("extract", 40), _entry("arg_1", 5)])
        prompt = build_act2_prompt(build_act2_evidence(state))
        block = _sequence_block(prompt)
        assert "un coup non rattaché à un argument" in block, block
        # the phase name must not reach the thread (« extracteur », the French
        # word, is a different token and lives elsewhere in the prompt)
        assert "extract" not in block, "the referent's raw name is not corpus text"
        assert "l'argument extract" not in block, "a phase must not be an argument"
        # and the resolved one still carries its referent in the legend
        assert any(_DESC_A in ln for ln in _legend_lines(prompt))


class TestTruncationAndAbsence:
    def test_a_long_unit_is_capped_in_the_legend(self) -> None:
        """The legend is a capped render, not an uncapped one: an untruncated
        copy here would re-inflate the prompt the movement blocks were capped
        to protect."""
        desc = _DESC_LONG
        state = _state([_entry("arg_9", 10)], args={"arg_9": desc})
        ev = build_act2_evidence(state)
        prompt = build_act2_prompt(ev)
        carried = ev.unit_texts["arg_9"]
        assert len(carried) < len(desc), "the legend referent is uncapped"
        assert "…" in carried, "the cut is invisible (a bare slice, #2967)"
        assert any(ln.strip() == f"• α : {carried}" for ln in _legend_lines(prompt))

    def test_no_letters_no_legend_lines_in_the_thread(self) -> None:
        """Honest absence: moves with no referent render no actor — and the
        thread block contributes no legend line of its own (the per-act legend
        lists units, and a thread without actors cites none)."""
        state = _state([dict(_entry("", 10), reacts_to=[])])
        prompt = build_act2_prompt(build_act2_evidence(state))
        block = _sequence_block(prompt)
        assert "coup non référencé" in block
        assert "l'argument" not in block, "an unanchored thread invented an actor"
