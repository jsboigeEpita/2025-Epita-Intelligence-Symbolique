# -*- coding: utf-8 -*-
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import uuid 

from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractResult
from argumentation_analysis.core.communication import MessageMiddleware

@pytest.fixture
def mock_operational_state():
    state = MagicMock(spec=OperationalState)
    # La méthode appelée par OperationalAgent.register_task est self.operational_state.add_task
    def mock_add_task(task_data):
        return task_data.get("id", f"mock_task_id_{uuid.uuid4().hex[:4]}")
    state.add_task = MagicMock(side_effect=mock_add_task) # Mocker add_task
    state.update_task_status = MagicMock()
    state.update_metrics = MagicMock()
    return state

@pytest.fixture
def mock_middleware_for_adapter():
    middleware = MagicMock(spec=MessageMiddleware)
    mock_channel = MagicMock()
    middleware.get_channel.return_value = mock_channel
    return middleware

@pytest.fixture
@patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.setup_extract_agent')
async def extract_agent_adapter_initialized(mock_setup_extract_agent, mock_operational_state, mock_middleware_for_adapter):
    mock_kernel = MagicMock()
    mock_extract_agent_instance = AsyncMock() 
    mock_setup_extract_agent.return_value = (mock_kernel, mock_extract_agent_instance)
    
    adapter = ExtractAgentAdapter(operational_state=mock_operational_state, middleware=mock_middleware_for_adapter)
    await adapter.initialize() 
    adapter.extract_agent = mock_extract_agent_instance 
    return adapter

@pytest.fixture
def extract_agent_adapter_not_initialized(mock_operational_state, mock_middleware_for_adapter):
    adapter = ExtractAgentAdapter(operational_state=mock_operational_state, middleware=mock_middleware_for_adapter)
    return adapter

def test_extract_agent_adapter_initialization_name(mock_operational_state, mock_middleware_for_adapter):
    adapter_default_name = ExtractAgentAdapter(operational_state=mock_operational_state, middleware=mock_middleware_for_adapter)
    assert adapter_default_name.name == "ExtractAgent"
    
    adapter_custom_name = ExtractAgentAdapter(name="MyExtractor", operational_state=mock_operational_state, middleware=mock_middleware_for_adapter)
    assert adapter_custom_name.name == "MyExtractor"
    assert not adapter_custom_name.initialized

@pytest.mark.anyio 
async def test_initialize_success(extract_agent_adapter_not_initialized):
    adapter = extract_agent_adapter_not_initialized 
    mock_kernel_instance = MagicMock()
    mock_extract_agent_instance = MagicMock() 

    with patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.setup_extract_agent', 
               new_callable=AsyncMock) as mock_async_setup:
        mock_async_setup.return_value = (mock_kernel_instance, mock_extract_agent_instance)
        
        assert not adapter.initialized
        success = await adapter.initialize() 
        
        assert success is True
        assert adapter.initialized is True
        assert adapter.kernel == mock_kernel_instance
        assert adapter.extract_agent == mock_extract_agent_instance
        mock_async_setup.assert_called_once()

@pytest.mark.anyio
async def test_initialize_failure_setup_returns_none(extract_agent_adapter_not_initialized):
    adapter = extract_agent_adapter_not_initialized
    mock_kernel_instance = MagicMock()

    with patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.setup_extract_agent', 
               new_callable=AsyncMock) as mock_async_setup:
        mock_async_setup.return_value = (mock_kernel_instance, None)
        
        success = await adapter.initialize()
        
        assert success is False
        assert adapter.initialized is False
        mock_async_setup.assert_called_once()

@pytest.mark.anyio
async def test_initialize_exception(extract_agent_adapter_not_initialized):
    adapter = extract_agent_adapter_not_initialized
    with patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.setup_extract_agent', 
               new_callable=AsyncMock) as mock_async_setup:
        mock_async_setup.side_effect = Exception("Setup failed")
        
        success = await adapter.initialize()
        
        assert success is False
        assert adapter.initialized is False
        mock_async_setup.assert_called_once()

@pytest.mark.anyio
async def test_initialize_already_initialized(extract_agent_adapter_initialized):
    adapter = extract_agent_adapter_initialized 
    
    with patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.setup_extract_agent', new_callable=AsyncMock) as mock_setup:
        success = await adapter.initialize()
        assert success is True
        mock_setup.assert_not_called() 

def test_get_capabilities(extract_agent_adapter_not_initialized):
    adapter = extract_agent_adapter_not_initialized
    capabilities = adapter.get_capabilities()
    assert "text_extraction" in capabilities
    assert "preprocessing" in capabilities
    assert "extract_validation" in capabilities

@pytest.mark.anyio
async def test_can_process_task(extract_agent_adapter_initialized):
    adapter = extract_agent_adapter_initialized 
    task_valid = {"required_capabilities": ["text_extraction"]}
    assert adapter.can_process_task(task_valid) is True 
    
    task_invalid_capability = {"required_capabilities": ["unknown_capability"]}
    assert adapter.can_process_task(task_invalid_capability) is False
    
    task_no_capability = {} 
    assert adapter.can_process_task(task_no_capability) is False

    task_empty_capability_list = {"required_capabilities": []}
    assert adapter.can_process_task(task_empty_capability_list) is False

