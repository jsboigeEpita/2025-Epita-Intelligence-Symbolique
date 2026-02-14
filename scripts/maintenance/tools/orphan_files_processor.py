#!/usr/bin/env python3
"""
Script pour traiter les fichiers orphelins identifiés dans VSCode
mais non trackés par Git dans le projet Sherlock Watson.
"""

import argumentation_analysis.core.environment
import os
import json
import shutil
from pathlib import Path
from datetime import datetime


class OrphanFilesProcessor:
    def __init__(self, root_dir="."):
        self.root_dir = Path(root_dir).resolve()
        self.orphan_files = []
        self.target_dir = Path("tests/validation_sherlock_watson")

    def identify_orphan_files(self):
        """Identifie les fichiers orphelins à partir de la liste connue"""
        known_orphans = [
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

        for filename in known_orphans:
            file_path = self.root_dir / filename
            if file_path.exists():
                self.orphan_files.append(
                    {
                        "path": str(file_path),
                        "name": filename,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime),
                        "type": "test" if filename.startswith("test_") else "doc",
                        "target": self.target_dir / filename,
                    }
                )

        return self.orphan_files

    def analyze_file_content(self, file_path):
        """Analyse le contenu d'un fichier pour déterminer son importance"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            analysis = {
                "lines": len(content.splitlines()),
                "size": len(content),
                "has_imports": "import " in content,
                "has_tests": any(
                    word in content.lower() for word in ["test_", "def test", "assert"]
                ),
                "has_oracle": "oracle" in content.lower(),
                "has_sherlock": "sherlock" in content.lower(),
                "is_empty": len(content.strip()) == 0,
            }

            return analysis

        except Exception as e:
            return {"error": str(e)}

    def generate_move_plan(self):
        """Génère un plan de déplacement pour les fichiers orphelins"""
        if not self.orphan_files:
            self.identify_orphan_files()

        move_plan = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_orphan_files": len(self.orphan_files),
                "target_directory": str(self.target_dir),
            },
            "operations": [],
        }

        for orphan in self.orphan_files:
            content_analysis = self.analyze_file_content(orphan["path"])

            operation = {
                "source": orphan["path"],
                "target": str(orphan["target"]),
                "name": orphan["name"],
                "type": orphan["type"],
                "size": orphan["size"],
                "modified": orphan["modified"].isoformat(),
                "content_analysis": content_analysis,
                "action": "move",
                "priority": (
                    "high"
                    if content_analysis.get("has_oracle")
                    or content_analysis.get("has_sherlock")
                    else "medium"
                ),
            }

            move_plan["operations"].append(operation)

        return move_plan

    def execute_move_plan(self, plan, dry_run=True):
        """Exécute le plan de déplacement"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "successful_moves": [],
            "failed_moves": [],
            "created_directories": [],
        }

        # Créer le répertoire cible si nécessaire
        if not dry_run and not self.target_dir.exists():
            self.target_dir.mkdir(parents=True, exist_ok=True)
            results["created_directories"].append(str(self.target_dir))

        for operation in plan["operations"]:
            source = Path(operation["source"])
            target = Path(operation["target"])

            try:
                if dry_run:
                    print(f"[DRY RUN] Déplacerait: {source} -> {target}")
                    results["successful_moves"].append(
                        {
                            "source": str(source),
                            "target": str(target),
                            "status": "would_move",
                        }
                    )
                else:
                    if source.exists():
                        shutil.move(str(source), str(target))
                        print(f"Déplacé: {source} -> {target}")
                        results["successful_moves"].append(
                            {
                                "source": str(source),
                                "target": str(target),
                                "status": "moved",
                            }
                        )
                    else:
                        results["failed_moves"].append(
                            {
                                "source": str(source),
                                "target": str(target),
                                "error": "source_not_found",
                            }
                        )

            except Exception as e:
                results["failed_moves"].append(
                    {"source": str(source), "target": str(target), "error": str(e)}
                )

        return results

    def generate_reports(self):
        """Génère les rapports complets"""
        plan = self.generate_move_plan()

        # Rapport JSON
        json_report_path = self.root_dir / "logs" / "orphan_files_move_plan.json"
        json_report_path.parent.mkdir(exist_ok=True)

        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

        # Rapport Markdown
        md_report_path = self.root_dir / "logs" / "orphan_files_move_plan.md"

        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write("# Plan de Déplacement - Fichiers Orphelins\n\n")
            f.write(f"**Date:** {plan['metadata']['generated_at']}\n")
            f.write(
                f"**Fichiers identifiés:** {plan['metadata']['total_orphan_files']}\n"
            )
            f.write(
                f"**Répertoire cible:** `{plan['metadata']['target_directory']}`\n\n"
            )

            f.write("## Actions de Déplacement\n\n")
            f.write("```bash\n")
            f.write("# Créer le répertoire cible\n")
            f.write(f"mkdir -p {plan['metadata']['target_directory']}\n\n")
            f.write("# Déplacer les fichiers orphelins\n")

            for op in plan["operations"]:
                f.write(f"mv '{op['source']}' '{op['target']}'\n")

            f.write("```\n\n")

            f.write("## Détails des Fichiers\n\n")
            for op in plan["operations"]:
                f.write(f"### {op['name']}\n")
                f.write(f"- **Source:** `{op['source']}`\n")
                f.write(f"- **Cible:** `{op['target']}`\n")
                f.write(f"- **Type:** {op['type']}\n")
                f.write(f"- **Taille:** {op['size']} octets\n")
                f.write(f"- **Modifié:** {op['modified']}\n")
                f.write(f"- **Priorité:** {op['priority']}\n")

                analysis = op["content_analysis"]
                if "error" not in analysis:
                    f.write(f"- **Lignes:** {analysis['lines']}\n")
                    f.write(
                        f"- **Contient Oracle:** {'Oui' if analysis['has_oracle'] else 'Non'}\n"
                    )
                    f.write(
                        f"- **Contient Sherlock:** {'Oui' if analysis['has_sherlock'] else 'Non'}\n"
                    )
                    f.write(
                        f"- **Contient tests:** {'Oui' if analysis['has_tests'] else 'Non'}\n"
                    )
                    f.write(f"- **Vide:** {'Oui' if analysis['is_empty'] else 'Non'}\n")

                f.write("\n")

        return {
            "json_report": str(json_report_path),
            "md_report": str(md_report_path),
            "plan": plan,
        }


def main():
    """Fonction principale"""
    print("=== Processeur de Fichiers Orphelins ===")
    print("Analyse des fichiers orphelins du projet Sherlock Watson...")

    processor = OrphanFilesProcessor()

    # Identifier les fichiers orphelins
    orphans = processor.identify_orphan_files()
    print(f"Fichiers orphelins identifiés: {len(orphans)}")

    # Générer les rapports
    reports = processor.generate_reports()
    print(f"Rapport JSON généré: {reports['json_report']}")
    print(f"Rapport MD généré: {reports['md_report']}")

    # Simulation du déplacement
    plan = reports["plan"]
    results = processor.execute_move_plan(plan, dry_run=True)

    print(f"\n=== Simulation de Déplacement ===")
    print(f"Déplacements réussis: {len(results['successful_moves'])}")
    print(f"Déplacements échoués: {len(results['failed_moves'])}")

    if results["failed_moves"]:
        print("\nErreurs:")
        for failure in results["failed_moves"]:
            print(f"  - {failure['source']}: {failure['error']}")

    print(f"\n✓ Analyse terminée. Consultez les rapports pour les détails.")


if __name__ == "__main__":
    main()
