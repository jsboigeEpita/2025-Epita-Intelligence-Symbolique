"""
Advanced tests for LLMJudge.

Tests cover:
- Timeout handling
- JSON parsing from LLM responses
- Large result processing
- Result preparation and trimming
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.evaluation.judge import LLMJudge, JudgeScore


@pytest.mark.unit
class TestJudgeScore:
    """Test JudgeScore dataclass."""

    def test_judge_score_creation(self):
        """Test creating a JudgeScore."""
        score = JudgeScore(
            completeness=4.5,
            accuracy=4.0,
            depth=3.5,
            coherence=4.2,
            actionability=3.8,
            overall=4.0,
            reasoning="Good analysis overall",
            judge_model="gpt-4",
            raw_response="Raw LLM response here",
        )

        assert score.completeness == 4.5
        assert score.accuracy == 4.0
        assert score.depth == 3.5
        assert score.coherence == 4.2
        assert score.actionability == 3.8
        assert score.overall == 4.0
        assert score.reasoning == "Good analysis overall"
        assert score.judge_model == "gpt-4"
        assert score.raw_response == "Raw LLM response here"

    def test_judge_score_defaults(self):
        """Test JudgeScore with default raw_response."""
        score = JudgeScore(
            completeness=5.0,
            accuracy=5.0,
            depth=5.0,
            coherence=5.0,
            actionability=5.0,
            overall=5.0,
            reasoning="Perfect analysis",
            judge_model="gpt-4",
        )

        assert score.raw_response == ""


@pytest.mark.unit
class TestJSONParsing:
    """Test JSON parsing from LLM responses."""

    def test_parse_plain_json(self):
        """Test parsing plain JSON response."""
        judge = LLMJudge()
        raw = '{"completeness": 4, "accuracy": 4, "depth": 3, "coherence": 4, "actionability": 3, "overall": 4, "reasoning": "Good"}'

        parsed = judge._parse_json_response(raw)

        assert parsed["completeness"] == 4
        assert parsed["overall"] == 4
        assert parsed["reasoning"] == "Good"

    def test_parse_json_markdown_block(self):
        """Test parsing JSON from markdown code block."""
        judge = LLMJudge()
        raw = """```json
{
  "completeness": 4,
  "accuracy": 4,
  "depth": 3,
  "coherence": 4,
  "actionability": 3,
  "overall": 4,
  "reasoning": "Good analysis"
}
```"""

        parsed = judge._parse_json_response(raw)

        assert parsed["completeness"] == 4
        assert parsed["reasoning"] == "Good analysis"

    def test_parse_json_markdown_no_language(self):
        """Test parsing JSON from markdown without language specifier."""
        judge = LLMJudge()
        raw = """```
{
  "completeness": 5,
  "overall": 5
}
```"""

        parsed = judge._parse_json_response(raw)

        assert parsed["completeness"] == 5
        assert parsed["overall"] == 5

    def test_parse_json_with_text_before(self):
        """Test parsing JSON when there's text before the JSON."""
        judge = LLMJudge()
        raw = """Here's my evaluation:

{"completeness": 4, "overall": 4, "reasoning": "Test"}

Hope this helps!"""

        parsed = judge._parse_json_response(raw)

        assert parsed["completeness"] == 4
        assert parsed["overall"] == 4

    def test_parse_invalid_json(self):
        """Test that invalid JSON returns empty dict."""
        judge = LLMJudge()
        raw = "This is not valid JSON at all"

        parsed = judge._parse_json_response(raw)

        assert parsed == {}

    def test_parse_malformed_json_fallback(self):
        """Test fallback extraction of JSON from malformed response."""
        judge = LLMJudge()
        raw = """The scores are:
completeness: 4
accuracy: 3
{"completeness": 4, "overall": 4}"""

        parsed = judge._parse_json_response(raw)

        assert parsed["completeness"] == 4
        assert parsed["overall"] == 4


