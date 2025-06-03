# tests/unit/argumentation_analysis/pipelines/test_embedding_pipeline.py
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY

from argumentation_analysis.pipelines.embedding_pipeline import run_embedding_generation_pipeline, PROJECT_ROOT

MODULE_PATH = "argumentation_analysis.pipelines.embedding_pipeline"
UI_CONFIG_PATH = "argumentation_analysis.ui.config" # For ENCRYPTION_KEY

# --- Fixtures for Mocks ---
@pytest.fixture
def mock_setup_logging():
    with patch(f"{MODULE_PATH}.setup_logging") as mock:
        yield mock

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
    # This key needs to be bytes and of a valid length for cryptographic operations
    # if not mocking the crypto functions themselves. For simplicity, use a valid-looking key.
    # The actual value might not matter if save_extract_definitions is fully mocked.
    # A 32-byte key (256-bit) is common for AES.
    # Let's use a base64 encoded string that would decode to 32 bytes if it were real.
    # For the mock, the content doesn't strictly matter as long as it's bytes.
    # For example: b'test_key_for_mocking_1234567890' (32 bytes)
    # However, the original code uses `CONFIG_UI_ENCRYPTION_KEY[:10].decode('utf-8', 'ignore')` for logging
    # so it should be decodable.
    # Let's use a simple byte string.
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

