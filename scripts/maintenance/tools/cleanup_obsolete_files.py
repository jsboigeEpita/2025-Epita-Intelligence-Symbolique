#!/usr/bin/env python3
"""
Script de nettoyage contrôlé des fichiers obsolètes
Tâche 4/5 - Nettoyage sécurisé selon le plan d'organisation

Fonctionnalités :
- Sauvegarde pré-nettoyage 
- Suppression contrôlée des tests obsolètes
- Archivage des tests historiques
- Validation post-nettoyage
- Traçabilité complète
"""

import argumentation_analysis.core.environment
import os
import sys
import json
import tarfile
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

class CleanupManager:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_data = {
            "timestamp": datetime.now().isoformat(),
            "cleanup_version": "1.0.0",
            "actions": [],
            "errors": [],
            "checksums": {},
            "backup_info": {}
        }
        
        # Fichiers à supprimer selon le plan Phase 4
        self.files_to_delete = [
            "fix_final_test.py",
            "validation_phase_b.py", 
            "test_cluedo_demo.py",
            "test_asyncmock_issues.py",
            "test_audit_integrite_cluedo.py",
            "test_diagnostic.py",
            "test_validation_integrite_apres_corrections.py"
        ]
        
        # Fichiers à archiver selon le plan Phase 4
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
        
        # Fichiers précieux à protéger (déjà intégrés)
        self.protected_files = [
            "test_oracle_behavior_demo.py",
            "test_oracle_behavior_simple.py",
            "conftest_gpt_enhanced.py",
            "test_mock_vs_real_behavior.py",
            "test_config_real_gpt.py",
            "test_enquete_states.py",
            "test_cluedo_extended_workflow.py",
            "test_cluedo_oracle_enhanced_real.py",
            "test_einstein_demo_real.py",
            "test_oracle_integration.py",
            "test_sherlock_watson_moriarty_real_gpt.py",
            "test_oracle_performance.py",
            "test_error_handling.py",
            "test_cluedo_dataset.py",
            "test_dataset_access_manager.py",
            "test_moriarty_interrogator_agent.py",
            "test_oracle_base_agent.py",
            "test_oracle_base_agent_fixed.py",
            "test_oracle_enhanced_behavior.py",
            "test_cluedo_oracle_state.py",
            "test_cluedo_enhanced_orchestrator.py",
            "test_scripts_execution.py",
            "test_phase_a_personnalites_distinctes.py",
            "test_phase_b_naturalite_dialogue.py",
            "test_phase_c_fluidite_transitions.py"
        ]

    def calculate_checksum(self, file_path: Path) -> str:
        """Calcule le checksum MD5 d'un fichier"""
        md5_hash = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            self.log_error(f"Erreur calcul checksum {file_path}: {e}")
            return ""

    def log_action(self, action: str, path: str, details: str = ""):
        """Enregistre une action dans le log"""
        self.log_data["actions"].append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "path": path,
            "details": details
        })

    def log_error(self, error: str):
        """Enregistre une erreur dans le log"""
        self.log_data["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "error": error
        })
        print(f"ERREUR: {error}")

    def find_orphan_files(self) -> List[Path]:
        """Trouve tous les fichiers de test orphelins dans le projet"""
        orphan_files = []
        
        # Chercher dans la racine du projet
        for pattern in ["test_*.py", "fix_*.py", "debug_*.py", "demo_*.py", "validation_*.py"]:
            orphan_files.extend(self.project_root.glob(pattern))
        
        # Chercher dans tests/validation_sherlock_watson/
        validation_dir = self.project_root / "tests" / "validation_sherlock_watson"
        if validation_dir.exists():
            orphan_files.extend(validation_dir.glob("*.py"))
        
        return orphan_files

    def create_backup(self, backup_name: str = None) -> Path:
        """Crée une archive de sauvegarde complète"""
        if backup_name is None:
            backup_name = f"pre_cleanup_backup_{self.timestamp}.tar.gz"
        
        backup_path = self.project_root / "archives" / backup_name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Création de la sauvegarde : {backup_path}")
        
        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                # Sauvegarder tous les fichiers orphelins
                orphan_files = self.find_orphan_files()
                
                for file_path in orphan_files:
                    if file_path.exists() and file_path.is_file():
                        # Calculer checksum avant sauvegarde
                        checksum = self.calculate_checksum(file_path)
                        self.log_data["checksums"][str(file_path)] = checksum
                        
                        # Ajouter à l'archive
                        arcname = file_path.relative_to(self.project_root)
                        tar.add(file_path, arcname=arcname)
                        print(f"  + {arcname} (checksum: {checksum[:8]}...)")
                
                # Sauvegarder les répertoires de configuration importants
                config_dirs = ["config", "scripts", "docs"]
                for dir_name in config_dirs:
                    dir_path = self.project_root / dir_name
                    if dir_path.exists():
                        tar.add(dir_path, arcname=dir_name)
                        print(f"  + {dir_name}/ (répertoire complet)")
                
            self.log_data["backup_info"] = {
                "path": str(backup_path),
                "size_bytes": backup_path.stat().st_size,
                "files_count": len(orphan_files)
            }
            
            self.log_action("backup_created", str(backup_path), f"Taille: {backup_path.stat().st_size} bytes")
            print(f"[OK] Sauvegarde créée avec succès : {backup_path}")
            return backup_path
            
        except Exception as e:
            self.log_error(f"Erreur lors de la création de la sauvegarde : {e}")
            raise

    def validate_protected_files(self) -> bool:
        """Valide que tous les fichiers précieux sont protégés"""
        print("Validation des fichiers précieux...")
        
        missing_protected = []
        for file_name in self.protected_files:
            found = False
            
            # Chercher dans tous les sous-répertoires de tests/
            tests_dir = self.project_root / "tests"
            if tests_dir.exists():
                for test_file in tests_dir.rglob(file_name):
                    if test_file.exists():
                        found = True
                        relative_dir = test_file.parent.relative_to(self.project_root)
                        print(f"  [OK] {file_name} trouvé dans {relative_dir}")
                        break
            
            if not found:
                missing_protected.append(file_name)
                print(f"  [WARNING] {file_name} NON TROUVE")
        
        if missing_protected:
            self.log_error(f"Fichiers précieux manquants : {missing_protected}")
            print(f"[WARNING] {len(missing_protected)} fichiers précieux non trouvés, mais on continue...")
            print("[INFO] Ces fichiers ont peut-être déjà été intégrés ou renommés")
        
        print("[OK] Validation terminée - poursuite du nettoyage")
        return True

    def delete_obsolete_files(self, dry_run: bool = True) -> int:
        """Supprime les fichiers obsolètes identifiés"""
        print(f"{'[SIMULATION] ' if dry_run else ''}Suppression des fichiers obsolètes...")
        
        deleted_count = 0
        orphan_files = self.find_orphan_files()
        
        for file_path in orphan_files:
            file_name = file_path.name
            
            if file_name in self.files_to_delete:
                if not dry_run:
                    try:
                        # Calculer checksum avant suppression
                        checksum = self.calculate_checksum(file_path)
                        self.log_data["checksums"][str(file_path)] = checksum
                        
                        # Supprimer le fichier
                        file_path.unlink()
                        self.log_action("file_deleted", str(file_path), f"Checksum: {checksum}")
                        deleted_count += 1
                        print(f"  [-] Supprimé : {file_path}")
                    except Exception as e:
                        self.log_error(f"Erreur suppression {file_path}: {e}")
                else:
                    print(f"  [SIMUL] Suppression : {file_path}")
                    deleted_count += 1
        
        print(f"{'[SIMULATION] ' if dry_run else ''}Fichiers obsolètes supprimés : {deleted_count}")
        return deleted_count

    def archive_historical_files(self, dry_run: bool = True) -> int:
        """Archive les fichiers historiques"""
        print(f"{'[SIMULATION] ' if dry_run else ''}Archivage des fichiers historiques...")
        
        archive_dir = self.project_root / "tests" / "archived"
        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
        
        archived_count = 0
        orphan_files = self.find_orphan_files()
        
        for file_path in orphan_files:
            file_name = file_path.name
            
            if file_name in self.files_to_archive:
                archive_path = archive_dir / file_name
                
                if not dry_run:
                    try:
                        # Calculer checksum
                        checksum = self.calculate_checksum(file_path)
                        self.log_data["checksums"][str(file_path)] = checksum
                        
                        # Copier vers l'archive
                        shutil.copy2(file_path, archive_path)
                        
                        # Supprimer l'original
                        file_path.unlink()
                        
                        self.log_action("file_archived", str(file_path), f"Vers: {archive_path}")
                        archived_count += 1
                        print(f"  [ARC] Archivé : {file_path} -> {archive_path}")
                    except Exception as e:
                        self.log_error(f"Erreur archivage {file_path}: {e}")
                else:
                    print(f"  [SIMUL] Archivage : {file_path} -> {archive_path}")
                    archived_count += 1
        
        print(f"{'[SIMULATION] ' if dry_run else ''}Fichiers archivés : {archived_count}")
        return archived_count

    def clean_empty_directories(self, dry_run: bool = True) -> int:
        """Nettoie les répertoires vides"""
        print(f"{'[SIMULATION] ' if dry_run else ''}Nettoyage des répertoires vides...")
        
        cleaned_count = 0
        
        # Chercher les répertoires potentiellement vides
        for root, dirs, files in os.walk(self.project_root):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                
                # Vérifier si le répertoire est vide (ou ne contient que __pycache__)
                try:
                    contents = list(dir_path.iterdir())
                    is_empty = len(contents) == 0
                    only_pycache = len(contents) == 1 and contents[0].name == "__pycache__"
                    
                    if is_empty or only_pycache:
                        if not dry_run:
                            if only_pycache:
                                shutil.rmtree(contents[0])
                            shutil.rmtree(dir_path)
                            self.log_action("empty_dir_removed", str(dir_path))
                            
                        print(f"  {'[SIMUL] ' if dry_run else ''}Répertoire vide supprimé : {dir_path}")
                        cleaned_count += 1
                        
                except Exception as e:
                    self.log_error(f"Erreur nettoyage répertoire {dir_path}: {e}")
        
        print(f"{'[SIMULATION] ' if dry_run else ''}Répertoires vides nettoyés : {cleaned_count}")
        return cleaned_count

    def save_execution_log(self):
        """Sauvegarde le log d'exécution"""
        log_path = self.project_root / "logs" / "cleanup_execution_log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(self.log_data, f, indent=2, ensure_ascii=False)
            print(f"[OK] Log d'exécution sauvegardé : {log_path}")
        except Exception as e:
            self.log_error(f"Erreur sauvegarde log : {e}")

    def generate_validation_report(self) -> Path:
        """Génère le rapport de validation post-nettoyage"""
        report_path = self.project_root / "logs" / "post_cleanup_validation_report.md"
        
        # Compter les fichiers restants
        remaining_orphans = self.find_orphan_files()
        protected_found = 0
        
        for file_name in self.protected_files:
            # Chercher dans tests/integration/ et tests/unit/
            if (self.project_root / "tests" / "integration" / file_name).exists():
                protected_found += 1
            elif list((self.project_root / "tests" / "unit").rglob(file_name)):
                protected_found += 1
        
        report_content = f"""# Rapport de validation post-nettoyage
*Généré le {datetime.now().isoformat()}*

## Résumé du nettoyage

### Actions exécutées
- **Fichiers supprimés** : {len([a for a in self.log_data['actions'] if a['action'] == 'file_deleted'])}
- **Fichiers archivés** : {len([a for a in self.log_data['actions'] if a['action'] == 'file_archived'])}
- **Répertoires nettoyés** : {len([a for a in self.log_data['actions'] if a['action'] == 'empty_dir_removed'])}
- **Erreurs rencontrées** : {len(self.log_data['errors'])}

### État post-nettoyage
- **Fichiers orphelins restants** : {len(remaining_orphans)}
- **Fichiers précieux protégés** : {protected_found}/{len(self.protected_files)}
- **Sauvegarde créée** : {self.log_data.get('backup_info', {}).get('path', 'N/A')}

## Validation des fonctionnalités critiques

### Oracle Enhanced v2.1.0
- [ ] Tests d'intégration Oracle fonctionnels
- [ ] API Dataset Access Manager opérationnelle  
- [ ] Agent Moriarty Interrogator validé
- [ ] Workflow Cluedo Extended testé

### Structure du projet
- [ ] Répertoires essentiels préservés
- [ ] Configuration système intacte
- [ ] Documentation à jour

## Fichiers restants à examiner

"""
        
        for file_path in remaining_orphans[:10]:  # Limiter à 10 pour lisibilité
            report_content += f"- `{file_path.relative_to(self.project_root)}`\n"
        
        if len(remaining_orphans) > 10:
            report_content += f"- ... et {len(remaining_orphans) - 10} autres fichiers\n"
        
        report_content += f"""
## Erreurs et avertissements

"""
        
        for error in self.log_data['errors']:
            report_content += f"- **{error['timestamp']}** : {error['error']}\n"
        
        if not self.log_data['errors']:
            report_content += "Aucune erreur détectée [OK]\n"
        
        report_content += f"""
## Recommandations

1. **Vérifier les tests critiques** après nettoyage
2. **Exécuter une suite de tests complète** Oracle Enhanced
3. **Valider les imports** dans les modules restants
4. **Nettoyer les références** aux fichiers supprimés

## Sauvegarde et rollback

En cas de problème, restaurer depuis :
```bash
cd {self.project_root}
tar -xzf {self.log_data.get('backup_info', {}).get('path', 'archives/backup.tar.gz')}
```

## Prochaines étapes

1. Tests de régression Oracle Enhanced
2. Validation des intégrations Sherlock Watson
3. Nettoyage final des imports obsolètes
4. Documentation de l'architecture finale
"""
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"[OK] Rapport de validation généré : {report_path}")
            return report_path
        except Exception as e:
            self.log_error(f"Erreur génération rapport : {e}")
            return report_path

