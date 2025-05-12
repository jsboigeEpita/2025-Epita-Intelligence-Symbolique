# Template d'outil d'analyse pour l'architecture hiérarchique

class BaseAnalysisTool:
    """Classe de base pour les outils d'analyse rhétorique.
    
    Attributs:
        config: Configuration de l'outil
        name: Nom de l'outil
    """
    
    def __init__(self, config: dict):
        """Initialise l'outil d'analyse avec sa configuration.
        
        Args:
            config: Dictionnaire contenant la configuration de l'outil
        """
        self.config = config
        self.name = config.get('name', 'base_analysis_tool')
    
    def analyze(self, input_data: str) -> dict:
        """Analyse les données d'entrée et retourne les résultats.
        
        Args:
            input_data: Données à analyser
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse
        """
        raise NotImplementedError("La méthode analyze doit être implémentée")
    
    def validate_input(self, input_data: str) -> bool:
        """Valide le format des données d'entrée.
        
        Args:
            input_data: Données à valider
            
        Returns:
            True si les données sont valides, False sinon
        """
        return True
    
    def get_results(self) -> dict:
        """Retourne les résultats de l'analyse.
        
        Returns:
            Dictionnaire contenant les résultats structurés
        """
        return {
            'tool': self.name,
            'status': 'completed',
            'results': {}
        }

# Exemple de configuration
ANALYSIS_TOOL_CONFIG_EXAMPLE = {
    "name": "analyse_rhetorique",
    "type": "rhetorical_analysis",
    "input_format": "text/plain",
    "output_format": "application/json",
    "dependencies": ["base_agent", "argument_coherence_evaluator"],
    "parameters": {
        "language": "fr",
        "depth": 3,
        "include_visualization": True
    }
}