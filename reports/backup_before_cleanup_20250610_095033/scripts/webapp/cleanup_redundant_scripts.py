#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Nettoyage - Scripts PowerShell Redondants
===================================================

Archive et nettoie les scripts PowerShell redondants remplacés par l'orchestrateur unifié.

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class RedundantScriptsCleaner:
    """
    Nettoie les scripts PowerShell redondants remplacés par l'orchestrateur unifié
    """
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.archive_dir = self.project_root / "archives" / "webapp_scripts_replaced" / datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Scripts redondants à archiver
        self.redundant_scripts = [
            "scripts/integration_test_with_trace.ps1",
            "scripts/integration_test_with_trace_robust.ps1", 
            "scripts/integration_test_with_trace_fixed.ps1",
            "scripts/integration_test_trace_working.ps1",
            "scripts/integration_test_trace_simple_success.ps1",
            "scripts/sprint3_final_validation.py",
            "test_backend_fixed.ps1",
            "archives/powershell_legacy/run_integration_tests.ps1"
        ]
        
        # Fichiers de référence à conserver pour l'architecture
        self.reference_files = [
            "project_core/test_runner.py"  # Sera renommé ou déprécié
        ]
        
    def archive_redundant_scripts(self) -> Dict[str, List[str]]:
        """Archive les scripts redondants"""
        print("🗂️ Archivage des scripts redondants...")
        
        # Création répertoire d'archive
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        archived = []
        missing = []
        errors = []
        
        for script_path in self.redundant_scripts:
            script_file = self.project_root / script_path
            
            if script_file.exists():
                try:
                    # Structure d'archive préservant la hiérarchie
                    archive_path = self.archive_dir / script_path
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copie avec métadonnées
                    shutil.copy2(script_file, archive_path)
                    archived.append(script_path)
                    print(f"  ✅ Archivé: {script_path}")
                    
                except Exception as e:
                    errors.append(f"{script_path}: {e}")
                    print(f"  ❌ Erreur archivage {script_path}: {e}")
            else:
                missing.append(script_path)
                print(f"  ⚠️ Introuvable: {script_path}")
        
        return {
            'archived': archived,
            'missing': missing,
            'errors': errors
        }
    
    def create_archive_manifest(self, results: Dict[str, List[str]]):
        """Crée un manifeste de l'archivage"""
        manifest_content = f"""# MANIFESTE D'ARCHIVAGE - SCRIPTS WEBAPP REDONDANTS
# =====================================================
# Date: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
# Orchestrateur unifié: scripts/webapp/unified_web_orchestrator.py
# Configuration: config/webapp_config.yml

## SCRIPTS ARCHIVÉS ({len(results['archived'])})
"""
        
        for script in results['archived']:
            manifest_content += f"- {script}\n"
        
        if results['missing']:
            manifest_content += f"\n## SCRIPTS INTROUVABLES ({len(results['missing'])})\n"
            for script in results['missing']:
                manifest_content += f"- {script}\n"
        
        if results['errors']:
            manifest_content += f"\n## ERREURS D'ARCHIVAGE ({len(results['errors'])})\n"
            for error in results['errors']:
                manifest_content += f"- {error}\n"
        
        manifest_content += f"""
## REMPLACEMENT
Tous ces scripts sont maintenant remplacés par :
- **Orchestrateur principal**: `scripts/webapp/unified_web_orchestrator.py`
- **Configuration centralisée**: `config/webapp_config.yml`
- **Gestionnaires spécialisés**: `scripts/webapp/backend_manager.py`, `frontend_manager.py`, etc.

## USAGE DE REMPLACEMENT
```bash
# Ancien usage (PowerShell)
powershell -File scripts/integration_test_with_trace.ps1 -Headfull

# Nouveau usage (Python unifié)
python scripts/webapp/unified_web_orchestrator.py --visible --integration

# Ou via point d'entrée
python scripts/run_webapp_integration.py --visible
```

## FONCTIONNALITÉS INTÉGRÉES
- ✅ Démarrage backend Flask avec failover de ports
- ✅ Démarrage frontend React optionnel
- ✅ Tests Playwright intégrés
- ✅ Tracing complet des opérations
- ✅ Cleanup automatique des processus
- ✅ Configuration centralisée YAML
- ✅ Cross-platform (Windows/Linux/macOS)
- ✅ Gestion d'erreurs robuste
- ✅ Rapports détaillés Markdown

## AVANTAGES
- 🎯 Point d'entrée unique au lieu de 8+ scripts
- 🔧 Configuration centralisée vs dispersée
- 🚀 Démarrage plus rapide et fiable
- 📊 Tracing uniforme et détaillé
- 🧹 Nettoyage automatique amélioré
- 🔄 Architecture modulaire et extensible
"""
        
        manifest_file = self.archive_dir / "MANIFEST.md"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            f.write(manifest_content)
        
        print(f"📋 Manifeste créé: {manifest_file}")
    
    def remove_archived_scripts(self, archived_scripts: List[str], 
                               confirm: bool = False) -> List[str]:
        """Supprime les scripts archivés du projet"""
        if not confirm:
            print("⚠️ Suppression désactivée (sécurité). Utilisez --confirm pour supprimer.")
            return []
        
        print("🗑️ Suppression des scripts redondants...")
        
        removed = []
        for script_path in archived_scripts:
            script_file = self.project_root / script_path
            
            if script_file.exists():
                try:
                    script_file.unlink()
                    removed.append(script_path)
                    print(f"  🗑️ Supprimé: {script_path}")
                except Exception as e:
                    print(f"  ❌ Erreur suppression {script_path}: {e}")
        
        return removed
    
    def update_documentation(self):
        """Met à jour la documentation du projet"""
        print("📚 Mise à jour documentation...")
        
        # Création/mise à jour README de l'orchestrateur
        readme_content = """# Orchestrateur d'Application Web Unifié

## Vue d'ensemble
L'orchestrateur unifié remplace tous les scripts PowerShell redondants d'intégration web par une solution Python modulaire et cross-platform.

## Usage Rapide
```bash
# Test d'intégration complet (recommandé)
python scripts/webapp/unified_web_orchestrator.py --integration

# Démarrage application seulement
python scripts/webapp/unified_web_orchestrator.py --start

# Tests Playwright seulement
python scripts/webapp/unified_web_orchestrator.py --test

# Mode visible (non-headless)
python scripts/webapp/unified_web_orchestrator.py --integration --visible

# Configuration personnalisée
python scripts/webapp/unified_web_orchestrator.py --config my_config.yml
```

## Architecture
- `unified_web_orchestrator.py` - Orchestrateur principal
- `backend_manager.py` - Gestionnaire backend Flask
- `frontend_manager.py` - Gestionnaire frontend React
- `playwright_runner.py` - Runner tests Playwright
- `process_cleaner.py` - Nettoyage processus
- `config/webapp_config.yml` - Configuration centralisée

## Fonctionnalités
- ✅ Démarrage backend avec failover automatique
- ✅ Tests fonctionnels Playwright intégrés  
- ✅ Tracing complet des opérations
- ✅ Nettoyage automatique des processus
- ✅ Cross-platform (Windows/Linux/macOS)
- ✅ Configuration centralisée YAML

## Scripts Remplacés
Cette solution remplace les 8+ scripts PowerShell redondants précédents :
- `integration_test_with_trace*.ps1` (4 variantes)
- `sprint3_final_validation.py`
- `test_backend_fixed.ps1`
- Et autres scripts d'intégration legacy

Voir `archives/webapp_scripts_replaced/` pour les archives.
"""
        
        readme_file = Path("scripts/webapp/README.md")
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"📖 README créé: {readme_file}")
    
    def generate_migration_summary(self, results: Dict[str, List[str]]) -> str:
        """Génère un résumé de la migration"""
        summary = f"""
🎯 RÉSUMÉ DE MIGRATION - ORCHESTRATEUR WEB UNIFIÉ
================================================

📅 Date: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
📁 Archive: {self.archive_dir}

📊 STATISTIQUES:
- Scripts archivés: {len(results['archived'])}
- Scripts introuvables: {len(results['missing'])}
- Erreurs: {len(results['errors'])}

✅ NOUVEAUX FICHIERS CRÉÉS:
- scripts/webapp/unified_web_orchestrator.py (orchestrateur principal)
- scripts/webapp/backend_manager.py (gestionnaire backend)
- scripts/webapp/frontend_manager.py (gestionnaire frontend)
- scripts/webapp/playwright_runner.py (tests Playwright)
- scripts/webapp/process_cleaner.py (nettoyage processus)
- config/webapp_config.yml (configuration centralisée)

🔄 REMPLACEMENT D'USAGE:
ANCIEN: powershell -File scripts/integration_test_with_trace.ps1
NOUVEAU: python scripts/webapp/unified_web_orchestrator.py --integration

🎉 AVANTAGES:
- Point d'entrée unique au lieu de 8+ scripts
- Configuration centralisée YAML
- Architecture modulaire et extensible  
- Cross-platform Windows/Linux/macOS
- Tracing uniforme et détaillé
- Nettoyage automatique amélioré

🚀 PROCHAINES ÉTAPES:
1. Tester l'orchestrateur: python scripts/webapp/test_orchestrator.py
2. Valider intégration: python scripts/webapp/unified_web_orchestrator.py --integration
3. Mettre à jour scripts appelants
4. Former les développeurs sur le nouvel usage
"""
        return summary

