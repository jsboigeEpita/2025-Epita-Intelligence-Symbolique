#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de suppression sécurisée des fichiers redondants - Phase 2
================================================================

Ce script supprime intelligemment les fichiers sources redondants après 
consolidation, conformément au PLAN_CONSOLIDATION_FINALE.md.

import argumentation_analysis.core.environment
Fonctionnalités :
- Vérification de l'existence des fichiers consolidés
- Mode dry-run pour validation
- Sauvegarde de la liste des suppressions
- Vérifications de sécurité multiples
- Rapport détaillé des opérations
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

class SecureFileCleanup:
    """Gestionnaire de suppression sécurisée des fichiers redondants."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()
        self.log_file = self.base_path / "cleanup_redundant_files.log"
        self.backup_list = self.base_path / "deleted_files_backup_list.json"
        self.dry_run = True
        
        # Fichiers consolidés qui DOIVENT exister avant suppression
        self.consolidated_files = [
            "demos/demo_unified_system.py",
            "scripts/maintenance/unified_maintenance.py", 
            "scripts/validation/unified_validation.py",
            "scripts/unified_utilities.py",
            "docs/UNIFIED_SYSTEM_GUIDE.md"
        ]
        
        # Fichiers redondants à supprimer (selon PLAN_CONSOLIDATION_FINALE.md)
        self.redundant_files = {
            "DEMOS": [
                "demo_correction_intelligente.py",
                "demo_orchestrateur_master.py",
                "demo_unified_reporting_system.py",
                "scripts/demo/complete_rhetorical_analysis_demo.py",
                "scripts/demo/demo_conversation_capture_complete.py",
                "scripts/demo/explore_corpus_extracts.py",
                "scripts/demo/run_analysis_with_complete_trace.py",
                "argumentation_analysis/examples/rhetorical_analysis_demo.py"
            ],
            "MAINTENANCE": [
                "scripts/maintenance/depot_cleanup_migration.py",
                "scripts/maintenance/depot_cleanup_migration_simple.py",
                "scripts/utils/cleanup_decrypt_traces.py"
            ],
            "VALIDATION": [
                "scripts/validate_authentic_system.py",
                "scripts/validate_complete_ecosystem.py",
                "scripts/validate_unified_orchestrations.py",
                "scripts/validate_unified_orchestrations_simple.py"
            ],
            "UTILITIES": [
                "scripts/data_processing/integrate_new_source_to_corpus.py",
                "scripts/utils/decrypt_specific_extract.py",
                "scripts/utils/list_encrypted_extracts.py"
            ],
            "DOCS": [
                "docs/GUIDE_INTEGRATION_SYSTEME_RECUPERE.md",
                "docs/OPTIMISATIONS_PERFORMANCE_SYSTEME.md",
                "docs/SYSTEM_UNIVERSEL_GUIDE.md"
            ]
        }
        
        # Fichiers critiques à ne JAMAIS supprimer
        self.protected_files = [
            "agents/",
            "config/",
            "project_core/",
            "services/",
            "orchestration/",
            "cleanup_redundant_files.py",
            "PLAN_CONSOLIDATION_FINALE.md"
        ]

    def log(self, message: str, level: str = "INFO"):
        """Enregistre un message dans le fichier de log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

    def verify_consolidated_files(self) -> bool:
        """Vérifie que tous les fichiers consolidés existent."""
        self.log("=== VÉRIFICATION DES FICHIERS CONSOLIDÉS ===")
        
        missing_files = []
        for file_path in self.consolidated_files:
            full_path = self.base_path / file_path
            if not full_path.exists():
                missing_files.append(file_path)
                self.log(f"[MANQUANT] {file_path}", "ERROR")
            else:
                # Vérifier la taille du fichier
                size = full_path.stat().st_size
                self.log(f"[TROUVE] {file_path} ({size} bytes)")
        
        if missing_files:
            self.log(f"[ECHEC] {len(missing_files)} fichiers consolides manquants!", "ERROR")
            return False
        
        self.log(f"[SUCCES] Tous les {len(self.consolidated_files)} fichiers consolides existent")
        return True

    def get_files_to_delete(self) -> List[Tuple[str, str]]:
        """Retourne la liste des fichiers à supprimer avec leur catégorie."""
        files_to_delete = []
        
        for category, file_list in self.redundant_files.items():
            for file_path in file_list:
                full_path = self.base_path / file_path
                if full_path.exists():
                    files_to_delete.append((file_path, category))
                else:
                    self.log(f"[DEJA SUPPRIME] {file_path}")
        
        return files_to_delete

    def verify_safety(self, files_to_delete: List[Tuple[str, str]]) -> bool:
        """Vérifie la sécurité avant suppression."""
        self.log("=== VÉRIFICATION DE SÉCURITÉ ===")
        
        # Vérifier qu'aucun fichier protégé n'est dans la liste
        for file_path, category in files_to_delete:
            for protected in self.protected_files:
                if protected in file_path:
                    self.log(f"[DANGER] Tentative de suppression d'un fichier protege: {file_path}", "ERROR")
                    return False
        
        # Vérifier que les fichiers consolidés ne sont pas dans la liste
        for file_path, category in files_to_delete:
            if file_path in self.consolidated_files:
                self.log(f"[DANGER] Tentative de suppression d'un fichier consolide: {file_path}", "ERROR")
                return False
        
        self.log(f"[SECURITE] {len(files_to_delete)} fichiers valides pour suppression")
        return True

    def create_backup_list(self, files_to_delete: List[Tuple[str, str]]):
        """Crée une liste de sauvegarde des fichiers à supprimer."""
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(files_to_delete),
            "files_by_category": {},
            "files": []
        }
        
        for file_path, category in files_to_delete:
            full_path = self.base_path / file_path
            
            if category not in backup_data["files_by_category"]:
                backup_data["files_by_category"][category] = []
            
            file_info = {
                "path": file_path,
                "category": category,
                "size": full_path.stat().st_size if full_path.exists() else 0,
                "modified": full_path.stat().st_mtime if full_path.exists() else 0
            }
            
            backup_data["files"].append(file_info)
            backup_data["files_by_category"][category].append(file_path)
        
        with open(self.backup_list, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"[BACKUP] Liste de sauvegarde creee: {self.backup_list}")

    def execute_deletion(self, files_to_delete: List[Tuple[str, str]]) -> Dict[str, int]:
        """Exécute la suppression des fichiers."""
        self.log("=== EXÉCUTION DE LA SUPPRESSION ===")
        
        stats = {
            "deleted": 0,
            "failed": 0,
            "skipped": 0
        }
        
        for file_path, category in files_to_delete:
            full_path = self.base_path / file_path
            
            if not full_path.exists():
                self.log(f"[IGNORE] {file_path} (n'existe pas)")
                stats["skipped"] += 1
                continue
            
            try:
                if self.dry_run:
                    self.log(f"[DRY-RUN] Supprimerait {file_path} ({category})")
                    stats["deleted"] += 1
                else:
                    full_path.unlink()
                    self.log(f"[SUPPRIME] {file_path} ({category})")
                    stats["deleted"] += 1
                    
            except Exception as e:
                self.log(f"[ECHEC] {file_path} - {str(e)}", "ERROR")
                stats["failed"] += 1
        
        return stats

    def generate_report(self, stats: Dict[str, int], files_to_delete: List[Tuple[str, str]]):
        """Génère un rapport détaillé de l'opération."""
        self.log("=== RAPPORT FINAL ===")
        
        # Statistiques par catégorie
        by_category = {}
        for file_path, category in files_to_delete:
            if category not in by_category:
                by_category[category] = 0
            by_category[category] += 1
        
        self.log("[STATS] Statistiques par categorie:")
        for category, count in by_category.items():
            self.log(f"   {category}: {count} fichiers")
        
        self.log("[STATS] Statistiques globales:")
        self.log(f"   Total traites: {len(files_to_delete)}")
        self.log(f"   Supprimes: {stats['deleted']}")
        self.log(f"   Echecs: {stats['failed']}")
        self.log(f"   Ignores: {stats['skipped']}")
        
        mode = "DRY-RUN" if self.dry_run else "REEL"
        self.log(f"[MODE] Mode d'execution: {mode}")

    def run(self, dry_run: bool = True):
        """Exécute le processus complet de nettoyage."""
        self.dry_run = dry_run
        
        self.log("=" * 60)
        self.log("[DEBUT] DEMARRAGE DU NETTOYAGE DES FICHIERS REDONDANTS")
        self.log(f"[DIR] Repertoire de base: {self.base_path}")
        self.log(f"[MODE] Mode: {'DRY-RUN' if dry_run else 'SUPPRESSION REELLE'}")
        self.log("=" * 60)
        
        # Étape 1: Vérifier les fichiers consolidés
        if not self.verify_consolidated_files():
            self.log("[ARRET] Fichiers consolides manquants", "ERROR")
            return False
        
        # Étape 2: Obtenir la liste des fichiers à supprimer
        files_to_delete = self.get_files_to_delete()
        if not files_to_delete:
            self.log("[INFO] Aucun fichier redondant trouve a supprimer")
            return True
        
        # Étape 3: Vérification de sécurité
        if not self.verify_safety(files_to_delete):
            self.log("[ARRET] Verification de securite echouee", "ERROR")
            return False
        
        # Étape 4: Créer la liste de sauvegarde
        self.create_backup_list(files_to_delete)
        
        # Étape 5: Exécuter la suppression
        stats = self.execute_deletion(files_to_delete)
        
        # Étape 6: Générer le rapport
        self.generate_report(stats, files_to_delete)
        
        self.log("[TERMINE] NETTOYAGE TERMINE AVEC SUCCES")
        return stats["failed"] == 0


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Suppression sécurisée des fichiers redondants")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Mode simulation (défaut)")
    parser.add_argument("--execute", action="store_true",
                       help="Exécution réelle (supprime les fichiers)")
    parser.add_argument("--force", action="store_true",
                       help="Force l'exécution sans demander confirmation")
    parser.add_argument("--base-path", default=".",
                       help="Chemin de base du projet")
    
    args = parser.parse_args()
    
    # Si --execute est spécifié, désactiver le dry-run
    dry_run = not args.execute
    
    cleanup = SecureFileCleanup(args.base_path)
    
    if dry_run:
        print("[DRY-RUN] Mode simulation: Aucun fichier ne sera supprime")
        print("          Utilisez --execute pour la suppression reelle")
    else:
        print("[ATTENTION] Mode SUPPRESSION REELLE: Les fichiers seront definitivement supprimes!")
        if not args.force:
            response = input("Êtes-vous sûr de vouloir continuer? (oui/non): ")
            if response.lower() not in ['oui', 'yes', 'y']:
                print("[ANNULE] Operation annulee par l'utilisateur")
                return
        else:
            print("[FORCE] Execution forcee, pas de confirmation demandee")
    
    success = cleanup.run(dry_run)
    
    if success:
        print(f"\n[SUCCES] Nettoyage termine avec succes!")
        print(f"[LOG] Log detaille: {cleanup.log_file}")
        if not dry_run:
            print(f"[BACKUP] Liste de sauvegarde: {cleanup.backup_list}")
    else:
        print(f"\n[ERREUR] Nettoyage echoue - voir {cleanup.log_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()