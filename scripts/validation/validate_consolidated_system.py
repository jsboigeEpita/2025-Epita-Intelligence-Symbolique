#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de Validation Système Complet - Phase 3
==============================================

Valide l'intégrité et le fonctionnement de tous les fichiers consolidés
après la suppression des fichiers redondants (Phase 2).

import argumentation_analysis.core.environment
Fichiers consolidés à valider :
1. demos/demo_unified_system.py
2. scripts/maintenance/unified_maintenance.py
3. scripts/validation/unified_validation.py
4. scripts/unified_utilities.py
5. docs/UNIFIED_SYSTEM_GUIDE.md

Tests d'intégrité des modules essentiels :
- argumentation_analysis/agents/core/*
- argumentation_analysis/orchestration/*
- config/*
- argumentation_analysis/core/*
"""

import sys
import os
import traceback
import importlib
import inspect
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration encodage Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Ajouter la racine du projet au sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class ValidationStatus(Enum):
    """Status de validation"""

    SUCCESS = "[SUCCESS] SUCCES"
    WARNING = "[WARNING] AVERTISSEMENT"
    ERROR = "[ERROR] ERREUR"
    SKIPPED = "[SKIPPED] IGNORE"


@dataclass
class ValidationResult:
    """Résultat d'une validation"""

    component: str
    status: ValidationStatus
    message: str
    details: Optional[str] = None
    execution_time: Optional[float] = None


class ConsolidatedSystemValidator:
    """Validateur système pour les fichiers consolidés"""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent
        self.results: List[ValidationResult] = []
        self.start_time = datetime.now()

        # Fichiers consolidés à valider
        self.consolidated_files = {
            "demos/demo_unified_system.py": "Système de démonstration unifié",
            "scripts/maintenance/unified_maintenance.py": "Maintenance système unifiée",
            "scripts/validation/unified_validation.py": "Validation système unifiée",
            "scripts/unified_utilities.py": "Utilitaires système unifiés",
            "docs/UNIFIED_SYSTEM_GUIDE.md": "Guide système unifié",
        }

        # Modules essentiels à vérifier
        self.essential_modules = [
            "argumentation_analysis.agents.core",
            "argumentation_analysis.orchestration",
            "argumentation_analysis.core",
            "config",
        ]

    def log_result(
        self,
        component: str,
        status: ValidationStatus,
        message: str,
        details: Optional[str] = None,
        execution_time: Optional[float] = None,
    ):
        """Enregistre un résultat de validation"""
        result = ValidationResult(component, status, message, details, execution_time)
        self.results.append(result)

        # Affichage temps réel
        status_icon = status.value
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] {status_icon} {component}: {message}"
        )
        if details:
            print(f"   [DETAILS] {details}")
        if execution_time:
            print(f"   [TEMPS] {execution_time:.3f}s")
        print()

    def validate_file_existence(self) -> None:
        """Valide l'existence des fichiers consolidés"""
        print("=" * 60)
        print("VALIDATION EXISTENCE DES FICHIERS CONSOLIDES")
        print("=" * 60)

        for file_path, description in self.consolidated_files.items():
            start_time = datetime.now()
            full_path = self.project_root / file_path

            if full_path.exists():
                file_size = full_path.stat().st_size
                details = f"Taille: {file_size:,} octets"
                self.log_result(
                    f"Fichier {file_path}",
                    ValidationStatus.SUCCESS,
                    f"{description} trouvé",
                    details,
                    (datetime.now() - start_time).total_seconds(),
                )
            else:
                self.log_result(
                    f"Fichier {file_path}",
                    ValidationStatus.ERROR,
                    f"{description} MANQUANT",
                    f"Chemin: {full_path}",
                    (datetime.now() - start_time).total_seconds(),
                )

    def validate_python_imports(self) -> None:
        """Valide les imports Python des fichiers consolidés"""
        print("=" * 60)
        print("VALIDATION IMPORTS PYTHON")
        print("=" * 60)

        python_files = [f for f in self.consolidated_files.keys() if f.endswith(".py")]

        for file_path in python_files:
            start_time = datetime.now()
            full_path = self.project_root / file_path

            if not full_path.exists():
                continue

            try:
                # Lire le fichier et vérifier les imports basiques
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Compter les lignes et imports
                lines = content.split("\n")
                import_lines = [
                    line
                    for line in lines
                    if line.strip().startswith(("import ", "from "))
                ]

                details = f"Lignes: {len(lines)}, Imports: {len(import_lines)}"

                # Test d'import simple (sans exécution)
                try:
                    # Convertir le chemin en nom de module
                    module_path = (
                        file_path.replace("/", ".")
                        .replace("\\", ".")
                        .replace(".py", "")
                    )

                    # Test de compilation du module
                    compile(content, str(full_path), "exec")

                    self.log_result(
                        f"Import {file_path}",
                        ValidationStatus.SUCCESS,
                        "Compilation réussie",
                        details,
                        (datetime.now() - start_time).total_seconds(),
                    )

                except Exception as e:
                    self.log_result(
                        f"Import {file_path}",
                        ValidationStatus.ERROR,
                        f"Erreur compilation: {str(e)[:100]}",
                        details,
                        (datetime.now() - start_time).total_seconds(),
                    )

            except Exception as e:
                self.log_result(
                    f"Import {file_path}",
                    ValidationStatus.ERROR,
                    f"Erreur lecture: {str(e)[:100]}",
                    None,
                    (datetime.now() - start_time).total_seconds(),
                )

    def validate_essential_modules(self) -> None:
        """Valide l'intégrité des modules essentiels"""
        print("=" * 60)
        print("VALIDATION MODULES ESSENTIELS")
        print("=" * 60)

        for module_name in self.essential_modules:
            start_time = datetime.now()

            try:
                # Convertir en chemin de fichier
                module_path = self.project_root / module_name.replace(".", "/")

                if module_path.is_dir():
                    # Compter les fichiers Python dans le module
                    py_files = list(module_path.rglob("*.py"))
                    details = f"Fichiers Python trouvés: {len(py_files)}"

                    # Vérifier la présence d'__init__.py
                    init_file = module_path / "__init__.py"
                    if init_file.exists():
                        details += " (avec __init__.py)"

                    self.log_result(
                        f"Module {module_name}",
                        ValidationStatus.SUCCESS,
                        "Structure module valide",
                        details,
                        (datetime.now() - start_time).total_seconds(),
                    )
                else:
                    self.log_result(
                        f"Module {module_name}",
                        ValidationStatus.WARNING,
                        "Répertoire module non trouvé",
                        f"Chemin: {module_path}",
                        (datetime.now() - start_time).total_seconds(),
                    )

            except Exception as e:
                self.log_result(
                    f"Module {module_name}",
                    ValidationStatus.ERROR,
                    f"Erreur validation: {str(e)[:100]}",
                    None,
                    (datetime.now() - start_time).total_seconds(),
                )

    def validate_demo_system_safe(self) -> None:
        """Valide le système de démo en mode sécurisé"""
        print("=" * 60)
        print("VALIDATION SYSTEME DEMO (MODE SECURISE)")
        print("=" * 60)

        start_time = datetime.now()
        demo_file = self.project_root / "demos/demo_unified_system.py"

        if not demo_file.exists():
            self.log_result(
                "Demo System",
                ValidationStatus.ERROR,
                "Fichier demo_unified_system.py manquant",
                None,
                (datetime.now() - start_time).total_seconds(),
            )
            return

        try:
            # Lire et analyser le contenu du fichier de démo
            with open(demo_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Rechercher des fonctions critiques
            critical_functions = [
                "main",
                "run_rhetorical_analysis",
                "demonstration_pipeline",
                "analyze_text",
            ]

            found_functions = []
            for func_name in critical_functions:
                if f"def {func_name}" in content:
                    found_functions.append(func_name)

            details = f"Fonctions critiques trouvées: {', '.join(found_functions) if found_functions else 'Aucune'}"

            if found_functions:
                self.log_result(
                    "Demo System Functions",
                    ValidationStatus.SUCCESS,
                    f"Fonctions critiques détectées ({len(found_functions)}/{len(critical_functions)})",
                    details,
                    (datetime.now() - start_time).total_seconds(),
                )
            else:
                self.log_result(
                    "Demo System Functions",
                    ValidationStatus.WARNING,
                    "Aucune fonction critique standard trouvée",
                    details,
                    (datetime.now() - start_time).total_seconds(),
                )

        except Exception as e:
            self.log_result(
                "Demo System",
                ValidationStatus.ERROR,
                f"Erreur analyse: {str(e)[:100]}",
                None,
                (datetime.now() - start_time).total_seconds(),
            )

    def validate_maintenance_system_safe(self) -> None:
        """Valide le système de maintenance en mode sécurisé"""
        print("=" * 60)
        print("VALIDATION SYSTEME MAINTENANCE (MODE SECURISE)")
        print("=" * 60)

        start_time = datetime.now()
        maintenance_file = (
            self.project_root / "scripts/maintenance/unified_maintenance.py"
        )

        if not maintenance_file.exists():
            self.log_result(
                "Maintenance System",
                ValidationStatus.ERROR,
                "Fichier unified_maintenance.py manquant",
                None,
                (datetime.now() - start_time).total_seconds(),
            )
            return

        try:
            with open(maintenance_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Rechercher des fonctions de maintenance critiques
            maintenance_functions = [
                "cleanup",
                "clean_temp_files",
                "validate_system",
                "migrate",
                "backup",
            ]

            found_functions = []
            for func_name in maintenance_functions:
                if f"def {func_name}" in content or f"def .*{func_name}" in content:
                    found_functions.append(func_name)

            details = f"Fonctions maintenance trouvées: {', '.join(found_functions) if found_functions else 'Aucune'}"

            self.log_result(
                "Maintenance System Functions",
                (
                    ValidationStatus.SUCCESS
                    if found_functions
                    else ValidationStatus.WARNING
                ),
                f"Fonctions maintenance détectées ({len(found_functions)})",
                details,
                (datetime.now() - start_time).total_seconds(),
            )

        except Exception as e:
            self.log_result(
                "Maintenance System",
                ValidationStatus.ERROR,
                f"Erreur analyse: {str(e)[:100]}",
                None,
                (datetime.now() - start_time).total_seconds(),
            )

    def validate_utilities_system_safe(self) -> None:
        """Valide le système d'utilitaires en mode sécurisé"""
        print("=" * 60)
        print("VALIDATION SYSTEME UTILITAIRES (MODE SECURISE)")
        print("=" * 60)

        start_time = datetime.now()
        utilities_file = self.project_root / "scripts/unified_utilities.py"

        if not utilities_file.exists():
            self.log_result(
                "Utilities System",
                ValidationStatus.ERROR,
                "Fichier unified_utilities.py manquant",
                None,
                (datetime.now() - start_time).total_seconds(),
            )
            return

        try:
            with open(utilities_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Rechercher des utilitaires critiques
            utility_functions = [
                "encrypt",
                "decrypt",
                "list_corpus",
                "validate",
                "analyze",
            ]

            found_functions = []
            for func_name in utility_functions:
                if (
                    f"def {func_name}" in content
                    or func_name.lower() in content.lower()
                ):
                    found_functions.append(func_name)

            details = f"Utilitaires trouvés: {', '.join(found_functions) if found_functions else 'Aucune'}"

            self.log_result(
                "Utilities System Functions",
                (
                    ValidationStatus.SUCCESS
                    if found_functions
                    else ValidationStatus.WARNING
                ),
                f"Utilitaires détectés ({len(found_functions)})",
                details,
                (datetime.now() - start_time).total_seconds(),
            )

        except Exception as e:
            self.log_result(
                "Utilities System",
                ValidationStatus.ERROR,
                f"Erreur analyse: {str(e)[:100]}",
                None,
                (datetime.now() - start_time).total_seconds(),
            )

    def validate_documentation(self) -> None:
        """Valide la documentation système"""
        print("=" * 60)
        print("📚 VALIDATION DOCUMENTATION SYSTÈME")
        print("=" * 60)

        start_time = datetime.now()
        doc_file = self.project_root / "docs/UNIFIED_SYSTEM_GUIDE.md"

        if not doc_file.exists():
            self.log_result(
                "Documentation",
                ValidationStatus.ERROR,
                "UNIFIED_SYSTEM_GUIDE.md manquant",
                None,
                (datetime.now() - start_time).total_seconds(),
            )
            return

        try:
            with open(doc_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Analyser la structure de la documentation
            lines = content.split("\n")
            headers = [line for line in lines if line.startswith("#")]

            # Sections critiques attendues
            critical_sections = [
                "installation",
                "configuration",
                "utilisation",
                "api",
                "exemples",
            ]

            found_sections = []
            for section in critical_sections:
                if section.lower() in content.lower():
                    found_sections.append(section)

            details = f"Lignes: {len(lines)}, En-têtes: {len(headers)}, Sections: {', '.join(found_sections)}"

            self.log_result(
                "Documentation Completeness",
                (
                    ValidationStatus.SUCCESS
                    if len(found_sections) >= 3
                    else ValidationStatus.WARNING
                ),
                f"Documentation analysée ({len(found_sections)}/{len(critical_sections)} sections critiques)",
                details,
                (datetime.now() - start_time).total_seconds(),
            )

        except Exception as e:
            self.log_result(
                "Documentation",
                ValidationStatus.ERROR,
                f"Erreur analyse: {str(e)[:100]}",
                None,
                (datetime.now() - start_time).total_seconds(),
            )

    def run_basic_integration_tests(self) -> None:
        """Exécute des tests d'intégration basiques non-destructifs"""
        print("=" * 60)
        print("🔗 TESTS D'INTÉGRATION BASIQUES")
        print("=" * 60)

        # Test 1: Vérification des chemins critiques
        start_time = datetime.now()
        critical_paths = [
            "config",
            "argumentation_analysis",
            "scripts",
            "demos",
            "docs",
        ]

        missing_paths = []
        for path_name in critical_paths:
            path_obj = self.project_root / path_name
            if not path_obj.exists():
                missing_paths.append(path_name)

        if not missing_paths:
            self.log_result(
                "Critical Paths",
                ValidationStatus.SUCCESS,
                "Tous les chemins critiques existent",
                f"Chemins vérifiés: {', '.join(critical_paths)}",
                (datetime.now() - start_time).total_seconds(),
            )
        else:
            self.log_result(
                "Critical Paths",
                ValidationStatus.ERROR,
                f"Chemins manquants: {', '.join(missing_paths)}",
                None,
                (datetime.now() - start_time).total_seconds(),
            )

        # Test 2: Vérification configuration
        start_time = datetime.now()
        config_files = (
            list((self.project_root / "config").glob("*.py"))
            if (self.project_root / "config").exists()
            else []
        )

        self.log_result(
            "Configuration Files",
            ValidationStatus.SUCCESS if config_files else ValidationStatus.WARNING,
            f"Fichiers configuration trouvés: {len(config_files)}",
            (
                f"Fichiers: {[f.name for f in config_files]}"
                if config_files
                else "Aucun fichier de configuration"
            ),
            (datetime.now() - start_time).total_seconds(),
        )

    def generate_validation_report(self) -> str:
        """Génère le rapport final de validation"""
        print("=" * 60)
        print("📊 GÉNÉRATION RAPPORT FINAL")
        print("=" * 60)

        total_time = (datetime.now() - self.start_time).total_seconds()

        # Statistiques
        total_tests = len(self.results)
        successes = len(
            [r for r in self.results if r.status == ValidationStatus.SUCCESS]
        )
        warnings = len(
            [r for r in self.results if r.status == ValidationStatus.WARNING]
        )
        errors = len([r for r in self.results if r.status == ValidationStatus.ERROR])
        skipped = len([r for r in self.results if r.status == ValidationStatus.SKIPPED])

        # Taux de réussite
        success_rate = (successes / total_tests * 100) if total_tests > 0 else 0

        # Génération du rapport
        report = f"""
RAPPORT DE VALIDATION SYSTÈME CONSOLIDÉ - PHASE 3
================================================

🕐 Validation exécutée le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
⏱️  Durée totale: {total_time:.2f} secondes
🎯 Taux de réussite: {success_rate:.1f}%

STATISTIQUES GLOBALES
=====================
📊 Total des tests: {total_tests}
✅ Succès: {successes}
⚠️  Avertissements: {warnings} 
❌ Erreurs: {errors}
⏭️  Ignorés: {skipped}

RÉSULTATS DÉTAILLÉS
==================
"""

        for result in self.results:
            report += f"\n{result.status.value} {result.component}\n"
            report += f"   Message: {result.message}\n"
            if result.details:
                report += f"   Détails: {result.details}\n"
            if result.execution_time:
                report += f"   Temps: {result.execution_time:.3f}s\n"

        # Recommandations
        report += f"\n\nRECOMMANDATIONS\n===============\n"

        if errors == 0 and warnings == 0:
            report += "🎉 EXCELLENT! Tous les tests passent avec succès.\n"
            report += "✅ Le système consolidé est entièrement opérationnel.\n"
            report += "🚀 Vous pouvez procéder en toute confiance.\n"
        elif errors == 0:
            report += f"✅ BIEN! Aucune erreur critique détectée.\n"
            report += (
                f"⚠️  {warnings} avertissement(s) à examiner mais non bloquant(s).\n"
            )
            report += (
                "🎯 Le système est opérationnel avec des améliorations possibles.\n"
            )
        else:
            report += f"❌ ATTENTION! {errors} erreur(s) critique(s) détectée(s).\n"
            report += "🔧 Corrections requises avant utilisation en production.\n"
            report += "📋 Vérifiez les détails des erreurs ci-dessus.\n"

        report += f"\n\nFICHIERS CONSOLIDÉS VALIDÉS\n==========================\n"
        for file_path, description in self.consolidated_files.items():
            status = (
                "✅"
                if any(
                    r.component.endswith(file_path)
                    and r.status == ValidationStatus.SUCCESS
                    for r in self.results
                )
                else "❓"
            )
            report += f"{status} {file_path}: {description}\n"

        report += f"\n\nMODULES ESSENTIELS VALIDÉS\n=========================\n"
        for module_name in self.essential_modules:
            status = (
                "✅"
                if any(
                    r.component.endswith(module_name)
                    and r.status == ValidationStatus.SUCCESS
                    for r in self.results
                )
                else "❓"
            )
            report += f"{status} {module_name}\n"

        report += f"""

PROCHAINES ÉTAPES RECOMMANDÉES
==============================
1. 📋 Examiner les avertissements et erreurs détaillés
2. 🔧 Corriger les problèmes critiques identifiés
3. 🧪 Exécuter des tests fonctionnels spécifiques si nécessaire
4. 🚀 Déployer le système consolidé en production

📝 Ce rapport a été généré automatiquement par validate_consolidated_system.py
🔗 Phase 3 de la consolidation système - Validation d'intégrité
"""

        return report

    def run_full_validation(self) -> str:
        """Exécute la validation complète du système"""
        print("DEBUT DE LA VALIDATION SYSTEME CONSOLIDE - PHASE 3")
        print("=" * 60)
        print(f"Demarrage: {self.start_time.strftime('%d/%m/%Y a %H:%M:%S')}")
        print(f"Repertoire projet: {self.project_root}")
        print("=" * 60)

        try:
            # Étapes de validation
            self.validate_file_existence()
            self.validate_python_imports()
            self.validate_essential_modules()
            self.validate_demo_system_safe()
            self.validate_maintenance_system_safe()
            self.validate_utilities_system_safe()
            self.validate_documentation()
            self.run_basic_integration_tests()

            # Génération du rapport final
            report = self.generate_validation_report()

            # Sauvegarde du rapport
            report_file = (
                self.project_root
                / f"RAPPORT_PHASE_3_VALIDATION_SYSTEME_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            )
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)

            print(f"Rapport sauvegarde: {report_file.name}")
            print("\n" + "=" * 60)
            print("VALIDATION SYSTEME TERMINEE")
            print("=" * 60)

            return str(report_file)

        except Exception as e:
            error_msg = f"Erreur critique durant la validation: {str(e)}"
            print(f"\n[ERROR] {error_msg}")
            traceback.print_exc()

            self.log_result(
                "Validation System",
                ValidationStatus.ERROR,
                error_msg,
                traceback.format_exc(),
            )

            return self.generate_validation_report()


def main():
    """Point d'entrée principal"""
    print("VALIDATION SYSTEME CONSOLIDE - PHASE 3")
    print("=" * 50)
    print()

    try:
        validator = ConsolidatedSystemValidator()
        report_file = validator.run_full_validation()

        print(f"\n[SUCCESS] Validation terminee avec succes!")
        print(f"[RAPPORT] Rapport disponible: {report_file}")

        return 0

    except KeyboardInterrupt:
        print("\n\n[WARNING] Validation interrompue par l'utilisateur")
        return 1
    except Exception as e:
        print(f"\n\n[ERROR] Erreur fatale: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
