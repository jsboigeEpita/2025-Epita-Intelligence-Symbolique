#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de simulation pour démontrer l'équilibrage de la participation des agents
avec la stratégie BalancedParticipationStrategy.
"""

import asyncio
import logging
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Tuple
from semantic_kernel.agents import Agent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from unittest.mock import MagicMock

# Import des modules du projet
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from argumentiation_analysis.core.strategies import BalancedParticipationStrategy
from argumentiation_analysis.core.shared_state import RhetoricalAnalysisState


# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                   datefmt='%H:%M:%S')
logger = logging.getLogger("SimulationScript")


class ConversationSimulator:
    """Classe pour simuler une conversation avec différentes stratégies de sélection."""
    
    def __init__(self, agent_names: List[str], default_agent: str = "ProjectManagerAgent"):
        """
        Initialise le simulateur avec une liste de noms d'agents.
        
        Args:
            agent_names: Liste des noms d'agents à simuler
            default_agent: Nom de l'agent par défaut
        """
        self.agent_names = agent_names
        self.default_agent = default_agent
        self.agents = self._create_mock_agents(agent_names)
        self.state = RhetoricalAnalysisState("Texte de simulation pour l'analyse rhétorique.")
        self.history = []
        
        logger.info(f"Simulateur initialisé avec {len(agent_names)} agents: {', '.join(agent_names)}")
    
    def _create_mock_agents(self, agent_names: List[str]) -> List[Agent]:
        """Crée des agents simulés pour les tests."""
        agents = []
        for name in agent_names:
            agent = MagicMock(spec=Agent)
            agent.name = name
            agents.append(agent)
        return agents
    
    async def run_simulation(self, strategy: BalancedParticipationStrategy, 
                           num_turns: int, 
                           designation_probability: float = 0.2,
                           designation_bias: Dict[str, float] = None) -> Dict[str, List[float]]:
        """
        Exécute une simulation de conversation avec la stratégie donnée.
        
        Args:
            strategy: La stratégie de sélection à utiliser
            num_turns: Nombre de tours à simuler
            designation_probability: Probabilité qu'un agent soit désigné explicitement
            designation_bias: Biais de désignation pour chaque agent (probabilités relatives)
            
        Returns:
            Dict[str, List[float]]: Historique des taux de participation pour chaque agent
        """
        # Initialiser les compteurs et l'historique
        participation_counts = {name: 0 for name in self.agent_names}
        participation_history = {name: [] for name in self.agent_names}
        
        # Configurer le biais de désignation (par défaut équitable)
        if designation_bias is None:
            designation_bias = {name: 1.0 / len(self.agent_names) for name in self.agent_names}
        
        # Normaliser le biais
        total_bias = sum(designation_bias.values())
        designation_bias = {name: bias / total_bias for name, bias in designation_bias.items()}
        
        logger.info(f"Démarrage de la simulation sur {num_turns} tours")
        logger.info(f"Probabilité de désignation explicite: {designation_probability:.2f}")
        logger.info(f"Biais de désignation: {designation_bias}")
        
        # Exécuter la simulation
        for turn in range(1, num_turns + 1):
            # Décider si on désigne explicitement un agent
            if np.random.random() < designation_probability:
                # Sélectionner un agent selon le biais
                designated_agent = np.random.choice(
                    self.agent_names, 
                    p=[designation_bias.get(name, 0) for name in self.agent_names]
                )
                self.state.designate_next_agent(designated_agent)
                logger.debug(f"Tour {turn}: Désignation explicite de {designated_agent}")
            
            # Sélectionner le prochain agent avec la stratégie
            selected_agent = await strategy.next(self.agents, self.history)
            participation_counts[selected_agent.name] += 1
            
            # Mettre à jour l'historique des taux de participation
            for name in self.agent_names:
                rate = participation_counts[name] / turn
                participation_history[name].append(rate)
            
            # Simuler un message de l'agent sélectionné
            message = MagicMock(spec=ChatMessageContent)
            message.role = AuthorRole.ASSISTANT
            message.name = selected_agent.name
            self.history.append(message)
            
            if turn % 10 == 0 or turn == num_turns:
                logger.info(f"Tour {turn}/{num_turns} - Agent sélectionné: {selected_agent.name}")
                current_rates = {name: count / turn for name, count in participation_counts.items()}
                logger.info(f"Taux de participation actuels: {current_rates}")
        
        # Afficher les résultats finaux
        logger.info("=== Résultats de la simulation ===")
        logger.info(f"Nombre total de tours: {num_turns}")
        for name in self.agent_names:
            count = participation_counts[name]
            rate = count / num_turns
            target = strategy._target_participation[name]
            logger.info(f"{name}: {count} tours ({rate:.2%}) - Cible: {target:.2%}")
        
        return participation_history
    
    def plot_participation_history(self, history: Dict[str, List[float]], 
                                 target_participation: Dict[str, float],
                                 title: str = "Évolution des taux de participation"):
        """
        Génère un graphique montrant l'évolution des taux de participation.
        
        Args:
            history: Historique des taux de participation
            target_participation: Taux de participation cibles
            title: Titre du graphique
        """
        plt.figure(figsize=(12, 6))
        
        # Tracer l'évolution pour chaque agent
        for name, rates in history.items():
            plt.plot(range(1, len(rates) + 1), rates, label=f"{name} (réel)")
            
            # Ajouter une ligne horizontale pour la cible
            if name in target_participation:
                plt.axhline(y=target_participation[name], 
                           linestyle='--', 
                           color=plt.gca().lines[-1].get_color(),
                           alpha=0.7,
                           label=f"{name} (cible)")
        
        plt.title(title)
        plt.xlabel("Nombre de tours")
        plt.ylabel("Taux de participation")
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Enregistrer le graphique
        output_path = os.path.join(os.path.dirname(__file__), "balanced_participation_simulation.png")
        plt.savefig(output_path)
        logger.info(f"Graphique enregistré: {output_path}")
        
        # Afficher le graphique
        plt.tight_layout()
        plt.show()


async def run_standard_simulation():
    """Exécute une simulation standard avec la stratégie d'équilibrage."""
    # Définir les agents
    agent_names = ["ProjectManagerAgent", "PropositionalLogicAgent", "InformalAnalysisAgent"]
    
    # Créer le simulateur
    simulator = ConversationSimulator(agent_names)
    
    # Définir les participations cibles personnalisées
    target_participation = {
        "ProjectManagerAgent": 0.4,
        "PropositionalLogicAgent": 0.3,
        "InformalAnalysisAgent": 0.3
    }
    
    # Créer la stratégie
    strategy = BalancedParticipationStrategy(
        simulator.agents, 
        simulator.state,
        target_participation=target_participation
    )
    
    # Définir un biais de désignation (le PM désigne plus souvent le PL)
    designation_bias = {
        "ProjectManagerAgent": 0.2,
        "PropositionalLogicAgent": 0.6,
        "InformalAnalysisAgent": 0.2
    }
    
    # Exécuter la simulation
    history = await simulator.run_simulation(
        strategy,
        num_turns=100,
        designation_probability=0.3,
        designation_bias=designation_bias
    )
    
    # Afficher les résultats
    simulator.plot_participation_history(history, target_participation)


