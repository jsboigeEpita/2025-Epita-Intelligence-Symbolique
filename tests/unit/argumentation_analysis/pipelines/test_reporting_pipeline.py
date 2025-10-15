# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# tests/unit/argumentation_analysis/pipelines/test_reporting_pipeline.py
import pytest

import pandas as actual_pandas_module  # Renommé pour clarté

# Capture des vrais types pandas avant tout mock potentiel par des fixtures ou autres imports
REAL_PANDAS_DATAFRAME_TYPE = actual_pandas_module.DataFrame
REAL_PANDAS_SERIES_TYPE = actual_pandas_module.Series
from pathlib import Path
import sys

from argumentation_analysis.pipelines.reporting_pipeline import (
    run_comprehensive_report_pipeline,
)

MODULE_PATH = "argumentation_analysis.pipelines.reporting_pipeline"
PANDAS_DATAFRAME_PATH = f"{MODULE_PATH}.pd.DataFrame"
MATPLOTLIB_PYPLOT_FIGURE_PATH = f"{MODULE_PATH}.plt.figure"
MATPLOTLIB_PYPLOT_CLOSE_PATH = f"{MODULE_PATH}.plt.close"
SEABORN_BARPLOT_PATH = f"{MODULE_PATH}.sns.barplot"

# @pytest.fixture
# def mock_load_results():
#     # Cette fonction n'existe plus directement dans reporting_pipeline.py
#     # with patch(f"{MODULE_PATH}.load_analysis_results") as mock:
#     #     yield mock
#     yield Magicawait self._create_authentic_gpt4o_mini_instance()


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
    return {"load_config": {"format": "json"}, "save_config": {}}


@pytest.fixture
def sample_analysis_data_list():  # Renommé pour refléter que c'est une liste
    return [
        {
            "text_id": "a1",
            "corpus_id": "corpus_A",
            "score": 0.8,
            "argument_type": "pro",
        },
        {
            "text_id": "a2",
            "corpus_id": "corpus_A",
            "score": 0.6,
            "argument_type": "con",
        },
        {
            "text_id": "b1",
            "corpus_id": "corpus_B",
            "score": 0.9,
            "argument_type": "pro",
        },
    ]


@pytest.fixture
def grouped_sample_analysis_data():  # Renommé pour clarté
    return {
        "corpus_A": [
            {
                "text_id": "a1",
                "corpus_id": "corpus_A",
                "score": 0.8,
                "argument_type": "pro",
            },
            {
                "text_id": "a2",
                "corpus_id": "corpus_A",
                "score": 0.6,
                "argument_type": "con",
            },
        ],
        "corpus_B": [
            {
                "text_id": "b1",
                "corpus_id": "corpus_B",
                "score": 0.9,
                "argument_type": "pro",
            }
        ],
    }


# Les tests suivants sont commentés car ils dépendent de l'ancienne structure du pipeline
# et des mocks qui ne sont plus valides (mock_load_results, etc.).
# Ils devront être réécrits pour correspondre à la nouvelle logique de
# run_comprehensive_report_pipeline qui opère sur des chemins de fichiers
# et appelle des fonctions comme load_json_file, load_text_file, etc.

# def test_run_comprehensive_report_pipeline_success(
#     mock_load_results, mock_group_results, mock_calculate_scores,
#     mock_generate_md, mock_save_html, default_config, sample_analysis_data
# ):
#     """Tests successful execution of the comprehensive reporting pipeline."""
#     pass

# def test_run_comprehensive_report_pipeline_load_failure(
#     mock_load_results, mock_group_results, mock_calculate_scores,
#     mock_generate_md, mock_save_html, default_config
# ):
#     """Tests pipeline failure if loading analysis results fails."""
#     pass

# ... (autres tests commentés de la version feature/migrate-project-core) ...
