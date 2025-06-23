import pytest
from unittest.mock import Mock, AsyncMock, patch

# Import the correct agent class
from argumentation_analysis.agents.watson_jtms.agent import WatsonJTMSAgent
from argumentation_analysis.agents.jtms_agent_base import JTMSSession


@pytest.fixture
def mock_kernel():
    """A mock of the semantic kernel."""
    return Mock()


@pytest.fixture
def mock_jtms_session():
    """A mock of the JTMSSession."""
    return Mock(spec=JTMSSession)


@pytest.fixture
@patch('argumentation_analysis.agents.watson_jtms.agent.ConsistencyChecker')
@patch('argumentation_analysis.agents.watson_jtms.agent.FormalValidator')
@patch('argumentation_analysis.agents.watson_jtms.agent.CritiqueEngine')
@patch('argumentation_analysis.agents.watson_jtms.agent.SynthesisEngine')
@patch('argumentation_analysis.agents.watson_jtms.agent.JTMSSession')
def watson_agent(mock_session, mock_synthesis, mock_critique, mock_validator, mock_consistency, mock_kernel):
    """
    Provides a WatsonJTMSAgent instance with all its dependencies mocked,
    including the JTMSSession from the base class.
    """
    # Instantiate the agent. The __init__ will use the mocked classes.
    agent = WatsonJTMSAgent(kernel=mock_kernel, agent_name="watson_test")
    
    # Attach mocked services for easy access in tests
    agent.consistency_checker = mock_consistency_instance = mock_consistency.return_value
    agent.validator = mock_validator_instance = mock_validator.return_value
    agent.critique_engine = mock_critique_instance = mock_critique.return_value
    agent.synthesis_engine = mock_synthesis_instance = mock_synthesis.return_value
    
    return agent, {
        "consistency": mock_consistency_instance,
        "validator": mock_validator_instance,
        "critique": mock_critique_instance,
        "synthesis": mock_synthesis_instance
    }


class TestWatsonJTMSAgentDelegation:
    """
    Tests to ensure that WatsonJTMSAgent correctly initializes its specialized services
    and delegates its public methods to the appropriate underlying service.
    """

    def test_agent_initialization_delegates_to_services(self, watson_agent):
        """
        Tests that the agent's __init__ correctly instantiates its helper services.
        """
        agent, mocks = watson_agent
        
        # Check that the services were instantiated (the mocks were called)
        assert agent.consistency_checker is not None
        assert agent.validator is not None
        assert agent.critique_engine is not None
        assert agent.synthesis_engine is not None
        
        assert agent.specialization == "critical_analysis"
        assert agent.agent_name == "watson_test"

    @pytest.mark.asyncio
    async def test_validate_hypothesis_delegates_to_validator(self, watson_agent):
        """
        Tests that validate_hypothesis calls the validator's prove_belief method.
        """
        agent, mocks = watson_agent
        mocks["validator"].prove_belief = AsyncMock(return_value={"provable": True})
        
        hypothesis_data = {"hypothesis": "Test proposition"}
        result = await agent.validate_hypothesis("hyp_123", hypothesis_data)
        
        mocks["validator"].prove_belief.assert_awaited_once_with("Test proposition")
        assert result["is_valid"] is True

    async def test_critique_reasoning_chain_delegates_to_critique_engine(self, watson_agent):
        """
        Tests that critique_reasoning_chain calls the critique_engine's method.
        """
        agent, mocks = watson_agent
        mocks["critique"].critique_reasoning_chain = AsyncMock(return_value={"success": True})
        
        chain = [{"step": "A"}, {"step": "B"}]
        await agent.critique_reasoning_chain("chain_abc", chain)
        
        mocks["critique"].critique_reasoning_chain.assert_awaited_once_with("chain_abc", chain)

    async def test_provide_alternative_theory_delegates_to_synthesis_engine(self, watson_agent):
        """
        Tests that provide_alternative_theory calls the synthesis_engine's method.
        """
        agent, mocks = watson_agent
        mocks["synthesis"].provide_alternative_theory = AsyncMock(return_value={"theory": "alt"})

        primary_theory = {"suspect": "A"}
        evidence = ["e1"]
        await agent.provide_alternative_theory("theory_1", primary_theory, evidence)

        mocks["synthesis"].provide_alternative_theory.assert_awaited_once_with("theory_1", primary_theory, evidence)
        
    async def test_resolve_conflicts_delegates_to_consistency_checker(self, watson_agent):
        """
        Tests that resolve_conflicts calls the consistency_checker's method.
        """
        agent, mocks = watson_agent
        mocks["consistency"].resolve_conflicts = AsyncMock(return_value={"resolved": True})
        
        conflicts = ["b1", "b2"]
        await agent.resolve_conflicts(conflicts)
        
        mocks["consistency"].resolve_conflicts.assert_awaited_once_with(conflicts)

    async def test_validate_reasoning_chain_delegates_to_validator_prove_belief(self, watson_agent):
        """
        Tests that validate_reasoning_chain iteratively calls validator.prove_belief.
        """
        agent, mocks = watson_agent
        mocks["validator"].prove_belief = AsyncMock(side_effect=[
            {"provable": True, "confidence": 0.9},
            {"provable": False, "confidence": 0.4}
        ])
        
        chain = [
            {"proposition": "Step 1"},
            {"hypothesis": "Step 2"} # Test alternative key
        ]
        
        result = await agent.validate_reasoning_chain(chain)
        
        assert mocks["validator"].prove_belief.call_count == 2
        mocks["validator"].prove_belief.assert_any_call("Step 1")
        mocks["validator"].prove_belief.assert_any_call("Step 2")
        
        assert result["is_valid"] is False
        assert result["confidence"] == 0.4
        assert len(result["steps"]) == 2

    # A simple test to check a method that was causing an AttributeError
    async def test_get_validation_summary_delegates(self, watson_agent):
        """
        Tests a simple delegation for a method that was previously missing.
        """
        agent, mocks = watson_agent
        mocks["validator"].get_validation_summary.return_value = {"summary": "All good"}
        
        # This will call the fallback in the agent if the validator method doesn't exist
        result = agent.get_validation_summary()

        # In this refactored test, we ensure it calls the mocked validator method
        mocks["validator"].get_validation_summary.assert_called_once()
        assert result["summary"] == "All good"