def test_run_embedding_generation_pipeline_success_file_source(
    tmp_path: Path,
    mock_setup_logging: MagicMock,
    mock_load_json_file: MagicMock,
    mock_load_document_content: MagicMock,
    mock_get_embeddings_for_chunks: MagicMock,
    mock_save_embeddings_data: MagicMock,
    mock_save_extract_definitions: MagicMock,
    mock_sys_exit: MagicMock,
    mock_config_ui_encryption_key: MagicMock,
    mock_sanitize_filename: MagicMock
):
    """Tests successful execution with a local file source, needing text retrieval."""
    input_config_content = [
        {
            "id": "test_doc_1",
            "type": "file",
            "path": "data/test_document.txt", # Relative to project root
            "fetch_method": "file",
            "full_text": None # Needs retrieval
        },
        {
            "id": "test_doc_2",
            "type": "file",
            "path": "data/another_doc.txt",
            "fetch_method": "file",
            "full_text": "Pre-existing full text for doc 2." # Already present
        }
    ]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "output_config.json.gz.enc"
    embeddings_model = "test_model_001"

    mock_load_json_file.return_value = input_config_content
    mock_load_document_content.return_value = "Retrieved full text for doc 1."
    mock_get_embeddings_for_chunks.return_value = [[0.1, 0.2], [0.3, 0.4]] # Two embeddings
    mock_save_embeddings_data.return_value = True
    mock_save_extract_definitions.return_value = True

    run_embedding_generation_pipeline(
        input_config_path=None,
        json_string=None,
        input_json_file_path=input_json_path,
        output_config_path=output_config_path,
        generate_embeddings_model=embeddings_model,
        force_overwrite=True,
        log_level="DEBUG"
    )

    mock_load_json_file.assert_called_once_with(input_json_path)
    # Called for the first doc which has full_text = None
    expected_doc1_path = (PROJECT_ROOT / "data/test_document.txt").resolve()
    mock_load_document_content.assert_called_once_with(expected_doc1_path)

    # Check calls to get_embeddings_for_chunks
    expected_texts_for_embedding = [
        "Retrieved full text for doc 1.",
        "Pre-existing full text for doc 2."
    ]
    # mock_get_embeddings_for_chunks.assert_called_once_with(expected_texts_for_embedding, embeddings_model) # This was the error, pipeline calls it per doc

    # Check calls to save_embeddings_data (called twice, once for each doc)
    # This assertion is already covered by the re-run logic below.
    # assert mock_save_embeddings_data.call_count == 2
    # The re-run logic will reset call counts, so we check after the second run.
    expected_embeddings_output_dir = output_config_path.parent / "embeddings_data"
    
    # Call 1 for doc1
    call_args_doc1 = mock_save_embeddings_data.call_args_list[0]
    expected_data_doc1 = {
        "source_id": "test_doc_1",
        "model_name": embeddings_model,
        "text_chunks": ["Retrieved full text for doc 1."],
        "embeddings": [[0.1, 0.2]] # Assuming get_embeddings_for_chunks returns list of embeddings per call
    }
    # We need to adjust the mock or the expectation if get_embeddings_for_chunks is called once for all texts
    # Based on the pipeline code: get_embeddings_for_chunks([text1, text2], model) -> [emb1, emb2]
    # Then the loop in pipeline does: embeddings = get_embeddings_for_chunks(text_chunks, ...) where text_chunks = [current_full_text]
    # So, get_embeddings_for_chunks is called PER document. Let's adjust the mock for that.

    # Re-mocking get_embeddings_for_chunks to be called per document
    mock_get_embeddings_for_chunks.side_effect = [
        [[0.1, 0.2]], # For doc1
        [[0.3, 0.4]]  # For doc2
    ]
    # Reset mocks for the re-run if necessary, or ensure side_effect handles multiple calls if the test structure implies it.
    # For this specific test, the re-run is to test the side_effect logic of get_embeddings_for_chunks.
    # The initial call to run_embedding_generation_pipeline already happened with the initial mock setup.
    # The issue was the assert_called_once_with before the re-run.
    # The re-run itself is part of the test's internal logic to set up the side_effect correctly.
    # The assertions below are for the state *after* the second run_embedding_generation_pipeline call.

    # Re-run with adjusted mock (this is the second call to the pipeline in this test)
    # We need to reset relevant mocks if their state from the first run interferes.
    mock_load_json_file.reset_mock()
    mock_load_document_content.reset_mock()
    mock_get_embeddings_for_chunks.reset_mock() # Reset to apply new side_effect cleanly
    mock_save_embeddings_data.reset_mock()
    mock_save_extract_definitions.reset_mock()
    mock_sys_exit.reset_mock() # Ensure it's clean for this run

    mock_load_json_file.return_value = input_config_content # Re-assign for the second run
    mock_load_document_content.return_value = "Retrieved full text for doc 1." # Re-assign
    mock_get_embeddings_for_chunks.side_effect = [ # This is the key part for the second run
        [[0.1, 0.2]], # For doc1
        [[0.3, 0.4]]  # For doc2
    ]
    mock_save_embeddings_data.return_value = True # Re-assign
    mock_save_extract_definitions.return_value = True # Re-assign


    run_embedding_generation_pipeline(
        input_config_path=None, json_string=None, input_json_file_path=input_json_path,
        output_config_path=output_config_path, generate_embeddings_model=embeddings_model,
        force_overwrite=True, log_level="DEBUG"
    )
    
    # Assertions after re-run with corrected mock_get_embeddings_for_chunks
    assert mock_get_embeddings_for_chunks.call_count == 2 # Called once for each of the 2 documents
    mock_get_embeddings_for_chunks.assert_any_call(["Retrieved full text for doc 1."], embeddings_model)
    mock_get_embeddings_for_chunks.assert_any_call(["Pre-existing full text for doc 2."], embeddings_model)

    assert mock_save_embeddings_data.call_count == 2 # Still 2, one per doc
    
    # Check save_embeddings_data call for doc1
    saved_data_doc1 = mock_save_embeddings_data.call_args_list[0][0][0]
    saved_path_doc1 = mock_save_embeddings_data.call_args_list[0][0][1]
    assert saved_data_doc1["source_id"] == "test_doc_1"
    assert saved_data_doc1["embeddings"] == [[0.1, 0.2]]
    assert saved_path_doc1 == expected_embeddings_output_dir / "embedding_test_doc_1_model_test_model_001.json"

    # Check save_embeddings_data call for doc2
    saved_data_doc2 = mock_save_embeddings_data.call_args_list[1][0][0]
    saved_path_doc2 = mock_save_embeddings_data.call_args_list[1][0][1]
    assert saved_data_doc2["source_id"] == "test_doc_2"
    assert saved_data_doc2["embeddings"] == [[0.3, 0.4]]
    assert saved_path_doc2 == expected_embeddings_output_dir / "embedding_test_doc_2_model_test_model_001.json"


    # Check call to save_extract_definitions
    expected_final_definitions = [
        {
            "id": "test_doc_1", "type": "file", "path": "data/test_document.txt",
            "fetch_method": "file", "full_text": "Retrieved full text for doc 1."
        },
        {
            "id": "test_doc_2", "type": "file", "path": "data/another_doc.txt",
            "fetch_method": "file", "full_text": "Pre-existing full text for doc 2."
        }
    ]
    mock_save_extract_definitions.assert_called_once_with(
        extract_definitions=expected_final_definitions,
        config_file=output_config_path,
        b64_derived_key=mock_config_ui_encryption_key, # Or the actual mocked value
        embed_full_text=True
    )
    mock_sys_exit.assert_not_called()

