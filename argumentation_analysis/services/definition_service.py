"""
Service de gestion des définitions d'extraits pour l'analyse d'argumentation.

Ce module fournit un service centralisé pour le chargement, la sauvegarde et la gestion
des définitions d'extraits, avec prise en charge du chiffrement et de la validation.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

# Imports absolus pour les tests
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
from services.crypto_service import CryptoService

# Configuration du logging
logger = logging.getLogger("Services.DefinitionService")


class DefinitionService:
    """Service pour la gestion des définitions d'extraits."""
    
    def __init__(
        self,
        crypto_service: CryptoService,
        config_file: Path,
        fallback_file: Optional[Path] = None,
        default_definitions: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialise le service de définitions.
        
        Args:
            crypto_service: Service de chiffrement
            config_file: Chemin vers le fichier de configuration principal
            fallback_file: Chemin vers le fichier de secours (optionnel)
            default_definitions: Définitions par défaut (optionnel)
        """
        self.crypto_service = crypto_service
        self.config_file = config_file
        self.fallback_file = fallback_file
        self.default_definitions = default_definitions or []
        self.logger = logger
        
        self.logger.info(f"Service de définitions initialisé avec fichier principal: {config_file}")
        if fallback_file:
            self.logger.info(f"Fichier de secours configuré: {fallback_file}")
    
    def load_definitions(self) -> Tuple[ExtractDefinitions, Optional[str]]:
        """
        Charge les définitions d'extraits avec gestion d'erreurs robuste.
        
        Returns:
            Tuple contenant (extract_definitions, error_message)
        """
        definitions_list = []
        error_message = None
        
        # Essayer de charger depuis le fichier principal
        if self.config_file.exists():
            try:
                if self.crypto_service.is_encryption_enabled():
                    # Fichier chiffré
                    with open(self.config_file, 'rb') as f:
                        encrypted_data = f.read()
                    
                    definitions_list = self.crypto_service.decrypt_and_decompress_json(encrypted_data)
                    
                    if definitions_list:
                        self.logger.info(f"✅ Définitions chargées depuis le fichier chiffré {self.config_file.name}")
                    else:
                        error_message = f"Échec du déchiffrement de {self.config_file.name}"
                        self.logger.error(error_message)
                else:
                    # Fichier JSON non chiffré
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        definitions_list = json.load(f)
                    
                    self.logger.info(f"✅ Définitions chargées depuis {self.config_file.name}")
            except Exception as e:
                error_message = f"Erreur lors du chargement de {self.config_file.name}: {str(e)}"
                self.logger.error(error_message)
        else:
            error_message = f"Le fichier {self.config_file.name} n'existe pas"
            self.logger.warning(error_message)
        
        # Si échec ou pas de définitions, essayer le fichier de secours
        if (not definitions_list or error_message) and self.fallback_file and self.fallback_file.exists():
            try:
                with open(self.fallback_file, 'r', encoding='utf-8') as f:
                    definitions_list = json.load(f)
                
                self.logger.info(f"✅ Définitions chargées depuis le fichier de secours {self.fallback_file.name}")
                error_message = None
            except Exception as e:
                error_message = f"Erreur lors du chargement du fichier de secours {self.fallback_file.name}: {str(e)}"
                self.logger.error(error_message)
        
        # Si toujours rien, utiliser les définitions par défaut
        if not definitions_list:
            definitions_list = self.default_definitions
            if not error_message:
                error_message = "Aucune définition trouvée, utilisation des définitions par défaut"
            self.logger.warning(f"⚠️ Utilisation des définitions par défaut ({len(definitions_list)} sources)")
        
        # Convertir en modèle ExtractDefinitions
        extract_definitions = ExtractDefinitions.from_dict_list(definitions_list)
        
        return extract_definitions, error_message
    
    def save_definitions(self, definitions: ExtractDefinitions) -> Tuple[bool, Optional[str]]:
        """
        Sauvegarde les définitions d'extraits avec gestion d'erreurs robuste.
        
        Args:
            definitions: Définitions d'extraits à sauvegarder
            
        Returns:
            Tuple contenant (success, error_message)
        """
        success = False
        error_message = None
        
        # Convertir en liste de dictionnaires
        definitions_list = definitions.to_dict_list()
        
        # Essayer de sauvegarder dans le fichier principal
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            if self.crypto_service.is_encryption_enabled():
                # Fichier chiffré
                encrypted_data = self.crypto_service.encrypt_and_compress_json(definitions_list)
                
                if encrypted_data:
                    with open(self.config_file, 'wb') as f:
                        f.write(encrypted_data)
                    
                    self.logger.info(f"✅ Définitions sauvegardées dans le fichier chiffré {self.config_file.name}")
                    success = True
                else:
                    error_message = "Échec du chiffrement des définitions"
                    self.logger.error(error_message)
            else:
                # Fichier JSON non chiffré
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(definitions_list, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"✅ Définitions sauvegardées dans {self.config_file.name}")
                success = True
        except Exception as e:
            error_message = f"Erreur lors de la sauvegarde dans {self.config_file.name}: {str(e)}"
            self.logger.error(error_message)
        
        # Si échec, essayer le fichier de secours
        if not success and self.fallback_file:
            try:
                self.fallback_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.fallback_file, 'w', encoding='utf-8') as f:
                    json.dump(definitions_list, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"✅ Définitions sauvegardées dans le fichier de secours {self.fallback_file.name}")
                success = True
                error_message = None
            except Exception as e:
                error_message = f"Erreur lors de la sauvegarde dans le fichier de secours {self.fallback_file.name}: {str(e)}"
                self.logger.error(error_message)
        
        return success, error_message
    
    def export_definitions_to_json(self, definitions: ExtractDefinitions, output_path: Path) -> Tuple[bool, str]:
        """
        Exporte les définitions d'extraits vers un fichier JSON.
        
        Args:
            definitions: Définitions d'extraits à exporter
            output_path: Chemin vers le fichier de sortie
            
        Returns:
            Tuple contenant (success, message)
        """
        try:
            # Convertir en liste de dictionnaires
            definitions_list = definitions.to_dict_list()
            
            # Créer le répertoire parent si nécessaire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Écrire dans le fichier
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(definitions_list, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Définitions exportées vers {output_path}")
            return True, f"✅ Définitions exportées vers {output_path}"
        except Exception as e:
            error_message = f"❌ Erreur lors de l'exportation: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def import_definitions_from_json(self, input_path: Path) -> Tuple[bool, Union[ExtractDefinitions, str]]:
        """
        Importe les définitions d'extraits depuis un fichier JSON.
        
        Args:
            input_path: Chemin vers le fichier d'entrée
            
        Returns:
            Tuple contenant (success, definitions_or_error_message)
        """
        try:
            # Vérifier que le fichier existe
            if not input_path.exists():
                error_message = f"❌ Le fichier {input_path} n'existe pas"
                self.logger.error(error_message)
                return False, error_message
            
            # Lire le fichier
            with open(input_path, 'r', encoding='utf-8') as f:
                definitions_list = json.load(f)
            
            # Convertir en modèle ExtractDefinitions
            extract_definitions = ExtractDefinitions.from_dict_list(definitions_list)
            
            self.logger.info(f"✅ Définitions importées depuis {input_path}")
            return True, extract_definitions
        except json.JSONDecodeError as e:
            error_message = f"❌ Erreur de format JSON: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"❌ Erreur lors de l'importation: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
    
    def validate_definitions(self, definitions: ExtractDefinitions) -> Tuple[bool, List[str]]:
        """
        Valide les définitions d'extraits.
        
        Args:
            definitions: Définitions d'extraits à valider
            
        Returns:
            Tuple contenant (is_valid, error_messages)
        """
        errors = []
        
        # Vérifier chaque source
        for i, source in enumerate(definitions.sources):
            # Vérifier les champs obligatoires de la source
            if not source.source_name:
                errors.append(f"Source #{i+1}: Nom de source manquant")
            
            if not source.source_type:
                errors.append(f"Source '{source.source_name}': Type de source manquant")
            
            if not source.schema:
                errors.append(f"Source '{source.source_name}': Schéma manquant")
            
            if not source.host_parts:
                errors.append(f"Source '{source.source_name}': Parties d'hôte manquantes")
            
            if not source.path:
                errors.append(f"Source '{source.source_name}': Chemin manquant")
            
            # Vérifier chaque extrait
            for j, extract in enumerate(source.extracts):
                # Vérifier les champs obligatoires de l'extrait
                if not extract.extract_name:
                    errors.append(f"Source '{source.source_name}', Extrait #{j+1}: Nom d'extrait manquant")
                
                if not extract.start_marker:
                    errors.append(f"Source '{source.source_name}', Extrait '{extract.extract_name}': Marqueur de début manquant")
                
                if not extract.end_marker:
                    errors.append(f"Source '{source.source_name}', Extrait '{extract.extract_name}': Marqueur de fin manquant")
        
        return len(errors) == 0, errors