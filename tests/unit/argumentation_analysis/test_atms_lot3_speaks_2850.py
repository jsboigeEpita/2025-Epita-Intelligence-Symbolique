"""#2850 lot 3 (dispatch R1094) — the atms and governance caps speak.

Measured pool (R1089 census, remaining after batches 1-2): ``_invoke_atms``
5 rows (spectacular only) + the governance ``raw_fallacies[:5]`` context row.
The family also counts the 3 ``_generate_hypotheses`` head slices (same
phase, same payload) — this lot leaves no atms-family row silent.

Shape (b), the batch-1 rule: the caps stay (claims/fallacies are produced
sub-populations, not the argument population — stratifying them would change
what the network reads with no population to stratify over), and the drops
are said twice: k of N on the phase payload (programmatic readers) AND the
atms trace summary (read by deep-synthesis's Section 5 and the
text_sequence restitution). The governance deliberation PROMPT stays
byte-identical — the five named fallacy types are exactly what it always
named; the disclosure lands on the payload, never inside the LLM input
(zero cassette drift, measured: 0/677 cassettes carry any atms/deep-synthesis
surface; positive control ``premises``=38).

Born red on ``e373efbdf`` (main): every payload key below is absent and the
atms phase writes no trace entry at all.
"""

import asyncio
from unittest.mock import MagicMock, patch

from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# The window (extraction) and the population (state) are DELIBERATELY
# disjoint — a witness whose two sources coincide cannot see the swap
# (same fixture discipline as #3030/#3031/#3036).
_WINDOW = [f"window claim number {i} about policy" for i in range(6)]
_POP = {
    f"pop_{i + 1}": f"population unit {i + 1} anchored in the corpus" for i in range(12)
}


def _populated_state() -> UnifiedAnalysisState:
    """A state whose merged population is the 12 identified arguments."""
    raw = " ".join(f"Sentence {i} of the corpus carries one unit." for i in range(40))
    state = UnifiedAnalysisState(raw)
    state.identified_arguments = dict(_POP)
    span = len(raw) // len(_POP)
    state.argument_provenance = {
        pop_id: {"producer": "extract", "offset": i * span}
        for i, pop_id in enumerate(_POP)
    }
    return state


def _claims(n: int) -> list:
    return [{"text": f"measured claim number {i}"} for i in range(n)]


def _fallacies(n: int) -> list:
    return [{"type": f"fallacy_{i}", "target_argument": "pop_1"} for i in range(n)]


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestAtmsSubPopulationCapsAreDisclosed:
    """The atms caps stay, but the payload and the trace summary say k of N."""

    def test_payload_and_trace_name_the_drops(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_atms,
        )

        state = _populated_state()
        ctx = {
            "_state_object": state,
            "source_metadata": {"opaque_id": "corpus_witness"},
            "phase_extract_output": {
                "arguments": [{"text": w} for w in _WINDOW],
                "claims": _claims(9),
            },
            "phase_hierarchical_fallacy_output": {"fallacies": _fallacies(9)},
        }
        result = _run(_invoke_atms(state.raw_text, ctx))

        assert result["claims_considered"] == 4
        assert result["claims_total"] == 9
        assert result["fallacies_considered"] == 4
        assert result["fallacies_total"] == 9
        # _generate_hypotheses' own head over the same detections population
        assert result["hypothesis_fallacy_targets_considered"] == 6
        assert result["hypothesis_fallacy_targets_total"] == 9

        atms_trace = [t for t in state.analysis_trace if t.get("phase") == "atms"]
        assert atms_trace, "atms trace entry missing"
        summary = atms_trace[-1]["summary"]
        assert "4 de 9 claims" in summary
        assert "4 de 9 sophismes" in summary
        assert "6 de 9 cibles" in summary


class TestAtmsSentenceFallbackNamesItsDrop:
    """The assumption-from-sentences fallback says k of N too."""

    def test_sentence_fallback_is_recorded(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_atms,
        )

        text = (
            ". ".join(
                f"Sentence number {i} is long enough to be counted here"
                for i in range(12)
            )
            + "."
        )
        state = UnifiedAnalysisState(text)
        ctx = {
            "_state_object": state,
            "phase_extract_output": {"arguments": [], "claims": []},
        }
        result = _run(_invoke_atms(text, ctx))

        assert result["assumptions_from_sentences"] == 6
        assert result["sentences_total"] == 12
        atms_trace = [t for t in state.analysis_trace if t.get("phase") == "atms"]
        assert atms_trace, "atms trace entry missing"
        assert "6 de 12 phrases" in atms_trace[-1]["summary"]


class TestGovernanceFallacyTypesSpeak:
    """The governance deliberation context names at most 5 fallacy types —
    the cap stays (the prompt must stay byte-identical), the payload says
    k of N."""

    def test_payload_names_k_of_n_types(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_governance,
        )

        state = _populated_state()
        ctx = {
            "_state_object": state,
            "source_metadata": {"opaque_id": "corpus_witness"},
            "phase_extract_output": {"arguments": [{"text": w} for w in _WINDOW]},
            "phase_hierarchical_fallacy_output": {"fallacies": _fallacies(9)},
        }
        client = MagicMock()
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = '{"recommended_method": "majority"}'
        client.chat.completions.create = MagicMock(return_value=resp)
        with patch("openai.AsyncOpenAI", return_value=client), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}
        ):
            result = _run(_invoke_governance(state.raw_text, ctx))

        assert result["fallacy_types_considered"] == 5
        assert result["fallacy_types_total"] == 9
        # The prompt itself must not carry the disclosure (cassette-key
        # stability): the five types it named are the first five, joined
        # exactly as before.
        prompt = client.chat.completions.create.call_args.kwargs.get("messages", "")
        prompt_str = str(prompt)
        assert "fallacy_0" in prompt_str and "fallacy_4" in prompt_str
        assert "fallacy_5" not in prompt_str
