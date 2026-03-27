# argumentation_analysis/core/bootstrap.py
import os
import sys
from pathlib import Path
import logging
from typing import Dict, List, Any
from argumentation_analysis.adapters.contextual_fallacy_detector_adapter import (
    ContextualFallacyDetectorAdapter,
)
import threading

# --- Verrou global pour l'initialisation de la JVM ---
_JVM_INITIALIZED = False
_JVM_INIT_LOCK = threading.Lock()

# Configuration du logger pour ce module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)  # Ou logging.DEBUG pour plus de détails

# Ajout de la racine du projet au sys.path pour les imports
project_root = None
try:
    current_script_path = Path(__file__).resolve()
    # argumentation_analysis/core/bootstrap.py -> argumentation_analysis/core -> argumentation_analysis -> project_root
    project_root = current_script_path.parent.parent.parent
    # La ligne suivante est la source de conflits avec pytest.
    # Le chemin doit être ajouté par l'exécutant (comme pytest via pyproject.toml ou le script de lancement)
    # if str(project_root) not in sys.path:
    #     sys.path.insert(0, str(project_root))
    # logger.info(f"Project root (from bootstrap.py) added to sys.path: {project_root}")
except (
    NameError
):  # __file__ n'est pas défini si exécuté interactivement ou via exec() sans contexte de fichier
    logger.warning(
        "__file__ not defined, sys.path might not be configured correctly by bootstrap.py itself."
    )
    pass


# Imports des services et modules nécessaires (seront dans des try-except)
try:
    from argumentation_analysis.config.settings import settings
except ImportError as e:
    logger.error(
        f"CRITICAL: Failed to import settings from argumentation_analysis.config: {e}"
    )
    settings = None

initialize_jvm_func = None
CryptoService_class = None
DefinitionService_class = None
create_llm_service_func = None
InformalAgent_class = None
ContextualFallacyDetector_class = None
sk_module = None
ENCRYPTION_KEY_imported = None
ExtractDefinitions_class, SourceDefinition_class, Extract_class = None, None, None

try:
    from argumentation_analysis.core.jvm_setup import (
        initialize_jvm as initialize_jvm_func,
    )
except ImportError as e:
    logger.error(
        f"Failed to import start_jvm_if_needed (aliased as initialize_jvm_func): {e}"
    )

try:
    from argumentation_analysis.services.crypto_service import (
        CryptoService as CryptoService_class,
    )
except ImportError as e:
    logger.error(f"Failed to import CryptoService: {e}")

try:
    from argumentation_analysis.services.definition_service import (
        DefinitionService as DefinitionService_class,
    )
except ImportError as e:
    logger.error(f"Failed to import DefinitionService: {e}")

try:
    from argumentation_analysis.core.llm_service import (
        create_llm_service as create_llm_service_func,
    )
except ImportError as e:
    logger.error(f"Failed to import create_llm_service: {e}")

try:
    from argumentation_analysis.agents.core.informal.informal_agent import (
        InformalAnalysisAgent as InformalAgent_class,
    )
except ImportError as e:
    logger.error(f"Failed to import {e}")

try:
    import semantic_kernel as sk_module
except ImportError as e:
    logger.error(f"Failed to import semantic_kernel: {e}")
    sk_module = None

# L'import de ENCRYPTION_KEY depuis ui.config est supprimé au profit de l'objet settings.
ENCRYPTION_KEY_imported = None

try:
    from argumentation_analysis.models.extract_definition import (
        ExtractDefinitions as ExtractDefinitions_class,
        SourceDefinition as SourceDefinition_class,
        Extract as Extract_class,
    )
except ImportError as e:
    logger.error(f"Failed to import extract models (ExtractDefinitions, etc.): {e}")

try:
    from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
        ContextualFallacyDetector as ContextualFallacyDetector_class,
    )
except ImportError as e:
    logger.error(f"Failed to import ContextualFallacyDetector: {e}")

# L'adaptateur local est maintenant remplacé par celui dans argumentation_analysis.adapters


