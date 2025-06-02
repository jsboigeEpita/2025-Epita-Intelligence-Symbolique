# tests/unit/argumentation_analysis/pipelines/test_embedding_pipeline.py
import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.pipelines.embedding_pipeline import run_embedding_generation_pipeline

MODULE_PATH = "src.argumentation_analysis.pipelines.embedding_pipeline"

@pytest.fixture
def mock_load_docs():
    with patch(f"{MODULE_PATH}.load_documents_from_file") as mock:
        yield mock

@pytest.fixture
def mock_preprocess_docs():
    with patch(f"{MODULE_PATH}.preprocess_documents_for_embedding") as mock:
        yield mock

@pytest.fixture
def mock_get_embeddings():
    with patch(f"{MODULE_PATH}.get_embeddings_for_chunks") as mock:
        yield mock

@pytest.fixture
def mock_save_embeddings():
    with patch(f"{MODULE_PATH}.save_embeddings_to_file") as mock:
        yield mock

@pytest.fixture
def default_config():
    return {
        "load_config": {"file_type": "txt"},
        "preprocess_config": {"chunk_size": 100},
        "embedding_config": {"model": "test_model"},
        "save_config": {"format": "json"}
    }

def test_run_embedding_generation_pipeline_success(
    mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
):
    """Tests successful execution of the embedding generation pipeline."""
    mock_load_docs.return_value = {"status": "success", "documents": ["doc1", "doc2"]}
    mock_preprocess_docs.return_value = {"status": "success", "processed_chunks": ["chunk1", "chunk2", "chunk3"]}
    mock_get_embeddings.return_value = {"status": "success", "embeddings": [[0.1], [0.2], [0.3]]}
    mock_save_embeddings.return_value = {"status": "success", "file_location": "output/path.json"}

    input_file = "input/data.txt"
    output_file = "output/path.json"

    result = run_embedding_generation_pipeline(input_file, output_file, default_config)

    mock_load_docs.assert_called_once_with(input_file, "txt")
    mock_preprocess_docs.assert_called_once_with(["doc1", "doc2"], default_config["preprocess_config"])
    mock_get_embeddings.assert_called_once_with(["chunk1", "chunk2", "chunk3"], default_config["embedding_config"])
    mock_save_embeddings.assert_called_once_with([[0.1], [0.2], [0.3]], output_file, "json")

    assert result["pipeline_status"] == "success"
    assert result["output_location"] == "output/path.json"
    assert result["embeddings_count"] == 3

def test_run_embedding_generation_pipeline_load_failure(
    mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
):
    """Tests pipeline failure if document loading fails."""
    mock_load_docs.return_value = {"error": "File not found", "documents": []}

    result = run_embedding_generation_pipeline("input.txt", "output.json", default_config)

    mock_load_docs.assert_called_once()
    mock_preprocess_docs.assert_not_called()
    mock_get_embeddings.assert_not_called()
    mock_save_embeddings.assert_not_called()

    assert result["pipeline_status"] == "failed"
    assert "Document loading error: File not found" in result["reason"]

def test_run_embedding_generation_pipeline_preprocess_failure(
    mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
):
    """Tests pipeline failure if preprocessing fails."""
    mock_load_docs.return_value = {"status": "success", "documents": ["doc1"]}
    mock_preprocess_docs.return_value = {"error": "Preprocessing issue", "processed_chunks": []}

    result = run_embedding_generation_pipeline("input.txt", "output.json", default_config)

    mock_load_docs.assert_called_once()
    mock_preprocess_docs.assert_called_once()
    mock_get_embeddings.assert_not_called()
    mock_save_embeddings.assert_not_called()

    assert result["pipeline_status"] == "failed"
    assert "Preprocessing error: Preprocessing issue" in result["reason"]

