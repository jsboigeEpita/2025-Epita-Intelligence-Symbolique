"""
Assistant de récupération après crash Git
Oracle Enhanced v2.1.0 - Récupération documentation
"""

import argumentation_analysis.core.environment
import os
import shutil
from pathlib import Path
from datetime import datetime


class RecoveryAssistant:
    """Assistant pour récupération après crash"""

    def __init__(self):
        self.project_root = Path(".")
        self.backup_dir = Path("recovery_backup")
        self.recovery_log = []

    def assess_damage(self) -> dict:
        """Évalue les dégâts du crash"""
        assessment = {
            "critical_files": {},
            "directories": {},
            "git_status": {},
            "recommendations": [],
        }

        # Fichiers critiques
        critical_files = [
            "README.md",
            "CHANGELOG_ORACLE_ENHANCED_V2_1_0.md",
            "docs/README.md",
            "scripts/env/activate_project_env.ps1",
        ]

        for file_path in critical_files:
            path = self.project_root / file_path
            assessment["critical_files"][file_path] = {
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
            }

        # Répertoires importants
        important_dirs = ["docs", "scripts", "logs", "argumentation_analysis"]

        for dir_name in important_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                files_count = len(list(dir_path.rglob("*")))
                assessment["directories"][dir_name] = {
                    "exists": True,
                    "files_count": files_count,
                }
            else:
                assessment["directories"][dir_name] = {
                    "exists": False,
                    "files_count": 0,
                }

        # Générer recommandations
        if not assessment["critical_files"]["README.md"]["exists"]:
            assessment["recommendations"].append("CRITIQUE: Recréer README.md")

        if assessment["directories"]["docs"]["files_count"] < 5:
            assessment["recommendations"].append(
                "IMPORTANT: Reconstituer documentation docs/"
            )

        return assessment

    def create_minimal_documentation(self):
        """Crée une documentation minimale de base"""

        # README.md de base si manquant
        readme_path = self.project_root / "README.md"
        if not readme_path.exists():
            readme_content = f"""# Oracle Enhanced v2.1.0
## Intelligence Symbolique - EPITA 2025

Système d'orchestration d'agents conversationnels Sherlock-Watson-Moriarty avec Oracle Enhanced.

## Démarrage Rapide

```bash
# Activation environnement
powershell -File .\\scripts\\env\\activate_project_env.ps1 -CommandToRun "python --version"

# Tests principaux
python test_oracle_import.py
```

## Structure

- `argumentation_analysis/` - Code principal Oracle Enhanced
- `scripts/` - Scripts de maintenance et d'environnement  
- `docs/` - Documentation technique
- `tests/` - Tests et validation

## Statut

Documentation maintenue et fonctionnelle.

Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)

            self.recovery_log.append("README.md minimal créé")

        # Documentation de base
        docs_dir = self.project_root / "docs"
        docs_dir.mkdir(exist_ok=True)

        docs_readme = docs_dir / "README.md"
        if not docs_readme.exists():
            docs_content = """# Documentation Oracle Enhanced v2.1.0

## Composants Disponibles

- Agents Sherlock-Watson-Moriarty
- Oracle Enhanced avec extensions Phase D
- Scripts de maintenance

## Maintenance

```bash
python scripts/maintenance/analyze_obsolete_documentation.py --quick-scan
```
"""

            with open(docs_readme, "w", encoding="utf-8") as f:
                f.write(docs_content)

            self.recovery_log.append("docs/README.md créé")

    def generate_recovery_report(self) -> str:
        """Génère un rapport de récupération"""
        report_path = (
            f"logs/recovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )

        assessment = self.assess_damage()

        report_content = f"""# Rapport de Récupération Oracle Enhanced v2.1.0

**Date:** {datetime.now().isoformat()}

## Évaluation des Dégâts

### Fichiers Critiques
"""

        for file_path, info in assessment["critical_files"].items():
            status = "✅" if info["exists"] else "❌"
            report_content += f"- {status} `{file_path}` ({info['size']} bytes)\n"

        report_content += "\n### Répertoires\n"

        for dir_name, info in assessment["directories"].items():
            status = "✅" if info["exists"] else "❌"
            count = info["files_count"]
            report_content += f"- {status} `{dir_name}/` ({count} fichiers)\n"

        report_content += "\n## Actions de Récupération\n"

        for action in self.recovery_log:
            report_content += f"- {action}\n"

        report_content += "\n## Recommandations\n"

        for rec in assessment["recommendations"]:
            report_content += f"- {rec}\n"

        # Sauvegarder le rapport
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return report_path


def main():
    """Point d'entrée de récupération"""
    print("Assistant de récupération Oracle Enhanced v2.1.0")

    assistant = RecoveryAssistant()

    # Évaluer les dégâts
    print("Évaluation des dégâts...")
    assessment = assistant.assess_damage()

    # Créer documentation minimale
    print("Création documentation minimale...")
    assistant.create_minimal_documentation()

    # Générer rapport
    print("Génération rapport de récupération...")
    report_path = assistant.generate_recovery_report()

    print(f"Récupération initiale terminée")
    print(f"Rapport: {report_path}")

    return 0


if __name__ == "__main__":
    exit(main())