def test_run_embedding_generation_pipeline_success_url_source(
    tmp_path: Path, mock_setup_logging: MagicMock, mock_load_json_file: MagicMock,
    mock_get_full_text_for_source: MagicMock, mock_get_embeddings_for_chunks: MagicMock,
    mock_save_embeddings_data: MagicMock, mock_save_extract_definitions: MagicMock,
    mock_sys_exit: MagicMock, mock_config_ui_encryption_key: MagicMock,
    mock_sanitize_filename: MagicMock
):
    """Tests successful execution with a URL source needing text retrieval."""
    input_config_content = [{
        "id": "web_page_1", "type": "url", "path": "http://example.com/page1",
        "fetch_method": "url", "full_text": None
    }]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "output_config_url.json.gz.enc"
    embeddings_model = "test_model_url"

    mock_load_json_file.return_value = input_config_content
    mock_get_full_text_for_source.return_value = "Retrieved web page content."
    mock_get_embeddings_for_chunks.return_value = [[0.5, 0.6]] # Corrected: single embedding for the single text
    mock_save_embeddings_data.return_value = True
    mock_save_extract_definitions.return_value = True

    run_embedding_generation_pipeline(
        input_json_file_path=input_json_path, output_config_path=output_config_path,
        generate_embeddings_model=embeddings_model, force_overwrite=True,
        input_config_path=None, json_string=None, log_level="DEBUG"
    )

    mock_load_json_file.assert_called_once_with(input_json_path)
    mock_get_full_text_for_source.assert_called_once_with(input_config_content[0], app_config=None)
    mock_get_embeddings_for_chunks.assert_called_once_with(["Retrieved web page content."], embeddings_model)
    
    expected_embeddings_output_dir = output_config_path.parent / "embeddings_data"
    expected_data = {
        "source_id": "web_page_1", "model_name": embeddings_model,
        "text_chunks": ["Retrieved web page content."], "embeddings": [[0.5, 0.6]]
    }
    mock_save_embeddings_data.assert_called_once_with(
        expected_data,
        expected_embeddings_output_dir / "embedding_web_page_1_model_test_model_url.json"
    )
    
    expected_final_definitions = [{
        "id": "web_page_1", "type": "url", "path": "http://example.com/page1",
        "fetch_method": "url", "full_text": "Retrieved web page content."
    }]
    mock_save_extract_definitions.assert_called_once_with(
        extract_definitions=expected_final_definitions,
        config_file=output_config_path,
        b64_derived_key=mock_config_ui_encryption_key,
        embed_full_text=True
    )
    mock_sys_exit.assert_not_called()


