# Template d'agent pour l'architecture hiérarchique


class BaseAgent:
    """Classe de base pour tous les agents du système d'orchestration.

    Attributs:
        config: Configuration de l'agent
        name: Nom de l'agent
    """

    def __init__(self, config: dict):
        """Initialise l'agent avec sa configuration.

        Args:
            config: Dictionnaire contenant la configuration de l'agent
        """
        self.config = config
        self.name = config.get("name", "base_agent")

    def process(self, input_data: str) -> dict:
        """Traite les données d'entrée et retourne les résultats.

        Args:
            input_data: Données à analyser

        Returns:
            Dictionnaire contenant les résultats de l'analyse
        """
        raise NotImplementedError("La méthode process doit être implémentée")

    def validate_input(self, input_data: str) -> bool:
        """Valide le format des données d'entrée.

        Args:
            input_data: Données à valider

        Returns:
            True si les données sont valides, False sinon
        """
        return True

    def get_status(self) -> dict:
        """Retourne l'état courant de l'agent.

        Returns:
            Dictionnaire contenant l'état de l'agent
        """
        return {"name": self.name, "status": "ready", "last_processed": None}


# Exemple de configuration
AGENT_CONFIG_EXAMPLE = {
    "name": "mon_agent",
    "type": "specialiste",
    "priority": 1,
    "capabilities": ["analyse_rhetorique", "traitement_texte"],
    "dependencies": ["outil_analyse_1", "outil_analyse_2"],
}
