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
        
        Args:
            config: Dictionnaire contenant la configuration du type d'analyse
        """
        self.config = config
        self.name = config.get('name', 'base_analysis_type')
        self.dependencies = config.get('dependencies', [])
    
    def analyze(self, input_data: str, context: dict) -> dict:
        """Effectue l'analyse selon le type défini.
        
        Args:
            input_data: Données à analyser
            context: Contexte d'exécution (agents, outils disponibles)
            
        Returns:
            Dictionnaire contenant les résultats spécifiques à ce type d'analyse
        """
        raise NotImplementedError("La méthode analyze doit être implémentée")
    
    def validate_configuration(self) -> bool:
        """Valide la configuration du type d'analyse.
        
        Returns:
            True si la configuration est valide, False sinon
        """
        return all(key in self.config for key in ['name', 'type', 'parameters'])
    
    def get_expected_results(self) -> dict:
        """Retourne la structure des résultats attendus.
        
        Returns:
            Dictionnaire décrivant la structure des résultats
        """
        return {
            'analysis_type': self.name,
            'results': {
                # Structure à implémenter selon le type d'analyse
            }
        }

# Exemple de configuration
ANALYSIS_TYPE_CONFIG_EXAMPLE = {
    "name": "analyse_sophisme",
    "type": "sophistic_analysis",
    "input_format": "text/markdown",
    "output_format": "application/json",
    "dependencies": ["base_agent", "contextual_fallacy_detector"],
    "parameters": {
        "depth": 2,
        "include_examples": True,
        "language": "fr"
    },
    "integration": {
        "agent_hooks": ["on_analysis_complete", "on_conflict_detected"],
        "tool_requirements": ["argument_coherence_evaluator"]
    }
}