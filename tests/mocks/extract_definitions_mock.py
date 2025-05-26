#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour ExtractDefinitions pour les tests.
Ce mock ajoute la méthode parse_obj manquante à la classe ExtractDefinitions.
"""

import logging
from typing import Any, Dict, List
from unittest.mock import patch
import json

# Configuration du logging
logger = logging.getLogger("ExtractDefinitionsMock")

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
            return json.dumps(self.dict(**kwargs))
        
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
        def mock_save_extract_definitions(definitions_obj, definitions_path=None, key_path=None, **kwargs):
            """
            Mock de save_extract_definitions compatible avec les tests.
            
            Args:
                definitions_obj: Objet ExtractDefinitions ou liste
                definitions_path: Chemin du fichier de définitions
                key_path: Chemin du fichier de clé (optionnel)
                **kwargs: Autres paramètres
                
            Returns:
                bool: True si succès
            """
            try:
                import json
                from pathlib import Path
                
                # Convertir l'objet en liste si nécessaire
                if hasattr(definitions_obj, 'to_dict_list'):
                    data_to_save = {"sources": definitions_obj.to_dict_list()}
                elif hasattr(definitions_obj, 'dict'):
                    data_to_save = definitions_obj.dict()
                elif isinstance(definitions_obj, list):
                    data_to_save = {"sources": definitions_obj}
                else:
                    data_to_save = {"sources": []}
                
                # Sauvegarder le fichier
                if definitions_path:
                    file_path = Path(definitions_path)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                    logger.info(f"Définitions sauvegardées dans {definitions_path}")
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde : {e}")
                return False
        
        # Patcher la fonction save_extract_definitions
        from argumentation_analysis.ui import file_operations
        file_operations.save_extract_definitions = mock_save_extract_definitions
        
        logger.info("Mock ExtractDefinitions configuré avec succès")
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