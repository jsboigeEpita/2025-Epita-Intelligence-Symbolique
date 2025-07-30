#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Système de maintenance unifié - Consolidation des scripts de maintenance
======================================================================

Ce fichier consolide la logique de :
- scripts/maintenance/depot_cleanup_migration.ps1
- scripts/maintenance/depot_cleanup_migration_simple.ps1  
- scripts/maintenance/cleanup_obsolete_files.py
- scripts/maintenance/safe_file_deletion.py
- scripts/utils/cleanup_decrypt_traces.py

Toute la logique fonctionnelle est préservée sans simulation.
"""

import os
import sys
import json
import tarfile
import shutil
import hashlib
import subprocess
import logging
import gc
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("UnifiedMaintenance")

class MaintenanceMode(Enum):
    """Modes de maintenance disponibles."""
    PREVIEW = "preview"
    EXECUTE = "execute"
    CLEANUP_ONLY = "cleanup-only"
    SAFE_DELETE = "safe-delete"
    DECRYPT_CLEANUP = "decrypt-cleanup"
    MIGRATION = "migration"
    FULL_MAINTENANCE = "full-maintenance"

@dataclass
class MaintenanceConfiguration:
    """Configuration pour les opérations de maintenance."""
    mode: MaintenanceMode = MaintenanceMode.PREVIEW
    create_backup: bool = True
    batch_size: int = 5
    verbose: bool = False
    project_root: Optional[Path] = None
    
    def __post_init__(self):
        if self.project_root is None:
            self.project_root = Path.cwd()
        else:
            self.project_root = Path(self.project_root)

class UnifiedMaintenanceSystem:
    """
    Système de maintenance unifié intégrant toutes les fonctionnalités.
    """
    
    def __init__(self, config: MaintenanceConfiguration):
        self.config = config
        self.project_root = config.project_root.resolve()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Répertoires de travail
        self.backup_dir = self.project_root / "archives"
        self.logs_dir = self.project_root / "logs"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Logs d'opérations
        self.log_data = {
            "timestamp": datetime.now().isoformat(),
            "maintenance_version": "1.0.0",
            "actions": [],
            "errors": [],
            "checksums": {},
            "backup_info": {}
        }
        
        # Définition des fichiers et répertoires à traiter
        self._initialize_file_definitions()
        
        # Vérification que nous sommes dans le bon répertoire
        if not (self.project_root / "argumentation_analysis").exists():
            raise RuntimeError(
                f"ERREUR: Ce script doit être exécuté depuis la racine du projet "
                f"(doit contenir argumentation_analysis/). Répertoire actuel: {self.project_root}"
            )
    
    def _initialize_file_definitions(self):
        """Initialise les définitions de fichiers à traiter."""
        
        # Tests éparpillés à la racine à déplacer
        self.tests_to_move = [
            {"source": "test_advanced_rhetorical_enhanced.py", "dest": "tests/integration/rhetorical/", "reason": "Test d'intégration rhétorique"},
            {"source": "test_conversation_integration.py", "dest": "tests/integration/conversation/", "reason": "Test d'intégration conversation"},
            {"source": "test_final_modal_correction_demo.py", "dest": "tests/demos/modal/", "reason": "Démo de correction modale"},
            {"source": "test_fol_demo_simple.py", "dest": "tests/demos/fol/", "reason": "Démo FOL simple"},
            {"source": "test_fol_demo.py", "dest": "tests/demos/fol/", "reason": "Démo FOL"},
            {"source": "test_intelligent_modal_correction.py", "dest": "tests/integration/modal/", "reason": "Test correction modale intelligente"},
            {"source": "test_micro_orchestration.py", "dest": "tests/integration/orchestration/", "reason": "Test micro-orchestration"},
            {"source": "test_modal_correction_validation.py", "dest": "tests/validation/modal/", "reason": "Validation correction modale"},
            {"source": "test_modal_retry_mechanism.py", "dest": "tests/integration/retry/", "reason": "Test mécanisme retry"},
            {"source": "test_rhetorical_demo_integration.py", "dest": "tests/demos/rhetorical/", "reason": "Démo intégration rhétorique"},
            {"source": "test_simple_unified_pipeline.py", "dest": "tests/integration/pipelines/", "reason": "Test pipeline unifié"},
            {"source": "test_sk_retry_demo.py", "dest": "tests/demos/retry/", "reason": "Démo SK retry"},
            {"source": "test_source_management_integration.py", "dest": "tests/integration/sources/", "reason": "Test gestion sources"},
            {"source": "test_trace_analyzer_conversation_format.py", "dest": "tests/unit/analyzers/", "reason": "Test unitaire analyseur"},
            {"source": "test_unified_report_generation_integration.py", "dest": "tests/integration/reporting/", "reason": "Test intégration reporting"},
            {"source": "test_unified_text_analysis_integration.py", "dest": "tests/integration/analysis/", "reason": "Test analyse de texte"},
            {"source": "TEST_MAPPING.md", "dest": "docs/testing/", "reason": "Documentation mapping tests"}
        ]
        
        # Rapports à déplacer
        self.reports_to_move = [
            {"source": "AUDIT_AUTHENTICITE_FOL_COMPLETE.md", "dest": "docs/audits/"},
            {"source": "AUDIT_REFACTORISATION_ORCHESTRATION.md", "dest": "docs/audits/"},
            {"source": "CONSOLIDATION_ORCHESTRATION_REUSSIE.md", "dest": "docs/reports/consolidation/"},
            {"source": "RAPPORT_ANALYSE_CORRECTION_BNF_INTELLIGENTE.md", "dest": "docs/reports/analysis/"},
            {"source": "RAPPORT_EVALUATION_TESTS_SYSTEME.md", "dest": "docs/reports/testing/"},
            {"source": "RAPPORT_FINAL_FOL_AUTHENTIQUE.md", "dest": "docs/reports/fol/"},
            {"source": "SYNTHESE_FINALE_REFACTORISATION_UNIFIED_REPORTS.md", "dest": "docs/reports/refactoring/"},
            {"source": "VALIDATION_ECOSYSTEM_FINALE.md", "dest": "docs/validation/"}
        ]
        
        # Fichiers temporaires à nettoyer
        self.temp_files_patterns = [
            "temp_original_file.enc", "page_content.html", "scratch_tweety_interactions.py",
            "pytest_full_output.log", "pytest_prop_logic_*.log", "pytest_all_tests_*.log",
            "pytest_output*.log", "setup_global_output.log", "extract_agent.log", "temp_*.py",
            "temp_extracts_metadata.json", "extract_info_*.json", "*.tmp", "decrypt_*.log"
        ]
        
        # Fichiers obsolètes à supprimer (selon plan Phase 4)
        self.files_to_delete = [
            "fix_final_test.py",
            "validation_phase_b.py", 
            "test_cluedo_demo.py",
            "test_asyncmock_issues.py",
            "test_audit_integrite_cluedo.py",
            "test_diagnostic.py",
            "test_validation_integrite_apres_corrections.py",
            # Archives temporaires
            "archives/pre_cleanup_backup_20250607_153104.tar.gz",
            "archives/pre_cleanup_backup_20250607_153122.tar.gz",
        ]
        
        # Fichiers à archiver (historiques précieux)
        self.files_to_archive = [
            "test_einstein_simple.py",
            "demo_tests_validation.py",
            "fix_failing_tests.py",
            "debug_jni_leak.py",
            "test_watson_logic_assistant.py",
            "test_sherlock_enquete_agent.py",
            "test_cluedo_orchestration_integration.py",
            "test_enquete_state_manager_plugin.py",
            "test_final_oracle_100_percent.py",
            "test_final_oracle_fixes.py",
            "test_group3_fixes.py",
            "test_phase_b_simple.py"
        ]
        
        # Répertoires à créer
        self.dirs_to_create = [
            "tests/demos/fol", "tests/demos/modal", "tests/demos/rhetorical", "tests/demos/retry",
            "tests/integration/conversation", "tests/integration/modal", "tests/integration/orchestration",
            "tests/integration/retry", "tests/integration/sources", "tests/integration/reporting",
            "tests/integration/analysis", "tests/integration/pipelines", "tests/validation/modal",
            "tests/unit/analyzers", "docs/audits", "docs/reports/consolidation", "docs/reports/analysis",
            "docs/reports/testing", "docs/reports/fol", "docs/reports/implementation", 
            "docs/reports/refactoring", "docs/reports/various", "docs/validation", "docs/testing"
        ]
        
        # Fichiers protégés (ne jamais supprimer)
        self.protected_files = [
            "test_oracle_behavior_demo.py", "test_oracle_behavior_simple.py",
            "conftest_gpt_enhanced.py", "test_mock_vs_real_behavior.py",
            "test_config_real_gpt.py", "test_enquete_states.py",
            "test_cluedo_extended_workflow.py", "test_cluedo_oracle_enhanced_real.py",
            "test_einstein_demo_real.py", "test_oracle_integration.py",
            "test_sherlock_watson_moriarty_real_gpt.py", "test_oracle_performance.py",
            "test_error_handling.py", "test_cluedo_dataset.py",
            "test_dataset_access_manager.py", "test_moriarty_interrogator_agent.py",
            "test_oracle_base_agent.py", "test_oracle_base_agent_fixed.py",
            "test_oracle_enhanced_behavior.py", "test_cluedo_oracle_state.py",
            "test_cluedo_enhanced_orchestrator.py", "test_scripts_execution.py",
            "test_phase_a_personnalites_distinctes.py", "test_phase_b_naturalite_dialogue.py",
            "test_phase_c_fluidite_transitions.py"
        ]

    async def run_maintenance(self) -> Dict[str, Any]:
        """
        Exécute les opérations de maintenance selon le mode configuré.
        """
        start_time = datetime.now()
        self._print_header(f"MAINTENANCE UNIFIÉE - MODE: {self.config.mode.value.upper()}")
        self._log_action("start_maintenance", str(self.project_root), f"Mode: {self.config.mode.value}")
        
        try:
            results = {"status": "RUNNING", "mode": self.config.mode.value, "actions": []}
            
            if self.config.mode == MaintenanceMode.PREVIEW:
                results = await self._run_preview_mode()
            elif self.config.mode == MaintenanceMode.EXECUTE:
                results = await self._run_execute_mode()
            elif self.config.mode == MaintenanceMode.CLEANUP_ONLY:
                results = await self._run_cleanup_only_mode()
            elif self.config.mode == MaintenanceMode.SAFE_DELETE:
                results = await self._run_safe_delete_mode()
            elif self.config.mode == MaintenanceMode.DECRYPT_CLEANUP:
                results = await self._run_decrypt_cleanup_mode()
            elif self.config.mode == MaintenanceMode.MIGRATION:
                results = await self._run_migration_mode()
            elif self.config.mode == MaintenanceMode.FULL_MAINTENANCE:
                results = await self._run_full_maintenance_mode()
            
            # Calcul du temps d'exécution
            execution_time = (datetime.now() - start_time).total_seconds()
            results["execution_time"] = execution_time
            results["timestamp"] = start_time.isoformat()
            
            # Sauvegarde des logs
            await self._save_maintenance_log(results)
            
            self._print_completion_summary(results)
            return results
            
        except Exception as e:
            logger.error(f"Erreur dans la maintenance: {e}")
            return {
                "status": "ERROR",
                "error": str(e),
                "mode": self.config.mode.value,
                "execution_time": (datetime.now() - start_time).total_seconds()
            }

    async def _run_preview_mode(self) -> Dict[str, Any]:
        """Mode preview - affiche ce qui va être fait sans modifier."""
        self._print_section("PREVIEW - ACTIONS PRÉVUES")
        
        # Répertoires à créer
        dirs_to_create = [d for d in self.dirs_to_create if not (self.project_root / d).exists()]
        self._print_subsection(f"RÉPERTOIRES - Création de {len(dirs_to_create)} nouveaux répertoires")
        for dir_path in dirs_to_create:
            print(f"  [CRÉER] {dir_path}")
        
        # Tests à déplacer
        tests_existing = [t for t in self.tests_to_move if (self.project_root / t["source"]).exists()]
        self._print_subsection(f"TESTS - Déplacement de {len(tests_existing)} fichiers")
        for test in tests_existing:
            size = self._get_file_size_kb(self.project_root / test["source"])
            print(f"  [DÉPLACER] {test['source']} -> {test['dest']} ({size}KB) - {test['reason']}")
        
        # Rapports à déplacer  
        reports_existing = [r for r in self.reports_to_move if (self.project_root / r["source"]).exists()]
        additional_reports = self._find_additional_reports()
        total_reports = len(reports_existing) + len(additional_reports)
        self._print_subsection(f"RAPPORTS - Déplacement de {total_reports} fichiers")
        
        for report in reports_existing + additional_reports:
            size = self._get_file_size_kb(self.project_root / report["source"])
            print(f"  [DÉPLACER] {report['source']} -> {report['dest']} ({size}KB)")
        
        # Fichiers temporaires à nettoyer
        temp_files = self._find_temp_files()
        self._print_subsection(f"NETTOYAGE - Suppression de {len(temp_files)} fichiers temporaires")
        for temp_file in temp_files:
            size = self._get_file_size_kb(temp_file)
            print(f"  [SUPPRIMER] {temp_file.relative_to(self.project_root)} ({size}KB)")
        
        # Fichiers obsolètes à supprimer
        obsolete_files = [f for f in self.files_to_delete if (self.project_root / f).exists()]
        self._print_subsection(f"SUPPRESSION - Suppression de {len(obsolete_files)} fichiers obsolètes")
        for file_path in obsolete_files:
            size = self._get_file_size_kb(self.project_root / file_path)
            print(f"  [SUPPRIMER] {file_path} ({size}KB)")
        
        return {
            "status": "SUCCESS",
            "mode": "preview",
            "summary": {
                "directories_to_create": len(dirs_to_create),
                "tests_to_move": len(tests_existing),
                "reports_to_move": total_reports,
                "temp_files_to_clean": len(temp_files),
                "obsolete_files_to_delete": len(obsolete_files)
            }
        }

    async def _run_execute_mode(self) -> Dict[str, Any]:
        """Mode execute - exécute toutes les opérations de maintenance."""
        self._print_section("EXÉCUTION - MAINTENANCE COMPLÈTE")
        
        results = {"status": "RUNNING", "actions": []}
        
        # Sauvegarde préalable si demandée
        if self.config.create_backup:
            backup_path = await self._create_comprehensive_backup()
            results["backup_created"] = str(backup_path)
            self._log_action("backup_created", str(backup_path))
        
        # 1. Création des répertoires
        dirs_created = await self._create_directories()
        results["directories_created"] = dirs_created
        
        # 2. Déplacement des tests
        tests_moved = await self._move_tests()
        results["tests_moved"] = tests_moved
        
        # 3. Déplacement des rapports
        reports_moved = await self._move_reports()
        results["reports_moved"] = reports_moved
        
        # 4. Nettoyage des fichiers temporaires
        temp_cleaned = await self._cleanup_temporary_files()
        results["temp_files_cleaned"] = temp_cleaned
        
        # 5. Suppression des fichiers obsolètes
        obsolete_deleted = await self._delete_obsolete_files()
        results["obsolete_files_deleted"] = obsolete_deleted
        
        # 6. Nettoyage sécurisé de la mémoire
        await self._secure_memory_cleanup()
        results["memory_cleaned"] = True
        
        results["status"] = "SUCCESS"
        return results

    async def _run_cleanup_only_mode(self) -> Dict[str, Any]:
        """Mode cleanup-only - nettoie uniquement les fichiers temporaires."""
        self._print_section("NETTOYAGE SEULEMENT - FICHIERS TEMPORAIRES")
        
        temp_cleaned = await self._cleanup_temporary_files()
        await self._secure_memory_cleanup()
        
        return {
            "status": "SUCCESS",
            "mode": "cleanup-only",
            "temp_files_cleaned": temp_cleaned,
            "memory_cleaned": True
        }

    async def _run_safe_delete_mode(self) -> Dict[str, Any]:
        """Mode safe-delete - suppression sécurisée des fichiers obsolètes."""
        self._print_section("SUPPRESSION SÉCURISÉE - FICHIERS OBSOLÈTES")
        
        results = {"status": "RUNNING"}
        
        # Sauvegarde spécifique pour la suppression
        if self.config.create_backup:
            backup_path = await self._create_deletion_backup()
            results["backup_created"] = str(backup_path)
        
        # Vérification de l'intégrité du système Oracle
        oracle_ok = await self._verify_oracle_integrity()
        results["oracle_integrity"] = oracle_ok
        
        if oracle_ok:
            obsolete_deleted = await self._delete_obsolete_files()
            results["obsolete_files_deleted"] = obsolete_deleted
            results["status"] = "SUCCESS"
        else:
            results["status"] = "ERROR"
            results["error"] = "Intégrité Oracle compromise, suppression annulée"
        
        return results

    async def _run_decrypt_cleanup_mode(self) -> Dict[str, Any]:
        """Mode decrypt-cleanup - nettoyage spécialisé pour les traces de déchiffrement."""
        self._print_section("NETTOYAGE SÉCURISÉ - TRACES DE DÉCHIFFREMENT")
        
        # Patterns spécifiques au déchiffrement
        decrypt_patterns = [
            "temp_extracts_metadata.json",
            "extract_info_*.json", 
            "*.tmp",
            "decrypt_*.log"
        ]
        
        files_cleaned = 0
        for pattern in decrypt_patterns:
            for file_path in self.project_root.glob(pattern):
                try:
                    file_path.unlink()
                    logger.info(f"Fichier de déchiffrement supprimé: {file_path}")
                    files_cleaned += 1
                    self._log_action("delete_decrypt_trace", str(file_path))
                except Exception as e:
                    logger.warning(f"Erreur suppression {file_path}: {e}")
                    self._log_error(f"Erreur suppression {file_path}: {e}")
        
        # Nettoyage sécurisé de la mémoire
        await self._secure_memory_cleanup()
        
        return {
            "status": "SUCCESS",
            "mode": "decrypt-cleanup",
            "decrypt_traces_cleaned": files_cleaned,
            "memory_cleaned": True
        }

    async def _run_migration_mode(self) -> Dict[str, Any]:
        """Mode migration - déplacement et réorganisation uniquement."""
        self._print_section("MIGRATION - RÉORGANISATION DES FICHIERS")
        
        results = {"status": "RUNNING"}
        
        # Sauvegarde avant migration
        if self.config.create_backup:
            backup_path = await self._create_migration_backup()
            results["backup_created"] = str(backup_path)
        
        # Création des répertoires nécessaires
        dirs_created = await self._create_directories()
        results["directories_created"] = dirs_created
        
        # Migration des tests
        tests_moved = await self._move_tests()
        results["tests_moved"] = tests_moved
        
        # Migration des rapports
        reports_moved = await self._move_reports()
        results["reports_moved"] = reports_moved
        
        results["status"] = "SUCCESS"
        return results

    async def _run_full_maintenance_mode(self) -> Dict[str, Any]:
        """Mode full-maintenance - toutes les opérations dans l'ordre optimal."""
        self._print_section("MAINTENANCE COMPLÈTE - TOUTES OPÉRATIONS")
        
        results = {"status": "RUNNING", "phases": []}
        
        # Phase 1: Sauvegarde complète
        if self.config.create_backup:
            backup_path = await self._create_comprehensive_backup()
            results["backup_created"] = str(backup_path)
            results["phases"].append("backup_complete")
        
        # Phase 2: Vérification intégrité
        oracle_ok = await self._verify_oracle_integrity()
        results["oracle_integrity"] = oracle_ok
        results["phases"].append("integrity_check")
        
        # Phase 3: Création répertoires
        dirs_created = await self._create_directories()
        results["directories_created"] = dirs_created
        results["phases"].append("directories_created")
        
        # Phase 4: Migration fichiers
        tests_moved = await self._move_tests()
        reports_moved = await self._move_reports()
        results["tests_moved"] = tests_moved
        results["reports_moved"] = reports_moved
        results["phases"].append("files_migrated")
        
        # Phase 5: Nettoyage
        temp_cleaned = await self._cleanup_temporary_files()
        results["temp_files_cleaned"] = temp_cleaned
        results["phases"].append("temp_cleaned")
        
        # Phase 6: Suppression sécurisée (seulement si Oracle OK)
        if oracle_ok:
            obsolete_deleted = await self._delete_obsolete_files()
            results["obsolete_files_deleted"] = obsolete_deleted
            results["phases"].append("obsolete_deleted")
        
        # Phase 7: Nettoyage final
        await self._secure_memory_cleanup()
        results["memory_cleaned"] = True
        results["phases"].append("memory_cleaned")
        
        results["status"] = "SUCCESS"
        return results

    # === MÉTHODES UTILITAIRES ===

    async def _create_comprehensive_backup(self) -> Path:
        """Crée une sauvegarde complète avant maintenance."""
        backup_name = f"comprehensive_backup_{self.timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_name
        
        self._print_info(f"Création sauvegarde complète: {backup_name}")
        
        with tarfile.open(backup_path, "w:gz") as tar:
            # Sauvegarder tous les fichiers qui vont être affectés
            all_files_to_backup = []
            
            # Tests à déplacer
            all_files_to_backup.extend([t["source"] for t in self.tests_to_move])
            # Rapports à déplacer
            all_files_to_backup.extend([r["source"] for r in self.reports_to_move])
            # Fichiers à supprimer
            all_files_to_backup.extend(self.files_to_delete)
            # Fichiers à archiver
            all_files_to_backup.extend(self.files_to_archive)
            
            for file_path in set(all_files_to_backup):
                full_path = self.project_root / file_path
                if full_path.exists():
                    tar.add(full_path, arcname=file_path)
                    self._log_action("backup_file", str(full_path))
        
        # Calcul du checksum
        md5_hash = self._calculate_md5(backup_path)
        self.log_data["backup_info"]["comprehensive"] = {
            "path": str(backup_path),
            "md5": md5_hash,
            "timestamp": self.timestamp
        }
        
        self._print_success(f"Sauvegarde créée: {backup_path} (MD5: {md5_hash[:8]}...)")
        return backup_path

    async def _create_deletion_backup(self) -> Path:
        """Crée une sauvegarde spécifique pour les suppressions."""
        backup_name = f"pre_deletion_backup_{self.timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_name
        
        with tarfile.open(backup_path, "w:gz") as tar:
            for file_path in self.files_to_delete:
                full_path = self.project_root / file_path
                if full_path.exists():
                    tar.add(full_path, arcname=file_path)
        
        return backup_path

    async def _create_migration_backup(self) -> Path:
        """Crée une sauvegarde spécifique pour les migrations."""
        backup_name = f"pre_migration_backup_{self.timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_name
        
        with tarfile.open(backup_path, "w:gz") as tar:
            # Sauvegarder les fichiers à déplacer
            for test in self.tests_to_move:
                full_path = self.project_root / test["source"]
                if full_path.exists():
                    tar.add(full_path, arcname=test["source"])
            
            for report in self.reports_to_move:
                full_path = self.project_root / report["source"]
                if full_path.exists():
                    tar.add(full_path, arcname=report["source"])
        
        return backup_path

    async def _create_directories(self) -> int:
        """Crée tous les répertoires nécessaires."""
        dirs_created = 0
        
        for dir_path in self.dirs_to_create:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                try:
                    full_path.mkdir(parents=True, exist_ok=True)
                    self._print_action("CRÉER", str(dir_path))
                    self._log_action("create_directory", str(full_path))
                    dirs_created += 1
                except Exception as e:
                    logger.error(f"Erreur création répertoire {dir_path}: {e}")
                    self._log_error(f"Erreur création répertoire {dir_path}: {e}")
        
        return dirs_created

    async def _move_tests(self) -> int:
        """Déplace tous les tests vers leur nouvelle organisation."""
        tests_moved = 0
        
        for test in self.tests_to_move:
            source_path = self.project_root / test["source"]
            dest_dir = self.project_root / test["dest"]
            dest_path = dest_dir / test["source"]
            
            if source_path.exists():
                try:
                    # Créer le répertoire de destination si nécessaire
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Déplacer le fichier
                    shutil.move(str(source_path), str(dest_path))
                    self._print_action("DÉPLACER", f"{test['source']} -> {test['dest']}")
                    self._log_action("move_test", f"{source_path} -> {dest_path}", test["reason"])
                    tests_moved += 1
                    
                except Exception as e:
                    logger.error(f"Erreur déplacement test {test['source']}: {e}")
                    self._log_error(f"Erreur déplacement test {test['source']}: {e}")
        
        return tests_moved

    async def _move_reports(self) -> int:
        """Déplace tous les rapports vers leur nouvelle organisation."""
        reports_moved = 0
        
        # Rapports prédéfinis
        all_reports = self.reports_to_move + self._find_additional_reports()
        
        for report in all_reports:
            source_path = self.project_root / report["source"]
            dest_dir = self.project_root / report["dest"]
            dest_path = dest_dir / report["source"]
            
            if source_path.exists():
                try:
                    # Créer le répertoire de destination si nécessaire
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Déplacer le fichier
                    shutil.move(str(source_path), str(dest_path))
                    self._print_action("DÉPLACER", f"{report['source']} -> {report['dest']}")
                    self._log_action("move_report", f"{source_path} -> {dest_path}")
                    reports_moved += 1
                    
                except Exception as e:
                    logger.error(f"Erreur déplacement rapport {report['source']}: {e}")
                    self._log_error(f"Erreur déplacement rapport {report['source']}: {e}")
        
        return reports_moved

    async def _cleanup_temporary_files(self) -> int:
        """Nettoie tous les fichiers temporaires."""
        files_cleaned = 0
        temp_files = self._find_temp_files()
        
        for temp_file in temp_files:
            try:
                temp_file.unlink()
                self._print_action("SUPPRIMER", str(temp_file.relative_to(self.project_root)))
                self._log_action("delete_temp", str(temp_file))
                files_cleaned += 1
            except Exception as e:
                logger.warning(f"Erreur suppression {temp_file}: {e}")
                self._log_error(f"Erreur suppression {temp_file}: {e}")
        
        return files_cleaned

    async def _delete_obsolete_files(self) -> int:
        """Supprime les fichiers obsolètes de manière sécurisée."""
        files_deleted = 0
        
        # Traitement par batch pour la sécurité
        batches = [self.files_to_delete[i:i + self.config.batch_size] 
                  for i in range(0, len(self.files_to_delete), self.config.batch_size)]
        
        for batch_num, batch in enumerate(batches, 1):
            self._print_info(f"Suppression batch {batch_num}/{len(batches)}: {len(batch)} fichiers")
            
            for file_path in batch:
                full_path = self.project_root / file_path
                
                # Vérifier que le fichier n'est pas protégé
                if file_path not in self.protected_files and full_path.exists():
                    try:
                        # Calculer le checksum avant suppression
                        checksum = self._calculate_md5(full_path)
                        self.log_data["checksums"][file_path] = checksum
                        
                        # Supprimer le fichier
                        full_path.unlink()
                        self._print_action("SUPPRIMER", file_path)
                        self._log_action("delete_obsolete", str(full_path), f"MD5: {checksum[:8]}")
                        files_deleted += 1
                        
                    except Exception as e:
                        logger.error(f"Erreur suppression {file_path}: {e}")
                        self._log_error(f"Erreur suppression {file_path}: {e}")
                elif file_path in self.protected_files:
                    logger.warning(f"Fichier protégé ignoré: {file_path}")
        
        return files_deleted

    async def _secure_memory_cleanup(self):
        """Effectue un nettoyage sécurisé de la mémoire."""
        logger.info("Nettoyage sécurisé de la mémoire...")
        
        # Forcer la collecte des objets
        collected = gc.collect()
        logger.info(f"Objets collectés par le garbage collector: {collected}")
        
        self._log_action("memory_cleanup", f"objects_collected: {collected}")

    async def _verify_oracle_integrity(self) -> bool:
        """Teste l'intégrité du système Oracle Enhanced."""
        self._print_info("Vérification de l'intégrité Oracle Enhanced...")
        
        try:
            # Test d'import Oracle
            cmd = [
                "python", "-c",
                "import argumentation_analysis.agents.core.oracle; print('Oracle OK')"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=self.project_root)
            
            if result.returncode == 0 and "Oracle OK" in result.stdout:
                self._print_success("Oracle Enhanced fonctionnel")
                self._log_action("oracle_check", "success")
                return True
            else:
                self._print_error(f"Échec du test Oracle: {result.stderr}")
                self._log_error(f"Échec du test Oracle: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self._print_error("Timeout lors du test Oracle")
            self._log_error("Timeout lors du test Oracle")
            return False
        except Exception as e:
            self._print_error(f"Erreur lors du test Oracle: {e}")
            self._log_error(f"Erreur lors du test Oracle: {e}")
            return False

    def _find_temp_files(self) -> List[Path]:
        """Trouve tous les fichiers temporaires selon les patterns."""
        temp_files = []
        
        for pattern in self.temp_files_patterns:
            temp_files.extend(self.project_root.glob(pattern))
        
        return temp_files

    def _find_additional_reports(self) -> List[Dict[str, str]]:
        """Trouve des rapports supplémentaires selon les patterns."""
        additional_reports = []
        
        for file_path in self.project_root.glob("*.md"):
            if file_path.name.startswith(("RAPPORT_", "TRACE_", "VALIDATION_", "rapport_")):
                if file_path.name not in [r["source"] for r in self.reports_to_move]:
                    additional_reports.append({
                        "source": file_path.name,
                        "dest": "docs/reports/various/"
                    })
        
        return additional_reports

    def _calculate_md5(self, file_path: Path) -> str:
        """Calcule le checksum MD5 d'un fichier."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self._log_error(f"Erreur calcul MD5 {file_path}: {e}")
            return ""

    def _get_file_size_kb(self, file_path: Path) -> str:
        """Retourne la taille d'un fichier en KB."""
        try:
            size_bytes = file_path.stat().st_size
            size_kb = round(size_bytes / 1024, 1)
            return str(size_kb)
        except:
            return "?"

    async def _save_maintenance_log(self, results: Dict[str, Any]):
        """Sauvegarde les logs de maintenance."""
        log_path = self.logs_dir / f"maintenance_log_{self.timestamp}.json"
        
        complete_log = {
            "results": results,
            "log_data": self.log_data,
            "config": {
                "mode": self.config.mode.value,
                "create_backup": self.config.create_backup,
                "batch_size": self.config.batch_size
            }
        }
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(complete_log, f, indent=2, ensure_ascii=False)
        
        self._print_info(f"Logs sauvegardés: {log_path}")

    def _log_action(self, action: str, path: str, details: str = ""):
        """Enregistre une action dans le log."""
        self.log_data["actions"].append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "path": path,
            "details": details
        })

    def _log_error(self, error: str):
        """Enregistre une erreur dans le log."""
        self.log_data["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "error": error
        })

    # === MÉTHODES D'AFFICHAGE ===

    def _print_header(self, title: str):
        """Affiche un en-tête principal."""
        print("\n" + "=" * 80)
        print(f" {title}")
        print("=" * 80)
        print(f"Répertoire: {self.project_root}")
        print(f"Timestamp: {self.timestamp}")
        print()

    def _print_section(self, title: str):
        """Affiche un titre de section."""
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")

    def _print_subsection(self, title: str):
        """Affiche un sous-titre."""
        print(f"\n[{title}]")
        print("-" * 40)

    def _print_action(self, action: str, details: str, reason: str = ""):
        """Affiche une action."""
        color_map = {
            "SUPPRIMER": "\033[91m",  # Rouge
            "DÉPLACER": "\033[95m",   # Magenta
            "CRÉER": "\033[92m",      # Vert
            "SAUVEGARDER": "\033[94m" # Bleu
        }
        color = color_map.get(action, "\033[96m")  # Cyan par défaut
        reset = "\033[0m"
        
        print(f"  {color}[{action}]{reset} {details}")
        if reason:
            print(f"    Raison: {reason}")

    def _print_info(self, message: str):
        """Affiche un message d'information."""
        print(f"\033[96m[INFO]\033[0m {message}")

    def _print_success(self, message: str):
        """Affiche un message de succès."""
        print(f"\033[92m[SUCCESS]\033[0m {message}")

    def _print_error(self, message: str):
        """Affiche un message d'erreur."""
        print(f"\033[91m[ERROR]\033[0m {message}")

    def _print_completion_summary(self, results: Dict[str, Any]):
        """Affiche le résumé final."""
        self._print_section("RÉSUMÉ DE LA MAINTENANCE")
        
        print(f"Statut: {results['status']}")
        print(f"Mode: {results.get('mode', 'N/A')}")
        print(f"Temps d'exécution: {results.get('execution_time', 0):.2f}s")
        
        if results.get("summary"):
            summary = results["summary"]
            for key, value in summary.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        if results.get("backup_created"):
            print(f"Sauvegarde créée: {results['backup_created']}")
        
        print(f"\nActions exécutées: {len(self.log_data['actions'])}")
        print(f"Erreurs rencontrées: {len(self.log_data['errors'])}")
        
        if self.log_data['errors']:
            print("\nErreurs:")
            for error in self.log_data['errors'][-5:]:  # Dernières 5 erreurs
                print(f"  - {error['error']}")

