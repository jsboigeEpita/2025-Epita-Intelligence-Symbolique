#!/usr/bin/env python3
"""
Script d'organisation des fichiers orphelins Oracle/Sherlock/Watson/Moriarty
Identifie, analyse et organise tous les fichiers contenant des références orphelines
"""

import os
import re
import shutil
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from datetime import datetime

# Configuration
PROJECT_ROOT = Path("d:/2025-Epita-Intelligence-Symbolique")
KEYWORDS = ["oracle", "sherlock", "watson", "moriarty", "enquête", "enquete", "cluedo"]
IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    "venv",
    "logs",
    "results",
}


class OrphanFileAnalyzer:
    """Analyse et organise les fichiers orphelins avec références Oracle/Sherlock/Watson/Moriarty"""

    def __init__(self):
        self.root_path = PROJECT_ROOT
        self.orphan_files = {}
        self.code_recovery = {}
        self.organization_plan = {}
        self.analysis_report = {
            "timestamp": datetime.now().isoformat(),
            "total_files_scanned": 0,
            "orphan_files_found": 0,
            "code_recovery_candidates": 0,
            "organization_actions": [],
        }

    def scan_for_orphan_files(self) -> Dict[str, Any]:
        """Scanne tous les fichiers pour identifier les orphelins avec références Oracle"""
        print(
            "[SCAN] Analyse des fichiers orphelins Oracle/Sherlock/Watson/Moriarty..."
        )

        # Scan récursif de tous les fichiers
        for root, dirs, files in os.walk(self.root_path):
            # Ignorer les répertoires système
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.root_path)

                self.analysis_report["total_files_scanned"] += 1

                # Analyser le contenu du fichier
                analysis = self._analyze_file_content(file_path)
                if analysis["has_oracle_references"]:
                    self.orphan_files[str(relative_path)] = analysis

                    # Analyser si c'est un vrai orphelin (pas dans une structure organisée)
                    if self._is_orphan_file(relative_path):
                        self.analysis_report["orphan_files_found"] += 1

                        # Analyser si contient du code récupérable
                        if self._has_recoverable_code(analysis):
                            self.analysis_report["code_recovery_candidates"] += 1

        return self.analysis_report

    def _analyze_file_content(self, file_path: Path) -> Dict[str, Any]:
        """Analyse le contenu d'un fichier pour détecter les références Oracle"""
        analysis = {
            "file_path": str(file_path),
            "file_size": 0,
            "file_type": file_path.suffix,
            "has_oracle_references": False,
            "keyword_matches": [],
            "reference_count": 0,
            "code_quality": "unknown",
            "integration_status": "unknown",
            "content_preview": "",
        }

        try:
            if file_path.stat().st_size > 10_000_000:  # Ignorer les fichiers >10MB
                return analysis

            analysis["file_size"] = file_path.stat().st_size

            # Lire le contenu pour analyse
            content = ""
            if file_path.suffix in [
                ".py",
                ".md",
                ".txt",
                ".yml",
                ".yaml",
                ".json",
                ".js",
                ".ts",
            ]:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except:
                    try:
                        content = file_path.read_text(
                            encoding="latin-1", errors="ignore"
                        )
                    except:
                        return analysis

            if not content:
                return analysis

            # Rechercher les mots-clés Oracle/Sherlock/Watson/Moriarty
            content_lower = content.lower()
            keyword_pattern = r"\b(" + "|".join(KEYWORDS) + r")\b"
            matches = re.findall(keyword_pattern, content_lower, re.IGNORECASE)

            if matches:
                analysis["has_oracle_references"] = True
                analysis["keyword_matches"] = list(set(matches))
                analysis["reference_count"] = len(matches)
                analysis["content_preview"] = (
                    content[:500] + "..." if len(content) > 500 else content
                )

                # Analyser la qualité du code
                analysis["code_quality"] = self._assess_code_quality(content, file_path)

                # Analyser le statut d'intégration
                analysis["integration_status"] = self._assess_integration_status(
                    content, file_path
                )

        except Exception as e:
            analysis["error"] = str(e)

        return analysis

    def _is_orphan_file(self, relative_path: Path) -> bool:
        """Détermine si un fichier est orphelin (pas dans une structure organisée)"""
        path_parts = relative_path.parts

        # Fichiers à la racine sont potentiellement orphelins
        if len(path_parts) == 1:
            # Sauf certains fichiers de configuration
            config_files = {
                "conftest.py",
                ".env",
                ".env.example",
                ".gitignore",
                "setup.py",
                "pyproject.toml",
                "requirements.txt",
            }
            return path_parts[0] not in config_files

        # Fichiers dans des répertoires temporaires ou tests ad-hoc
        temp_patterns = ["temp", "tmp", "_test", "test_", "debug", "draft", "scratch"]
        for part in path_parts:
            if any(pattern in part.lower() for pattern in temp_patterns):
                return True

        # Fichiers dans tests/validation_sherlock_watson sont intégrés
        if "tests/validation_sherlock_watson" in str(relative_path):
            return False

        return False

    def _has_recoverable_code(self, analysis: Dict[str, Any]) -> bool:
        """Détermine si le fichier contient du code récupérable"""
        if analysis["file_type"] not in [".py", ".js", ".ts"]:
            return False

        content = analysis.get("content_preview", "")

        # Indicateurs de code de qualité
        quality_indicators = [
            "class ",
            "def ",
            "function ",
            "import ",
            "from ",
            "async def",
            "@",
            '"""',
            "# TODO",
            "# FIXME",
        ]

        return any(indicator in content for indicator in quality_indicators)

    def _assess_code_quality(self, content: str, file_path: Path) -> str:
        """Évalue la qualité du code dans le fichier"""
        if file_path.suffix != ".py":
            return "non-python"

        # Compteurs pour évaluer la qualité
        lines = content.split("\n")
        code_lines = [
            line for line in lines if line.strip() and not line.strip().startswith("#")
        ]

        if len(code_lines) < 10:
            return "minimal"
        elif len(code_lines) < 50:
            return "basic"
        elif len(code_lines) < 200:
            return "moderate"
        else:
            return "substantial"

    def _assess_integration_status(self, content: str, file_path: Path) -> str:
        """Évalue le statut d'intégration du code"""
        # Chercher des imports Oracle Enhanced
        oracle_imports = [
            "from argumentation_analysis.agents.core.oracle",
            "from argumentation_analysis.core.cluedo_oracle_state",
            "from argumentation_analysis.orchestration.cluedo_extended_orchestrator",
        ]

        if any(imp in content for imp in oracle_imports):
            return "integrated"

        # Chercher des TODO ou FIXME
        if "TODO" in content or "FIXME" in content:
            return "work_in_progress"

        # Chercher des tests
        if "test_" in file_path.name or "Test" in content:
            return "test_file"

        return "standalone"

    def analyze_phase_d_extensions(self) -> Dict[str, Any]:
        """Analyse spécifique du fichier phase_d_extensions.py"""
        print("\n[ANALYSE] Analyse spécifique de phase_d_extensions.py...")

        phase_d_path = self.root_path / "phase_d_extensions.py"
        if not phase_d_path.exists():
            return {"status": "not_found"}

        content = phase_d_path.read_text(encoding="utf-8")

        analysis = {
            "file_size": len(content),
            "line_count": len(content.split("\n")),
            "has_valuable_code": True,
            "classes_found": [],
            "functions_found": [],
            "integration_recommendations": [],
        }

        # Analyser les classes
        class_pattern = r"class\s+(\w+):"
        classes = re.findall(class_pattern, content)
        analysis["classes_found"] = classes

        # Analyser les fonctions
        function_pattern = r"def\s+(\w+)\("
        functions = re.findall(function_pattern, content)
        analysis["functions_found"] = functions

        # Recommandations d'intégration
        if "PhaseDExtensions" in classes:
            analysis["integration_recommendations"].append(
                {
                    "action": "move_to_oracle_module",
                    "target": "argumentation_analysis/agents/core/oracle/phase_d_extensions.py",
                    "reason": "Extensions Oracle Enhanced Phase D",
                }
            )

        if "extend_oracle_state_phase_d" in functions:
            analysis["integration_recommendations"].append(
                {
                    "action": "integrate_with_oracle_state",
                    "target": "argumentation_analysis/core/cluedo_oracle_state.py",
                    "reason": "Extensions CluedoOracleState",
                }
            )

        return analysis

    def create_organization_plan(self) -> Dict[str, Any]:
        """Crée un plan d'organisation des fichiers orphelins"""
        print("\n[PLAN] Creation du plan d'organisation...")

        plan = {
            "timestamp": datetime.now().isoformat(),
            "actions": [],
            "code_recovery": [],
            "deletions": [],
            "summary": {
                "files_to_move": 0,
                "files_to_delete": 0,
                "code_to_integrate": 0,
            },
        }

        # Analyser phase_d_extensions.py
        phase_d_analysis = self.analyze_phase_d_extensions()
        if phase_d_analysis.get("has_valuable_code"):
            plan["actions"].append(
                {
                    "type": "move_and_integrate",
                    "source": "phase_d_extensions.py",
                    "target": "argumentation_analysis/agents/core/oracle/phase_d_extensions.py",
                    "reason": "Code Oracle Enhanced Phase D précieux",
                    "integration_needed": True,
                }
            )
            plan["summary"]["code_to_integrate"] += 1

        # Analyser autres fichiers orphelins
        for file_path, analysis in self.orphan_files.items():
            if self._is_orphan_file(Path(file_path)):
                if self._has_recoverable_code(analysis):
                    # Code récupérable - déplacer vers scripts/orphaned ou intégrer
                    plan["code_recovery"].append(
                        {
                            "source": file_path,
                            "analysis": analysis,
                            "recommended_action": self._recommend_action(
                                file_path, analysis
                            ),
                        }
                    )
                    plan["summary"]["code_to_integrate"] += 1
                else:
                    # Fichier sans code précieux - supprimer après vérification
                    plan["deletions"].append(
                        {
                            "file": file_path,
                            "reason": "Pas de code récupérable",
                            "size": analysis["file_size"],
                        }
                    )
                    plan["summary"]["files_to_delete"] += 1

        self.organization_plan = plan
        return plan

    def _recommend_action(self, file_path: str, analysis: Dict[str, Any]) -> str:
        """Recommande une action pour un fichier orphelin"""
        if "test_" in file_path:
            return "move_to_tests_orphaned"
        elif analysis["code_quality"] == "substantial":
            return "review_for_integration"
        elif analysis["integration_status"] == "integrated":
            return "move_to_appropriate_module"
        else:
            return "move_to_scripts_orphaned"

    def execute_organization_plan(self, dry_run: bool = True) -> Dict[str, Any]:
        """Exécute le plan d'organisation"""
        print(f"\n{'[DRY RUN]' if dry_run else '[EXECUTION]'} Plan d'organisation...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "actions_completed": [],
            "errors": [],
        }

        # Créer les répertoires de destination si nécessaire
        orphaned_dirs = ["scripts/orphaned", "tests/orphaned", "docs/orphaned"]

        for dir_path in orphaned_dirs:
            full_path = self.root_path / dir_path
            if not dry_run:
                full_path.mkdir(parents=True, exist_ok=True)
                print(f"[CREATED] {dir_path}")

        # Traiter phase_d_extensions.py
        phase_d_source = self.root_path / "phase_d_extensions.py"
        if phase_d_source.exists():
            target = (
                self.root_path
                / "argumentation_analysis/agents/core/oracle/phase_d_extensions.py"
            )

            if dry_run:
                print(f"[DRY RUN] Move: {phase_d_source} -> {target}")
            else:
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(phase_d_source), str(target))
                    print(f"[MOVED] phase_d_extensions.py -> oracle/")
                    results["actions_completed"].append(
                        {
                            "action": "move",
                            "source": "phase_d_extensions.py",
                            "target": str(target.relative_to(self.root_path)),
                        }
                    )
                except Exception as e:
                    results["errors"].append(f"Error moving phase_d_extensions.py: {e}")

        # Traiter autres fichiers selon le plan
        for recovery in self.organization_plan.get("code_recovery", []):
            source_path = self.root_path / recovery["source"]
            action = recovery["recommended_action"]

            if action == "move_to_scripts_orphaned":
                target_path = (
                    self.root_path / "scripts/orphaned" / Path(recovery["source"]).name
                )
            elif action == "move_to_tests_orphaned":
                target_path = (
                    self.root_path / "tests/orphaned" / Path(recovery["source"]).name
                )
            else:
                continue  # Actions manuelles

            if dry_run:
                print(f"[DRY RUN] Move: {source_path} -> {target_path}")
            else:
                try:
                    if source_path.exists():
                        shutil.move(str(source_path), str(target_path))
                        results["actions_completed"].append(
                            {
                                "action": "move",
                                "source": recovery["source"],
                                "target": str(target_path.relative_to(self.root_path)),
                            }
                        )
                except Exception as e:
                    results["errors"].append(f"Error moving {recovery['source']}: {e}")

        return results

    def generate_report(self) -> str:
        """Génère un rapport complet de l'analyse"""
        report = f"""
# Rapport d'Analyse des Fichiers Orphelins Oracle/Sherlock/Watson/Moriarty
Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Résumé Exécutif
- **Fichiers scannés**: {self.analysis_report['total_files_scanned']}
- **Fichiers avec références Oracle**: {len(self.orphan_files)}
- **Fichiers orphelins détectés**: {self.analysis_report['orphan_files_found']}
- **Candidats pour récupération de code**: {self.analysis_report['code_recovery_candidates']}

## Analyse de phase_d_extensions.py
"""

        phase_d_analysis = self.analyze_phase_d_extensions()
        if phase_d_analysis.get("has_valuable_code"):
            report += f"""
### [OK] Code Precieux Detecte
- **Classes trouvées**: {', '.join(phase_d_analysis.get('classes_found', []))}
- **Fonctions trouvées**: {len(phase_d_analysis.get('functions_found', []))} fonctions
- **Lignes de code**: {phase_d_analysis.get('line_count', 0)}

### [RECOMMANDATIONS] Integration
"""
            for rec in phase_d_analysis.get("integration_recommendations", []):
                report += f"- **{rec['action']}**: {rec['target']} - {rec['reason']}\n"

        report += f"""

## Plan d'Organisation
- **Fichiers à déplacer**: {self.organization_plan.get('summary', {}).get('files_to_move', 0)}
- **Code à intégrer**: {self.organization_plan.get('summary', {}).get('code_to_integrate', 0)}
- **Fichiers à supprimer**: {self.organization_plan.get('summary', {}).get('files_to_delete', 0)}

## Actions Recommandées

### [ACTIONS] Immediates
1. **Déplacer phase_d_extensions.py** vers `argumentation_analysis/agents/core/oracle/`
2. **Intégrer les extensions Phase D** dans `CluedoOracleState`
3. **Organiser les tests orphelins** dans `tests/orphaned/`

### [NETTOYAGE] Actions de Nettoyage
"""

        for deletion in self.organization_plan.get("deletions", []):
            report += f"- Supprimer `{deletion['file']}` ({deletion['size']} bytes) - {deletion['reason']}\n"

        report += f"""

## Conclusion
Le fichier **phase_d_extensions.py** contient du code précieux pour les extensions Oracle Enhanced Phase D.
Il doit être intégré dans le système Oracle Enhanced pour les fonctionnalités avancées de révélations progressives,
fausses pistes, et métriques de trace idéale.

Les autres fichiers orphelins nécessitent une révision manuelle pour déterminer leur statut d'intégration.
"""

        return report


