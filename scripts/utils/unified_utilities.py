import argumentation_analysis.core.environment

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Système d'Utilitaires Unifiés
=============================

Consolide toutes les opérations utilitaires sur le corpus chiffré :
- Intégration de nouvelles sources au corpus
- Déchiffrement d'extraits spécifiques  
- Listing sécurisé des métadonnées d'extraits
- Gestion unifiée du chiffrement/déchiffrement
- Validation et opérations de maintenance

Fichiers sources consolidés :
- scripts/data_processing/integrate_new_source_to_corpus.py
- scripts/utils/decrypt_specific_extract.py
- scripts/utils/list_encrypted_extracts.py
"""

import os
import sys
import json
import gzip
import logging
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

# Configuration de l'encodage pour Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("UnifiedUtilities")


class UtilityMode(Enum):
    """Modes d'opération des utilitaires."""

    LIST = "list"  # Lister les extraits disponibles
    EXTRACT = "extract"  # Extraire un extrait spécifique
    INTEGRATE = "integrate"  # Intégrer une nouvelle source
    VALIDATE = "validate"  # Valider l'intégrité du corpus
    MAINTENANCE = "maintenance"  # Opérations de maintenance
    INFO = "info"  # Informations générales sur le corpus


class OutputFormat(Enum):
    """Formats de sortie disponibles."""

    TEXT = "text"  # Sortie texte formatée
    JSON = "json"  # Sortie JSON structurée
    CSV = "csv"  # Sortie CSV pour tableur
    HTML = "html"  # Sortie HTML avec CSS


@dataclass
class UtilityConfiguration:
    """Configuration pour les utilitaires unifiés."""

    mode: UtilityMode = UtilityMode.LIST
    passphrase: Optional[str] = None
    output_format: OutputFormat = OutputFormat.TEXT
    output_file: Optional[str] = None
    detailed: bool = False
    show_content: bool = False
    dry_run: bool = False
    backup_before_modify: bool = True
    validate_after_modify: bool = True
    secure_mode: bool = True
    timeout_seconds: int = 300


@dataclass
class CorpusInfo:
    """Informations sur le corpus."""

    total_sources: int
    total_extracts: int
    total_content_length: int
    file_size_bytes: int
    last_modified: str
    encryption_status: str
    sources_summary: List[Dict[str, Any]]


@dataclass
class ExtractInfo:
    """Informations détaillées sur un extrait."""

    source_info: Dict[str, Any]
    extract_info: Dict[str, Any]
    content: str
    content_length: int
    metadata: Dict[str, Any]