# Factory functions pour création de configurations spécialisées

def create_preview_config(project_root: str = None) -> MaintenanceConfiguration:
    """Crée une configuration pour le mode preview."""
    return MaintenanceConfiguration(
        mode=MaintenanceMode.PREVIEW,
        project_root=project_root
    )

def create_execute_config(project_root: str = None, create_backup: bool = True) -> MaintenanceConfiguration:
    """Crée une configuration pour l'exécution complète."""
    return MaintenanceConfiguration(
        mode=MaintenanceMode.EXECUTE,
        create_backup=create_backup,
        project_root=project_root
    )

def create_cleanup_config(project_root: str = None) -> MaintenanceConfiguration:
    """Crée une configuration pour le nettoyage seulement."""
    return MaintenanceConfiguration(
        mode=MaintenanceMode.CLEANUP_ONLY,
        create_backup=False,
        project_root=project_root
    )

def create_safe_delete_config(project_root: str = None) -> MaintenanceConfiguration:
    """Crée une configuration pour la suppression sécurisée."""
    return MaintenanceConfiguration(
        mode=MaintenanceMode.SAFE_DELETE,
        create_backup=True,
        batch_size=3,  # Plus conservateur
        project_root=project_root
    )

# Interface simplifiée pour utilisation standalone
async def run_maintenance(mode: str = "preview", project_root: str = None, **kwargs) -> Dict[str, Any]:
    """
    Interface simplifiée pour exécuter la maintenance.
    
    Args:
        mode: Mode de maintenance
        project_root: Chemin vers la racine du projet
        **kwargs: Arguments supplémentaires
        
    Returns:
        Résultats de la maintenance
    """
    mode_map = {
        "preview": MaintenanceMode.PREVIEW,
        "execute": MaintenanceMode.EXECUTE,
        "cleanup-only": MaintenanceMode.CLEANUP_ONLY,
        "safe-delete": MaintenanceMode.SAFE_DELETE,
        "decrypt-cleanup": MaintenanceMode.DECRYPT_CLEANUP,
        "migration": MaintenanceMode.MIGRATION,
        "full-maintenance": MaintenanceMode.FULL_MAINTENANCE
    }
    
    maintenance_mode = mode_map.get(mode, MaintenanceMode.PREVIEW)
    
    config = MaintenanceConfiguration(
        mode=maintenance_mode,
        create_backup=kwargs.get('create_backup', True),
        batch_size=kwargs.get('batch_size', 5),
        verbose=kwargs.get('verbose', False),
        project_root=project_root
    )
    
    maintenance_system = UnifiedMaintenanceSystem(config)
    return await maintenance_system.run_maintenance()

