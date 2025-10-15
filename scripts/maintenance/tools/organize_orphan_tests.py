#!/usr/bin/env python3
"""
Script d'organisation des tests orphelins identifiés dans la tâche 1/5.

Ce script organise les 51 tests orphelins selon leur valeur et destination :
- À intégrer : Tests uniques avec valeur ajoutée
- À archiver : Tests historiques pour référence 
- À moderniser : Tests anciens mais adaptables
- À supprimer : Tests obsolètes/doublons

import argumentation_analysis.core.environment
Auteur: Assistant Roo
Date: 2025-06-07
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class OrphanTestOrganizer:
    """Organisateur des tests orphelins selon leur valeur et destin."""

    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = Path(workspace_dir)
        self.timestamp = datetime.now().isoformat()

        # Chemins de destination
        self.paths = {
            "integration": self.workspace_dir / "tests" / "integration",
            "archived": self.workspace_dir / "tests" / "archived",
            "deprecated": self.workspace_dir / "tests" / "deprecated",
            "modernized": self.workspace_dir / "tests" / "validation" / "modernized",
        }

        # Manifeste de traçabilité
        self.traceability_manifest = {
            "metadata": {
                "timestamp": self.timestamp,
                "organizer_version": "1.0.0",
                "total_orphan_tests": 51,
                "task": "3/5 - Organisation et tri des tests orphelins",
            },
            "actions_executed": [],
            "files_moved": [],
            "errors": [],
        }

    def load_categorization_data(self) -> Dict:
        """Charge les données de catégorisation de la tâche 1/5."""
        categorization_file = (
            self.workspace_dir / "logs" / "oracle_files_categorization_detailed.json"
        )

        if not categorization_file.exists():
            raise FileNotFoundError(
                f"Fichier de catégorisation introuvable: {categorization_file}"
            )

        with open(categorization_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_orphan_tests_by_priority(self, data: Dict) -> Dict[str, List[Dict]]:
        """Groupe les tests orphelins par catégorie de priorité."""
        orphan_tests = data.get("detailed_analyses", {}).get("tests_orphelins", [])

        categories = {
            "a_integrer": [],  # Priority 7-9 avec integration_potential = "integrated"
            "a_moderniser": [],  # Priority 6-7 avec integration_potential = "test_file"
            "a_archiver": [],  # Priority 4-5 avec valeur historique
            "a_supprimer": [],  # Priority 1-3 ou tests obsolètes
        }

        for test in orphan_tests:
            priority = test.get("recovery_priority", 0)
            integration_potential = test.get("integration_potential", "")
            confidence_score = test.get("confidence_score", 0)
            file_path = test.get("file_path", "")

            # Exclure les dépendances externes (venv_test)
            if "venv_test" in file_path:
                continue

            # Logique de catégorisation
            if priority >= 7 and (
                integration_potential == "integrated" or confidence_score >= 0.7
            ):
                categories["a_integrer"].append(test)
            elif priority >= 6 and integration_potential == "test_file":
                categories["a_moderniser"].append(test)
            elif 4 <= priority <= 5:
                categories["a_archiver"].append(test)
            else:
                categories["a_supprimer"].append(test)

        return categories

    def create_directory_structure(self) -> None:
        """Crée la structure de répertoires pour l'organisation."""
        for path_name, path in self.paths.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"[OK] Répertoire créé/vérifié: {path}")
                self.traceability_manifest["actions_executed"].append(
                    {
                        "action": "create_directory",
                        "path": str(path),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                error_msg = f"Erreur création répertoire {path}: {e}"
                print(f"[ERROR] {error_msg}")
                self.traceability_manifest["errors"].append(
                    {
                        "type": "directory_creation",
                        "message": error_msg,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    def move_test_file(
        self, source_path: str, destination_category: str, reason: str
    ) -> bool:
        """Déplace un fichier de test vers sa destination."""
        source = Path(source_path)

        # Déterminer le répertoire de destination
        if destination_category == "a_integrer":
            dest_dir = self.paths["integration"]
        elif destination_category == "a_moderniser":
            dest_dir = self.paths["modernized"]
        elif destination_category == "a_archiver":
            dest_dir = self.paths["archived"]
        else:  # a_supprimer
            dest_dir = self.paths["deprecated"]

        # Construire le chemin de destination
        relative_path = source.relative_to(self.workspace_dir)
        destination = dest_dir / relative_path.name

        try:
            # Vérifier que le fichier source existe
            if not source.exists():
                print(f"[WARN] Fichier source introuvable: {source}")
                return False

            # Créer les répertoires intermédiaires si nécessaire
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Déplacer le fichier
            shutil.move(str(source), str(destination))

            # Enregistrer l'action
            move_record = {
                "source": str(source),
                "destination": str(destination),
                "category": destination_category,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }

            self.traceability_manifest["files_moved"].append(move_record)
            print(f"[OK] Déplacé: {source.name} -> {destination_category}")
            return True

        except Exception as e:
            error_msg = f"Erreur déplacement {source} -> {destination}: {e}"
            print(f"[ERROR] {error_msg}")
            self.traceability_manifest["errors"].append(
                {
                    "type": "file_move",
                    "source": str(source),
                    "destination": str(destination),
                    "message": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return False

    def organize_tests(self, categorized_tests: Dict[str, List[Dict]]) -> None:
        """Organise les tests selon leur catégorie."""
        total_moved = 0

        for category, tests in categorized_tests.items():
            print(
                f"\n[CAT] Traitement catégorie: {category.upper()} ({len(tests)} tests)"
            )

            for test in tests:
                file_path = test.get("file_path", "")
                recommendation = test.get("recommendation", "")
                priority = test.get("recovery_priority", 0)

                # Convertir le chemin Windows vers un chemin relatif
                if "d:\\2025-Epita-Intelligence-Symbolique\\" in file_path:
                    relative_path = file_path.replace(
                        "d:\\2025-Epita-Intelligence-Symbolique\\", ""
                    )
                    source_path = self.workspace_dir / relative_path.replace("\\", "/")
                else:
                    source_path = Path(file_path)

                reason = f"Priorité {priority} - {recommendation}"

                if self.move_test_file(str(source_path), category, reason):
                    total_moved += 1

        print(f"\n[DONE] Organisation terminée: {total_moved} tests organisés")

    def generate_cleanup_plan(self, categorized_tests: Dict[str, List[Dict]]) -> str:
        """Génère le plan de nettoyage pour la phase 4."""
        plan = [
            "# Plan de nettoyage Phase 4 - Tests orphelins",
            f"*Généré le {self.timestamp}*",
            "",
            "## Résumé de l'organisation",
            "",
        ]

        for category, tests in categorized_tests.items():
            plan.append(
                f"### {category.replace('_', ' ').title()} ({len(tests)} tests)"
            )
            plan.append("")

            for test in tests:
                file_path = test.get("file_path", "")
                filename = Path(file_path).name
                priority = test.get("recovery_priority", 0)
                recommendation = test.get("recommendation", "")

                plan.append(f"- **{filename}** (P{priority}) - {recommendation}")

            plan.append("")

        plan.extend(
            [
                "## Actions de nettoyage recommandées",
                "",
                "### Phase 4A - Validation des intégrations",
                "- [ ] Tester les tests intégrés dans `tests/integration/`",
                "- [ ] Valider la compatibilité Oracle Enhanced v2.1.0",
                "- [ ] Corriger les éventuelles incompatibilités",
                "",
                "### Phase 4B - Modernisation",
                "- [ ] Adapter les tests dans `tests/validation/modernized/`",
                "- [ ] Mettre à jour les APIs obsolètes",
                "- [ ] Harmoniser avec les standards actuels",
                "",
                "### Phase 4C - Archivage sécurisé",
                "- [ ] Compresser les tests archivés",
                "- [ ] Créer un index de recherche",
                "- [ ] Documenter l'historique",
                "",
                "### Phase 4D - Suppression définitive",
                "- [ ] Valider que les tests deprecated ne sont plus référencés",
                "- [ ] Supprimer définitivement après validation",
                "- [ ] Nettoyer les imports et références",
            ]
        )

        return "\n".join(plan)

    def generate_categorization_report(
        self, categorized_tests: Dict[str, List[Dict]]
    ) -> Dict:
        """Génère le rapport de catégorisation détaillé."""
        report = {
            "metadata": {
                "timestamp": self.timestamp,
                "analyzer": "OrphanTestOrganizer v1.0.0",
                "task": "3/5 - Organisation et tri des tests orphelins",
            },
            "summary": {
                "total_tests_analyzed": sum(
                    len(tests) for tests in categorized_tests.values()
                ),
                "categories": {},
            },
            "detailed_categorization": {},
            "integration_analysis": {
                "high_value_tests": [],
                "modernization_candidates": [],
                "archive_worthy": [],
                "deprecation_targets": [],
            },
        }

        for category, tests in categorized_tests.items():
            report["summary"]["categories"][category] = len(tests)
            report["detailed_categorization"][category] = []

            for test in tests:
                test_info = {
                    "file_path": test.get("file_path", ""),
                    "filename": Path(test.get("file_path", "")).name,
                    "priority": test.get("recovery_priority", 0),
                    "confidence_score": test.get("confidence_score", 0),
                    "oracle_references": test.get("oracle_references", {}),
                    "recommendation": test.get("recommendation", ""),
                    "justification": self._get_categorization_justification(
                        test, category
                    ),
                }

                report["detailed_categorization"][category].append(test_info)

                # Analyser pour l'intégration
                if category == "a_integrer":
                    report["integration_analysis"]["high_value_tests"].append(
                        test_info["filename"]
                    )
                elif category == "a_moderniser":
                    report["integration_analysis"]["modernization_candidates"].append(
                        test_info["filename"]
                    )
                elif category == "a_archiver":
                    report["integration_analysis"]["archive_worthy"].append(
                        test_info["filename"]
                    )
                else:
                    report["integration_analysis"]["deprecation_targets"].append(
                        test_info["filename"]
                    )

        return report

    def _get_categorization_justification(self, test: Dict, category: str) -> str:
        """Génère la justification de catégorisation."""
        priority = test.get("recovery_priority", 0)
        confidence = test.get("confidence_score", 0)
        integration_potential = test.get("integration_potential", "")
        oracle_refs = test.get("oracle_references", {}).get("reference_count", 0)

        if category == "a_integrer":
            return f"Test haute valeur (P{priority}, conf={confidence:.2f}, {oracle_refs} refs Oracle) avec potentiel d'intégration {integration_potential}"
        elif category == "a_moderniser":
            return f"Test adaptable (P{priority}) nécessitant modernisation API pour compatibilité Oracle Enhanced v2.1.0"
        elif category == "a_archiver":
            return f"Test historique (P{priority}) conservé pour référence et documentation du projet"
        else:
            return f"Test obsolète (P{priority}, conf={confidence:.2f}) sans valeur ajoutée identifiée"

    def save_manifests(
        self, categorized_tests: Dict, cleanup_plan: str, categorization_report: Dict
    ) -> None:
        """Sauvegarde tous les manifestes et rapports."""
        logs_dir = self.workspace_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Manifeste de traçabilité
        traceability_file = logs_dir / "orphan_tests_categorization.json"
        with open(traceability_file, "w", encoding="utf-8") as f:
            json.dump(self.traceability_manifest, f, indent=2, ensure_ascii=False)
        print(f"[OK] Manifeste de traçabilité: {traceability_file}")

        # Plan de nettoyage
        cleanup_file = logs_dir / "cleanup_plan_phase4.md"
        with open(cleanup_file, "w", encoding="utf-8") as f:
            f.write(cleanup_plan)
        print(f"[OK] Plan de nettoyage: {cleanup_file}")

        # Rapport de catégorisation
        report_file = logs_dir / "orphan_tests_organization_report.md"
        self._write_organization_report(report_file, categorization_report)
        print(f"[OK] Rapport d'organisation: {report_file}")

    def _write_organization_report(
        self, report_file: Path, categorization_report: Dict
    ) -> None:
        """Écrit le rapport d'organisation en Markdown."""
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# Rapport d'organisation des tests orphelins\n\n")
            f.write(f"*Généré le {categorization_report['metadata']['timestamp']}*\n\n")

            # Résumé
            f.write("## Résumé exécutif\n\n")
            summary = categorization_report["summary"]
            f.write(
                f"**Total analysé:** {summary['total_tests_analyzed']} tests orphelins\n\n"
            )

            for category, count in summary["categories"].items():
                f.write(f"- **{category.replace('_', ' ').title()}:** {count} tests\n")
            f.write("\n")

            # Détails par catégorie
            f.write("## Catégorisation détaillée\n\n")

            for category, tests in categorization_report[
                "detailed_categorization"
            ].items():
                f.write(f"### {category.replace('_', ' ').title()}\n\n")

                for test in tests:
                    f.write(f"**{test['filename']}**\n")
                    f.write(f"- Priorité: {test['priority']}\n")
                    f.write(f"- Confiance: {test['confidence_score']:.2f}\n")
                    f.write(
                        f"- Références Oracle: {test['oracle_references'].get('reference_count', 0)}\n"
                    )
                    f.write(f"- Justification: {test['justification']}\n\n")

            # Analyse d'intégration
            f.write("## Analyse d'intégration\n\n")
            integration = categorization_report["integration_analysis"]

            f.write(
                f"**Tests haute valeur à intégrer:** {len(integration['high_value_tests'])}\n"
            )
            for test in integration["high_value_tests"]:
                f.write(f"- {test}\n")
            f.write("\n")

            f.write(
                f"**Candidats à la modernisation:** {len(integration['modernization_candidates'])}\n"
            )
            for test in integration["modernization_candidates"]:
                f.write(f"- {test}\n")
            f.write("\n")

            f.write("## Recommandations\n\n")
            f.write("1. **Intégration immédiate** des tests haute valeur\n")
            f.write("2. **Modernisation progressive** des candidats identifiés\n")
            f.write("3. **Archivage sécurisé** des tests historiques\n")
            f.write("4. **Suppression contrôlée** des tests obsolètes\n")


def main():
    """Point d'entrée principal du script."""
    print("[INFO] Démarrage de l'organisation des tests orphelins...")

    organizer = OrphanTestOrganizer()

    try:
        # Charger les données de catégorisation
        print("[LOAD] Chargement des données de catégorisation...")
        categorization_data = organizer.load_categorization_data()

        # Grouper les tests par priorité
        print("[SORT] Catégorisation des tests orphelins...")
        categorized_tests = organizer.get_orphan_tests_by_priority(categorization_data)

        # Afficher le résumé
        print("\n[SUMMARY] Résumé de la catégorisation:")
        for category, tests in categorized_tests.items():
            print(f"  - {category.replace('_', ' ').title()}: {len(tests)} tests")

        # Créer la structure de répertoires
        print("\n[MKDIR] Création de la structure de répertoires...")
        organizer.create_directory_structure()

        # Organiser les tests (mode simulation par défaut)
        simulate_only = True  # Mode simulation automatique
        print(f"\n[SIM] Mode simulation activé - aucun fichier ne sera déplacé")

        if not simulate_only:
            print("\n[MOVE] Organisation des tests...")
            organizer.organize_tests(categorized_tests)
        else:
            print("[SIM] Simulation de l'organisation des tests...")
            # Simuler l'organisation sans déplacer les fichiers
            for category, tests in categorized_tests.items():
                print(f"[SIM] Catégorie {category.upper()}: {len(tests)} tests")
                for test in tests[:3]:  # Afficher les 3 premiers de chaque catégorie
                    filename = Path(test.get("file_path", "")).name
                    priority = test.get("recovery_priority", 0)
                    print(f"  - {filename} (P{priority})")
                if len(tests) > 3:
                    print(f"  ... et {len(tests) - 3} autres")

        # Générer les rapports
        print("\n[GEN] Génération des manifestes...")
        cleanup_plan = organizer.generate_cleanup_plan(categorized_tests)
        categorization_report = organizer.generate_categorization_report(
            categorized_tests
        )

        # Sauvegarder
        organizer.save_manifests(categorized_tests, cleanup_plan, categorization_report)

        print("\n[SUCCESS] Organisation des tests orphelins terminée avec succès!")
        print("\n[FILES] Fichiers générés:")
        print("  - logs/orphan_tests_categorization.json")
        print("  - logs/cleanup_plan_phase4.md")
        print("  - logs/orphan_tests_organization_report.md")

    except Exception as e:
        print(f"\n[ERROR] Erreur lors de l'organisation: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