class ProjectContext:
    def __init__(self):
        self.kernel: sk_module.Kernel = None
        self.jvm_initialized = False
        self.crypto_service = None
        self.definition_service = None
        self.llm_service = None
        self._fallacy_detector_instance = None
        self._fallacy_detector_lock = threading.Lock()
        self.tweety_classes = {}
        self.config = {}
        self.settings = None
        self.project_root_path = None
        self.services = {}  # Dictionnaire pour regrouper les services

    def get_fallacy_detector(self):
        """
        Initialise de manière paresseuse et retourne le ContextualFallacyDetector.
        L'initialisation est thread-safe.
        """
        if self._fallacy_detector_instance is None:
            with self._fallacy_detector_lock:
                # Double-vérification pour s'assurer que l'instance n'a pas été créée
                # pendant que le thread attendait le verrou.
                if self._fallacy_detector_instance is None:
                    logger.info(
                        "Initialisation paresseuse de ContextualFallacyDetector..."
                    )
                    if ContextualFallacyDetector_class:
                        try:
                            original_detector = ContextualFallacyDetector_class()
                            # Utilisation du nouvel adaptateur importé
                            self._fallacy_detector_instance = (
                                ContextualFallacyDetectorAdapter(original_detector)
                            )
                            logger.info(
                                "ContextualFallacyDetector initialisé via l'adaptateur et mis en cache."
                            )
                        except Exception as e:
                            logger.error(
                                f"Erreur lors de l'initialisation paresseuse de ContextualFallacyDetector : {e}",
                                exc_info=True,
                            )
                            # On retourne None pour que l'application puisse continuer
                            # sans le détecteur si l'initialisation échoue.
                            return None
                    else:
                        logger.error(
                            "Impossible d'initialiser paresseusement : ContextualFallacyDetector_class n'a pas été importé."
                        )
                        return None
        return self._fallacy_detector_instance


def _load_tweety_classes(context: "ProjectContext"):
    """Charge les classes Tweety nécessaires si la JVM est démarrée."""
    if not context.jvm_initialized:
        logger.warning(
            "Tentative de chargement des classes Tweety alors que la JVM n'est pas initialisée."
        )
        return

    try:
        import jpype
        import jpype.imports

        logger.info(
            "Chargement des classes Java depuis Tweety pour l'analyse d'argumentation textuelle..."
        )

        # 1. Charger le parser pour la logique propositionnelle (langage sous-jacent)
        PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        pl_parser_instance = PlParser()
        logger.info(
            "Classe 'org.tweetyproject.logics.pl.parser.PlParser' chargée et instanciée."
        )

        # 2. Charger le générateur de formules pour les règles ASPIC basées sur la logique prop.
        PlFormulaGenerator = jpype.JClass(
            "org.tweetyproject.arg.aspic.ruleformulagenerator.PlFormulaGenerator"
        )
        pl_formula_generator_instance = PlFormulaGenerator()
        logger.info(
            "Classe 'org.tweetyproject.arg.aspic.ruleformulagenerator.PlFormulaGenerator' chargée et instanciée."
        )

        # 3. Charger et instancier le parser ASPIC principal avec ses dépendances
        AspicParser = jpype.JClass("org.tweetyproject.arg.aspic.parser.AspicParser")
        aspic_parser_instance = AspicParser(
            pl_parser_instance, pl_formula_generator_instance
        )
        logger.info(
            "Classe 'org.tweetyproject.arg.aspic.parser.AspicParser' chargée et instanciée."
        )

        # 4. Stocker l'instance du parser dans le contexte de l'application
        context.tweety_classes["AspicParser"] = aspic_parser_instance
        logger.info(
            "Instance de AspicParser stockée dans context.tweety_classes['AspicParser']."
        )

        # L'ancien 'ArgumentParser' est maintenant remplacé par le 'AspicParser' configuré.

    except ImportError as e:
        logger.critical(
            f"Échec critique de l'import d'une classe Tweety après le démarrage de la JVM: {e}",
            exc_info=True,
        )
    except Exception as e:
        logger.critical(
            f"Erreur inattendue lors du chargement des classes Tweety: {e}",
            exc_info=True,
        )


