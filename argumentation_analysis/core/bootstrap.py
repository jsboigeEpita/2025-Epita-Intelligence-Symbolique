# argumentation_analysis/core/bootstrap.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Dict, List, Any # Ajout pour List et Dict dans l'adaptateur

# Configuration du logger pour ce module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Ou logging.DEBUG pour plus de détails

# Ajout de la racine du projet au sys.path pour les imports
project_root = None
try:
    current_script_path = Path(__file__).resolve()
    # argumentation_analysis/core/bootstrap.py -> argumentation_analysis/core -> argumentation_analysis -> project_root
    project_root = current_script_path.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    logger.info(f"Project root (from bootstrap.py) added to sys.path: {project_root}")
except NameError: # __file__ n'est pas défini si exécuté interactivement ou via exec() sans contexte de fichier
    logger.warning("__file__ not defined, sys.path might not be configured correctly by bootstrap.py itself.")
    pass


# Imports des services et modules nécessaires (seront dans des try-except)
initialize_jvm_func = None
CryptoService_class = None
DefinitionService_class = None
create_llm_service_func = None
InformalAgent_class = None # Changé de InformalAnalysisAgent à InformalAgent
ContextualFallacyDetector_class = None
sk_module = None
ENCRYPTION_KEY_imported = None
ExtractDefinitions_class, SourceDefinition_class, Extract_class = None, None, None

try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm as initialize_jvm_func
except ImportError as e:
    logger.error(f"Failed to import initialize_jvm: {e}")

try:
    from argumentation_analysis.services.crypto_service import CryptoService as CryptoService_class
except ImportError as e:
    logger.error(f"Failed to import CryptoService: {e}")

try:
    from argumentation_analysis.services.definition_service import DefinitionService as DefinitionService_class
except ImportError as e:
    logger.error(f"Failed to import DefinitionService: {e}")

try:
    from argumentation_analysis.core.llm_service import create_llm_service as create_llm_service_func
except ImportError as e:
    logger.error(f"Failed to import create_llm_service: {e}")

try:
    # Changement ici pour refléter le renommage/déplacement potentiel de l'agent
    from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent as InformalAgent_class
except ImportError as e:
    logger.error(f"Failed to import InformalAgent (anciennement InformalAnalysisAgent): {e}")

try:
    import semantic_kernel as sk_module
except ImportError as e:
    logger.error(f"Failed to import semantic_kernel: {e}")

try:
    from argumentation_analysis.ui.config import ENCRYPTION_KEY as ENCRYPTION_KEY_imported
except ImportError:
    logger.warning("ENCRYPTION_KEY not found in argumentation_analysis.ui.config. CryptoService might rely on .env or fail.")

try:
    from argumentation_analysis.models.extract_definition import ExtractDefinitions as ExtractDefinitions_class, SourceDefinition as SourceDefinition_class, Extract as Extract_class
except ImportError as e:
    logger.error(f"Failed to import extract models (ExtractDefinitions, etc.): {e}")

try:
    from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector as ContextualFallacyDetector_class
except ImportError as e:
    logger.error(f"Failed to import ContextualFallacyDetector: {e}")

# Adapter pour ContextualFallacyDetector
class ContextualFallacyDetectorAdapter:
    def __init__(self, actual_detector):
        self.actual_detector = actual_detector
        self.logger = logging.getLogger("ContextualFallacyDetectorAdapter")

    def detect(self, text: str, context_description: str = "général") -> List[Dict[str, Any]]:
        self.logger.info(f"Adapter: Appel de detect_contextual_fallacies pour le texte: {text[:50]}...")
        try:
            results = self.actual_detector.detect_contextual_fallacies(
                argument=text,
                context_description=context_description
            )
            detected_fallacies = results.get("detected_fallacies", [])
            if not isinstance(detected_fallacies, list):
                self.logger.warning(f"Adapter: 'detected_fallacies' n'est pas une liste, mais {type(detected_fallacies)}. Retourne [].")
                return []
            return detected_fallacies
        except Exception as e:
            self.logger.error(f"Adapter: Erreur lors de l'appel à detect_contextual_fallacies: {e}", exc_info=True)
            return []

