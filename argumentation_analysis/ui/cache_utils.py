"""
Utilitaires de gestion du cache pour l'interface utilisateur.
"""
import hashlib
import logging
from pathlib import Path
from typing import Optional

# Importation de la configuration UI pour CACHE_DIR
from . import config as ui_config

# Chaque module peut avoir son propre logger pour une meilleure granularité
cache_logger = logging.getLogger("App.UI.CacheUtils")
if not cache_logger.handlers and not cache_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    cache_logger.addHandler(handler)
    cache_logger.setLevel(logging.INFO) # Ou INFO selon le besoin

def get_cache_filepath(url: str) -> Path:
    """Génère le chemin du fichier cache pour une URL donnée.

    Le nom du fichier est un hachage SHA256 de l'URL, stocké dans `ui_config.CACHE_DIR`.

    :param url: L'URL pour laquelle générer le chemin du fichier cache.
    :type url: str
    :return: Le chemin (objet Path) vers le fichier cache.
    :rtype: Path
    """
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    return ui_config.CACHE_DIR / f"{url_hash}.txt"

def load_from_cache(url: str) -> Optional[str]:
    """Charge le contenu textuel depuis le cache fichier si disponible pour une URL donnée.

    :param url: L'URL à rechercher dans le cache.
    :type url: str
    :return: Le contenu textuel en tant que chaîne si trouvé, sinon None.
    :rtype: Optional[str]
    """
    filepath = get_cache_filepath(url)
    if filepath.exists():
        try:
            cache_logger.info(f"   -> Lecture depuis cache : {filepath.name}")
            return filepath.read_text(encoding='utf-8')
        except Exception as e:
            cache_logger.warning(f"   -> Erreur lecture cache {filepath.name}: {e}")
            return None
    cache_logger.debug(f"Cache miss pour URL: {url}")
    return None

def save_to_cache(url: str, text: str) -> None:
    """Sauvegarde le contenu textuel dans le cache fichier pour une URL donnée.

    Ne fait rien si le texte est vide. Crée le répertoire de cache si nécessaire.

    :param url: L'URL associée au contenu.
    :type url: str
    :param text: Le contenu textuel à sauvegarder.
    :type text: str
    :return: None
    :rtype: None
    """
    if not text:
        cache_logger.info("   -> Texte vide, non sauvegardé.")
        return
    filepath = get_cache_filepath(url)
    try:
        # S'assurer que le dossier cache existe
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(text, encoding='utf-8')
        cache_logger.info(f"   -> Texte sauvegardé : {filepath.name}")
    except Exception as e:
        cache_logger.error(f"   -> Erreur sauvegarde cache {filepath.name}: {e}")

cache_logger.info("Utilitaires de cache UI définis.")