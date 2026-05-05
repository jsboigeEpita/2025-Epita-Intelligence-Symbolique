"""NL-to-Logic SK Plugin — exposes NLToLogicTranslator as @kernel_function methods.

Wraps the NL-to-formal-logic translation service (services/nl_to_logic.py)
so that LLM agents in conversational mode can translate natural language
arguments into propositional and first-order logic formulas, validated
via Tweety with a translate-validate-retry loop.

Issue #285: Wire Tweety PL/FOL/Modal in conversational pipeline.
"""

import json
import logging

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class NLToLogicPlugin:
    """Semantic Kernel plugin for NL-to-formal-logic translation.

    Provides @kernel_function methods that:
    1. Translate natural language to PL or FOL formulas
    2. Validate formulas via Tweety (with retry loop)
    3. Return structured results for storage in analysis state

    Usage:
        kernel.add_plugin(NLToLogicPlugin(), plugin_name="nl_to_logic")
    """

    @kernel_function(
        name="translate_to_pl",
        description=(
            "Translate a natural language argument into propositional logic (PL). "
            "Uses LLM with Tweety validation and retry loop. "
            "Input: plain text argument. "
            "Returns JSON with 'formula', 'variables', 'is_valid', 'confidence'."
        ),
    )
    async def translate_to_pl(self, text: str) -> str:
        """Translate NL text to propositional logic."""
        from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

        translator = NLToLogicTranslator(max_retries=3, logic_type="propositional")
        result = await translator.translate(text, logic_type="propositional")

        return json.dumps(
            {
                "original_text": result.original_text[:200],
                "formula": result.formula,
                "logic_type": result.logic_type,
                "is_valid": result.is_valid,
                "validation_message": result.validation_message,
                "attempts": result.attempts,
                "variables": result.variables,
                "confidence": result.confidence,
            }
        )

    @kernel_function(
        name="translate_to_fol",
        description=(
            "Translate a natural language argument into first-order logic (FOL). "
            "Uses LLM with Tweety validation and retry loop. "
            "Input: plain text argument. "
            "Returns JSON with 'formula', 'predicates', 'constants', 'is_valid', 'confidence'."
        ),
    )
    async def translate_to_fol(self, text: str) -> str:
        """Translate NL text to first-order logic."""
        from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

        translator = NLToLogicTranslator(max_retries=3, logic_type="fol")
        result = await translator.translate(text, logic_type="fol")

        return json.dumps(
            {
                "original_text": result.original_text[:200],
                "formula": result.formula,
                "logic_type": result.logic_type,
                "is_valid": result.is_valid,
                "validation_message": result.validation_message,
                "attempts": result.attempts,
                "variables": result.variables,
                "confidence": result.confidence,
            }
        )

    @kernel_function(
        name="translate_batch_to_pl",
        description=(
            "Translate multiple NL arguments to propositional logic in batch. "
            "Input: JSON with 'arguments' (list of text strings). "
            "Returns JSON with 'translations' list and 'overall_consistency'."
        ),
    )
    async def translate_batch_to_pl(self, input: str) -> str:
        """Translate batch of NL texts to propositional logic."""
        from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

        params = _parse_json_or_default(input, {"arguments": []})
        arguments = params.get("arguments", [])

        if not arguments:
            return json.dumps({"error": "No arguments provided", "translations": []})

        translator = NLToLogicTranslator(max_retries=3, logic_type="propositional")
        batch = await translator.translate_batch(arguments, logic_type="propositional")

        return json.dumps(
            {
                "translations": [
                    {
                        "original_text": t.original_text[:200],
                        "formula": t.formula,
                        "is_valid": t.is_valid,
                        "variables": t.variables,
                        "confidence": t.confidence,
                    }
                    for t in batch.translations
                ],
                "overall_consistency": batch.overall_consistency,
                "consistency_message": batch.consistency_message,
                "method": batch.method,
            }
        )

    @kernel_function(
        name="translate_batch_to_fol",
        description=(
            "Translate multiple NL arguments to first-order logic in batch. "
            "Input: JSON with 'arguments' (list of text strings). "
            "Returns JSON with 'translations' list and 'overall_consistency'."
        ),
    )
    async def translate_batch_to_fol(self, input: str) -> str:
        """Translate batch of NL texts to first-order logic."""
        from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

        params = _parse_json_or_default(input, {"arguments": []})
        arguments = params.get("arguments", [])

        if not arguments:
            return json.dumps({"error": "No arguments provided", "translations": []})

        translator = NLToLogicTranslator(max_retries=3, logic_type="fol")
        batch = await translator.translate_batch(arguments, logic_type="fol")

        return json.dumps(
            {
                "translations": [
                    {
                        "original_text": t.original_text[:200],
                        "formula": t.formula,
                        "is_valid": t.is_valid,
                        "variables": t.variables,
                        "confidence": t.confidence,
                    }
                    for t in batch.translations
                ],
                "overall_consistency": batch.overall_consistency,
                "consistency_message": batch.consistency_message,
                "method": batch.method,
            }
        )


def _parse_json_or_default(text: str, default: dict) -> dict:
    """Try to parse JSON from text, return default on failure."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return default
    except (json.JSONDecodeError, TypeError):
        return default
