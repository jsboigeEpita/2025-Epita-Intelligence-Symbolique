#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 VALIDATION FINALE SYSTÈME ORACLE ENHANCED V2.1.0 - VERSION CORRIGÉE

Script de validation complète pour la tâche 5/6 avec tests corrigés.
Effectue tous les tests critiques réels et génère un rapport complet.

Auteur: Système Oracle Enhanced
Version: 2.1.0
Date: 2025-06-07
"""

import sys
import json
import time
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Any
from project_core.utils.shell import run_in_activated_env, ShellCommandError


class OracleEnhancedValidatorCorrected:
    """Validateur complet corrigé du système Oracle Enhanced v2.1.0"""

    def __init__(self):
        self.project_root = Path("d:/2025-Epita-Intelligence-Symbolique")
        self.results = {
            "validation_date": datetime.now().isoformat(),
            "oracle_enhanced_version": "2.1.0",
            "tests_performed": {},
            "critical_tests": {},
            "import_tests": {},
            "integration_tests": {},
            "system_integrity": {},
            "git_analysis": {},
            "performance_tests": {},
            "overall_score": 0.0,
            "status": "UNKNOWN",
            "errors": [],
            "warnings": [],
            "recommendations": [],
        }

    def log_result(
        self, test_name: str, success: bool, details: str = "", error: str = ""
    ):
        """Enregistre un résultat de test"""
        self.results["tests_performed"][test_name] = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "error": error if error else None,
        }

        if not success and error:
            self.results["errors"].append(f"{test_name}: {error}")
        elif not success:
            self.results["warnings"].append(f"{test_name}: {details}")

        print(f"{'✅' if success else '❌'} {test_name}: {details}")
        if error:
            print(f"   💥 Erreur: {error}")

    def run_command_with_env(
        self, command: str, test_name: str, timeout: int = 120
    ) -> Tuple[bool, str, str]:
        """Exécute une commande avec l'environnement projet activé via le service unifié."""
        try:
            command_parts = command.split()

            result = run_in_activated_env(
                command=command_parts,
                env_name="projet-is",
                cwd=self.project_root,
                check_errors=False,
                timeout=timeout,
            )

            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            return success, stdout, stderr

        except ShellCommandError as e:
            return False, "", str(e)
        except Exception as e:
            return False, "", f"Erreur inattendue dans run_command_with_env: {str(e)}"

    def test_oracle_imports_corrected(self) -> bool:
        """Test 1: Validation des imports Oracle Enhanced v2.1.0 - Version corrigée"""
        print("\n🔍 === TEST 1: IMPORTS ORACLE ENHANCED (CORRIGÉ) ===")

        # Test import principal Oracle
        success, stdout, stderr = self.run_command_with_env(
            "python -c \"import argumentation_analysis.agents.core.oracle; print('Oracle Enhanced v2.1.0 OK')\"",
            "oracle_main_import",
        )

        if success and "Oracle Enhanced v2.1.0 OK" in stdout:
            self.log_result(
                "oracle_main_import", True, "Import principal Oracle réussi"
            )
            self.results["import_tests"]["oracle_main"] = True
        else:
            self.log_result(
                "oracle_main_import", False, "Import principal Oracle échoué", stderr
            )
            self.results["import_tests"]["oracle_main"] = False

        # Test CluedoOracleState
        success, stdout, stderr = self.run_command_with_env(
            "python -c \"from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState; print('CluedoOracleState OK')\"",
            "cluedo_oracle_state",
        )

        if success and "CluedoOracleState OK" in stdout:
            self.log_result("cluedo_oracle_state", True, "CluedoOracleState accessible")
            self.results["import_tests"]["cluedo_state"] = True
        else:
            self.log_result(
                "cluedo_oracle_state", False, "CluedoOracleState non accessible", stderr
            )
            self.results["import_tests"]["cluedo_state"] = False

        # Test agents individuels
        agents_tests = [
            (
                "from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent; print('Sherlock OK')",
                "sherlock_agent",
                "Sherlock OK",
            ),
            (
                "from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant; print('Watson OK')",
                "watson_agent",
                "Watson OK",
            ),
            (
                "from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent; print('Moriarty OK')",
                "moriarty_agent",
                "Moriarty OK",
            ),
        ]

        for command, test_key, expected in agents_tests:
            success, stdout, stderr = self.run_command_with_env(
                f'python -c "{command}"', test_key
            )
            if success and expected in stdout:
                self.log_result(test_key, True, f"Agent {test_key} accessible")
                self.results["import_tests"][test_key] = True
            else:
                self.log_result(
                    test_key, False, f"Agent {test_key} non accessible", stderr
                )
                self.results["import_tests"][test_key] = False

        import_score = sum(self.results["import_tests"].values()) / len(
            self.results["import_tests"]
        )
        self.results["critical_tests"]["imports"] = import_score

        return import_score >= 0.8  # Au moins 80% des imports doivent réussir

    def test_simple_functionality(self) -> bool:
        """Test 2: Fonctionnalités de base simplifiées"""
        print("\n🛠️ === TEST 2: FONCTIONNALITÉS DE BASE ===")

        # Test creation simple d'états
        success, stdout, stderr = self.run_command_with_env(
            "python -c \"from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState; state = CluedoOracleState('test', [], 'balanced'); print(f'État créé: {state.nom_enquete}')\"",
            "state_creation",
        )

        if success and "État créé: test" in stdout:
            self.log_result("state_creation", True, "Création d'état Oracle réussie")
            self.results["integration_tests"]["state_creation"] = True
        else:
            self.log_result(
                "state_creation", False, "Création d'état Oracle échouée", stderr
            )
            self.results["integration_tests"]["state_creation"] = False

        # Test dataset minimal
        success, stdout, stderr = self.run_command_with_env(
            "python -c \"from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset; ds = CluedoDataset(['test']); print(f'Dataset créé avec {len(ds.moriarty_cards)} cartes')\"",
            "dataset_creation",
        )

        if success and "Dataset créé avec" in stdout:
            self.log_result(
                "dataset_creation", True, "Création de dataset Oracle réussie"
            )
            self.results["integration_tests"]["dataset_creation"] = True
        else:
            self.log_result(
                "dataset_creation", False, "Création de dataset Oracle échouée", stderr
            )
            self.results["integration_tests"]["dataset_creation"] = False

        functionality_score = sum(self.results["integration_tests"].values()) / max(
            len(self.results["integration_tests"]), 1
        )
        self.results["critical_tests"]["functionality"] = functionality_score

        return functionality_score >= 0.5

    def test_system_integrity_corrected(self) -> bool:
        """Test 3: Intégrité du système - Version corrigée"""
        print("\n🔧 === TEST 3: INTÉGRITÉ SYSTÈME (CORRIGÉE) ===")

        # Vérification structure projet
        critical_paths = [
            "argumentation_analysis/agents/core/oracle",
            "argumentation_analysis/core",
            "tests/integration",
            "scripts/env",
            "scripts/maintenance",
        ]

        missing_paths = []
        for path in critical_paths:
            full_path = self.project_root / path
            if not full_path.exists():
                missing_paths.append(path)

        if not missing_paths:
            self.log_result("project_structure", True, "Structure du projet intacte")
            self.results["system_integrity"]["structure"] = True
        else:
            self.log_result(
                "project_structure", False, f"Chemins manquants: {missing_paths}"
            )
            self.results["system_integrity"]["structure"] = False

        # Test fichiers refactored accessibility
        refactored_files = [
            "tests/unit/argumentation_analysis/agents/core/oracle/test_oracle_behavior_demo.py_refactored",
            "tests/unit/argumentation_analysis/agents/core/oracle/test_oracle_behavior_simple.py_refactored",
            "tests/unit/argumentation_analysis/agents/core/oracle/update_test_coverage.py_refactored",
        ]

        accessible_refactored = 0
        for file_path in refactored_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                accessible_refactored += 1

        if accessible_refactored == len(refactored_files):
            self.log_result(
                "refactored_files", True, "Tous les fichiers refactorisés accessibles"
            )
            self.results["system_integrity"]["refactored_files"] = True
        else:
            self.log_result(
                "refactored_files",
                False,
                f"Seulement {accessible_refactored}/{len(refactored_files)} fichiers accessibles",
            )
            self.results["system_integrity"]["refactored_files"] = False

        # Test fichiers de validation
        validation_scripts = [
            "test_phase_d_integration.py",
            "test_group1_simple.py",
            "test_group2_corrections_simple.py",
        ]

        accessible_validation = 0
        for script in validation_scripts:
            full_path = self.project_root / script
            if full_path.exists():
                accessible_validation += 1

        if accessible_validation >= 2:
            self.log_result(
                "validation_scripts",
                True,
                f"{accessible_validation}/{len(validation_scripts)} scripts de validation accessibles",
            )
            self.results["system_integrity"]["validation_scripts"] = True
        else:
            self.log_result(
                "validation_scripts",
                False,
                f"Seulement {accessible_validation}/{len(validation_scripts)} scripts accessibles",
            )
            self.results["system_integrity"]["validation_scripts"] = False

        integrity_score = sum(self.results["system_integrity"].values()) / len(
            self.results["system_integrity"]
        )
        self.results["critical_tests"]["integrity"] = integrity_score

        return integrity_score >= 0.7

    def test_working_scripts(self) -> bool:
        """Test 4: Scripts fonctionnels"""
        print("\n🧪 === TEST 4: SCRIPTS FONCTIONNELS ===")

        # Test Phase D intégration
        phase_d_script = self.project_root / "test_phase_d_integration.py"
        if phase_d_script.exists():
            success, stdout, stderr = self.run_command_with_env(
                "python test_phase_d_integration.py", "phase_d_integration", timeout=60
            )

            if success:
                self.log_result(
                    "phase_d_integration", True, "Test Phase D intégration réussi"
                )
                self.results["performance_tests"]["phase_d_script"] = True
            else:
                self.log_result(
                    "phase_d_integration",
                    False,
                    "Test Phase D intégration échoué",
                    stderr,
                )
                self.results["performance_tests"]["phase_d_script"] = False
        else:
            self.log_result(
                "phase_d_integration",
                False,
                "Script test_phase_d_integration.py introuvable",
            )
            self.results["performance_tests"]["phase_d_script"] = False

        # Test des scripts simples validés
        simple_scripts = [
            ("test_group1_simple.py", "group1_simple"),
            ("test_group2_corrections_simple.py", "group2_simple"),
        ]

        scripts_success = 0
        for script_name, test_key in simple_scripts:
            script_path = self.project_root / script_name
            if script_path.exists():
                success, stdout, stderr = self.run_command_with_env(
                    f"python {script_name}", test_key, timeout=30
                )
                if success:
                    scripts_success += 1
                    self.log_result(
                        test_key, True, f"Script {script_name} exécuté avec succès"
                    )
                else:
                    self.log_result(
                        test_key, False, f"Script {script_name} échoué", stderr[:200]
                    )
            else:
                self.log_result(test_key, False, f"Script {script_name} introuvable")

        self.results["performance_tests"]["simple_scripts_score"] = (
            scripts_success / len(simple_scripts) if simple_scripts else 0
        )

        scripts_score = (
            self.results["performance_tests"].get("phase_d_script", 0) * 0.6
            + self.results["performance_tests"].get("simple_scripts_score", 0) * 0.4
        )
        self.results["critical_tests"]["scripts"] = scripts_score

        return scripts_score >= 0.5

    def analyze_git_status(self) -> bool:
        """Test 5: Analyse état Git"""
        print("\n📋 === TEST 5: ANALYSE GIT ===")

        try:
            # Git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            if result.returncode == 0:
                git_status = result.stdout.strip()
                lines = git_status.split("\n") if git_status else []

                modified_files = [line for line in lines if line.startswith("M ")]
                added_files = [line for line in lines if line.startswith("A ")]
                deleted_files = [line for line in lines if line.startswith("D ")]
                untracked_files = [line for line in lines if line.startswith("??")]

                self.results["git_analysis"] = {
                    "modified_files": len(modified_files),
                    "added_files": len(added_files),
                    "deleted_files": len(deleted_files),
                    "untracked_files": len(untracked_files),
                    "total_changes": len(lines),
                    "status_detail": git_status,
                }

                self.log_result(
                    "git_status",
                    True,
                    f"Git analysé: {len(lines)} changements détectés",
                )
                return True
            else:
                self.log_result(
                    "git_status", False, "Erreur analyse Git", result.stderr
                )
                return False

        except Exception as e:
            self.log_result("git_status", False, "Exception analyse Git", str(e))
            return False

    def calculate_overall_score(self) -> float:
        """Calcule le score global de validation"""
        critical_weights = {
            "imports": 0.35,  # 35% - Imports critiques (le plus important)
            "functionality": 0.20,  # 20% - Fonctionnalités de base
            "integrity": 0.25,  # 25% - Intégrité système
            "scripts": 0.20,  # 20% - Scripts fonctionnels
        }

        weighted_score = 0.0
        for test_name, weight in critical_weights.items():
            score = self.results["critical_tests"].get(test_name, 0.0)
            weighted_score += score * weight

        return weighted_score

    def generate_recommendations(self):
        """Génère les recommandations basées sur les résultats"""
        recommendations = []

        # Recommandations basées sur les tests critiques
        if self.results["critical_tests"].get("imports", 0) < 0.8:
            recommendations.append(
                "🔧 CRITIQUE: Corriger les problèmes d'imports Oracle Enhanced"
            )
        elif self.results["critical_tests"].get("imports", 0) >= 0.8:
            recommendations.append("✅ EXCELLENT: Imports Oracle Enhanced fonctionnels")

        if self.results["critical_tests"].get("functionality", 0) < 0.5:
            recommendations.append(
                "🛠️ IMPORTANTE: Déboguer les fonctionnalités de base"
            )
        elif self.results["critical_tests"].get("functionality", 0) >= 0.5:
            recommendations.append("✅ BON: Fonctionnalités de base opérationnelles")

        if self.results["critical_tests"].get("integrity", 0) < 0.7:
            recommendations.append(
                "🔧 PRIORITÉ: Restaurer l'intégrité de la structure du projet"
            )
        elif self.results["critical_tests"].get("integrity", 0) >= 0.7:
            recommendations.append("✅ BON: Intégrité du système préservée")

        if self.results["critical_tests"].get("scripts", 0) < 0.5:
            recommendations.append("🧪 ATTENTION: Vérifier les scripts de validation")
        elif self.results["critical_tests"].get("scripts", 0) >= 0.5:
            recommendations.append("✅ BON: Scripts de validation fonctionnels")

        # Recommandations Git
        git_changes = self.results.get("git_analysis", {}).get("total_changes", 0)
        if git_changes > 50:
            recommendations.append(
                f"📋 INFO: {git_changes} changements Git détectés - Préparer commit structuré"
            )
        elif git_changes > 0:
            recommendations.append(
                f"📋 NORMAL: {git_changes} changements Git à committer"
            )

        self.results["recommendations"] = recommendations

    def run_validation(self) -> Dict[str, Any]:
        """Lance la validation complète corrigée"""
        print("🚀 === DÉBUT VALIDATION ORACLE ENHANCED V2.1.0 - CORRIGÉE ===")
        print(f"📅 Date: {self.results['validation_date']}")
        print(f"📂 Projet: {self.project_root}")

        start_time = time.time()

        # Tests critiques corrigés
        tests_results = []
        tests_results.append(self.test_oracle_imports_corrected())
        tests_results.append(self.test_simple_functionality())
        tests_results.append(self.test_system_integrity_corrected())
        tests_results.append(self.test_working_scripts())
        tests_results.append(self.analyze_git_status())

        # Calcul score global
        self.results["overall_score"] = self.calculate_overall_score()

        # Détermination du statut
        if self.results["overall_score"] >= 0.85:
            self.results["status"] = "✅ EXCELLENT"
        elif self.results["overall_score"] >= 0.70:
            self.results["status"] = "✅ VALIDÉ"
        elif self.results["overall_score"] >= 0.50:
            self.results["status"] = "⚠️ PARTIEL"
        else:
            self.results["status"] = "❌ CRITIQUE"

        # Génération recommandations
        self.generate_recommendations()

        execution_time = time.time() - start_time
        self.results["execution_time"] = execution_time

        print(f"\n🏁 === VALIDATION TERMINÉE ===")
        print(f"⏱️ Temps d'exécution: {execution_time:.2f}s")
        print(f"📊 Score global: {self.results['overall_score']:.1%}")
        print(f"🎯 Statut: {self.results['status']}")

        return self.results


def main():
    """Point d'entrée principal"""
    try:
        validator = OracleEnhancedValidatorCorrected()
        results = validator.run_validation()

        # Sauvegarde des résultats
        output_file = Path("logs/final_validation_results_corrected.json")
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Résultats sauvegardés: {output_file}")

        # Code de sortie basé sur le statut
        if results["overall_score"] >= 0.70:
            sys.exit(0)  # Succès
        else:
            sys.exit(1)  # Échec

    except Exception as e:
        print(f"💥 ERREUR CRITIQUE: {str(e)}")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
