"""
LLM Judge: evaluate analysis quality using a capable LLM.

Uses a structured rubric to score analysis results on multiple dimensions.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("evaluation.judge")

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator of argumentation analysis quality.
You will receive:
1. An input text that was analyzed
2. The analysis results produced by an automated system
3. The workflow that was used

Rate the analysis on a scale of 1-5 for each criterion:
- **Completeness** (1-5): Does the analysis cover all key arguments and claims in the text?
- **Accuracy** (1-5): Are the identified arguments, fallacies, and relationships correct?
- **Depth** (1-5): Does the analysis go beyond surface-level observations?
- **Coherence** (1-5): Are the results internally consistent and well-structured?
- **Actionability** (1-5): Could someone use these results to understand the argumentation?

Respond with ONLY a JSON object:
{
  "completeness": <1-5>,
  "accuracy": <1-5>,
  "depth": <1-5>,
  "coherence": <1-5>,
  "actionability": <1-5>,
  "overall": <1-5>,
  "reasoning": "<brief explanation of scores>"
}"""

JUDGE_USER_TEMPLATE = """## Input Text (excerpt)
{input_text}

## Workflow Used
{workflow_name}

## Analysis Results
{analysis_results}

Please evaluate the quality of this analysis. Note: results may be summarized for brevity — evaluate based on the depth and quality of what is shown, not on apparent truncation."""


@dataclass
class JudgeScore:
    """Score from LLM judge evaluation."""

    completeness: float
    accuracy: float
    depth: float
    coherence: float
    actionability: float
    overall: float
    reasoning: str
    judge_model: str
    raw_response: str = ""


class LLMJudge:
    """Evaluate analysis quality using an LLM judge."""

    def __init__(self, model_name: str = "default"):
        self.model_name = model_name

    async def evaluate(
        self,
        input_text: str,
        workflow_name: str,
        analysis_results: Dict[str, Any],
        model_registry: Optional[Any] = None,
    ) -> JudgeScore:
        """
        Evaluate analysis quality using an LLM.

        Uses the OpenAI SDK directly for simplicity (no SK kernel needed).

        Args:
            input_text: The original text that was analyzed.
            workflow_name: The workflow used for analysis.
            analysis_results: The analysis output to evaluate.
            model_registry: Optional ModelRegistry for model switching.
        """
        from openai import AsyncOpenAI
        import os

        # Prepare the prompt with smart summarization
        prepared = self._prepare_results_for_judge(analysis_results)
        results_str = json.dumps(prepared, indent=2, ensure_ascii=False, default=str)
        # Budget: 12000 chars for results (gpt-5-mini has 128k context)
        if len(results_str) > 12000:
            results_str = results_str[:12000] + "\n... [summarized]"

        user_msg = JUDGE_USER_TEMPLATE.format(
            input_text=input_text[:2000],
            workflow_name=workflow_name,
            analysis_results=results_str,
        )

        # Switch model if needed
        saved_env = None
        if model_registry and self.model_name != "default":
            saved_env = model_registry.save_env()
            model_registry.activate(self.model_name)

        try:
            model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
            base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            api_key = os.environ.get("OPENAI_API_KEY", "")

            client = AsyncOpenAI(api_key=api_key, base_url=base_url)

            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
            )

            raw = response.choices[0].message.content or ""
            # Parse JSON from response
            score_data = self._parse_json_response(raw)

            return JudgeScore(
                completeness=score_data.get("completeness", 0),
                accuracy=score_data.get("accuracy", 0),
                depth=score_data.get("depth", 0),
                coherence=score_data.get("coherence", 0),
                actionability=score_data.get("actionability", 0),
                overall=score_data.get("overall", 0),
                reasoning=score_data.get("reasoning", ""),
                judge_model=model_id,
                raw_response=raw,
            )

        except Exception as e:
            logger.error(f"Judge evaluation failed: {e}")
            return JudgeScore(
                completeness=0,
                accuracy=0,
                depth=0,
                coherence=0,
                actionability=0,
                overall=0,
                reasoning=f"Evaluation failed: {e}",
                judge_model=self.model_name,
            )
        finally:
            if saved_env and model_registry:
                model_registry.restore_env(saved_env)

    @staticmethod
    def _prepare_results_for_judge(results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare analysis results for the judge by stripping redundant data
        and summarizing large collections.

        The raw state_snapshot often includes raw_text (already in input_text)
        and full lists of arguments/beliefs/etc. that blow the char budget.
        This method keeps the structure informative while fitting in ~12k chars.
        """
        # Keys whose content duplicates the input text
        TEXT_KEYS = {"raw_text", "raw_text_snippet"}
        # Max items to show from any list
        MAX_LIST_ITEMS = 5
        # Max string length for individual values
        MAX_VALUE_LEN = 500

        def _trim(obj: Any, depth: int = 0) -> Any:
            if depth > 6:
                return "..."
            if isinstance(obj, dict):
                trimmed = {}
                for k, v in obj.items():
                    if k in TEXT_KEYS:
                        # Replace raw text with a short snippet
                        if isinstance(v, str) and len(v) > 100:
                            trimmed[k] = v[:100] + f"... ({len(v)} chars total)"
                        else:
                            trimmed[k] = v
                    else:
                        trimmed[k] = _trim(v, depth + 1)
                return trimmed
            elif isinstance(obj, list):
                if len(obj) > MAX_LIST_ITEMS:
                    shown = [_trim(item, depth + 1) for item in obj[:MAX_LIST_ITEMS]]
                    return shown + [
                        f"... and {len(obj) - MAX_LIST_ITEMS} more (total: {len(obj)})"
                    ]
                return [_trim(item, depth + 1) for item in obj]
            elif isinstance(obj, str) and len(obj) > MAX_VALUE_LEN:
                return obj[:MAX_VALUE_LEN] + f"... ({len(obj)} chars)"
            return obj

        return _trim(results)

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling markdown code blocks."""
        text = raw.strip()
        # Strip markdown code block
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse judge response as JSON: {text[:200]}")
            return {}