def _pre_init_safety_checks(project_root: Path, env_path: Path) -> bool:
    """
    Pre-initialization safety checks to detect common issues before JVM startup.

    Performs critical validation to prevent silent failures and hangs during
    initialization. Returns True if all checks pass, False otherwise.

    Args:
        project_root: Path to the project root directory
        env_path: Path to the .env configuration file

    Returns:
        True if all safety checks pass, False if any critical check fails
    """
    checks_passed = True
    warnings = []

    # Check 1: Python version compatibility
    python_version = sys.version_info
    if python_version < (3, 10):
        logger.critical(
            f"Python version {python_version[0]}.{python_version[1]} is not supported. "
            f"Required: Python 3.10+"
        )
        return False
    elif python_version >= (3, 13):
        warnings.append(
            f"Python {python_version[0]}.{python_version[1]} is not yet fully tested. "
            f"Recommended: Python 3.10-3.12"
        )

    # Check 2: jpype availability (critical for JVM)
    try:
        import jpype
        logger.debug(f"jpype version {jpype.__version__} is available")
    except ImportError as e:
        logger.critical(
            f"jpype is not installed but is required for JVM operations: {e}"
        )
        logger.critical("Install with: pip install jpype1")
        return False

    # Check 3: File system accessibility
    if not project_root.exists():
        logger.critical(f"Project root directory does not exist: {project_root}")
        return False

    if not project_root.is_dir():
        logger.critical(f"Project root path is not a directory: {project_root}")
        return False

    # Check 4: Configuration file accessibility
    if env_path and env_path.exists():
        if not env_path.is_file():
            logger.warning(f"Environment path exists but is not a file: {env_path}")
            checks_passed = False
    else:
        warnings.append(f"Environment file not found (may be optional): {env_path}")

    # Check 5: Available memory (basic check)
    psutil_available = False
    try:
        import psutil
        psutil_available = True
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        if available_memory_gb < 0.5:  # Less than 512MB
            logger.warning(
                f"Low available memory: {available_memory_gb:.2f}GB. "
                f"JVM initialization may fail or be slow."
            )
    except ImportError:
        logger.debug("psutil not available, skipping memory check")

    # Check 6: Disk space (basic check)
    if psutil_available:
        try:
            disk_usage = psutil.disk_usage(str(project_root))
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 0.1:  # Less than 100MB
                logger.warning(
                    f"Low disk space: {free_gb:.2f}GB free at {project_root}"
                )
        except OSError as e:
            logger.debug(f"Could not check disk space: {e}")

    # Check 7: Known problematic environments
    # Detect if running in certain IDEs with known issues
    if any(name in sys.executable.lower() for name in ["pycharm", "idea"]):
        warnings.append(
            "Running from PyCharm/IntelliJ IDE. Ensure 'Emulate terminal in output console' is enabled."
        )

    # Log warnings and return result
    for warning in warnings:
        logger.warning(f"[PRE-INIT CHECK] {warning}")

    if checks_passed:
        logger.info("[PRE-INIT CHECK] All critical safety checks passed")
    else:
        logger.error("[PRE-INIT CHECK] Some safety checks failed")

    return checks_passed