if __name__ == "__main__":
    # Interface en ligne de commande
    parser = argparse.ArgumentParser(description="Système de maintenance unifié")
    parser.add_argument("--mode", default="preview",
                       choices=["preview", "execute", "cleanup-only", "safe-delete", 
                               "decrypt-cleanup", "migration", "full-maintenance"],
                       help="Mode de maintenance")
    parser.add_argument("--no-backup", action="store_true",
                       help="Désactiver la création de sauvegarde")
    parser.add_argument("--batch-size", type=int, default=5,
                       help="Taille des batches pour suppression")
    parser.add_argument("--verbose", action="store_true",
                       help="Mode verbeux")
    parser.add_argument("--project-root", help="Chemin vers la racine du projet")
    
    args = parser.parse_args()
    
    async def main():
        print("🔧 Système de Maintenance Unifié")
        print("=" * 50)
        
        kwargs = {
            'create_backup': not args.no_backup,
            'batch_size': args.batch_size,
            'verbose': args.verbose
        }
        
        try:
            results = await run_maintenance(args.mode, args.project_root, **kwargs)
            
            if results["status"] == "SUCCESS":
                print(f"\n✅ Maintenance terminée avec succès!")
                exit_code = 0
            else:
                print(f"\n❌ Maintenance échouée: {results.get('error', 'Erreur inconnue')}")
                exit_code = 1
                
        except Exception as e:
            print(f"\n💥 Erreur critique: {e}")
            exit_code = 1
        
        sys.exit(exit_code)
    
    # Gestion de la boucle d'événements
    import asyncio
    asyncio.run(main())