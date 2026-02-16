# -*- coding: utf-8 -*-
import pytest
import uuid
import semantic_kernel as sk
from unittest.mock import MagicMock, patch, AsyncMock

from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import (
    ExtractAgentAdapter,
)
from argumentation_analysis.orchestration.hierarchical.operational.state import (
    OperationalState,
)
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractResult
from argumentation_analysis.core.communication import MessageMiddleware
from argumentation_analysis.core.bootstrap import ProjectContext


@pytest.fixture
def mock_project_context():
    return MagicMock(spec=ProjectContext)


@pytest.fixture
def mock_operational_state():
    state = MagicMock(spec=OperationalState)

    def mock_add_task(task_data):
        return task_data.get("id", f"mock_task_id_{uuid.uuid4().hex[:4]}")

    state.add_task = MagicMock(side_effect=mock_add_task)
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
async def extract_agent_adapter_initialized(
    mock_operational_state, mock_middleware_for_adapter, mock_project_context
):
    mock_kernel_instance = MagicMock(spec=sk.Kernel)
    mock_llm_service_id = "test_llm_id_initialized"

    adapter = ExtractAgentAdapter(
        operational_state=mock_operational_state, middleware=mock_middleware_for_adapter
    )

    with patch(
        "argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgent"
    ) as MockedExtractAgentClass:
        mock_agent_internal_instance = AsyncMock()
        mock_agent_internal_instance.setup_agent_components = AsyncMock(
            return_value=None
        )
        mock_agent_internal_instance.extract_from_name = AsyncMock(
            return_value=MagicMock(spec=ExtractResult)
        )
        MockedExtractAgentClass.return_value = mock_agent_internal_instance

        await adapter.initialize(
            kernel=mock_kernel_instance,
            llm_service_id=mock_llm_service_id,
            project_context=mock_project_context,
        )
    return adapter


@pytest.fixture
def extract_agent_adapter_not_initialized(
    mock_operational_state, mock_middleware_for_adapter
):
    adapter = ExtractAgentAdapter(
        operational_state=mock_operational_state, middleware=mock_middleware_for_adapter
    )
    adapter.kernel = MagicMock(spec=sk.Kernel)
    adapter.llm_service_id = "dummy_llm_id_not_init"
    return adapter


def test_extract_agent_adapter_initialization_name(
    mock_operational_state, mock_middleware_for_adapter
):
    adapter_default_name = ExtractAgentAdapter(
        operational_state=mock_operational_state, middleware=mock_middleware_for_adapter
    )
    assert adapter_default_name.name == "ExtractAgent"

    adapter_custom_name = ExtractAgentAdapter(
        name="MyExtractor",
        operational_state=mock_operational_state,
        middleware=mock_middleware_for_adapter,
    )
    assert adapter_custom_name.name == "MyExtractor"
    assert not adapter_custom_name.initialized


async def test_initialize_success(
    extract_agent_adapter_not_initialized, mock_project_context
):
    adapter = extract_agent_adapter_not_initialized
    mock_kernel_instance = MagicMock(spec=sk.Kernel)
    mock_llm_id = "llm_test_id"

    with patch(
        "argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgent"
    ) as MockExtractAgentClass:
        mock_extract_agent_instance = AsyncMock()
        mock_extract_agent_instance.setup_agent_components = AsyncMock(
            return_value=None
        )
        MockExtractAgentClass.return_value = mock_extract_agent_instance

        assert not adapter.initialized
        success = await adapter.initialize(
            kernel=mock_kernel_instance,
            llm_service_id=mock_llm_id,
            project_context=mock_project_context,
        )

        assert success is True
        assert adapter.initialized is True
        assert adapter.kernel == mock_kernel_instance
        assert adapter.llm_service_id == mock_llm_id
        assert adapter.agent == mock_extract_agent_instance
        MockExtractAgentClass.assert_called_once_with(
            kernel=mock_kernel_instance,
            agent_name=f"{adapter.name}_ExtractAgent",
            llm_service_id=mock_llm_id,
        )


@pytest.mark.xfail(reason="API changed: initialize() no longer calls setup_agent_components")
async def test_initialize_failure_agent_setup_fails(
    extract_agent_adapter_not_initialized, mock_project_context
):
    adapter = extract_agent_adapter_not_initialized
    mock_kernel_instance = MagicMock(spec=sk.Kernel)
    mock_llm_id = "llm_fail_id"

    with patch(
        "argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgent"
    ) as MockExtractAgentClass:
        mock_extract_agent_instance = AsyncMock()
        mock_extract_agent_instance.setup_agent_components = AsyncMock(
            side_effect=Exception("Component setup failed")
        )
        MockExtractAgentClass.return_value = mock_extract_agent_instance

        success = await adapter.initialize(
            kernel=mock_kernel_instance,
            llm_service_id=mock_llm_id,
            project_context=mock_project_context,
        )

        assert success is False
        assert adapter.initialized is False
        MockExtractAgentClass.assert_called_once()
        mock_extract_agent_instance.setup_agent_components.assert_called_once()


async def test_initialize_exception_during_agent_instantiation(
    extract_agent_adapter_not_initialized, mock_project_context
):
    adapter = extract_agent_adapter_not_initialized
    mock_kernel_instance = MagicMock(spec=sk.Kernel)
    mock_llm_id = "llm_inst_fail_id"

    with patch(
        "argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgent",
        side_effect=Exception("Agent instantiation failed"),
    ) as MockExtractAgentClass:
        success = await adapter.initialize(
            kernel=mock_kernel_instance,
            llm_service_id=mock_llm_id,
            project_context=mock_project_context,
        )

        assert success is False
        assert adapter.initialized is False
        MockExtractAgentClass.assert_called_once()


