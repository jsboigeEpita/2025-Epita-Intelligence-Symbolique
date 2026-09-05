"""#2041 — brothers of the #2035 « string where a sequence is expected »
family: two live production surfaces feed LLM-produced JSON into a join.

The sweep (issue deliverable) found no CONFIRMED instance — no traced caller
passes a str today — but two production sites are ONE MODEL-DRIFT away from
the exact #2035 symptom (a scalar where the template means a list, then
``join``/slice iterate it character by character):

* ``ai_shield/layers/llm_validator.py`` — ``analysis.get("categories", [])``
  from ``json.loads`` of the model's reply; a scalar emission
  (``"categories": "prompt_injection"``) made the shield reason read
  ``LLM detected: p, r, o, m, p, t, _…`` (no crash — silent absurdity).
* ``tweety_result_interpretation_plugin._interpret_dung`` — handles a dict
  payload (``grounded.get("set", [])``) but a bare string passes through:
  ``grounded[:10]`` slices the STRING and the reader prose becomes
  « contient 10 argument(s): a, 1, ,, a, 2 ».

Both take the conservative normalization the #2035 fix used on the producer
side — a scalar becomes a one-element list (the semantics the emitter
intended), never a discarded value and never an empty fallback (an empty
category list / extension is a silent false negative, strictly worse).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _llm_reply(content: str) -> MagicMock:
    """An OpenAI client whose single completion carries ``content``."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    client = MagicMock()
    client.chat.completions.create.return_value = response
    return client


class TestLlmValidatorScalarCategories:
    """ai_shield llm_validator — a scalar ``categories`` must render as ONE
    category, not as a character soup in the shield reason."""

    def test_scalar_category_renders_as_one_category(self):
        from argumentation_analysis.services.ai_shield.layers.llm_validator import (
            LLMValidatorLayer,
        )

        layer = LLMValidatorLayer(api_key="test-key")
        client = _llm_reply(
            '{"threat_score": 0.9, "categories": "prompt_injection", '
            '"explanation": "attempt detected"}'
        )
        with patch("openai.OpenAI", return_value=client):
            result = layer.validate("some suspicious input")

        assert (
            "prompt_injection" in result.reason
        ), f"#2041: a scalar category must render as one category, got: {result.reason!r}"
        assert result.reason == "LLM detected: prompt_injection"
        assert result.details["categories"] == ["prompt_injection"]

    def test_list_categories_unchanged(self):
        from argumentation_analysis.services.ai_shield.layers.llm_validator import (
            LLMValidatorLayer,
        )

        layer = LLMValidatorLayer(api_key="test-key")
        client = _llm_reply(
            '{"threat_score": 0.9, "categories": ["jailbreak", "bias"], '
            '"explanation": ""}'
        )
        with patch("openai.OpenAI", return_value=client):
            result = layer.validate("some suspicious input")

        assert result.reason == "LLM detected: jailbreak, bias"
        assert result.details["categories"] == ["jailbreak", "bias"]


class TestInterpretDungStringExtension:
    """_interpret_dung — a serialized scalar extension must count as ONE
    argument, not as N characters sliced out of the string."""

    def test_string_grounded_extension_counts_one_argument(self):
        from argumentation_analysis.plugins.tweety_result_interpretation_plugin import (
            _interpret_dung,
        )

        text = _interpret_dung({"grounded": "a1"}, arguments=["a1", "a2"])
        assert (
            "contient 1 argument(s): a1." in text
        ), f"#2041: a scalar extension must render as one argument, got: {text!r}"
        # The pre-fix absurdity, for the record: len('a1') == 2 and the
        # slice yielded characters — « contient 2 argument(s): a, 1 ».
        assert "a, 1" not in text

    def test_long_string_extension_is_not_sliced_into_characters(self):
        from argumentation_analysis.plugins.tweety_result_interpretation_plugin import (
            _interpret_dung,
        )

        text = _interpret_dung({"grounded": "arg_alpha"}, arguments=["arg_alpha"])
        assert "arg_alpha" in text
        assert "a, r, g" not in text

    def test_list_and_dict_payloads_unchanged(self):
        from argumentation_analysis.plugins.tweety_result_interpretation_plugin import (
            _interpret_dung,
        )

        text = _interpret_dung({"grounded": ["a1", "a2"]}, arguments=["a1", "a2"])
        assert "contient 2 argument(s): a1, a2." in text
        text = _interpret_dung({"grounded": {"set": ["a1"]}}, arguments=["a1"])
        assert "contient 1 argument(s): a1." in text