class UnifiedCorpusManager:
    """Gestionnaire unifié pour toutes les opérations sur le corpus chiffré."""

    def __init__(self, config: UtilityConfiguration = None):
        """Initialise le gestionnaire avec une configuration."""
        self.config = config or UtilityConfiguration()
        self.logger = logging.getLogger(__name__)

        # Détection automatique de la passphrase
        self.passphrase = self._get_passphrase()

        # Chemins des fichiers
        self.data_dir = self._get_data_dir()
        self.encrypted_file_path = self.data_dir / "extract_sources.json.gz.enc"

        # Cache pour éviter de multiples déchiffrements
        self._corpus_cache = None
        self._cache_timestamp = None

    def _get_passphrase(self) -> str:
        """Obtient la passphrase de déchiffrement."""
        passphrase = (
            self.config.passphrase
            or os.getenv("TEXT_CONFIG_PASSPHRASE")
            or "Propaganda"  # Fallback par défaut
        )

        if not passphrase:
            raise ValueError("Passphrase requise pour accéder au corpus chiffré")

        return passphrase

    def _get_data_dir(self) -> Path:
        """Obtient le répertoire de données."""
        try:
            from argumentation_analysis.paths import DATA_DIR

            return DATA_DIR
        except ImportError:
            # Fallback si le module n'est pas disponible
            return PROJECT_ROOT / "data"

    def _load_crypto_utils(self):
        """Charge les utilitaires de chiffrement avec fallback."""
        try:
            from argumentation_analysis.utils.core_utils.crypto_utils import (
                load_encryption_key,
                decrypt_data_with_fernet,
                encrypt_data_with_fernet,
            )

            return (
                load_encryption_key,
                decrypt_data_with_fernet,
                encrypt_data_with_fernet,
            )
        except ImportError:
            self.logger.warning(
                "Modules de chiffrement non disponibles - utilisation de mocks"
            )

            # Mocks pour les tests
            def mock_load_key(passphrase_arg=None):
                return b"mock_key_for_testing_purposes_32b"

            def mock_decrypt(data, key):
                # Mock simple pour les tests
                try:
                    return gzip.compress(json.dumps([]).encode("utf-8"))
                except:
                    return None

            def mock_encrypt(data, key):
                return data  # Mock simple

            return mock_load_key, mock_decrypt, mock_encrypt

    def load_corpus(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Charge et déchiffre le corpus complet.

        Args:
            use_cache: Utiliser le cache si disponible

        Returns:
            List[Dict]: Données déchiffrées du corpus
        """
        # Vérifier le cache
        if use_cache and self._corpus_cache is not None:
            if self._cache_timestamp:
                file_mtime = self.encrypted_file_path.stat().st_mtime
                if file_mtime <= self._cache_timestamp:
                    self.logger.debug("Utilisation du cache corpus")
                    return self._corpus_cache

        self.logger.info("Chargement et déchiffrement du corpus...")

        # Charger les utilitaires de chiffrement
        load_encryption_key, decrypt_data_with_fernet, _ = self._load_crypto_utils()

        # Charger la clé de chiffrement
        encryption_key = load_encryption_key(passphrase_arg=self.passphrase)
        if not encryption_key:
            raise ValueError("Impossible de dériver la clé de chiffrement")

        # Vérifier l'existence du fichier chiffré
        if not self.encrypted_file_path.exists():
            self.logger.warning("Fichier chiffré non trouvé - corpus vide")
            return []

        try:
            # Déchiffrer les données
            with open(self.encrypted_file_path, "rb") as f:
                encrypted_data = f.read()

            decrypted_gzipped_data = decrypt_data_with_fernet(
                encrypted_data, encryption_key
            )
            if not decrypted_gzipped_data:
                raise ValueError("Échec du déchiffrement des données")

            # Décompresser et parser JSON
            json_data_bytes = gzip.decompress(decrypted_gzipped_data)
            sources_list = json.loads(json_data_bytes.decode("utf-8"))

            # Mettre en cache
            self._corpus_cache = sources_list
            self._cache_timestamp = self.encrypted_file_path.stat().st_mtime

            self.logger.info(f"Corpus chargé: {len(sources_list)} sources")
            return sources_list

        except Exception as e:
            self.logger.error(f"Erreur lors du chargement: {e}")
            raise

    def save_corpus(
        self, corpus_data: List[Dict[str, Any]], backup: bool = None
    ) -> bool:
        """
        Sauvegarde le corpus en format chiffré.

        Args:
            corpus_data: Données du corpus à sauvegarder
            backup: Créer une sauvegarde avant modification

        Returns:
            bool: True si sauvegarde réussie
        """
        if backup is None:
            backup = self.config.backup_before_modify

        self.logger.info("Sauvegarde du corpus chiffré...")

        try:
            # Créer une sauvegarde si demandé
            if backup and self.encrypted_file_path.exists():
                backup_path = self.encrypted_file_path.with_suffix(
                    f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.enc"
                )
                import shutil

                shutil.copy2(self.encrypted_file_path, backup_path)
                self.logger.info(f"Sauvegarde créée: {backup_path}")

            # Charger les utilitaires de chiffrement
            load_encryption_key, _, encrypt_data_with_fernet = self._load_crypto_utils()

            # Sérialiser en JSON
            json_content = json.dumps(corpus_data, ensure_ascii=False, indent=2)
            json_bytes = json_content.encode("utf-8")

            # Compresser
            compressed_bytes = gzip.compress(json_bytes)
            self.logger.info(f"Données compressées: {len(compressed_bytes)} bytes")

            # Chiffrer
            encryption_key = load_encryption_key(passphrase_arg=self.passphrase)
            encrypted_data = encrypt_data_with_fernet(compressed_bytes, encryption_key)

            if not encrypted_data:
                raise ValueError("Échec du chiffrement")

            # Créer le répertoire de destination si nécessaire
            self.encrypted_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Sauvegarder
            if not self.config.dry_run:
                with open(self.encrypted_file_path, "wb") as f:
                    f.write(encrypted_data)

                # Invalider le cache
                self._corpus_cache = None
                self._cache_timestamp = None

                self.logger.info(f"Corpus sauvegardé: {self.encrypted_file_path}")
            else:
                self.logger.info("[DRY-RUN] Sauvegarde simulée")

            return True

        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde: {e}")
            return False

    def get_corpus_info(self) -> CorpusInfo:
        """Obtient les informations générales sur le corpus."""
        self.logger.info("Collecte des informations sur le corpus...")

        corpus_data = self.load_corpus()

        # Calculer les statistiques
        total_sources = len(corpus_data)
        total_extracts = sum(len(source.get("extracts", [])) for source in corpus_data)
        total_content_length = 0

        sources_summary = []

        for i, source in enumerate(corpus_data):
            extracts = source.get("extracts", [])
            extract_count = len(extracts)

            source_content_length = sum(
                len(extract.get("full_text", "")) for extract in extracts
            )
            total_content_length += source_content_length

            sources_summary.append(
                {
                    "index": i,
                    "name": source.get("source_name", f"Source_{i}"),
                    "type": source.get("source_type", "unknown"),
                    "extract_count": extract_count,
                    "content_length": source_content_length,
                }
            )

        # Informations sur le fichier
        file_size = (
            self.encrypted_file_path.stat().st_size
            if self.encrypted_file_path.exists()
            else 0
        )
        last_modified = (
            datetime.fromtimestamp(self.encrypted_file_path.stat().st_mtime).isoformat()
            if self.encrypted_file_path.exists()
            else "N/A"
        )

        return CorpusInfo(
            total_sources=total_sources,
            total_extracts=total_extracts,
            total_content_length=total_content_length,
            file_size_bytes=file_size,
            last_modified=last_modified,
            encryption_status="encrypted"
            if self.encrypted_file_path.exists()
            else "not_found",
            sources_summary=sources_summary,
        )

    def list_extracts(self) -> Dict[str, Any]:
        """
        Liste les extraits disponibles avec métadonnées sécurisées.

        Returns:
            Dict contenant la liste des extraits avec leurs métadonnées
        """
        self.logger.info("Extraction sécurisée des métadonnées d'extraits...")

        corpus_data = self.load_corpus()

        metadata = {
            "total_sources": len(corpus_data),
            "extraction_timestamp": datetime.now().isoformat(),
            "total_extracts": 0,
            "sources": [],
        }

        for source_idx, source in enumerate(corpus_data):
            source_meta = {
                "source_index": source_idx,
                "source_name": source.get("source_name", f"Source_{source_idx}"),
                "source_type": source.get("source_type", "unknown"),
                "schema": source.get("schema", "unknown"),
                "path": source.get("path", ""),
                "extract_count": 0,
                "extracts": [],
            }

            # Traiter les extraits
            extracts = source.get("extracts", [])
            source_meta["extract_count"] = len(extracts)

            for extract_idx, extract in enumerate(extracts):
                # Extraction sécurisée des métadonnées sans accès au contenu textuel
                extract_meta = {
                    "extract_index": extract_idx,
                    "extract_id": f"{source_idx}_{extract_idx}",
                    "extract_name": extract.get(
                        "extract_name", f"Extrait_{extract_idx}"
                    ),
                    "start_marker": extract.get("start_marker", ""),
                    "end_marker": extract.get("end_marker", ""),
                    "has_content": "full_text" in extract
                    and bool(extract.get("full_text")),
                    "content_length": len(extract.get("full_text", ""))
                    if extract.get("full_text")
                    else 0,
                    "metadata": extract.get("metadata", {}),
                }

                source_meta["extracts"].append(extract_meta)

            metadata["sources"].append(source_meta)

        # Statistiques globales
        metadata["total_extracts"] = sum(
            src["extract_count"] for src in metadata["sources"]
        )

        self.logger.info(
            f"Métadonnées extraites: {metadata['total_sources']} sources, {metadata['total_extracts']} extraits"
        )

        return metadata

    def find_extract_by_id(
        self, extract_id: str
    ) -> Optional[Tuple[Dict, Dict, int, int]]:
        """
        Trouve un extrait par son ID.

        Args:
            extract_id: ID de l'extrait (format "source_index_extract_index")

        Returns:
            Tuple[source, extract, source_idx, extract_idx] ou None
        """
        try:
            source_idx, extract_idx = map(int, extract_id.split("_"))
        except ValueError:
            self.logger.error(
                f"Format d'ID invalide: {extract_id}. Utilisez le format 'source_extract' (ex: '0_1')"
            )
            return None

        corpus_data = self.load_corpus()

        if source_idx >= len(corpus_data):
            self.logger.error(f"Index de source invalide: {source_idx}")
            return None

        source = corpus_data[source_idx]
        extracts = source.get("extracts", [])

        if extract_idx >= len(extracts):
            self.logger.error(f"Index d'extrait invalide: {extract_idx}")
            return None

        extract = extracts[extract_idx]
        return source, extract, source_idx, extract_idx

    def find_extract_by_name(
        self, extract_name: str
    ) -> Optional[Tuple[Dict, Dict, int, int]]:
        """
        Trouve un extrait par son nom.

        Args:
            extract_name: Nom de l'extrait

        Returns:
            Tuple[source, extract, source_idx, extract_idx] ou None
        """
        corpus_data = self.load_corpus()

        for source_idx, source in enumerate(corpus_data):
            extracts = source.get("extracts", [])
            for extract_idx, extract in enumerate(extracts):
                if extract.get("extract_name", "") == extract_name:
                    return source, extract, source_idx, extract_idx

        self.logger.error(f"Extrait non trouvé avec le nom: {extract_name}")
        return None

    def extract_specific_content(
        self, extract_id: Optional[str] = None, extract_name: Optional[str] = None
    ) -> Optional[ExtractInfo]:
        """
        Extrait le contenu d'un extrait spécifique.

        Args:
            extract_id: ID de l'extrait
            extract_name: Nom de l'extrait

        Returns:
            ExtractInfo contenant les informations de l'extrait ou None
        """
        if not extract_id and not extract_name:
            raise ValueError("Spécifiez soit l'ID soit le nom de l'extrait")

        # Trouver l'extrait
        if extract_id:
            result = self.find_extract_by_id(extract_id)
        else:
            result = self.find_extract_by_name(extract_name)

        if not result:
            return None

        source, extract, source_idx, extract_idx = result

        # Compiler les informations de l'extrait
        extract_info = ExtractInfo(
            source_info={
                "source_index": source_idx,
                "source_name": source.get("source_name", ""),
                "source_type": source.get("source_type", ""),
                "schema": source.get("schema", ""),
                "path": source.get("path", ""),
            },
            extract_info={
                "extract_index": extract_idx,
                "extract_id": f"{source_idx}_{extract_idx}",
                "extract_name": extract.get("extract_name", ""),
                "start_marker": extract.get("start_marker", ""),
                "end_marker": extract.get("end_marker", ""),
            },
            content=extract.get("full_text", ""),
            content_length=len(extract.get("full_text", "")),
            metadata=extract.get("metadata", {}),
        )

        self.logger.info(f"Extrait trouvé: {extract_info.extract_info['extract_name']}")
        self.logger.info(
            f"Longueur du contenu: {extract_info.content_length} caractères"
        )

        return extract_info

    def integrate_new_source(
        self, source_file_path: str, validate: bool = None
    ) -> bool:
        """
        Intègre une nouvelle source au corpus existant.

        Args:
            source_file_path: Chemin vers le fichier source JSON
            validate: Valider l'intégration après sauvegarde

        Returns:
            bool: True si intégration réussie
        """
        if validate is None:
            validate = self.config.validate_after_modify

        self.logger.info(f"Intégration d'une nouvelle source: {source_file_path}")

        try:
            # Charger le corpus existant
            existing_corpus = self.load_corpus()

            # Charger la nouvelle source
            new_source = self._load_new_source(source_file_path)

            # Intégrer
            updated_corpus = existing_corpus.copy()
            updated_corpus.append(new_source)

            # Statistiques
            total_sources = len(updated_corpus)
            total_extracts = sum(
                len(source.get("extracts", [])) for source in updated_corpus
            )
            new_extracts = len(new_source.get("extracts", []))

            self.logger.info(
                f"Corpus mis à jour: {total_sources} sources, {total_extracts} extraits (+{new_extracts} nouveaux)"
            )

            # Sauvegarder
            if self.save_corpus(updated_corpus):
                # Valider si demandé
                if validate:
                    return self._validate_integration(new_source)
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Erreur lors de l'intégration: {e}")
            return False

    def _load_new_source(self, source_file_path: str) -> Dict[str, Any]:
        """Charge une nouvelle source depuis un fichier JSON."""
        self.logger.info(f"Chargement de la nouvelle source: {source_file_path}")

        source_path = Path(source_file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Fichier source non trouvé: {source_file_path}")

        with open(source_path, "r", encoding="utf-8") as f:
            new_source_data = json.load(f)

        # Adapter la structure si nécessaire
        if "extraits" in new_source_data:
            new_source_data["extracts"] = new_source_data.pop("extraits")

        self.logger.info(
            f"Nouvelle source chargée: {len(new_source_data.get('extracts', []))} extraits"
        )
        return new_source_data

    def _validate_integration(self, new_source: Dict[str, Any]) -> bool:
        """Valide l'intégration en rechargeant et vérifiant le corpus."""
        self.logger.info("Validation de l'intégration...")

        try:
            # Recharger le corpus pour validation
            reloaded_corpus = self.load_corpus(use_cache=False)  # Force reload

            # Vérifier que la dernière source contient nos extraits
            if not reloaded_corpus:
                self.logger.error("Corpus rechargé vide")
                return False

            last_source = reloaded_corpus[-1]
            last_source_name = last_source.get("source_name", "Unknown")
            extract_count = len(last_source.get("extracts", []))
            expected_count = len(new_source.get("extracts", []))

            if extract_count == expected_count:
                self.logger.info(
                    f"Validation réussie - Source: '{last_source_name}' avec {extract_count} extraits"
                )
                return True
            else:
                self.logger.error(
                    f"Validation échouée - Attendu: {expected_count}, Trouvé: {extract_count}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Erreur lors de la validation: {e}")
            return False

    def validate_corpus_integrity(self) -> Dict[str, Any]:
        """Valide l'intégrité complète du corpus."""
        self.logger.info("Validation de l'intégrité du corpus...")

        validation_results = {
            "file_exists": False,
            "decryption_success": False,
            "json_valid": False,
            "structure_valid": False,
            "content_stats": {},
            "errors": [],
            "warnings": [],
        }

        try:
            # Vérifier l'existence du fichier
            validation_results["file_exists"] = self.encrypted_file_path.exists()
            if not validation_results["file_exists"]:
                validation_results["errors"].append("Fichier chiffré non trouvé")
                return validation_results

            # Tenter le déchiffrement
            try:
                corpus_data = self.load_corpus(use_cache=False)
                validation_results["decryption_success"] = True
                validation_results["json_valid"] = True

                # Valider la structure
                if isinstance(corpus_data, list):
                    validation_results["structure_valid"] = True

                    # Statistiques
                    total_sources = len(corpus_data)
                    total_extracts = 0
                    corrupted_sources = 0

                    for i, source in enumerate(corpus_data):
                        if not isinstance(source, dict):
                            corrupted_sources += 1
                            validation_results["warnings"].append(
                                f"Source {i} n'est pas un dictionnaire"
                            )
                            continue

                        extracts = source.get("extracts", [])
                        if not isinstance(extracts, list):
                            corrupted_sources += 1
                            validation_results["warnings"].append(
                                f"Source {i}: extracts n'est pas une liste"
                            )
                            continue

                        total_extracts += len(extracts)

                        # Vérifier les extraits
                        for j, extract in enumerate(extracts):
                            if not isinstance(extract, dict):
                                validation_results["warnings"].append(
                                    f"Source {i}, extrait {j}: format invalide"
                                )
                            elif not extract.get("full_text"):
                                validation_results["warnings"].append(
                                    f"Source {i}, extrait {j}: contenu vide"
                                )

                    validation_results["content_stats"] = {
                        "total_sources": total_sources,
                        "total_extracts": total_extracts,
                        "corrupted_sources": corrupted_sources,
                        "integrity_score": (total_sources - corrupted_sources)
                        / total_sources
                        if total_sources > 0
                        else 0,
                    }

                else:
                    validation_results["structure_valid"] = False
                    validation_results["errors"].append(
                        "Structure racine n'est pas une liste"
                    )

            except Exception as e:
                validation_results["errors"].append(f"Erreur de déchiffrement: {e}")

        except Exception as e:
            validation_results["errors"].append(f"Erreur générale: {e}")

        # Score global
        validation_results["overall_valid"] = (
            validation_results["file_exists"]
            and validation_results["decryption_success"]
            and validation_results["json_valid"]
            and validation_results["structure_valid"]
            and len(validation_results["errors"]) == 0
        )

        return validation_results

    def maintenance_operations(self) -> Dict[str, Any]:
        """Exécute des opérations de maintenance sur le corpus."""
        self.logger.info("Exécution des opérations de maintenance...")

        maintenance_results = {
            "backup_created": False,
            "integrity_check": {},
            "optimization_applied": False,
            "cleanup_performed": False,
            "errors": [],
        }

        try:
            # Créer une sauvegarde
            if self.encrypted_file_path.exists():
                backup_path = self.encrypted_file_path.with_suffix(
                    f".maintenance_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.enc"
                )
                import shutil

                shutil.copy2(self.encrypted_file_path, backup_path)
                maintenance_results["backup_created"] = True
                self.logger.info(f"Sauvegarde de maintenance créée: {backup_path}")

            # Vérification d'intégrité
            maintenance_results["integrity_check"] = self.validate_corpus_integrity()

            # Optimisation (suppression des champs inutiles, compression)
            if maintenance_results["integrity_check"]["overall_valid"]:
                corpus_data = self.load_corpus(use_cache=False)
                optimized_corpus = self._optimize_corpus_structure(corpus_data)

                if self.save_corpus(optimized_corpus, backup=False):
                    maintenance_results["optimization_applied"] = True
                    self.logger.info("Optimisation du corpus appliquée")

            # Nettoyage des fichiers temporaires
            maintenance_results["cleanup_performed"] = self._cleanup_temporary_files()

        except Exception as e:
            maintenance_results["errors"].append(f"Erreur de maintenance: {e}")
            self.logger.error(f"Erreur lors de la maintenance: {e}")

        return maintenance_results

    def _optimize_corpus_structure(
        self, corpus_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Optimise la structure du corpus."""
        optimized_corpus = []

        for source in corpus_data:
            optimized_source = {
                "source_name": source.get("source_name", ""),
                "source_type": source.get("source_type", ""),
                "schema": source.get("schema", ""),
                "path": source.get("path", ""),
                "extracts": [],
            }

            for extract in source.get("extracts", []):
                optimized_extract = {
                    "extract_name": extract.get("extract_name", ""),
                    "start_marker": extract.get("start_marker", ""),
                    "end_marker": extract.get("end_marker", ""),
                    "full_text": extract.get("full_text", ""),
                    "metadata": extract.get("metadata", {}),
                }

                # Supprimer les champs vides pour réduire la taille
                optimized_extract = {k: v for k, v in optimized_extract.items() if v}
                optimized_source["extracts"].append(optimized_extract)

            optimized_corpus.append(optimized_source)

        return optimized_corpus

    def _cleanup_temporary_files(self) -> bool:
        """Nettoie les fichiers temporaires."""
        try:
            temp_patterns = [
                self.data_dir.glob("*.tmp"),
                self.data_dir.glob("*.backup.*"),
                self.data_dir.glob("*_temp_*"),
            ]

            cleaned_count = 0
            for pattern in temp_patterns:
                for temp_file in pattern:
                    if temp_file.stat().st_mtime < (
                        datetime.now().timestamp() - 86400
                    ):  # Plus de 24h
                        temp_file.unlink()
                        cleaned_count += 1

            self.logger.info(
                f"Nettoyage: {cleaned_count} fichiers temporaires supprimés"
            )
            return True

        except Exception as e:
            self.logger.warning(f"Erreur lors du nettoyage: {e}")
            return False


class UnifiedUtilityFormatter:
    """Formateur pour les différents formats de sortie."""

    @staticmethod
    def format_corpus_info(info: CorpusInfo, format_type: OutputFormat) -> str:
        """Formate les informations du corpus selon le format demandé."""
        if format_type == OutputFormat.JSON:
            return json.dumps(
                {
                    "total_sources": info.total_sources,
                    "total_extracts": info.total_extracts,
                    "total_content_length": info.total_content_length,
                    "file_size_bytes": info.file_size_bytes,
                    "last_modified": info.last_modified,
                    "encryption_status": info.encryption_status,
                    "sources_summary": info.sources_summary,
                },
                indent=2,
                ensure_ascii=False,
            )

        elif format_type == OutputFormat.TEXT:
            output = []
            output.append("=" * 80)
            output.append("INFORMATIONS SUR LE CORPUS CHIFFRÉ")
            output.append("=" * 80)
            output.append(f"Sources totales: {info.total_sources}")
            output.append(f"Extraits totaux: {info.total_extracts}")
            output.append(
                f"Longueur totale du contenu: {info.total_content_length:,} caractères"
            )
            output.append(f"Taille du fichier: {info.file_size_bytes:,} bytes")
            output.append(f"Dernière modification: {info.last_modified}")
            output.append(f"Statut de chiffrement: {info.encryption_status}")

            output.append("\nDÉTAIL DES SOURCES:")
            output.append("-" * 60)
            for source in info.sources_summary:
                output.append(
                    f"[{source['index']}] {source['name']} ({source['type']})"
                )
                output.append(
                    f"    Extraits: {source['extract_count']}, Contenu: {source['content_length']:,} caractères"
                )

            output.append("=" * 80)
            return "\n".join(output)

        elif format_type == OutputFormat.CSV:
            import io
            import csv

            output = io.StringIO()
            writer = csv.writer(output)

            # En-têtes
            writer.writerow(["Métrique", "Valeur"])
            writer.writerow(["Sources totales", info.total_sources])
            writer.writerow(["Extraits totaux", info.total_extracts])
            writer.writerow(["Longueur totale contenu", info.total_content_length])
            writer.writerow(["Taille fichier bytes", info.file_size_bytes])
            writer.writerow(["Dernière modification", info.last_modified])
            writer.writerow(["Statut chiffrement", info.encryption_status])

            # Sources
            writer.writerow([])
            writer.writerow(["Index", "Nom", "Type", "Extraits", "Longueur contenu"])
            for source in info.sources_summary:
                writer.writerow(
                    [
                        source["index"],
                        source["name"],
                        source["type"],
                        source["extract_count"],
                        source["content_length"],
                    ]
                )

            return output.getvalue()

        elif format_type == OutputFormat.HTML:
            return UnifiedUtilityFormatter._format_corpus_info_html(info)

        return str(info)

    @staticmethod
    def _format_corpus_info_html(info: CorpusInfo) -> str:
        """Formate les informations du corpus en HTML."""
        html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informations Corpus - {info.last_modified}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background: #e8f4f8; padding: 15px; border-radius: 5px; text-align: center; }}
        .sources {{ margin: 20px 0; }}
        .source {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Informations sur le Corpus Chiffré</h1>
        <p>Dernière modification: {info.last_modified}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>{info.total_sources}</h3>
            <p>Sources</p>
        </div>
        <div class="stat-card">
            <h3>{info.total_extracts}</h3>
            <p>Extraits</p>
        </div>
        <div class="stat-card">
            <h3>{info.total_content_length:,}</h3>
            <p>Caractères</p>
        </div>
        <div class="stat-card">
            <h3>{info.file_size_bytes:,}</h3>
            <p>Bytes</p>
        </div>
    </div>
    
    <div class="sources">
        <h2>Détail des Sources</h2>
        <table>
            <tr><th>Index</th><th>Nom</th><th>Type</th><th>Extraits</th><th>Contenu</th></tr>
"""

        for source in info.sources_summary:
            html += f"""
            <tr>
                <td>{source['index']}</td>
                <td>{source['name']}</td>
                <td>{source['type']}</td>
                <td>{source['extract_count']}</td>
                <td>{source['content_length']:,} caractères</td>
            </tr>
"""

        html += """
        </table>
    </div>
</body>
</html>
"""
        return html

    @staticmethod
    def format_extract_list(
        metadata: Dict[str, Any], format_type: OutputFormat, detailed: bool = False
    ) -> str:
        """Formate la liste des extraits selon le format demandé."""
        if format_type == OutputFormat.JSON:
            return json.dumps(metadata, indent=2, ensure_ascii=False)

        elif format_type == OutputFormat.TEXT:
            output = []
            output.append("=" * 80)
            output.append("LISTE DES EXTRAITS DISPONIBLES")
            output.append("=" * 80)
            output.append(f"Sources totales: {metadata['total_sources']}")
            output.append(f"Extraits totaux: {metadata['total_extracts']}")
            output.append(f"Timestamp: {metadata['extraction_timestamp']}")

            output.append("\nSOURCES ET EXTRAITS:")
            output.append("-" * 60)

            for source in metadata["sources"]:
                output.append(
                    f"\n[SOURCE {source['source_index']}] {source['source_name']}"
                )
                output.append(
                    f"   Type: {source['source_type']}, Schema: {source['schema']}"
                )
                output.append(f"   Extraits: {source['extract_count']}")

                if detailed and source["extracts"]:
                    for extract in source["extracts"]:
                        output.append(
                            f"   [{extract['extract_id']}] {extract['extract_name']}"
                        )
                        output.append(
                            f"      - Debut: '{extract['start_marker'][:50]}{'...' if len(extract['start_marker']) > 50 else ''}'"
                        )
                        output.append(
                            f"      - Fin: '{extract['end_marker'][:50]}{'...' if len(extract['end_marker']) > 50 else ''}'"
                        )
                        output.append(
                            f"      - Contenu: {'OUI' if extract['has_content'] else 'NON'} ({extract['content_length']} caracteres)"
                        )
                elif source["extracts"]:
                    extract_ids = [
                        extract["extract_id"] for extract in source["extracts"]
                    ]
                    output.append(f"   IDs: {', '.join(extract_ids)}")

            output.append("\n" + "=" * 80)
            return "\n".join(output)

        elif format_type == OutputFormat.CSV:
            import io
            import csv

            output = io.StringIO()
            writer = csv.writer(output)

            # En-têtes
            writer.writerow(
                [
                    "Source_Index",
                    "Source_Name",
                    "Source_Type",
                    "Extract_ID",
                    "Extract_Name",
                    "Content_Length",
                    "Has_Content",
                ]
            )

            for source in metadata["sources"]:
                for extract in source["extracts"]:
                    writer.writerow(
                        [
                            source["source_index"],
                            source["source_name"],
                            source["source_type"],
                            extract["extract_id"],
                            extract["extract_name"],
                            extract["content_length"],
                            extract["has_content"],
                        ]
                    )

            return output.getvalue()

        return str(metadata)

    @staticmethod
    def format_extract_content(
        extract_info: ExtractInfo, format_type: OutputFormat, show_content: bool = True
    ) -> str:
        """Formate le contenu d'un extrait selon le format demandé."""
        if format_type == OutputFormat.JSON:
            data = {
                "source_info": extract_info.source_info,
                "extract_info": extract_info.extract_info,
                "content_length": extract_info.content_length,
                "metadata": extract_info.metadata,
            }
            if show_content:
                data["content"] = extract_info.content
            return json.dumps(data, indent=2, ensure_ascii=False)

        elif format_type == OutputFormat.TEXT:
            output = []
            output.append("=" * 80)
            output.append("INFORMATION SUR L'EXTRAIT SÉLECTIONNÉ")
            output.append("=" * 80)

            # Informations sur la source
            output.append(f"\nSOURCE:")
            output.append(f"- Index: {extract_info.source_info['source_index']}")
            output.append(f"- Nom: {extract_info.source_info['source_name']}")
            output.append(f"- Type: {extract_info.source_info['source_type']}")
            output.append(f"- Schema: {extract_info.source_info['schema']}")
            output.append(f"- Chemin: {extract_info.source_info['path']}")

            # Informations sur l'extrait
            output.append(f"\nEXTRAIT:")
            output.append(f"- ID: {extract_info.extract_info['extract_id']}")
            output.append(f"- Nom: {extract_info.extract_info['extract_name']}")
            output.append(
                f"- Marqueur début: '{extract_info.extract_info['start_marker']}'"
            )
            output.append(
                f"- Marqueur fin: '{extract_info.extract_info['end_marker']}'"
            )
            output.append(f"- Longueur: {extract_info.content_length} caractères")

            # Métadonnées additionnelles
            if extract_info.metadata:
                output.append(f"\nMÉTADONNÉES:")
                for key, value in extract_info.metadata.items():
                    output.append(f"- {key}: {value}")

            # Contenu textuel si demandé
            if show_content and extract_info.content:
                output.append(f"\nCONTENU TEXTUEL:")
                output.append("-" * 60)
                output.append(extract_info.content)
                output.append("-" * 60)

            output.append("=" * 80)
            return "\n".join(output)

        return str(extract_info)


def create_utility_factory(mode: str = "list", **kwargs) -> UnifiedCorpusManager:
    """Factory pour créer un gestionnaire d'utilitaires avec configuration prédéfinie."""

    mode_configs = {
        "list": UtilityConfiguration(
            mode=UtilityMode.LIST, output_format=OutputFormat.TEXT, detailed=False
        ),
        "extract": UtilityConfiguration(
            mode=UtilityMode.EXTRACT, output_format=OutputFormat.TEXT, show_content=True
        ),
        "integrate": UtilityConfiguration(
            mode=UtilityMode.INTEGRATE,
            backup_before_modify=True,
            validate_after_modify=True,
        ),
        "validate": UtilityConfiguration(
            mode=UtilityMode.VALIDATE, output_format=OutputFormat.JSON
        ),
        "maintenance": UtilityConfiguration(
            mode=UtilityMode.MAINTENANCE, backup_before_modify=True
        ),
        "info": UtilityConfiguration(
            mode=UtilityMode.INFO, output_format=OutputFormat.TEXT
        ),
    }

    config = mode_configs.get(mode, mode_configs["list"])

    # Application des overrides
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return UnifiedCorpusManager(config)


async def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Système d'Utilitaires Unifiés pour le Corpus Chiffré",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
    # Lister les extraits
    python scripts/unified_utilities.py --mode list --detailed
    
    # Extraire un extrait spécifique
    python scripts/unified_utilities.py --mode extract --extract-id "0_1"
    
    # Intégrer une nouvelle source
    python scripts/unified_utilities.py --mode integrate --source-file data/new_source.json
    
    # Informations sur le corpus
    python scripts/unified_utilities.py --mode info --format json
    
    # Validation d'intégrité
    python scripts/unified_utilities.py --mode validate
    
    # Maintenance du corpus
    python scripts/unified_utilities.py --mode maintenance
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["list", "extract", "integrate", "validate", "maintenance", "info"],
        default="list",
        help="Mode d'opération",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv", "html"],
        default="text",
        help="Format de sortie",
    )
    parser.add_argument("--output", help="Fichier de sortie")
    parser.add_argument("--passphrase", help="Phrase secrète pour le déchiffrement")
    parser.add_argument("--detailed", action="store_true", help="Affichage détaillé")
    parser.add_argument(
        "--show-content", action="store_true", help="Afficher le contenu textuel"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulation sans modification"
    )

    # Arguments spécifiques au mode extract
    parser.add_argument(
        "--extract-id", help="ID de l'extrait (format: 'source_extract')"
    )
    parser.add_argument("--extract-name", help="Nom de l'extrait")

    # Arguments spécifiques au mode integrate
    parser.add_argument("--source-file", help="Fichier source JSON à intégrer")
    parser.add_argument(
        "--no-backup", action="store_true", help="Ne pas créer de sauvegarde"
    )
    parser.add_argument(
        "--no-validate", action="store_true", help="Ne pas valider après intégration"
    )

    args = parser.parse_args()

    try:
        # Configuration du gestionnaire
        manager = create_utility_factory(
            mode=args.mode,
            passphrase=args.passphrase,
            output_format=getattr(OutputFormat, args.format.upper()),
            output_file=args.output,
            detailed=args.detailed,
            show_content=args.show_content,
            dry_run=args.dry_run,
            backup_before_modify=not args.no_backup,
            validate_after_modify=not args.no_validate,
        )

        # Exécution selon le mode
        if args.mode == "list":
            metadata = manager.list_extracts()
            output = UnifiedUtilityFormatter.format_extract_list(
                metadata, manager.config.output_format, args.detailed
            )

        elif args.mode == "extract":
            if not args.extract_id and not args.extract_name:
                parser.error("Mode extract nécessite --extract-id ou --extract-name")

            extract_info = manager.extract_specific_content(
                args.extract_id, args.extract_name
            )
            if extract_info:
                output = UnifiedUtilityFormatter.format_extract_content(
                    extract_info, manager.config.output_format, args.show_content
                )
            else:
                print("Extrait non trouvé")
                return 1

        elif args.mode == "integrate":
            if not args.source_file:
                parser.error("Mode integrate nécessite --source-file")

            success = manager.integrate_new_source(args.source_file)
            if success:
                print("✅ Intégration réussie")
                return 0
            else:
                print("❌ Échec de l'intégration")
                return 1

        elif args.mode == "validate":
            results = manager.validate_corpus_integrity()
            output = json.dumps(results, indent=2, ensure_ascii=False)

        elif args.mode == "maintenance":
            results = manager.maintenance_operations()
            output = json.dumps(results, indent=2, ensure_ascii=False)

        elif args.mode == "info":
            info = manager.get_corpus_info()
            output = UnifiedUtilityFormatter.format_corpus_info(
                info, manager.config.output_format
            )

        # Affichage ou sauvegarde
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Résultats sauvegardés dans: {args.output}")
        else:
            print(output)

        return 0

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution: {e}")
        return 1


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))