def initialize_project_environment(
    env_path_str: str = None,
    root_path_str: str = None,
    force_mock_llm: bool = False,
    force_real_llm_in_test: bool = False,
) -> ProjectContext:
    global project_root

    context = ProjectContext()

    if root_path_str:
        current_project_root = Path(root_path_str)
    elif project_root:
        current_project_root = project_root
    else:
        current_project_root = Path(os.getcwd()).resolve()
        logger.warning(
            f"Project root not determined via __file__ or argument, using CWD: {current_project_root}"
        )
        if str(current_project_root) not in sys.path:
            sys.path.insert(0, str(current_project_root))
            logger.info(
                f"Added CWD-based project root to sys.path: {current_project_root}"
            )
            # Re-tenter les imports
            global initialize_jvm_func, CryptoService_class, DefinitionService_class, create_llm_service_func, InformalAgent_class, ContextualFallacyDetector_class, sk_module, ENCRYPTION_KEY_imported, ExtractDefinitions_class, SourceDefinition_class, Extract_class
            if not initialize_jvm_func:
                try:
                    from argumentation_analysis.core.jvm_setup import (
                        initialize_jvm as initialize_jvm_func,
                    )

                    logger.info("Late import: initialize_jvm_func")
                except ImportError:
                    pass
            if not CryptoService_class:
                try:
                    from argumentation_analysis.services.crypto_service import (
                        CryptoService as CryptoService_class,
                    )

                    logger.info("Late import: CryptoService_class")
                except ImportError:
                    pass
            if not ContextualFallacyDetector_class:
                try:
                    from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
                        ContextualFallacyDetector as ContextualFallacyDetector_class,
                    )

                    logger.info("Late import: ContextualFallacyDetector_class")
                except ImportError:
                    pass
            # L'import tardif de InformalAgent a été supprimé.

    context.project_root_path = current_project_root
    logger.info(
        f"--- Initialisation de l'environnement du projet (Racine: {current_project_root}) ---"
    )

    if env_path_str:
        actual_env_path = Path(env_path_str)
    else:
        # Ajustement du chemin .env pour être relatif à la racine du projet
        actual_env_path = current_project_root / ".env"
        # Ou si vous voulez le garder dans argumentation_analysis:
        # actual_env_path = current_project_root / "argumentation_analysis" / ".env"

    # Pre-initialization safety checks (#253)
    # Run critical validation before JVM startup to prevent silent failures
    if not _pre_init_safety_checks(current_project_root, actual_env_path):
        logger.critical(
            "Pre-initialization safety checks failed. Aborting initialization."
        )
        raise RuntimeError(
            "Bootstrap failed: Pre-initialization safety checks did not pass. "
            "Check logs for details."
        )

    # La configuration est maintenant chargée via le module `settings` à l'import.
    # On peuple `context.config` pour la compatibilité avec le reste du code.
    if settings:
        context.settings = settings
        logger.info(
            "Chargement de la configuration depuis l'objet `settings` centralisé."
        )
        context.config["OPENAI_API_KEY"] = (
            settings.openai.api_key.get_secret_value()
            if settings.openai.api_key
            else None
        )

        # Récupération sécurisée des secrets depuis l'objet settings.
        # Le dictionnaire context.config est conservé pour la compatibilité ascendante du reste du script.
        context.config["TEXT_CONFIG_PASSPHRASE"] = (
            settings.passphrase.get_secret_value() if settings.passphrase else None
        )
        context.config["ENCRYPTION_KEY_FROM_ENV"] = (
            settings.encryption_key.get_secret_value()
            if settings.encryption_key
            else None
        )

        if not context.config.get("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY non configurée dans `settings`.")
        if not context.config.get("TEXT_CONFIG_PASSPHRASE"):
            logger.warning("TEXT_CONFIG_PASSPHRASE non configurée dans `settings`.")
    else:
        logger.error(
            "Le module `settings` n'a pas pu être importé. La configuration est indisponible."
        )

    # Utiliser un attribut sur le module `sys` pour un état vraiment global
    # qui survit au rechargement de module par Uvicorn.
    if hasattr(sys, "_jvm_initialized") and sys._jvm_initialized:
        logger.info(
            "JVM déjà initialisée dans ce processus (détecté via sys._jvm_initialized). On saute la ré-initialisation."
        )
        context.jvm_initialized = True
    else:
        with _JVM_INIT_LOCK:
            # Re-vérifier à l'intérieur du verrou (double-checked locking)
            if hasattr(sys, "_jvm_initialized") and sys._jvm_initialized:
                logger.info(
                    "JVM initialisée par un autre thread pendant l'attente du verrou."
                )
                context.jvm_initialized = True
            else:
                if initialize_jvm_func:
                    logger.info(
                        "APPEL IMMINENT : Initialisation de la JVM via jvm_setup.initialize_jvm()..."
                    )  # LOG AJOUTÉ
                    logger.info(
                        "Initialisation de la JVM via jvm_setup.initialize_jvm()..."
                    )
                    try:
                        if (
                            initialize_jvm_func()
                        ):  # Appelle initialize_jvm qui retourne un booléen
                            context.jvm_initialized = True
                            sys._jvm_initialized = (
                                True  # Marquer globalement pour ce processus
                            )
                            logger.info(
                                "JVM initialisée avec succès (confirmé par le retour de initialize_jvm)."
                            )
                        else:
                            context.jvm_initialized = False
                            sys._jvm_initialized = False  # Assurer la cohérence
                            logger.error(
                                "Échec de l'initialisation de la JVM (initialize_jvm a retourné False)."
                            )
                    except (
                        Exception
                    ) as e:  # Capturer les exceptions potentielles de initialize_jvm
                        logger.error(
                            f"Erreur lors de l'appel à initialize_jvm_func : {e}",
                            exc_info=True,
                        )
                        context.jvm_initialized = False
                        sys._jvm_initialized = (
                            False  # Assurer que c'est False en cas d'erreur
                        )
                else:
                    logger.error(
                        "La fonction initialize_jvm n'a pas pu être importée. Impossible d'initialiser la JVM."
                    )
                    context.jvm_initialized = False
                    sys._jvm_initialized = False

    # --- Chargement des classes Java si la JVM a été initialisée ---
    if context.jvm_initialized:
        _load_tweety_classes(context)

    if CryptoService_class:
        logger.info("Initialisation de CryptoService...")
        # La logique de recherche de clé est simplifiée pour utiliser directement l'objet `settings`.
        key_from_settings = (
            settings.encryption_key.get_secret_value()
            if settings.encryption_key
            else None
        )
        passphrase_from_settings = (
            settings.passphrase.get_secret_value() if settings.passphrase else None
        )

        try:
            if key_from_settings:
                context.crypto_service = CryptoService_class(
                    encryption_key=key_from_settings
                )
                logger.info(
                    "CryptoService initialisé avec la clé de `settings.encryption_key`."
                )
            elif passphrase_from_settings:
                temp_crypto_for_derivation = CryptoService_class()
                derived_key = temp_crypto_for_derivation.derive_key_from_passphrase(
                    passphrase_from_settings
                )
                if derived_key:
                    context.crypto_service = CryptoService_class(
                        encryption_key=derived_key
                    )
                    logger.info(
                        "CryptoService initialisé avec une clé dérivée de `settings.passphrase`."
                    )
                else:
                    logger.error(
                        "Échec de la dérivation de la clé à partir de la passphrase. CryptoService initialisé sans clé."
                    )
                    context.crypto_service = CryptoService_class()
            else:
                context.crypto_service = CryptoService_class()
                logger.warning(
                    "CryptoService initialisé sans clé ou passphrase explicite depuis `settings`."
                )
        except Exception as e:
            logger.error(
                f"Erreur lors de l'initialisation de CryptoService : {e}", exc_info=True
            )
    else:
        logger.error("CryptoService_class n'a pas pu être importé.")

    if DefinitionService_class and context.crypto_service:
        logger.info("Initialisation de DefinitionService...")
        # Ajustement du chemin pour data/extract_sources.json.gz.enc
        definitions_config_path = (
            current_project_root
            / "argumentation_analysis"
            / "data"
            / "extract_sources.json.gz.enc"
        )
        if definitions_config_path.exists():
            try:
                context.definition_service = DefinitionService_class(
                    crypto_service=context.crypto_service,
                    config_file=str(definitions_config_path),
                )
                logger.info(
                    f"DefinitionService initialisé avec : {definitions_config_path}"
                )
            except Exception as e:
                logger.error(
                    f"Erreur lors de l'initialisation de DefinitionService : {e}",
                    exc_info=True,
                )
        else:
            logger.error(
                f"Fichier de configuration pour DefinitionService non trouvé : {definitions_config_path}"
            )
    elif not context.crypto_service:
        logger.error(
            "CryptoService non initialisé. Impossible d'initialiser DefinitionService."
        )
    else:
        logger.error("DefinitionService_class n'a pas pu être importé.")

    # L'initialisation de ContextualFallacyDetector est maintenant paresseuse
    # et gérée via la méthode context.get_fallacy_detector().
    # Le bloc d'initialisation rapide ici est donc supprimé.

    if sk_module and create_llm_service_func:
        logger.info("Initialisation du Kernel Semantic Kernel...")
        try:
            context.kernel = sk_module.Kernel()
            # Le service LLM est un prérequis pour de nombreux plugins, donc on l'ajoute au kernel.
            # Le paramètre force_mock_llm détermine si on doit forcer l'usage du service mocké.
            # Récupérer le model_id depuis les settings, avec un fallback
            model_id_to_use = (
                "default_model"  # Fallback au cas où settings ne serait pas dispo
            )
            if settings and settings.openai and settings.openai.chat_model_id:
                model_id_to_use = settings.openai.chat_model_id
            else:
                logger.warning(
                    "Impossible de trouver `settings.openai.chat_model_id`, utilisation de 'default_model' comme fallback."
                )

            context.llm_service = create_llm_service_func(
                service_id="default_llm_bootstrap",
                model_id=model_id_to_use,
                force_mock=force_mock_llm,
                force_authentic=force_real_llm_in_test,
            )
            context.kernel.add_service(
                context.llm_service
            )  # Assurez-vous que c'est la bonne méthode
            logger.info(
                "Semantic Kernel et LLMService initialisés et ajoutés au contexte."
            )
        except Exception as e:
            logger.error(
                f"Erreur lors de l'initialisation du Semantic Kernel ou du LLM Service : {e}",
                exc_info=True,
            )
    else:
        logger.warning(
            "Semantic-kernel non importé ou create_llm_service non disponible, le kernel ne sera pas initialisé."
        )

    # Regrouper les services dans un dictionnaire pour faciliter leur passage
    context.services = {
        "kernel": context.kernel,
        "crypto_service": context.crypto_service,
        "definition_service": context.definition_service,
        "llm_service": context.llm_service,
        "fallacy_detector": context.get_fallacy_detector(),
    }

    logger.info("--- Fin de l'initialisation de l'environnement du projet ---")
    return context


