"""
Tests for the Governance module (integrated from 2.1.6).

Tests validate:
- Module import without errors
- CapabilityRegistry registration
- 7 governance methods (voting)
- Agent creation and decision-making
- Simulation and metrics
- Conflict resolution
"""

import pytest
import numpy as np


class TestGovernanceImport:
    """Test that the governance module can be imported."""

    def test_import_package(self):
        """Governance package imports without errors."""
        from argumentation_analysis.agents.core.governance import (
            Agent,
            BDIAgent,
            ReactiveAgent,
            AgentFactory,
            GOVERNANCE_METHODS,
            simulate_governance,
        )

        assert Agent is not None
        assert BDIAgent is not None
        assert ReactiveAgent is not None
        assert AgentFactory is not None
        assert len(GOVERNANCE_METHODS) == 7
        assert callable(simulate_governance)

    def test_import_methods(self):
        """All 7 governance methods are importable."""
        from argumentation_analysis.agents.core.governance.governance_methods import (
            majority_voting,
            plurality_voting,
            borda_count,
            condorcet_method,
            quadratic_voting,
            byzantine_consensus,
            raft_consensus,
            GOVERNANCE_METHODS,
        )

        expected = [
            "majority",
            "plurality",
            "borda",
            "condorcet",
            "quadratic",
            "byzantine",
            "raft",
        ]
        for name in expected:
            assert name in GOVERNANCE_METHODS

    def test_import_metrics(self):
        """Metrics module imports without errors."""
        from argumentation_analysis.agents.core.governance.metrics import (
            consensus_rate,
            gini,
            fairness_index,
            efficiency,
            satisfaction,
            stability,
            summarize_results,
            validate_scenario,
        )

        assert callable(consensus_rate)
        assert callable(gini)

    def test_import_conflict_resolution(self):
        """Conflict resolution module imports."""
        from argumentation_analysis.agents.core.governance.conflict_resolution import (
            detect_conflicts,
            resolve_conflict,
        )

        assert callable(detect_conflicts)
        assert callable(resolve_conflict)


