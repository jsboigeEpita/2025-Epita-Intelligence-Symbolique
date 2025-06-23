#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de gestion des workflows avec déchiffrement automatique
===========================================================

Composant réutilisable pour :
- Déchiffrement automatique de corpus
- Gestion des clés de chiffrement
- Pipeline de traitement des textes chiffrés
- Validation de l'intégrité des données

Intégré dans l'architecture modulaire pour éviter la duplication de code.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from cryptography.fernet import Fernet
import base64
import hashlib

from argumentation_analysis.core.io_manager import load_extract_definitions
from argumentation_analysis.config.settings import settings

@dataclass
class CorpusDecryptionResult:
    """Résultat du déchiffrement de corpus."""
    success: bool
    loaded_files: List[Dict[str, Any]]
    errors: List[str]
    total_definitions: int
    processing_time: float


class CryptoWorkflowManager:
    """Gestionnaire de workflows avec déchiffrement automatique."""
    
    def __init__(self, passphrase: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.CryptoWorkflowManager")
        
        passphrase_to_use = passphrase
        if not passphrase_to_use and settings.passphrase:
            passphrase_to_use = settings.passphrase.get_secret_value()
            
        if not passphrase_to_use:
            self.logger.warning("Aucune passphrase fournie ou configurée dans les settings. Le déchiffrement échouera probablement.")
            
        self.passphrase = passphrase_to_use
        self._encryption_key = None
        
    def derive_encryption_key(self) -> bytes:
        """Dérive une clé de chiffrement depuis la passphrase."""
        if self._encryption_key is None:
            if not self.passphrase:
                raise ValueError("Impossible de dériver la clé: aucune passphrase n'est définie.")
            # Dérivation compatible avec le système existant
            key_material = self.passphrase.encode('utf-8')
            key_hash = hashlib.sha256(key_material).digest()
            self._encryption_key = base64.urlsafe_b64encode(key_hash)
        return self._encryption_key
    
    async def load_encrypted_corpus(self, corpus_files: List[str]) -> CorpusDecryptionResult:
        """
        Charge et déchiffre une liste de fichiers de corpus.
        
        Args:
            corpus_files: Liste des chemins vers les fichiers chiffrés
            
        Returns:
            Résultat du déchiffrement avec métadonnées
        """
        import time
        start_time = time.time()
        
        result = CorpusDecryptionResult(
            success=True,
            loaded_files=[],
            errors=[],
            total_definitions=0,
            processing_time=0.0
        )
        
        try:
            encryption_key = self.derive_encryption_key()
            self.logger.info(f"🔓 Déchiffrement de {len(corpus_files)} fichiers de corpus")
            
            for corpus_file in corpus_files:
                corpus_path = Path(corpus_file)
                
                if not corpus_path.exists():
                    error_msg = f"Fichier corpus non trouvé: {corpus_path}"
                    self.logger.warning(error_msg)
                    result.errors.append(error_msg)
                    continue
                
                try:
                    self.logger.debug(f"📂 Déchiffrement: {corpus_path}")
                    
                    # Chargement et déchiffrement
                    definitions = load_extract_definitions(
                        config_file=corpus_path,
                        b64_derived_key=encryption_key,
                        fallback_definitions=[]
                    )
                    
                    if definitions:
                        file_info = {
                            "file": str(corpus_path),
                            "definitions_count": len(definitions),
                            "definitions": definitions,
                            "status": "success"
                        }
                        result.loaded_files.append(file_info)
                        result.total_definitions += len(definitions)
                        
                        self.logger.info(f"✅ {corpus_path.name}: {len(definitions)} définitions")
                    else:
                        error_msg = f"Échec du déchiffrement: {corpus_path}"
                        result.errors.append(error_msg)
                        self.logger.error(error_msg)
                        
                except Exception as e:
                    error_msg = f"Erreur traitement {corpus_path}: {e}"
                    result.errors.append(error_msg)
                    self.logger.error(error_msg)
            
            result.success = len(result.loaded_files) > 0
            result.processing_time = time.time() - start_time
            
            self.logger.info(f"🎯 Déchiffrement terminé: {len(result.loaded_files)} fichiers, {result.total_definitions} définitions")
            
        except ImportError as e:
            error_msg = f"Modules de déchiffrement non disponibles: {e}"
            self.logger.error(error_msg)
            result.success = False
            result.errors.append(error_msg)
            result.processing_time = time.time() - start_time
            
        except Exception as e:
            error_msg = f"Erreur générale de déchiffrement: {e}"
            self.logger.error(error_msg, exc_info=True)
            result.success = False
            result.errors.append(error_msg)
            result.processing_time = time.time() - start_time
        
        return result
    
    def encrypt_content(self, content: str) -> bytes:
        """Chiffre du contenu textuel."""
        try:
            fernet = Fernet(self.derive_encryption_key())
            return fernet.encrypt(content.encode('utf-8'))
        except Exception as e:
            self.logger.error(f"Erreur chiffrement: {e}")
            raise
    
    def decrypt_content(self, encrypted_content: bytes) -> str:
        """Déchiffre du contenu textuel."""
        try:
            fernet = Fernet(self.derive_encryption_key())
            return fernet.decrypt(encrypted_content).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Erreur déchiffrement: {e}")
            raise
    
    def validate_corpus_integrity(self, corpus_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valide l'intégrité des données de corpus déchiffrées."""
        errors = []
        
        if not corpus_data.get("loaded_files"):
            errors.append("Aucun fichier chargé")
            return False, errors
        
        for file_data in corpus_data["loaded_files"]:
            if not file_data.get("definitions"):
                errors.append(f"Fichier sans définitions: {file_data.get('file', 'inconnu')}")
            
            for definition in file_data.get("definitions", []):
                if not definition.get("content"):
                    errors.append(f"Définition sans contenu dans {file_data.get('file', 'inconnu')}")
        
        return len(errors) == 0, errors


# Factory function pour faciliter l'utilisation
def create_crypto_manager(passphrase: Optional[str] = None) -> CryptoWorkflowManager:
    """Crée un gestionnaire de workflow crypto."""
    return CryptoWorkflowManager(passphrase)