import pytest
import json
from pathlib import Path
import asyncio

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
    # Adjust the path to be relative to this test file's location
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "scenarios"
    scenario_file = fixtures_dir / f"{scenario_name}.json"
    with open(scenario_file, 'r', encoding='utf-8') as f:
        return json.load(f)

class TestLogicalAgentHardening:
    """
    Test suite for hardening the logical agent against complex scenarios,
    using the SherlockJTMSAgent.
    """

    @pytest.mark.parametrize("load_scenario", ["contradictory_scenario"], indirect=True)
    def test_agent_identifies_contradiction(self, kernel, load_scenario):
        """
        Test that the agent correctly identifies a contradiction using its JTMS.
        """
        # This test is synchronous as it does not await any coroutines.
        agent = SherlockJTMSAgent(kernel, agent_name="test_contradiction_agent")

        # Manually add facts as beliefs. A more advanced implementation
        # would parse rules into justifications.
        fact1_belief = agent.add_belief("in_kitchen(Moutarde)", {"description": "Fact 1"})
        fact2_belief = agent.add_belief("in_salon(Moutarde)", {"description": "Fact 2"})

        # Set these beliefs as TRUE facts for the JTMS to process
        agent.set_fact(fact1_belief.name, True)
        agent.set_fact(fact2_belief.name, True)

        # Manually add the contradictory rule as a justification.
        # "in_kitchen(Moutarde)" implies "NOT in_salon(Moutarde)".
        # This creates a conflict because "in_salon(Moutarde)" is also a fact.
        # We represent "NOT in_salon(Moutarde)" by adding `fact2_belief.name` to the `out_list`.
        agent.add_justification(
            in_list=[fact1_belief.name],
            out_list=[fact2_belief.name], # This creates the rule: fact1 -> NOT fact2
            conclusion="rule_kitchen_implies_not_salon"
        )

        consistency_report = agent.check_consistency()

        assert not consistency_report["is_consistent"], \
            "The JTMS should report an inconsistency for contradictory facts and rules."
        assert len(consistency_report.get("conflicts", [])) > 0, \
            "The list of conflicts should not be empty."

    @pytest.mark.parametrize("load_scenario", ["ambiguous_scenario"], indirect=True)
    def test_agent_handles_ambiguity(self, kernel, load_scenario):
        """
        Test that the agent reports low confidence when facts are ambiguous.
        """
        async def run_test():
            agent = SherlockJTMSAgent(kernel, agent_name="test_ambiguity_agent")

            # Add facts from the scenario
            for fact in load_scenario["facts"]:
                agent._evidence_manager.add_evidence({"description": fact})

            # Create two competing hypotheses based on the rules.
            # The scenario implies "weapon is Revolver OR weapon is Poignard".
            h1_id = agent._hypothesis_tracker.create_hypothesis("weapon(Revolver)")
            h2_id = agent._hypothesis_tracker.create_hypothesis("weapon(Poignard)")
            
            # In a real scenario, evidence would support one or the other.
            # Here, with no specific supporting evidence, the agent should be uncertain.
            
            solution = await agent.deduce_solution({"goal": "Determine the weapon"})

            assert "error" not in solution, "Deduction should not result in an error."
            assert solution["confidence_score"] < 0.6, \
                f"Confidence should be low for an ambiguous case, but was {solution['confidence_score']}."
            assert len(solution.get("alternative_hypotheses", [])) > 0, \
                "There should be at least one alternative hypothesis."
        asyncio.run(run_test())
