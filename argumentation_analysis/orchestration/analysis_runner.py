# -*- coding: utf-8 -*-
"""
analysis_runner.py — Backward-compatibility shim

This module was replaced by analysis_runner_v2.py but several entry points
(main_orchestrator.py, run_orchestration.py) still import from this path.

This shim re-exports the v2 classes and functions under the old names to
maintain backward compatibility without modifying all consumers.

See: analysis_runner_v2.py for the actual implementation.
"""

from argumentation_analysis.orchestration.analysis_runner_v2 import (
    AnalysisRunnerV2,
    run_analysis_v2,
)


class AnalysisRunner(AnalysisRunnerV2):
    """Backward-compatible alias for AnalysisRunnerV2.

    Adds `run_analysis_async` as an alias for `run_analysis` to support
    the calling convention used in main_orchestrator.py.
    """

    async def run_analysis_async(self, text_content, llm_service=None):
        """Alias for run_analysis() — backward compatibility."""
        return await self.run_analysis(
            text_content=text_content, llm_service=llm_service
        )


# Function alias for run_orchestration.py which imports `run_analysis`
run_analysis = run_analysis_v2

__all__ = ["AnalysisRunner", "run_analysis"]
