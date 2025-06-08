#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution des tests FirstOrderLogicAgent (FOL).

Ce script lance une validation complète de l'agent FOL selon les critères :
✅ Tests unitaires complets  
✅ Tests d'intégration Tweety
✅ Validation complète avec métriques
✅ Tests de migration Modal → FOL
✅ Génération de rapport détaillé

Usage:
    python scripts/run_fol_tests.py [options]
    
Options:
    --unit-only       : Tests unitaires seulement
    --integration     : Tests d'intégration (nécessite Tweety)
    --validation      : Validation complète avec métriques
    --migration       : Tests migration Modal → FOL
    --all            : Tous les tests (défaut)
    --real-tweety    : Force utilisation Tweety réel
    --report-path    : Chemin rapport de sortie
"""

import argparse
import asyncio
import subprocess
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FOLTestRunner:
    """Exécuteur de tests pour agent FOL."""
    
    def __init__(self, args):
        self.args = args
        self.results = {}
        self.start_time = time.time()
        
        # Chemins des tests
        self.test_paths = {
            "unit": "tests/unit/agents/test_fol_logic_agent.py",
            "integration": "tests/integration/test_fol_tweety_integration.py", 
            "validation": "tests/validation/test_fol_complete_validation.py",
            "migration": "tests/migration/test_modal_to_fol_migration.py"
        }
        
        # Configuration environnement
        self.env_config = self._setup_environment()
    
    def _setup_environment(self) -> Dict[str, str]:
        """Configure l'environnement pour les tests."""
        import os
        
        env = os.environ.copy()
        
        # Configuration Tweety si demandé
        if self.args.real_tweety:
            env.update({
                "USE_REAL_JPYPE": "true",
                "TWEETY_JAR_PATH": "libs/tweety-full.jar",
                "JVM_MEMORY": "1024m"
            })
            logger.info("🔧 Configuration Tweety réel activée")
        else:
            env.update({
                "USE_REAL_JPYPE": "false"
            })
            logger.info("🔧 Configuration Tweety mock activée")
        
        # Configuration tests
        env.update({
            "UNIFIED_LOGIC_TYPE": "fol",
            "UNIFIED_MOCK_LEVEL": "none" if self.args.real_tweety else "partial",
            "PYTHONPATH": str(Path.cwd())
        })
        
        return env
    
    def run_pytest_suite(self, test_path: str, test_name: str) -> Dict[str, Any]:
        """Exécute une suite de tests pytest."""
        logger.info(f"▶️ Exécution {test_name}...")
        
        start_time = time.time()
        
        # Construction commande pytest
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "-v",
            "--tb=short"
        ]
        
        # Options spéciales pour intégration
        if test_name == "integration" and not self.args.real_tweety:
            cmd.extend(["-k", "not test_real_tweety"])
        
        try:
            # Création répertoire rapports
            Path("reports").mkdir(exist_ok=True)
            
            # Exécution
            result = subprocess.run(
                cmd,
                env=self.env_config,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max par suite
            )
            
            duration = time.time() - start_time
            
            # Analyse résultats
            success = result.returncode == 0
            
            test_result = {
                "success": success,
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
            
            # Lecture rapport JSON si disponible
            json_report_path = f"reports/{test_name}_report.json"
            if Path(json_report_path).exists():
                try:
                    with open(json_report_path, 'r') as f:
                        json_report = json.load(f)
                        test_result["detailed_report"] = json_report
                except Exception as e:
                    logger.warning(f"⚠️ Impossible de lire rapport JSON: {e}")
            
            if success:
                logger.info(f"✅ {test_name} réussi en {duration:.2f}s")
            else:
                logger.error(f"❌ {test_name} échoué en {duration:.2f}s")
                logger.error(f"Erreur: {result.stderr}")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {test_name} timeout après 5 minutes")
            return {
                "success": False,
                "duration": 300,
                "return_code": -1,
                "error": "Timeout",
                "command": " ".join(cmd)
            }
        except Exception as e:
            logger.error(f"❌ Erreur exécution {test_name}: {e}")
            return {
                "success": False,
                "duration": 0,
                "return_code": -1,
                "error": str(e),
                "command": " ".join(cmd)
            }
    
    async def run_validation_script(self) -> Dict[str, Any]:
        """Exécute le script de validation complète."""
        logger.info("▶️ Exécution validation complète...")
        
        start_time = time.time()
        
        try:
            # Import et exécution du validateur
            sys.path.insert(0, str(Path.cwd()))
            
            from tests.validation.test_fol_complete_validation import FOLCompleteValidator
            
            validator = FOLCompleteValidator()
            report = await validator.run_complete_validation()
            
            duration = time.time() - start_time
            
            validation_result = {
                "success": report.get("overall_success", False),
                "duration": duration,
                "validation_report": report
            }
            
            if validation_result["success"]:
                logger.info(f"✅ Validation complète réussie en {duration:.2f}s")
            else:
                logger.warning(f"⚠️ Validation complète avec problèmes en {duration:.2f}s")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Erreur validation complète: {e}")
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    def run_unit_tests(self):
        """Exécute les tests unitaires."""
        if not Path(self.test_paths["unit"]).exists():
            logger.error(f"❌ Tests unitaires non trouvés: {self.test_paths['unit']}")
            return {"success": False, "error": "Tests non trouvés"}
        
        return self.run_pytest_suite(self.test_paths["unit"], "unit")
    
    def run_integration_tests(self):
        """Exécute les tests d'intégration."""
        if not Path(self.test_paths["integration"]).exists():
            logger.error(f"❌ Tests intégration non trouvés: {self.test_paths['integration']}")
            return {"success": False, "error": "Tests non trouvés"}
        
        return self.run_pytest_suite(self.test_paths["integration"], "integration")
    
    async def run_validation_tests(self):
        """Exécute la validation complète."""
        if not Path(self.test_paths["validation"]).exists():
            logger.error(f"❌ Tests validation non trouvés: {self.test_paths['validation']}")
            return {"success": False, "error": "Tests non trouvés"}
        
        return await self.run_validation_script()
    
    def run_migration_tests(self):
        """Exécute les tests de migration."""
        if not Path(self.test_paths["migration"]).exists():
            logger.error(f"❌ Tests migration non trouvés: {self.test_paths['migration']}")
            return {"success": False, "error": "Tests non trouvés"}
        
        return self.run_pytest_suite(self.test_paths["migration"], "migration")
    
    async def run_all_tests(self):
        """Exécute tous les tests selon la configuration."""
        logger.info("🚀 Début exécution tests FOL")
        
        # Sélection des tests à exécuter
        if self.args.unit_only:
            test_suites = [("unit", self.run_unit_tests)]
        elif self.args.integration:
            test_suites = [("integration", self.run_integration_tests)]
        elif self.args.validation:
            test_suites = [("validation", self.run_validation_tests)]
        elif self.args.migration:
            test_suites = [("migration", self.run_migration_tests)]
        else:  # --all ou défaut
            test_suites = [
                ("unit", self.run_unit_tests),
                ("integration", self.run_integration_tests),
                ("validation", self.run_validation_tests),
                ("migration", self.run_migration_tests)
            ]
        
        # Exécution des suites
        for suite_name, suite_func in test_suites:
            try:
                if asyncio.iscoroutinefunction(suite_func):
                    result = await suite_func()
                else:
                    result = suite_func()
                
                self.results[suite_name] = result
                
            except Exception as e:
                logger.error(f"❌ Erreur suite {suite_name}: {e}")
                self.results[suite_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Génération rapport final
        await self.generate_final_report()
    
    async def generate_final_report(self):
        """Génère le rapport final des tests."""
        total_duration = time.time() - self.start_time
        
        # Calcul statistiques globales
        total_suites = len(self.results)
        successful_suites = sum(1 for r in self.results.values() if r.get("success", False))
        
        # Création rapport
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_duration": total_duration,
            "configuration": {
                "real_tweety": self.args.real_tweety,
                "test_selection": self._get_test_selection()
            },
            "summary": {
                "total_suites": total_suites,
                "successful_suites": successful_suites,
                "success_rate": successful_suites / total_suites if total_suites > 0 else 0.0,
                "overall_success": successful_suites == total_suites
            },
            "results": self.results,
            "recommendations": self._generate_recommendations()
        }
        
        # Sauvegarde rapport
        report_path = Path(self.args.report_path or "reports/fol_tests_complete_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        # Affichage résumé
        self._print_summary(report, report_path)
        
        return report
    
    def _get_test_selection(self) -> str:
        """Retourne la sélection de tests."""
        if self.args.unit_only:
            return "unit_only"
        elif self.args.integration:
            return "integration_only"
        elif self.args.validation:
            return "validation_only"
        elif self.args.migration:
            return "migration_only"
        else:
            return "all"
    
    def _generate_recommendations(self) -> List[str]:
        """Génère recommandations basées sur les résultats."""
        recommendations = []
        
        # Analyse des échecs
        failed_suites = [name for name, result in self.results.items() 
                        if not result.get("success", False)]
        
        if not failed_suites:
            recommendations.append("✅ Tous les tests réussis - Agent FOL prêt pour production")
        else:
            for suite in failed_suites:
                if suite == "unit":
                    recommendations.append("Corriger les tests unitaires avant déploiement")
                elif suite == "integration":
                    recommendations.append("Vérifier intégration Tweety - possibles problèmes JAR/JVM")
                elif suite == "validation":
                    recommendations.append("Améliorer métriques validation selon rapport détaillé")
                elif suite == "migration":
                    recommendations.append("Revoir migration Modal Logic - compatibilité insuffisante")
        
        # Recommandations configuration
        if not self.args.real_tweety:
            recommendations.append("Exécuter avec --real-tweety pour validation complète")
        
        return recommendations
    
    def _print_summary(self, report: Dict[str, Any], report_path: Path):
        """Affiche résumé des résultats."""
        print("\n" + "="*80)
        print("📋 RAPPORT TESTS AGENT FOL")
        print("="*80)
        
        summary = report["summary"]
        print(f"\n🕐 Durée totale: {report['total_duration']:.2f}s")
        print(f"🎯 Succès global: {'✅ OUI' if summary['overall_success'] else '❌ NON'}")
        print(f"📊 Taux réussite: {summary['success_rate']:.1%} ({summary['successful_suites']}/{summary['total_suites']})")
        
        print(f"\n📋 Résultats par suite:")
        for suite_name, result in self.results.items():
            status = "✅" if result.get("success", False) else "❌"
            duration = result.get("duration", 0)
            print(f"  {status} {suite_name.title()}: {duration:.2f}s")
            
            if not result.get("success", False) and "error" in result:
                print(f"      Erreur: {result['error']}")
        
        print(f"\n💡 Recommandations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")
        
        print(f"\n💾 Rapport détaillé: {report_path}")
        
        if summary["overall_success"]:
            print("\n🎉 Agent FOL validé avec succès!")
        else:
            print("\n⚠️ Agent FOL nécessite des corrections")


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Exécuteur de tests pour FirstOrderLogicAgent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python scripts/run_fol_tests.py --all
  python scripts/run_fol_tests.py --unit-only
  python scripts/run_fol_tests.py --integration --real-tweety
  python scripts/run_fol_tests.py --validation --report-path reports/custom.json
        """
    )
    
    # Options de sélection des tests
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--unit-only", action="store_true",
                      help="Exécuter seulement les tests unitaires")
    group.add_argument("--integration", action="store_true", 
                      help="Exécuter seulement les tests d'intégration")
    group.add_argument("--validation", action="store_true",
                      help="Exécuter seulement la validation complète")
    group.add_argument("--migration", action="store_true",
                      help="Exécuter seulement les tests de migration")
    group.add_argument("--all", action="store_true", default=True,
                      help="Exécuter tous les tests (défaut)")
    
    # Options de configuration
    parser.add_argument("--real-tweety", action="store_true",
                       help="Utiliser Tweety réel (nécessite JAR)")
    parser.add_argument("--report-path", type=str,
                       help="Chemin du rapport de sortie")
    
    args = parser.parse_args()
    
    # Exécution
    runner = FOLTestRunner(args)
    
    try:
        asyncio.run(runner.run_all_tests())
        
        # Code de sortie basé sur le succès
        overall_success = all(r.get("success", False) for r in runner.results.values())
        sys.exit(0 if overall_success else 1)
        
    except KeyboardInterrupt:
        logger.info("🛑 Interruption utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()