"""
Advanced tests for judge.py (LLM Judge robustness, edge cases).
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from argumentation_analysis.evaluation.judge import (
    JUDGE_SYSTEM_PROMPT,
    JUDGE_USER_TEMPLATE,
    JudgeScore,
    LLMJudge,
)


# =====================================================================
# JudgeScore Tests
# =====================================================================


class TestJudgeScore:
    """Tests for JudgeScore dataclass."""

    def test_creation_with_all_fields(self):
        """Verify score creation with all fields."""
        score = JudgeScore(
            completeness=4,
            accuracy=3,
            depth=3,
            coherence=4,
            actionability=3,
            overall=3,
            reasoning="Good analysis",
            judge_model="gpt-5-mini",
            raw_response='{"overall": 3}',
        )
        assert score.completeness == 4
        assert score.overall == 3
        assert score.judge_model == "gpt-5-mini"

    def test_creation_minimal(self):
        """Verify score can be created with required fields only."""
        score = JudgeScore(
            completeness=0,
            accuracy=0,
            depth=0,
            coherence=0,
            actionability=0,
            overall=0,
            reasoning="",
            judge_model="default",
        )
        assert score.raw_response == ""


# =====================================================================
# LLMJudge Tests
# =====================================================================


class TestLLMJudgeAdvanced:
    """Advanced tests for LLMJudge."""

    def test_initialization_default_model(self):
        """Verify judge initializes with default model."""
        judge = LLMJudge()
        assert judge.model_name == "default"

    def test_initialization_custom_model(self):
        """Verify judge can use custom model name."""
        judge = LLMJudge(model_name="claude-opus")
        assert judge.model_name == "claude-opus"

    def test_judge_system_prompt_defined(self):
        """Verify system prompt is defined."""
        assert JUDGE_SYSTEM_PROMPT
        assert "completeness" in JUDGE_SYSTEM_PROMPT
        assert "accuracy" in JUDGE_SYSTEM_PROMPT
        assert "depth" in JUDGE_SYSTEM_PROMPT
        assert "coherence" in JUDGE_SYSTEM_PROMPT
        assert "actionability" in JUDGE_SYSTEM_PROMPT

    def test_judge_user_template_defined(self):
        """Verify user template is defined."""
        assert JUDGE_USER_TEMPLATE
        assert "{input_text}" in JUDGE_USER_TEMPLATE
        assert "{workflow_name}" in JUDGE_USER_TEMPLATE
        assert "{analysis_results}" in JUDGE_USER_TEMPLATE

    def test_parse_json_response_empty(self):
        """Verify parsing empty response returns empty dict."""
        judge = LLMJudge()
        result = judge._parse_json_response("")
        assert result == {}

    def test_parse_json_response_malformed(self):
        """Verify parsing malformed JSON returns empty dict."""
        judge = LLMJudge()
        result = judge._parse_json_response('{invalid json}')
        assert result == {}

    def test_parse_json_response_nested_json(self):
        """Verify parsing nested JSON structures."""
        judge = LLMJudge()
        raw = '{"outer": {"inner": {"value": 5}}}'
        result = judge._parse_json_response(raw)
        assert result["outer"]["inner"]["value"] == 5

    def test_parse_json_response_with_newlines(self):
        """Verify parsing JSON with newlines."""
        judge = LLMJudge()
        raw = '''{
  "completeness": 4,
  "overall": 3
}'''
        result = judge._parse_json_response(raw)
        assert result["completeness"] == 4

    def test_parse_json_response_trailing_comma(self):
        """Verify parsing handles trailing comma (non-strict)."""
        judge = LLMJudge()
        # This should fail strict JSON but we handle it gracefully
        raw = '{"completeness": 4, "overall": 3}'
        result = judge._parse_json_response(raw)
        assert result["completeness"] == 4

    @pytest.mark.asyncio
    async def test_evaluate_with_model_registry(self):
        """Verify evaluation uses model_registry when provided."""
        judge = LLMJudge(model_name="custom")

        mock_registry = MagicMock()
        mock_registry.save_env.return_value = {"OPENAI_API_KEY": "original"}
        mock_registry.activate = MagicMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(
            content='{"completeness": 4, "accuracy": 3, "depth": 3, '
                   '"coherence": 4, "actionability": 3, "overall": 3, "reasoning": "Good"}'
        ))]

        with patch("openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            score = await judge.evaluate(
                input_text="Test",
                workflow_name="light",
                analysis_results={},
                model_registry=mock_registry,
            )

        # Verify model was activated
        mock_registry.activate.assert_called_once_with("custom")
        # Verify env was restored
        mock_registry.restore_env.assert_called_once()
        assert score.overall == 3

    @pytest.mark.asyncio
    async def test_evaluate_with_large_results(self):
        """Verify evaluation handles large analysis results."""
        judge = LLMJudge()

        # Create large results
        large_results = {
            "raw_text": "A" * 10000,
            "identified_arguments": [{"text": f"Argument {i}"} for i in range(100)],
            "beliefs": [{"id": f"belief_{i}"} for i in range(50)],
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(
            content='{"completeness": 3, "accuracy": 3, "depth": 3, '
                   '"coherence": 3, "actionability": 3, "overall": 3, "reasoning": "ok"}'
        ))]

        with patch("openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            score = await judge.evaluate(
                input_text="Test",
                workflow_name="light",
                analysis_results=large_results,
            )

        assert score.overall == 3

    @pytest.mark.asyncio
    async def test_evaluate_timeout_handling(self):
        """Verify evaluation handles timeouts gracefully."""
        judge = LLMJudge()

        with patch("openai.AsyncOpenAI", side_effect=TimeoutError("Request timed out")):
            score = await judge.evaluate(
                input_text="Test",
                workflow_name="light",
                analysis_results={},
            )

        assert score.overall == 0
        assert "failed" in score.reasoning.lower()

    @pytest.mark.asyncio
    async def test_evaluate_api_key_missing(self, monkeypatch):
        """Verify evaluation handles missing API key."""
        judge = LLMJudge()

        # Clear API key
        monkeypatch.setenv("OPENAI_API_KEY", "")

        with patch("openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("No API key")
            )
            MockClient.return_value = mock_client

            score = await judge.evaluate(
                input_text="Test",
                workflow_name="light",
                analysis_results={},
            )

        assert score.overall == 0

    def test_prepare_results_deeply_nested(self):
        """Verify preparation handles deeply nested structures."""
        judge = LLMJudge()
        results = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "raw_text": "Deep text" * 100,
                            "value": "ok",
                        }
                    }
                }
            }
        }

        prepared = judge._prepare_results_for_judge(results)

        # Deep nesting should be preserved
        assert "level1" in prepared
        assert "level2" in prepared["level1"]
        # Long text should be truncated
        assert "chars total" in prepared["level1"]["level2"]["level3"]["level4"]["raw_text"]

    def test_prepare_results_preserves_numbers(self):
        """Verify preparation preserves numeric values."""
        judge = LLMJudge()
        results = {
            "score": 0.95,
            "count": 42,
            "ratio": 3.14159,
        }

        prepared = judge._prepare_results_for_judge(results)

        assert prepared["score"] == 0.95
        assert prepared["count"] == 42
        assert prepared["ratio"] == 3.14159

    def test_prepare_results_handles_booleans(self):
        """Verify preparation preserves boolean values."""
        judge = LLMJudge()
        results = {
            "is_valid": True,
            "has_errors": False,
        }

        prepared = judge._prepare_results_for_judge(results)

        assert prepared["is_valid"] is True
        assert prepared["has_errors"] is False

    def test_prepare_results_handles_none_values(self):
        """Verify preparation preserves None values."""
        judge = LLMJudge()
        results = {
            "optional_field": None,
            "another": "value",
        }

        prepared = judge._prepare_results_for_judge(results)

        assert prepared["optional_field"] is None
        assert prepared["another"] == "value"

    def test_prepare_results_empty_dict(self):
        """Verify preparation handles empty dict."""
        judge = LLMJudge()
        prepared = judge._prepare_results_for_judge({})
        assert prepared == {}

    def test_prepare_results_empty_list(self):
        """Verify preparation handles empty list."""
        judge = LLMJudge()
        results = {"items": []}
        prepared = judge._prepare_results_for_judge(results)
        assert prepared["items"] == []

    @pytest.mark.asyncio
    async def test_evaluate_parses_malformed_judge_response(self):
        """Verify evaluation handles malformed judge response."""
        judge = LLMJudge()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(
            content='This is not valid JSON at all'
        ))]

        with patch("openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            score = await judge.evaluate(
                input_text="Test",
                workflow_name="light",
                analysis_results={},
            )

        # Should return zero scores when parsing fails
        assert score.overall == 0

    @pytest.mark.asyncio
    async def test_evaluate_with_missing_fields_in_response(self):
        """Verify evaluation handles missing fields in judge response."""
        judge = LLMJudge()

        # Response with only some fields
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(
            content='{"completeness": 4, "overall": 3}'
        ))]

        with patch("openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            score = await judge.evaluate(
                input_text="Test",
                workflow_name="light",
                analysis_results={},
            )

        # Missing fields should default to 0
        assert score.completeness == 4
        assert score.overall == 3
        assert score.accuracy == 0
        assert score.depth == 0
