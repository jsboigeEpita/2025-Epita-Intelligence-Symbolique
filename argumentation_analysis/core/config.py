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
    # 'eprover' (défaut) utilise EProver via Tweety's EFOLReasoner — robust (#939).
    # 'prover9' utilise un appel à un processus externe Prover9.
    # 'tweety' fallback — SimpleFolReasoner via JPype, last resort only.
    #
    solver: SolverChoice = SolverChoice.EPROVER

    #
    # Le choix du solveur pour la logique modale.
    # 'tweety' (défaut) utilise SimpleMlReasoner (pure-Java) — query-based
    #   consistency DÉCIDE réellement, aucun binaire externe requis (#1205,
    #   firsthand-vérifié). C'est le défaut honnête.
    # 'spass' utilise SPASSMlReasoner (binaire externe) — disponible mais exige
    #   un build CLI exécutable de SPASS ; le binaire vendoré actuel est un build
    #   GUI/élévation (CreateProcess err740), donc SPASS reste fail-loud None
    #   tant qu'un vrai CLI n'est pas fourni (anti-théâtre #1019, pas de fallback
    #   silencieux). L'ancien défaut 'spass' (#939) n'a jamais décidé :
    #   SPASSMlReasoner n'expose pas isConsistent + binaire non exécutable.
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
