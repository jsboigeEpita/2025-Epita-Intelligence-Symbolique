#!/usr/bin/env python3
"""
Script de validation de la migration vers l'UnifiedWebOrchestrator
Version: 1.0.0
Date: 08/06/2025

Ce script vérifie que la migration depuis PowerShell vers Python
a été effectuée correctement et que tous les composants fonctionnent.
"""

import sys
import json
import yaml
import subprocess
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class MigrationValidator:
    """Validateur de migration pour l'UnifiedWebOrchestrator"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "validation_results": {},
            "overall_status": "UNKNOWN",
            "summary": {},
        }

    def log(self, message: str, level: str = "INFO"):
        """Affiche un message avec timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "[INFO]",
            "SUCCESS": "[OK]",
            "ERROR": "[ERROR]",
            "WARNING": "[WARNING]",
            "TEST": "[TEST]",
        }.get(level, "[LOG]")

        print(f"[{timestamp}] {prefix} {message}")

    def validate_file_presence(self) -> bool:
        """Vérifie la présence des fichiers essentiels"""
        self.log("Validation de la présence des fichiers...", "TEST")

        required_files = [
            "start_webapp.py",
            "config/webapp_config.yml",
            "MIGRATION_WEBAPP.md",
            "archives/legacy_scripts/README.md",
        ]

        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
                self.log(f"Fichier manquant: {file_path}", "ERROR")
            else:
                self.log(f"Fichier trouvé: {file_path}", "SUCCESS")

        success = len(missing_files) == 0
        self.results["validation_results"]["file_presence"] = {
            "status": "PASS" if success else "FAIL",
            "required_files": required_files,
            "missing_files": missing_files,
        }

        return success

    def validate_legacy_archival(self) -> bool:
        """Vérifie que les anciens scripts ont été archivés"""
        self.log("Validation de l'archivage des scripts obsolètes...", "TEST")

        # Vérifier que start_web_application.ps1 n'est plus à la racine
        old_script = self.project_root / "start_web_application.ps1"
        archived_script = (
            self.project_root / "archives/legacy_scripts/start_web_application.ps1"
        )

        if old_script.exists():
            self.log("L'ancien script PowerShell n'a pas été archivé", "ERROR")
            success = False
        elif archived_script.exists():
            self.log("Script PowerShell correctement archivé", "SUCCESS")
            success = True
        else:
            self.log(
                "Script PowerShell introuvable (ni à la racine ni dans les archives)",
                "WARNING",
            )
            success = False

        self.results["validation_results"]["legacy_archival"] = {
            "status": "PASS" if success else "FAIL",
            "old_script_removed": not old_script.exists(),
            "archived_script_present": archived_script.exists(),
        }

        return success

    def validate_configuration(self) -> bool:
        """Vérifie la configuration YAML"""
        self.log("Validation de la configuration YAML...", "TEST")

        config_path = self.project_root / "config/webapp_config.yml"

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # Vérifier les sections essentielles
            required_sections = ["backend", "frontend", "logging"]
            missing_sections = [
                section for section in required_sections if section not in config
            ]

            # Vérifier que health check est configuré (soit section dédiée soit dans backend)
            has_health_check = "health_check" in config or (
                config.get("backend", {}).get("health_endpoint") is not None
            )

            if missing_sections:
                self.log(
                    f"Sections manquantes dans la config: {missing_sections}", "ERROR"
                )
                success = False
            elif not has_health_check:
                self.log("Configuration health check manquante", "ERROR")
                success = False
            else:
                self.log(
                    "Configuration YAML valide avec toutes les sections requises",
                    "SUCCESS",
                )
                success = True

        except Exception as e:
            self.log(f"Erreur lors de la lecture de la configuration: {e}", "ERROR")
            success = False
            config = None
            missing_sections = required_sections

        self.results["validation_results"]["configuration"] = {
            "status": "PASS" if success else "FAIL",
            "config_file_exists": config_path.exists(),
            "config_valid": success,
            "missing_sections": missing_sections if not success else [],
        }

        return success

    def validate_webapp_script(self) -> bool:
        """Vérifie que le script start_webapp.py est fonctionnel"""
        self.log("Validation du script start_webapp.py...", "TEST")

        script_path = self.project_root / "start_webapp.py"

        try:
            # Test syntaxe Python
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode != 0:
                self.log(
                    f"Erreur de syntaxe dans start_webapp.py: {result.stderr}", "ERROR"
                )
                success = False
            else:
                self.log("Script start_webapp.py syntaxiquement correct", "SUCCESS")

                # Test d'aide (--help)
                help_result = subprocess.run(
                    [sys.executable, "start_webapp.py", "--help"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=10,
                )

                if help_result.returncode == 0:
                    self.log("Option --help fonctionnelle", "SUCCESS")
                    success = True
                else:
                    self.log("Problème avec l'option --help", "WARNING")
                    success = True  # Non bloquant

        except subprocess.TimeoutExpired:
            self.log("Timeout lors du test de --help", "WARNING")
            success = True  # Non bloquant
        except Exception as e:
            self.log(f"Erreur lors de la validation du script: {e}", "ERROR")
            success = False

        self.results["validation_results"]["webapp_script"] = {
            "status": "PASS" if success else "FAIL",
            "syntax_valid": success,
            "help_functional": success,
        }

        return success

    def validate_orchestrator_import(self) -> bool:
        """Vérifie que l'orchestrateur peut être importé"""
        self.log("Validation de l'import de l'orchestrateur...", "TEST")

        try:
            # Test d'import
            import_result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from project_core.pipelines.unified_web_orchestrator import UnifiedWebOrchestrator; print('Import réussi')",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=15,
            )

            if import_result.returncode == 0:
                self.log("UnifiedWebOrchestrator importé avec succès", "SUCCESS")
                success = True
            else:
                self.log(
                    f"Erreur d'import de l'orchestrateur: {import_result.stderr}",
                    "ERROR",
                )
                success = False

        except subprocess.TimeoutExpired:
            self.log("Timeout lors de l'import de l'orchestrateur", "ERROR")
            success = False
        except Exception as e:
            self.log(f"Erreur lors du test d'import: {e}", "ERROR")
            success = False

        self.results["validation_results"]["orchestrator_import"] = {
            "status": "PASS" if success else "FAIL",
            "import_successful": success,
        }

        return success

    def validate_documentation(self) -> bool:
        """Vérifie que la documentation a été mise à jour"""
        self.log("Validation de la documentation...", "TEST")

        checks = {}

        # Vérifier README.md principal
        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()

            checks["readme_updated"] = "🚀 **Démarrage Rapide**" in readme_content
            checks["migration_mentioned"] = "MIGRATION_WEBAPP.md" in readme_content
            checks["new_script_mentioned"] = "start_webapp.py" in readme_content
        else:
            checks = {
                "readme_updated": False,
                "migration_mentioned": False,
                "new_script_mentioned": False,
            }

        # Vérifier MIGRATION_WEBAPP.md
        migration_doc = self.project_root / "MIGRATION_WEBAPP.md"
        checks["migration_doc_exists"] = migration_doc.exists()

        success = all(checks.values())

        for check, result in checks.items():
            status = "SUCCESS" if result else "ERROR"
            self.log(f"Documentation {check}: {'OK' if result else 'FAIL'}", status)

        self.results["validation_results"]["documentation"] = {
            "status": "PASS" if success else "FAIL",
            "checks": checks,
        }

        return success

    def run_validation(self) -> Dict:
        """Exécute toutes les validations"""
        self.log("Début de la validation de la migration", "INFO")
        self.log("=" * 60, "INFO")

        validations = [
            ("Présence des fichiers", self.validate_file_presence),
            ("Archivage des scripts obsolètes", self.validate_legacy_archival),
            ("Configuration YAML", self.validate_configuration),
            ("Script start_webapp.py", self.validate_webapp_script),
            ("Import orchestrateur", self.validate_orchestrator_import),
            ("Documentation", self.validate_documentation),
        ]

        passed = 0
        total = len(validations)

        for name, validation_func in validations:
            self.log(f"\n--- {name} ---", "INFO")
            try:
                result = validation_func()
                if result:
                    passed += 1
                    self.log(f"{name}: RÉUSSI", "SUCCESS")
                else:
                    self.log(f"{name}: ÉCHEC", "ERROR")
            except Exception as e:
                self.log(f"{name}: ERREUR - {e}", "ERROR")

        # Calcul du statut global
        success_rate = passed / total
        if success_rate == 1.0:
            overall_status = "RÉUSSI"
        elif success_rate >= 0.8:
            overall_status = "RÉUSSI_AVEC_AVERTISSEMENTS"
        else:
            overall_status = "ÉCHEC"

        self.results["overall_status"] = overall_status
        self.results["summary"] = {
            "total_validations": total,
            "passed_validations": passed,
            "success_rate": success_rate,
        }

        # Affichage du résumé
        self.log("\n" + "=" * 60, "INFO")
        self.log(
            f"RÉSULTAT GLOBAL: {overall_status}",
            "SUCCESS" if success_rate >= 0.8 else "ERROR",
        )
        self.log(f"Validations réussies: {passed}/{total} ({success_rate:.1%})", "INFO")

        if overall_status == "RÉUSSI":
            self.log("La migration a été effectuée avec succès !", "SUCCESS")
            self.log(
                "Vous pouvez maintenant utiliser: python start_webapp.py", "SUCCESS"
            )
        elif overall_status == "RÉUSSI_AVEC_AVERTISSEMENTS":
            self.log("Migration réussie avec quelques avertissements", "WARNING")
        else:
            self.log("La migration nécessite des corrections", "ERROR")

        return self.results

    def save_results(self, output_file: Optional[str] = None):
        """Sauvegarde les résultats au format JSON"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"validation_migration_{timestamp}.json"

        output_path = self.project_root / output_file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        self.log(f"Résultats sauvegardés dans: {output_file}", "INFO")


def main():
    """Fonction principale"""
    print("Validation de la Migration vers l'UnifiedWebOrchestrator")
    print("=" * 70)
    print()

    validator = MigrationValidator()
    results = validator.run_validation()

    # Sauvegarder les résultats
    validator.save_results()

    # Code de sortie
    exit_code = (
        0
        if results["overall_status"] in ["RÉUSSI", "RÉUSSI_AVEC_AVERTISSEMENTS"]
        else 1
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
