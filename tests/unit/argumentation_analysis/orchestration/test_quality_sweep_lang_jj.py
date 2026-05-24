"""Tests for the conversational quality sweep + language-aware extraction (Track JJ #699).

Two collaborative-path blind spots, both verified here with the LLM mocked away
(no real API, no JVM):

  1. **Quality = 0 on the conversational path.** The conversational ``QualityAgent``
     depends on the agent turn budget; when it runs out the dialogue emits 0 quality
     scores, so some corpora end with quality = 0 (path-dependent, non-deterministic).
     ``_run_quality_sweep_from_state`` mirrors the Dung/modal/ASPIC/PL/FOL
     post-processors: it reuses the robust *sequential* 9-virtue
     ``_invoke_quality_evaluator`` over every ``identified_argument`` and writes the
     scores back via ``state.add_quality_score`` — deterministic, gap-filling only.

  2. **Non-English under-extraction.** The English-only extraction prompt gave the
     model no cue to analyze in the source language, so dense non-English text
     under-recalled (corpus B/DE ~2 args vs ~7/5 for A/C-EN), starving every
     downstream layer. ``_invoke_fact_extraction`` now detects the language (reusing
     the tested heuristic) and injects a language-aware instruction for non-English
     text. English text is left unchanged.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import argumentation_analysis.orchestration.invoke_callables as mod

# German sentence rich in _detect_language DE markers (der/die/das/und/ist/ein/mit).
_DE_TEXT = (
    "Der Staat ist die Grundlage der Ordnung und das Volk muss mit Vernunft "
    "handeln. Eine starke Wirtschaft ist der Schlüssel und die Politik wird "
    "durch klare Regeln bestimmt. Wir sind für den Fortschritt. " * 4
)
_EN_TEXT = (
    "The state is the basis of order and the people must act with reason. A "
    "strong economy is the key and policy is determined by clear rules. We are "
    "for progress and the future of the nation depends on it. " * 4
)


class _FakeState:
    """Minimal stand-in for UnifiedAnalysisState used by the quality sweep."""

    def __init__(self, identified_arguments, prefilled=None):
        self.identified_arguments = identified_arguments
        self.argument_quality_scores = dict(prefilled or {})

    def add_quality_score(self, arg_id, scores, overall, llm_assessment=None):
        self.argument_quality_scores[arg_id] = {
            "scores": scores,
            "overall": overall,
            "llm_assessment": llm_assessment,
        }


def _canned_quality_output(arg_ids):
    """Shape mirrors _invoke_quality_evaluator's per_argument_scores return."""
    return {
        "per_argument_scores": {
            aid: {
                "note_finale": 0.6,
                "scores_par_vertu": {"clarity": 0.7, "coherence": 0.5},
                "llm_assessment": None,
            }
            for aid in arg_ids
        },
        "aggregate_score": 0.6,
        "arguments_evaluated": len(arg_ids),
    }


class TestQualitySweepFromState:
    """#699 defect 1: deterministic quality sweep fills the conversational gap."""

    async def test_dict_arguments_get_scored(self):
        state = _FakeState({"a1": "Argument one text.", "a2": "Argument two text."})
        with patch.object(
            mod,
            "_invoke_quality_evaluator",
            new=AsyncMock(return_value=_canned_quality_output(["arg_1", "arg_2"])),
        ):
            out = await mod._run_quality_sweep_from_state(state)
        assert out["added"] == 2
        assert len(state.argument_quality_scores) == 2

    async def test_list_of_dicts_arguments_get_scored(self):
        state = _FakeState(
            [{"text": "Argument one text."}, {"description": "Argument two text."}]
        )
        with patch.object(
            mod,
            "_invoke_quality_evaluator",
            new=AsyncMock(return_value=_canned_quality_output(["arg_1", "arg_2"])),
        ):
            out = await mod._run_quality_sweep_from_state(state)
        assert out["added"] == 2

    async def test_already_scored_ids_are_skipped(self):
        # arg_1 already present → only arg_2 is newly added (gap-filling, no overwrite).
        state = _FakeState(
            {"a1": "one", "a2": "two"},
            prefilled={"arg_1": {"scores": {}, "overall": 0.9}},
        )
        with patch.object(
            mod,
            "_invoke_quality_evaluator",
            new=AsyncMock(return_value=_canned_quality_output(["arg_1", "arg_2"])),
        ):
            out = await mod._run_quality_sweep_from_state(state)
        assert out["added"] == 1
        # Pre-existing agent score untouched.
        assert state.argument_quality_scores["arg_1"]["overall"] == 0.9

    async def test_no_arguments_is_noop(self):
        state = _FakeState({})
        with patch.object(mod, "_invoke_quality_evaluator", new=AsyncMock()) as ev:
            out = await mod._run_quality_sweep_from_state(state)
        assert out["added"] == 0
        ev.assert_not_called()

    async def test_state_without_add_method_is_noop(self):
        bare = SimpleNamespace(identified_arguments={"a1": "one"})
        with patch.object(mod, "_invoke_quality_evaluator", new=AsyncMock()) as ev:
            out = await mod._run_quality_sweep_from_state(bare)
        assert out["added"] == 0
        ev.assert_not_called()


def _make_fake_client(capture):
    """Fake OpenAI client whose create() records the system prompt then returns JSON."""

    async def _create(*args, **kwargs):
        capture["messages"] = kwargs.get("messages", [])
        msg = SimpleNamespace(
            content='{"arguments": [], "claims": [], "summary": "ok"}'
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    completions = SimpleNamespace(create=_create)
    chat = SimpleNamespace(completions=completions)
    return SimpleNamespace(chat=chat)


class TestLanguageAwareExtraction:
    """#699 defect 2: non-English extraction gets a language-aware instruction."""

    async def _run(self, text):
        capture = {}
        client = _make_fake_client(capture)
        with patch.object(mod, "_get_openai_client", return_value=(client, "model-x")):
            await mod._invoke_fact_extraction(text, {})
        system = next(
            (m["content"] for m in capture["messages"] if m["role"] == "system"), ""
        )
        return system

    async def test_german_text_injects_language_clause(self):
        system = await self._run(_DE_TEXT)
        assert "German" in system
        assert "original language" in system
        # The JSON contract still follows the clause.
        assert "Respond with ONLY a JSON object" in system

    async def test_english_text_has_no_language_clause(self):
        system = await self._run(_EN_TEXT)
        assert "German" not in system
        assert "original language" not in system
