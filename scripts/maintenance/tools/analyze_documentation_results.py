"""
Analyseur des résultats de documentation obsolète pour priorisation des corrections
Oracle Enhanced v2.1.0 - Mise à jour Documentation
"""

import json
import re
from pathlib import Path
from typing import Dict, List


class DocumentationUpdatePrioritizer:
    """Priorise les corrections de documentation basées sur l'analyse"""

    def __init__(self, analysis_file: str):
        with open(analysis_file, "r", encoding="utf-8") as f:
            self.analysis_data = json.load(f)

        self.priority_files = [
            "README.md",
            "docs/",
            "CHANGELOG",
            "INSTALL",
            "CONTRIBUTING",
        ]

    def categorize_broken_links(self) -> Dict:
        """Catégorise les liens brisés par type de problème"""
        categories = {
            "moved_files": [],
            "deleted_files": [],
            "typos": [],
            "external_links": [],
            "priority_docs": [],
            "low_priority": [],
        }

        for broken_link in self.analysis_data["broken_links"]:
            link = broken_link["link"]
            source_file = broken_link["source_file"]

            # Prioriser les fichiers critiques
            if any(priority in source_file for priority in self.priority_files):
                categories["priority_docs"].append(broken_link)

            # Détecter les fichiers potentiellement déplacés
            elif self.detect_moved_file(link):
                categories["moved_files"].append(broken_link)

            # Détecter les typos probables
            elif self.detect_typo(link):
                categories["typos"].append(broken_link)

            else:
                categories["low_priority"].append(broken_link)

        return categories

    def detect_moved_file(self, link: str) -> bool:
        """Détecte si un fichier a probablement été déplacé"""
        # Rechercher des fichiers similaires dans le projet
        filename = Path(link).name
        if filename and "." in filename:
            try:
                # Nettoyer le nom de fichier pour éviter les erreurs de pattern
                re.escape(filename)
                # Rechercher le fichier dans tout le projet
                for file_path in Path(".").rglob("*"):
                    if file_path.is_file() and file_path.name == filename:
                        return True
            except (ValueError, OSError):
                # En cas d'erreur, ignorer silencieusement
                pass
        return False

    def detect_typo(self, link: str) -> bool:
        """Détecte les typos probables dans les liens"""
        # Rechercher des fichiers avec noms similaires
        filename = Path(link).name
        if filename:
            try:
                # Simple heuristique pour détecter les typos
                for file_path in Path(".").rglob("*"):
                    if file_path.is_file() and self.similar_names(
                        filename, file_path.name
                    ):
                        return True
            except (ValueError, OSError):
                # En cas d'erreur, ignorer silencieusement
                pass
        return False

    def similar_names(self, name1: str, name2: str) -> bool:
        """Compare la similarité de deux noms de fichiers"""
        # Calcul simple de distance d'édition
        if abs(len(name1) - len(name2)) > 3:
            return False

        # Vérifier les caractères communs
        common_chars = set(name1.lower()) & set(name2.lower())
        return len(common_chars) > len(name1) * 0.7

    def find_replacement_files(self, broken_links: List[Dict]) -> Dict:
        """Trouve les fichiers de remplacement pour les liens brisés"""
        replacements = {}

        for broken_link in broken_links:
            link = broken_link["link"]
            filename = Path(link).name

            if filename:
                try:
                    # Rechercher des fichiers similaires
                    candidates = []
                    for file_path in Path(".").rglob("*"):
                        if (
                            file_path.is_file()
                            and filename.lower() in file_path.name.lower()
                        ):
                            candidates.append(str(file_path))

                    if candidates:
                        # Prendre le candidat le plus probable
                        best_candidate = min(candidates, key=lambda x: len(x))
                        replacements[link] = best_candidate
                except (ValueError, OSError):
                    # En cas d'erreur, ignorer silencieusement
                    continue

        return replacements

    def generate_correction_plan(self) -> Dict:
        """Génère un plan de correction prioritaire"""
        categories = self.categorize_broken_links()
        replacements = self.find_replacement_files(categories["moved_files"])

        plan = {
            "summary": {
                "total_broken": len(self.analysis_data["broken_links"]),
                "priority_docs": len(categories["priority_docs"]),
                "moved_files": len(categories["moved_files"]),
                "auto_correctable": len(replacements),
                "manual_review_needed": len(categories["priority_docs"])
                + len(categories["typos"]),
            },
            "automatic_corrections": replacements,
            "priority_corrections": categories["priority_docs"][:20],  # Top 20
            "categories": categories,
        }

        return plan


def main():
    """Exécute l'analyse des résultats et génère le plan de correction"""
    analyzer = DocumentationUpdatePrioritizer("logs/documentation_analysis_data.json")
    correction_plan = analyzer.generate_correction_plan()

    # Sauvegarder le plan de correction
    with open("logs/documentation_correction_plan.json", "w", encoding="utf-8") as f:
        json.dump(correction_plan, f, indent=2, ensure_ascii=False)

    print("📊 Plan de correction généré:")
    print(f"   🔗 Total liens brisés: {correction_plan['summary']['total_broken']}")
    print(f"   🏆 Documents prioritaires: {correction_plan['summary']['priority_docs']}")
    print(
        f"   🤖 Corrections automatiques: {correction_plan['summary']['auto_correctable']}"
    )
    print(
        f"   👁️ Révision manuelle requise: {correction_plan['summary']['manual_review_needed']}"
    )

    return correction_plan


if __name__ == "__main__":
    main()
