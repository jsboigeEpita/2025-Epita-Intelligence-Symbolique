# -*- coding: utf-8 -*-
"""
Définition des interfaces pour les personnalités des agents.

Ce module établit le contrat formel (interface) pour ce qui définit une "personnalité" d'agent,
la rendant chargeable et utilisable par l'AgentLoader.
"""
from abc import abstractmethod
from typing import Any, Dict

from src.core.plugins.interfaces import BasePlugin


class IAgentPersonality(BasePlugin):
    """
    Interface pour une "personnalité" d'agent.

    Hérite de BasePlugin pour la réutilisation des métadonnées
    et définit les comportements spécifiques à un agent.
    """

    @abstractmethod
    def load_configuration(self, config_data: Dict[str, Any]) -> None:
        """
        Charge la configuration spécifique de l'agent.
        """
        raise NotImplementedError

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Retourne le prompt système qui définit le comportement fondamental de l'agent.
        """
        raise NotImplementedError