def test_run_embedding_generation_pipeline_input_json_file_not_found(
    tmp_path: Path, mock_sys_exit: MagicMock, mock_setup_logging: MagicMock
):
    """Tests pipeline exit if input_json_file_path does not exist."""
    non_existent_input_path = tmp_path / "non_existent_config.json"
    output_config_path = tmp_path / "output_config.json.gz.enc"

    # Configure mock_sys_exit to raise an exception to halt execution after it's called
    mock_sys_exit.side_effect = SystemExit(1)

    with pytest.raises(SystemExit) as excinfo:
        run_embedding_generation_pipeline(
            input_json_file_path=non_existent_input_path,
            output_config_path=output_config_path,
            generate_embeddings_model="any_model",
            force_overwrite=False, input_config_path=None, json_string=None
        )
    
    assert excinfo.value.code == 1
    mock_sys_exit.assert_called_once_with(1)

def test_run_embedding_generation_pipeline_output_exists_no_force(
    tmp_path: Path, mock_sys_exit: MagicMock, mock_load_json_file: MagicMock,
    mock_setup_logging: MagicMock
):
    """Tests pipeline exit if output_config_path exists and force_overwrite is False."""
    input_config_content = [{"id": "doc1"}]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "existing_output.json.gz.enc"
    output_config_path.touch() # Create the file

    mock_load_json_file.return_value = input_config_content

    run_embedding_generation_pipeline(
        input_json_file_path=input_json_path,
        output_config_path=output_config_path,
        generate_embeddings_model=None, # No embedding generation needed for this test
        force_overwrite=False, input_config_path=None, json_string=None
    )
    mock_sys_exit.assert_called_once_with(1)


def test_run_embedding_generation_pipeline_json_string_malformed(
    tmp_path: Path, mock_sys_exit: MagicMock, mock_setup_logging: MagicMock,
    mock_config_ui_encryption_key: MagicMock
):
    """Tests pipeline exit if json_string is malformed."""
    malformed_json_string = "{'id': 'doc1', 'type': 'file'" # Missing closing brace
    output_config_path = tmp_path / "output_config.json.gz.enc"

    run_embedding_generation_pipeline(
        json_string=malformed_json_string,
        output_config_path=output_config_path,
        generate_embeddings_model=None, force_overwrite=True,
        input_config_path=None, input_json_file_path=None
    )
    mock_sys_exit.assert_called_once_with(1)

def test_run_embedding_generation_pipeline_load_document_content_fails(
    tmp_path: Path, mock_setup_logging: MagicMock, mock_load_json_file: MagicMock,
    mock_load_document_content: MagicMock, mock_save_extract_definitions: MagicMock,
    mock_sys_exit: MagicMock, mock_config_ui_encryption_key: MagicMock
):
    """Tests behavior when load_document_content returns None (simulating read failure)."""
    input_config_content = [{
        "id": "doc_fail", "type": "file", "path": "path/to/failing_doc.txt",
        "fetch_method": "file", "full_text": None
    }]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "output_config_load_fail.json.gz.enc"

    mock_load_json_file.return_value = input_config_content
    mock_load_document_content.return_value = None # Simulate failure
    mock_save_extract_definitions.return_value = True # Assume save still called

    run_embedding_generation_pipeline(
        input_json_file_path=input_json_path, output_config_path=output_config_path,
        generate_embeddings_model=None, force_overwrite=True, # No embedding generation
        input_config_path=None, json_string=None
    )

    mock_load_document_content.assert_called_once()
    # The pipeline should continue and try to save the (un-updated) definitions
    expected_final_definitions = [{
        "id": "doc_fail", "type": "file", "path": "path/to/failing_doc.txt",
        "fetch_method": "file", "full_text": None # Still None
    }]
    mock_save_extract_definitions.assert_called_once_with(
        extract_definitions=expected_final_definitions,
        config_file=output_config_path,
        b64_derived_key=mock_config_ui_encryption_key,
        embed_full_text=True
    )
    mock_sys_exit.assert_not_called() # Should not exit if only text retrieval fails for one source


