#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour ExtractDefinitions pour les tests.
Ce mock ajoute la méthode parse_obj manquante à la classe ExtractDefinitions.
Version corrigée qui évite les erreurs isinstance.
"""

import logging
from typing import Any, Dict, List, Optional, Union # MODIFIÉ
from unittest.mock import patch
import json as json_module
import gzip
import base64
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# Configuration du logging
logger = logging.getLogger("ExtractDefinitionsMock")

# Salt fixe pour la dérivation de clé (même que dans le vrai code)
FIXED_SALT = b'argumentation_analysis_salt_2024'

def derive_key_from_passphrase(passphrase: Union[str, bytes]) -> bytes:
    """
    Dérive une clé Fernet à partir d'une passphrase.
    Utilise la même logique que le vrai code.
    """
    if not passphrase:
        raise ValueError("Passphrase vide")

    passphrase_bytes: bytes
    if isinstance(passphrase, str):
        passphrase_bytes = passphrase.encode('utf-8')
    elif isinstance(passphrase, bytes):
        passphrase_bytes = passphrase
    else:
        raise TypeError("Passphrase doit être str ou bytes")
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=FIXED_SALT,
        iterations=480000,
        backend=default_backend()
    )
    derived_key_raw = kdf.derive(passphrase_bytes)
    return base64.urlsafe_b64encode(derived_key_raw)

def setup_extract_definitions_mock():
    """Configure le mock pour ExtractDefinitions."""
    try:
        # Importer la classe originale
        from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
        
        # Ajouter la méthode parse_obj à la classe ExtractDefinitions
        @classmethod
        def parse_obj(cls, data: Dict[str, Any]) -> 'ExtractDefinitions':
            """
            Crée une instance d'ExtractDefinitions à partir d'un dictionnaire.
            Compatible avec l'API Pydantic v1.
            
            Args:
                data: Dictionnaire contenant les données, avec une clé 'sources'
                
            Returns:
                Instance d'ExtractDefinitions
            """
            try:
                if hasattr(data, 'get') and "sources" in data:
                    # Utiliser la méthode from_dict_list existante
                    return cls.from_dict_list(data["sources"])
                elif hasattr(data, '__iter__') and not isinstance(data, str):
                    # Si c'est directement une liste de sources
                    return cls.from_dict_list(data)
                else:
                    # Fallback : créer une instance vide
                    return cls()
            except Exception as e:
                logger.error(f"Erreur dans parse_obj: {e}")
                # Fallback : créer une instance vide
                return cls()
        
        # Ajouter la méthode dict pour compatibilité Pydantic
        def dict(self, **kwargs) -> Dict[str, Any]:
            """
            Convertit l'instance en dictionnaire.
            Compatible avec l'API Pydantic.
            
            Returns:
                Dictionnaire avec la structure attendue
            """
            return {
                "sources": self.to_dict_list()
            }
        
        # Ajouter la méthode json pour compatibilité Pydantic
        def json(self, **kwargs) -> str:
            """
            Convertit l'instance en JSON.
            Compatible avec l'API Pydantic.
            
            Returns:
                Chaîne JSON
            """
            return json_module.dumps(self.dict(**kwargs))
        
        # Ajouter une méthode pour la compatibilité avec save_extract_definitions
        def to_list(self) -> List[Dict[str, Any]]:
            """
            Convertit l'instance en liste de dictionnaires.
            Compatible avec save_extract_definitions.
            
            Returns:
                Liste de dictionnaires des sources
            """
            return self.to_dict_list()
        
        # Ajouter la méthode model_validate pour compatibilité Pydantic v2
        @classmethod
        def model_validate(cls, data: Dict[str, Any]) -> 'ExtractDefinitions':
            """
            Crée une instance d'ExtractDefinitions à partir d'un dictionnaire.
            Compatible avec l'API Pydantic v2.
            
            Args:
                data: Dictionnaire contenant les données
                
            Returns:
                Instance d'ExtractDefinitions
            """
            return cls.parse_obj(data)
        
        # Patcher la classe avec les nouvelles méthodes
        ExtractDefinitions.parse_obj = parse_obj
        ExtractDefinitions.model_validate = model_validate
        ExtractDefinitions.dict = dict
        ExtractDefinitions.json = json
        
        # Mock pour save_extract_definitions pour compatibilité avec les tests
        def mock_save_extract_definitions(extract_definitions: List[Dict[str, Any]],
                                          config_file: Path,
                                          encryption_key: Optional[bytes] = None, # Correspond à la signature réelle
                                          key_path: Optional[str] = None, # Ajout pour flexibilité
                                          embed_full_text: bool = False,
                                          config: Optional[Dict[str, Any]] = None,
                                          **kwargs): # Garder kwargs au cas où
            """Mock simplifié de save_extract_definitions."""
            try:
                logger.info(f"Mock save_extract_definitions appelé avec: config_file={config_file}, key_path={key_path}")
                
                current_encryption_key = encryption_key
                if not current_encryption_key and key_path:
                    try:
                        with open(key_path, 'rb') as kf:
                            current_encryption_key = kf.read()
                        if not current_encryption_key: # Clé vide
                             logger.warning(f"Clé chargée depuis {key_path} est vide.")
                             current_encryption_key = None # Forcer la sauvegarde non chiffrée
                    except Exception as e_key_load:
                        logger.error(f"Erreur lors du chargement de la clé depuis {key_path}: {e_key_load}")
                        current_encryption_key = None # Forcer la sauvegarde non chiffrée en cas d'erreur

                # Convertir l'objet en liste si nécessaire
                # extract_definitions est déjà supposé être une List[Dict]
                if isinstance(extract_definitions, list):
                    data_to_save = {"sources": extract_definitions}
                elif hasattr(extract_definitions, 'to_dict_list'): # Pour l'objet ExtractDefinitions
                    data_to_save = {"sources": extract_definitions.to_dict_list()}
                elif hasattr(extract_definitions, 'dict'): # Pour un objet Pydantic
                    data_to_save = extract_definitions.dict()
                else:
                    logger.warning(f"Type inattendu pour extract_definitions: {type(extract_definitions)}. Tentative de sauvegarde directe.")
                    data_to_save = {"sources": []} # Fallback
                
                # Sauvegarder le fichier
                if config_file:
                    file_path = Path(str(config_file))
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Si une current_encryption_key est fournie, chiffrer les données avec Fernet
                    if current_encryption_key:
                        # La clé est déjà dérivée et en bytes
                        f_cipher = Fernet(current_encryption_key)
                        
                        # Chiffrement avec Fernet
                        json_data = json_module.dumps(data_to_save, indent=2, ensure_ascii=False).encode('utf-8')
                        compressed_data = gzip.compress(json_data)
                        encrypted_data = f_cipher.encrypt(compressed_data)
                        
                        with open(str(file_path), 'wb') as f_file:
                            f_file.write(encrypted_data)
                        logger.info(f"Définitions chiffrées avec Fernet sauvegardées dans {config_file}")
                    else:
                        # Sauvegarder en JSON non chiffré
                        with open(str(file_path), 'w', encoding='utf-8') as f_file: # Renommer f en f_file pour éviter conflit
                            json_module.dump(data_to_save, f_file, indent=2, ensure_ascii=False)
                        logger.info(f"Définitions sauvegardées (non chiffrées) dans {config_file}")
                    
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde : {e}")
                return False
        
        # Mock pour load_extract_definitions compatible avec le mock de sauvegarde
        # La signature de mock_load_extract_definitions semble correcte par rapport à son usage dans les tests
        # (key est la passphrase, qui est ensuite dérivée en clé Fernet à l'intérieur du mock)
        def mock_load_extract_definitions(config_file, key, app_config=None):
            """Mock simplifié de load_extract_definitions."""
            try:
                logger.info(f"Mock load_extract_definitions appelé avec: config_file={config_file}")
                
                # Définitions par défaut
                fallback_definitions = [
                    {"source_name": "Default", "source_type": "direct_download", "schema": "https", 
                     "host_parts": ["example", "com"], "path": "/", "extracts": []}
                ]
                
                # Vérifier si le fichier existe
                config_file_path = Path(str(config_file))
                if not config_file_path.exists():
                    logger.info(f"Fichier config chiffré '{config_file}' non trouvé. Utilisation définitions par défaut.")
                    return fallback_definitions[:]
                
                # Vérifier la clé
                if not key:
                    logger.warning("Clé chiffrement absente. Chargement config impossible. Utilisation définitions par défaut.")
                    return fallback_definitions[:]
                
                # Lire et déchiffrer le fichier
                with open(str(config_file_path), 'rb') as f:
                    encrypted_data = f.read()
                
                # Déchiffrement avec Fernet
                final_fernet_key: bytes
                if isinstance(key, str): # Supposons que str est une passphrase à dériver
                    logger.info(f"Dérivation de la clé Fernet à partir de la passphrase (str) pour {config_file_path}")
                    final_fernet_key = derive_key_from_passphrase(key)
                elif isinstance(key, bytes) and len(key) == 44 and key.endswith(b'='): # Heuristique pour une clé Fernet b64
                    logger.info(f"Utilisation de la clé Fernet (bytes) fournie directement pour {config_file_path}")
                    final_fernet_key = key
                else: # Fallback si ce n'est ni une str ni une clé Fernet bytes reconnaissable
                    logger.warning(f"Type de clé inattendu ou format incorrect ({type(key)}, len={len(key) if isinstance(key, bytes) else 'N/A'}). Tentative de dérivation comme passphrase.")
                    final_fernet_key = derive_key_from_passphrase(key)

                f_cipher = Fernet(final_fernet_key)
                # Le try/except pour InvalidToken doit englober decrypt ET le reste du traitement
                # pour s'assurer qu'on ne retourne pas de fallback si le déchiffrement échoue.
                compressed_data = f_cipher.decrypt(encrypted_data) # Peut lever InvalidToken
                logger.info(f"Mock: Données déchiffrées avec succès pour {config_file_path}")
                
                # Décompresser
                decompressed_data = gzip.decompress(compressed_data)
                logger.info("Données décompressées avec succès")
                
                # Parser JSON
                json_str = decompressed_data.decode('utf-8')
                data = json_module.loads(json_str)
                logger.info("JSON parsé avec succès")
                
                # Extraire les sources
                if hasattr(data, 'get') and "sources" in data:
                    definitions = data["sources"]
                elif hasattr(data, '__iter__') and not isinstance(data, str):
                    definitions = data
                else:
                    logger.warning("Format de données invalide. Utilisation définitions par défaut.")
                    return fallback_definitions[:]
                
                # Validation simple
                if not hasattr(definitions, '__iter__') or isinstance(definitions, str):
                    logger.warning("Format définitions invalide (pas itérable). Utilisation définitions par défaut.")
                    return fallback_definitions[:]
                
                # Convertir en liste et valider
                result_definitions = []
                for item in definitions:
                    if hasattr(item, 'get'):  # dict-like
                        # Vérifier les champs essentiels
                        required_fields = ["source_name", "source_type", "schema", "host_parts", "path"]
                        if all(field in item for field in required_fields):
                            # S'assurer que extracts existe
                            if "extracts" not in item:
                                item["extracts"] = []
                            result_definitions.append(item)
                        else:
                            logger.warning(f"Élément invalide ignoré: champs manquants")
                
                if result_definitions:
                    logger.info(f"[OK] {len(result_definitions)} définitions chargées depuis fichier mock.")
                    return result_definitions
                else:
                    logger.warning("Aucune définition valide trouvée. Utilisation définitions par défaut.")
                    return fallback_definitions[:]
                    
            except InvalidToken as e_token_outer:
                logger.error(f"Mock: Échec du déchiffrement (InvalidToken) pour {config_file_path} lors de l'appel à decrypt. Clé dérivée de passphrase commençant par: {key[:5]}...")
                raise e_token_outer # S'assurer que InvalidToken est bien relancée
            except Exception as e_other: # Renommer pour clarté
                logger.error(f"Mock: [ERREUR] Autre erreur non-InvalidToken lors du chargement mock pour {config_file_path}: {e_other}")
                return fallback_definitions[:]
        
        # Patcher les fonctions save_extract_definitions et load_extract_definitions
        from argumentation_analysis.ui import file_operations
        file_operations.save_extract_definitions = mock_save_extract_definitions
        file_operations.load_extract_definitions = mock_load_extract_definitions
        
        logger.info("Mock ExtractDefinitions configuré avec succès (save + load)")
        return True
        
    except ImportError as e:
        logger.error(f"Erreur lors de l'import d'ExtractDefinitions : {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la configuration du mock ExtractDefinitions : {e}")
        return False

# Configuration automatique du mock
if __name__ != "__main__":
    setup_extract_definitions_mock()