class ProjectContext:
    def __init__(self):
        self.jvm_initialized = False
        self.crypto_service = None
        self.definition_service = None
        self.llm_service = None
        self.informal_agent = None
        self.fallacy_detector = None
        self.tweety_classes = {}
        self.config = {}
        self.project_root_path = None


def initialize_project_environment(env_path_str: str = None, root_path_str: str = None) -> ProjectContext:
    global project_root

    context = ProjectContext()
    
    if root_path_str:
        current_project_root = Path(root_path_str)
    elif project_root:
        current_project_root = project_root
    else:
        current_project_root = Path(os.getcwd()).resolve()
        logger.warning(f"Project root not determined via __file__ or argument, using CWD: {current_project_root}")
        if str(current_project_root) not in sys.path:
            sys.path.insert(0, str(current_project_root))
            logger.info(f"Added CWD-based project root to sys.path: {current_project_root}")
            # Re-tenter les imports
            global initialize_jvm_func, CryptoService_class, DefinitionService_class, create_llm_service_func, InformalAgent_class, ContextualFallacyDetector_class, sk_module, ENCRYPTION_KEY_imported, ExtractDefinitions_class, SourceDefinition_class, Extract_class
            if not initialize_jvm_func:
                try:
                    from argumentation_analysis.core.jvm_setup import initialize_jvm as initialize_jvm_func
                    logger.info("Late import: initialize_jvm_func")
                except ImportError: pass
            if not CryptoService_class:
                try:
                    from argumentation_analysis.services.crypto_service import CryptoService as CryptoService_class
                    logger.info("Late import: CryptoService_class")
                except ImportError: pass
            if not ContextualFallacyDetector_class:
                try:
                    from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector as ContextualFallacyDetector_class
                    logger.info("Late import: ContextualFallacyDetector_class")
                except ImportError: pass
            if not InformalAgent_class: # Ajout pour InformalAgent
                try:
                    from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent as InformalAgent_class
                    logger.info("Late import: InformalAgent_class")
                except ImportError: pass


    context.project_root_path = current_project_root
    logger.info(f"--- Initialisation de l'environnement du projet (Racine: {current_project_root}) ---")

    if env_path_str:
        actual_env_path = Path(env_path_str)
    else:
        # Ajustement du chemin .env pour être relatif à la racine du projet
        actual_env_path = current_project_root / ".env"
        # Ou si vous voulez le garder dans argumentation_analysis:
        # actual_env_path = current_project_root / "argumentation_analysis" / ".env"

    if actual_env_path.exists():
        load_dotenv(dotenv_path=actual_env_path, override=True)
        logger.info(f"Variables d'environnement chargées depuis : {actual_env_path}")
        context.config['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY")
        context.config['TEXT_CONFIG_PASSPHRASE'] = os.getenv("TEXT_CONFIG_PASSPHRASE")
        context.config['ENCRYPTION_KEY_FROM_ENV'] = os.getenv("ENCRYPTION_KEY")

        if not context.config['OPENAI_API_KEY']:
            logger.warning("OPENAI_API_KEY non trouvée dans le .env ou l'environnement.")
        if not context.config['TEXT_CONFIG_PASSPHRASE']:
            logger.warning("TEXT_CONFIG_PASSPHRASE non trouvée dans le .env ou l'environnement.")
    else:
        logger.warning(f"Fichier .env non trouvé à {actual_env_path}. Les services dépendant de variables d'environnement pourraient ne pas fonctionner.")

    if initialize_jvm_func:
        logger.info("Initialisation de la JVM via jvm_setup.initialize_jvm()...")
        try:
            context.jvm_initialized = initialize_jvm_func()
            if context.jvm_initialized:
                logger.info("JVM initialisée avec succès.")
            else:
                logger.error("Échec de l'initialisation de la JVM.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la JVM : {e}", exc_info=True)
            context.jvm_initialized = False
    else:
        logger.error("La fonction initialize_jvm n'a pas pu être importée. Impossible d'initialiser la JVM.")
        context.jvm_initialized = False

    if CryptoService_class:
        logger.info("Initialisation de CryptoService...")
        key_to_use = ENCRYPTION_KEY_imported
        passphrase_to_use = None

        if not key_to_use and context.config.get('ENCRYPTION_KEY_FROM_ENV'):
            key_to_use = context.config['ENCRYPTION_KEY_FROM_ENV']
            logger.info("Utilisation de ENCRYPTION_KEY depuis le fichier .env pour CryptoService.")
        elif not key_to_use:
             passphrase_to_use = context.config.get('TEXT_CONFIG_PASSPHRASE')
             if passphrase_to_use:
                 logger.info("ENCRYPTION_KEY non trouvée, utilisation de TEXT_CONFIG_PASSPHRASE pour CryptoService.")
             else:
                 logger.warning("Ni ENCRYPTION_KEY (ui.config ou .env) ni TEXT_CONFIG_PASSPHRASE (.env) trouvées pour CryptoService.")
        
        try:
            if key_to_use:
                context.crypto_service = CryptoService_class(encryption_key=key_to_use)
                logger.info("CryptoService initialisé avec encryption_key.")
            elif passphrase_to_use:
                 context.crypto_service = CryptoService_class(passphrase=passphrase_to_use)
                 logger.info("CryptoService initialisé avec passphrase.")
            else:
                context.crypto_service = CryptoService_class()
                logger.warning("CryptoService initialisé sans clé/passphrase explicite.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de CryptoService : {e}", exc_info=True)
    else:
        logger.error("CryptoService_class n'a pas pu être importé.")

    if DefinitionService_class and context.crypto_service:
        logger.info("Initialisation de DefinitionService...")
        # Ajustement du chemin pour data/extract_sources.json.gz.enc
        definitions_config_path = current_project_root / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
        if definitions_config_path.exists():
            try:
                context.definition_service = DefinitionService_class(
                    crypto_service=context.crypto_service,
                    config_file=str(definitions_config_path)
                )
                logger.info(f"DefinitionService initialisé avec : {definitions_config_path}")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation de DefinitionService : {e}", exc_info=True)
        else:
            logger.error(f"Fichier de configuration pour DefinitionService non trouvé : {definitions_config_path}")
    elif not context.crypto_service:
        logger.error("CryptoService non initialisé. Impossible d'initialiser DefinitionService.")
    else:
        logger.error("DefinitionService_class n'a pas pu être importé.")

    if create_llm_service_func:
        logger.info("Initialisation de LLMService via create_llm_service...")
        if context.config.get('OPENAI_API_KEY'):
            try:
                context.llm_service = create_llm_service_func(service_id="default_llm_bootstrap")
                logger.info("LLMService initialisé via create_llm_service.")
            except Exception as e:
                logger.error(f"Erreur lors de l'appel à create_llm_service : {e}", exc_info=True)
        else:
            logger.warning("OPENAI_API_KEY non disponible. Tentative d'initialisation de LLMService sans clé (pourrait retourner un mock ou échouer).")
            try:
                context.llm_service = create_llm_service_func(service_id="default_llm_bootstrap_no_key")
                if context.llm_service:
                     logger.info(f"create_llm_service (sans clé API) a retourné: {type(context.llm_service).__name__}")
            except Exception as e:
                logger.error(f"Erreur lors de l'appel à create_llm_service (sans clé API) : {e}", exc_info=True)
    else:
        logger.error("create_llm_service_func n'a pas pu être importé.")

    if ContextualFallacyDetector_class:
        logger.info("Initialisation de ContextualFallacyDetector...")
        try:
            original_detector = ContextualFallacyDetector_class()
            context.fallacy_detector = ContextualFallacyDetectorAdapter(original_detector)
            logger.info("ContextualFallacyDetector initialisé et enveloppé dans l'adaptateur.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de ContextualFallacyDetector ou de son adaptateur : {e}", exc_info=True)
    else:
        logger.error("ContextualFallacyDetector_class n'a pas pu être importé.")

    if InformalAgent_class and context.llm_service and sk_module and context.fallacy_detector:
        logger.info("Initialisation de InformalAgent...")
        try:
            kernel = sk_module.Kernel()
            kernel.add_service(context.llm_service)
            
            informal_agent_tools = {
                "fallacy_detector": context.fallacy_detector
            }
            
            context.informal_agent = InformalAgent_class(
                agent_id="bootstrap_informal_agent",
                tools=informal_agent_tools,
                semantic_kernel=kernel
            )
            logger.info("InformalAgent initialisé.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de InformalAgent : {e}", exc_info=True)
    elif not context.llm_service:
         logger.error("LLMService non initialisé. Impossible d'initialiser InformalAgent.")
    elif not sk_module:
        logger.error("Semantic Kernel (sk_module) non importé.")
    elif not context.fallacy_detector:
        logger.error("FallacyDetector non initialisé. Impossible d'initialiser InformalAgent.")
    else:
        logger.error("InformalAgent_class n'a pas pu être importé.")

    logger.info("--- Fin de l'initialisation de l'environnement du projet ---")
    return context

if __name__ == '__main__':
    print("Test direct du module de bootstrap:")
    
    main_project_root = Path(__file__).resolve().parent.parent.parent # Ajusté pour argumentation_analysis/core/bootstrap.py
    if str(main_project_root) not in sys.path:
       sys.path.insert(0, str(main_project_root))
       print(f"Ajout de {main_project_root} à sys.path pour le test direct.")

    test_env_file_path = main_project_root / ".env.example" # Ajusté pour .env à la racine
    if not test_env_file_path.exists():
        test_env_file_path = main_project_root / ".env"
    
    if not test_env_file_path.exists():
        logger.warning(f"Fichier .env de test non trouvé ({main_project_root / '.env[.example]'}), les tests pourraient être limités.")
        test_env_file_path = None
    else:
        logger.info(f"Utilisation du fichier .env de test: {test_env_file_path}")


    initialized_context = initialize_project_environment(
        env_path_str=str(test_env_file_path) if test_env_file_path else None,
        root_path_str=str(main_project_root)
        )
    
    print("\n--- Résumé du contexte initialisé ---")
    print(f"Project Root: {initialized_context.project_root_path}")
    print(f"JVM Initialisée: {initialized_context.jvm_initialized}")
    print(f"CryptoService: {'Oui' if initialized_context.crypto_service else 'Non'} (Type: {type(initialized_context.crypto_service).__name__ if initialized_context.crypto_service else 'N/A'})")
    print(f"DefinitionService: {'Oui' if initialized_context.definition_service else 'Non'} (Type: {type(initialized_context.definition_service).__name__ if initialized_context.definition_service else 'N/A'})")
    print(f"LLMService: {'Oui' if initialized_context.llm_service else 'Non'} (Type: {type(initialized_context.llm_service).__name__ if initialized_context.llm_service else 'N/A'})")
    print(f"InformalAgent: {'Oui' if initialized_context.informal_agent else 'Non'} (Type: {type(initialized_context.informal_agent).__name__ if initialized_context.informal_agent else 'N/A'})")
    print(f"Configuration chargée (.env):")
    for key, value in initialized_context.config.items():
        display_value = value
        if isinstance(value, str) and ("KEY" in key.upper() or "PASSPHRASE" in key.upper()) and len(value) > 4:
            display_value = "****" + value[-4:]
        print(f"  {key}: {display_value if display_value is not None else 'Non défini'}")

    if initialized_context.jvm_initialized:
        try:
            import jpype
            if jpype.isJVMStarted():
                ArrayList = jpype.JClass("java.util.ArrayList")
                my_list_test = ArrayList()
                my_list_test.add("Test JPype depuis bootstrap")
                print(f"Test JPype (ArrayList): {my_list_test.get(0)}")
            else:
                print("Test JPype post-init: JVM non démarrée selon jpype.isJVMStarted() après initialisation.")
        except Exception as e:
            print(f"Erreur lors du test JPype post-initialisation: {e}")