def test_run_embedding_generation_pipeline_get_embeddings_fails(
    tmp_path: Path, mock_setup_logging: MagicMock, mock_load_json_file: MagicMock,
    mock_get_embeddings_for_chunks: MagicMock, mock_save_extract_definitions: MagicMock,
    mock_sys_exit: MagicMock, mock_config_ui_encryption_key: MagicMock,
    mock_sanitize_filename: MagicMock
):
    """Tests behavior when get_embeddings_for_chunks raises an exception."""
    input_config_content = [{
        "id": "doc_emb_fail", "type": "text", "full_text": "Some text to embed."
    }]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "output_config_emb_fail.json.gz.enc"
    embeddings_model = "failing_model"

    mock_load_json_file.return_value = input_config_content
    mock_get_embeddings_for_chunks.side_effect = Exception("Embedding API down")
    mock_save_extract_definitions.return_value = True

    run_embedding_generation_pipeline(
        input_json_file_path=input_json_path, output_config_path=output_config_path,
        generate_embeddings_model=embeddings_model, force_overwrite=True,
        input_config_path=None, json_string=None
    )

    mock_get_embeddings_for_chunks.assert_called_once_with(["Some text to embed."], embeddings_model)
    # Save of definitions should still happen
    mock_save_extract_definitions.assert_called_once()
    mock_sys_exit.assert_not_called() # Embedding failure for one source doesn't stop all


def test_run_embedding_generation_pipeline_save_embeddings_fails(
    tmp_path: Path, mock_setup_logging: MagicMock, mock_load_json_file: MagicMock,
    mock_get_embeddings_for_chunks: MagicMock, mock_save_embeddings_data: MagicMock,
    mock_save_extract_definitions: MagicMock, mock_sys_exit: MagicMock,
    mock_config_ui_encryption_key: MagicMock, mock_sanitize_filename: MagicMock
):
    """Tests behavior when save_embeddings_data returns False."""
    input_config_content = [{"id": "doc_save_fail", "full_text": "Text"}]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "output_config_save_fail.json.gz.enc"
    embeddings_model = "model_x"

    mock_load_json_file.return_value = input_config_content
    mock_get_embeddings_for_chunks.return_value = [[[0.7]]]
    mock_save_embeddings_data.return_value = False # Simulate save failure
    mock_save_extract_definitions.return_value = True

    run_embedding_generation_pipeline(
        input_json_file_path=input_json_path, output_config_path=output_config_path,
        generate_embeddings_model=embeddings_model, force_overwrite=True,
        input_config_path=None, json_string=None
    )

    mock_save_embeddings_data.assert_called_once()
    mock_save_extract_definitions.assert_called_once() # Still called
    mock_sys_exit.assert_not_called()


def test_run_embedding_generation_pipeline_no_embeddings_model_provided(
    tmp_path: Path, mock_setup_logging: MagicMock, mock_load_json_file: MagicMock,
    mock_get_embeddings_for_chunks: MagicMock, mock_save_embeddings_data: MagicMock,
    mock_save_extract_definitions: MagicMock, mock_sys_exit: MagicMock,
    mock_config_ui_encryption_key: MagicMock
):
    """Tests that no embedding generation occurs if generate_embeddings_model is None."""
    input_config_content = [{"id": "doc_no_emb", "full_text": "Some text"}]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "output_config_no_emb.json.gz.enc"

    mock_load_json_file.return_value = input_config_content
    mock_save_extract_definitions.return_value = True

    run_embedding_generation_pipeline(
        input_json_file_path=input_json_path, output_config_path=output_config_path,
        generate_embeddings_model=None, # Key for this test
        force_overwrite=True, input_config_path=None, json_string=None
    )

    mock_get_embeddings_for_chunks.assert_not_called()
    mock_save_embeddings_data.assert_not_called()
    mock_save_extract_definitions.assert_called_once() # Definitions still saved
    mock_sys_exit.assert_not_called()