if __name__ == "__main__":
    print("Test direct du module de bootstrap:")

    main_project_root = (
        Path(__file__).resolve().parent.parent.parent
    )  # Ajusté pour argumentation_analysis/core/bootstrap.py
    if str(main_project_root) not in sys.path:
        sys.path.insert(0, str(main_project_root))
        print(f"Ajout de {main_project_root} à sys.path pour le test direct.")

    test_env_file_path = (
        main_project_root / ".env.example"
    )  # Ajusté pour .env à la racine
    if not test_env_file_path.exists():
        test_env_file_path = main_project_root / ".env"

    if not test_env_file_path.exists():
        logger.warning(
            f"Fichier .env de test non trouvé ({main_project_root / '.env[.example]'}), les tests pourraient être limités."
        )
        test_env_file_path = None
    else:
        logger.info(f"Utilisation du fichier .env de test: {test_env_file_path}")

    initialized_context = initialize_project_environment(
        env_path_str=str(test_env_file_path) if test_env_file_path else None,
        root_path_str=str(main_project_root),
    )

    print("\n--- Résumé du contexte initialisé ---")
    print(f"Project Root: {initialized_context.project_root_path}")
    print(f"JVM Initialisée: {initialized_context.jvm_initialized}")
    print(
        f"CryptoService: {'Oui' if initialized_context.crypto_service else 'Non'} (Type: {type(initialized_context.crypto_service).__name__ if initialized_context.crypto_service else 'N/A'})"
    )
    print(
        f"DefinitionService: {'Oui' if initialized_context.definition_service else 'Non'} (Type: {type(initialized_context.definition_service).__name__ if initialized_context.definition_service else 'N/A'})"
    )
    print(
        f"LLMService: {'Oui' if initialized_context.llm_service else 'Non'} (Type: {type(initialized_context.llm_service).__name__ if initialized_context.llm_service else 'N/A'})"
    )
    print(
        f"Kernel: {'Oui' if initialized_context.kernel else 'Non'} (Type: {type(initialized_context.kernel).__name__ if initialized_context.kernel else 'N/A'})"
    )
    print(f"Configuration chargée (.env):")
    for key, value in initialized_context.config.items():
        display_value = value
        if (
            isinstance(value, str)
            and ("KEY" in key.upper() or "PASSPHRASE" in key.upper())
            and len(value) > 4
        ):
            display_value = "****" + value[-4:]
        print(
            f"  {key}: {display_value if display_value is not None else 'Non défini'}"
        )

    if initialized_context.jvm_initialized:
        try:
            import jpype

            if jpype.isJVMStarted():
                ArrayList = jpype.JClass("java.util.ArrayList")
                my_list_test = ArrayList()
                my_list_test.add("Test JPype depuis bootstrap")
                print(f"Test JPype (ArrayList): {my_list_test.get(0)}")
            else:
                print(
                    "Test JPype post-init: JVM non démarrée selon jpype.isJVMStarted() après initialisation."
                )
        except Exception as e:
            print(f"Erreur lors du test JPype post-initialisation: {e}")
