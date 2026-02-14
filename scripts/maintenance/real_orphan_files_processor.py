#!/usr/bin/env python3
"""
Script pour traiter les vrais fichiers orphelins identifiés par Git
dans le projet Sherlock Watson.
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


class RealOrphanFilesProcessor:
    def __init__(self, root_dir="."):
        self.root_dir = Path(root_dir).resolve()
        self.orphan_files = []

    def get_git_untracked_files(self):
        """Obtient la liste des fichiers non-trackés par Git"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            untracked_files = []
            for line in result.stdout.strip().split("\n"):
                if line.startswith("??"):
                    file_path = line[3:].strip()
                    untracked_files.append(file_path)

            return untracked_files

        except subprocess.CalledProcessError as e:
            print(f"Erreur Git: {e}")
            return []

    def categorize_file(self, file_path):
        """Catégorise un fichier selon son type et contenu"""
        path_obj = Path(file_path)

        categories = {
            "logs": "logs/" in str(file_path),
            "archives": "archives/" in str(file_path) or "backup" in str(file_path),
            "maintenance_scripts": "scripts/maintenance/" in str(file_path),
            "recovered_code": "/recovered/" in str(file_path),
            "documentation": path_obj.suffix in [".md", ".txt", ".rst"],
            "configuration": path_obj.suffix in [".json", ".yml", ".yaml", ".toml"],
            "python_code": path_obj.suffix == ".py",
            "test_files": "test_" in path_obj.name or "/tests/" in str(file_path),
            "oracle_related": any(
                word in str(file_path).lower()
                for word in ["oracle", "sherlock", "watson"]
            ),
        }

        # Déterminer la catégorie principale
        if categories["logs"]:
            return "logs"
        elif categories["archives"]:
            return "archives"
        elif categories["maintenance_scripts"]:
            return "maintenance_scripts"
        elif categories["recovered_code"]:
            return "recovered_code"
        elif categories["test_files"]:
            return "test_files"
        elif categories["oracle_related"]:
            return "oracle_related"
        elif categories["documentation"]:
            return "documentation"
        elif categories["configuration"]:
            return "configuration"
        else:
            return "other"

    def get_recommendation(self, file_path, category):
        """Détermine la recommandation pour un fichier"""
        path_obj = Path(file_path)

        # Règles de recommandation
        if category == "logs":
            if "git_files" in str(file_path) or "orphan_files" in str(file_path):
                return "keep", "Rapport d'inventaire récent - conserver"
            else:
                return "delete", "Fichier de log temporaire - supprimer"

        elif category == "archives":
            if "backup" in str(file_path) and any(
                ext in str(file_path) for ext in [".tar.gz", ".zip"]
            ):
                return (
                    "delete",
                    "Archive temporaire non nécessaire sous contrôle de version",
                )
            else:
                return "keep", "Archive à examiner avant suppression"

        elif category == "maintenance_scripts":
            return "keep", "Script de maintenance récent - conserver"

        elif category == "recovered_code":
            return "integrate", "Code récupéré - examiner pour intégration"

        elif category == "test_files":
            if "validation" in str(file_path):
                return (
                    "integrate",
                    "Test de validation - déplacer vers tests/validation/",
                )
            else:
                return (
                    "integrate",
                    "Fichier de test - intégrer dans la structure appropriée",
                )

        elif category == "oracle_related":
            return "keep", "Fichier Oracle/Sherlock - conserver et examiner"

        elif category == "documentation":
            return "keep", "Documentation - examiner et conserver"

        elif category == "configuration":
            return "keep", "Configuration - examiner et conserver"

        else:
            return "review", "Fichier à examiner individuellement"

    def analyze_file_content(self, file_path):
        """Analyse le contenu d'un fichier pour déterminer son importance"""
        try:
            full_path = self.root_dir / file_path
            if not full_path.exists():
                return {"error": "file_not_found"}

            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            analysis = {
                "lines": len(content.splitlines()),
                "size": len(content),
                "has_imports": "import " in content,
                "has_functions": "def " in content,
                "has_classes": "class " in content,
                "has_tests": any(
                    word in content.lower() for word in ["test_", "def test", "assert"]
                ),
                "has_oracle": "oracle" in content.lower(),
                "has_sherlock": "sherlock" in content.lower(),
                "is_empty": len(content.strip()) == 0,
                "first_lines": content.splitlines()[:5] if content.splitlines() else [],
            }

            return analysis

        except Exception as e:
            return {"error": str(e)}

    def process_orphan_files(self):
        """Traite tous les fichiers orphelins"""
        untracked_files = self.get_git_untracked_files()

        for file_path in untracked_files:
            full_path = self.root_dir / file_path

            if full_path.exists():
                category = self.categorize_file(file_path)
                recommendation, reason = self.get_recommendation(file_path, category)
                content_analysis = self.analyze_file_content(file_path)

                file_info = {
                    "path": file_path,
                    "category": category,
                    "recommendation": recommendation,
                    "reason": reason,
                    "size": full_path.stat().st_size if full_path.exists() else 0,
                    "modified": (
                        datetime.fromtimestamp(full_path.stat().st_mtime).isoformat()
                        if full_path.exists()
                        else None
                    ),
                    "content_analysis": content_analysis,
                }

                self.orphan_files.append(file_info)

        return self.orphan_files

    def generate_action_plan(self):
        """Génère un plan d'actions détaillé"""
        if not self.orphan_files:
            self.process_orphan_files()

        # Grouper par recommandation
        actions = {"delete": [], "keep": [], "integrate": [], "review": []}

        for file_info in self.orphan_files:
            recommendation = file_info["recommendation"]
            actions[recommendation].append(file_info)

        # Générer le plan
        plan = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_orphan_files": len(self.orphan_files),
                "summary": {
                    "delete": len(actions["delete"]),
                    "keep": len(actions["keep"]),
                    "integrate": len(actions["integrate"]),
                    "review": len(actions["review"]),
                },
            },
            "actions": actions,
        }

        return plan

    def generate_reports(self):
        """Génère les rapports complets"""
        plan = self.generate_action_plan()

        # Rapport JSON
        json_report_path = (
            self.root_dir / "logs" / "complete_orphan_files_action_plan.json"
        )
        json_report_path.parent.mkdir(exist_ok=True)

        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

        # Rapport Markdown
        md_report_path = self.root_dir / "logs" / "complete_orphan_files_action_plan.md"

        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write("# Plan d'Actions Complet - Fichiers Orphelins Git\n\n")
            f.write(f"**Date:** {plan['metadata']['generated_at']}\n")
            f.write(f"**Total fichiers:** {plan['metadata']['total_orphan_files']}\n\n")

            f.write("## Résumé des Actions\n\n")
            for action, count in plan["metadata"]["summary"].items():
                f.write(f"- **{action.upper()}**: {count} fichiers\n")
            f.write("\n")

            # Actions DELETE
            if plan["actions"]["delete"]:
                f.write(
                    "## DELETE ({} fichiers)\n\n".format(len(plan["actions"]["delete"]))
                )
                f.write("```bash\n")
                for file_info in plan["actions"]["delete"]:
                    f.write(f"rm -f '{file_info['path']}'\n")
                f.write("```\n\n")

                for file_info in plan["actions"]["delete"]:
                    f.write(f"- `{file_info['path']}` - {file_info['reason']}\n")
                f.write("\n")

            # Actions INTEGRATE
            if plan["actions"]["integrate"]:
                f.write(
                    "## INTEGRATE ({} fichiers)\n\n".format(
                        len(plan["actions"]["integrate"])
                    )
                )
                for file_info in plan["actions"]["integrate"]:
                    f.write(f"- `{file_info['path']}` - {file_info['reason']}\n")
                f.write("\n")

            # Actions REVIEW
            if plan["actions"]["review"]:
                f.write(
                    "## REVIEW ({} fichiers)\n\n".format(len(plan["actions"]["review"]))
                )
                for file_info in plan["actions"]["review"]:
                    f.write(f"- `{file_info['path']}` - {file_info['reason']}\n")
                f.write("\n")

            # Actions KEEP (liste abrégée)
            if plan["actions"]["keep"]:
                f.write(
                    "## KEEP ({} fichiers)\n\n".format(len(plan["actions"]["keep"]))
                )
                f.write("### Scripts de maintenance et rapports importants\n")
                for file_info in plan["actions"]["keep"][:10]:  # Top 10
                    f.write(f"- `{file_info['path']}` - {file_info['reason']}\n")

                if len(plan["actions"]["keep"]) > 10:
                    f.write(
                        f"\n... et {len(plan['actions']['keep']) - 10} autres fichiers à conserver.\n"
                    )
                f.write("\n")

            # Détails par catégorie
            f.write("## Analyse par Catégorie\n\n")
            categories = {}
            for file_info in self.orphan_files:
                cat = file_info["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(file_info)

            for category, files in categories.items():
                f.write(
                    f"### {category.replace('_', ' ').title()} ({len(files)} fichiers)\n"
                )
                for file_info in files:
                    f.write(
                        f"- `{file_info['path']}` → **{file_info['recommendation'].upper()}**\n"
                    )
                f.write("\n")

        return {
            "json_report": str(json_report_path),
            "md_report": str(md_report_path),
            "plan": plan,
        }


def main():
    """Fonction principale"""
    print("=== Processeur de Fichiers Orphelins Git ===")
    print("Analyse des fichiers non-trackés par Git...")

    processor = RealOrphanFilesProcessor()

    # Traiter les fichiers orphelins
    orphans = processor.process_orphan_files()
    print(f"Fichiers orphelins identifiés: {len(orphans)}")

    # Générer les rapports
    reports = processor.generate_reports()
    print(f"Rapport JSON généré: {reports['json_report']}")
    print(f"Rapport MD généré: {reports['md_report']}")

    # Statistiques
    plan = reports["plan"]
    print(f"\n=== Statistiques ===")
    for action, count in plan["metadata"]["summary"].items():
        print(f"{action.upper()}: {count} fichiers")

    print(f"\n✓ Analyse terminée. Consultez les rapports pour les détails.")


if __name__ == "__main__":
    main()
