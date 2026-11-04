"""#3395 (acts slice) — Acts II and III receive the first reading's moves.

The issue's ask 2 names three writers: the synthesis briefing (delivered with
the producer, #3406) and **Acts II–III**. This file holds the acts' witnesses.

The contract, same as the synthesis briefing's:

- the moves reach the act writer's PROMPT as their own labelled section —
  LECTURE PREMIÈRE, gestures of the TEXT, never a lens's verdict;
- the wording comes from the ONE producer (``first_reading_note``) — the acts
  do not re-render the moves in their own vocabulary;
- a record without moves states the absence in the prompt (the writer knows
  "nothing to say" from "nobody read the document");
- a state that carries no record at all (a bare double) omits the section
  entirely — a producer's vocabulary never enters a context that has none.

Born-red: the ``first_reading`` evidence field does not exist on the pre-fix
tree, so every witness here fails for its own reason (AttributeError on the
evidence field, or the section absent from the prompt).
"""

from types import SimpleNamespace

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_FILLER = "filler text for the witness, no corpus content."
_QUOTE = "La concession centrale du texte, citee verbatim."


def _state_with_moves() -> UnifiedAnalysisState:
    """A production-shaped state whose first reading recorded two moves."""
    state = UnifiedAnalysisState(_FILLER)
    state.defining_moves = {
        "moves": [
            {
                "kind": "thesis",
                "reading": "La these tient la concession pour la retourner.",
                "quote": _QUOTE,
                "offset": 12,
                "basis": "first_reading",
            },
            {
                "kind": "device",
                "reading": "La metaphore centrale structure tout le discours.",
                "quote": "Une metaphore ouvriere porte l'argument entier.",
                "offset": 48,
                "basis": "first_reading",
            },
        ],
        "dropped_quotes": 1,
        "status": "ok",
        "error": "",
        "read_scope": {"whole_document": True, "offset": 0, "window": len(_FILLER)},
        "basis": "first_reading",
    }
    return state


def _state_without_moves(status: str = "no_llm") -> UnifiedAnalysisState:
    state = UnifiedAnalysisState(_FILLER)
    state.defining_moves = {
        "moves": [],
        "dropped_quotes": 0,
        "status": status,
        "error": "",
        "read_scope": {"whole_document": True, "offset": 0, "window": len(_FILLER)},
        "basis": "first_reading",
    }
    return state


class TestAct2ReceivesTheMoves:
    def test_the_prompt_carries_the_labelled_moves_section(self):
        prompt = build_act2_prompt(build_act2_evidence(_state_with_moves()))
        # The label first: a first-reading line never reads as a lens's verdict.
        assert "LECTURE PREMIÈRE" in prompt
        assert "GESTES DU TEXTE" in prompt
        # The verbatim quote is on the line, with its position.
        assert _QUOTE in prompt
        assert "position 12" in prompt

    def test_the_block_is_the_one_producers_wording(self):
        from argumentation_analysis.agents.core.reading import first_reading_note

        state = _state_with_moves()
        evidence = build_act2_evidence(state)
        assert evidence.first_reading == first_reading_note(state)

    def test_the_kind_prints_in_french(self):
        prompt = build_act2_prompt(build_act2_evidence(_state_with_moves()))
        # The label leads the move's own line ("thèse : <reading>") — the
        # prompt's standing "thèse → soutiens" thread vocabulary is not this.
        assert "thèse : La these tient la concession" in prompt
        assert "procédé : La metaphore centrale" in prompt
        # The English key stays in the state; the reader sees French.
        assert "- thesis" not in prompt

    def test_the_dropped_quotes_are_counted_on_the_block(self):
        prompt = build_act2_prompt(build_act2_evidence(_state_with_moves()))
        assert "1 geste(s) écarté(s)" in prompt

    def test_a_record_without_moves_states_the_absence(self):
        prompt = build_act2_prompt(build_act2_evidence(_state_without_moves()))
        assert "LECTURE PREMIÈRE" in prompt
        assert "non enregistrée" in prompt

    def test_a_state_without_the_record_omits_the_section(self):
        # A bare double that never ran a first reading path: no producer
        # vocabulary may enter its prompt (#3395's honest-absence contract).
        state = SimpleNamespace()
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "LECTURE PREMIÈRE" not in prompt


class TestAct3ReceivesTheMoves:
    def test_the_prompt_carries_the_labelled_moves_section(self):
        prompt = build_act3_prompt(build_act3_evidence(_state_with_moves()))
        assert "LECTURE PREMIÈRE" in prompt
        assert "GESTES DU TEXTE" in prompt
        assert _QUOTE in prompt
        assert "position 12" in prompt

    def test_the_block_is_the_one_producers_wording(self):
        from argumentation_analysis.agents.core.reading import first_reading_note

        state = _state_with_moves()
        evidence = build_act3_evidence(state)
        assert evidence.first_reading == first_reading_note(state)

    def test_a_record_without_moves_states_the_absence(self):
        prompt = build_act3_prompt(build_act3_evidence(_state_without_moves()))
        assert "LECTURE PREMIÈRE" in prompt
        assert "non enregistrée" in prompt

    def test_a_state_without_the_record_omits_the_section(self):
        state = SimpleNamespace()
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert "LECTURE PREMIÈRE" not in prompt
