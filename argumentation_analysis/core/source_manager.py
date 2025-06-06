#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestionnaire de sources pour le basculement entre sources simples et corpus chiffré.

Ce module fournit une interface unifiée pour accéder aux sources de données,
qu'elles soient simples (mockées) ou complexes (corpus chiffré de discours politiques).
"""

import os
import sys
import json
import gzip
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

# Imports pour le déchiffrement
from argumentation_analysis.utils.core_utils.crypto_utils import load_encryption_key, decrypt_data_with_fernet
from argumentation_analysis.models.extract_definition import ExtractDefinitions
from argumentation_analysis.paths import DATA_DIR

logger = logging.getLogger(__name__)

class SourceType(Enum):
    """Types de sources disponibles."""
    SIMPLE = "simple"
    COMPLEX = "complex"

@dataclass
class SourceConfig:
    """Configuration pour l'accès aux sources."""
    source_type: SourceType
    passphrase: Optional[str] = None
    anonymize_logs: bool = True
    auto_cleanup: bool = True

class SourceManager:
    """
    Gestionnaire unifié pour l'accès aux sources de données.
    
    Permet de basculer entre :
    - Sources simples : données mockées pour tests et développement
    - Sources complexes : corpus chiffré de discours politiques réels
    """
    
    def __init__(self, config: SourceConfig):
        """
        Initialise le gestionnaire de sources.
        
        Args:
            config: Configuration pour l'accès aux sources
        """
        self.config = config
        self.logger = self._setup_logging()
        self._temp_files: List[Path] = []  # Pour le nettoyage automatique
        
    def _setup_logging(self) -> logging.Logger:
        """Configure le logging avec anonymisation si nécessaire."""
        source_logger = logging.getLogger(f"{__name__}.{self.config.source_type.value}")
        
        if self.config.anonymize_logs and self.config.source_type == SourceType.COMPLEX:
            # Pour les données sensibles, on ajoute un filtre d'anonymisation
            class AnonymizeFilter(logging.Filter):
                def filter(self, record):
                    # Anonymiser les noms propres et données sensibles
                    if hasattr(record, 'msg') and isinstance(record.msg, str):
                        # Simple anonymisation - à adapter selon les besoins
                        msg = record.msg
                        # Remplacer les noms communs de politiciens par des placeholders
                        sensitive_patterns = [
                            'Hitler', 'Staline', 'Mao', 'Churchill', 'Roosevelt',
                            'Trump', 'Biden', 'Macron', 'Poutine'
                        ]
                        for pattern in sensitive_patterns:
                            msg = msg.replace(pattern, '[LEADER]')
                        record.msg = msg
                    return True
            
            source_logger.addFilter(AnonymizeFilter())
            
        return source_logger
    
    def load_sources(self) -> Tuple[Optional[ExtractDefinitions], str]:
        """
        Charge les sources selon la configuration.
        
        Returns:
            Tuple[Optional[ExtractDefinitions], str]: Les définitions et un message de statut
        """
        if self.config.source_type == SourceType.SIMPLE:
            return self._load_simple_sources()
        elif self.config.source_type == SourceType.COMPLEX:
            return self._load_complex_sources()
        else:
            return None, f"Type de source non supporté: {self.config.source_type}"
    
    def _load_simple_sources(self) -> Tuple[Optional[ExtractDefinitions], str]:
        """
        Charge les sources simples (mockées) pour tests et développement.
        
        Returns:
            Tuple contenant les définitions mockées et un message de statut
        """
        self.logger.info("Chargement des sources simples (mode développement/test)")
        
        # Créer des sources mockées représentatives
        mock_sources_data = [
            {
                "source_name": "Débat sur le climat - Exemple",
                "source_type": "text",
                "schema": "mock",
                "host_parts": ["climate", "debate"],
                "path": "/mock/climate_debate",
                "extracts": [
                    {
                        "extract_name": "Argumentation sur le réchauffement",
                        "start_marker": "Le réchauffement climatique",
                        "end_marker": "déconstruire les sophismes.",
                        "full_text": (
                            "Le réchauffement climatique est un sujet complexe. Certains affirment qu'il s'agit d'un mythe, "
                            "citant par exemple des hivers froids comme preuve. D'autres soutiennent que des mesures "
                            "drastiques sont nécessaires immédiatement pour éviter une catastrophe planétaire. Il est "
                            "également courant d'entendre que les scientifiques qui alertent sur ce danger sont "
                            "financièrement motivés, ce qui mettrait en doute leurs conclusions. Face à ces arguments, "
                            "il est crucial d'analyser les faits avec rigueur et de déconstruire les sophismes."
                        )
                    }
                ]
            },
            {
                "source_name": "Discours politique - Exemple",
                "source_type": "text",
                "schema": "mock",
                "host_parts": ["political", "speech"],
                "path": "/mock/political_speech",
                "extracts": [
                    {
                        "extract_name": "Rhétorique de l'urgence",
                        "start_marker": "Mes chers concitoyens",
                        "end_marker": "actions d'aujourd'hui.",
                        "full_text": (
                            "Mes chers concitoyens, nous vivons une époque où nos valeurs sont menacées. "
                            "L'ennemi cherche à diviser notre nation. Mais nous, peuple uni, nous résisterons. "
                            "Tous ceux qui ne sont pas avec nous sont contre nous. C'est pourquoi nous devons "
                            "agir maintenant, sans hésitation, car demain il sera trop tard. L'histoire nous "
                            "jugera sur nos actions d'aujourd'hui."
                        )
                    }
                ]
            }
        ]
        
        try:
            extract_definitions = ExtractDefinitions.from_dict_list(mock_sources_data)
            message = f"Sources simples chargées avec succès ({len(mock_sources_data)} sources mockées)"
            self.logger.info(message)
            return extract_definitions, message
            
        except Exception as e:
            error_msg = f"Erreur lors du chargement des sources simples: {e}"
            self.logger.error(error_msg)
            return None, error_msg
    
    def _load_complex_sources(self) -> Tuple[Optional[ExtractDefinitions], str]:
        """
        Charge les sources complexes depuis le corpus chiffré.
        
        Returns:
            Tuple contenant les définitions déchiffrées et un message de statut
        """
        self.logger.info("Chargement des sources complexes (corpus chiffré)")
        
        if not self.config.passphrase:
            passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
            if not passphrase:
                error_msg = "Passphrase requise pour accéder au corpus chiffré"
                self.logger.error(error_msg)
                return None, error_msg
        else:
            passphrase = self.config.passphrase
        
        # Charger la clé de chiffrement
        encryption_key = load_encryption_key(passphrase_arg=passphrase)
        if not encryption_key:
            error_msg = "Impossible de dériver la clé de chiffrement"
            self.logger.error(error_msg)
            return None, error_msg
        
        # Chemin vers le fichier chiffré
        encrypted_file_path = DATA_DIR / "extract_sources.json.gz.enc"
        if not encrypted_file_path.exists():
            error_msg = f"Fichier chiffré non trouvé : {encrypted_file_path}"
            self.logger.error(error_msg)
            return None, error_msg
        
        try:
            # Déchiffrer les données
            with open(encrypted_file_path, "rb") as f:
                encrypted_data = f.read()
            
            decrypted_gzipped_data = decrypt_data_with_fernet(encrypted_data, encryption_key)
            if not decrypted_gzipped_data:
                error_msg = "Échec du déchiffrement des données"
                self.logger.error(error_msg)
                return None, error_msg
            
            # Décompresser et parser JSON
            json_data_bytes = gzip.decompress(decrypted_gzipped_data)
            sources_list_dict = json.loads(json_data_bytes.decode('utf-8'))
            
            # Convertir en ExtractDefinitions
            extract_definitions = ExtractDefinitions.from_dict_list(sources_list_dict)
            
            if not extract_definitions or not extract_definitions.sources:
                error_msg = "Aucune source trouvée dans le corpus déchiffré"
                self.logger.warning(error_msg)
                return None, error_msg
            
            # Log anonymisé du succès
            sources_count = len(extract_definitions.sources)
            total_extracts = sum(len(src.extracts) if src.extracts else 0 for src in extract_definitions.sources)
            
            message = f"Corpus chiffré chargé avec succès ({sources_count} sources, {total_extracts} extraits)"
            self.logger.info(message)
            
            # Log détaillé mais anonymisé
            if self.config.anonymize_logs:
                self.logger.info("Sources chargées depuis le corpus politique [DÉTAILS ANONYMISÉS]")
            else:
                for i, source in enumerate(extract_definitions.sources[:3]):  # Limiter aux 3 premières
                    self.logger.debug(f"Source {i+1}: {source.source_name} ({len(source.extracts) if source.extracts else 0} extraits)")
            
            return extract_definitions, message
            
        except Exception as e:
            error_msg = f"Erreur lors du chargement du corpus chiffré: {e}"
            self.logger.error(error_msg)
            return None, error_msg
    
    def select_text_for_analysis(self, extract_definitions: Optional[ExtractDefinitions]) -> Tuple[str, str]:
        """
        Sélectionne un texte pour l'analyse depuis les sources chargées.
        
        Args:
            extract_definitions: Les définitions d'extraits chargées
            
        Returns:
            Tuple[str, str]: Le texte sélectionné et sa description
        """
        if not extract_definitions or not extract_definitions.sources:
            # Texte par défaut de fallback
            fallback_text = (
                "Analyse de fallback : les arguments politiques contiennent souvent des sophismes "
                "qu'il convient d'identifier et d'analyser avec rigueur scientifique."
            )
            return fallback_text, "Texte de fallback (aucune source disponible)"
        
        # Pour les sources simples, prendre le premier extrait disponible
        if self.config.source_type == SourceType.SIMPLE:
            for source in extract_definitions.sources:
                if source.extracts:
                    first_extract = source.extracts[0]
                    if hasattr(first_extract, 'full_text') and first_extract.full_text:
                        self.logger.info(f"Texte sélectionné depuis source simple: {source.source_name}")
                        return first_extract.full_text.strip(), f"Source simple: {source.source_name}"
        
        # Pour les sources complexes, chercher un extrait avec contenu substantiel
        elif self.config.source_type == SourceType.COMPLEX:
            for source in extract_definitions.sources:
                if source.extracts:
                    for extract in source.extracts:
                        if hasattr(extract, 'full_text') and extract.full_text and len(extract.full_text.strip()) > 200:
                            description = f"Source politique: [ANONYMISÉ]" if self.config.anonymize_logs else f"Source: {source.source_name}"
                            self.logger.info(f"Texte sélectionné depuis corpus chiffré: {description}")
                            return extract.full_text.strip(), description
        
        # Si aucun texte substantiel trouvé, utiliser le fallback
        fallback_text = (
            "Analyse de fallback : les arguments politiques contiennent souvent des sophismes "
            "qu'il convient d'identifier et d'analyser avec rigueur scientifique."
        )
        return fallback_text, "Texte de fallback (aucun contenu substantiel trouvé)"
    
    def cleanup_sensitive_data(self):
        """
        Nettoie les données sensibles si le mode auto_cleanup est activé.
        """
        if not self.config.auto_cleanup:
            return
        
        self.logger.info("Nettoyage automatique des données sensibles...")
        
        # Nettoyer les fichiers temporaires
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    self.logger.debug(f"Fichier temporaire supprimé: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Erreur lors de la suppression de {temp_file}: {e}")
        
        self._temp_files.clear()
        
        # Pour les sources complexes, effectuer un nettoyage plus approfondi
        if self.config.source_type == SourceType.COMPLEX:
            # Nettoyer les logs sensibles dans les fichiers de log
            logs_dir = Path("logs")
            if logs_dir.exists():
                sensitive_log_patterns = ["political", "discourse", "speech"]
                for log_file in logs_dir.glob("*.log"):
                    # Optionnel : archiver ou supprimer les logs anciens
                    pass
        
        self.logger.info("Nettoyage automatique terminé")
    
    def __enter__(self):
        """Support du context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Nettoyage automatique à la sortie du context manager."""
        self.cleanup_sensitive_data()

def create_source_manager(source_type: str, passphrase: Optional[str] = None, 
                         anonymize_logs: bool = True, auto_cleanup: bool = True) -> SourceManager:
    """
    Factory function pour créer un SourceManager configuré.
    
    Args:
        source_type: Type de source ("simple" ou "complex")
        passphrase: Phrase secrète pour le déchiffrement (optionnel)
        anonymize_logs: Activer l'anonymisation des logs
        auto_cleanup: Activer le nettoyage automatique
        
    Returns:
        SourceManager configuré
    """
    try:
        source_enum = SourceType(source_type.lower())
    except ValueError:
        raise ValueError(f"Type de source non supporté: {source_type}. Utilisez 'simple' ou 'complex'.")
    
    config = SourceConfig(
        source_type=source_enum,
        passphrase=passphrase,
        anonymize_logs=anonymize_logs,
        auto_cleanup=auto_cleanup
    )
    
    return SourceManager(config)