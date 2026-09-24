"""
Utilitaires de gestion du cache pour l'interface utilisateur.

#2344: this module and ``ui/utils.py`` each carried their own copy of the text
cache, on the same directory and file names as
``services.cache_service.CacheService``. The copies wrote in place, so a failed
write left an empty file that they then served as the cached document. They
now delegate to the service: one cache, one set of guards.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from ..services.cache_service import CacheService

# Importation de la configuration UI pour CACHE_DIR
from . import config as ui_config

# Chaque module peut avoir son propre logger pour une meilleure granularité
cache_logger = logging.getLogger("App.UI.CacheUtils")
if not cache_logger.handlers and not cache_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    cache_logger.addHandler(handler)
    cache_logger.setLevel(logging.INFO)  # Ou INFO selon le besoin

_cache_services: Dict[Path, CacheService] = {}


def cache_service() -> CacheService:
    """The CacheService on ``ui_config.CACHE_DIR``, read at call time.

    One instance per directory, so the UI's many cache calls do not rebuild it.
    """
    cache_dir = ui_config.CACHE_DIR
    service = _cache_services.get(cache_dir)
    if service is None:
        service = _cache_services[cache_dir] = CacheService(cache_dir)
    return service


def get_cache_filepath(url: str) -> Path:
    """Génère le chemin du fichier cache pour une URL donnée.

    Le nom du fichier est un hachage SHA256 de l'URL, stocké dans `ui_config.CACHE_DIR`.

    :param url: L'URL pour laquelle générer le chemin du fichier cache.
    :type url: str
    :return: Le chemin (objet Path) vers le fichier cache.
    :rtype: Path
    """
    return cache_service().get_cache_filepath(url)


def load_from_cache(url: str) -> Optional[str]:
    """Charge le contenu textuel depuis le cache fichier si disponible pour une URL donnée.

    :param url: L'URL à rechercher dans le cache.
    :type url: str
    :return: Le contenu textuel en tant que chaîne si trouvé, sinon None.
        Un fichier vide est une écriture interrompue : il se lit comme un défaut
        de cache.
    :rtype: Optional[str]
    """
    return cache_service().load_from_cache(url)


def save_to_cache(url: str, text: str) -> bool:
    """Sauvegarde le contenu textuel dans le cache fichier pour une URL donnée.

    Ne fait rien si le texte est vide. L'écriture est atomique : un échec ne
    laisse aucune entrée.

    :param url: L'URL associée au contenu.
    :type url: str
    :param text: Le contenu textuel à sauvegarder.
    :type text: str
    :return: True si le texte a été sauvegardé, False sinon.
    :rtype: bool
    """
    return cache_service().save_to_cache(url, text)


cache_logger.info("Utilitaires de cache UI définis.")
