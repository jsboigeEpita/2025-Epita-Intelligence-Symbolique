#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de gestion unifiée des sources - Composant Core Réutilisable.

Ce module centralise et unifie l'accès à toutes les sources de données du système :
- Sources simples (démo/test) 
- Corpus complexe chiffré (recherche)
- Fichiers .enc personnalisés
- Fichiers texte locaux
- Texte libre (saisie directe)

Intégration harmonieuse avec l'écosystème core existant et les composants refactorisés.
"""

import os
import sys
import json
import gzip
import getpass
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
from contextlib import contextmanager

# Imports core existants
from argumentation_analysis.core.source_manager import SourceManager, SourceConfig, SourceType as LegacySourceType
from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key, load_encryption_key
from argumentation_analysis.ui.file_operations import load_extract_definitions
from argumentation_analysis.models.extract_definition import ExtractDefinitions

logger = logging.getLogger(__name__)

class UnifiedSourceType(Enum):
    """Types de sources unifiés - Extension du système existant."""
    SIMPLE = "simple"
    COMPLEX = "complex"
    ENC_FILE = "enc_file"
    TEXT_FILE = "text_file"
    FREE_TEXT = "free_text"

@dataclass
class UnifiedSourceConfig:
    """Configuration unifiée pour l'accès aux sources - Compatible avec SourceConfig existant."""
    source_type: UnifiedSourceType
    passphrase: Optional[str] = None
    anonymize_logs: bool = True
    auto_cleanup: bool = True
    enc_file_path: Optional[str] = None
    text_file_path: Optional[str] = None
    free_text_content: Optional[str] = None
    source_index: int = 0
    interactive_mode: bool = False
    auto_passphrase: bool = True
    
    # Compatibilité avec SourceConfig existant
    @classmethod
    def from_legacy_config(cls, legacy_config: SourceConfig) -> 'UnifiedSourceConfig':
        """Convertit une SourceConfig existante vers UnifiedSourceConfig."""
        return cls(
            source_type=UnifiedSourceType(legacy_config.source_type.value),
            passphrase=legacy_config.passphrase,
            anonymize_logs=legacy_config.anonymize_logs,
            auto_cleanup=legacy_config.auto_cleanup
        )
    
    def to_legacy_config(self) -> SourceConfig:
        """Convertit vers SourceConfig pour compatibilité."""
        legacy_type = LegacySourceType(self.source_type.value) if self.source_type.value in ['simple', 'complex'] else LegacySourceType.SIMPLE
        return SourceConfig(
            source_type=legacy_type,
            passphrase=self.passphrase,
            anonymize_logs=self.anonymize_logs,
            auto_cleanup=self.auto_cleanup
        )

