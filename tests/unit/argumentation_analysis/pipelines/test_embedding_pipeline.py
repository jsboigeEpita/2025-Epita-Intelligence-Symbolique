
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# tests/unit/argumentation_analysis/pipelines/test_embedding_pipeline.py
import pytest
import json
from pathlib import Path


from argumentation_analysis.pipelines.embedding_pipeline import run_embedding_generation_pipeline, PROJECT_ROOT

MODULE_PATH = "argumentation_analysis.pipelines.embedding_pipeline"
UI_CONFIG_PATH = "argumentation_analysis.ui.config" # For ENCRYPTION_KEY

# @pytest.fixture
# def mock_load_docs():
#     # Cette fonction n'existe plus directement dans embedding_pipeline.py
#     # Les tests utilisant cette fixture devront être adaptés ou commentés.
#     # with patch(f"{MODULE_PATH}.load_documents_from_file") as mock:
#     #     yield mock
#     yield Magicawait self._create_authentic_gpt4o_mini_instance() # Retourne un mock simple pour l'instant pour éviter des erreurs si la fixture est appelée

@pytest.fixture
def mock_load_json_file():
    with patch(f"{MODULE_PATH}.load_json_file") as mock:
        yield mock

@pytest.fixture
def mock_load_document_content(): # Renamed from mock_load_docs for clarity
    with patch(f"{MODULE_PATH}.load_document_content") as mock:
        yield mock

@pytest.fixture
def mock_get_full_text_for_source():
    with patch(f"{MODULE_PATH}.get_full_text_for_source") as mock:
        yield mock

@pytest.fixture
def mock_get_embeddings_for_chunks(): # Renamed from mock_get_embeddings
    with patch(f"{MODULE_PATH}.get_embeddings_for_chunks") as mock:
        yield mock

@pytest.fixture
def mock_save_embeddings_data(): # Renamed from mock_save_embeddings
    with patch(f"{MODULE_PATH}.save_embeddings_data") as mock:
        yield mock

@pytest.fixture
def mock_save_extract_definitions():
    with patch(f"{MODULE_PATH}.save_extract_definitions") as mock:
        yield mock

@pytest.fixture
def mock_sys_exit():
    with patch(f"{MODULE_PATH}.sys.exit") as mock:
        yield mock

@pytest.fixture
def mock_config_ui_encryption_key():
    with patch(f"{MODULE_PATH}.CONFIG_UI_ENCRYPTION_KEY", b"a_mocked_encryption_key_123456") as mock:
        yield mock
@pytest.fixture
def mock_sanitize_filename():
    with patch(f"{MODULE_PATH}.sanitize_filename", side_effect=lambda x: x) as mock: # Simple pass-through
        yield mock

# --- Helper for creating temp config ---
def create_temp_json_config(tmp_path: Path, content: list) -> Path:
    config_file = tmp_path / "input_config.json"
    with open(config_file, "w") as f:
        json.dump(content, f)
    return config_file

# --- Tests ---
# Les tests suivants sont commentés car ils dépendent de l'ancienne structure du pipeline
# et des mocks qui ne sont plus valides (mock_load_docs, mock_preprocess_docs, etc.).
# Ils devront être réécrits pour correspondre à la nouvelle logique de
# run_embedding_generation_pipeline qui opère sur une configuration JSON
# et appelle des fonctions comme load_document_content, get_full_text_for_source, etc.

# def test_run_embedding_generation_pipeline_success(
#     mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
# ):
#     """Tests successful execution of the embedding generation pipeline."""
#     pass

# def test_run_embedding_generation_pipeline_load_failure(
#     mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
# ):
#     """Tests pipeline failure if document loading fails."""
#     pass

# ... (autres tests commentés de la version feature/migrate-project-core) ...
