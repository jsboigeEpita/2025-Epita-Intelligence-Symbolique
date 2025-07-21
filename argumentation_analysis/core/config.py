import enum
from pydantic_settings import BaseSettings, SettingsConfigDict

class SolverChoice(str, enum.Enum):
    """Énumération pour les choix de solveurs disponibles."""
    TWEETY = "tweety"
    PROVER9 = "prover9"

class ArgAnalysisSettings(BaseSettings):
    """
    Paramètres de configuration pour le système d'analyse d'arguments.
    
    Les valeurs sont chargées à partir des variables d'environnement.
    """
    #
    # Le choix du solveur à utiliser pour les opérations de logique.
    # 'tweety' (défaut) utilise le pont JPype vers TweetyProject.
    # 'prover9' utilise un appel à un processus externe Prover9.
    #
    solver: SolverChoice = SolverChoice.TWEETY

    model_config = SettingsConfigDict(
        env_prefix='ARG_ANALYSIS_'
    )

# Instance unique à importer dans les autres modules
settings = ArgAnalysisSettings()