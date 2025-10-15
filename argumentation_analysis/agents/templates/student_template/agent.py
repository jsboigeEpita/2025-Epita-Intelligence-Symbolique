"""
Template d'agent pour les étudiants.
Ce fichier contient l'implémentation principale de l'agent.
"""

from typing import Dict, List, Any, Optional
from .definitions import AgentInput, AgentOutput
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


class StudentAgent:
    """
    Classe de base pour un agent étudiant.

    Cette classe fournit une structure de base pour implémenter un nouvel agent
    dans le système d'analyse d'argumentation.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise un nouvel agent étudiant.

        Args:
            config: Configuration optionnelle pour l'agent
        """
        self.config = config or {}
        # Initialisez ici les attributs spécifiques à votre agent

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """
        Traite les données d'entrée et produit une sortie.

        Cette méthode est le point d'entrée principal de l'agent.

        Args:
            input_data: Les données d'entrée à traiter

        Returns:
            Les données de sortie produites par l'agent
        """
        # Implémentez ici la logique de traitement de votre agent

        # Exemple simple:
        prompt = self._prepare_prompt(input_data)
        # Utilisez un service LLM pour obtenir une réponse
        # response = await llm_service.generate(prompt)

        # Traitez la réponse
        # result = self._process_response(response)

        # Pour l'exemple, nous retournons une sortie factice
        return AgentOutput(
            result="Résultat de l'analyse",
            confidence=0.8,
            metadata={"processing_time": 1.5, "model_used": "example-model"},
        )

    def _prepare_prompt(self, input_data: AgentInput) -> str:
        """
        Prépare le prompt à envoyer au modèle de langage.

        Args:
            input_data: Les données d'entrée

        Returns:
            Le prompt formaté
        """
        # Utilisez les templates de prompts définis dans prompts.py
        return USER_PROMPT_TEMPLATE.format(
            text=input_data.text, context=input_data.context
        )

    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        Traite la réponse du modèle de langage.

        Args:
            response: La réponse brute du modèle

        Returns:
            Les données extraites et structurées
        """
        # Implémentez ici la logique de traitement de la réponse
        # Par exemple, extraction de données structurées, analyse, etc.
        return {"raw_response": response, "processed_data": "Données traitées"}


# Vous pouvez ajouter d'autres classes ou fonctions utiles ici
