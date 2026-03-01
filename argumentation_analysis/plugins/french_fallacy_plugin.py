"""
French fallacy detection SK plugin — wraps FrenchFallacyAdapter as kernel functions.

Provides @kernel_function methods for 3-tier hybrid fallacy detection
(symbolic rules, NLI zero-shot, LLM zero-shot). Can be registered in
any agent's kernel via kernel.add_plugin().

Integrated from student project 2.3.2-detection-sophismes (GitHub #44).
"""

import json

from semantic_kernel.functions import kernel_function

from argumentation_analysis.adapters.french_fallacy_adapter import (
    FALLACY_LABELS_FR,
    FrenchFallacyAdapter,
)


class FrenchFallacyPlugin:
    """Semantic Kernel plugin for French fallacy detection.

    Wraps FrenchFallacyAdapter's 3-tier detection system as
    @kernel_function methods for use through kernel.invoke().
    """

    def __init__(self, **adapter_kwargs):
        self.adapter = FrenchFallacyAdapter(**adapter_kwargs)

    @kernel_function(
        name="detect_fallacies",
        description=(
            "Detect logical fallacies in French text using 3-tier hybrid "
            "detection (symbolic rules, NLI zero-shot, LLM). Returns JSON "
            "with detected fallacies, confidence scores, and sources."
        ),
    )
    def detect_fallacies(self, text: str) -> str:
        """Detect fallacies and return results as JSON."""
        result = self.adapter.detect(text)
        return json.dumps(result, ensure_ascii=False)

    @kernel_function(
        name="get_available_tiers",
        description=(
            "List available detection tiers (symbolic, nli, llm)."
        ),
    )
    def get_available_tiers(self) -> str:
        """Return available detection tiers as JSON."""
        return json.dumps({
            "available_tiers": self.adapter.get_available_tiers(),
            "is_available": self.adapter.is_available(),
        })

    @kernel_function(
        name="list_fallacy_types",
        description="List the 13 French fallacy types that can be detected.",
    )
    def list_fallacy_types(self) -> str:
        """Return the list of detectable fallacy types as JSON."""
        return json.dumps(FALLACY_LABELS_FR, ensure_ascii=False)
