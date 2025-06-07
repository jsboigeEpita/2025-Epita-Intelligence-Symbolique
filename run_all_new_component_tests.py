#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrateur Master de Validation des Nouveaux Composants
========================================================

Script principal pour exécuter tous les nouveaux tests créés et générer
un rapport consolidé de validation du système complet.

Usage:
    python run_all_new_component_tests.py --authentic --verbose
    python run_all_new_component_tests.py --fast
    python run_all_new_component_tests.py --component TweetyErrorAnalyzer
"""

import argparse
import subprocess
import sys
import time
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import traceback

# Configuration de l'encodage pour Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Tentative de forcer UTF-8 sur stdout
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Configuration des couleurs pour output console
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

@dataclass
class TestSuiteResult:
    """Résultat d'exécution d'une suite de tests."""
    name: str
    files: List[str]
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    success: bool = False
    error_messages: List[str] = None
    coverage: Optional[float] = None
    authenticity_level: str = "UNKNOWN"
    
    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []
    
    @property
    def total_tests(self) -> int:
        return self.passed + self.failed + self.skipped + self.errors
    
    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

@dataclass
class ValidationReport:
    """Rapport consolidé de validation."""
    timestamp: str
    total_duration: float
    suite_results: List[TestSuiteResult]
    global_status: str
    authenticity_level: str
    recommendations: List[str]
    
    @property
    def total_tests(self) -> int:
        return sum(r.total_tests for r in self.suite_results)
    
    @property
    def total_passed(self) -> int:
        return sum(r.passed for r in self.suite_results)
    
    @property
    def total_failed(self) -> int:
        return sum(r.failed for r in self.suite_results)
    
    @property
    def global_pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.total_passed / self.total_tests) * 100

class TestSuiteRunner:
    """Exécuteur de suites de tests avec validation."""
    
    # Configuration des suites de tests
    TEST_SUITES = {
        "TweetyErrorAnalyzer": {
            "files": ["tests/unit/argumentation_analysis/test_tweety_error_analyzer.py"],
            "description": "Analyseur d'erreurs Tweety avec feedback BNF",
            "expected_tests": 21,
            "fast": True,
            "authenticity_required": False
        },
        "UnifiedConfig": {
            "files": [
                "tests/unit/config/test_unified_config.py",
                "tests/unit/scripts/test_configuration_cli.py", 
                "tests/unit/integration/test_unified_config_integration.py"
            ],
            "description": "Système de configuration unifié",
            "expected_tests": 12,
            "fast": True,
            "authenticity_required": False
        },
        "FirstOrderLogicAgent": {
            "files": ["tests/unit/agents/test_fol_logic_agent.py"],
            "description": "Agent logique premier ordre avec intégration Tweety",
            "expected_tests": 25,
            "fast": True,
            "authenticity_required": True
        },
        "AuthenticitySystem": {
            "files": [
                "tests/unit/authentication/test_mock_elimination_advanced.py",
                "tests/integration/test_authentic_components.py",
                "tests/unit/authentication/test_cli_authentic_commands.py"
            ],
            "description": "Système d'authenticité et élimination des mocks",
            "expected_tests": 17,
            "fast": False,
            "authenticity_required": True
        },
        "UnifiedOrchestrations": {
            "files": [
                "tests/unit/orchestration/test_unified_orchestrations.py",
                "tests/integration/test_unified_system_integration.py"
            ],
            "description": "Orchestrations système unifiées",
            "expected_tests": 8,
            "fast": False,
            "authenticity_required": True
        }
    }
    
    def __init__(self, authentic: bool = False, verbose: bool = False):
        self.authentic = authentic
        self.verbose = verbose
        self.project_root = Path(__file__).parent
        
    def _check_prerequisites(self) -> Tuple[bool, List[str]]:
        """Vérifie les prérequis système."""
        issues = []
        
        # Vérification Python et pytest
        try:
            result = subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                issues.append("pytest non disponible")
        except Exception:
            issues.append("pytest non disponible")
        
        # Vérification configuration unifiée
        config_file = self.project_root / "config" / "unified_config.py"
        if not config_file.exists():
            issues.append("Configuration unifiée manquante")
        
        # Vérifications authentiques si requises
        if self.authentic:
            # Vérification clé API OpenAI
            import os
            if not os.getenv("OPENAI_API_KEY"):
                issues.append("Clé API OpenAI manquante")
            
            # Vérification JAR Tweety
            tweety_jar = self.project_root / "libs" / "tweety.jar"
            if not tweety_jar.exists():
                issues.append("JAR Tweety manquant")
            
            # Vérification taxonomie sophismes
            taxonomy_dir = self.project_root / "config" / "taxonomies"
            if not taxonomy_dir.exists():
                issues.append("Taxonomie sophismes manquante")
        
        return len(issues) == 0, issues
    
    def _run_pytest_command(self, files: List[str], suite_name: str) -> Tuple[TestSuiteResult, str]:
        """Exécute une commande pytest et parse les résultats."""
        start_time = time.time()
        
        # Construction de la commande pytest
        cmd = [
            sys.executable, "-m", "pytest",
            "-v",
            "--tb=short",
            "--no-header"
        ]
        
        # Ajout de la couverture si authentique
        if self.authentic:
            cmd.extend(["--cov=argumentation_analysis", "--cov-report=term-missing"])
        
        # Ajout des fichiers
        existing_files = []
        for file_path in files:
            full_path = self.project_root / file_path
            if full_path.exists():
                existing_files.append(str(full_path))
            else:
                print(f"⚠️  Fichier manquant: {file_path}")
        
        if not existing_files:
            duration = time.time() - start_time
            return TestSuiteResult(
                name=suite_name,
                files=files,
                success=False,
                duration=duration,
                error_messages=["Aucun fichier de test trouvé"]
            ), ""
        
        cmd.extend(existing_files)
        
        # Exécution
        try:
            if self.verbose:
                print(f"🔄 Exécution: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes max
                cwd=str(self.project_root),
                encoding='utf-8',
                errors='replace'  # Remplace les caractères non décodables
            )
            
            duration = time.time() - start_time
            # Gestion sécurisée des outputs None
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            output = stdout + stderr
            
            # Parse des résultats pytest
            return self._parse_pytest_output(
                output, result.returncode, suite_name, files, duration
            ), output
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestSuiteResult(
                name=suite_name,
                files=files,
                success=False,
                duration=duration,
                error_messages=["Timeout lors de l'exécution des tests"]
            ), "TIMEOUT"
        except Exception as e:
            duration = time.time() - start_time
            return TestSuiteResult(
                name=suite_name,
                files=files,
                success=False,
                duration=duration,
                error_messages=[f"Erreur d'exécution: {str(e)}"]
            ), str(e)
    
    def _parse_pytest_output(self, output: str, return_code: int, 
                           suite_name: str, files: List[str], duration: float) -> TestSuiteResult:
        """Parse la sortie de pytest pour extraire les métriques."""
        result = TestSuiteResult(name=suite_name, files=files, duration=duration)
        
        # Recherche des statistiques finales pytest
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            
            # Format: "= 21 passed in 0.09s ="
            if " passed " in line and " in " in line:
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed" and i > 0:
                            result.passed = int(parts[i-1])
                        elif part == "failed" and i > 0:
                            result.failed = int(parts[i-1])
                        elif part == "skipped" and i > 0:
                            result.skipped = int(parts[i-1])
                        elif part == "error" and i > 0:
                            result.errors = int(parts[i-1])
                except (ValueError, IndexError):
                    pass
            
            # Recherche des erreurs
            if "FAILED" in line or "ERROR" in line:
                result.error_messages.append(line)
            
            # Couverture si disponible
            if "Total coverage:" in line:
                try:
                    coverage_str = line.split(":")[-1].strip().rstrip('%')
                    result.coverage = float(coverage_str)
                except ValueError:
                    pass
        
        # Détermination du succès
        result.success = (return_code == 0 and result.failed == 0 and result.errors == 0)
        
        # Niveau d'authenticité
        if self.authentic and result.success:
            result.authenticity_level = "AUTHENTIC"
        elif result.success:
            result.authenticity_level = "MOCK"
        else:
            result.authenticity_level = "FAILED"
        
        return result
    
    def run_suite(self, suite_name: str) -> Tuple[TestSuiteResult, str]:
        """Exécute une suite de tests spécifique."""
        if suite_name not in self.TEST_SUITES:
            raise ValueError(f"Suite inconnue: {suite_name}")
        
        suite_config = self.TEST_SUITES[suite_name]
        
        # Vérification des prérequis d'authenticité
        if suite_config["authenticity_required"] and not self.authentic:
            print(f"⚠️  {suite_name}: Mode authentique recommandé")
        
        print(f"\n{'='*60}")
        print(f"🧪 EXÉCUTION: {suite_name}")
        print(f"📝 {suite_config['description']}")
        print(f"📁 Fichiers: {len(suite_config['files'])}")
        print(f"🎯 Tests attendus: {suite_config['expected_tests']}")
        print(f"{'='*60}")
        
        return self._run_pytest_command(suite_config["files"], suite_name)
    
    def run_all_suites(self, component_filter: Optional[str] = None, 
                      fast_only: bool = False) -> ValidationReport:
        """Exécute toutes les suites de tests."""
        start_time = time.time()
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}[TEST] VALIDATION COMPLETE DES NOUVEAUX COMPOSANTS{Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"[TIME] Debut: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[MODE] Mode: {'Authentique' if self.authentic else 'Mock'}")
        print(f"[SPEED] Rapide: {'Oui' if fast_only else 'Non'}")
        
        # Vérification des prérequis
        prereq_ok, issues = self._check_prerequisites()
        if not prereq_ok:
            print(f"\n{Colors.RED}[ERROR] PREREQUIS MANQUANTS:{Colors.END}")
            for issue in issues:
                print(f"  - {issue}")
            if not self.authentic:
                print(f"{Colors.YELLOW}[INFO] Passage en mode degrade{Colors.END}")
            else:
                print(f"{Colors.RED}[ERROR] Impossible de continuer en mode authentique{Colors.END}")
                sys.exit(1)
        
        # Sélection des suites
        suites_to_run = []
        for suite_name, config in self.TEST_SUITES.items():
            # Filtrage par composant
            if component_filter and suite_name != component_filter:
                continue
            
            # Filtrage mode rapide
            if fast_only and not config["fast"]:
                continue
            
            suites_to_run.append(suite_name)
        
        print(f"\n[LIST] Suites selectionnees: {len(suites_to_run)}")
        for suite in suites_to_run:
            print(f"  - {suite}")
        
        # Exécution des suites
        results = []
        outputs = {}
        
        for i, suite_name in enumerate(suites_to_run, 1):
            print(f"\n{Colors.CYAN}[{i}/{len(suites_to_run)}]{Colors.END}")
            
            try:
                result, output = self.run_suite(suite_name)
                results.append(result)
                outputs[suite_name] = output
                
                # Affichage du résultat
                status_icon = "[OK]" if result.success else "[FAIL]"
                color = Colors.GREEN if result.success else Colors.RED
                
                print(f"{color}{status_icon} {suite_name}: {result.passed}/{result.total_tests} tests ({result.pass_rate:.1f}%) - {result.duration:.2f}s{Colors.END}")
                
                if not result.success and self.verbose:
                    print(f"{Colors.RED}Erreurs:{Colors.END}")
                    for error in result.error_messages[:3]:  # Max 3 erreurs
                        print(f"  {error}")
                
            except Exception as e:
                error_result = TestSuiteResult(
                    name=suite_name,
                    files=self.TEST_SUITES[suite_name]["files"],
                    success=False,
                    duration=0.0,
                    error_messages=[f"Exception: {str(e)}"]
                )
                results.append(error_result)
                outputs[suite_name] = traceback.format_exc()
                
                print(f"{Colors.RED}[EXCEPTION] {suite_name}: {str(e)}{Colors.END}")
        
        # Génération du rapport
        total_duration = time.time() - start_time
        
        # Détermination du statut global
        all_passed = all(r.success for r in results)
        global_status = "[OK] PRODUCTION READY" if all_passed else "[FAIL] ISSUES DETECTEES"
        
        # Niveau d'authenticité global
        if self.authentic and all_passed:
            authenticity_level = "100% AUTHENTIQUE"
        elif all_passed:
            authenticity_level = "MOCK VALIDÉ"
        else:
            authenticity_level = "ÉCHEC PARTIEL"
        
        # Recommandations
        recommendations = []
        if not all_passed:
            failed_suites = [r.name for r in results if not r.success]
            recommendations.append(f"Corriger les erreurs dans: {', '.join(failed_suites)}")
        
        if not self.authentic:
            recommendations.append("Exécuter en mode authentique pour validation complète")
        
        for result in results:
            if result.total_tests < self.TEST_SUITES[result.name]["expected_tests"]:
                recommendations.append(f"{result.name}: Tests manquants détectés")
        
        report = ValidationReport(
            timestamp=datetime.now().isoformat(),
            total_duration=total_duration,
            suite_results=results,
            global_status=global_status,
            authenticity_level=authenticity_level,
            recommendations=recommendations
        )
        
        # Affichage du résumé
        self._print_summary(report)
        
        # Sauvegarde des outputs détaillés si verbose
        if self.verbose:
            self._save_detailed_outputs(outputs, report)
        
        return report
    
    def _print_summary(self, report: ValidationReport):
        """Affiche le résumé consolidé."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}[SUMMARY] RESUME GLOBAL{Colors.END}")
        print(f"{Colors.BLUE}{'='*50}{Colors.END}")
        
        # Résultats par suite
        for result in report.suite_results:
            status_icon = "[OK]" if result.success else "[FAIL]"
            color = Colors.GREEN if result.success else Colors.RED
            print(f"{color}{status_icon} {result.name:<20} : {result.passed:>2}/{result.total_tests:<2} tests ({result.pass_rate:>5.1f}%) - {result.duration:>5.2f}s{Colors.END}")
        
        print(f"\n{Colors.BOLD}[METRICS] METRIQUES GLOBALES{Colors.END}")
        print(f"- Total tests : {report.total_passed}/{report.total_tests} ({report.global_pass_rate:.1f}%)")
        print(f"- Temps total : {report.total_duration:.2f}s")
        print(f"- Authenticité : {report.authenticity_level}")
        
        # Statut final
        if "[OK]" in report.global_status:
            print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] {report.global_status}{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}[WARNING] {report.global_status}{Colors.END}")
        
        # Recommandations
        if report.recommendations:
            print(f"\n{Colors.YELLOW}[RECOMMENDATIONS] RECOMMANDATIONS{Colors.END}")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"{i}. {rec}")
    
    def _save_detailed_outputs(self, outputs: Dict[str, str], report: ValidationReport):
        """Sauvegarde les outputs détaillés."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Outputs raw
        output_file = self.project_root / f"validation_outputs_{timestamp}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"VALIDATION OUTPUTS - {report.timestamp}\n")
            f.write("="*80 + "\n\n")
            
            for suite_name, output in outputs.items():
                f.write(f"SUITE: {suite_name}\n")
                f.write("-"*40 + "\n")
                # Gestion sécurisée des outputs None
                if output is not None:
                    f.write(output)
                else:
                    f.write("ERREUR: Output manquant ou None")
                f.write("\n\n")
        
        print(f"\n[SAVE] Outputs detailles sauves: {output_file}")
    
    def save_report(self, report: ValidationReport, output_file: Optional[str] = None):
        """Sauvegarde le rapport en JSON."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"validation_report_{timestamp}.json"
        
        output_path = self.project_root / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        
        print(f"\n[SAVE] Rapport JSON sauve: {output_path}")
        return output_path

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Orchestrateur Master de Validation des Nouveaux Composants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'usage:
  python run_all_new_component_tests.py --authentic --verbose
  python run_all_new_component_tests.py --fast
  python run_all_new_component_tests.py --component TweetyErrorAnalyzer
  python run_all_new_component_tests.py --report validation_report.json
        """
    )
    
    parser.add_argument(
        "--authentic", 
        action="store_true",
        help="Mode authentique (composants réels, API, etc.)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Affichage détaillé"
    )
    
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Tests unitaires rapides seulement"
    )
    
    parser.add_argument(
        "--component",
        choices=list(TestSuiteRunner.TEST_SUITES.keys()),
        help="Exécuter un composant spécifique"
    )
    
    parser.add_argument(
        "--level",
        choices=["unit", "integration", "all"],
        default="all",
        help="Niveau de tests à exécuter"
    )
    
    parser.add_argument(
        "--report",
        help="Fichier de sortie pour le rapport JSON"
    )
    
    parser.add_argument(
        "--output",
        help="Alias pour --report"
    )
    
    args = parser.parse_args()
    
    # Configuration du runner
    runner = TestSuiteRunner(authentic=args.authentic, verbose=args.verbose)
    
    try:
        # Exécution
        report = runner.run_all_suites(
            component_filter=args.component,
            fast_only=args.fast
        )
        
        # Sauvegarde du rapport
        if args.report or args.output:
            runner.save_report(report, args.report or args.output)
        
        # Code de retour
        all_passed = all(r.success for r in report.suite_results)
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[INTERRUPT] Interruption utilisateur{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}[CRITICAL] ERREUR CRITIQUE: {str(e)}{Colors.END}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()