def test_can_process_task_not_initialized(extract_agent_adapter_not_initialized):
    adapter = extract_agent_adapter_not_initialized
    task_valid = {"required_capabilities": ["text_extraction"]}
    assert adapter.can_process_task(task_valid) is False


@pytest.mark.anyio
async def test_process_task_initialization_failure_in_process(extract_agent_adapter_not_initialized, mock_operational_state):
    adapter = extract_agent_adapter_not_initialized
    task_data = {"id": "task_init_fail", "tactical_task_id": "t_task_1"}

    adapter.initialize = AsyncMock(return_value=False) 
        
    result = await adapter.process_task(task_data)

    adapter.initialize.assert_called_once()
    assert result["status"] == "failed"
    assert result["task_id"] == task_data["id"] 
    assert result["tactical_task_id"] == "t_task_1"
    assert len(result["issues"]) == 1
    assert result["issues"][0]["type"] == "initialization_error"
    mock_operational_state.add_task.assert_not_called() # Doit être add_task


@pytest.mark.anyio
async def test_process_task_success_relevant_segment_extraction(extract_agent_adapter_initialized, mock_operational_state):
    adapter = extract_agent_adapter_initialized 
    task_id_original = "task_seg_extract"
    task_data = {
        "id": task_id_original,
        "tactical_task_id": "t_task_seg",
        "techniques": [{"name": "relevant_segment_extraction", "parameters": {}}],
        "text_extracts": [{"id": "ext1", "source": "doc1", "content": "Some text."}]
    }
    
    mock_extract_result = MagicMock(spec=ExtractResult)
    mock_extract_result.status = "valid"
    mock_extract_result.start_marker = "start"
    mock_extract_result.end_marker = "end"
    mock_extract_result.template_start = "template"
    mock_extract_result.extracted_text = "extracted"
    
    adapter.extract_agent.extract_from_name = AsyncMock(return_value=mock_extract_result)

    # Configurer le mock de add_task pour retourner l'ID de la tâche originale
    mock_operational_state.add_task.return_value = task_id_original

    result = await adapter.process_task(task_data)

    mock_operational_state.add_task.assert_called_with(task_data)
    mock_operational_state.update_task_status.assert_any_call(task_id_original, "in_progress", {
        "message": "Traitement de la tâche en cours", "agent": adapter.name
    })
    adapter.extract_agent.extract_from_name.assert_called_once_with(
        {"source_name": "doc1", "source_text": "Some text."}, "ext1"
    )
    assert result["status"] == "completed"
    assert result["task_id"] == task_id_original 
    assert len(result["outputs"]["extracted_segments"]) == 1
    assert result["outputs"]["extracted_segments"][0]["extracted_text"] == "extracted"
    mock_operational_state.update_task_status.assert_called_with(task_id_original, "completed", {
        "message": "Traitement terminé avec statut: completed", 
        "results_count": 1, 
        "issues_count": 0
    })
    mock_operational_state.update_metrics.assert_called_once()


@pytest.mark.anyio
async def test_process_task_extraction_error(extract_agent_adapter_initialized, mock_operational_state):
    adapter = extract_agent_adapter_initialized 
    task_data = {
        "id": "task_ext_err",
        "techniques": [{"name": "relevant_segment_extraction"}],
        "text_extracts": [{"id": "ext_err", "content": "Error text"}]
    }
    
    mock_error_result = MagicMock(spec=ExtractResult)
    mock_error_result.status = "error"
    mock_error_result.message = "Extraction failed"
    mock_error_result.explanation = "Detailed error"
    adapter.extract_agent.extract_from_name = AsyncMock(return_value=mock_error_result)
    mock_operational_state.add_task.return_value = task_data["id"]


    result = await adapter.process_task(task_data)
    
    assert result["status"] == "completed_with_issues"
    assert result["task_id"] == task_data["id"]
    assert result["outputs"] == {'extracted_segments': [], 'normalized_text': []}
    assert len(result["issues"]) == 1
    assert result["issues"][0]["type"] == "extraction_error"
    assert result["issues"][0]["description"] == "Extraction failed"


@pytest.mark.anyio
async def test_process_task_text_normalization(extract_agent_adapter_initialized, mock_operational_state):
    adapter = extract_agent_adapter_initialized 
    task_id_original = "task_norm"
    task_data = {
        "id": task_id_original,
        "techniques": [{"name": "text_normalization", "parameters": {"remove_stopwords": True}}],
        "text_extracts": [{"id": "ext_norm", "content": "Ceci est un test de normalisation."}]
    }
    mock_operational_state.add_task.return_value = task_id_original

    result = await adapter.process_task(task_data)

    assert result["status"] == "completed"
    assert result["task_id"] == task_id_original
    assert len(result["outputs"]["normalized_text"]) == 1 
    assert result["outputs"]["normalized_text"][0]["normalized_text"] == "Ceci test normalisation."


