#!/usr/bin/env python3
"""
Script d'inventaire rapide des fichiers sous contrôle Git avec recommandations détaillées
Version accélérée sans tests de fonctionnalité
"""

import argumentation_analysis.core.environment
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict
from collections import defaultdict


@dataclass
class FileAnalysis:
    path: str
    status: str
    file_type: str
    size: int
    modified: str
    category: str
    recommendation: str
    reason: str


class GitFilesInventoryFast:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.files_analysis: List[FileAnalysis] = []
        self.categories = {
            "oracle": ["oracle", "cluedo", "sherlock", "watson", "moriarty"],
            "test": ["test_", "tests/", "conftest"],
            "documentation": [".md", "README", "GUIDE"],
            "configuration": [".ini", ".yaml", ".yml", ".json", ".env"],
            "script": [".py", ".ps1", ".sh"],
            "archive": ["backup", "archive", "_archive"],
            "log": ["log", ".log"],
            "temporary": ["temp", "_temp", ".tmp"],
        }

    def run_git_command(self, command: List[str]) -> str:
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Erreur Git: {e}")
            return ""

    def get_tracked_files(self) -> List[str]:
        output = self.run_git_command(["ls-files"])
        return [f for f in output.split("\n") if f.strip()]

    def get_untracked_files(self) -> List[str]:
        output = self.run_git_command(["ls-files", "--others", "--exclude-standard"])
        return [f for f in output.split("\n") if f.strip()]

    def get_git_status(self) -> Dict[str, List[str]]:
        status_output = self.run_git_command(["status", "--porcelain"])

        status_files = {"modified": [], "added": [], "deleted": [], "untracked": []}

        for line in status_output.split("\n"):
            if not line.strip():
                continue

            status_code = line[:2]
            file_path = line[3:].strip()

            if status_code.startswith("??"):
                status_files["untracked"].append(file_path)
            elif status_code.startswith(" D"):
                status_files["deleted"].append(file_path)
            elif status_code.startswith("M") or status_code.startswith(" M"):
                status_files["modified"].append(file_path)
            elif status_code.startswith("A"):
                status_files["added"].append(file_path)

        return status_files

    def find_orphan_files(self) -> List[str]:
        orphan_files = []

        vscode_visible = [
            "test_import.py",
            "test_oracle_import.py",
            "test_oracle_fixes.py",
            "test_oracle_fixes_simple.py",
            "test_asyncmock_issues.py",
            "test_group1_fixes.py",
            "test_group1_simple.py",
            "groupe1_corrections_summary.md",
            "test_group2_corrections.py",
            "test_group2_corrections_simple.py",
            "test_groupe2_validation.py",
            "test_groupe2_validation_simple.py",
        ]

        for file_name in vscode_visible:
            file_path = self.project_root / file_name
            if file_path.exists():
                orphan_files.append(file_name)

        return orphan_files

    def categorize_file(self, file_path: str) -> str:
        file_lower = file_path.lower()

        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword in file_lower:
                    return category

        if file_path.endswith((".py", ".ipynb")):
            return "code"
        elif file_path.endswith((".md", ".txt", ".rst")):
            return "documentation"
        elif file_path.endswith((".json", ".yaml", ".yml", ".ini", ".cfg")):
            return "configuration"
        else:
            return "other"

    def get_file_info(self, file_path: str) -> Dict:
        full_path = self.project_root / file_path

        info = {"exists": full_path.exists(), "size": 0, "modified": "unknown"}

        if full_path.exists():
            try:
                stat = full_path.stat()
                info["size"] = stat.st_size
                info["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except OSError:
                pass

        return info

    def generate_recommendation(
        self, file_path: str, status: str, category: str, file_info: Dict
    ) -> tuple:
        if status == "deleted":
            return (
                "confirm_delete",
                "Fichier supprimé dans Git - confirmer la suppression",
            )

        if status == "orphan":
            if file_path.startswith("test_"):
                return (
                    "move",
                    f"Fichier de test orphelin - déplacer vers tests/validation_sherlock_watson/",
                )
            elif file_path.endswith(".md"):
                return "move", "Fichier de documentation - déplacer vers docs/"
            else:
                return "delete", "Fichier orphelin sans emplacement évident"

        if category == "archive" or "backup" in file_path:
            if status == "untracked":
                return (
                    "delete",
                    "Archive temporaire non nécessaire sous contrôle de version",
                )
            else:
                return "keep", "Archive sous contrôle de version - conserver"

        if category == "log" or file_path.startswith("logs/"):
            if status == "untracked":
                return "delete", "Fichier de log temporaire"
            else:
                return "keep", "Log important sous contrôle de version"

        if "/recovered/" in file_path:
            return "integrate", "Code récupéré - examiner pour intégration"

        if category == "oracle" or "sherlock" in file_path.lower():
            return "keep", "Fichier Oracle/Sherlock - conserver et examiner"

        if category == "documentation":
            if file_info["size"] > 100:
                return "keep", "Documentation non vide - conserver"
            else:
                return "review", "Documentation potentiellement vide - examiner"

        if category == "configuration":
            return "keep", "Fichier de configuration - conserver"

        if "maintenance" in file_path and status == "untracked":
            return "keep", "Script de maintenance récent - conserver"

        if status == "tracked":
            return "keep", "Fichier sous contrôle Git - conserver par défaut"
        else:
            return "review", "Fichier à examiner individuellement"

    def analyze_file(self, file_path: str, status: str) -> FileAnalysis:
        file_info = self.get_file_info(file_path)
        category = self.categorize_file(file_path)

        recommendation, reason = self.generate_recommendation(
            file_path, status, category, file_info
        )

        return FileAnalysis(
            path=file_path,
            status=status,
            file_type=Path(file_path).suffix or "no_extension",
            size=file_info["size"],
            modified=file_info["modified"],
            category=category,
            recommendation=recommendation,
            reason=reason,
        )

    def run_inventory(self) -> None:
        print("[INFO] Demarrage de l'inventaire rapide des fichiers Git...")

        print("[INFO] Analyse des fichiers trackes...")
        tracked_files = self.get_tracked_files()
        for file_path in tracked_files:
            analysis = self.analyze_file(file_path, "tracked")
            self.files_analysis.append(analysis)

        print("📋 Analyse des fichiers non-trackés...")
        untracked_files = self.get_untracked_files()
        for file_path in untracked_files:
            analysis = self.analyze_file(file_path, "untracked")
            self.files_analysis.append(analysis)

        print("📋 Analyse des fichiers supprimés...")
        git_status = self.get_git_status()
        for file_path in git_status["deleted"]:
            analysis = self.analyze_file(file_path, "deleted")
            self.files_analysis.append(analysis)

        print("📋 Analyse des fichiers orphelins...")
        orphan_files = self.find_orphan_files()
        for file_path in orphan_files:
            analysis = self.analyze_file(file_path, "orphan")
            self.files_analysis.append(analysis)

        print(f"✅ Inventaire terminé - {len(self.files_analysis)} fichiers analysés")

    def generate_reports(self) -> None:
        self.generate_detailed_report()
        self.generate_decision_matrix()
        self.generate_action_plan()
        print("📊 Tous les rapports ont été générés dans logs/")

    def generate_detailed_report(self) -> None:
        report_path = self.project_root / "logs" / "git_files_analysis_report.md"
        stats = self.calculate_statistics()

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Rapport d'Analyse des Fichiers Git\n\n")
            f.write(
                f"**Date de génération:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write(f"**Projet:** Intelligence Symbolique - Sherlock Watson\n")
            f.write(f"**Total de fichiers analysés:** {len(self.files_analysis)}\n\n")
            f.write(f"## 📊 Statistiques Générales\n\n")
            f.write(f"### Par Statut\n")
            for status, count in stats["by_status"].items():
                f.write(f"- **{status}:** {count} fichiers\n")

            f.write(f"\n### Par Catégorie\n")
            for category, count in stats["by_category"].items():
                f.write(f"- **{category}:** {count} fichiers\n")

            f.write(f"\n### Par Recommandation\n")
            for recommendation, count in stats["by_recommendation"].items():
                f.write(f"- **{recommendation}:** {count} fichiers\n")

            f.write(f"\n## 🔍 Analyse Détaillée par Catégorie\n\n")

            by_category = defaultdict(list)
            for analysis in self.files_analysis:
                by_category[analysis.category].append(analysis)

            for category, files in by_category.items():
                f.write(f"### {category.upper()}\n\n")

                for file_analysis in files:
                    f.write(f"**📁 {file_analysis.path}**\n")
                    f.write(f"- Status: `{file_analysis.status}`\n")
                    f.write(f"- Taille: {file_analysis.size} octets\n")
                    f.write(f"- Modifié: {file_analysis.modified}\n")
                    f.write(f"- **Recommandation: `{file_analysis.recommendation}`**\n")
                    f.write(f"- Raison: {file_analysis.reason}\n")
                    f.write(f"\n")

                f.write(f"\n")

        print(f"📄 Rapport détaillé généré: {report_path}")

    def generate_decision_matrix(self) -> None:
        matrix_path = self.project_root / "logs" / "git_files_decision_matrix.json"

        matrix = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_files": len(self.files_analysis),
                "project": "Intelligence Symbolique - Sherlock Watson",
            },
            "files": [asdict(analysis) for analysis in self.files_analysis],
            "statistics": self.calculate_statistics(),
        }

        with open(matrix_path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)

        print(f"📊 Matrice de décision générée: {matrix_path}")

    def generate_action_plan(self) -> None:
        plan_path = self.project_root / "logs" / "git_cleanup_action_plan.md"

        by_recommendation = defaultdict(list)
        for analysis in self.files_analysis:
            by_recommendation[analysis.recommendation].append(analysis)

        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(f"# Plan d'Actions - Nettoyage Git\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## 🎯 Actions Prioritaires\n\n")

            priority_order = [
                "delete",
                "move",
                "refactor",
                "integrate",
                "review",
                "keep",
            ]

            for recommendation in priority_order:
                if recommendation in by_recommendation:
                    files = by_recommendation[recommendation]
                    f.write(f"### {recommendation.upper()} ({len(files)} fichiers)\n\n")

                    if recommendation == "delete":
                        f.write("```bash\n")
                        for file_analysis in files:
                            f.write(f"rm -f '{file_analysis.path}'\n")
                        f.write("```\n\n")

                    elif recommendation == "move":
                        f.write("```bash\n")
                        for file_analysis in files:
                            if file_analysis.path.startswith("test_"):
                                f.write(
                                    f"mv '{file_analysis.path}' tests/validation_sherlock_watson/\n"
                                )
                            elif file_analysis.path.endswith(".md"):
                                f.write(f"mv '{file_analysis.path}' docs/\n")
                        f.write("```\n\n")

                    for file_analysis in files:
                        f.write(f"- `{file_analysis.path}` - {file_analysis.reason}\n")

                    f.write(f"\n")

        print(f"📋 Plan d'actions généré: {plan_path}")

    def calculate_statistics(self) -> Dict:
        stats = {
            "by_status": defaultdict(int),
            "by_category": defaultdict(int),
            "by_recommendation": defaultdict(int),
            "by_file_type": defaultdict(int),
        }

        for analysis in self.files_analysis:
            stats["by_status"][analysis.status] += 1
            stats["by_category"][analysis.category] += 1
            stats["by_recommendation"][analysis.recommendation] += 1
            stats["by_file_type"][analysis.file_type] += 1

        return {k: dict(v) for k, v in stats.items()}


def main():
    print("🚀 Script d'Inventaire Rapide des Fichiers Git - Sherlock Watson")
    print("=" * 60)

    os.makedirs("logs", exist_ok=True)

    inventory = GitFilesInventoryFast()
    inventory.run_inventory()
    inventory.generate_reports()

    print("\n✅ Inventaire terminé avec succès!")
    print("\n📁 Fichiers générés:")
    print("- logs/git_files_analysis_report.md")
    print("- logs/git_files_decision_matrix.json")
    print("- logs/git_cleanup_action_plan.md")


if __name__ == "__main__":
    main()
