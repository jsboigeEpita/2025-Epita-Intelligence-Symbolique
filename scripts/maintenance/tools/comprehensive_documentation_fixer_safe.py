#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de Correction Automatique de Documentation - Version Sécurisée
Évite la génération de gros fichiers JSON pour GitHub
Oracle Enhanced v2.1.0
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class DocumentationIssue:
    """Représente un problème de documentation détecté."""

    file_path: str
    line_number: int
    issue_type: str
    description: str
    original_text: str
    suggested_fix: str
    confidence: float
    severity: str = "medium"


@dataclass
class FixResult:
    """Résultat d'une correction appliquée."""

    file_path: str
    issue_type: str
    original_text: str
    corrected_text: str
    line_number: int
    confidence: float
    applied: bool
    reason: str


class ComprehensiveDocumentationFixer:
    """Correcteur automatique de documentation avec génération de rapports légers."""

    def __init__(self):
        self.root_path = Path(".")
        self.setup_logging()

        # Patterns de liens cassés - optimisés
        self.broken_link_patterns = [
            # Markdown links
            r"\[([^\]]+)\]\(([^)]+)\)",
            # Références de fichiers dans le texte
            r'(?:consultez?|voir|référence|fichier|script)\s*:?\s*[`"]?([^`"\s,;]+\.(?:md|py|js|yml|json|txt|html|css|ps1|sh))[`"]?',
            # Chemins relatifs
            r"(?:\.{1,2}/)?([a-zA-Z0-9_\-/\.]+\.(?:md|py|js|yml|json|txt|html|css|ps1|sh))",
        ]

        # Corrections automatiques communes
        self.auto_corrections = {
            # Corrections de chemins
            "docs/sherlock_watson/ARCHITECTURE_TECHNIQUE_DETAILLEE.md": "docs/sherlock_watson/ARCHITECTURE_ORACLE_ENHANCED.md",
            "docs/sherlock_watson/GUIDE_UTILISATEUR.md": "docs/sherlock_watson/GUIDE_UTILISATEUR_COMPLET.md",
            "README_ENVIRONNEMENT.md": "docs/README_ENVIRONNEMENT.md",
            "STRUCTURE.md": "docs/STRUCTURE.md",
            "CONTRIBUTING.md": "docs/CONTRIBUTING.md",
            # Scripts
            "start_web_application.ps1": "scripts/start_web_application.ps1",
            "run_webapp_integration.py": "scripts/run_webapp_integration.py",
            # Documentation spécialisée
            "strategies_architecture.md": "docs/architecture/strategies/strategies_architecture.md",
            "semantic_kernel_integration.md": "docs/architecture/strategies/semantic_kernel_integration.md",
        }

    def setup_logging(self):
        """Configure le logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(
                    "logs/comprehensive_fixer_safe.log", encoding="utf-8"
                ),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def find_markdown_files(self) -> List[Path]:
        """Trouve tous les fichiers Markdown."""
        markdown_files = []
        for ext in ["*.md", "*.rst"]:
            markdown_files.extend(self.root_path.rglob(ext))
        return sorted(markdown_files)

    def detect_issues_in_file(self, file_path: Path) -> List[DocumentationIssue]:
        """Détecte les problèmes dans un fichier."""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                for pattern in self.broken_link_patterns:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        referenced_file = (
                            match.group(1)
                            if len(match.groups()) >= 1
                            else match.group(0)
                        )

                        # Nettoyer la référence
                        referenced_file = referenced_file.strip("`\"'()[]")

                        # Skip URLs et patterns normaux
                        if any(
                            skip in referenced_file.lower()
                            for skip in ["http", "https", "mailto:", "{", "}", "$"]
                        ):
                            continue

                        # Vérifier si le fichier existe
                        if not self.file_exists(referenced_file):
                            suggested_fix = self.get_suggested_fix(referenced_file)
                            confidence = (
                                0.8
                                if suggested_fix and self.file_exists(suggested_fix)
                                else 0.3
                            )

                            issues.append(
                                DocumentationIssue(
                                    file_path=str(
                                        file_path.relative_to(self.root_path)
                                    ),
                                    line_number=line_num,
                                    issue_type="BROKEN_LINK",
                                    description=f"Lien cassé vers: {referenced_file}",
                                    original_text=line.strip(),
                                    suggested_fix=suggested_fix
                                    or f"Vérifier le chemin: {referenced_file}",
                                    confidence=confidence,
                                    severity="high" if confidence > 0.7 else "medium",
                                )
                            )

        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de {file_path}: {e}")

        return issues

    def file_exists(self, file_path: str) -> bool:
        """Vérifie si un fichier existe."""
        try:
            # Essayer plusieurs variantes du chemin
            variants = [
                file_path,
                file_path.lstrip("./"),
                f"./{file_path}",
                f"docs/{file_path}",
                f"scripts/{file_path}",
            ]

            for variant in variants:
                if (self.root_path / variant).exists():
                    return True
            return False
        except:
            return False

    def get_suggested_fix(self, broken_path: str) -> Optional[str]:
        """Obtient une correction suggérée pour un chemin cassé."""
        # Vérifier dans auto_corrections
        if broken_path in self.auto_corrections:
            return self.auto_corrections[broken_path]

        # Rechercher un fichier similaire
        filename = os.path.basename(broken_path)
        for file_path in self.root_path.rglob(filename):
            relative_path = file_path.relative_to(self.root_path)
            return str(relative_path)

        return None

    def apply_fixes(self, issues: List[DocumentationIssue]) -> List[FixResult]:
        """Applique les corrections."""
        results = []
        files_to_fix = {}

        # Grouper par fichier
        for issue in issues:
            if issue.confidence >= 0.7:  # Seulement les corrections haute confiance
                if issue.file_path not in files_to_fix:
                    files_to_fix[issue.file_path] = []
                files_to_fix[issue.file_path].append(issue)

        # Appliquer les corrections fichier par fichier
        for file_path, file_issues in files_to_fix.items():
            results.extend(self.fix_file(file_path, file_issues))

        return results

    def fix_file(
        self, file_path: str, issues: List[DocumentationIssue]
    ) -> List[FixResult]:
        """Corrige un fichier spécifique."""
        results = []
        file_obj = self.root_path / file_path

        if not file_obj.exists():
            return results

        try:
            # Lire le fichier
            with open(file_obj, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            modified = False

            # Appliquer les corrections
            for issue in issues:
                if issue.suggested_fix and self.file_exists(issue.suggested_fix):
                    # Extraire la partie à remplacer de original_text
                    for pattern in self.broken_link_patterns:
                        matches = re.finditer(
                            pattern, issue.original_text, re.IGNORECASE
                        )
                        for match in matches:
                            old_ref = (
                                match.group(1)
                                if len(match.groups()) >= 1
                                else match.group(0)
                            )
                            old_ref = old_ref.strip("`\"'()[]")

                            if old_ref in issue.description:
                                # Remplacer dans le contenu
                                new_content = content.replace(
                                    old_ref, issue.suggested_fix
                                )
                                if new_content != content:
                                    content = new_content
                                    modified = True

                                    results.append(
                                        FixResult(
                                            file_path=file_path,
                                            issue_type=issue.issue_type,
                                            original_text=old_ref,
                                            corrected_text=issue.suggested_fix,
                                            line_number=issue.line_number,
                                            confidence=issue.confidence,
                                            applied=True,
                                            reason=f"Correction automatique: {old_ref} → {issue.suggested_fix}",
                                        )
                                    )
                                    break

            # Sauvegarder si modifié
            if modified:
                with open(file_obj, "w", encoding="utf-8") as f:
                    f.write(content)
                self.logger.info(f"Fichier corrigé: {file_path}")

        except Exception as e:
            self.logger.error(f"Erreur lors de la correction de {file_path}: {e}")

        return results

    def generate_lightweight_report(
        self, all_issues: List[DocumentationIssue], results: List[FixResult]
    ) -> str:
        """Génère un rapport léger sans JSON volumineux."""
        datetime.now().strftime("%Y%m%d_%H%M%S")

        # Statistiques
        total_issues = len(all_issues)
        fixed_issues = len([r for r in results if r.applied])
        files_analyzed = len(set(issue.file_path for issue in all_issues))
        files_fixed = len(set(r.file_path for r in results if r.applied))

        report = f"""# 📋 Rapport de Corrections Automatiques
