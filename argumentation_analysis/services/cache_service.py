"""
Service de cache pour l'analyse d'argumentation.

Ce module fournit un service centralisé pour la gestion du cache de textes,
permettant de stocker et récupérer des contenus textuels à partir d'URLs.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple

# Configuration du logging
logger = logging.getLogger("Services.CacheService")


class CacheService:
    """Service pour la gestion du cache de textes."""

    def __init__(self, cache_dir: Path):
        """
        Initialise le service de cache.

        :param cache_dir: Le chemin (objet Path) vers le répertoire où le cache sera stocké.
        :type cache_dir: Path
        """
        self.cache_dir = cache_dir
        self.logger = logger

        # S'assurer que le répertoire de cache existe
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Répertoire de cache initialisé: {self.cache_dir}")

    def get_cache_filepath(self, url: str) -> Path:
        """
        Génère le chemin du fichier cache pour une URL donnée.

        Le nom du fichier est basé sur un hachage SHA256 de l'URL.

        :param url: L'URL pour laquelle générer le chemin du fichier cache.
        :type url: str
        :return: Le chemin (objet Path) complet vers le fichier cache potentiel.
        :rtype: Path
        """
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.txt"

    def load_from_cache(self, url: str) -> Optional[str]:
        """
        Charge le contenu textuel depuis le cache pour une URL donnée, si disponible.

        :param url: L'URL dont le contenu est à charger depuis le cache.
        :type url: str
        :return: Le contenu textuel en tant que chaîne de caractères si trouvé dans le cache,
                 sinon None.
        :rtype: Optional[str]
        """
        filepath = self.get_cache_filepath(url)
        if filepath.exists():
            try:
                self.logger.info(f"Lecture depuis cache: {filepath.name}")
                return filepath.read_text(encoding="utf-8")
            except Exception as e:
                self.logger.warning(f"Erreur lecture cache {filepath.name}: {e}")
                return None
        self.logger.debug(f"Cache miss pour URL: {url}")
        return None

    def save_to_cache(self, url: str, text: str) -> bool:
        """
        Sauvegarde le contenu textuel dans le cache pour une URL donnée.

        :param url: L'URL associée au contenu textuel.
        :type url: str
        :param text: Le contenu textuel à sauvegarder.
        :type text: str
        :return: True si la sauvegarde a réussi, False sinon.
        :rtype: bool
        """
        if not text:
            self.logger.info("Texte vide, non sauvegardé.")
            return False

        filepath = self.get_cache_filepath(url)
        try:
            # S'assurer que le dossier cache existe
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(text, encoding="utf-8")
            self.logger.info(f"Texte sauvegardé: {filepath.name}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde cache {filepath.name}: {e}")
            return False

    def clear_cache(self, url: Optional[str] = None) -> Tuple[int, int]:
        """
        Efface le cache pour une URL spécifique ou l'intégralité du cache.

        :param url: L'URL spécifique dont le cache doit être effacé.
                    Si None, tout le cache (fichiers .txt) dans le répertoire
                    configuré sera effacé.
        :type url: Optional[str]
        :return: Un tuple contenant le nombre de fichiers effacés et le nombre d'erreurs
                 rencontrées pendant l'opération.
        :rtype: Tuple[int, int]
        """
        if url:
            # Effacer le cache pour une URL spécifique
            filepath = self.get_cache_filepath(url)
            if filepath.exists():
                try:
                    filepath.unlink()
                    self.logger.info(f"Cache effacé pour {url}: {filepath.name}")
                    return 1, 0
                except Exception as e:
                    self.logger.error(
                        f"Erreur lors de l'effacement du cache pour {url}: {e}"
                    )
                    return 0, 1
            return 0, 0
        else:
            # Effacer tout le cache
            deleted = 0
            errors = 0
            for file in self.cache_dir.glob("*.txt"):
                try:
                    file.unlink()
                    deleted += 1
                except Exception as e:
                    self.logger.error(
                        f"Erreur lors de l'effacement du fichier {file.name}: {e}"
                    )
                    errors += 1

            self.logger.info(
                f"Cache entièrement effacé: {deleted} fichiers supprimés, {errors} erreurs"
            )
            return deleted, errors

    def get_cache_size(self) -> Tuple[int, int]:
        """
        Récupère la taille actuelle du cache.

        Calcule le nombre total de fichiers .txt dans le répertoire de cache
        et leur taille cumulée en octets.

        :return: Un tuple contenant le nombre de fichiers dans le cache et
                 la taille totale du cache en octets.
        :rtype: Tuple[int, int]
        """
        file_count = 0
        total_size = 0

        for file in self.cache_dir.glob("*.txt"):
            file_count += 1
            total_size += file.stat().st_size

        return file_count, total_size

    def get_cache_info(self) -> str:
        """
        Récupère des informations formatées sur l'état actuel du cache.

        :return: Une chaîne de caractères décrivant le nombre de fichiers
                 et la taille totale du cache dans un format lisible.
        :rtype: str
        """
        file_count, total_size = self.get_cache_size()

        # Convertir la taille en format lisible
        size_str = self._format_size(total_size)

        return f"Cache: {file_count} fichiers, {size_str}"

    def _format_size(self, size_bytes: int) -> str:
        """
        Formate une taille donnée en octets en une chaîne de caractères lisible par l'homme
        (par exemple, KB, MB, GB).

        :param size_bytes: La taille en octets à formater.
        :type size_bytes: int
        :return: Une chaîne de caractères représentant la taille formatée avec son unité.
        :rtype: str
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0 or unit == "GB":
                break
            size_bytes /= 1024.0

        return f"{size_bytes:.2f} {unit}"