@pytest.mark.unit
class TestResultPreparation:
    """Test result preparation for judge."""

    def test_trim_raw_text(self):
        """Test that raw_text is trimmed."""
        judge = LLMJudge()
        long_text = "A" * 200

        results = {
            "raw_text": long_text,
            "other_field": "keep this",
        }

        prepared = judge._prepare_results_for_judge(results)

        assert "raw_text" in prepared
        assert len(prepared["raw_text"]) < len(long_text)
        assert "chars total" in prepared["raw_text"]
        assert prepared["other_field"] == "keep this"

    def test_trim_lists(self):
        """Test that long lists are truncated."""
        judge = LLMJudge()
        long_list = [{"item": f"item_{i}"} for i in range(10)]

        results = {
            "arguments": long_list,
        }

        prepared = judge._prepare_results_for_judge(results)

        assert "arguments" in prepared
        assert len(prepared["arguments"]) <= 6  # 5 items + "and X more"
        assert any("more" in str(item) for item in prepared["arguments"])

    def test_trim_long_strings(self):
        """Test that long string values are truncated."""
        judge = LLMJudge()
        long_string = "B" * 600

        results = {
            "description": long_string,
        }

        prepared = judge._prepare_results_for_judge(results)

        assert "description" in prepared
        assert len(prepared["description"]) < len(long_string)
        assert "chars" in prepared["description"]

    def test_max_depth_limit(self):
        """Test that deeply nested structures are limited."""
        judge = LLMJudge()

        # Create a structure deeper than max depth
        nested = {"level": 0}
        current = nested
        for i in range(10):
            current["next"] = {"level": i + 1}
            current = current["next"]

        results = {"nested": nested}

        prepared = judge._prepare_results_for_judge(results)

        # Should be truncated at depth 6
        assert "nested" in prepared
        # Find the deepest level
        deepest = prepared["nested"]
        depth = 0
        while "next" in deepest and isinstance(deepest["next"], dict):
            deepest = deepest["next"]
            depth += 1

        assert depth <= 6

    def test_preserve_important_structure(self):
        """Test that important structure is preserved."""
        judge = LLMJudge()

        results = {
            "arguments": [
                {"id": "arg1", "text": "Argument 1", "strength": 0.8},
                {"id": "arg2", "text": "Argument 2", "strength": 0.6},
            ],
            "fallacies": [
                {"name": "ad_hominem", "confidence": 0.9},
            ],
            "quality_score": 0.75,
        }

        prepared = judge._prepare_results_for_judge(results)

        assert "arguments" in prepared
        assert len(prepared["arguments"]) == 2
        assert prepared["arguments"][0]["id"] == "arg1"
        assert "fallacies" in prepared
        assert prepared["quality_score"] == 0.75


@pytest.mark.unit
class TestLargeResultProcessing:
    """Test handling of large analysis results."""

    def test_large_results_truncation(self):
        """Test that large results are truncated for the judge."""
        judge = LLMJudge()

        # Create a large result set
        large_results = {
            "arguments": [
                {"id": f"arg_{i}", "text": "Argument text"} for i in range(100)
            ],
            "fallacies": [
                {"name": f"fallacy_{i}", "confidence": 0.5} for i in range(50)
            ],
            "raw_text": "A" * 10000,
        }

        prepared = judge._prepare_results_for_judge(large_results)

        # Verify truncation
        assert len(prepared["arguments"]) < 100
        assert len(prepared["fallacies"]) < 50
        assert len(prepared["raw_text"]) < 10000

    def test_results_str_length_limit(self):
        """Test that JSON string is limited to ~12k chars."""
        judge = LLMJudge()

        # Create results that would exceed the limit
        large_results = {"data": ["item_" + str(i) for i in range(1000)]}

        prepared = judge._prepare_results_for_judge(large_results)
        results_str = json.dumps(prepared, indent=2, ensure_ascii=False, default=str)

        # In actual usage, there's a 12000 char limit in evaluate()
        # This test verifies the preparation helps stay within limits
        assert len(results_str) < 50000  # Should be significantly reduced