def main():
    """Fonction principale d'analyse et d'organisation des fichiers orphelins"""
    print(
        "[START] Demarrage de l'analyse des fichiers orphelins Oracle/Sherlock/Watson/Moriarty"
    )

    analyzer = OrphanFileAnalyzer()

    # 1. Scanner les fichiers orphelins
    scan_results = analyzer.scan_for_orphan_files()
    print(f"[OK] Scan termine: {scan_results['total_files_scanned']} fichiers analyses")

    # 2. Créer le plan d'organisation
    organization_plan = analyzer.create_organization_plan()
    print(f"[OK] Plan cree: {len(organization_plan['actions'])} actions planifiees")

    # 3. Exécuter en mode dry-run
    execution_results = analyzer.execute_organization_plan(dry_run=True)
    print(
        f"[OK] Simulation terminee: {len(execution_results['actions_completed'])} actions simulees"
    )

    # 4. Générer le rapport
    report = analyzer.generate_report()

    # 5. Sauvegarder les résultats
    results_dir = PROJECT_ROOT / "logs"
    results_dir.mkdir(exist_ok=True)

    report_file = (
        results_dir
        / f"orphan_files_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    report_file.write_text(report, encoding="utf-8")
    print(f"[SAVED] Rapport sauvegarde: {report_file}")

    # 6. Sauvegarder les données JSON
    json_file = (
        results_dir
        / f"orphan_files_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    json_data = {
        "analysis_report": analyzer.analysis_report,
        "organization_plan": analyzer.organization_plan,
        "execution_results": execution_results,
    }
    json_file.write_text(
        json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[SAVED] Donnees sauvegardees: {json_file}")

    print("\n" + "=" * 80)
    print("[RESUME] ACTIONS RECOMMANDEES")
    print("=" * 80)
    print(
        "1. [MOVE] Deplacer phase_d_extensions.py vers argumentation_analysis/agents/core/oracle/"
    )
    print("2. [INTEGRATE] Integrer les extensions Phase D dans CluedoOracleState")
    print("3. [ORGANIZE] Organiser les fichiers orphelins selon le plan genere")
    print("4. [REVIEW] Consulter le rapport detaille pour les actions manuelles")

    return analyzer


if __name__ == "__main__":
    analyzer = main()
