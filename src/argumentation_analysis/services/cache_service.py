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
        
        Args:
            cache_dir: Répertoire de cache
        """
        self.cache_dir = cache_dir
        self.logger = logger
        
        # S'assurer que le répertoire de cache existe
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Répertoire de cache initialisé: {self.cache_dir}")
    
    def get_cache_filepath(self, url: str) -> Path:
        """
        Génère le chemin du fichier cache pour une URL.
        
        Args:
            url: URL à hacher
            
        Returns:
            Chemin du fichier cache
        """
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.txt"
    
    def load_from_cache(self, url: str) -> Optional[str]:
        """
        Charge le contenu textuel depuis le cache si disponible.
        
        Args:
            url: URL à rechercher dans le cache
            
        Returns:
            Contenu textuel ou None si non trouvé
        """
        filepath = self.get_cache_filepath(url)
        if filepath.exists():
            try:
                self.logger.info(f"Lecture depuis cache: {filepath.name}")
                return filepath.read_text(encoding='utf-8')
            except Exception as e:
                self.logger.warning(f"Erreur lecture cache {filepath.name}: {e}")
                return None
        self.logger.debug(f"Cache miss pour URL: {url}")
        return None
    
    def save_to_cache(self, url: str, text: str) -> bool:
        """
        Sauvegarde le contenu textuel dans le cache.
        
        Args:
            url: URL associée au contenu
            text: Contenu textuel à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi, False sinon
        """
        if not text:
            self.logger.info("Texte vide, non sauvegardé.")
            return False
        
        filepath = self.get_cache_filepath(url)
        try:
            # S'assurer que le dossier cache existe
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(text, encoding='utf-8')
            self.logger.info(f"Texte sauvegardé: {filepath.name}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde cache {filepath.name}: {e}")
            return False
    
    def clear_cache(self, url: Optional[str] = None) -> Tuple[int, int]:
        """
        Efface le cache pour une URL spécifique ou tout le cache.
        
        Args:
            url: URL spécifique à effacer (si None, efface tout le cache)
            
        Returns:
            Tuple contenant (nombre de fichiers effacés, nombre d'erreurs)
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
                    self.logger.error(f"Erreur lors de l'effacement du cache pour {url}: {e}")
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
                    self.logger.error(f"Erreur lors de l'effacement du fichier {file.name}: {e}")
                    errors += 1
            
            self.logger.info(f"Cache entièrement effacé: {deleted} fichiers supprimés, {errors} erreurs")
            return deleted, errors
    
    def get_cache_size(self) -> Tuple[int, int]:
        """
        Récupère la taille du cache.
        
        Returns:
            Tuple contenant (nombre de fichiers, taille totale en octets)
        """
        file_count = 0
        total_size = 0
        
        for file in self.cache_dir.glob("*.txt"):
            file_count += 1
            total_size += file.stat().st_size
        
        return file_count, total_size
    
    def get_cache_info(self) -> str:
        """
        Récupère des informations sur le cache.
        
        Returns:
            Chaîne d'informations sur le cache
        """
        file_count, total_size = self.get_cache_size()
        
        # Convertir la taille en format lisible
        size_str = self._format_size(total_size)
        
        return f"Cache: {file_count} fichiers, {size_str}"
    
    def _format_size(self, size_bytes: int) -> str:
        """
        Formate une taille en octets en format lisible.
        
        Args:
            size_bytes: Taille en octets
            
        Returns:
            Chaîne formatée
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0 or unit == 'GB':
                break
            size_bytes /= 1024.0
        
        return f"{size_bytes:.2f} {unit}"