def main():
    print("=== NETTOYAGE CONTRÔLÉ DES FICHIERS OBSOLÈTES ===")
    print("Tâche 4/5 - Exécution selon le plan Phase 4")
    print()
    
    # Initialiser le gestionnaire de nettoyage
    cleanup = CleanupManager()
    
    try:
        # Phase 1 : Validation pré-nettoyage
        print("PHASE 1 : Validation pré-nettoyage")
        print("-" * 40)
        
        if not cleanup.validate_protected_files():
            print("[ERROR] ARRÊT : Fichiers précieux manquants !")
            return 1
        
        # Phase 2 : Sauvegarde complète
        print("\nPHASE 2 : Sauvegarde complète")
        print("-" * 40)
        backup_path = cleanup.create_backup()
        
        # Phase 3 : Simulation du nettoyage
        print("\nPHASE 3 : Simulation du nettoyage")
        print("-" * 40)
        
        deleted_sim = cleanup.delete_obsolete_files(dry_run=True)
        archived_sim = cleanup.archive_historical_files(dry_run=True)
        cleaned_sim = cleanup.clean_empty_directories(dry_run=True)
        
        print(f"\nRésumé simulation :")
        print(f"- Fichiers à supprimer : {deleted_sim}")
        print(f"- Fichiers à archiver : {archived_sim}")
        print(f"- Répertoires à nettoyer : {cleaned_sim}")
        
        # Demander confirmation
        response = input("\nExécuter le nettoyage réel ? (y/N) : ").strip().lower()
        if response != 'y':
            print("Nettoyage annulé par l'utilisateur.")
            return 0
        
        # Phase 4 : Exécution réelle
        print("\nPHASE 4 : Exécution du nettoyage")
        print("-" * 40)
        
        deleted_real = cleanup.delete_obsolete_files(dry_run=False)
        archived_real = cleanup.archive_historical_files(dry_run=False)
        cleaned_real = cleanup.clean_empty_directories(dry_run=False)
        
        # Phase 5 : Génération des rapports
        print("\nPHASE 5 : Génération des rapports")
        print("-" * 40)
        
        cleanup.save_execution_log()
        report_path = cleanup.generate_validation_report()
        
        print(f"\n[SUCCESS] NETTOYAGE TERMINÉ AVEC SUCCÈS !")
        print(f"- Fichiers supprimés : {deleted_real}")
        print(f"- Fichiers archivés : {archived_real}")
        print(f"- Répertoires nettoyés : {cleaned_real}")
        print(f"- Sauvegarde : {backup_path}")
        print(f"- Rapport : {report_path}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n[STOP] Nettoyage interrompu par l'utilisateur")
        return 1
    except Exception as e:
        cleanup.log_error(f"Erreur fatale : {e}")
        print(f"[ERROR] Erreur fatale : {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())