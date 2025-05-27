#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour ExtractDefinitions pour les tests.
Ce mock ajoute la méthode parse_obj manquante à la classe ExtractDefinitions.
Version corrigée qui évite les erreurs isinstance.
"""

import logging
from typing import Any, Dict, List
from unittest.mock import patch
import json as json_module
import gzip
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# Configuration du logging
logger = logging.getLogger("ExtractDefinitionsMock")

# Salt fixe pour la dérivation de clé (même que dans le vrai code)
FIXED_SALT = b'argumentation_analysis_salt_2024'

def derive_key_from_passphrase(passphrase: str) -> bytes:
    """
    Dérive une clé Fernet à partir d'une passphrase.
    Utilise la même logique que le vrai code.
    """
    if not passphrase:
        raise ValueError("Passphrase vide")
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=FIXED_SALT,
        iterations=480000,
        backend=default_backend()
    )
    derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
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
            return cls.model_validate(data)
        
        # Patcher la classe avec les nouvelles méthodes
        ExtractDefinitions.parse_obj = parse_obj
        ExtractDefinitions.model_validate = model_validate
        ExtractDefinitions.dict = dict
        ExtractDefinitions.json = json
        
        # Mock pour save_extract_definitions pour compatibilité avec les tests
        def mock_save_extract_definitions(definitions_obj, definitions_path=None, key_path=None, embed_full_text=False, config=None, **kwargs):
            """Mock simplifié de save_extract_definitions."""
            try:
                logger.info(f"Mock save_extract_definitions appelé avec: definitions_path={definitions_path}")
                
                # Convertir l'objet en liste si nécessaire
                if hasattr(definitions_obj, 'to_dict_list'):
                    data_to_save = {"sources": definitions_obj.to_dict_list()}
                elif hasattr(definitions_obj, 'dict'):
                    data_to_save = definitions_obj.dict()
                elif hasattr(definitions_obj, '__iter__') and not isinstance(definitions_obj, str):
                    data_to_save = {"sources": list(definitions_obj)}
                else:
                    data_to_save = {"sources": []}
                
                # Sauvegarder le fichier
                if definitions_path:
                    file_path = Path(str(definitions_path))
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Si un key_path est fourni, chiffrer les données avec Fernet
                    if key_path:
                        # Dériver la clé Fernet à partir de la passphrase
                        fernet_key = derive_key_from_passphrase(key_path)
                        f = Fernet(fernet_key)
                        
                        # Chiffrement avec Fernet
                        json_data = json_module.dumps(data_to_save, indent=2, ensure_ascii=False).encode('utf-8')
                        compressed_data = gzip.compress(json_data)
                        encrypted_data = f.encrypt(compressed_data)
                        
                        with open(str(file_path), 'wb') as f_file:
                            f_file.write(encrypted_data)
                        logger.info(f"Définitions chiffrées avec Fernet sauvegardées dans {definitions_path}")
                    else:
                        # Sauvegarder en JSON non chiffré
                        with open(str(file_path), 'w', encoding='utf-8') as f:
                            json_module.dump(data_to_save, f, indent=2, ensure_ascii=False)
                        logger.info(f"Définitions sauvegardées dans {definitions_path}")
                    
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde : {e}")
                return False
        
        # Mock pour load_extract_definitions compatible avec le mock de sauvegarde
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
                fernet_key = derive_key_from_passphrase(key)
                f_cipher = Fernet(fernet_key)
                compressed_data = f_cipher.decrypt(encrypted_data)
                logger.info("Données déchiffrées avec succès (Fernet)")
                
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
                    
            except Exception as e:
                logger.error(f"[ERREUR] Erreur lors du chargement mock: {e}")
                return [{"source_name": "Default", "source_type": "direct_download", "schema": "https", 
                        "host_parts": ["example", "com"], "path": "/", "extracts": []}]
        
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