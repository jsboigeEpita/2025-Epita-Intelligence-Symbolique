"""#2965 (Expected 3) — the Act II thread's letters designate something.

``_actor_letters`` gave each distinct ``arg_ref`` a stable Greek letter so the
narrative thread would stop printing raw ``arg_N`` ids (#2896 (d): the paid run
printed « arg_40 tente de… » into the prose). But the map was built **and never
emitted**: the writer read « l'argument γ » with no line telling it what γ is,
and no way to join it to the movement blocks it also receives.

The legend carries the REFERENT, never the id — the referent may travel, the
identifier may not be printed. Both halves are witnessed here: the letter
becomes joinable, and the block still prints no ``arg_N``.

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


def _legend_lines(block: str) -> List[str]:
    return [ln for ln in block.splitlines() if ln.strip().startswith("•")]


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
        block = _sequence_block(prompt)
        legend = _legend_lines(block)
        assert len(legend) == 3, f"expected one legend line per actor: {legend}"
        for desc in (_DESC_A, _DESC_B, _DESC_C):
            assert any(
                desc in ln for ln in legend
            ), f"no legend line carries this unit's referent: {desc[:40]!r}"

    def test_legend_repeats_the_description_the_writer_already_read(self) -> None:
        """The join must be to the SAME capped description the movement blocks
        carry — a second, differently-truncated copy would join to nothing."""
        ev = build_act2_evidence(
            _state([_entry("arg_1", 40), _entry("arg_2", 5), _entry("arg_3", 70)])
        )
        block = _sequence_block(build_act2_prompt(ev))
        by_id = {a.arg_id: a.description for m in ev.movements for a in m.arguments}
        for arg_id in ("arg_1", "arg_2", "arg_3"):
            assert any(by_id[arg_id] in ln for ln in _legend_lines(block)), arg_id

    def test_letters_are_distinct_and_all_appear_in_the_legend(self) -> None:
        block = _sequence_block(self._prompt())
        letters = set(re.findall(r"l'argument (\S) —", block))
        legend_letters = set(re.findall(r"l'argument (\S) :", block))
        assert len(letters) == 3
        assert legend_letters == letters
        # one letter per distinct referent: assert-then-retract by ONE argument
        # stays readable as one actor
        moves = [_entry("arg_1", 10), _entry("arg_1", 90, "retract")]
        block2 = _sequence_block(build_act2_prompt(build_act2_evidence(_state(moves))))
        assert len(set(re.findall(r"l'argument (\S) —", block2))) == 1
        assert len(_legend_lines(block2)) == 1


class TestOpacityIsStillHeld:
    """#2896 (d) stays green: the referent travels, the id is not printed."""

    def test_legend_prints_no_raw_arg_id(self) -> None:
        block = _sequence_block(
            build_act2_prompt(
                build_act2_evidence(_state([_entry("arg_1", 40), _entry("arg_2", 5)]))
            )
        )
        assert not re.search(r"arg_\d+", block), block

    def test_unresolved_referent_says_so_instead_of_borrowing_a_text(self) -> None:
        """A move's referent is often a PHASE (``reacts_to=["extract"]``), not a
        unit: no argument carries it, so the legend must not hand the writer a
        text it cannot ground."""
        state = _state([_entry("extract", 40), _entry("arg_1", 5)])
        block = _sequence_block(build_act2_prompt(build_act2_evidence(state)))
        legend = _legend_lines(block)
        assert len(legend) == 2
        unresolved = [ln for ln in legend if "aucun argument identifié" in ln]
        assert len(unresolved) == 1, legend
        assert "extract" not in block, "the referent's raw name is not corpus text"
        # and the resolved one still carries its referent
        assert any(_DESC_A in ln for ln in legend)


class TestTruncationAndAbsence:
    def test_a_long_unit_is_capped_in_the_legend(self) -> None:
        """The legend is a second render of a capped field, not an uncapped
        one: an untruncated copy here would re-inflate the prompt the movement
        blocks were capped to protect."""
        desc = _DESC_LONG
        state = _state([_entry("arg_9", 10)], args={"arg_9": desc})
        ev = build_act2_evidence(state)
        block = _sequence_block(build_act2_prompt(ev))
        legend = _legend_lines(block)
        assert len(legend) == 1
        carried = next(
            a.description
            for m in ev.movements
            for a in m.arguments
            if a.arg_id == "arg_9"
        )
        assert len(carried) < len(desc), "the movement block is itself uncapped"
        assert legend[0] == f"    • l'argument α : {carried}"
        assert len(block) < len(desc), "the cap did not reach the sequence block"

    def test_no_letters_no_legend(self) -> None:
        """Honest absence: moves with no referent render no actor and no
        legend — never an empty scaffold."""
        state = _state([dict(_entry("", 10), reacts_to=[])])
        prompt = build_act2_prompt(build_act2_evidence(state))
        block = _sequence_block(prompt)
        assert "coup non référencé" in block
        assert _legend_lines(block) == []
