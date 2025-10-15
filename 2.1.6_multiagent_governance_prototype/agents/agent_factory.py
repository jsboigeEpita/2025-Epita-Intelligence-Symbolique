import numpy as np
from .base_agent import Agent, BDIAgent, ReactiveAgent

PERSONALITIES = ["stubborn", "flexible", "strategic", "random"]


class AgentFactory:
    @staticmethod
    def create_agents(agent_configs, seed=None):
        np.random.seed(seed)
        agents = []
        n_agents = len(agent_configs)
        for cfg in agent_configs:
            personality = cfg.get("personality", np.random.choice(PERSONALITIES))
            preferences = cfg.get(
                "preferences", list(np.random.permutation(cfg.get("options", [])))
            )
            agent_type = cfg.get("type", "base").lower()
            if agent_type == "bdi":
                agent = BDIAgent(
                    name=cfg.get("name", f"agent_{len(agents)}"),
                    personality=personality,
                    preferences=preferences,
                    strategy=cfg.get("strategy", None),
                    n_agents=n_agents,
                )
            elif agent_type == "reactive":
                agent = ReactiveAgent(
                    name=cfg.get("name", f"agent_{len(agents)}"),
                    personality=personality,
                    preferences=preferences,
                    strategy=cfg.get("strategy", None),
                    n_agents=n_agents,
                )
            else:
                agent = Agent(
                    name=cfg.get("name", f"agent_{len(agents)}"),
                    personality=personality,
                    preferences=preferences,
                    strategy=cfg.get("strategy", None),
                    n_agents=n_agents,
                )
            agents.append(agent)
        return agents
