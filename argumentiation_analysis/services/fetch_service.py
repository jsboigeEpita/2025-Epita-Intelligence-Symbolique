"""
Service de récupération de texte pour l'analyse d'argumentation.

Ce module fournit un service centralisé pour la récupération de texte à partir d'URLs,
avec prise en charge de différentes méthodes (direct, Jina, Tika) et gestion du cache.
"""

import hashlib
import logging
import requests
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Union

from .cache_service import CacheService

# Configuration du logging
logger = logging.getLogger("Services.FetchService")


class FetchService:
    """Service pour la récupération de texte à partir d'URLs."""
    
    def __init__(
        self,
        cache_service: CacheService,
        jina_reader_prefix: str = "https://r.jina.ai/",
        tika_server_url: str = "https://tika.open-webui.myia.io/tika",
        temp_download_dir: Optional[Path] = None,
        plaintext_extensions: Optional[List[str]] = None
    ):
        """
        Initialise le service de récupération.
        
        Args:
            cache_service: Service de cache
            jina_reader_prefix: Préfixe pour le lecteur Jina
            tika_server_url: URL du serveur Tika
            temp_download_dir: Répertoire temporaire pour les téléchargements
            plaintext_extensions: Extensions de fichiers texte
        """
        self.cache_service = cache_service
        self.jina_reader_prefix = jina_reader_prefix
        self.tika_server_url = tika_server_url
        self.temp_download_dir = temp_download_dir
        self.plaintext_extensions = plaintext_extensions or ['.txt', '.md', '.json', '.csv', '.xml', '.py', '.js', '.html', '.htm']
        self.logger = logger
        
        # S'assurer que le répertoire temporaire existe
        if self.temp_download_dir:
            self.temp_download_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Répertoire temporaire initialisé: {self.temp_download_dir}")
    
    def reconstruct_url(self, schema: str, host_parts: List[str], path: str) -> Optional[str]:
        """
        Reconstruit une URL à partir de schema, host_parts, et path.
        
        Args:
            schema: Schéma de l'URL (http, https, etc.)
            host_parts: Parties de l'hôte
            path: Chemin de l'URL
            
        Returns:
            URL reconstruite ou None si invalide
        """
        if not schema or not host_parts or not path:
            return None
        
        host = ".".join(part for part in host_parts if part)
        path = path if path.startswith('/') or not path else '/' + path
        
        return f"{schema}//{host}{path}"
    
    def fetch_text(
        self,
        source_info: Dict[str, Any],
        force_refresh: bool = False
    ) -> Tuple[Optional[str], str]:
        """
        Récupère le texte d'une source en utilisant la méthode appropriée.
        
        Args:
            source_info: Informations sur la source
            force_refresh: Si True, ignore le cache et force la récupération
            
        Returns:
            Tuple contenant (texte_source, message_ou_url)
        """
        # Reconstruire l'URL
        schema = source_info.get("schema")
        host_parts = source_info.get("host_parts", [])
        path = source_info.get("path")
        
        url = self.reconstruct_url(schema, host_parts, path)
        if not url:
            return None, "URL invalide"
        
        # Déterminer la méthode de récupération
        source_type = source_info.get("source_type", "direct_download")
        
        # Vérifier le cache si force_refresh est False
        if not force_refresh:
            cached_text = self.cache_service.load_from_cache(url)
            if cached_text is not None:
                return cached_text, url
        
        # Récupérer le texte selon le type de source
        try:
            if source_type == "jina":
                return self.fetch_with_jina(url), url
            elif source_type == "tika":
                # Vérifier si c'est un fichier texte
                is_plaintext = any(path.lower().endswith(ext) for ext in self.plaintext_extensions)
                if is_plaintext:
                    return self.fetch_direct_text(url), url
                else:
                    return self.fetch_with_tika(url), url
            else:  # direct_download ou autre
                return self.fetch_direct_text(url), url
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération de {url}: {e}")
            return None, f"Erreur: {str(e)}"
    
    def fetch_direct_text(self, url: str, timeout: int = 60) -> Optional[str]:
        """
        Récupère le contenu texte brut d'une URL.
        
        Args:
            url: URL à récupérer
            timeout: Délai d'attente en secondes
            
        Returns:
            Texte récupéré ou None en cas d'erreur
        """
        self.logger.info(f"Téléchargement direct depuis: {url}...")
        
        headers = {'User-Agent': 'ArgumentAnalysisApp/1.0'}
        
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            texte_brut = response.content.decode('utf-8', errors='ignore')
            self.logger.info(f"Contenu direct récupéré (longueur {len(texte_brut)}).")
            
            # Sauvegarder dans le cache
            self.cache_service.save_to_cache(url, texte_brut)
            
            return texte_brut
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur téléchargement direct ({url}): {e}")
            return None
    
    def fetch_with_jina(self, url: str, timeout: int = 90) -> Optional[str]:
        """
        Récupère et extrait le texte via Jina.
        
        Args:
            url: URL à récupérer
            timeout: Délai d'attente en secondes
            
        Returns:
            Texte récupéré ou None en cas d'erreur
        """
        jina_url = f"{self.jina_reader_prefix}{url}"
        self.logger.info(f"Récupération via Jina: {jina_url}...")
        
        headers = {'Accept': 'text/markdown', 'User-Agent': 'ArgumentAnalysisApp/1.0'}
        
        try:
            response = requests.get(jina_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            content = response.text
            md_start_marker = "Markdown Content:"
            md_start_index = content.find(md_start_marker)
            
            texte_brut = content[md_start_index + len(md_start_marker):].strip() if md_start_index != -1 else content
            self.logger.info(f"Contenu Jina récupéré (longueur {len(texte_brut)}).")
            
            # Sauvegarder dans le cache
            self.cache_service.save_to_cache(url, texte_brut)
            
            return texte_brut
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur Jina ({jina_url}): {e}")
            return None
    
    def fetch_with_tika(
        self,
        url: Optional[str] = None,
        file_content: Optional[bytes] = None,
        file_name: str = "fichier",
        raw_file_cache_path: Optional[Union[Path, str]] = None,
        timeout_dl: int = 60,
        timeout_tika: int = 600
    ) -> Optional[str]:
        """
        Traite une source via Tika.
        
        Args:
            url: URL à récupérer
            file_content: Contenu du fichier
            file_name: Nom du fichier
            raw_file_cache_path: Chemin du cache brut
            timeout_dl: Délai d'attente pour le téléchargement
            timeout_tika: Délai d'attente pour Tika
            
        Returns:
            Texte récupéré ou None en cas d'erreur
        """
        cache_key = url if url else f"file://{file_name}"
        
        content_to_send = None
        
        if url:
            original_filename = Path(url).name
            
            # Vérifier si c'est un fichier texte
            if any(url.lower().endswith(ext) for ext in self.plaintext_extensions):
                self.logger.info(f"URL détectée comme texte simple ({url}). Fetch direct.")
                return self.fetch_direct_text(url)
            
            # Gestion cache brut
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            file_extension = Path(original_filename).suffix if Path(original_filename).suffix else ".download"
            
            if self.temp_download_dir:
                effective_raw_cache_path = Path(raw_file_cache_path) if raw_file_cache_path else self.temp_download_dir / f"{url_hash}{file_extension}"
                
                # Vérifier si le fichier brut est déjà en cache
                if effective_raw_cache_path.exists() and effective_raw_cache_path.stat().st_size > 0:
                    try:
                        self.logger.info(f"Lecture fichier brut depuis cache local: {effective_raw_cache_path.name}")
                        content_to_send = effective_raw_cache_path.read_bytes()
                    except Exception as e_read_raw:
                        self.logger.warning(f"Erreur lecture cache brut {effective_raw_cache_path.name}: {e_read_raw}. Re-téléchargement...")
                        content_to_send = None
            
            # Télécharger si nécessaire
            if content_to_send is None:
                self.logger.info(f"Téléchargement (pour Tika) depuis: {url}...")
                
                try:
                    response_dl = requests.get(url, stream=True, timeout=timeout_dl)
                    response_dl.raise_for_status()
                    
                    content_to_send = response_dl.content
                    self.logger.info(f"Doc téléchargé ({len(content_to_send)} bytes).")
                    
                    # Sauvegarder dans le cache brut
                    if self.temp_download_dir and effective_raw_cache_path:
                        try:
                            effective_raw_cache_path.parent.mkdir(parents=True, exist_ok=True)
                            effective_raw_cache_path.write_bytes(content_to_send)
                            self.logger.info(f"Doc brut sauvegardé: {effective_raw_cache_path}")
                        except Exception as e_save:
                            self.logger.error(f"Erreur sauvegarde brut: {e_save}")
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Erreur téléchargement {url}: {e}")
                    return None
        elif file_content:
            self.logger.info(f"Utilisation contenu fichier '{file_name}' ({len(file_content)} bytes)...")
            content_to_send = file_content
            
            # Vérifier si c'est un fichier texte
            if any(file_name.lower().endswith(ext) for ext in self.plaintext_extensions):
                self.logger.info("Fichier uploadé détecté comme texte simple. Lecture directe.")
                
                try:
                    texte_brut = file_content.decode('utf-8', errors='ignore')
                    self.cache_service.save_to_cache(cache_key, texte_brut)
                    return texte_brut
                except Exception as e_decode:
                    self.logger.warning(f"Erreur décodage fichier texte '{file_name}': {e_decode}. Tentative avec Tika...")
        else:
            self.logger.error("fetch_with_tika: Il faut soit source_url soit file_content.")
            return None
        
        # Vérifier que le contenu est disponible
        if not content_to_send:
            self.logger.warning("Contenu brut vide ou non récupéré. Impossible d'envoyer à Tika.")
            self.cache_service.save_to_cache(cache_key, "")
            return ""
        
        # Envoyer à Tika
        self.logger.info(f"Envoi contenu à Tika ({self.tika_server_url})... (Timeout={timeout_tika}s)")
        
        headers = {
            'Accept': 'text/plain',
            'Content-Type': 'application/octet-stream',
            'X-Tika-OCRLanguage': 'fra+eng'
        }
        
        try:
            response_tika = requests.put(self.tika_server_url, data=content_to_send, headers=headers, timeout=timeout_tika)
            response_tika.raise_for_status()
            
            texte_brut = response_tika.text
            
            if not texte_brut:
                self.logger.warning(f"Warning: Tika status {response_tika.status_code} sans texte.")
            else:
                self.logger.info(f"Texte Tika extrait (longueur {len(texte_brut)}).")
            
            # Sauvegarder dans le cache
            self.cache_service.save_to_cache(cache_key, texte_brut)
            
            return texte_brut
        except requests.exceptions.Timeout:
            self.logger.error(f"❌ Timeout Tika ({timeout_tika}s).")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur Tika: {e}")
            return None