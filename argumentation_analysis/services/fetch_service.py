"""
Service de récupération de texte pour l'analyse d'argumentation.

Ce module fournit un service centralisé pour la récupération de texte à partir d'URLs,
avec prise en charge de différentes méthodes (direct, Jina, Tika) et gestion du cache.
"""

import hashlib
import logging
import os
import requests
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Union
from pybreaker import CircuitBreakerError

from argumentation_analysis.config.settings import settings
from argumentation_analysis.models.extract_definition import SourceDefinition
from argumentation_analysis.core.utils.network_utils import retry_on_network_error, network_breaker
from .cache_service import CacheService

# Configuration du logging
logger = logging.getLogger("Services.FetchService")


class FetchService:
    """Service pour la récupération de texte à partir d'URLs."""
    
    def __init__(
        self,
        cache_service: CacheService,
        jina_reader_prefix: str = "https://r.jina.ai/",
        tika_server_url: Optional[str] = None,
        tika_server_timeout: Optional[int] = None,
        temp_download_dir: Optional[Path] = None,
        plaintext_extensions: Optional[List[str]] = None
    ):
        """
        Initialise le service de récupération de texte.

        :param cache_service: Instance du service de cache à utiliser.
        :type cache_service: CacheService
        :param jina_reader_prefix: Préfixe de l'URL pour le service Jina Reader.
        :type jina_reader_prefix: str
        :param tika_server_url: URL optionnelle du serveur Tika. Si non fournie,
                                utilise la valeur de la variable d'environnement
                                `TIKA_SERVER_ENDPOINT` ou une valeur par défaut.
        :type tika_server_url: Optional[str]
        :param tika_server_timeout: Timeout optionnel en secondes pour les requêtes Tika.
                                    Si non fourni, utilise `TIKA_SERVER_TIMEOUT` ou 30s.
        :type tika_server_timeout: Optional[int]
        :param temp_download_dir: Répertoire optionnel pour stocker les fichiers bruts
                                  téléchargés avant traitement par Tika.
        :type temp_download_dir: Optional[Path]
        :param plaintext_extensions: Liste optionnelle des extensions de fichiers à considérer
                                     comme du texte brut (pour éviter Tika si possible).
        :type plaintext_extensions: Optional[List[str]]
        """
        self.cache_service = cache_service
        self.jina_reader_prefix = jina_reader_prefix
        
        # Utiliser la configuration centralisée, avec les arguments comme surcharge
        tika_url = tika_server_url or str(settings.tika.server_endpoint)
        self.tika_server_url = tika_url if tika_url.endswith('/tika') else f"{tika_url.rstrip('/')}/tika"
        self.tika_server_timeout = tika_server_timeout or settings.tika.server_timeout
        
        self.temp_download_dir = temp_download_dir
        self.plaintext_extensions = plaintext_extensions or ['.txt', '.md', '.json', '.csv', '.xml', '.py', '.js', '.html', '.htm']
        self.logger = logger
        
        self.logger.info(f"FetchService initialisé avec Tika URL: {self.tika_server_url}, timeout: {self.tika_server_timeout}s")
        
        # S'assurer que le répertoire temporaire existe
        if self.temp_download_dir:
            self.temp_download_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Répertoire temporaire initialisé: {self.temp_download_dir}")
    
    def reconstruct_url(self, schema: str, host_parts: List[str], path: str) -> Optional[str]:
        """
        Reconstruit une URL complète à partir de ses composants.

        :param schema: Le schéma de l'URL (par exemple, "http", "https").
        :type schema: str
        :param host_parts: Une liste des parties composant le nom d'hôte
                           (par exemple, ["www", "example", "com"]).
        :type host_parts: List[str]
        :param path: Le chemin de la ressource sur le serveur (par exemple, "/page.html").
        :type path: str
        :return: L'URL reconstruite sous forme de chaîne de caractères, ou None si
                 l'un des composants essentiels est manquant.
        :rtype: Optional[str]
        """
        if not schema or not host_parts or not path:
            return None
        
        host = ".".join(part for part in host_parts if part)
        path = path if path.startswith('/') or not path else '/' + path
        
        return f"{schema}//{host}{path}"
    
    def fetch_text(
        self,
        source_info: Union[Dict[str, Any], SourceDefinition],
        force_refresh: bool = False
    ) -> Tuple[Optional[str], str]:
        """
        Récupère le texte d'une source en utilisant la méthode de récupération appropriée
        (direct, Jina, Tika) et gère le cache.

        :param source_info: Un dictionnaire ou un objet SourceDefinition contenant les
                            informations de la source.
        :type source_info: Union[Dict[str, Any], SourceDefinition]
        :param force_refresh: Si True, ignore le cache et force une nouvelle récupération
                              du contenu. Par défaut à False.
        :type force_refresh: bool
        :return: Un tuple contenant:
                 - Le texte source récupéré (str, ou None si échec).
                 - Un message de statut ou l'URL traitée (str).
        :rtype: Tuple[Optional[str], str]
        """
        url = None
        source_type = "direct_download"
        path = ""

        if isinstance(source_info, SourceDefinition):
            url = source_info.get_url()
            source_type = source_info.source_type
            path = source_info.path
        elif isinstance(source_info, dict):
            schema = source_info.get("schema")
            host_parts = source_info.get("host_parts", [])
            path = source_info.get("path", "")
            url = self.reconstruct_url(schema, host_parts, path)
            source_type = source_info.get("source_type", "direct_download")

        if not url:
            return None, "URL invalide ou informations de source incomplètes"
        
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
    
    @retry_on_network_error
    @network_breaker
    def fetch_direct_text(self, url: str, timeout: int = 15) -> Optional[str]:
        """
        Récupère le contenu texte brut d'une URL par téléchargement direct de manière robuste.
        """
        self.logger.info(f"Téléchargement direct depuis: {url}...")
        headers = {'User-Agent': 'ArgumentAnalysisApp/1.0'}
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            texte_brut = response.content.decode('utf-8', errors='ignore')
            self.logger.info(f"Contenu direct récupéré (longueur {len(texte_brut)}).")
            
            self.cache_service.save_to_cache(url, texte_brut)
            return texte_brut
        except CircuitBreakerError:
            self.logger.error(f"Disjoncteur ouvert pour fetch_direct_text sur {url}.")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur persistante de téléchargement direct pour {url}: {e}")
            raise  # Relancer pour que Tenacity puisse gérer
    
    @retry_on_network_error
    @network_breaker
    def fetch_with_jina(self, url: str, timeout: int = 45) -> Optional[str]:
        """
        Récupère et extrait le contenu textuel d'une URL via Jina de manière robuste.
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
            
            self.cache_service.save_to_cache(url, texte_brut)
            return texte_brut
        except CircuitBreakerError:
            self.logger.error(f"Disjoncteur ouvert pour fetch_with_jina sur {jina_url}.")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur Jina persistante pour {jina_url}: {e}")
            raise # Relancer pour que Tenacity puisse gérer
    
    def fetch_with_tika(
        self,
        url: Optional[str] = None,
        file_content: Optional[bytes] = None,
        file_name: str = "fichier",
        raw_file_cache_path: Optional[Union[Path, str]] = None,
        timeout_dl: int = 60,
        timeout_tika: Optional[int] = None
    ) -> Optional[str]:
        """
        Récupère et extrait le contenu textuel d'une URL ou d'un contenu binaire
        de fichier en utilisant un serveur Apache Tika.

        Si une URL est fournie et qu'elle ne pointe pas vers un type de fichier texte simple,
        le contenu est d'abord téléchargé (et mis en cache brut si `temp_download_dir`
        est configuré), puis envoyé à Tika. Si `file_content` est fourni, il est
        directement envoyé à Tika (sauf s'il s'agit d'un type texte simple).

        :param url: URL optionnelle du fichier à traiter.
        :type url: Optional[str]
        :param file_content: Contenu binaire optionnel du fichier à traiter.
        :type file_content: Optional[bytes]
        :param file_name: Nom du fichier (utilisé pour le cache et la détection de type
                          si `file_content` est fourni). Par défaut "fichier".
        :type file_name: str
        :param raw_file_cache_path: Chemin optionnel pour stocker le fichier brut téléchargé.
        :type raw_file_cache_path: Optional[Union[Path, str]]
        :param timeout_dl: Délai d'attente en secondes pour le téléchargement du fichier si `url` est utilisé.
        :type timeout_dl: int
        :param timeout_tika: Délai d'attente optionnel en secondes pour la requête au serveur Tika.
                             Utilise `self.tika_server_timeout` si None.
        :type timeout_tika: Optional[int]
        :return: Le contenu textuel extrait par Tika, ou None si une erreur survient.
                 Retourne une chaîne vide si Tika ne retourne aucun texte mais que la requête réussit.
        :rtype: Optional[str]
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
                    response_dl = self._robust_get_request(url, timeout=timeout_dl)
                    if response_dl is None: return None
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
        
        # Utiliser le timeout configuré ou celui fourni en paramètre
        effective_timeout = timeout_tika or self.tika_server_timeout
        
        # Envoyer à Tika
        self.logger.info(f"Envoi contenu à Tika ({self.tika_server_url})... (Timeout={effective_timeout}s)")
        
        headers = {
            'Accept': 'text/plain',
            'Content-Type': 'application/octet-stream',
            'X-Tika-OCRLanguage': 'fra+eng'
        }
        
        try:
            response_tika = self._robust_put_request(self.tika_server_url, data=content_to_send, headers=headers, timeout=effective_timeout)
            if response_tika is None: return None
            texte_brut = response_tika.text
            
            if not texte_brut:
                self.logger.warning(f"Warning: Tika status {response_tika.status_code} sans texte.")
            else:
                self.logger.info(f"Texte Tika extrait (longueur {len(texte_brut)}).")
            
            # Sauvegarder dans le cache
            self.cache_service.save_to_cache(cache_key, texte_brut)
            
            return texte_brut
        except requests.exceptions.Timeout: # Déjà géré par Tenacity mais garde une sécurité
            self.logger.error(f"Timeout Tika ({effective_timeout}s).")
            return None
        except requests.exceptions.RequestException as e: # Déjà géré par Tenacity
            self.logger.error(f"Erreur Tika persistante: {e}")
            return None

    @retry_on_network_error
    @network_breaker
    def _robust_get_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        try:
            response = requests.get(url, **kwargs)
            response.raise_for_status()
            return response
        except CircuitBreakerError:
            self.logger.error(f"Disjoncteur ouvert pour GET sur {url}.")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur GET persistante pour {url}: {e}")
            raise
    
    @retry_on_network_error
    @network_breaker
    def _robust_put_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        try:
            response = requests.put(url, **kwargs)
            response.raise_for_status()
            return response
        except CircuitBreakerError:
            self.logger.error(f"Disjoncteur ouvert pour PUT sur {url}.")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur PUT persistante pour {url}: {e}")
            raise