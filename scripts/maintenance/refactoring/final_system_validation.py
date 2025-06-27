#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[VALIDATION] VALIDATION FINALE SYSTÈME ORACLE ENHANCED V2.1.0

Script de validation complète pour la tâche 5/6.
Effectue tous les tests critiques et génère un rapport complet.

Auteur: Système Oracle Enhanced
Version: 2.1.0
Date: 2025-06-07
"""

import argumentation_analysis.core.environment
import os
import sys
import json
import time
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

class OracleEnhancedValidator:
    """Validateur complet du système Oracle Enhanced v2.1.0"""
    
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
            "overall_score": 0.0,
            "status": "UNKNOWN",
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
    def log_result(self, test_name: str, success: bool, details: str = "", error: str = ""):
        """Enregistre un résultat de test"""
        self.results["tests_performed"][test_name] = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "error": error if error else None
        }
        
        if not success and error:
            self.results["errors"].append(f"{test_name}: {error}")
        
        print(f"{'[OK]' if success else '[ERREUR]'} {test_name}: {details}")
        if error:
            print(f"   [ERREUR] Erreur: {error}")
    
    def run_command_with_env(self, command: str, test_name: str) -> Tuple[bool, str, str]:
        """Exécute une commande avec l'environnement projet activé"""
        try:
            # Commande avec activation d'environnement
            full_command = f'powershell -File .\\scripts\\env\\activate_project_env.ps1 -CommandToRun "{command}"'
            
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.project_root)
            )
            
            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            return success, stdout, stderr
            
        except subprocess.TimeoutExpired:
            return False, "", f"Timeout lors de l'exécution de {command}"
        except Exception as e:
            return False, "", f"Erreur d'exécution: {str(e)}"
    
    def test_oracle_imports(self) -> bool:
        """Test 1: Validation des imports Oracle Enhanced v2.1.0"""
        print("\n[RECHERCHE] === TEST 1: IMPORTS ORACLE ENHANCED ===")
        
        # Test import principal Oracle
        success, stdout, stderr = self.run_command_with_env(
            "python -c \"import argumentation_analysis.agents.core.oracle; print('Oracle Enhanced v2.1.0 OK')\"",
            "oracle_main_import"
        )
        
        if success and "Oracle Enhanced v2.1.0 OK" in stdout:
            self.log_result("oracle_main_import", True, "Import principal Oracle réussi")
            self.results["import_tests"]["oracle_main"] = True
        else:
            self.log_result("oracle_main_import", False, "Import principal Oracle échoué", stderr)
            self.results["import_tests"]["oracle_main"] = False
            return False
        
        # Test extensions Phase D
        success, stdout, stderr = self.run_command_with_env(
            "python -c \"from argumentation_analysis.agents.core.oracle import PhaseDExtensions; print('Phase D OK')\"",
            "phase_d_extensions"
        )
        
        if success and "Phase D OK" in stdout:
            self.log_result("phase_d_extensions", True, "Extensions Phase D disponibles")
            self.results["import_tests"]["phase_d"] = True
        else:
            self.log_result("phase_d_extensions", False, "Extensions Phase D non disponibles", stderr)
            self.results["import_tests"]["phase_d"] = False
        
        # Test CluedoOracleState
        success, stdout, stderr = self.run_command_with_env(
            "python -c \"from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState; print('CluedoOracleState OK')\"",
            "cluedo_oracle_state"
        )
        
        if success and "CluedoOracleState OK" in stdout:
            self.log_result("cluedo_oracle_state", True, "CluedoOracleState accessible")
            self.results["import_tests"]["cluedo_state"] = True
        else:
            self.log_result("cluedo_oracle_state", False, "CluedoOracleState non accessible", stderr)
            self.results["import_tests"]["cluedo_state"] = False
        
        import_score = sum(self.results["import_tests"].values()) / len(self.results["import_tests"])
        self.results["critical_tests"]["imports"] = import_score
        
        return import_score >= 0.8  # Au moins 80% des imports doivent réussir
    
    def test_sherlock_watson_functionality(self) -> bool:
        """Test 2: Fonctionnalités Sherlock-Watson-Moriarty"""
        print("\n[DETECTIVE] === TEST 2: SHERLOCK-WATSON-MORIARTY ===")
        
        # Test des agents Oracle
        success, stdout, stderr = self.run_command_with_env(
            "python -m pytest tests/integration/test_oracle_integration_recovered1.py::test_oracle_base_functionality -v",
            "oracle_integration_test"
        )
        
        if success:
            self.log_result("oracle_integration_test", True, "Tests d'intégration Oracle réussis")
            self.results["integration_tests"]["oracle_agents"] = True
        else:
            self.log_result("oracle_integration_test", False, "Tests d'intégration Oracle échoués", stderr)
            self.results["integration_tests"]["oracle_agents"] = False
        
        # Test workflow Cluedo étendu
        success, stdout, stderr = self.run_command_with_env(
            "python -m pytest tests/integration/test_cluedo_extended_workflow_recovered1.py::test_basic_workflow -v",
            "cluedo_workflow_test"
        )
        
        if success:
            self.log_result("cluedo_workflow_test", True, "Workflow Cluedo étendu fonctionnel")
            self.results["integration_tests"]["cluedo_workflow"] = True
        else:
            self.log_result("cluedo_workflow_test", False, "Workflow Cluedo étendu défaillant", stderr)
            self.results["integration_tests"]["cluedo_workflow"] = False
        
        functionality_score = sum(self.results["integration_tests"].values()) / max(len(self.results["integration_tests"]), 1)
        self.results["critical_tests"]["functionality"] = functionality_score
        
        return functionality_score >= 0.5  # Au moins 50% des tests de fonctionnalité doivent réussir
    
    def test_system_integrity(self) -> bool:
        """Test 3: Intégrité du système"""
        print("\n[OUTILS] === TEST 3: INTÉGRITÉ SYSTÈME ===")
        
        # Vérification structure projet
        critical_paths = [
            "argumentation_analysis/agents/core/oracle",
            "argumentation_analysis/core",
            "tests/integration",
            "scripts/env"
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
            self.log_result("project_structure", False, f"Chemins manquants: {missing_paths}")
            self.results["system_integrity"]["structure"] = False
        
        # Test files refactored accessibility
        refactored_files = [
            "tests/unit/argumentation_analysis/agents/core/oracle/test_oracle_behavior_demo.py_refactored",
            "tests/unit/argumentation_analysis/agents/core/oracle/test_oracle_behavior_simple.py_refactored",
            "tests/unit/argumentation_analysis/agents/core/oracle/update_test_coverage.py_refactored"
        ]
        
        accessible_refactored = 0
        for file_path in refactored_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                accessible_refactored += 1
        
        if accessible_refactored == len(refactored_files):
            self.log_result("refactored_files", True, "Tous les fichiers refactorisés accessibles")
            self.results["system_integrity"]["refactored_files"] = True
        else:
            self.log_result("refactored_files", False, f"Seulement {accessible_refactored}/{len(refactored_files)} fichiers accessibles")
            self.results["system_integrity"]["refactored_files"] = False
        
        integrity_score = sum(self.results["system_integrity"].values()) / len(self.results["system_integrity"])
        self.results["critical_tests"]["integrity"] = integrity_score
        
        return integrity_score >= 0.8
    
    def test_non_regression(self) -> bool:
        """Test 4: Non-régression des fonctionnalités"""
        print("\n[TESTS] === TEST 4: NON-RÉGRESSION ===")
        
        # Test Phase D intégration
        phase_d_script = self.project_root / "test_phase_d_integration.py"
        if phase_d_script.exists():
            success, stdout, stderr = self.run_command_with_env(
                "python test_phase_d_integration.py",
                "phase_d_integration"
            )
            
            if success:
                self.log_result("phase_d_integration", True, "Test Phase D intégration réussi")
                self.results["integration_tests"]["phase_d_script"] = True
            else:
                self.log_result("phase_d_integration", False, "Test Phase D intégration échoué", stderr)
                self.results["integration_tests"]["phase_d_script"] = False
        else:
            self.log_result("phase_d_integration", False, "Script test_phase_d_integration.py introuvable")
            self.results["integration_tests"]["phase_d_script"] = False
        
        # Test des corrections de groupe validées précédemment
        group_tests = [
            "test_group1_simple.py",
            "test_group2_corrections_simple.py",
            "test_groupe2_validation_simple.py"
        ]
        
        group_success = 0
        for test_file in group_tests:
            file_path = self.project_root / test_file
            if file_path.exists():
                success, stdout, stderr = self.run_command_with_env(
                    f"python {test_file}",
                    f"group_test_{test_file}"
                )
                if success:
                    group_success += 1
                    self.log_result(f"group_test_{test_file}", True, f"Test {test_file} réussi")
                else:
                    self.log_result(f"group_test_{test_file}", False, f"Test {test_file} échoué", stderr)
        
        self.results["integration_tests"]["group_tests_score"] = group_success / len(group_tests) if group_tests else 0
        
        regression_score = (
            self.results["integration_tests"].get("phase_d_script", 0) * 0.6 + 
            self.results["integration_tests"].get("group_tests_score", 0) * 0.4
        )
        self.results["critical_tests"]["non_regression"] = regression_score
        
        return regression_score >= 0.6
    
    def validate_documentation_links(self) -> bool:
        """Test 5: Validation des liens de documentation"""
        print("\n[DOCUMENTATION] === TEST 5: VALIDATION DOCUMENTATION ===")
        
        try:
            # Exécution de l'analyseur de documentation obsolète
            cmd = [
                sys.executable,
                "scripts/maintenance/analyze_obsolete_documentation.py",
                "--quick-scan",
                "--output-format", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                # Documentation saine
                self.log_result("documentation_links", True, "Aucun lien brisé détecté dans la documentation")
                self.results["system_integrity"]["documentation_health"] = True
                return True
            else:
                # Documentation obsolète détectée
                # Tenter de parser la sortie pour obtenir des statistiques
                output_lines = result.stdout.split('\n')
                links_info = {}
                
                for line in output_lines:
                    if "Fichiers analyses:" in line:
                        links_info["analyzed_files"] = line.split(':')[1].strip()
                    elif "Liens totaux:" in line:
                        links_info["total_links"] = line.split(':')[1].strip()
                    elif "Liens brises:" in line:
                        links_info["broken_links"] = line.split(':')[1].strip()
                    elif "Pourcentage de liens valides:" in line:
                        links_info["valid_percentage"] = line.split(':')[1].strip().replace('%', '')
                
                details = f"Documentation obsolète détectée: {links_info.get('broken_links', 'N/A')} liens brisés"
                self.log_result("documentation_links", False, details)
                self.results["system_integrity"]["documentation_health"] = False
                
                # Ajouter un avertissement si le pourcentage de liens valides est très bas
                try:
                    valid_pct = float(links_info.get("valid_percentage", "0"))
                    if valid_pct < 50:
                        self.results["warnings"].append(f"📚 CRITIQUE: Seulement {valid_pct}% des liens de documentation sont valides")
                    elif valid_pct < 80:
                        self.results["warnings"].append(f"📚 ATTENTION: {valid_pct}% des liens de documentation sont valides")
                except ValueError:
                    pass
                
                return False
            
        except subprocess.TimeoutExpired:
            self.log_result("documentation_links", False, "Timeout lors de l'analyse de documentation")
            self.results["system_integrity"]["documentation_health"] = False
            return False
        except Exception as e:
            error_msg = f"Exception lors de la validation documentation: {str(e)}"
            self.log_result("documentation_links", False, error_msg)
            self.results["system_integrity"]["documentation_health"] = False
            return False
    
    def analyze_git_status(self) -> bool:
        """Test 5: Analyse état Git"""
        print("\n[GIT] === TEST 5: ANALYSE GIT ===")
        
        try:
            # Git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )
            
            if result.returncode == 0:
                git_status = result.stdout.strip()
                lines = git_status.split('\n') if git_status else []
                
                modified_files = [line for line in lines if line.startswith('M ')]
                added_files = [line for line in lines if line.startswith('A ')]
                deleted_files = [line for line in lines if line.startswith('D ')]
                untracked_files = [line for line in lines if line.startswith('??')]
                
                self.results["git_analysis"] = {
                    "modified_files": len(modified_files),
                    "added_files": len(added_files),
                    "deleted_files": len(deleted_files),
                    "untracked_files": len(untracked_files),
                    "total_changes": len(lines),
                    "status_detail": git_status
                }
                
                self.log_result("git_status", True, f"Git analysé: {len(lines)} changements détectés")
                return True
            else:
                self.log_result("git_status", False, "Erreur analyse Git", result.stderr)
                return False
                
        except Exception as e:
            self.log_result("git_status", False, "Exception analyse Git", str(e))
            return False
    
    def calculate_overall_score(self) -> float:
        """Calcule le score global de validation"""
        critical_weights = {
            "imports": 0.25,      # 25% - Imports critiques
            "functionality": 0.25, # 25% - Fonctionnalités Sherlock-Watson
            "integrity": 0.20,    # 20% - Intégrité système
            "documentation": 0.15, # 15% - Santé documentation
            "non_regression": 0.15 # 15% - Non-régression
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
            recommendations.append("[CRITIQUE] CRITIQUE: Corriger les problèmes d'imports Oracle Enhanced")
        
        if self.results["critical_tests"].get("functionality", 0) < 0.5:
            recommendations.append("[PRIORITE] HAUTE PRIORITÉ: Déboguer les fonctionnalités Sherlock-Watson-Moriarty")
        
        if self.results["critical_tests"].get("documentation", 0) < 0.8:
            recommendations.append("📚 IMPORTANT: Corriger les liens brisés dans la documentation")
        
        if self.results["critical_tests"].get("integrity", 0) < 0.8:
            recommendations.append("[IMPORTANT] IMPORTANTE: Restaurer l'intégrité de la structure du projet")
        
        if self.results["critical_tests"].get("non_regression", 0) < 0.6:
            recommendations.append("[PRIORITE] PRIORITÉ: Investiguer les régressions détectées")
        
        # Recommandations Git
        git_changes = self.results.get("git_analysis", {}).get("total_changes", 0)
        if git_changes > 50:
            recommendations.append(f"[INFO] INFO: {git_changes} changements Git détectés - Préparer commit structuré")
        
        self.results["recommendations"] = recommendations
    
    def run_validation(self) -> Dict[str, Any]:
        """Lance la validation complète"""
        print("[DEMARRAGE] === DÉBUT VALIDATION ORACLE ENHANCED V2.1.0 ===")
        print(f"[DATE] Date: {self.results['validation_date']}")
        print(f"[PROJET] Projet: {self.project_root}")
        
        start_time = time.time()
        
        # Tests critiques
        tests_results = []
        tests_results.append(self.test_oracle_imports())
        tests_results.append(self.test_sherlock_watson_functionality())
        tests_results.append(self.test_system_integrity())
        tests_results.append(self.test_non_regression())
        tests_results.append(self.validate_documentation_links())
        tests_results.append(self.analyze_git_status())
        
        # Calcul score global
        self.results["overall_score"] = self.calculate_overall_score()
        
        # Détermination du statut
        if self.results["overall_score"] >= 0.85:
            self.results["status"] = "[EXCELLENT] EXCELLENT"
        elif self.results["overall_score"] >= 0.70:
            self.results["status"] = "[VALIDE] VALIDÉ"
        elif self.results["overall_score"] >= 0.50:
            self.results["status"] = "[PARTIEL] PARTIEL"
        else:
            self.results["status"] = "[CRITIQUE] CRITIQUE"
        
        # Génération recommandations
        self.generate_recommendations()
        
        execution_time = time.time() - start_time
        self.results["execution_time"] = execution_time
        
        print(f"\n[FIN] === VALIDATION TERMINÉE ===")
        print(f"[DUREE] Temps d'exécution: {execution_time:.2f}s")
        print(f"[SCORE] Score global: {self.results['overall_score']:.1%}")
        print(f"[STATUT] Statut: {self.results['status']}")
        
        return self.results

def main():
    """Point d'entrée principal"""
    try:
        validator = OracleEnhancedValidator()
        results = validator.run_validation()
        
        # Sauvegarde des résultats
        output_file = Path("logs/final_validation_results.json")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n[SAUVEGARDE] Résultats sauvegardés: {output_file}")
        
        # Code de sortie basé sur le statut
        if results["overall_score"] >= 0.70:
            sys.exit(0)  # Succès
        else:
            sys.exit(1)  # Échec
            
    except Exception as e:
        print(f"[ERREUR] ERREUR CRITIQUE: {str(e)}")
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    main()