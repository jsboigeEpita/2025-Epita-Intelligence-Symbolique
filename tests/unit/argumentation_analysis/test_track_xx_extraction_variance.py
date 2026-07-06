"""Tests for Track XX (#680): Extraction run-to-run variance (determinism).

Tests cover:
  1. _get_determinism_params returns empty dict by default
  2. LLM_DETERMINISTIC_MODE=1 enables temperature=0 + seed=42
  3. LLM_TEMPERATURE and LLM_SEED fine-grained overrides
  4. Individual overrides take precedence over shorthand
  5. Invalid values are ignored gracefully
  6. Downstream JSON parsing is deterministic for identical mock input
  7. Extraction metrics are deterministic for identical synthetic state
"""

import json
import os

import pytest


class TestGetDeterminismParams:
    """_get_determinism_params reads env vars correctly."""

    def test_default_returns_empty(self):
        """No env vars set → empty dict (provider defaults apply)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        os.environ.pop("LLM_DETERMINISTIC_MODE", None)
        os.environ.pop("LLM_TEMPERATURE", None)
        os.environ.pop("LLM_SEED", None)
        result = _get_determinism_params()
        assert result == {}

    def test_deterministic_mode_shorthand(self):
        """LLM_DETERMINISTIC_MODE=1 → temperature=0, seed=42."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        os.environ.pop("LLM_TEMPERATURE", None)
        os.environ.pop("LLM_SEED", None)
        os.environ.pop("LLM_FORCE_SAMPLING_PARAMS", None)
        # Use a standard (non-reasoning) model so params are not suppressed
        prev_model = os.environ.get("OPENAI_CHAT_MODEL_ID")
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-4o"
        os.environ["LLM_DETERMINISTIC_MODE"] = "1"
        try:
            result = _get_determinism_params()
            assert result["temperature"] == 0.0
            assert result["seed"] == 42
        finally:
            os.environ.pop("LLM_DETERMINISTIC_MODE", None)
            if prev_model is None:
                os.environ.pop("OPENAI_CHAT_MODEL_ID", None)
            else:
                os.environ["OPENAI_CHAT_MODEL_ID"] = prev_model

    def test_temperature_override(self):
        """LLM_TEMPERATURE=0.5 → temperature=0.5 only."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        os.environ.pop("LLM_DETERMINISTIC_MODE", None)
        os.environ.pop("LLM_SEED", None)
        os.environ.pop("LLM_FORCE_SAMPLING_PARAMS", None)
        prev_model = os.environ.get("OPENAI_CHAT_MODEL_ID")
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-4o"
        os.environ["LLM_TEMPERATURE"] = "0.5"
        try:
            result = _get_determinism_params()
            assert result == {"temperature": 0.5}
        finally:
            os.environ.pop("LLM_TEMPERATURE", None)
            if prev_model is None:
                os.environ.pop("OPENAI_CHAT_MODEL_ID", None)
            else:
                os.environ["OPENAI_CHAT_MODEL_ID"] = prev_model

    def test_seed_override(self):
        """LLM_SEED=123 → seed=123 only."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        os.environ.pop("LLM_DETERMINISTIC_MODE", None)
        os.environ.pop("LLM_TEMPERATURE", None)
        os.environ.pop("LLM_FORCE_SAMPLING_PARAMS", None)
        prev_model = os.environ.get("OPENAI_CHAT_MODEL_ID")
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-4o"
        os.environ["LLM_SEED"] = "123"
        try:
            result = _get_determinism_params()
            assert result == {"seed": 123}
        finally:
            os.environ.pop("LLM_SEED", None)
            if prev_model is None:
                os.environ.pop("OPENAI_CHAT_MODEL_ID", None)
            else:
                os.environ["OPENAI_CHAT_MODEL_ID"] = prev_model

    def test_individual_overrides_take_precedence(self):
        """LLM_TEMPERATURE and LLM_SEED override LLM_DETERMINISTIC_MODE values."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        os.environ.pop("LLM_FORCE_SAMPLING_PARAMS", None)
        prev_model = os.environ.get("OPENAI_CHAT_MODEL_ID")
        os.environ["OPENAI_CHAT_MODEL_ID"] = "gpt-4o"
        os.environ["LLM_DETERMINISTIC_MODE"] = "1"
        os.environ["LLM_TEMPERATURE"] = "0.7"
        os.environ["LLM_SEED"] = "999"
        try:
            result = _get_determinism_params()
            assert result["temperature"] == 0.7
            assert result["seed"] == 999
        finally:
            os.environ.pop("LLM_DETERMINISTIC_MODE", None)
            os.environ.pop("LLM_TEMPERATURE", None)
            os.environ.pop("LLM_SEED", None)
            if prev_model is None:
                os.environ.pop("OPENAI_CHAT_MODEL_ID", None)
            else:
                os.environ["OPENAI_CHAT_MODEL_ID"] = prev_model

    def test_invalid_temperature_ignored(self):
        """Non-numeric LLM_TEMPERATURE is silently skipped."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        os.environ.pop("LLM_DETERMINISTIC_MODE", None)
        os.environ.pop("LLM_SEED", None)
        os.environ["LLM_TEMPERATURE"] = "not_a_number"
        try:
            result = _get_determinism_params()
            assert result == {}
        finally:
            os.environ.pop("LLM_TEMPERATURE", None)

    def test_invalid_seed_ignored(self):
        """Non-integer LLM_SEED is silently skipped."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        os.environ.pop("LLM_DETERMINISTIC_MODE", None)
        os.environ.pop("LLM_TEMPERATURE", None)
        os.environ["LLM_SEED"] = "abc"
        try:
            result = _get_determinism_params()
            assert result == {}
        finally:
            os.environ.pop("LLM_SEED", None)

    def test_empty_deterministic_mode_string_no_effect(self):
        """LLM_DETERMINISTIC_MODE='' is falsy → no effect."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        os.environ.pop("LLM_TEMPERATURE", None)
        os.environ.pop("LLM_SEED", None)
        os.environ["LLM_DETERMINISTIC_MODE"] = ""
        try:
            result = _get_determinism_params()
            assert result == {}
        finally:
            os.environ.pop("LLM_DETERMINISTIC_MODE", None)


