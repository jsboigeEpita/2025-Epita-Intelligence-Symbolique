from unittest.mock import MagicMock
import pytest
from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
    UnifiedProductionAnalyzer,
)


def test_successful_simple_argument_analysis(
    mocker, successful_simple_argument_analysis_fixture_path
):
    """
    Test a successful analysis of a simple argument.
    """
    # Create an instance of the analyzer
    analyzer = UnifiedProductionAnalyzer()

    # Mock the subprocess.run method
    mock_run = mocker.patch("subprocess.run")

    # Call the method to be tested
    analyzer.run_jvm_based_analysis(successful_simple_argument_analysis_fixture_path)

    # Assert that subprocess.run was called with the correct arguments
    mock_run.assert_called_once()
    # You might want to add more specific assertions here
    # For instance, checking parts of the command passed to subprocess.run