@pytest.mark.anyio
async def test_process_task_unsupported_technique(extract_agent_adapter_initialized, mock_operational_state):
    adapter = extract_agent_adapter_initialized 
    task_id_original = "task_unsupported"
    task_data = {
        "id": task_id_original,
        "techniques": [{"name": "unknown_technique"}],
        "text_extracts": [{"id": "ext_unsup", "content": "Some content"}]
    }
    mock_operational_state.add_task.return_value = task_id_original


    result = await adapter.process_task(task_data)

    assert result["status"] == "completed_with_issues"
    assert result["task_id"] == task_id_original
    assert result["outputs"] == {'extracted_segments': [], 'normalized_text': []}
    assert len(result["issues"]) == 1
    assert result["issues"][0]["type"] == "unsupported_technique"


@pytest.mark.anyio
async def test_process_task_no_text_extracts(extract_agent_adapter_initialized, mock_operational_state):
    adapter = extract_agent_adapter_initialized 
    task_id_original = "task_no_extracts"
    task_data = {
        "id": task_id_original,
        "techniques": [{"name": "relevant_segment_extraction"}],
        "text_extracts": [] 
    }
    mock_operational_state.add_task.return_value = task_id_original


    result = await adapter.process_task(task_data)

    assert result["status"] == "failed"
    assert result["task_id"] == task_id_original 
    assert len(result["issues"]) == 1
    assert result["issues"][0]["type"] == "execution_error"
    assert "Aucun extrait de texte fourni" in result["issues"][0]["description"]


@pytest.mark.anyio
async def test_process_task_general_exception(extract_agent_adapter_initialized, mock_operational_state):
    adapter = extract_agent_adapter_initialized 
    task_id_original = "task_exception"
    task_data = {
        "id": task_id_original,
        "techniques": [{"name": "relevant_segment_extraction"}],
        "text_extracts": [{"id": "ext_ex", "content": "Exception content"}]
    }
    mock_operational_state.add_task.return_value = task_id_original
    
    adapter.extract_agent.extract_from_name = AsyncMock(side_effect=RuntimeError("Unexpected error"))

    result = await adapter.process_task(task_data)

    assert result["status"] == "failed"
    assert result["task_id"] == task_id_original
    assert len(result["issues"]) == 1
    assert result["issues"][0]["type"] == "execution_error"
    assert "Unexpected error" in result["issues"][0]["description"]

@pytest.mark.anyio
async def test_process_extract_calls_agent(extract_agent_adapter_initialized):
    adapter = extract_agent_adapter_initialized 
    extract_data = {"id": "e1", "source": "s1", "content": "Test content"}
    mock_result = MagicMock(spec=ExtractResult)
    adapter.extract_agent.extract_from_name = AsyncMock(return_value=mock_result)

    result = await adapter._process_extract(extract_data, {})

    adapter.extract_agent.extract_from_name.assert_called_once_with(
        {"source_name": "s1", "source_text": "Test content"}, "e1"
    )
    assert result == mock_result

@pytest.mark.anyio
async def test_process_extract_initializes_if_needed(extract_agent_adapter_not_initialized):
    adapter = extract_agent_adapter_not_initialized
    extract_data = {"id": "e2", "content": "Content"}
    
    mock_kernel_instance = MagicMock()
    mock_extract_agent_instance = AsyncMock() 
    mock_extract_agent_instance.extract_from_name = AsyncMock(return_value=MagicMock(spec=ExtractResult))

    with patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.setup_extract_agent', 
               new_callable=AsyncMock) as mock_async_setup:
        mock_async_setup.return_value = (mock_kernel_instance, mock_extract_agent_instance)
        
        await adapter._process_extract(extract_data, {}) 
        
        mock_async_setup.assert_called_once() 
        mock_extract_agent_instance.extract_from_name.assert_called_once()


@pytest.mark.anyio 
async def test_normalize_text_remove_stopwords(extract_agent_adapter_initialized): 
    adapter = extract_agent_adapter_initialized 
    text = "Ceci est un test et une démonstration de la normalisation"
    params = {"remove_stopwords": True}
    normalized = adapter._normalize_text(text, params) 
    assert normalized == "Ceci test démonstration normalisation"

@pytest.mark.anyio 
async def test_normalize_text_no_stopwords(extract_agent_adapter_initialized): 
    adapter = extract_agent_adapter_initialized 
    text = "Ceci est un test"
    params = {"remove_stopwords": False} 
    normalized = adapter._normalize_text(text, params)
    assert normalized == "Ceci est un test"

@pytest.mark.anyio 
async def test_normalize_text_lemmatize_logs_not_implemented(extract_agent_adapter_initialized, caplog): 
    adapter = extract_agent_adapter_initialized 
    text = "testing lemmatization"
    params = {"lemmatize": True}
    
    with caplog.at_level("INFO"):
        adapter._normalize_text(text, params)
    
    assert "Lemmatisation demandée mais non implémentée." in caplog.text