
from config.unified_config import UnifiedConfig
import pytest
from semantic_kernel.kernel import Kernel
from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent, OracleTools
from argumentation_analysis.agents.core.oracle.dataset_access_manager import DatasetAccessManager
from argumentation_analysis.agents.core.oracle.permissions import QueryType, PermissionRule, OracleResponse
from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset

# --- Fixtures for Real Component Integration ---

@pytest.fixture
def kernel_service() -> Kernel:
    """Provides a real Kernel instance with gpt-4o-mini configured."""
    config = UnifiedConfig()
    # Assuming get_kernel_with_gpt4o_mini returns a configured Kernel
    # This might need to be awaited if it's an async function
    return config.get_kernel_with_gpt4o_mini()

@pytest.fixture
def real_cluedo_dataset() -> CluedoDataset:
    """Provides a real CluedoDataset instance for integration tests."""
    solution_secrete = {
        "suspect": "Colonel Moutarde",
        "arme": "Poignard",
        "lieu": "Salon"
    }
    cartes_distribuees = {
        "Moriarty": ["Professeur Violet", "Chandelier"],
        "AutresJoueurs": ["Cuisine"]
    }
    return CluedoDataset(
        solution_secrete=solution_secrete,
        cartes_distribuees=cartes_distribuees
    )

@pytest.fixture
def real_dataset_manager(real_cluedo_dataset: CluedoDataset) -> DatasetAccessManager:
    """Provides a real DatasetAccessManager instance for integration tests."""
    return DatasetAccessManager(dataset=real_cluedo_dataset)

@pytest.fixture
def sample_agent_config() -> dict:
    """Provides a sample agent configuration for tests."""
    return {
        "agent_name": "TestOracle",
        "system_prompt_suffix": "Vous êtes un Oracle de test spécialisé.",
        "access_level": "expert",  # Use a high access level for most tests
        "allowed_query_types": [
            QueryType.CARD_INQUIRY,
            QueryType.DATASET_ACCESS,
            QueryType.GAME_STATE,
            QueryType.ADMIN_COMMAND # Allow admin for testing purposes
        ]
    }

@pytest.fixture
def oracle_agent(kernel_service: Kernel, real_dataset_manager: DatasetAccessManager, sample_agent_config: dict) -> OracleBaseAgent:
    """Provides a fully initialized OracleBaseAgent with real components."""
    agent = OracleBaseAgent(
        kernel=kernel_service,
        dataset_manager=real_dataset_manager,
        **sample_agent_config
    )
    return agent

# --- Refactored Tests using Real Components ---

def test_oracle_agent_initialization(oracle_agent: OracleBaseAgent, real_dataset_manager: DatasetAccessManager):
    """Test the correct initialization of an OracleBaseAgent with real components."""
    assert oracle_agent.name == "TestOracle"
    assert oracle_agent.dataset_manager == real_dataset_manager
    assert oracle_agent.access_level == "expert"
    assert QueryType.CARD_INQUIRY in oracle_agent.allowed_query_types
    
    instructions = oracle_agent.instructions
    assert "Oracle de test spécialisé" in instructions
    assert "Oracle, gardien des données" in instructions

def test_oracle_tools_are_initialized(oracle_agent: OracleBaseAgent):
    """Test that OracleTools are correctly initialized within the agent."""
    tools = oracle_agent.oracle_tools
    assert isinstance(tools, OracleTools)
    assert tools.dataset_manager == oracle_agent.dataset_manager
    assert tools.agent_name == oracle_agent.name

@pytest.mark.asyncio
async def test_execute_query_successfully(oracle_agent: OracleBaseAgent, real_dataset_manager: DatasetAccessManager):
    """Test a successful, authorized query execution against the real dataset."""
    # Setup: Grant permission for the query
    permission_rule = PermissionRule(
        agent_name="TestOracle",
        allowed_query_types=[QueryType.CARD_INQUIRY]
    )
    real_dataset_manager.permission_manager.add_permission_rule(permission_rule)
    
    # Execute a query that should be successful
    result = await oracle_agent.oracle_tools.query_oracle_dataset(
        query_type="card_inquiry",
        query_params='{"card": "Colonel Moutarde"}'
    )
    
    # Assertions on the real, non-deterministic response
    assert isinstance(result, str)
    assert "Requête Oracle exécutée" in result
    # This part of the logic might depend on the dataset's implementation
    assert "Colonel Moutarde" in result

@pytest.mark.asyncio
async def test_execute_query_with_permission_denied(oracle_agent: OracleBaseAgent, real_dataset_manager: DatasetAccessManager):
    """Test query execution where permissions are explicitly denied."""
    # Setup: Ensure no permission rule allows this query for this agent
    # By default, without a rule, access should be denied. Let's make it explicit.
    real_dataset_manager.permission_manager.rules = [] # Clear existing rules
    
    # Execute
    result = await oracle_agent.oracle_tools.query_oracle_dataset(
        query_type="admin_command",
        query_params='{"command": "reset_game"}'
    )
    
    # Assertions
    assert "Requête Oracle refusée" in result
    assert "non autorisé" in result

@pytest.mark.asyncio
async def test_validate_permissions_for_another_agent(oracle_agent: OracleBaseAgent, real_dataset_manager: DatasetAccessManager):
    """Test validating permissions for another agent."""
    # Setup for the target agent ("Watson")
    permission_rule = PermissionRule(
        agent_name="Watson",
        allowed_query_types=[QueryType.CARD_INQUIRY]
    )
    real_dataset_manager.permission_manager.add_permission_rule(permission_rule)
    
    # Test for success
    result_success = await oracle_agent.oracle_tools.validate_agent_permissions(
        target_agent="Watson",
        query_type="card_inquiry"
    )
    assert "Watson a les permissions pour card_inquiry" in result_success

    # Test for failure
    result_failure = await oracle_agent.oracle_tools.validate_agent_permissions(
        target_agent="Watson",
        query_type="admin_command"
    )
    assert "Watson n'a pas les permissions pour admin_command" in result_failure

def test_kernel_function_decorators_exist(oracle_agent: OracleBaseAgent):
    """Check that OracleTools methods are decorated as kernel functions."""
    tools = oracle_agent.oracle_tools
    assert hasattr(tools.query_oracle_dataset, "__kernel_function__")
    assert hasattr(tools.validate_agent_permissions, "__kernel_function__")
    assert callable(tools.query_oracle_dataset)
    
    query_doc = tools.query_oracle_dataset.__doc__ or ""
    assert "Oracle" in query_doc or "dataset" in query_doc

@pytest.mark.asyncio
async def test_query_with_invalid_json_parameters(oracle_agent: OracleBaseAgent):
    """Test error handling for invalid JSON in query parameters."""
    result = await oracle_agent.oracle_tools.query_oracle_dataset(
        query_type="card_inquiry",
        query_params="this is not valid json"
    )
    assert "Erreur de format JSON" in result
    assert "not valid json" in result

@pytest.mark.asyncio
async def test_query_with_invalid_query_type(oracle_agent: OracleBaseAgent):
    """Test error handling for an invalid query type."""
    with pytest.raises(ValueError, match="Type de requête invalide"):
        await oracle_agent.oracle_tools.query_oracle_dataset(
            query_type="this_is_an_invalid_type",
            query_params='{}'
        )