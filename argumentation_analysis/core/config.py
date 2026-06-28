import enum
from pydantic_settings import BaseSettings, SettingsConfigDict


class SolverChoice(str, enum.Enum):
    """Énumération pour les choix de solveurs disponibles."""

    TWEETY = "tweety"
    PROVER9 = "prover9"
    EPROVER = "eprover"
    # FP-19 #1243: Mace4 (LADR model-finder) as a selectable, comparable FOL
    # backend. Mace4 is a SEMI-decision procedure for satisfiability — it proves
    # CONSISTENT by exhibiting a finite model; it is the sound complement to the
    # refutation provers (EProver/Prover9, which prove INCONSISTENT). It must be
    # run bounded + with a hard timeout (an unbounded model search hangs forever
    # on an inconsistent KB — firsthand-verified, the #1240 trap in this dimension).
    MACE4 = "mace4"


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
    #   firsthand-vérifié). C'est le défaut honnête QUAND SPASS n'est pas
    #   disponible.
    # 'spass' utilise SPASSMlReasoner (binaire externe) — le binaire vendoré
    #   `ext_tools/spass/SPASS.exe` (build CLI natif post-#1242, + adapter
    #   EML→eml) DÉCIDE sur les KB qui OOM SimpleMlReasoner (#1239/#1242,
    #   firsthand 4/4). Track C #1279 : le chemin pipeline réel préfère
    #   SPASS quand il est détecté (voir ``modal_prefer_spass_when_available``).
    #
    modal_solver: ModalSolverChoice = ModalSolverChoice.TWEETY

    #
    # Track C #1279 : quand un binaire SPASS vendoré est détecté
    # (``EXTERNAL_TOOL_PATHS['spass']`` peuplé par ``jvm_setup``), le chemin
    # pipeline ``_invoke_modal_logic`` route vers SPASS — le solveur qui DÉCIDE
    # sans OOM, au lieu du défaut SimpleMlReasoner (Kripke naïf, OOM sur KB
    # réels ~12 atomes, FP-16 #1231). Anti-pendule : on *soustrait* le défaut
    # OOM-prone en routant vers le solveur capable, on n'empile pas un try/except
    # sur l'OOM. Un utilisateur/fixture peut forcer TWEETY (False) pour tester
    # le path SimpleMlReasoner explicitement — un ``modal_solver`` explicitement
    # choisi est toujours respecté.
    #
    modal_prefer_spass_when_available: bool = True

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
