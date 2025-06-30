import pytest
from unittest.mock import MagicMock
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.models.extract_result import ExtractResult
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract

@pytest.fixture
def mock_kernel():
    """Provides a mocked Semantic Kernel."""
    kernel = MagicMock()
    kernel.plugins = MagicMock()
    # Mock a function within the mocked plugin collection
    mock_plugin = MagicMock()
    mock_function = MagicMock()
    mock_function.invoke.return_value = '{"formulas": ["exists X: (Cat(X))"]}' # Default mock response
    mock_plugin.__getitem__.return_value = mock_function
    kernel.plugins.__getitem__.return_value = mock_plugin
    return kernel

@pytest.fixture
def fol_agent(mock_kernel):
    """Provides a concrete, testable instance of FOLLogicAgent."""

    class ConcreteFOLAgent(FOLLogicAgent):
        async def validate_argument(self, premises: list[str], conclusion: str, **kwargs) -> bool:
            """Mocked implementation for abstract method."""
            return True

    agent = ConcreteFOLAgent(kernel=mock_kernel, agent_name="fol_test_agent")
    # Mocking the bridge to avoid real Java calls
    agent._tweety_bridge = MagicMock()
    agent._tweety_bridge.validate_fol_belief_set.return_value = (True, "Valid")
    return agent

@pytest.fixture
def extract_result_dict():
    """Provides a dictionary for a valid ExtractResult."""
    return {
        "source_name": "Test Source",
        "extract_name": "Test Extract",
        "status": "valid",
        "message": "Extraction réussie",
        "start_marker": "DEBUT_EXTRAIT",
        "end_marker": "FIN_EXTRAIT",
        "template_start": "T{0}",
        "explanation": "Explication de l'extraction",
        "extracted_text": "Texte extrait de test"
    }

@pytest.fixture
def valid_extract_result(extract_result_dict):
    """Provides a valid instance of ExtractResult."""
    return ExtractResult.from_dict(extract_result_dict)

@pytest.fixture
def error_extract_result(extract_result_dict):
    """Provides an error instance of ExtractResult."""
    error_dict = extract_result_dict.copy()
    error_dict["status"] = "error"
    error_dict["message"] = "Erreur lors de l'extraction"
    return ExtractResult.from_dict(error_dict)

@pytest.fixture
def rejected_extract_result(extract_result_dict):
    """Provides a rejected instance of ExtractResult."""
    rejected_dict = extract_result_dict.copy()
    rejected_dict["status"] = "rejected"
    rejected_dict["message"] = "Extraction rejetée"
    return ExtractResult.from_dict(rejected_dict)

@pytest.fixture
def sample_definitions():
    """Provides a sample ExtractDefinitions object for tests."""
    extract = Extract(
        extract_name="Test Extract",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT",
        template_start="T{0}"
    )
    source = SourceDefinition(
        source_name="Test Source",
        source_type="url",
        schema="https",
        host_parts=["example", "com"],
        path="/test",
        extracts=[extract]
    )
    return ExtractDefinitions(sources=[source])

@pytest.fixture
def mock_parse_args(mocker):
    """Fixture to mock argparse.ArgumentParser.parse_args."""
    return mocker.patch("argparse.ArgumentParser.parse_args")