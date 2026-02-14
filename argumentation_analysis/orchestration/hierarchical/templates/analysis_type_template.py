"""
Template pour la définition de types d'analyse dans l'architecture hiérarchique.

Ce module fournit une classe de base `BaseAnalysisType` que les types d'analyse
spécifiques peuvent hériter. Il définit une interface commune pour l'initialisation,
l'exécution de l'analyse, la validation de la configuration et la description
de la structure des résultats attendus.
"""

from argumentation_analysis.paths import RESULTS_DIR

# Template de type d'analyse pour l'architecture hiérarchique


class BaseAnalysisType:
    """Classe de base pour définir un nouveau type d'analyse rhétorique.

    Attributs:
        config: Configuration du type d'analyse
        name: Nom du type d'analyse
        dependencies: Dépendances requises
    """

    def __init__(self, config: dict):
        """Initialise le type d'analyse avec sa configuration.

        :param config: Dictionnaire contenant la configuration du type d'analyse.
        :type config: dict
        """
        self.config = config
        self.name = config.get("name", "base_analysis_type")
        self.dependencies = config.get("dependencies", [])

    def analyze(self, input_data: str, context: dict) -> dict:
        """Effectue l'analyse selon le type défini.

        Cette méthode doit être implémentée par les classes dérivées.

        :param input_data: Données à analyser.
        :type input_data: str
        :param context: Contexte d'exécution (par exemple, agents, outils disponibles).
        :type context: dict
        :return: Dictionnaire contenant les résultats spécifiques à ce type d'analyse.
        :rtype: dict
        :raises NotImplementedError: Si la méthode n'est pas implémentée dans la classe dérivée.
        """
        raise NotImplementedError("La méthode analyze doit être implémentée")

    def validate_configuration(self) -> bool:
        """Valide la configuration du type d'analyse.

        Par défaut, vérifie la présence des clés 'name', 'type', et 'parameters'.
        Les classes dérivées peuvent surcharger cette méthode pour une validation plus spécifique.

        :return: True si la configuration est valide, False sinon.
        :rtype: bool
        """
        return all(key in self.config for key in ["name", "type", "parameters"])

    def get_expected_results(self) -> dict:
        """Retourne la structure des résultats attendus.

        Les classes dérivées devraient surcharger cette méthode pour décrire
        la structure spécifique des résultats qu'elles produisent.

        :return: Dictionnaire décrivant la structure des résultats.
        :rtype: dict
        """
        return {
            "analysis_type": self.name,
            RESULTS_DIR: {  # RESULTS_DIR est une constante Path, son utilisation comme clé ici pourrait être revue.
                # Structure à implémenter selon le type d'analyse
            },
        }


# Exemple de configuration
ANALYSIS_TYPE_CONFIG_EXAMPLE = {
    "name": "analyse_sophisme",
    "type": "sophistic_analysis",
    "input_format": "text/markdown",
    "output_format": "application/json",
    "dependencies": ["base_agent", "contextual_fallacy_detector"],
    "parameters": {"depth": 2, "include_examples": True, "language": "fr"},
    "integration": {
        "agent_hooks": ["on_analysis_complete", "on_conflict_detected"],
        "tool_requirements": ["argument_coherence_evaluator"],
    },
}
