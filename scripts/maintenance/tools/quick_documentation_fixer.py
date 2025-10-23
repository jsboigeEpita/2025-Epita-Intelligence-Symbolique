#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Correcteur de Documentation Rapide et Ciblé
Version optimisée pour éviter les répertoires volumineux
Oracle Enhanced v2.1.0
"""

import os
import re
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class FixResult:
    """Résultat d'une correction appliquée."""

    file_path: str
    original_text: str
    corrected_text: str
    line_number: int
    applied: bool


class QuickDocumentationFixer:
    """Correcteur rapide de documentation avec exclusions intelligentes."""

    def __init__(self):
        self.root_path = Path(".")
        self.setup_logging()

        # Répertoires à exclure pour éviter la lenteur
        self.excluded_dirs = {
            "node_modules",
            ".git",
            ".vscode",
            "__pycache__",
            "venv",
            "env",
            ".env",
            "logs",
            "temp",
            "tmp",
            "build",
            "dist",
            "cache",
            ".cache",
            "coverage",
        }

        # Répertoires prioritaires à analyser
        self.priority_dirs = ["docs", "README.md", "*.md"]  # Fichiers MD à la racine

        # Corrections automatiques communes
        self.auto_corrections = {
            "docs/sherlock_watson/ARCHITECTURE_TECHNIQUE_DETAILLEE.md": "docs/sherlock_watson/ARCHITECTURE_ORACLE_ENHANCED.md",
            "docs/sherlock_watson/GUIDE_UTILISATEUR.md": "docs/sherlock_watson/GUIDE_UTILISATEUR_COMPLET.md",
            "README_ENVIRONNEMENT.md": "docs/README_ENVIRONNEMENT.md",
            "STRUCTURE.md": "docs/STRUCTURE.md",
            "CONTRIBUTING.md": "docs/CONTRIBUTING.md",
            "start_web_application.ps1": "scripts/start_web_application.ps1",
            "run_webapp_integration.py": "scripts/run_webapp_integration.py",
            "strategies_architecture.md": "docs/architecture/strategies/strategies_architecture.md",
            "semantic_kernel_integration.md": "docs/architecture/strategies/semantic_kernel_integration.md",
        }

        # Patterns de liens cassés optimisés
        self.link_patterns = [
            r"\[.*?\]\(([^)]+)\)",  # [text](link)
            r'href=["\']([^"\']+)["\']',  # href="link"
            r'src=["\']([^"\']+)["\']',  # src="link"
        ]

    def setup_logging(self):
        """Configure le logging."""
        os.makedirs("logs", exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("logs/quick_fixer.log", encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def find_markdown_files_safe(self) -> List[Path]:
        """Trouve les fichiers Markdown en évitant les répertoires lents."""
        markdown_files = []

        # Fichiers MD à la racine
        for file in self.root_path.glob("*.md"):
            markdown_files.append(file)

        # Parcourir seulement le répertoire docs
        docs_path = self.root_path / "docs"
        if docs_path.exists():
            for file in docs_path.rglob("*.md"):
                # Vérifier qu'on n'est pas dans un répertoire exclu
                if not any(excluded in str(file) for excluded in self.excluded_dirs):
                    markdown_files.append(file)

        self.logger.info(
            f"📁 {len(markdown_files)} fichiers Markdown trouvés (recherche sécurisée)"
        )
        return sorted(markdown_files)

    def detect_and_fix_file(self, file_path: Path) -> List[FixResult]:
        """Détecte et corrige les problèmes dans un fichier."""
        results = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            modified_lines = []
            file_modified = False

            for line_num, line in enumerate(lines):
                modified_line = line

                # Rechercher et corriger les liens cassés
                for pattern in self.link_patterns:
                    matches = list(re.finditer(pattern, line, re.IGNORECASE))
                    for match in reversed(
                        matches
                    ):  # Reverse pour maintenir les positions
                        referenced_file = match.group(1)

                        # Nettoyer la référence
                        referenced_file = referenced_file.strip("`\"'()[]")

                        # Skip URLs et patterns normaux
                        if any(
                            skip in referenced_file.lower()
                            for skip in ["http", "https", "mailto:", "{", "}", "$"]
                        ):
                            continue

                        # Vérifier si on a une correction automatique
                        if referenced_file in self.auto_corrections:
                            correct_path = self.auto_corrections[referenced_file]
                            modified_line = modified_line.replace(
                                referenced_file, correct_path
                            )
                            file_modified = True

                            results.append(
                                FixResult(
                                    file_path=str(
                                        file_path.relative_to(self.root_path)
                                    ),
                                    original_text=referenced_file,
                                    corrected_text=correct_path,
                                    line_number=line_num + 1,
                                    applied=True,
                                )
                            )

                modified_lines.append(modified_line)

            # Écrire le fichier modifié si nécessaire
            if file_modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(modified_lines)
                self.logger.info(f"✅ Fichier corrigé: {file_path}")

        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'analyse de {file_path}: {e}")

        return results

    def run_quick_fix(self) -> Dict:
        """Exécute la correction rapide."""
        self.logger.info("🚀 Démarrage des corrections rapides")

        # Trouver les fichiers Markdown (recherche sécurisée)
        markdown_files = self.find_markdown_files_safe()

        # Analyser et corriger tous les fichiers
        all_results = []
        for file_path in markdown_files:
            self.logger.info(f"🔍 Analyse: {file_path}")
            results = self.detect_and_fix_file(file_path)
            all_results.extend(results)

        applied_fixes = [r for r in all_results if r.applied]

        self.logger.info(
            f"✅ {len(applied_fixes)} corrections appliquées sur {len(markdown_files)} fichiers"
        )

        # Générer le rapport
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"logs/quick_documentation_fixes_{timestamp}.md"

        report_content = """# Rapport de Corrections Rapides - {timestamp}

## Résumé
- **Fichiers analysés**: {len(markdown_files)}
- **Corrections appliquées**: {len(applied_fixes)}
- **Taux de réussite**: {(len(applied_fixes)/len(markdown_files)*100):.1f}%

## Corrections Appliquées

"""

        for result in applied_fixes:
            report_content += """### {result.file_path} (ligne {result.line_number})
- **Original**: `{result.original_text}`
- **Corrigé**: `{result.corrected_text}`

"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return {
            "success": True,
            "files_analyzed": len(markdown_files),
            "fixes_applied": len(applied_fixes),
            "report_path": report_path,
        }


def main():
    """Point d'entrée principal."""
    try:
        fixer = QuickDocumentationFixer()
        results = fixer.run_quick_fix()

        print("🎯 CORRECTIONS RAPIDES TERMINÉES")
        print(f"📊 {results['fixes_applied']} corrections appliquées")
        print(f"📁 {results['files_analyzed']} fichiers analysés")
        print(f"📄 Rapport: {results['report_path']}")

        return 0

    except Exception as e:
        print(f"❌ Erreur: {e}")
        logging.exception("Erreur dans les corrections rapides")
        return 1


if __name__ == "__main__":
    exit(main())