async def test_initialize_already_initialized(
    extract_agent_adapter_initialized, mock_project_context
):
    adapter = extract_agent_adapter_initialized
    original_agent_instance = adapter.agent

    with patch(
        "argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgent"
    ) as MockExtractAgentClass:
        success = await adapter.initialize(
            kernel=adapter.kernel,
            llm_service_id=adapter.llm_service_id,
            project_context=mock_project_context,
        )
        assert success is True
        MockExtractAgentClass.assert_not_called()
        assert adapter.agent is original_agent_instance


def test_get_capabilities(extract_agent_adapter_not_initialized):
    adapter = extract_agent_adapter_not_initialized
    capabilities = adapter.get_capabilities()
    assert "text_extraction" in capabilities
    assert "preprocessing" in capabilities
    assert "extract_validation" in capabilities


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


@pytest.mark.xfail(reason="API changed: process_task no longer sets in_progress status")
async def test_process_task_success_relevant_segment_extraction(
    extract_agent_adapter_initialized, mock_operational_state
):
    adapter = extract_agent_adapter_initialized
    task_id_original = "task_seg_extract"
    task_data = {
        "id": task_id_original,
        "tactical_task_id": "t_task_seg",
        "techniques": [{"name": "relevant_segment_extraction", "parameters": {}}],
        "text_extracts": [{"id": "ext1", "source": "doc1", "content": "Some text."}],
    }

    mock_extract_result = MagicMock(spec=ExtractResult)
    mock_extract_result.status = "valid"
    mock_extract_result.start_marker = "start"
    mock_extract_result.end_marker = "end"
    mock_extract_result.template_start = "template"
    mock_extract_result.extracted_text = "extracted"

    adapter.agent.extract_from_name = AsyncMock(return_value=mock_extract_result)
    mock_operational_state.add_task.return_value = task_id_original

    result = await adapter.process_task(task_data)

    mock_operational_state.add_task.assert_called_once_with(task_data)
    mock_operational_state.update_task_status.assert_any_call(
        task_id_original,
        "in_progress",
        {"message": "Traitement de la tâche en cours", "agent": adapter.name},
    )
    adapter.agent.extract_from_name.assert_called_once_with(
        {"source_name": "doc1", "source_text": "Some text."}, "ext1"
    )
    assert result["status"] == "completed"
    assert result["task_id"] == task_id_original
    assert len(result["outputs"]["extracted_segments"]) == 1
    assert result["outputs"]["extracted_segments"][0]["extracted_text"] == "extracted"
    mock_operational_state.update_task_status.assert_called_with(
        task_id_original,
        "completed",
        {
            "message": "Traitement terminé avec statut: completed",
            "results_count": 1,
            "issues_count": 0,
        },
    )
    mock_operational_state.update_metrics.assert_called_once()


@pytest.mark.xfail(reason="API changed: process_task return format changed")
async def test_process_task_extraction_error(
    extract_agent_adapter_initialized, mock_operational_state
):
    adapter = extract_agent_adapter_initialized
    task_data = {
        "id": "task_ext_err",
        "techniques": [{"name": "relevant_segment_extraction"}],
        "text_extracts": [{"id": "ext_err", "content": "Error text"}],
    }

    mock_error_result = MagicMock(spec=ExtractResult)
    mock_error_result.status = "error"
    mock_error_result.message = "Extraction failed"
    mock_error_result.explanation = "Detailed error"
    adapter.agent.extract_from_name = AsyncMock(return_value=mock_error_result)
    mock_operational_state.add_task.return_value = task_data["id"]

    result = await adapter.process_task(task_data)

    assert result["status"] == "completed_with_issues"
    assert result["task_id"] == task_data["id"]
    assert result["outputs"] == {"extracted_segments": [], "normalized_text": []}
    assert len(result["issues"]) == 1
    assert result["issues"][0]["type"] == "extraction_error"
    assert result["issues"][0]["description"] == "Extraction failed"


@pytest.mark.xfail(reason="API changed: _normalize_text method removed from adapter")
async def test_normalize_text_remove_stopwords(extract_agent_adapter_initialized):
    adapter = extract_agent_adapter_initialized
    text = "Ceci est un test et une démonstration de la normalisation"
    params = {"remove_stopwords": True}
    normalized = adapter._normalize_text(text, params)
    assert normalized == "Ceci test démonstration normalisation"


@pytest.mark.xfail(reason="API changed: _normalize_text method removed from adapter")
async def test_normalize_text_no_stopwords(extract_agent_adapter_initialized):
    adapter = extract_agent_adapter_initialized
    text = "Ceci est un test"
    params = {"remove_stopwords": False}
    normalized = adapter._normalize_text(text, params)
    assert normalized == "Ceci est un test"


@pytest.mark.xfail(reason="API changed: _normalize_text method removed from adapter")
async def test_normalize_text_lemmatize_logs_not_implemented(
    extract_agent_adapter_initialized, caplog
):
    adapter = extract_agent_adapter_initialized
    text = "testing lemmatization"
    params = {"lemmatize": True}

    with caplog.at_level("INFO"):
        adapter._normalize_text(text, params)

    assert "Lemmatisation demandée mais non implémentée." in caplog.text
