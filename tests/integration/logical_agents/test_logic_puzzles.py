# tests/integration/logical_agents/test_logic_puzzles.py

import pytest
import json
from pathlib import Path

import semantic_kernel as sk
from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent

# Fixture to create a mock kernel for the agent
@pytest.fixture
def kernel():
    return sk.Kernel()

# Fixture to load scenarios from JSON files
@pytest.fixture
def load_scenario(request):
    scenario_name = request.param
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "scenarios"
    scenario_file = fixtures_dir / f"{scenario_name}.json"
    with open(scenario_file, 'r', encoding='utf-8') as f:
        return json.load(f)

class TestLogicalAgentHardening:
    """
    Test suite for hardening the logical agent against complex scenarios.
    """

    @pytest.mark.parametrize("load_scenario", ["contradictory_scenario"], indirect=True)
    async def test_agent_identifies_contradiction(self, kernel, load_scenario):
        """
        Test that the agent correctly identifies and reports a contradiction
        in the provided facts by explicitly defining a conflict.
        """
        # 1. Initialize the agent
        agent = SherlockJTMSAgent(kernel, agent_name="test_contradiction_agent")

        # 2. Add a single fact
        fact_description = load_scenario["facts"][0]
        fact_id = agent._evidence_manager.add_evidence({"description": fact_description})

        # 3. Create a direct contradiction by stating a fact is also false.
        # A justification where a node supports its own negation is a fundamental contradiction.
        agent.add_justification(
            in_list=[fact_id],
            out_list=[fact_id],
            conclusion=f"contradiction_for_{fact_id}"
        )

        # 4. Check for consistency
        consistency_report = agent.check_consistency()
        
        # 5. Assert that the agent's state indicates a contradiction
        assert consistency_report["is_consistent"] is False, \
            "The JTMS should report an inconsistency."
        assert len(consistency_report.get("conflicts", [])) > 0, \
            "The list of conflicts should not be empty."
        
        # 6. Verify the conflict details
        conflict = consistency_report["conflicts"][0]
        assert fact_id in conflict["beliefs"], "The conflict should involve the contradictory fact."
        
    @pytest.mark.parametrize("load_scenario", ["ambiguous_scenario"], indirect=True)
    async def test_agent_handles_ambiguity(self, kernel, load_scenario):
        """
        Test that the agent correctly identifies and reports ambiguity
        (i.e., multiple possible solutions) when facts are insufficient.
        """
        # 1. Initialize the agent
        agent = SherlockJTMSAgent(kernel, agent_name="test_ambiguity_agent")
        
        # 2. Add all facts as evidence
        evidence_ids = [agent._evidence_manager.add_evidence({"description": f}) for f in load_scenario["facts"]]
        
        # 3. Manually create two competing hypotheses to simulate ambiguity
        hypothesis1_id = agent._hypothesis_tracker.create_hypothesis("Le Colonel Moutarde est le coupable.")
        hypothesis2_id = agent._hypothesis_tracker.create_hypothesis("Mme. Pervenche est la coupable.")

        # 4. Link evidence to support each hypothesis
        # The first half of the evidence supports Moutarde
        for ev_id in evidence_ids[:len(evidence_ids)//2]:
            agent._hypothesis_tracker.link_evidence_to_hypothesis(hypothesis1_id, ev_id, "positive")
            
        # The second half supports Pervenche
        for ev_id in evidence_ids[len(evidence_ids)//2:]:
            agent._hypothesis_tracker.link_evidence_to_hypothesis(hypothesis2_id, ev_id, "positive")
        
        # 5. Attempt to deduce a solution
        investigation_context = {"goal": "Find the murderer, weapon, and location"}
        solution_report = await agent.deduce_solution(investigation_context)

        # 6. Assertions for ambiguity
        assert "error" not in solution_report, "Deduction should not fail."
        
        # Confidence should be less than 1.0 because of a strong competitor
        assert solution_report["confidence_score"] < 0.8, \
            f"Confidence should be less than 0.8 in an ambiguous case, but was {solution_report['confidence_score']}"
        
        # There should be at least one alternative hypothesis
        assert len(solution_report.get("alternative_hypotheses", [])) > 0, \
            "There should be at least one alternative hypothesis."
            
        # Verify that the alternative is the other hypothesis we created
        alt_ids = [h["hypothesis_id"] for h in solution_report["alternative_hypotheses"]]
        primary_id = solution_report["primary_hypothesis"]["hypothesis_id"]
        
        assert (hypothesis1_id in alt_ids or hypothesis2_id in alt_ids), \
            "The alternative hypothesis list should contain one of our created hypotheses."
        assert primary_id != alt_ids[0], "The primary and alternative hypotheses must be different."