class UnifiedSourceManager:
    """
    Gestionnaire unifié et étendu des sources - Composant Core Réutilisable.
    
    Étend les capacités du SourceManager existant avec :
    - Support des fichiers .enc personnalisés
    - Support des fichiers texte locaux
    - Support du texte libre
    - Interface interactive optionnelle
    - API programmable complète
    - Intégration harmonieuse avec l'écosystème refactorisé
    """
    
    def __init__(self, config: UnifiedSourceConfig):
        """
        Initialise le gestionnaire unifié de sources.
        
        Args:
            config: Configuration unifiée pour l'accès aux sources
        """
        self.config = config
        self.logger = self._setup_logging()
        self._temp_files: List[Path] = []
        self._cached_sources: Dict[str, Any] = {}
        
        # Intégration avec le SourceManager existant pour compatibilité
        self._legacy_manager: Optional[SourceManager] = None
        if config.source_type in [UnifiedSourceType.SIMPLE, UnifiedSourceType.COMPLEX]:
            self._legacy_manager = SourceManager(config.to_legacy_config())
    
    def _setup_logging(self) -> logging.Logger:
        """Configure le logging avec anonymisation si nécessaire."""
        source_logger = logging.getLogger(f"{__name__}.{self.config.source_type.value}")
        
        if self.config.anonymize_logs and self.config.source_type in [UnifiedSourceType.COMPLEX, UnifiedSourceType.ENC_FILE]:
            # Réutiliser le filtre d'anonymisation existant
            class AnonymizeFilter(logging.Filter):
                def filter(self, record):
                    if hasattr(record, 'msg') and isinstance(record.msg, str):
                        msg = record.msg
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
    
    def _get_passphrase(self) -> str:
        """Récupère la phrase secrète depuis l'environnement ou la demande à l'utilisateur."""
        if self.config.passphrase:
            return self.config.passphrase
            
        if self.config.auto_passphrase:
            env_passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
            if env_passphrase:
                self.logger.info("Phrase secrète récupérée depuis l'environnement.")
                return env_passphrase
        
        if not self.config.interactive_mode:
            raise ValueError("Aucune phrase secrète fournie et mode non-interactif activé")
        
        try:
            passphrase = getpass.getpass("Veuillez entrer la phrase secrète pour déchiffrer les sources : ")
            if not passphrase:
                raise ValueError("Aucune phrase secrète fournie")
            return passphrase
        except Exception as e:
            self.logger.error(f"Impossible de récupérer la phrase secrète: {e}")
            raise
    
    def load_sources(self) -> Tuple[Optional[ExtractDefinitions], str]:
        """
        Charge les sources selon la configuration unifiée.
        
        Returns:
            Tuple[Optional[ExtractDefinitions], str]: Les définitions et un message de statut
        """
        source_type = self.config.source_type
        
        if source_type == UnifiedSourceType.SIMPLE:
            return self._load_simple_sources()
        elif source_type == UnifiedSourceType.COMPLEX:
            return self._load_complex_sources()
        elif source_type == UnifiedSourceType.ENC_FILE:
            return self._load_enc_file_sources()
        elif source_type == UnifiedSourceType.TEXT_FILE:
            return self._load_text_file_sources()
        elif source_type == UnifiedSourceType.FREE_TEXT:
            return self._load_free_text_sources()
        else:
            return None, f"Type de source non supporté: {source_type}"
    
    def _load_simple_sources(self) -> Tuple[Optional[ExtractDefinitions], str]:
        """Délègue au SourceManager existant pour les sources simples."""
        if self._legacy_manager:
            return self._legacy_manager.load_sources()
        return None, "Erreur: SourceManager legacy non initialisé"
    
    def _load_complex_sources(self) -> Tuple[Optional[ExtractDefinitions], str]:
        """Délègue au SourceManager existant pour les sources complexes."""
        if self._legacy_manager:
            return self._legacy_manager.load_sources()
        return None, "Erreur: SourceManager legacy non initialisé"
    
    def _load_enc_file_sources(self) -> Tuple[Optional[ExtractDefinitions], str]:
        """Charge un fichier .enc personnalisé."""
        if not self.config.enc_file_path:
            return None, "Chemin de fichier .enc requis"
        
        enc_path = Path(self.config.enc_file_path)
        if not enc_path.exists():
            return None, f"Fichier .enc non trouvé: {enc_path}"
        
        try:
            passphrase = self._get_passphrase()
            encryption_key = derive_encryption_key(passphrase)
            if not encryption_key:
                return None, "Impossible de dériver la clé de chiffrement"
            
            # Charger les définitions
            definitions = load_extract_definitions(config_file=enc_path, b64_derived_key=encryption_key)
            if not definitions:
                return None, "Impossible de charger les définitions depuis le fichier .enc"
            
            # Convertir en ExtractDefinitions si nécessaire
            if isinstance(definitions, list):
                extract_definitions = ExtractDefinitions.from_dict_list(definitions)
            else:
                extract_definitions = definitions
            
            message = f"Fichier .enc chargé avec succès: {enc_path.name}"
            self.logger.info(message)
            return extract_definitions, message
            
        except Exception as e:
            error_msg = f"Erreur chargement fichier .enc: {e}"
            self.logger.error(error_msg)
            return None, error_msg
    
    def _load_text_file_sources(self) -> Tuple[Optional[ExtractDefinitions], str]:
        """Charge un fichier texte local."""
        if not self.config.text_file_path:
            return None, "Chemin de fichier texte requis"
        
        text_path = Path(self.config.text_file_path)
        if not text_path.exists():
            return None, f"Fichier texte non trouvé: {text_path}"
        
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            if not text_content.strip():
                return None, "Le fichier texte est vide"
            
            # Créer une ExtractDefinition pour le fichier texte
            source_data = [{
                "source_name": f"Fichier local: {text_path.name}",
                "source_type": "text_file",
                "schema": "local_file",
                "host_parts": ["local"],
                "path": str(text_path),
                "full_text": text_content,
                "extracts": [{
                    "extract_name": f"Contenu de {text_path.name}",
                    "start_marker": "",
                    "end_marker": "",
                    "full_text": text_content
                }]
            }]
            
            extract_definitions = ExtractDefinitions.from_dict_list(source_data)
            message = f"Fichier texte chargé avec succès: {text_path.name} ({len(text_content)} caractères)"
            self.logger.info(message)
            return extract_definitions, message
            
        except Exception as e:
            error_msg = f"Erreur chargement fichier texte: {e}"
            self.logger.error(error_msg)
            return None, error_msg
    
    def _load_free_text_sources(self) -> Tuple[Optional[ExtractDefinitions], str]:
        """Charge du texte libre fourni."""
        if not self.config.free_text_content:
            return None, "Contenu de texte libre requis"
        
        text_content = self.config.free_text_content.strip()
        if not text_content:
            return None, "Le texte libre est vide"
        
        try:
            # Créer une ExtractDefinition pour le texte libre
            source_data = [{
                "source_name": "Texte libre",
                "source_type": "free_text",
                "schema": "user_input",
                "host_parts": ["user"],
                "path": "/user/free_text",
                "full_text": text_content,
                "extracts": [{
                    "extract_name": "Saisie utilisateur",
                    "start_marker": "",
                    "end_marker": "",
                    "full_text": text_content
                }]
            }]
            
            extract_definitions = ExtractDefinitions.from_dict_list(source_data)
            message = f"Texte libre chargé avec succès ({len(text_content)} caractères)"
            self.logger.info(message)
            return extract_definitions, message
            
        except Exception as e:
            error_msg = f"Erreur chargement texte libre: {e}"
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
            fallback_text = (
                "Analyse de fallback : les arguments politiques contiennent souvent des sophismes "
                "qu'il convient d'identifier et d'analyser avec rigueur scientifique."
            )
            return fallback_text, "Texte de fallback (aucune source disponible)"
        
        # Pour les sources simples et complexes, déléguer au SourceManager existant
        if self.config.source_type in [UnifiedSourceType.SIMPLE, UnifiedSourceType.COMPLEX] and self._legacy_manager:
            return self._legacy_manager.select_text_for_analysis(extract_definitions)
        
        # Pour les nouveaux types de sources, sélectionner le contenu approprié
        for source in extract_definitions.sources:
            if hasattr(source, 'full_text') and source.full_text:
                description = f"Source {self.config.source_type.value}: {source.source_name}"
                self.logger.info(f"Texte sélectionné: {description}")
                return source.full_text.strip(), description
            
            if source.extracts:
                for extract in source.extracts:
                    if hasattr(extract, 'full_text') and extract.full_text:
                        description = f"Source {self.config.source_type.value}: {extract.extract_name}"
                        self.logger.info(f"Texte sélectionné: {description}")
                        return extract.full_text.strip(), description
        
        # Fallback si aucun texte trouvé
        fallback_text = (
            "Analyse de fallback : les arguments politiques contiennent souvent des sophismes "
            "qu'il convient d'identifier et d'analyser avec rigueur scientifique."
        )
        return fallback_text, "Texte de fallback (aucun contenu trouvé)"
    
    def list_available_sources(self) -> Dict[str, List[str]]:
        """
        Liste toutes les sources disponibles sans les charger complètement.
        
        Returns:
            Dict contenant les listes de sources par type
        """
        sources = {
            "simple": ["Sources de démonstration/test"],
            "complex": [],
            "enc_files": [],
            "text_files": []
        }
        
        # Sources complexes (nécessite authentification)
        try:
            passphrase = self.config.passphrase or os.getenv("TEXT_CONFIG_PASSPHRASE")
            if passphrase:
                config = UnifiedSourceConfig(
                    source_type=UnifiedSourceType.COMPLEX,
                    passphrase=passphrase,
                    anonymize_logs=True,
                    auto_cleanup=True
                )
                temp_manager = UnifiedSourceManager(config)
                extract_definitions, _ = temp_manager.load_sources()
                if extract_definitions:
                    for source in extract_definitions.sources:
                        name = getattr(source, 'source_name', 'Source inconnue')
                        sources["complex"].append(name)
        except Exception as e:
            self.logger.debug(f"Impossible de lister les sources complexes: {e}")
        
        # Fichiers .enc dans le projet
        project_root = Path(__file__).resolve().parent.parent.parent
        for enc_file in project_root.glob("**/*.enc"):
            if enc_file.is_file():
                sources["enc_files"].append(str(enc_file.relative_to(project_root)))
        
        return sources
    
    def cleanup_sensitive_data(self):
        """Nettoie les données sensibles si le mode auto_cleanup est activé."""
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
        
        # Déléguer au SourceManager existant si applicable
        if self._legacy_manager:
            self._legacy_manager.cleanup_sensitive_data()
        
        self.logger.info("Nettoyage automatique terminé")
    
    def __enter__(self):
        """Support du context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Nettoyage automatique à la sortie du context manager."""
        self.cleanup_sensitive_data()