def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nettoyage scripts PowerShell redondants")
    parser.add_argument('--archive', action='store_true', default=True,
                       help='Archive les scripts redondants')
    parser.add_argument('--remove', action='store_true',
                       help='Supprime les scripts après archivage')
    parser.add_argument('--confirm', action='store_true',
                       help='Confirme la suppression des fichiers')
    parser.add_argument('--update-docs', action='store_true', default=True,
                       help='Met à jour la documentation')
    
    args = parser.parse_args()
    
    print("🧹 NETTOYAGE SCRIPTS WEBAPP REDONDANTS")
    print("=" * 50)
    
    cleaner = RedundantScriptsCleaner()
    
    # Archivage
    if args.archive:
        results = cleaner.archive_redundant_scripts()
        cleaner.create_archive_manifest(results)
        
        # Suppression optionnelle
        if args.remove:
            removed = cleaner.remove_archived_scripts(results['archived'], args.confirm)
            results['removed'] = removed
    
    # Documentation
    if args.update_docs:
        cleaner.update_documentation()
    
    # Résumé final
    summary = cleaner.generate_migration_summary(results)
    print(summary)
    
    # Sauvegarde résumé
    summary_file = cleaner.archive_dir / "MIGRATION_SUMMARY.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(f"\n💾 Résumé sauvegardé: {summary_file}")
    print("\n🎉 Nettoyage terminé avec succès!")

if __name__ == "__main__":
    main()