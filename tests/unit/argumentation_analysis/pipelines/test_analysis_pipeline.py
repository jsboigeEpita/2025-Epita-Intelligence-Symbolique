# tests/unit/argumentation_analysis/pipelines/test_analysis_pipeline.py
import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.pipelines.analysis_pipeline import run_text_analysis_pipeline

MODULE_PATH = "src.argumentation_analysis.pipelines.analysis_pipeline"

@pytest.fixture
def mock_initialize_services():
    with patch(f"{MODULE_PATH}.initialize_analysis_services") as mock:
        yield mock

@pytest.fixture
def mock_perform_analysis():
    with patch(f"{MODULE_PATH}.perform_text_analysis") as mock:
        yield mock

@pytest.fixture
def mock_store_results():
    with patch(f"{MODULE_PATH}.store_analysis_results") as mock:
        yield mock

def test_run_text_analysis_pipeline_success(
    mock_initialize_services, mock_perform_analysis, mock_store_results
):
    """
    Tests the successful execution of the text analysis pipeline.
    """
    mock_initialize_services.return_value = {"service_status": "initialized"}
    mock_perform_analysis.return_value = {"analysis_complete": True, "results": "Mocked results"}
    mock_store_results.return_value = {"storage_status": "success"}

    text_input = "Sample text"
    analysis_config = {"lang": "en"}
    storage_settings = {"db": "test_db"}

    result = run_text_analysis_pipeline(text_input, analysis_config, storage_settings)

    mock_initialize_services.assert_called_once_with(analysis_config)
    mock_perform_analysis.assert_called_once_with(text_input, {"service_status": "initialized"})
    mock_store_results.assert_called_once_with(
        {"analysis_complete": True, "results": "Mocked results"}, storage_settings
    )

    assert result["pipeline_status"] == "success"
    assert result["analysis_output"] == {"analysis_complete": True, "results": "Mocked results"}
    assert result["storage_info"] == {"storage_status": "success"}

def test_run_text_analysis_pipeline_service_initialization_failure(
    mock_initialize_services, mock_perform_analysis, mock_store_results
):
    """
    Tests pipeline failure if service initialization fails.
    """
    mock_initialize_services.return_value = {"service_status": "failed", "error": "Init error"}

    text_input = "Sample text"
    analysis_config = {}
    storage_settings = {}

    result = run_text_analysis_pipeline(text_input, analysis_config, storage_settings)

    mock_initialize_services.assert_called_once_with(analysis_config)
    mock_perform_analysis.assert_not_called()
    mock_store_results.assert_not_called()

    assert result["pipeline_status"] == "failed"
    assert result["reason"] == "Service initialization error"

def test_run_text_analysis_pipeline_analysis_failure(
    mock_initialize_services, mock_perform_analysis, mock_store_results
):
    """
    Tests pipeline failure if text analysis fails.
    """
    mock_initialize_services.return_value = {"service_status": "initialized"}
    mock_perform_analysis.return_value = {"error": "Analysis error"}

    text_input = "Sample text"
    analysis_config = {}
    storage_settings = {}

    result = run_text_analysis_pipeline(text_input, analysis_config, storage_settings)

    mock_initialize_services.assert_called_once_with(analysis_config)
    mock_perform_analysis.assert_called_once_with(text_input, {"service_status": "initialized"})
    mock_store_results.assert_not_called()

    assert result["pipeline_status"] == "failed"
    assert result["reason"] == "Analysis error"

def test_run_text_analysis_pipeline_storage_failure(
    mock_initialize_services, mock_perform_analysis, mock_store_results
):
    """
    Tests pipeline failure if storing results fails.
    """
    mock_initialize_services.return_value = {"service_status": "initialized"}
    mock_perform_analysis.return_value = {"analysis_complete": True, "results": "Mocked results"}
    mock_store_results.return_value = {"storage_status": "failed", "error": "Storage error"}

    text_input = "Sample text"
    analysis_config = {}
    storage_settings = {}

    result = run_text_analysis_pipeline(text_input, analysis_config, storage_settings)

    mock_initialize_services.assert_called_once_with(analysis_config)
    mock_perform_analysis.assert_called_once_with(text_input, {"service_status": "initialized"})
    mock_store_results.assert_called_once_with(
        {"analysis_complete": True, "results": "Mocked results"}, storage_settings
    )

    assert result["pipeline_status"] == "failed"
    assert result["reason"] == "Storage error"

def test_run_text_analysis_pipeline_empty_input_handled_by_analysis_step(
    mock_initialize_services, mock_perform_analysis, mock_store_results
):
    """
    Tests how the pipeline handles empty text input, assuming perform_text_analysis handles it.
    """
    mock_initialize_services.return_value = {"service_status": "initialized"}
    # Simulate perform_text_analysis returning an error for empty input
    mock_perform_analysis.return_value = {"error": "No text data provided"}

    text_input = "" # Empty input
    analysis_config = {"lang": "en"}
    storage_settings = {"db": "test_db"}

    result = run_text_analysis_pipeline(text_input, analysis_config, storage_settings)

    mock_initialize_services.assert_called_once_with(analysis_config)
    mock_perform_analysis.assert_called_once_with(text_input, {"service_status": "initialized"})
    mock_store_results.assert_not_called() # Should not be called if analysis fails

    assert result["pipeline_status"] == "failed"
    assert result["reason"] == "No text data provided"