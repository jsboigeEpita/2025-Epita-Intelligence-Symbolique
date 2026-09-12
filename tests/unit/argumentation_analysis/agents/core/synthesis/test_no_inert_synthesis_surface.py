"""#2140: the inert SynthesisAgent surface is gone.

The eponymous class of the ``synthesis`` package promised a unified
formal+informal synthesis its two fabriques could never deliver: no
production code ever populated ``_logic_agents_cache`` or
``_informal_agent``, so both always raised, and the surrounding
``except`` wrote the exception text into result fields
(``propositional_result``, ``arguments_structure``) — a failure
traveling as data (#1019). Worse, the door was armed in production:
``run_unified_analysis(mode="original")`` (and the error-fallback from
every other mode) maps the default ``analysis_type="comprehensive"``
to the ``unified`` analysis mode, so on a seat with LLM keys the
pipeline constructed the agent and produced a report whose synthesis
was error text. Wiring it would have duplicated the informal+formal
analyses the constructing pipeline already runs, so the surface is
removed rather than wired. ``DeepSynthesisAgent`` is the synthesis
surface that produces real reports.
"""

import argumentation_analysis.agents.core.synthesis as synthesis_pkg
from argumentation_analysis.pipelines.unified_text_analysis import (
    UnifiedAnalysisConfig,
)


def test_synthesis_package_exports_no_inert_surface():
    exports = set(getattr(synthesis_pkg, "__all__", [])) | {
        n for n in vars(synthesis_pkg) if not n.startswith("_")
    }
    assert "SynthesisAgent" not in exports
    assert "UnifiedReport" not in exports
    assert "LogicAnalysisResult" not in exports
    assert "InformalAnalysisResult" not in exports


def test_unified_analysis_mode_no_longer_promises_synthesis():
    """The "unified" mode existed to call SynthesisAgent — it must not
    survive as a label for something that no longer runs."""
    cfg = UnifiedAnalysisConfig(analysis_modes=["informal", "formal", "unified"])
    assert "unified" not in cfg.analysis_modes