class TestJsonParsingDeterminism:
    """Downstream JSON parsing is deterministic for identical input."""

    def test_parse_json_from_llm_deterministic(self):
        """_parse_json_from_llm produces identical output for identical input."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _parse_json_from_llm,
        )

        raw = '```json\n{"arguments": [{"text": "test arg"}], "claims": []}\n```'
        r1 = _parse_json_from_llm(raw)
        r2 = _parse_json_from_llm(raw)
        assert r1 == r2
        assert r1["arguments"][0]["text"] == "test arg"

    def test_normalize_items_deterministic(self):
        """_normalize_items_with_quotes produces identical output for same input."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _normalize_items_with_quotes,
        )

        items = [
            {"text": "arg1", "source_quote": "quote1"},
            "plain_string_arg",
            {"text": "arg2", "content": "fallback"},
        ]
        r1 = _normalize_items_with_quotes(items)
        r2 = _normalize_items_with_quotes(items)
        assert r1 == r2
        assert len(r1) == 3

    def test_fact_extraction_json_parse_deterministic(self):
        """JSON parsing from fact extraction is deterministic."""
        raw = (
            "Some text before\n```json\n"
            '{"arguments": [{"text": "A1"}, {"text": "A2"}], '
            '"claims": [{"text": "C1"}], '
            '"summary": "test summary"}\n'
            "```\nSome text after"
        )
        text_content = raw.strip()
        if "```json" in text_content:
            text_content = text_content.split("```json")[1].split("```")[0]
        start = text_content.find("{")
        end = text_content.rfind("}") + 1
        data = json.loads(text_content[start:end])

        assert len(data["arguments"]) == 2
        assert len(data["claims"]) == 1
        assert data["summary"] == "test summary"


