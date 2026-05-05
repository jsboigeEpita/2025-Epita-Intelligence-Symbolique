"""Shield presets — pre-configured layer combinations.

Based on soutenance description:
- basic: Heuristic only (fast, zero cost)
- advanced: All layers (heuristic + LLM + output filter)
- output_only: Output filter only (for post-LLM validation)
"""

from typing import Optional

from argumentation_analysis.services.ai_shield.shield import Shield
from argumentation_analysis.services.ai_shield.layers.heuristic import HeuristicLayer
from argumentation_analysis.services.ai_shield.layers.llm_validator import (
    LLMValidatorLayer,
)
from argumentation_analysis.services.ai_shield.layers.output_filter import (
    OutputFilterLayer,
)


def load_preset(
    preset_name: str = "basic",
    api_key: Optional[str] = None,
    fail_open: bool = False,
) -> Shield:
    """Load a pre-configured shield preset.

    Args:
        preset_name: "basic", "advanced", or "output_only".
        api_key: OpenAI API key for LLM validator layer.
        fail_open: If True, allow input when layers error.

    Returns:
        Configured Shield instance.
    """
    if preset_name == "basic":
        return Shield(
            name="basic",
            fail_open=fail_open,
            layers=[
                HeuristicLayer(threshold=0.5),
            ],
        )

    elif preset_name == "advanced":
        return Shield(
            name="advanced",
            fail_open=fail_open,
            layers=[
                HeuristicLayer(threshold=0.5),
                LLMValidatorLayer(threshold=0.6, api_key=api_key),
                OutputFilterLayer(threshold=0.4),
            ],
        )

    elif preset_name == "output_only":
        return Shield(
            name="output_only",
            fail_open=fail_open,
            layers=[
                OutputFilterLayer(threshold=0.4),
            ],
        )

    elif preset_name == "strict":
        return Shield(
            name="strict",
            fail_open=False,
            layers=[
                HeuristicLayer(threshold=0.3),  # Lower threshold = stricter
                LLMValidatorLayer(threshold=0.4, api_key=api_key),
                OutputFilterLayer(threshold=0.3),
            ],
        )

    else:
        raise ValueError(
            f"Unknown preset '{preset_name}'. "
            f"Available: basic, advanced, output_only, strict"
        )