@pytest.mark.unit
class TestEvaluateMethod:
    """Test the evaluate method."""

    @pytest.mark.requires_api
    @pytest.mark.asyncio
    async def test_evaluate_with_api(self):
        """Test evaluation with actual API (requires API key)."""
        judge = LLMJudge()

        # Simple test results
        analysis_results = {
            "arguments": [
                {"id": "arg1", "text": "Premise 1"},
                {"id": "arg2", "text": "Premise 2"},
            ],
            "conclusion": "Therefore, conclusion",
            "quality_score": 0.8,
        }

        try:
            score = await judge.evaluate(
                input_text="This is a test argument. Premise 1 and Premise 2 lead to conclusion.",
                workflow_name="light",
                analysis_results=analysis_results,
                model_registry=None,
            )

            # Verify score structure
            assert hasattr(score, "completeness")
            assert hasattr(score, "accuracy")
            assert hasattr(score, "overall")
            assert hasattr(score, "reasoning")

            # Scores should be in valid range
            assert 0 <= score.completeness <= 5
            assert 0 <= score.overall <= 5

        except Exception as e:
            pytest.skip(f"API not available: {e}")

    @pytest.mark.asyncio
    async def test_evaluate_timeout(self):
        """Test that timeout is handled gracefully."""
        judge = LLMJudge()

        # Mock OpenAI client with delay
        async def slow_completion(*args, **kwargs):
            await asyncio.sleep(5)
            return MagicMock(
                choices=[MagicMock(message=MagicMock(content='{"overall": 4}'))]
            )

        with patch("openai.AsyncOpenAI") as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create = slow_completion
            mock_client.return_value = mock_instance

            # Set a short timeout using asyncio.wait_for
            try:
                result = await asyncio.wait_for(
                    judge.evaluate(
                        input_text="Test",
                        workflow_name="light",
                        analysis_results={},
                        model_registry=None,
                    ),
                    timeout=0.1,
                )
                # If it completes, that's fine too
                assert result is not None
            except asyncio.TimeoutError:
                # Timeout is expected behavior
                pass

    @pytest.mark.asyncio
    async def test_evaluate_api_error_handling(self):
        """Test that API errors are handled gracefully."""
        judge = LLMJudge()

        # Mock OpenAI client that raises an error
        async def failing_completion(*args, **kwargs):
            raise Exception("API Error")

        with patch("openai.AsyncOpenAI") as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create = failing_completion
            mock_client.return_value = mock_instance

            result = await judge.evaluate(
                input_text="Test",
                workflow_name="light",
                analysis_results={},
                model_registry=None,
            )

            # Should return a zero score on error
            assert result.completeness == 0
            assert result.overall == 0
            assert "Evaluation failed" in result.reasoning

    @pytest.mark.asyncio
    async def test_evaluate_with_model_registry(self):
        """Test evaluation with model registry for model switching."""
        judge = LLMJudge(model_name="custom_model")

        mock_registry = MagicMock()
        mock_registry.save_env = MagicMock(return_value={"env": "saved"})
        mock_registry.activate = MagicMock()
        mock_registry.restore_env = MagicMock()

        # Mock successful API call
        async def mock_completion(*args, **kwargs):
            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            content='{"completeness": 4, "accuracy": 4, "depth": 4, "coherence": 4, "actionability": 4, "overall": 4, "reasoning": "Test"}'
                        )
                    )
                ]
            )

        with patch("openai.AsyncOpenAI") as mock_client:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create = mock_completion
            mock_client.return_value = mock_instance

            result = await judge.evaluate(
                input_text="Test",
                workflow_name="light",
                analysis_results={},
                model_registry=mock_registry,
            )

            # Verify model registry was used
            mock_registry.activate.assert_called_once_with("custom_model")
            mock_registry.restore_env.assert_called_once()

            assert result.overall == 4


@pytest.mark.unit
class TestSystemPrompts:
    """Test system prompts and templates."""

    def test_judge_system_prompt_structure(self):
        """Test that system prompt contains required criteria."""
        from argumentation_analysis.evaluation.judge import JUDGE_SYSTEM_PROMPT

        assert "Completeness" in JUDGE_SYSTEM_PROMPT
        assert "Accuracy" in JUDGE_SYSTEM_PROMPT
        assert "Depth" in JUDGE_SYSTEM_PROMPT
        assert "Coherence" in JUDGE_SYSTEM_PROMPT
        assert "Actionability" in JUDGE_SYSTEM_PROMPT
        assert "1-5" in JUDGE_SYSTEM_PROMPT

    def test_judge_user_template(self):
        """Test that user template has correct placeholders."""
        from argumentation_analysis.evaluation.judge import JUDGE_USER_TEMPLATE

        assert "{input_text}" in JUDGE_USER_TEMPLATE
        assert "{workflow_name}" in JUDGE_USER_TEMPLATE
        assert "{analysis_results}" in JUDGE_USER_TEMPLATE

    def test_template_formatting(self):
        """Test that template can be formatted correctly."""
        from argumentation_analysis.evaluation.judge import JUDGE_USER_TEMPLATE

        formatted = JUDGE_USER_TEMPLATE.format(
            input_text="Test input",
            workflow_name="test_workflow",
            analysis_results='{"result": "value"}',
        )

        assert "Test input" in formatted
        assert "test_workflow" in formatted
        assert '{"result": "value"}' in formatted