class TestExtractionMetricsDeterminism:
    """Extraction metrics are deterministic for identical synthetic state."""

    def test_quality_aggregation_deterministic(self):
        """_aggregate_virtue_scores produces same result for same input."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _aggregate_virtue_scores,
        )

        per_arg_results = {
            "arg_1": {
                "scores_par_vertu": {
                    "clarity": 7,
                    "coherence": 8,
                    "relevance": 6,
                }
            },
            "arg_2": {
                "scores_par_vertu": {
                    "clarity": 5,
                    "coherence": 6,
                    "relevance": 4,
                }
            },
        }
        r1 = _aggregate_virtue_scores(per_arg_results)
        r2 = _aggregate_virtue_scores(per_arg_results)
        assert r1 == r2
        assert r1["clarity"] == pytest.approx(6.0)
        assert r1["coherence"] == pytest.approx(7.0)

    def test_hypothesis_generation_deterministic(self):
        """_generate_hypotheses produces same output for same input."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _generate_hypotheses,
        )

        arg_names = ["First argument", "Second argument", "Third argument"]
        claim_names = ["Claim 1"]
        fallacies = [{"target_argument_id": "arg_1", "fallacy_type": "ad hominem"}]
        per_arg_scores = {
            "arg_1": {"overall": 8.0},
            "arg_2": {"overall": 3.0},
            "arg_3": {"overall": 7.5},
        }
        r1 = _generate_hypotheses(arg_names, claim_names, fallacies, per_arg_scores)
        r2 = _generate_hypotheses(arg_names, claim_names, fallacies, per_arg_scores)
        assert r1 == r2

    def test_dung_fallback_deterministic(self):
        """_python_social_fallback is a fail-loud JVM-required stub (#1019).

        The function is a deterministic RA-8 anti-théâtre guard: it ALWAYS raises
        ``RuntimeError("Social argumentation unavailable: JVM/Tweety required...")``
        because the social argumentation path requires a real JVM/Tweety bridge
        and there is no pure-Python fallback (synthetic scores would violate
        anti-théâtre #1019 — see docstring of ``_python_social_fallback``).

        Determinism here means: two consecutive invocations raise the same
        exception. The test was previously asserting a non-existent ``social_scores``
        key on a dict the function never returns (it raises), which made the test
        fail-loud at runtime in any env without JVM/Tweety. Mark with ``jpype``
        since the production behavior depends on JVM availability.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_social_fallback,
        )

        args = ["Arg A", "Arg B", "Arg C"]
        attacks = [("Arg A", "Arg B")]
        votes = {"Arg A": 3, "Arg B": 1, "Arg C": 2}
        context = {}

        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            _python_social_fallback(args, attacks, votes, context)
        # Determinism: a second invocation raises identically.
        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            _python_social_fallback(args, attacks, votes, context)


class TestDeterminismParamsInSource:
    """Verify _get_determinism_params is wired into invoke callables."""

    def test_function_exists(self):
        """_get_determinism_params is importable."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_determinism_params,
        )

        assert callable(_get_determinism_params)

    def test_det_params_used_in_fact_extraction(self):
        """_invoke_fact_extraction source references _get_determinism_params."""
        import inspect

        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fact_extraction,
        )

        source = inspect.getsource(_invoke_fact_extraction)
        assert "_get_determinism_params" in source

    def test_det_params_used_in_pl(self):
        """_invoke_propositional_logic source references _get_determinism_params."""
        import inspect

        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        source = inspect.getsource(_invoke_propositional_logic)
        assert "_get_determinism_params" in source

    def test_det_params_used_in_fol(self):
        """_invoke_fol_reasoning source references _get_determinism_params."""
        import inspect

        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        source = inspect.getsource(_invoke_fol_reasoning)
        assert "_get_determinism_params" in source

    def test_det_params_used_in_governance(self):
        """_invoke_governance source references _get_determinism_params."""
        import inspect

        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_governance,
        )

        source = inspect.getsource(_invoke_governance)
        assert "_get_determinism_params" in source

    def test_det_params_used_in_debate(self):
        """_invoke_debate_analysis source references _get_determinism_params."""
        import inspect

        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_debate_analysis,
        )

        source = inspect.getsource(_invoke_debate_analysis)
        assert "_get_determinism_params" in source
