# -*- coding: utf-8 -*-
"""Initialisation des services centraux du projet."""

from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Ces imports supposent que les services sont accessibles depuis ces chemins.
# Si les services sont aussi déplacés vers project_core, ces imports devront changer.
try:
    from argumentation_analysis.services.cache_service import CacheService
    from argumentation_analysis.services.crypto_service import CryptoService
    from argumentation_analysis.services.definition_service import DefinitionService
    from argumentation_analysis.services.extract_service import ExtractService
    from argumentation_analysis.services.fetch_service import FetchService
    # Les constantes de configuration sont généralement gérées de manière centralisée.
    from argumentation_analysis.ui.config import ENCRYPTION_KEY as DEFAULT_ENCRYPTION_KEY
    from argumentation_analysis.ui.config import CONFIG_FILE as DEFAULT_CONFIG_FILE_PATH
    from argumentation_analysis.ui.config import CONFIG_FILE_JSON as DEFAULT_CONFIG_FILE_JSON_PATH
except ImportError as e:
    logging.getLogger(__name__).error(f"Erreur d'importation des services ou de la configuration: {e}. Assurez-vous que argumentation_analysis est installé et accessible.")
    # Gérer l'erreur d'une manière qui a du sens pour votre application
    # Par exemple, lever l'erreur pour arrêter l'exécution si ces services sont critiques.
    raise

logger = logging.getLogger(__name__)

def initialize_core_services(
    encryption_key: Optional[str] = None,
    config_file_path: Optional[Path] = None,
    config_json_fallback_path: Optional[Path] = None,
    project_root_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Initialise et retourne un dictionnaire des services centraux du projet.

    Args:
        encryption_key (Optional[str]): Clé de chiffrement à utiliser.
                                         Si None, utilise DEFAULT_ENCRYPTION_KEY.
        config_file_path (Optional[Path]): Chemin vers le fichier de configuration principal.
                                            Si None, utilise DEFAULT_CONFIG_FILE_PATH.
        config_json_fallback_path (Optional[Path]): Chemin vers le fichier de configuration JSON de secours.
                                                     Si None, utilise DEFAULT_CONFIG_FILE_JSON_PATH.
        project_root_dir (Optional[Path]): Répertoire racine du projet. Si fourni, les chemins relatifs
                                           pour le cache et les téléchargements seront basés sur ce répertoire.
                                           Si None, les chemins relatifs sont basés sur le CWD.

    Returns:
        Dict[str, Any]: Un dictionnaire contenant les instances des services initialisés.
                        Ex: {"crypto_service": crypto_instance, "cache_service": cache_instance, ...}
    """
    logger.info("Initialisation des services centraux...")

    services: Dict[str, Any] = {}
    
    # Déterminer le répertoire de base pour les chemins relatifs
    base_path = project_root_dir if project_root_dir else Path.cwd()
    logger.debug(f"Répertoire de base pour les services: {base_path.resolve()}")

    # Clé de chiffrement et fichier de configuration
    current_encryption_key = encryption_key if encryption_key is not None else DEFAULT_ENCRYPTION_KEY
    
    # Pour les fichiers de configuration, s'ils ne sont pas absolus, les rendre relatifs à base_path
    current_config_file = Path(DEFAULT_CONFIG_FILE_PATH)
    if config_file_path is not None:
        current_config_file = config_file_path
    if not current_config_file.is_absolute():
        current_config_file = base_path / current_config_file
    
    current_fallback_file = Path(DEFAULT_CONFIG_FILE_JSON_PATH)
    if config_json_fallback_path is not None:
        current_fallback_file = config_json_fallback_path
    if not current_fallback_file.is_absolute():
        current_fallback_file = base_path / current_fallback_file
        
    if not current_fallback_file.exists():
        logger.warning(f"Fichier de fallback JSON {current_fallback_file.resolve()} non trouvé. Il ne sera pas utilisé.")
        current_fallback_file = None

    # Service de chiffrement
    try:
        crypto_service = CryptoService(current_encryption_key)
        services["crypto_service"] = crypto_service
        logger.debug("CryptoService initialisé.")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de CryptoService: {e}")
        raise

    # Service de cache
    try:
        cache_dir = base_path / "argumentation_analysis" / "text_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_service = CacheService(cache_dir=cache_dir)
        services["cache_service"] = cache_service
        logger.debug(f"CacheService initialisé avec cache_dir: {cache_dir.resolve()}")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de CacheService: {e}")
        raise

    # Service d'extraction
    try:
        extract_service = ExtractService()
        services["extract_service"] = extract_service
        logger.debug("ExtractService initialisé.")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de ExtractService: {e}")
        raise

    # Service de récupération (FetchService)
    try:
        temp_download_dir = base_path / "argumentation_analysis" / "temp_downloads"
        temp_download_dir.mkdir(parents=True, exist_ok=True)
        fetch_service = FetchService(
            cache_service=services["cache_service"],
            temp_download_dir=temp_download_dir
        )
        services["fetch_service"] = fetch_service
        logger.debug(f"FetchService initialisé avec temp_download_dir: {temp_download_dir.resolve()}")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de FetchService: {e}")
        raise

    # Service de définition
    try:
        if not current_config_file.exists():
            logger.warning(f"Fichier de configuration principal {current_config_file.resolve()} non trouvé.")
        
        definition_service = DefinitionService(
            crypto_service=services["crypto_service"],
            config_file=current_config_file,
            fallback_file=current_fallback_file
        )
        services["definition_service"] = definition_service
        logger.debug(f"DefinitionService initialisé avec config_file: {current_config_file.resolve()}, fallback: {current_fallback_file.resolve() if current_fallback_file else 'None'}")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de DefinitionService: {e}")
        raise
        
    logger.info("✅ Services centraux initialisés.")
    return services

# Note: create_llm_service n'est pas inclus ici car il n'est pas commun à tous les scripts
# qui pourraient utiliser cette fonction d'initialisation. Il peut être appelé séparément.