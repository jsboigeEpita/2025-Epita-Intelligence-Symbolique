# tests/unit/argumentation_analysis/pipelines/test_reporting_pipeline.py
import pytest
from unittest.mock import patch, MagicMock, call

from argumentation_analysis.pipelines.reporting_pipeline import run_comprehensive_report_pipeline

MODULE_PATH = "argumentation_analysis.pipelines.reporting_pipeline"

@pytest.fixture
def mock_load_results():
    with patch(f"{MODULE_PATH}.load_analysis_results") as mock:
        yield mock

@pytest.fixture
def mock_group_results():
    with patch(f"{MODULE_PATH}.group_results_by_corpus") as mock:
        yield mock

@pytest.fixture
def mock_calculate_scores():
    with patch(f"{MODULE_PATH}.calculate_average_scores") as mock:
        yield mock

@pytest.fixture
def mock_generate_md():
    with patch(f"{MODULE_PATH}.generate_markdown_report_for_corpus") as mock:
        yield mock

@pytest.fixture
def mock_save_html():
    with patch(f"{MODULE_PATH}.save_markdown_to_html") as mock:
        yield mock

@pytest.fixture
def default_config():
    return {
        "load_config": {"format": "json"},
        "save_config": {}
    }

@pytest.fixture
def sample_analysis_data():
    return {
        "corpus_A": [{"text_id": "a1", "score": 0.8}, {"text_id": "a2", "score": 0.6}],
        "corpus_B": [{"text_id": "b1", "score": 0.9}]
    }

def test_run_comprehensive_report_pipeline_success(
    mock_load_results, mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config, sample_analysis_data
):
    """Tests successful execution of the comprehensive reporting pipeline."""
    mock_load_results.return_value = {"status": "success", "data": sample_analysis_data}
    mock_group_results.return_value = {"status": "success", "grouped_data": sample_analysis_data}
    
    # Mock calculate_average_scores to return different averages for different corpora
    def calculate_side_effect(corpus_data):
        if corpus_data == sample_analysis_data["corpus_A"]:
            return {"status": "success", "average_score": 0.7}
        elif corpus_data == sample_analysis_data["corpus_B"]:
            return {"status": "success", "average_score": 0.9}
        return {"error": "Unknown corpus data"}
    mock_calculate_scores.side_effect = calculate_side_effect
    
    mock_generate_md.side_effect = [
        {"status": "success", "markdown": "Report A"},
        {"status": "success", "markdown": "Report B"}
    ]
    mock_save_html.return_value = {"status": "success", "html_location": "output/report.html"}

    results_path = "input/results.json"
    output_path = "output/report.html"

    result = run_comprehensive_report_pipeline(results_path, output_path, default_config)

    mock_load_results.assert_called_once_with(results_path, "json")
    mock_group_results.assert_called_once_with(sample_analysis_data)
    
    expected_calculate_calls = [
        call(sample_analysis_data["corpus_A"]),
        call(sample_analysis_data["corpus_B"])
    ]
    mock_calculate_scores.assert_has_calls(expected_calculate_calls, any_order=True) # Order might vary due to dict iteration

    expected_generate_md_calls = [
        call("corpus_A", sample_analysis_data["corpus_A"], 0.7),
        call("corpus_B", sample_analysis_data["corpus_B"], 0.9)
    ]
    # We need to check calls carefully due to dict iteration order for corpora
    # This check assumes corpus_A is processed before corpus_B based on typical dict iteration.
    # If this is not guaranteed, a more robust check is needed.
    assert mock_generate_md.call_args_list[0] in expected_generate_md_calls
    assert mock_generate_md.call_args_list[1] in expected_generate_md_calls


    expected_final_md = "# Comprehensive Analysis Report\n\nReport A\nReport B\n"
    mock_save_html.assert_called_once_with(expected_final_md, output_path)

    assert result["pipeline_status"] == "success"
    assert result["report_location"] == "output/report.html"
    assert result["corpora_processed"] == 2

def test_run_comprehensive_report_pipeline_load_failure(
    mock_load_results, mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config
):
    """Tests pipeline failure if loading analysis results fails."""
    mock_load_results.return_value = {"error": "File not found", "data": None}

    result = run_comprehensive_report_pipeline("input.json", "output.html", default_config)

    mock_load_results.assert_called_once()
    mock_group_results.assert_not_called()
    mock_calculate_scores.assert_not_called()
    mock_generate_md.assert_not_called()
    mock_save_html.assert_not_called()

    assert result["pipeline_status"] == "failed"
    assert "Loading results error: File not found" in result["reason"]

def test_run_comprehensive_report_pipeline_grouping_failure(
    mock_load_results, mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config, sample_analysis_data
):
    """Tests pipeline failure if grouping results fails."""
    mock_load_results.return_value = {"status": "success", "data": sample_analysis_data}
    mock_group_results.return_value = {"error": "Grouping issue", "grouped_data": None}

    result = run_comprehensive_report_pipeline("input.json", "output.html", default_config)

    mock_load_results.assert_called_once()
    mock_group_results.assert_called_once()
    mock_calculate_scores.assert_not_called()
    mock_generate_md.assert_not_called()
    mock_save_html.assert_not_called()

    assert result["pipeline_status"] == "failed"
    assert "Grouping error: Grouping issue" in result["reason"]


