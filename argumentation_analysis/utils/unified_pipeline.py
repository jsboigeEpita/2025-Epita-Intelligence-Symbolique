# Archived: 2026-03-24 — Deprecation shim for backward compatibility (#217)
# Renamed to: argumentation_analysis/utils/analysis_config.py
# Reason: Name collision with orchestration/unified_pipeline.py (3900+ lines)
import warnings

warnings.warn(
    "argumentation_analysis.utils.unified_pipeline is deprecated. "
    "Import from argumentation_analysis.utils.analysis_config instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything for backward compatibility
from argumentation_analysis.utils.analysis_config import (  # noqa: F401, E402
    AnalysisMode,
    SourceType,
    AnalysisConfig,
    AnalysisResult,
    UnifiedAnalysisPipeline,
    create_analysis_pipeline,
)

__all__ = [
    "AnalysisMode",
    "SourceType",
    "AnalysisConfig",
    "AnalysisResult",
    "UnifiedAnalysisPipeline",
    "create_analysis_pipeline",
]