class TestGovernanceRegistration:
    """Test CapabilityRegistry registration."""

    def test_register_governance(self):
        """Governance registers correctly in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import CapabilityRegistry
        from argumentation_analysis.agents.core.governance import Agent

        registry = CapabilityRegistry()
        registry.register_agent(
            "governance_agent",
            Agent,
            capabilities=[
                "governance_simulation",
                "multi_agent_voting",
                "coalition_formation",
            ],
        )

        agents = registry.find_agents_for_capability("governance_simulation")
        assert len(agents) == 1
        assert agents[0].name == "governance_agent"

    def test_provides_declared_capabilities(self):
        """Governance provides the capabilities it declares."""
        from argumentation_analysis.core.capability_registry import CapabilityRegistry
        from argumentation_analysis.agents.core.governance import Agent

        registry = CapabilityRegistry()
        registry.register_agent(
            "governance_agent",
            Agent,
            capabilities=[
                "governance_simulation",
                "multi_agent_voting",
                "coalition_formation",
            ],
        )

        all_caps = registry.get_all_capabilities()
        assert "governance_simulation" in all_caps
        assert "multi_agent_voting" in all_caps
        assert "coalition_formation" in all_caps


class TestGovernanceMethods:
    """Test the 7 governance/voting methods."""

    def _make_agents(self, votes):
        """Create governance Agent objects with preferences matching votes."""
        from argumentation_analysis.agents.core.governance import Agent

        options = list(set(votes))
        agents = []
        for i, vote in enumerate(votes):
            prefs = [vote] + [o for o in options if o != vote]
            a = Agent(name=f"agent_{i}", personality="stubborn", preferences=prefs)
            agents.append(a)
        return agents, options

    def test_majority_voting(self):
        """Majority voting selects the option with most votes."""
        from argumentation_analysis.agents.core.governance.governance_methods import (
            majority_voting,
        )

        agents, options = self._make_agents(["A", "A", "A", "B", "B"])
        result = majority_voting(agents, options, {})
        assert result == "A"

    def test_plurality_voting(self):
        """Plurality voting is an alias for majority."""
        from argumentation_analysis.agents.core.governance.governance_methods import (
            plurality_voting,
        )

        agents, options = self._make_agents(["A", "A", "B", "C", "C"])
        result = plurality_voting(agents, options, {})
        assert result in ["A", "C"]

    def test_borda_count(self):
        """Borda count assigns points by preference ranking."""
        from argumentation_analysis.agents.core.governance.governance_methods import (
            borda_count,
        )
        from argumentation_analysis.agents.core.governance import Agent

        agents = [
            Agent(name="a0", personality="stubborn", preferences=["A", "B", "C"]),
            Agent(name="a1", personality="stubborn", preferences=["A", "C", "B"]),
            Agent(name="a2", personality="stubborn", preferences=["B", "A", "C"]),
        ]
        result = borda_count(agents, ["A", "B", "C"], {})
        assert result == "A"

    def test_condorcet_method(self):
        """Condorcet finds the pairwise winner."""
        from argumentation_analysis.agents.core.governance.governance_methods import (
            condorcet_method,
        )
        from argumentation_analysis.agents.core.governance import Agent

        agents = [
            Agent(name="a0", personality="stubborn", preferences=["A", "B", "C"]),
            Agent(name="a1", personality="stubborn", preferences=["A", "C", "B"]),
            Agent(name="a2", personality="stubborn", preferences=["B", "A", "C"]),
        ]
        result = condorcet_method(agents, ["A", "B", "C"], {})
        assert result == "A"

    def test_quadratic_voting(self):
        """Quadratic voting with credit allocation."""
        from argumentation_analysis.agents.core.governance.governance_methods import (
            quadratic_voting,
        )
        from argumentation_analysis.agents.core.governance import Agent

        agents = [
            Agent(name="a0", personality="stubborn", preferences=["A", "B"]),
            Agent(name="a1", personality="stubborn", preferences=["A", "B"]),
            Agent(name="a2", personality="stubborn", preferences=["B", "A"]),
        ]
        result = quadratic_voting(agents, ["A", "B"], {})
        assert result in ["A", "B"]

    def test_byzantine_consensus(self):
        """Byzantine consensus tolerates faulty agents."""
        from argumentation_analysis.agents.core.governance.governance_methods import (
            byzantine_consensus,
        )

        agents, options = self._make_agents(["A", "A", "A", "A", "B"])
        result = byzantine_consensus(agents, options, {"byzantine_ratio": 0.2})
        assert result in options

    def test_raft_consensus(self):
        """Raft consensus elects a leader and gets acceptance."""
        from argumentation_analysis.agents.core.governance.governance_methods import (
            raft_consensus,
        )

        agents, options = self._make_agents(["A", "A", "A"])
        result = raft_consensus(agents, options, {})
        assert result in options


class TestGovernanceAgents:
    """Test agent creation and behavior."""

    def test_create_agent(self):
        """Basic agent creation with required fields."""
        from argumentation_analysis.agents.core.governance import Agent

        agent = Agent(
            name="test",
            personality="stubborn",
            preferences=["B", "A", "C"],
        )
        assert agent.name == "test"
        assert agent.personality == "stubborn"
        assert agent.preferences == ["B", "A", "C"]

    def test_agent_decide_stubborn(self):
        """Stubborn agent always returns top preference."""
        from argumentation_analysis.agents.core.governance import Agent

        agent = Agent(name="test", personality="stubborn", preferences=["B", "A", "C"])
        decision = agent.decide(["A", "B", "C"])
        assert decision == "B"

    def test_agent_decide_flexible(self):
        """Flexible agent can follow majority hint."""
        from argumentation_analysis.agents.core.governance import Agent

        agent = Agent(name="test", personality="flexible", preferences=["B", "A", "C"])
        decision = agent.decide(["A", "B", "C"], {"majority_hint": "A"})
        assert decision == "A"

    def test_bdi_agent(self):
        """BDI agent has beliefs, desires, and intentions."""
        from argumentation_analysis.agents.core.governance import BDIAgent

        agent = BDIAgent(
            name="bdi_test",
            personality="flexible",
            preferences=["A", "B"],
        )
        assert hasattr(agent, "beliefs")
        assert hasattr(agent, "desires")
        assert hasattr(agent, "intentions")
        decision = agent.decide(["A", "B"])
        assert decision in ["A", "B"]

    def test_bdi_agent_intention(self):
        """BDI agent follows intentions when set."""
        from argumentation_analysis.agents.core.governance import BDIAgent

        agent = BDIAgent(
            name="bdi_test",
            personality="flexible",
            preferences=["A", "B"],
        )
        agent.form_intention("B")
        decision = agent.decide(["A", "B"])
        assert decision == "B"

    def test_reactive_agent(self):
        """Reactive agent decides based on rules or fallback."""
        from argumentation_analysis.agents.core.governance import ReactiveAgent

        agent = ReactiveAgent(
            name="reactive_test",
            personality="stubborn",
            preferences=["A", "B"],
        )
        decision = agent.decide(["A", "B"])
        assert decision in ["A", "B"]

    def test_agent_factory(self):
        """AgentFactory creates agents from config dicts."""
        from argumentation_analysis.agents.core.governance import AgentFactory

        configs = [
            {"name": "alice", "options": ["A", "B"], "preferences": ["A", "B"]},
            {
                "name": "bob",
                "options": ["A", "B"],
                "preferences": ["B", "A"],
                "type": "bdi",
            },
            {
                "name": "charlie",
                "options": ["A", "B"],
                "preferences": ["A", "B"],
                "type": "reactive",
            },
        ]
        agents = AgentFactory.create_agents(configs)
        assert len(agents) == 3
        assert agents[0].name == "alice"

    def test_agent_qlearning_update(self):
        """Agent Q-learning updates via update_q."""
        from argumentation_analysis.agents.core.governance import Agent

        agent = Agent(
            name="learner",
            personality="random",
            preferences=["A", "B"],
        )
        state = agent.get_state(["A", "B"], {})
        old_q = agent.q_table.get((state, "A"), 0.0)
        agent.update_q(["A", "B"], {}, "A", 1.0, ["A", "B"], {})
        new_q = agent.q_table.get((state, "A"), 0.0)
        assert new_q != old_q or old_q == 0.0

    def test_agent_negotiate(self):
        """Agent negotiate returns a negotiation action."""
        from argumentation_analysis.agents.core.governance import Agent

        agent = Agent(
            name="negotiator",
            personality="stubborn",
            preferences=["A", "B"],
        )
        action, value = agent.negotiate(["A", "B"])
        assert action in ["propose", "accept", "argue", "form_coalition"]

    def test_agent_argumentation(self):
        """Agent can propose and receive arguments."""
        from argumentation_analysis.agents.core.governance import Agent

        a1 = Agent(name="alice", personality="stubborn", preferences=["A", "B"])
        a2 = Agent(name="bob", personality="flexible", preferences=["B", "A"])

        arg = a1.propose_argument("A", "A is more efficient")
        assert arg["agent"] == "alice"
        assert arg["option"] == "A"

        a2.receive_argument(arg)
        assert a2.preferences[0] == "A"


class TestGovernanceMetrics:
    """Test governance metrics computation."""

    def test_consensus_rate(self):
        """Consensus rate is fraction voting for winner."""
        from argumentation_analysis.agents.core.governance.metrics import consensus_rate

        result = {"votes": ["A", "A", "A", "B", "B"], "winner": "A"}
        assert consensus_rate(result) == 0.6

    def test_consensus_rate_empty(self):
        """Consensus rate handles empty input."""
        from argumentation_analysis.agents.core.governance.metrics import consensus_rate

        assert consensus_rate({}) == 0.0
        assert consensus_rate(None) == 0.0

    def test_gini_equal(self):
        """Gini is 0 for perfectly equal distribution."""
        from argumentation_analysis.agents.core.governance.metrics import gini

        result = gini([1, 1, 1, 1])
        assert abs(result) < 0.01

    def test_gini_unequal(self):
        """Gini is high for unequal distribution."""
        from argumentation_analysis.agents.core.governance.metrics import gini

        result = gini([0, 0, 0, 100])
        assert result > 0.5

    def test_fairness_index(self):
        """Fairness = 1 - Gini."""
        from argumentation_analysis.agents.core.governance.metrics import fairness_index

        result = {"satisfaction": [1.0, 1.0, 1.0, 1.0]}
        fairness = fairness_index(result)
        assert fairness > 0.9

    def test_efficiency(self):
        """Efficiency is 1 when resolved in 1 round."""
        from argumentation_analysis.agents.core.governance.metrics import efficiency

        assert efficiency({"rounds": 1}, max_rounds=3) == 1.0
        assert efficiency({"rounds": 3}, max_rounds=3) == 0.0

    def test_satisfaction_mean(self):
        """Satisfaction is mean of agent satisfaction scores."""
        from argumentation_analysis.agents.core.governance.metrics import satisfaction

        result = {"satisfaction": [0.8, 0.6, 1.0]}
        assert abs(satisfaction(result) - 0.8) < 0.01

    def test_stability(self):
        """Stability is 1 if all runs have same winner."""
        from argumentation_analysis.agents.core.governance.metrics import stability

        results_list = [
            {"winner": "A"},
            {"winner": "A"},
            {"winner": "A"},
        ]
        assert stability(results_list) == 1.0

    def test_stability_unstable(self):
        """Stability is 0 if runs have different winners."""
        from argumentation_analysis.agents.core.governance.metrics import stability

        results_list = [{"winner": "A"}, {"winner": "B"}]
        assert stability(results_list) == 0.0

    def test_summarize_single(self):
        """Summarize works for a single result."""
        from argumentation_analysis.agents.core.governance.metrics import (
            summarize_results,
        )

        result = {
            "votes": ["A", "A", "B"],
            "winner": "A",
            "satisfaction": [1.0, 0.5, 0.5],
            "rounds": 1,
        }
        summary = summarize_results(result)
        assert "consensus_rate" in summary
        assert "fairness" in summary
        assert "efficiency" in summary

    def test_validate_scenario_valid(self):
        """Valid scenario passes validation."""
        from argumentation_analysis.agents.core.governance.metrics import (
            validate_scenario,
        )

        scenario = {
            "agents": [
                {"name": "a1", "preferences": ["X", "Y"], "options": ["X", "Y"]},
                {"name": "a2", "preferences": ["Y", "X"], "options": ["X", "Y"]},
            ],
            "options": ["X", "Y"],
        }
        is_valid, msg = validate_scenario(scenario)
        assert is_valid is True

    def test_validate_scenario_invalid(self):
        """Invalid scenario fails validation."""
        from argumentation_analysis.agents.core.governance.metrics import (
            validate_scenario,
        )

        is_valid, msg = validate_scenario({})
        assert is_valid is False


class TestConflictResolution:
    """Test conflict detection and resolution."""

    def test_detect_conflicts(self):
        """Detects conflicts between differing positions."""
        from argumentation_analysis.agents.core.governance.conflict_resolution import (
            detect_conflicts,
        )

        positions = {"alice": "A", "bob": "B", "charlie": "A"}
        conflicts = detect_conflicts(positions)
        assert len(conflicts) == 2

    def test_detect_no_conflicts(self):
        """No conflicts when all agree."""
        from argumentation_analysis.agents.core.governance.conflict_resolution import (
            detect_conflicts,
        )

        positions = {"alice": "A", "bob": "A"}
        conflicts = detect_conflicts(positions)
        assert len(conflicts) == 0

    def test_resolve_collaborative(self):
        """Collaborative mediation returns expected format."""
        from argumentation_analysis.agents.core.governance.conflict_resolution import (
            resolve_conflict,
        )

        conflict = {"agents": ["alice", "bob"], "conflict_level": 1.0}
        resolution = resolve_conflict(conflict, strategy="collaborative")
        assert resolution["resolution_type"] == "collaborative"
        assert resolution["success_probability"] == 0.8

    def test_resolve_competitive(self):
        """Competitive mediation has lower success."""
        from argumentation_analysis.agents.core.governance.conflict_resolution import (
            resolve_conflict,
        )

        conflict = {"agents": ["alice", "bob"], "conflict_level": 1.0}
        resolution = resolve_conflict(conflict, strategy="competitive")
        assert resolution["resolution_type"] == "competitive"
        assert resolution["success_probability"] == 0.5

    def test_resolve_compromise(self):
        """Compromise mediation returns expected format."""
        from argumentation_analysis.agents.core.governance.conflict_resolution import (
            resolve_conflict,
        )

        conflict = {"agents": ["alice", "bob"], "conflict_level": 1.0}
        resolution = resolve_conflict(conflict, strategy="compromise")
        assert resolution["resolution_type"] == "compromise"
        assert resolution["success_probability"] == 0.7


class TestSimulation:
    """Test governance simulation functions."""

    def test_simulate_governance_basic(self):
        """Basic governance simulation runs end-to-end."""
        from argumentation_analysis.agents.core.governance import AgentFactory
        from argumentation_analysis.agents.core.governance.simulation import (
            simulate_governance,
        )

        configs = [
            {"name": "a1", "preferences": ["X", "Y"], "personality": "stubborn"},
            {"name": "a2", "preferences": ["Y", "X"], "personality": "stubborn"},
            {"name": "a3", "preferences": ["X", "Y"], "personality": "stubborn"},
        ]
        agents = AgentFactory.create_agents(configs)
        scenario_data = {"options": ["X", "Y"]}
        result = simulate_governance(agents, scenario_data, "majority")
        assert result is not None
        assert "winner" in result

    def test_shapley_value(self):
        """Shapley value computation returns per-agent values."""
        from argumentation_analysis.agents.core.governance import Agent
        from argumentation_analysis.agents.core.governance.simulation import (
            shapley_value,
        )

        agents = [
            Agent(name="a1", personality="stubborn", preferences=["X"]),
            Agent(name="a2", personality="stubborn", preferences=["X"]),
            Agent(name="a3", personality="stubborn", preferences=["X"]),
        ]

        def payoff(names):
            return 1.0 if len(names) >= 2 else 0.0

        values = shapley_value(agents, agents, payoff)
        assert len(values) == 3
        assert all(isinstance(v, (int, float)) for v in values.values())