def test_run_comprehensive_report_pipeline_calculate_score_failure_for_one_corpus(
    mock_load_results, mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config, sample_analysis_data
):
    """Tests behavior when calculating score fails for one corpus but succeeds for another."""
    mock_load_results.return_value = {"status": "success", "data": sample_analysis_data}
    mock_group_results.return_value = {"status": "success", "grouped_data": sample_analysis_data}
    
    mock_calculate_scores.side_effect = [
        {"error": "Calc error for A", "average_score": None}, # Fails for corpus_A
        {"status": "success", "average_score": 0.9}          # Succeeds for corpus_B
    ]
    mock_generate_md.return_value = {"status": "success", "markdown": "Report B"} # Only B is generated
    mock_save_html.return_value = {"status": "success", "html_location": "output/report.html"}

    result = run_comprehensive_report_pipeline("input.json", "output.html", default_config)

    mock_load_results.assert_called_once()
    mock_group_results.assert_called_once()
    
    # Order of calls to calculate_scores might vary, check count and that generate_md is called for B
    assert mock_calculate_scores.call_count == 2 
    # This assertion depends on the iteration order of sample_analysis_data.
    # If corpus_A is processed first:
    mock_generate_md.assert_called_once_with("corpus_B", sample_analysis_data["corpus_B"], 0.9)
    
    expected_final_md = "# Comprehensive Analysis Report\n\n## Error processing corpus: corpus_A\n - Calc error for A\n\nReport B\n"
    mock_save_html.assert_called_once_with(expected_final_md, "output.html")

    assert result["pipeline_status"] == "success" # Pipeline can succeed if at least one corpus is processed
    assert result["corpora_processed"] == 1


def test_run_comprehensive_report_pipeline_generate_md_failure_for_one_corpus(
    mock_load_results, mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config, sample_analysis_data
):
    """Tests behavior when markdown generation fails for one corpus."""
    mock_load_results.return_value = {"status": "success", "data": sample_analysis_data}
    mock_group_results.return_value = {"status": "success", "grouped_data": sample_analysis_data}
    mock_calculate_scores.side_effect = [
        {"status": "success", "average_score": 0.7},
        {"status": "success", "average_score": 0.9}
    ]
    mock_generate_md.side_effect = [
        {"error": "MD gen error for A", "markdown": ""}, # Fails for corpus_A
        {"status": "success", "markdown": "Report B"}     # Succeeds for corpus_B
    ]
    mock_save_html.return_value = {"status": "success", "html_location": "output/report.html"}

    result = run_comprehensive_report_pipeline("input.json", "output.html", default_config)
    
    # Assuming corpus_A is processed first due to dict iteration
    expected_final_md = "# Comprehensive Analysis Report\n\n## Error generating report for corpus: corpus_A\n - MD gen error for A\n\nReport B\n"
    mock_save_html.assert_called_once_with(expected_final_md, "output.html")
    
    assert result["pipeline_status"] == "success"
    assert result["corpora_processed"] == 1


def test_run_comprehensive_report_pipeline_save_html_failure(
    mock_load_results, mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config, sample_analysis_data
):
    """Tests pipeline failure if saving the final HTML report fails."""
    mock_load_results.return_value = {"status": "success", "data": sample_analysis_data}
    mock_group_results.return_value = {"status": "success", "grouped_data": sample_analysis_data}
    mock_calculate_scores.return_value = {"status": "success", "average_score": 0.75}
    mock_generate_md.return_value = {"status": "success", "markdown": "Some Report"}
    mock_save_html.return_value = {"error": "Disk full"}

    result = run_comprehensive_report_pipeline("input.json", "output.html", default_config)

    mock_save_html.assert_called_once()
    assert result["pipeline_status"] == "failed"
    assert "Saving report error: Disk full" in result["reason"]

def test_run_comprehensive_report_pipeline_no_data_loaded(
    mock_load_results, mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config
):
    """Tests pipeline behavior when no data is loaded (e.g., empty results file)."""
    mock_load_results.return_value = {"status": "success", "data": {}} # Empty data
    mock_group_results.return_value = {"status": "success", "grouped_data": {}}
    mock_save_html.return_value = {"status": "success", "html_location": "output/empty_report.html"}

    result = run_comprehensive_report_pipeline("input.json", "output/empty_report.html", default_config)

    mock_load_results.assert_called_once()
    mock_group_results.assert_called_once_with({})
    mock_calculate_scores.assert_not_called()
    mock_generate_md.assert_not_called()
    
    expected_empty_report_md = "# Comprehensive Analysis Report\n\n"
    mock_save_html.assert_called_once_with(expected_empty_report_md, "output/empty_report.html")

    assert result["pipeline_status"] == "success" # Success, but no corpora processed
    assert result["report_location"] == "output/empty_report.html"
    assert result["corpora_processed"] == 0

def test_run_comprehensive_report_pipeline_all_corpora_fail_processing(
    mock_load_results, mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config, sample_analysis_data
):
    """Tests pipeline failure if all corpora fail during processing (e.g., score calculation)."""
    mock_load_results.return_value = {"status": "success", "data": sample_analysis_data}
    mock_group_results.return_value = {"status": "success", "grouped_data": sample_analysis_data}
    mock_calculate_scores.return_value = {"error": "Generic calc error", "average_score": None} # All fail

    result = run_comprehensive_report_pipeline("input.json", "output.html", default_config)

    mock_generate_md.assert_not_called() # No MD should be generated if all calcs fail
    mock_save_html.assert_not_called() # No HTML should be saved

    assert result["pipeline_status"] == "failed"
    assert result["reason"] == "No corpus reports generated successfully."