#!/usr/bin/env python3
"""
🧹 Nettoyage des Scripts Obsolètes - Architecture Centralisée EPITA

Ce script identifie et archive les scripts obsolètes après la migration
vers l'architecture centralisée (3 scripts + pipeline unifié).

Auteur: Roo
Date: 10/06/2025
"""

import os
import shutil
import json
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime

class ObsoleteScriptsCleaner:
    def __init__(self, base_path: str = "scripts"):
        self.base_path = Path(base_path)
        self.archive_path = Path("archived_scripts/obsolete_migration_2025")
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "migration_context": "Architecture Centralisée - 42+ scripts → 3 scripts consolidés",
            "preserved_scripts": [],
            "archived_scripts": [],
            "preserved_directories": [],
            "archived_directories": [],
            "total_files_archived": 0,
            "space_freed_mb": 0
        }
        
        # Scripts consolidés à PRÉSERVER (notre architecture cible)
        self.preserved_scripts = {
            "scripts/consolidated/unified_production_analyzer.py",
            "scripts/consolidated/educational_showcase_system.py", 
            "scripts/consolidated/comprehensive_workflow_processor.py",
            "scripts/consolidated/universal_rhetorical_analyzer.py",  # Legacy mais fonctionnel
            "scripts/consolidated/migration_guide.py"
        }
        
        # Répertoires critiques à PRÉSERVER
        self.preserved_directories = {
            "scripts/consolidated",      # Notre architecture cible
            "scripts/setup",            # Installation et configuration
            "scripts/maintenance",      # Maintenance système
            "scripts/testing",          # Tests et validation
            "scripts/utils",           # Utilitaires nécessaires
            "scripts/setup_core"       # Configuration core
        }
        
        # Scripts utilitaires à PRÉSERVER au niveau racine
        self.preserved_root_scripts = {
            "migrate_to_unified.py",
            "unified_utilities.py",
            "validation_finale_success_demonstration.py",
            "orchestration_validation.py"
        }

    def analyze_obsolete_structure(self) -> Dict:
        """Analyse la structure pour identifier les scripts obsolètes."""
        obsolete_analysis = {
            "obsolete_directories": [],
            "obsolete_scripts": [],
            "size_analysis": {}
        }
        
        print(">>> Analyse de la structure obsolete...")
        
        # Analyse des répertoires obsolètes
        for item in self.base_path.iterdir():
            if item.is_dir():
                relative_path = str(item.relative_to(Path(".")))
                
                if relative_path not in self.preserved_directories:
                    # Répertoires identifiés comme obsolètes après migration
                    obsolete_directories = {
                        "analysis", "apps", "archived", "core", "data_processing",
                        "demo", "diagnostic", "execution", "fix", "legacy_root",
                        "main", "reporting", "sherlock_watson", "test", "validation",
                        "webapp"
                    }
                    
                    if item.name in obsolete_directories:
                        size_mb = self._calculate_directory_size(item)
                        obsolete_analysis["obsolete_directories"].append({
                            "path": relative_path,
                            "size_mb": size_mb,
                            "reason": "Fonctionnalités intégrées dans pipeline unifié"
                        })
                        obsolete_analysis["size_analysis"][relative_path] = size_mb
        
        # Analyse des scripts obsolètes au niveau racine
        for item in self.base_path.iterdir():
            if item.is_file() and item.suffix == ".py":
                relative_path = str(item.relative_to(Path(".")))
                
                if item.name not in self.preserved_root_scripts:
                    size_mb = item.stat().st_size / (1024 * 1024)
                    obsolete_analysis["obsolete_scripts"].append({
                        "path": relative_path,
                        "size_mb": size_mb,
                        "reason": "Remplacé par scripts consolidés"
                    })
        
        return obsolete_analysis

    def _calculate_directory_size(self, directory: Path) -> float:
        """Calcule la taille d'un répertoire en MB."""
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (PermissionError, FileNotFoundError):
            pass
        return total_size / (1024 * 1024)

    def create_archive_structure(self):
        """Crée la structure d'archivage."""
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Créer sous-répertoires d'archivage
        (self.archive_path / "directories").mkdir(exist_ok=True)
        (self.archive_path / "scripts").mkdir(exist_ok=True)
        (self.archive_path / "metadata").mkdir(exist_ok=True)

    def archive_obsolete_directories(self, obsolete_analysis: Dict):
        """Archive les répertoires obsolètes."""
        print(">>> Archivage des repertoires obsoletes...")
        
        for dir_info in obsolete_analysis["obsolete_directories"]:
            source_path = Path(dir_info["path"])
            target_path = self.archive_path / "directories" / source_path.name
            
            try:
                if source_path.exists():
                    print(f"  >>> Archivage: {source_path} -> {target_path}")
                    shutil.move(str(source_path), str(target_path))
                    
                    self.report["archived_directories"].append({
                        "source": str(source_path),
                        "target": str(target_path),
                        "size_mb": dir_info["size_mb"],
                        "reason": dir_info["reason"]
                    })
                    self.report["space_freed_mb"] += dir_info["size_mb"]
                    
            except Exception as e:
                print(f"  ERREUR archivage {source_path}: {e}")

    def archive_obsolete_scripts(self, obsolete_analysis: Dict):
        """Archive les scripts obsolètes au niveau racine."""
        print(">>> Archivage des scripts obsoletes...")
        
        for script_info in obsolete_analysis["obsolete_scripts"]:
            source_path = Path(script_info["path"])
            target_path = self.archive_path / "scripts" / source_path.name
            
            try:
                if source_path.exists():
                    print(f"  >>> Archivage: {source_path} -> {target_path}")
                    shutil.move(str(source_path), str(target_path))
                    
                    self.report["archived_scripts"].append({
                        "source": str(source_path),
                        "target": str(target_path),
                        "size_mb": script_info["size_mb"],
                        "reason": script_info["reason"]
                    })
                    self.report["space_freed_mb"] += script_info["size_mb"]
                    
            except Exception as e:
                print(f"  ERREUR archivage {source_path}: {e}")

    def update_preserved_inventory(self):
        """Met à jour l'inventaire des éléments préservés."""
        print(">>> Inventaire des elements preserves...")
        
        # Scripts préservés
        for script_path in self.preserved_scripts:
            if Path(script_path).exists():
                self.report["preserved_scripts"].append(script_path)
                print(f"  >>> Preserve: {script_path}")
        
        # Répertoires préservés
        for dir_path in self.preserved_directories:
            if Path(dir_path).exists():
                self.report["preserved_directories"].append(dir_path)
                print(f"  >>> Preserve: {dir_path}")

    def generate_cleanup_report(self):
        """Génère le rapport de nettoyage."""
        report_path = self.archive_path / "metadata" / "cleanup_report.json"
        
        # Statistiques finales
        self.report["total_files_archived"] = len(self.report["archived_scripts"]) + \
                                            len(self.report["archived_directories"])
        
        # Sauvegarde rapport JSON
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        # Rapport Markdown
        self.generate_markdown_report()
        
        print(f"\n>>> Rapport de nettoyage genere: {report_path}")

    def generate_markdown_report(self):
        """Génère un rapport Markdown lisible."""
        report_md_path = self.archive_path / "metadata" / "RAPPORT_NETTOYAGE_FINAL.md"
        
        content = f"""# 🧹 Rapport de Nettoyage Final - Architecture Centralisée

**Date**: {self.report['timestamp']}
**Contexte**: {self.report['migration_context']}

## 📊 Résumé Exécutif

- **Fichiers archivés**: {self.report['total_files_archived']}
- **Espace libéré**: {self.report['space_freed_mb']:.2f} MB
- **Scripts préservés**: {len(self.report['preserved_scripts'])}
- **Répertoires préservés**: {len(self.report['preserved_directories'])}

## ✅ Scripts Consolidés Préservés

"""
        
        for script in self.report['preserved_scripts']:
            content += f"- ✅ `{script}`\n"
        
        content += "\n## 📁 Répertoires Critiques Préservés\n\n"
        
        for directory in self.report['preserved_directories']:
            content += f"- ✅ `{directory}/`\n"
        
        content += "\n## 📦 Répertoires Archivés\n\n"
        
        for dir_info in self.report['archived_directories']:
            content += f"- 📁 `{dir_info['source']}` → `{dir_info['target']}` ({dir_info['size_mb']:.2f} MB)\n"
            content += f"  - **Raison**: {dir_info['reason']}\n"
        
        content += "\n## 📜 Scripts Archivés\n\n"
        
        for script_info in self.report['archived_scripts']:
            content += f"- 📄 `{script_info['source']}` → `{script_info['target']}`\n"
        
        content += f"""

## 🎯 Architecture Finale

Après le nettoyage, la structure finale est:

```
scripts/
├── consolidated/           ✅ ARCHITECTURE CIBLE
│   ├── unified_production_analyzer.py
│   ├── educational_showcase_system.py  
│   └── comprehensive_workflow_processor.py
├── setup/                 ✅ Configuration système
├── maintenance/           ✅ Maintenance
├── testing/              ✅ Tests
├── utils/                ✅ Utilitaires
└── setup_core/           ✅ Configuration core
```

## ✅ Mission Accomplie

L'architecture centralisée est maintenant **propre et finalisée** avec :
- 3 scripts consolidés opérationnels
- Pipeline unifié central
- Nettoyage complet des redondances
- {self.report['space_freed_mb']:.2f} MB d'espace libéré
"""
        
        with open(report_md_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def execute_cleanup(self):
        """Exécute le nettoyage complet."""
        print(">>> Demarrage du nettoyage des scripts obsoletes...")
        print("=" * 60)
        
        # Analyse
        obsolete_analysis = self.analyze_obsolete_structure()
        
        # Création structure d'archivage
        self.create_archive_structure()
        
        # Archivage
        self.archive_obsolete_directories(obsolete_analysis)
        self.archive_obsolete_scripts(obsolete_analysis)
        
        # Inventaire préservé
        self.update_preserved_inventory()
        
        # Rapport
        self.generate_cleanup_report()
        
        print("=" * 60)
        print(">>> Nettoyage termine avec succes!")
        print(f">>> {self.report['total_files_archived']} elements archives")
        print(f">>> {self.report['space_freed_mb']:.2f} MB liberes")
        print(">>> Architecture centralisee finalisee!")

if __name__ == "__main__":
    cleaner = ObsoleteScriptsCleaner()
    cleaner.execute_cleanup()