async def run_comparison_simulation():
    """
    Exécute une simulation comparative avec différentes configurations
    pour montrer l'impact des paramètres sur l'équilibrage.
    """
    # Définir les agents
    agent_names = ["ProjectManagerAgent", "PropositionalLogicAgent", "InformalAnalysisAgent"]
    
    # Créer le simulateur
    simulator = ConversationSimulator(agent_names)
    
    # Configuration 1: Distribution équitable
    equal_targets = {name: 1.0 / len(agent_names) for name in agent_names}
    strategy1 = BalancedParticipationStrategy(
        simulator.agents, 
        simulator.state,
        target_participation=equal_targets
    )
    
    # Configuration 2: PM dominant
    pm_dominant = {
        "ProjectManagerAgent": 0.6,
        "PropositionalLogicAgent": 0.2,
        "InformalAnalysisAgent": 0.2
    }
    strategy2 = BalancedParticipationStrategy(
        simulator.agents, 
        simulator.state,
        target_participation=pm_dominant
    )
    
    # Exécuter les simulations
    logger.info("=== Simulation 1: Distribution équitable ===")
    history1 = await simulator.run_simulation(
        strategy1,
        num_turns=100,
        designation_probability=0.2
    )
    
    # Réinitialiser le simulateur
    simulator = ConversationSimulator(agent_names)
    
    logger.info("=== Simulation 2: PM dominant ===")
    history2 = await simulator.run_simulation(
        strategy2,
        num_turns=100,
        designation_probability=0.2
    )
    
    # Afficher les résultats
    simulator.plot_participation_history(
        history1, 
        equal_targets,
        title="Simulation avec distribution équitable"
    )
    
    simulator.plot_participation_history(
        history2, 
        pm_dominant,
        title="Simulation avec PM dominant"
    )


if __name__ == "__main__":
    # Exécuter la simulation standard
    asyncio.run(run_standard_simulation())
    
    # Pour exécuter la simulation comparative, décommenter:
    # asyncio.run(run_comparison_simulation())