def test_run_embedding_generation_pipeline_embedding_failure(
    mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
):
    """Tests pipeline failure if embedding generation fails."""
    mock_load_docs.return_value = {"status": "success", "documents": ["doc1"]}
    mock_preprocess_docs.return_value = {"status": "success", "processed_chunks": ["chunk1"]}
    mock_get_embeddings.return_value = {"error": "Embedding model error", "embeddings": []}

    result = run_embedding_generation_pipeline("input.txt", "output.json", default_config)

    mock_load_docs.assert_called_once()
    mock_preprocess_docs.assert_called_once()
    mock_get_embeddings.assert_called_once()
    mock_save_embeddings.assert_not_called()

    assert result["pipeline_status"] == "failed"
    assert "Embedding generation error: Embedding model error" in result["reason"]

def test_run_embedding_generation_pipeline_save_failure(
    mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
):
    """Tests pipeline failure if saving embeddings fails."""
    mock_load_docs.return_value = {"status": "success", "documents": ["doc1"]}
    mock_preprocess_docs.return_value = {"status": "success", "processed_chunks": ["chunk1"]}
    mock_get_embeddings.return_value = {"status": "success", "embeddings": [[0.1]]}
    mock_save_embeddings.return_value = {"error": "Disk full"}

    result = run_embedding_generation_pipeline("input.txt", "output.json", default_config)

    mock_load_docs.assert_called_once()
    mock_preprocess_docs.assert_called_once()
    mock_get_embeddings.assert_called_once()
    mock_save_embeddings.assert_called_once()

    assert result["pipeline_status"] == "failed"
    assert "Saving embeddings error: Disk full" in result["reason"]

def test_run_embedding_generation_pipeline_no_documents_loaded(
    mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
):
    """Tests pipeline behavior when no documents are loaded, leading to preprocess failure."""
    mock_load_docs.return_value = {"status": "success", "documents": []} # No documents
    # Preprocess should fail if no documents are passed
    mock_preprocess_docs.return_value = {"error": "No documents to preprocess", "processed_chunks": []}


    result = run_embedding_generation_pipeline("input.txt", "output.json", default_config)

    mock_load_docs.assert_called_once()
    mock_preprocess_docs.assert_called_once_with([], default_config["preprocess_config"])
    mock_get_embeddings.assert_not_called()
    mock_save_embeddings.assert_not_called()

    assert result["pipeline_status"] == "failed"
    assert "Preprocessing error: No documents to preprocess" in result["reason"]

def test_run_embedding_generation_pipeline_no_chunks_to_embed(
    mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
):
    """Tests pipeline behavior when no chunks are produced, leading to embedding failure."""
    mock_load_docs.return_value = {"status": "success", "documents": ["doc1"]}
    mock_preprocess_docs.return_value = {"status": "success", "processed_chunks": []} # No chunks
    # Embedding should fail if no chunks are passed
    mock_get_embeddings.return_value = {"error": "No chunks to embed", "embeddings": []}

    result = run_embedding_generation_pipeline("input.txt", "output.json", default_config)

    mock_load_docs.assert_called_once()
    mock_preprocess_docs.assert_called_once()
    mock_get_embeddings.assert_called_once_with([], default_config["embedding_config"])
    mock_save_embeddings.assert_not_called()

    assert result["pipeline_status"] == "failed"
    assert "Embedding generation error: No chunks to embed" in result["reason"]

def test_run_embedding_generation_pipeline_no_embeddings_to_save(
    mock_load_docs, mock_preprocess_docs, mock_get_embeddings, mock_save_embeddings, default_config
):
    """Tests pipeline behavior when no embeddings are generated, leading to save failure."""
    mock_load_docs.return_value = {"status": "success", "documents": ["doc1"]}
    mock_preprocess_docs.return_value = {"status": "success", "processed_chunks": ["chunk1"]}
    mock_get_embeddings.return_value = {"status": "success", "embeddings": []} # No embeddings
    # Saving should fail if no embeddings are passed
    mock_save_embeddings.return_value = {"error": "No embeddings to save"}

    result = run_embedding_generation_pipeline("input.txt", "output.json", default_config)

    mock_load_docs.assert_called_once()
    mock_preprocess_docs.assert_called_once()
    mock_get_embeddings.assert_called_once()
    mock_save_embeddings.assert_called_once_with([], "output.json", "json")

    assert result["pipeline_status"] == "failed"
    assert "Saving embeddings error: No embeddings to save" in result["reason"]