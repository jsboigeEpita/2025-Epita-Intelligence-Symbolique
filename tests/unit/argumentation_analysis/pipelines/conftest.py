# conftest.py for tests/unit/argumentation_analysis/pipelines/
# Exclude test_unified_pipelines.py from collection — JPype DLL crash on Windows
# + broken import get_fallacy_detector cascading to all orchestration subpackages.
# The module targets the legacy router argumentation_analysis.pipelines.unified_pipeline
# (NOT the active orchestration/unified_pipeline.py).
# B-03 audit #814 — 88 tests archived (0 collected due to collection error).

collect_ignore = ["test_unified_pipelines.py"]
