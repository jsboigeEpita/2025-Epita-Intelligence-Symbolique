"""
Template pour la création d'outils d'analyse dans l'architecture hiérarchique.

Ce module fournit une classe de base `BaseAnalysisTool` que les outils d'analyse
spécifiques peuvent hériter. Il définit une interface commune pour l'initialisation,
l'analyse, la validation des entrées et la récupération des résultats.
"""

# Template d'outil d'analyse pour l'architecture hiérarchique


class BaseAnalysisTool:
    """Classe de base pour les outils d'analyse rhétorique.

    Attributs:
        config: Configuration de l'outil
        name: Nom de l'outil
    """

    def __init__(self, config: dict):
        """Initialise l'outil d'analyse avec sa configuration.

        :param config: Dictionnaire contenant la configuration de l'outil.
        :type config: dict
        """
        self.config = config
        self.name = config.get("name", "base_analysis_tool")

    def analyze(self, input_data: str) -> dict:
        """Analyse les données d'entrée et retourne les résultats.

        Cette méthode doit être implémentée par les classes dérivées.

        :param input_data: Données à analyser.
        :type input_data: str
        :return: Dictionnaire contenant les résultats de l'analyse.
        :rtype: dict
        :raises NotImplementedError: Si la méthode n'est pas implémentée dans la classe dérivée.
        """
        raise NotImplementedError("La méthode analyze doit être implémentée")

    def validate_input(self, input_data: str) -> bool:
        """Valide le format des données d'entrée.

        Par défaut, cette méthode retourne True. Les classes dérivées peuvent
        la surcharger pour implémenter une logique de validation spécifique.

        :param input_data: Données à valider.
        :type input_data: str
        :return: True si les données sont valides, False sinon.
        :rtype: bool
        """
        return True

    def get_results(self) -> dict:
        """Retourne les résultats de l'analyse.

        Par défaut, retourne un dictionnaire de base avec le nom de l'outil
        et un statut "completed". Les classes dérivées peuvent surcharger
        cette méthode pour retourner des résultats plus spécifiques.

        :return: Dictionnaire contenant les résultats structurés.
        :rtype: dict
        """
        return {
            "tool": self.name,
            "status": "completed",
            # Charge de résultats sous la clé chaîne "results" — sérialisable
            # en JSON (#2180) ; l'ancienne clé Path cassait json.dumps.
            "results": {},
        }


# Exemple de configuration
ANALYSIS_TOOL_CONFIG_EXAMPLE = {
    "name": "analyse_rhetorique",
    "type": "rhetorical_analysis",
    "input_format": "text/plain",
    "output_format": "application/json",
    "dependencies": ["base_agent", "argument_coherence_evaluator"],
    "parameters": {"language": "fr", "depth": 3, "include_visualization": True},
}