def test_run_embedding_generation_pipeline_no_full_text_for_embedding(
    tmp_path: Path, mock_setup_logging: MagicMock, mock_load_json_file: MagicMock,
    mock_load_document_content: MagicMock, mock_get_embeddings_for_chunks: MagicMock,
    mock_save_extract_definitions: MagicMock, mock_sys_exit: MagicMock,
    mock_config_ui_encryption_key: MagicMock
):
    """Tests that embedding is skipped if full_text is missing and cannot be retrieved."""
    input_config_content = [{
        "id": "doc_no_text", "type": "file", "path": "non_retrievable.txt",
        "fetch_method": "file", "full_text": None
    }]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "output_config_no_text.json.gz.enc"

    mock_load_json_file.return_value = input_config_content
    mock_load_document_content.return_value = None # Retrieval fails
    mock_save_extract_definitions.return_value = True

    run_embedding_generation_pipeline(
        input_json_file_path=input_json_path, output_config_path=output_config_path,
        generate_embeddings_model="any_model", force_overwrite=True,
        input_config_path=None, json_string=None
    )

    mock_load_document_content.assert_called_once()
    mock_get_embeddings_for_chunks.assert_not_called() # Skipped due to no text
    mock_save_extract_definitions.assert_called_once()
    mock_sys_exit.assert_not_called()

def test_run_embedding_generation_pipeline_final_save_definitions_fails(
    tmp_path: Path, mock_setup_logging: MagicMock, mock_load_json_file: MagicMock,
    mock_save_extract_definitions: MagicMock, mock_sys_exit: MagicMock,
    mock_config_ui_encryption_key: MagicMock
):
    """Tests pipeline exit if the final save_extract_definitions fails."""
    input_config_content = [{"id": "doc_final_save_fail", "full_text": "Text"}]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "output_config_final_save_fail.json.gz.enc"

    mock_load_json_file.return_value = input_config_content
    mock_save_extract_definitions.return_value = False # Simulate final save failure

    run_embedding_generation_pipeline(
        input_json_file_path=input_json_path, output_config_path=output_config_path,
        generate_embeddings_model=None, force_overwrite=True,
        input_config_path=None, json_string=None
    )
    # The pipeline currently logs an error but doesn't sys.exit if save_extract_definitions returns False.
    # If this behavior changes to sys.exit(1), this assertion needs to be updated.
    # For now, we check that sys.exit was NOT called due to this specific failure.
    # However, if the *exception* occurs in save_extract_definitions, it *will* sys.exit(1).
    mock_save_extract_definitions.assert_called_once()
    mock_sys_exit.assert_not_called() # Based on current pipeline code for return False

def test_run_embedding_generation_pipeline_final_save_definitions_exception(
    tmp_path: Path, mock_setup_logging: MagicMock, mock_load_json_file: MagicMock,
    mock_save_extract_definitions: MagicMock, mock_sys_exit: MagicMock,
    mock_config_ui_encryption_key: MagicMock
):
    """Tests pipeline exit if save_extract_definitions raises an exception."""
    input_config_content = [{"id": "doc_final_save_exception", "full_text": "Text"}]
    input_json_path = create_temp_json_config(tmp_path, input_config_content)
    output_config_path = tmp_path / "output_config_final_save_exception.json.gz.enc"

    mock_load_json_file.return_value = input_config_content
    mock_save_extract_definitions.side_effect = Exception("Disk full during final save")

    run_embedding_generation_pipeline(
        input_json_file_path=input_json_path, output_config_path=output_config_path,
        generate_embeddings_model=None, force_overwrite=True,
        input_config_path=None, json_string=None
    )
    mock_save_extract_definitions.assert_called_once()
    mock_sys_exit.assert_called_once_with(1) # Exception in save leads to exit