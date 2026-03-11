"""
Governance agents — base, BDI, and reactive agent archetypes.

Agents have personalities (stubborn, flexible, strategic, random),
preferences, trust networks, coalitions, argumentation, and Q-learning.

Adapted from 2.1.6_multiagent_governance_prototype/agents/.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

PERSONALITIES = ["stubborn", "flexible", "strategic", "random"]


class Agent:
    """Agent with personality, preferences, trust, memory, coalition logic,
    argumentation, and Q-learning adaptation."""

    def __init__(
        self,
        name: str,
        personality: str,
        preferences: List[str],
        strategy: Optional[str] = None,
        n_agents: Optional[int] = None,
    ):
        self.name = name
        self.personality = personality
        self.preferences = list(preferences)
        self.strategy = strategy
        self.memory: List[Dict[str, Any]] = []
        self.trust: Dict[str, float] = {}
        self.coalition: Optional[str] = None
        self.satisfaction_history: List[float] = []
        self.argument_history: List[Dict[str, Any]] = []
        self.q_table: Dict[Tuple, float] = {}
        self.epsilon = 0.1
        self.alpha = 0.5
        self.gamma = 0.9
        if n_agents:
            self.trust = {
                f"Agent{i+1}": 0.5
                for i in range(n_agents)
                if f"Agent{i+1}" != self.name
            }

    def get_state(self, options, context):
        coalition = self.coalition if self.coalition else "none"
        top_pref = self.preferences[0] if self.preferences else "none"
        return (top_pref, coalition)

    def choose_action(self, options, context):
        """Epsilon-greedy policy from Q-table."""
        state = self.get_state(options, context)
        if np.random.rand() < self.epsilon:
            return np.random.choice(options)
        q_values = [self.q_table.get((state, o), 0.0) for o in options]
        max_q = max(q_values)
        best_options = [o for o, q in zip(options, q_values) if q == max_q]
        return np.random.choice(best_options)

    def update_q(self, options, context, action, reward, next_options, next_context):
        """Q-learning update rule."""
        state = self.get_state(options, context)
        next_state = self.get_state(next_options, next_context)
        max_next_q = (
            max([self.q_table.get((next_state, o), 0.0) for o in next_options])
            if next_options
            else 0.0
        )
        old_q = self.q_table.get((state, action), 0.0)
        self.q_table[(state, action)] = old_q + self.alpha * (
            reward + self.gamma * max_next_q - old_q
        )

    def decide(self, options, context=None):
        """Main decision logic based on personality."""
        if context and self.coalition and "coalition_leader" in context:
            return context["coalition_leader"]
        if (
            len(self.satisfaction_history) >= 3
            and np.mean(self.satisfaction_history[-3:]) < 0.3
        ):
            if self.personality == "stubborn":
                self.personality = "flexible"
        if self.personality == "stubborn":
            return self.preferences[0]
        elif self.personality == "flexible":
            if context and "majority_hint" in context:
                majority = context["majority_hint"]
                if majority in options:
                    return majority
            return self.preferences[0]
        elif self.personality == "strategic":
            if context and "likely_winner" in context and self.trust:
                likely = context["likely_winner"]
                if likely in self.preferences and max(self.trust.values()) > 0.7:
                    return likely
            return (
                self.preferences[1]
                if len(self.preferences) > 1
                else self.preferences[0]
            )
        else:
            return self.choose_action(options, context)

    def update_memory(self, decision, outcome, context=None):
        """Store decision history, update satisfaction, apply Q-learning."""
        self.memory.append(
            {"decision": decision, "outcome": outcome, "context": context}
        )
        if outcome in self.preferences:
            sat = 1.0 - self.preferences.index(outcome) / max(
                1, len(self.preferences) - 1
            )
        else:
            sat = 0
        self.satisfaction_history.append(sat)
        if len(self.memory) > 1:
            prev = self.memory[-2]
            prev_options = (
                prev["context"]["options"]
                if prev["context"] and "options" in prev["context"]
                else []
            )
            prev_context = prev["context"]
            if prev_options:
                self.update_q(
                    prev_options, prev_context, prev["decision"], sat, [], context
                )
        if context and "proposed_by" in context:
            proposer = context["proposed_by"]
            if proposer != self.name:
                self.trust[proposer] = min(1.0, self.trust.get(proposer, 0.5) + 0.1)

    def negotiate(self, options, context=None):
        """Negotiate: form_coalition, propose, accept, or argue."""
        if self.trust and max(self.trust.values()) > 0.8:
            partner = max(self.trust, key=self.trust.get)
            return ("form_coalition", partner)
        if self.personality == "stubborn":
            return ("propose", self.preferences[0])
        elif self.personality == "flexible":
            if (
                context
                and "proposed" in context
                and context["proposed"] in self.preferences[:2]
            ):
                return ("accept", context["proposed"])
            return ("propose", self.preferences[0])
        elif self.personality == "strategic":
            if (
                context
                and "proposed" in context
                and context["proposed"] != self.preferences[0]
            ):
                return (
                    "argue",
                    (
                        self.preferences[1]
                        if len(self.preferences) > 1
                        else self.preferences[0]
                    ),
                )
            return ("propose", self.preferences[0])
        else:
            return ("propose", np.random.choice(options))

    def propose_argument(self, option, reason):
        """Propose an argument for an option."""
        argument = {"agent": self.name, "option": option, "reason": reason}
        self.argument_history.append(argument)
        return argument

    def receive_argument(self, argument):
        """Receive argument from another agent; flexible agents may reorder preferences."""
        self.argument_history.append(argument)
        if self.personality == "flexible" and argument["option"] in self.preferences:
            idx = self.preferences.index(argument["option"])
            if idx > 0:
                self.preferences.pop(idx)
                self.preferences.insert(0, argument["option"])

    def counter_argument(self, option, reason):
        """Counter an argument with a new reason."""
        return self.propose_argument(option, reason)


class BDIAgent(Agent):
    """Belief-Desire-Intention agent for governance."""

    def __init__(self, name, personality, preferences, strategy=None, n_agents=None):
        super().__init__(name, personality, preferences, strategy, n_agents)
        self.beliefs = set()
        self.desires = set()
        self.intentions = set()

    def decide(self, options, context=None):
        if self.intentions:
            for intent in self.intentions:
                if intent in options:
                    return intent
        return super().decide(options, context)

    def update_beliefs(self, new_belief):
        self.beliefs.add(new_belief)

    def add_desire(self, desire):
        self.desires.add(desire)

    def form_intention(self, intention):
        self.intentions.add(intention)


class ReactiveAgent(Agent):
    """Reactive agent that responds using rule-based logic."""

    def __init__(self, name, personality, preferences, strategy=None, n_agents=None):
        super().__init__(name, personality, preferences, strategy, n_agents)
        self.rules = []

    def add_rule(self, condition, action):
        self.rules.append((condition, action))

    def decide(self, options, context=None):
        for condition, action in self.rules:
            if condition(context):
                return action(options, context)
        return super().decide(options, context)


class AgentFactory:
    """Factory for creating governance agents from config dicts."""

    @staticmethod
    def create_agents(agent_configs, seed=None):
        """Create agents from a list of configuration dicts.

        Each config dict may contain: name, personality, preferences, type, options, strategy.
        """
        if seed is not None:
            np.random.seed(seed)
        agents = []
        n_agents = len(agent_configs)
        for cfg in agent_configs:
            personality = cfg.get("personality", np.random.choice(PERSONALITIES))
            preferences = cfg.get(
                "preferences", list(np.random.permutation(cfg.get("options", [])))
            )
            agent_type = cfg.get("type", "base").lower()
            kwargs = dict(
                name=cfg.get("name", f"agent_{len(agents)}"),
                personality=personality,
                preferences=preferences,
                strategy=cfg.get("strategy", None),
                n_agents=n_agents,
            )
            if agent_type == "bdi":
                agent = BDIAgent(**kwargs)
            elif agent_type == "reactive":
                agent = ReactiveAgent(**kwargs)
            else:
                agent = Agent(**kwargs)
            agents.append(agent)
        return agents
