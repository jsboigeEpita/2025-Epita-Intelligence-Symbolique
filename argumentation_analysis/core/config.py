import enum
from pydantic_settings import BaseSettings, SettingsConfigDict


class SolverChoice(str, enum.Enum):
    """Énumération pour les choix de solveurs disponibles."""

    TWEETY = "tweety"
    PROVER9 = "prover9"
    EPROVER = "eprover"


class ModalSolverChoice(str, enum.Enum):
    """Énumération pour les solveurs de logique modale."""

    TWEETY = "tweety"
    SPASS = "spass"


class PLSolverChoice(str, enum.Enum):
    """Énumération pour les solveurs de logique propositionnelle."""

    TWEETY = "tweety"
    PYSAT = "pysat"


class ArgAnalysisSettings(BaseSettings):
    """
    Paramètres de configuration pour le système d'analyse d'arguments.

    Les valeurs sont chargées à partir des variables d'environnement.
    """

    #
    # Le choix du solveur à utiliser pour les opérations de logique FOL.
    # 'tweety' (défaut) utilise le pont JPype vers TweetyProject (SimpleFolReasoner).
    # 'prover9' utilise un appel à un processus externe Prover9.
    # 'eprover' utilise EProver via Tweety's EFOLReasoner (requires eprover binary).
    #
    solver: SolverChoice = SolverChoice.TWEETY

    #
    # Le choix du solveur pour la logique modale.
    # 'tweety' (défaut) utilise SimpleMlReasoner.
    # 'spass' utilise SPASSMlReasoner (requires SPASS binary).
    #
    modal_solver: ModalSolverChoice = ModalSolverChoice.TWEETY

    #
    # Le choix du solveur pour la logique propositionnelle.
    # 'tweety' (défaut) utilise SimplePlReasoner via JPype.
    # 'pysat' utilise PySAT (CaDiCaL, Glucose, etc.) — no JVM required.
    #
    pl_solver: PLSolverChoice = PLSolverChoice.TWEETY

    #
    # Le solveur SAT spécifique à utiliser avec PySAT.
    # Options: cadical195, cryptominisat5, glucose42, maplechrono, lingeling, minisat22
    #
    pysat_solver: str = "cadical195"

    model_config = SettingsConfigDict(env_prefix="ARG_ANALYSIS_")


# Instance unique à importer dans les autres modules
settings = ArgAnalysisSettings()
