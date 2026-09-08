# -*- coding: utf-8 -*-
"""Import guards for the #2076/#2077 repair — the formerly import-dead chain.

Deliberately in its own file, away from the three test files that used to
manufacture ``get_fallacy_detector`` before importing (test_unified_pipelines,
test_execution_strategies, test_argumentation_analyzer): a guard living inside
a manufacturing file would pass green on the manufactured symbol and certify
nothing. Nothing here patches, injects, or pre-imports anything — if the
production chain breaks again, these go red on the real cause.
"""


def test_unified_text_analysis_imports_cleanly():
    import argumentation_analysis.pipelines.unified_text_analysis  # noqa: F401


def test_pipelines_orchestration_subpackage_imports_cleanly():
    import argumentation_analysis.pipelines.orchestration  # noqa: F401


def test_argumentation_analyzer_imports_cleanly():
    import argumentation_analysis.core.argumentation_analyzer  # noqa: F401


def test_reporting_data_collector_imports_cleanly():
    import argumentation_analysis.reporting.data_collector  # noqa: F401


def test_reporting_orchestrator_imports_cleanly():
    import argumentation_analysis.reporting.orchestrator  # noqa: F401
