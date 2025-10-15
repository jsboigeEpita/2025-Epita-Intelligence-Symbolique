import pytest
from argumentation_analysis.utils.unified_pipeline import (
    UnifiedAnalysisPipeline,
    AnalysisConfig,
    AnalysisMode,
)


@pytest.mark.use_real_numpy
async def test_full_analysis_workflow_simple_text():
    """
    Tests the full analysis pipeline with a simple, non-controversial text.
    Verifies that the pipeline runs without errors and produces a basic result.
    """
    # Arrange
    config = AnalysisConfig(
        analysis_modes=[AnalysisMode.FALLACIES],
        require_real_llm=False,  # Use mocks for this functional test
    )
    pipeline = UnifiedAnalysisPipeline(config)
    sample_text = "The sky is blue. Grass is green."

    # Act
    result = await pipeline.analyze_text(sample_text)

    # Assert
    assert result is not None
    assert result.status == "completed", f"Analysis failed with errors: {result.errors}"
    assert "fallacies" in result.results
    # Using a mock, we expect a specific mock result.
    assert result.results["fallacies"]["authentic"] is False
    assert (
        len(result.errors) == 0
    ), f"No errors should be reported, but got: {result.errors}"
