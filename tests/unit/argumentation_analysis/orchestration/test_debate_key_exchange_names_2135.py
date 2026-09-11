"""#2135 — the debate writer must read the keys the LLM prompt actually asks for.

The producer contract is fixed by the prompt (``invoke_callables.py:1670``):
each key exchange arrives as ``{"agent_a_point", "agent_b_rebuttal",
"judge_note"}``. The writer used to read ``point``/``rebuttal`` — keys no
producer emits — so every exchange landed empty, unclassifiable, and Act II
skipped it (``act2_narrative_plugin._collect_debate`` drops exchanges with no
point AND no rebuttal).

These tests feed the writer the PROMPT schema and require the exchange to
survive the whole chain: stored, scheme-grounded, and collected by Act II.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

from argumentation_analysis.orchestration.state_writers import _write_debate_to_state

# "expert" + "domaine" is a lexical signature of the expert_opinion scheme
# (_SCHEME_KEYWORDS, argumentation_schemes.py) — deterministic, no LLM.
PROMPT_SHAPED_EXCHANGE: Dict[str, Any] = {
    "agent_a_point": "L'expert du domaine affirme que la réforme est nécessaire",
    "agent_b_rebuttal": "L'expert évoque un autre domaine, hors sujet",
    "judge_note": "Rebuttal partiellement valide",
}


class _RecordingState:
    """Minimal state double: records what the writer stores."""

    def __init__(self) -> None:
        self.debate_transcripts: List[Dict[str, Any]] = []

    def add_debate_transcript(self, topic: str, exchanges: List[Dict[str, Any]], winner=None) -> str:
        self.debate_transcripts.append(
            {"id": f"debate_{len(self.debate_transcripts)}", "topic": topic,
             "exchanges": exchanges, "winner": winner}
        )
        return self.debate_transcripts[-1]["id"]


def _prompt_shaped_output() -> Dict[str, Any]:
    return {
        "winner": "Agent A",
        "llm_debate_assessment": {
            "key_exchanges": [dict(PROMPT_SHAPED_EXCHANGE)],
            "new_insights": [],
        },
    }


class TestWriterReadsThePromptSchema:
    def test_point_and_rebuttal_come_from_the_prompt_keys(self):
        state = _RecordingState()
        _write_debate_to_state(_prompt_shaped_output(), state, {"input_data": "réforme"})
        stored = state.debate_transcripts[0]["exchanges"][0]
        assert stored["point"] == PROMPT_SHAPED_EXCHANGE["agent_a_point"]
        assert stored["rebuttal"] == PROMPT_SHAPED_EXCHANGE["agent_b_rebuttal"]

    def test_scheme_is_grounded_when_the_text_classifies(self):
        state = _RecordingState()
        _write_debate_to_state(_prompt_shaped_output(), state, {"input_data": "réforme"})
        stored = state.debate_transcripts[0]["exchanges"][0]
        # classify_scheme fires on "expert ... domaine" (expert_opinion).
        assert stored.get("scheme") is not None
        assert stored.get("scheme_key") == "expert_opinion"
        assert stored.get("critical_question")

    def test_old_keys_are_no_longer_read(self):
        """The writer must not honour keys no producer emits — reading both
        would keep the dead contract alive next to the live one (#2135)."""
        state = _RecordingState()
        output = {
            "llm_debate_assessment": {
                "key_exchanges": [
                    {"point": "fabricated by a test", "rebuttal": "same"}
                ]
            }
        }
        _write_debate_to_state(output, state, {"input_data": "x"})
        stored = state.debate_transcripts[0]["exchanges"][0]
        assert stored["point"] == ""
        assert stored["rebuttal"] == ""


class TestAct2ReceivesTheExchange:
    def test_collect_debate_is_not_empty_after_write(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_debate,
        )

        state = _RecordingState()
        _write_debate_to_state(_prompt_shaped_output(), state, {"input_data": "réforme"})
        collected = _collect_debate(state)
        assert len(collected) == 1
        assert collected[0].point == PROMPT_SHAPED_EXCHANGE["agent_a_point"]
        assert collected[0].scheme is not None

    def test_collect_debate_empty_when_writer_was_never_fixed(self):
        """Control: an all-empty exchange (what the bug produced) is skipped
        downstream — the assertion above therefore measures a real chain, not
        a lenient collector."""
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_debate,
        )

        state = SimpleNamespace(
            debate_transcripts=[
                {"exchanges": [{"point": "", "rebuttal": ""}]}
            ]
        )
        assert _collect_debate(state) == []