# Factory functions pour compatibilité et nouvelles fonctionnalités

def create_unified_source_manager(
    source_type: str,
    passphrase: Optional[str] = None,
    anonymize_logs: bool = True,
    auto_cleanup: bool = True,
    enc_file_path: Optional[str] = None,
    text_file_path: Optional[str] = None,
    free_text_content: Optional[str] = None,
    source_index: int = 0,
    interactive_mode: bool = False,
    auto_passphrase: bool = True
) -> UnifiedSourceManager:
    """
    Factory function pour créer un UnifiedSourceManager configuré.
    
    Args:
        source_type: Type de source ("simple", "complex", "enc_file", "text_file", "free_text")
        passphrase: Phrase secrète pour le déchiffrement (optionnel)
        anonymize_logs: Activer l'anonymisation des logs
        auto_cleanup: Activer le nettoyage automatique
        enc_file_path: Chemin vers fichier .enc (si source_type="enc_file")
        text_file_path: Chemin vers fichier texte (si source_type="text_file")
        free_text_content: Contenu texte libre (si source_type="free_text")
        source_index: Index de la source à sélectionner
        interactive_mode: Autoriser les interactions utilisateur
        auto_passphrase: Récupération automatique depuis l'environnement
        
    Returns:
        UnifiedSourceManager configuré
    """
    try:
        source_enum = UnifiedSourceType(source_type.lower())
    except ValueError:
        supported_types = [t.value for t in UnifiedSourceType]
        raise ValueError(f"Type de source non supporté: {source_type}. Utilisez: {supported_types}")
    
    config = UnifiedSourceConfig(
        source_type=source_enum,
        passphrase=passphrase,
        anonymize_logs=anonymize_logs,
        auto_cleanup=auto_cleanup,
        enc_file_path=enc_file_path,
        text_file_path=text_file_path,
        free_text_content=free_text_content,
        source_index=source_index,
        interactive_mode=interactive_mode,
        auto_passphrase=auto_passphrase
    )
    
    return UnifiedSourceManager(config)