## Oracle Enhanced v2.1.0 - Version Sécurisée

**Date d'analyse :** {datetime.now().isoformat()}

## 📊 Résumé Exécutif
- **Fichiers analysés :** {files_analyzed}
- **Problèmes détectés :** {total_issues}
- **Corrections appliquées :** {fixed_issues}
- **Fichiers corrigés :** {files_fixed}
- **Taux de succès :** {(fixed_issues/total_issues)*100:.1f}%

## 🔧 Corrections Appliquées (Échantillon)

"""

        # Afficher les premières corrections
        for i, result in enumerate(results[:50] if results else []):
            if result.applied:
                report += f"""### {result.file_path} (ligne {result.line_number})
- **Avant :** `{result.original_text}`
- **Après :** `{result.corrected_text}`
- **Confiance :** {result.confidence:.2f}

"""

        if len(results) > 50:
            report += f"... et {len(results)-50} autres corrections\n\n"

        report += f"""## 💡 Recommandations

1. **Validation manuelle** : Vérifier les corrections appliquées
2. **Tests** : Exécuter les tests pour valider les liens
3. **Documentation** : Mettre à jour les guides de contribution
4. **Surveillance** : Intégrer ces contrôles dans CI/CD

## ✅ Étapes suivantes

- Réviser les corrections dans Git
- Tester les liens corrigés
- Committer les changements validés
"""

        return report

    def run_comprehensive_fix(self) -> Dict:
        """Exécute la correction complète avec génération de rapport léger."""
        self.logger.info("🚀 Démarrage des corrections automatiques")

        # Trouver les fichiers Markdown
        markdown_files = self.find_markdown_files()
        self.logger.info(f"📁 {len(markdown_files)} fichiers Markdown trouvés")

        # Analyser tous les fichiers
        all_issues = []
        for file_path in markdown_files:
            issues = self.detect_issues_in_file(file_path)
            all_issues.extend(issues)

        self.logger.info(f"🔍 {len(all_issues)} problèmes détectés")

        # Appliquer les corrections
        results = self.apply_fixes(all_issues)
        applied_fixes = [r for r in results if r.applied]

        self.logger.info(f"✅ {len(applied_fixes)} corrections appliquées")

        # Générer le rapport
        report_content = self.generate_lightweight_report(all_issues, results)

        # Sauvegarder le rapport
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("logs", exist_ok=True)

        report_path = f"logs/comprehensive_documentation_fixes_{timestamp}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        # Sauvegarder des données JSON légères (seulement statistiques)
        json_path = f"logs/comprehensive_fixes_summary_{timestamp}.json"
        summary_data = {
            "timestamp": timestamp,
            "files_analyzed": len(set(issue.file_path for issue in all_issues)),
            "total_issues": len(all_issues),
            "fixes_applied": len(applied_fixes),
            "success_rate": (len(applied_fixes) / len(all_issues)) * 100
            if all_issues
            else 0,
            "files_modified": list(set(r.file_path for r in applied_fixes)),
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"📄 Rapport généré: {report_path}")

        return {
            "success": True,
            "issues_found": len(all_issues),
            "fixes_applied": len(applied_fixes),
            "report_path": report_path,
            "json_path": json_path,
        }


def main():
    """Point d'entrée principal."""
    try:
        fixer = ComprehensiveDocumentationFixer()
        results = fixer.run_comprehensive_fix()

        print(f"🎯 CORRECTIONS TERMINÉES")
        print(
            f"📊 {results['fixes_applied']} corrections appliquées sur {results['issues_found']} problèmes"
        )
        print(f"📄 Rapport: {results['report_path']}")

        return 0

    except Exception as e:
        print(f"❌ Erreur: {e}")
        logging.exception("Erreur dans les corrections automatiques")
        return 1


if __name__ == "__main__":
    exit(main())