# Interface de compatibilité avec l'API existante
def create_source_manager(source_type: str, passphrase: Optional[str] = None, 
                         anonymize_logs: bool = True, auto_cleanup: bool = True) -> UnifiedSourceManager:
    """
    Factory function pour compatibilité avec l'API existante.
    Délègue vers create_unified_source_manager.
    """
    return create_unified_source_manager(
        source_type=source_type,
        passphrase=passphrase,
        anonymize_logs=anonymize_logs,
        auto_cleanup=auto_cleanup,
        interactive_mode=False,
        auto_passphrase=True
    )

# Interface interactive pour les scripts

class InteractiveSourceSelector:
    """
    Interface interactive pour la sélection de sources.
    Composant utilisé par les scripts CLI.
    """
    
    def __init__(self, passphrase: str = None, auto_passphrase: bool = True):
        """
        Initialise le sélecteur interactif.
        
        Args:
            passphrase: Phrase secrète pour déchiffrement (optionnel)
            auto_passphrase: Si True, récupère automatiquement depuis l'environnement
        """
        self.passphrase = passphrase
        self.auto_passphrase = auto_passphrase
        self._cached_sources = {}
    
    def select_source_interactive(self) -> Tuple[str, str, str]:
        """
        Interface interactive pour sélectionner une source.
        
        Returns:
            Tuple[str, str, str]: (selected_text, description, source_type)
        """
        print("\n" + "="*60)
        print("           SÉLECTION DE SOURCE POUR ANALYSE")
        print("="*60)
        print("1. 📚 Sources simples (démo/test)")
        print("2. 🔒 Corpus complexe chiffré (recherche)")
        print("3. 📁 Fichier .enc personnalisé")
        print("4. ✏️  Texte libre (saisie directe)")
        print("5. 📄 Fichier texte local")
        print("-"*60)
        
        while True:
            try:
                choice = input("Votre choix (1-5): ").strip()
                
                if choice == "1":
                    return self._load_simple_source()
                elif choice == "2":
                    return self._load_complex_source()
                elif choice == "3":
                    return self._load_custom_enc_file()
                elif choice == "4":
                    return self._load_free_text()
                elif choice == "5":
                    return self._load_local_file()
                else:
                    print("❌ Choix invalide. Veuillez entrer un nombre entre 1 et 5.")
                    continue
            except KeyboardInterrupt:
                print("\n❌ Sélection annulée par l'utilisateur.")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Erreur lors de la sélection: {e}")
                print(f"❌ Erreur: {e}")
                continue
    
    def load_source_batch(self, 
                         source_type: str, 
                         enc_file: str = None, 
                         text_file: str = None,
                         source_index: int = 0,
                         free_text: str = None) -> Tuple[str, str, str]:
        """
        Charge une source en mode batch (non-interactif).
        
        Args:
            source_type: "simple", "complex", "enc_file", "text_file", "free_text"
            enc_file: Chemin vers fichier .enc (si source_type="enc_file")
            text_file: Chemin vers fichier texte (si source_type="text_file")
            source_index: Index de la source à sélectionner (pour complex)
            free_text: Contenu texte libre (si source_type="free_text")
            
        Returns:
            Tuple[str, str, str]: (selected_text, description, source_type)
        """
        logger.info(f"Chargement en mode batch: source_type={source_type}")
        
        with create_unified_source_manager(
            source_type=source_type,
            passphrase=self.passphrase,
            enc_file_path=enc_file,
            text_file_path=text_file,
            free_text_content=free_text,
            source_index=source_index,
            interactive_mode=False,
            auto_passphrase=self.auto_passphrase
        ) as manager:
            
            extract_definitions, status = manager.load_sources()
            if not extract_definitions:
                raise Exception(f"Échec chargement source: {status}")
            
            text, description = manager.select_text_for_analysis(extract_definitions)
            return text, description, source_type
    
    def _load_simple_source(self) -> Tuple[str, str, str]:
        """Charge les sources simples de démonstration."""
        return self.load_source_batch("simple")
    
    def _load_complex_source(self) -> Tuple[str, str, str]:
        """Charge les sources complexes chiffrées avec sélection interactive."""
        logger.info("Chargement des sources complexes chiffrées...")
        
        with create_unified_source_manager(
            source_type="complex",
            passphrase=self.passphrase,
            interactive_mode=True,
            auto_passphrase=self.auto_passphrase
        ) as manager:
            
            extract_definitions, status = manager.load_sources()
            if not extract_definitions:
                raise Exception(f"Échec chargement sources complexes: {status}")
            
            # Interface de sélection interactive
            print(f"\n📚 {len(extract_definitions.sources)} SOURCES DISPONIBLES:")
            print("-" * 50)
            for i, source in enumerate(extract_definitions.sources):
                name = getattr(source, 'source_name', f'Source {i+1}')
                extracts_count = len(getattr(source, 'extracts', []))
                content_type = getattr(source, 'content_type', 'Inconnu')
                print(f"{i+1:2d}. {name}")
                print(f"     📊 {extracts_count} extraits - Type: {content_type}")
            
            print("-" * 50)
            
            while True:
                try:
                    choice = input(f"Sélectionnez une source (1-{len(extract_definitions.sources)}): ").strip()
                    if choice.lower() in ['q', 'quit', 'exit']:
                        raise KeyboardInterrupt
                    
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(extract_definitions.sources):
                        selected_source = extract_definitions.sources[choice_idx]
                        # Créer une ExtractDefinitions avec seulement la source sélectionnée
                        selected_definitions = ExtractDefinitions(sources=[selected_source])
                        text, desc = manager.select_text_for_analysis(selected_definitions)
                        logger.info(f"✅ Source complexe sélectionnée: {desc}")
                        return text, desc, "complex"
                    else:
                        print(f"❌ Choix invalide. Entrez un nombre entre 1 et {len(extract_definitions.sources)}.")
                except ValueError:
                    print("❌ Veuillez entrer un nombre valide.")
                except KeyboardInterrupt:
                    raise
    
    def _load_custom_enc_file(self) -> Tuple[str, str, str]:
        """Charge un fichier .enc personnalisé avec sélection interactive."""
        print("\n📁 CHARGEMENT FICHIER .ENC PERSONNALISÉ")
        print("-" * 40)
        
        while True:
            enc_file_path = input("Chemin vers le fichier .enc: ").strip()
            if not enc_file_path:
                print("❌ Veuillez entrer un chemin valide.")
                continue
            
            enc_path = Path(enc_file_path)
            if not enc_path.exists():
                print(f"❌ Fichier non trouvé: {enc_path}")
                continue
            
            return self.load_source_batch("enc_file", enc_file=str(enc_path))
    
    def _load_free_text(self) -> Tuple[str, str, str]:
        """Permet la saisie directe de texte libre."""
        print("\n✏️  SAISIE DE TEXTE LIBRE")
        print("-" * 30)
        print("Entrez votre texte (terminez par une ligne vide):")
        
        lines = []
        while True:
            try:
                line = input()
                if not line.strip():  # Ligne vide = fin de saisie
                    break
                lines.append(line)
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n❌ Saisie annulée.")
                raise
        
        if not lines:
            raise ValueError("Aucun texte saisi")
        
        free_text = "\n".join(lines)
        return self.load_source_batch("free_text", free_text=free_text)
    
    def _load_local_file(self) -> Tuple[str, str, str]:
        """Charge un fichier texte local avec sélection interactive."""
        print("\n📄 CHARGEMENT FICHIER TEXTE LOCAL")
        print("-" * 35)
        
        while True:
            file_path = input("Chemin vers le fichier texte: ").strip()
            if not file_path:
                print("❌ Veuillez entrer un chemin valide.")
                continue
            
            path = Path(file_path)
            if not path.exists():
                print(f"❌ Fichier non trouvé: {path}")
                continue
            
            return self.load_source_batch("text_file", text_file=str(path))
    
    def list_available_sources(self) -> Dict[str, List[str]]:
        """Liste toutes les sources disponibles sans les charger complètement."""
        with create_unified_source_manager(
            source_type="simple",  # Type par défaut pour le listing
            passphrase=self.passphrase,
            auto_passphrase=self.auto_passphrase
        ) as manager:
            return manager.list_available_sources()