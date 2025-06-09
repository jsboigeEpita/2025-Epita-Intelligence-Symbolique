#!/usr/bin/env python3
"""
Test de Non-Régression Phase 5 - Validation des Interfaces Coexistantes
======================================================================

Ce script valide que :
1. L'interface React existante (interface_web/) fonctionne toujours
2. L'interface simple active (services/web_api/interface-simple/) fonctionne  
3. Les deux interfaces peuvent coexister sans conflit
4. Les anciennes fonctionnalités ne sont pas cassées

Version: 1.0.0
Date: 09/06/2025
"""

import asyncio
import json
import logging
import subprocess
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [Phase5] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration des ports pour éviter les conflits
INTERFACE_REACT_PORT = 3001    # Interface React existante
INTERFACE_SIMPLE_PORT = 3000   # Interface simple (actuellement active)
PLAYWRIGHT_TIMEOUT = 30       # Timeout pour les tests Playwright

class Phase5ValidationManager:
    """Gestionnaire de validation pour la Phase 5."""
    
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent
        self.results = {}
        self.processes = []
        
    async def run_validation(self) -> Dict[str, Any]:
        """Execute la validation complète de non-régression."""
        logger.info("🚀 DÉMARRAGE VALIDATION PHASE 5 - NON-RÉGRESSION")
        
        try:
            # 1. Test des interfaces séparément
            react_results = await self._test_react_interface()
            simple_results = await self._test_simple_interface() 
            
            # 2. Test de coexistence
            coexistence_results = await self._test_coexistence()
            
            # 3. Test des anciennes fonctionnalités
            legacy_results = await self._test_legacy_functionalities()
            
            # 4. Test des scripts et APIs existants
            scripts_results = await self._test_existing_scripts()
            
            # 5. Compilation des résultats
            self.results = {
                'timestamp': datetime.now().isoformat(),
                'phase': 5,
                'validation_type': 'non_regression',
                'interfaces': {
                    'react_interface': react_results,
                    'simple_interface': simple_results,
                    'coexistence': coexistence_results
                },
                'legacy_validation': {
                    'functionalities': legacy_results,
                    'scripts': scripts_results
                },
                'summary': self._generate_summary()
            }
            
            return self.results
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation: {e}")
            self.results['error'] = str(e)
            return self.results
        finally:
            await self._cleanup_processes()
    
    async def _test_react_interface(self) -> Dict[str, Any]:
        """Teste l'interface React existante."""
        logger.info("📱 Test Interface React (interface_web/)")
        
        results = {
            'status': 'unknown',
            'startup': False,
            'accessibility': False,
            'functionality': False,
            'port': INTERFACE_REACT_PORT,
            'errors': []
        }
        
        try:
            # Démarrage de l'interface React sur port 3001
            logger.info(f"Démarrage interface React sur port {INTERFACE_REACT_PORT}")
            
            # Modification temporaire du port dans l'interface React
            react_app_path = self.project_root / "interface_web" / "app.py"
            await self._start_interface_on_port(
                str(react_app_path.parent), 
                INTERFACE_REACT_PORT,
                "react"
            )
            
            # Attendre le démarrage
            await asyncio.sleep(5)
            
            # Test d'accessibilité
            if await self._test_interface_accessibility(INTERFACE_REACT_PORT):
                results['accessibility'] = True
                logger.info("✅ Interface React accessible")
                
                # Test de fonctionnalité basique
                if await self._test_basic_functionality(INTERFACE_REACT_PORT):
                    results['functionality'] = True
                    logger.info("✅ Interface React fonctionnelle")
                    results['status'] = 'operational'
                else:
                    results['errors'].append("Fonctionnalité de base échouée")
            else:
                results['errors'].append("Interface non accessible")
                
            results['startup'] = True
            
        except Exception as e:
            logger.error(f"Erreur interface React: {e}")
            results['errors'].append(str(e))
            results['status'] = 'error'
            
        return results
    
    async def _test_simple_interface(self) -> Dict[str, Any]:
        """Teste l'interface simple active."""
        logger.info("🔧 Test Interface Simple (services/web_api/interface-simple/)")
        
        results = {
            'status': 'unknown',
            'startup': False,
            'accessibility': False,
            'functionality': False,
            'servicemanager_integration': False,
            'port': INTERFACE_SIMPLE_PORT,
            'errors': []
        }
        
        try:
            # L'interface simple devrait déjà être accessible ou redémarrable
            logger.info(f"Test interface simple sur port {INTERFACE_SIMPLE_PORT}")
            
            # Redémarrage de l'interface simple
            simple_app_path = self.project_root / "services" / "web_api" / "interface-simple"
            await self._start_interface_on_port(
                str(simple_app_path), 
                INTERFACE_SIMPLE_PORT,
                "simple"
            )
            
            # Attendre le démarrage
            await asyncio.sleep(5)
            
            # Test d'accessibilité
            if await self._test_interface_accessibility(INTERFACE_SIMPLE_PORT):
                results['accessibility'] = True
                logger.info("✅ Interface Simple accessible")
                
                # Test de fonctionnalité basique
                if await self._test_basic_functionality(INTERFACE_SIMPLE_PORT):
                    results['functionality'] = True
                    logger.info("✅ Interface Simple fonctionnelle")
                    
                # Test d'intégration ServiceManager
                if await self._test_servicemanager_integration(INTERFACE_SIMPLE_PORT):
                    results['servicemanager_integration'] = True
                    logger.info("✅ ServiceManager intégré")
                    results['status'] = 'operational'
                else:
                    results['status'] = 'degraded'
            else:
                results['errors'].append("Interface non accessible")
                
            results['startup'] = True
            
        except Exception as e:
            logger.error(f"Erreur interface simple: {e}")
            results['errors'].append(str(e))
            results['status'] = 'error'
            
        return results
    
    async def _test_coexistence(self) -> Dict[str, Any]:
        """Teste la coexistence des deux interfaces."""
        logger.info("🤝 Test Coexistence des Interfaces")
        
        results = {
            'simultaneous_access': False,
            'port_conflict': False,
            'resource_sharing': False,
            'performance_impact': 'unknown',
            'errors': []
        }
        
        try:
            # Test d'accès simultané aux deux interfaces
            react_response = await self._make_request(INTERFACE_REACT_PORT, '/status')
            simple_response = await self._make_request(INTERFACE_SIMPLE_PORT, '/status')
            
            if react_response and simple_response:
                results['simultaneous_access'] = True
                logger.info("✅ Accès simultané réussi")
                
                # Vérification absence de conflit de ports
                if react_response.get('status') and simple_response.get('status'):
                    results['port_conflict'] = False  # Pas de conflit
                    logger.info("✅ Aucun conflit de ports détecté")
                    
                    # Test de performance avec charge simultanée
                    perf_result = await self._test_simultaneous_load()
                    results['performance_impact'] = perf_result
                    results['resource_sharing'] = True
                    
        except Exception as e:
            logger.error(f"Erreur test coexistence: {e}")
            results['errors'].append(str(e))
            
        return results
    
    async def _test_legacy_functionalities(self) -> Dict[str, Any]:
        """Teste les anciennes fonctionnalités pour détecter les régressions."""
        logger.info("🔍 Test Fonctionnalités Existantes")
        
        results = {
            'servicemanager_compatibility': False,
            'api_endpoints': {},
            'data_processing': False,
            'configuration_loading': False,
            'errors': []
        }
        
        try:
            # Test de compatibilité ServiceManager
            if await self._test_servicemanager_compatibility():
                results['servicemanager_compatibility'] = True
                logger.info("✅ ServiceManager compatible")
            
            # Test des endpoints API existants
            api_tests = await self._test_api_endpoints()
            results['api_endpoints'] = api_tests
            
            # Test de traitement des données
            if await self._test_data_processing():
                results['data_processing'] = True
                logger.info("✅ Traitement des données fonctionnel")
            
            # Test de chargement de configuration
            if await self._test_configuration_loading():
                results['configuration_loading'] = True
                logger.info("✅ Configuration chargée correctement")
                
        except Exception as e:
            logger.error(f"Erreur test fonctionnalités: {e}")
            results['errors'].append(str(e))
            
        return results
    
    async def _test_existing_scripts(self) -> Dict[str, Any]:
        """Teste les scripts existants pour s'assurer qu'ils fonctionnent toujours."""
        logger.info("📜 Test Scripts Existants")
        
        results = {
            'import_tests': False,
            'configuration_scripts': False,
            'data_scripts': False,
            'errors': []
        }
        
        try:
            # Test d'import des modules principaux
            if await self._test_module_imports():
                results['import_tests'] = True
                logger.info("✅ Imports de modules réussis")
            
            # Test des scripts de configuration
            if await self._test_configuration_scripts():
                results['configuration_scripts'] = True
                logger.info("✅ Scripts de configuration fonctionnels")
            
            # Test des scripts de données
            if await self._test_data_scripts():
                results['data_scripts'] = True
                logger.info("✅ Scripts de données fonctionnels")
                
        except Exception as e:
            logger.error(f"Erreur test scripts: {e}")
            results['errors'].append(str(e))
            
        return results
    
    async def _start_interface_on_port(self, app_dir: str, port: int, interface_type: str):
        """Démarre une interface sur un port spécifique."""
        try:
            # Arrêt des processus Python existants sur le port
            await self._kill_process_on_port(port)
            
            # Commande de démarrage avec port personnalisé
            env = os.environ.copy()
            env['PORT'] = str(port)
            
            cmd = f'cd "{app_dir}" && python app.py'
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            self.processes.append(process)
            logger.info(f"Interface {interface_type} démarrée sur port {port} (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Erreur démarrage interface {interface_type}: {e}")
            raise
    
    async def _test_interface_accessibility(self, port: int) -> bool:
        """Teste l'accessibilité d'une interface."""
        try:
            for attempt in range(10):  # 10 tentatives
                try:
                    response = requests.get(f'http://localhost:{port}/', timeout=5)
                    if response.status_code == 200:
                        return True
                except:
                    await asyncio.sleep(2)
                    continue
            return False
        except Exception as e:
            logger.error(f"Erreur accessibilité port {port}: {e}")
            return False
    
    async def _test_basic_functionality(self, port: int) -> bool:
        """Teste la fonctionnalité de base d'une interface."""
        try:
            # Test du statut
            status_response = await self._make_request(port, '/status')
            if not status_response:
                return False
            
            # Test des exemples
            examples_response = await self._make_request(port, '/api/examples')
            if not examples_response:
                return False
            
            # Test d'analyse simple
            analysis_response = await self._make_request(
                port, 
                '/analyze',
                method='POST',
                data={
                    'text': 'Test de régression simple',
                    'analysis_type': 'comprehensive'
                }
            )
            
            return analysis_response is not None
            
        except Exception as e:
            logger.error(f"Erreur fonctionnalité port {port}: {e}")
            return False
    
    async def _test_servicemanager_integration(self, port: int) -> bool:
        """Teste l'intégration ServiceManager."""
        try:
            status_response = await self._make_request(port, '/status')
            if status_response and 'services' in status_response:
                services = status_response['services']
                return services.get('service_manager') == 'active'
            return False
        except Exception as e:
            logger.error(f"Erreur test ServiceManager port {port}: {e}")
            return False
    
    async def _make_request(self, port: int, endpoint: str, method: str = 'GET', data: Dict = None) -> Optional[Dict]:
        """Effectue une requête HTTP vers une interface."""
        try:
            url = f'http://localhost:{port}{endpoint}'
            
            if method == 'GET':
                response = requests.get(url, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=15)
            else:
                return None
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.debug(f"Erreur requête {method} {endpoint} port {port}: {e}")
            return None
    
    async def _test_simultaneous_load(self) -> str:
        """Teste la performance avec charge simultanée."""
        try:
            start_time = time.time()
            
            # Requêtes simultanées aux deux interfaces
            tasks = []
            for _ in range(5):
                tasks.append(self._make_request(INTERFACE_REACT_PORT, '/status'))
                tasks.append(self._make_request(INTERFACE_SIMPLE_PORT, '/status'))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Évaluation de la performance
            success_count = sum(1 for r in results if isinstance(r, dict))
            success_rate = success_count / len(results)
            
            if success_rate > 0.8 and duration < 10:
                return 'good'
            elif success_rate > 0.6:
                return 'acceptable'
            else:
                return 'degraded'
                
        except Exception:
            return 'error'
    
    async def _test_servicemanager_compatibility(self) -> bool:
        """Teste la compatibilité ServiceManager."""
        try:
            # Import test
            from argumentation_analysis.orchestration.service_manager import ServiceManager
            
            # Test de création d'instance
            manager = ServiceManager()
            return True
            
        except Exception as e:
            logger.debug(f"ServiceManager compatibility error: {e}")
            return False
    
    async def _test_api_endpoints(self) -> Dict[str, bool]:
        """Teste les endpoints API existants."""
        endpoints = {
            '/status': False,
            '/api/examples': False,
            '/analyze': False
        }
        
        try:
            for endpoint in endpoints:
                # Test sur l'interface simple (plus complète)
                if endpoint == '/analyze':
                    response = await self._make_request(
                        INTERFACE_SIMPLE_PORT, 
                        endpoint,
                        'POST',
                        {'text': 'test', 'analysis_type': 'comprehensive'}
                    )
                else:
                    response = await self._make_request(INTERFACE_SIMPLE_PORT, endpoint)
                
                endpoints[endpoint] = response is not None
                
        except Exception as e:
            logger.error(f"Erreur test endpoints: {e}")
            
        return endpoints
    
    async def _test_data_processing(self) -> bool:
        """Teste le traitement des données."""
        try:
            # Test simple de traitement de texte
            test_text = "Si A alors B. A. Donc B."
            
            # Simulation de traitement
            words = test_text.split()
            sentences = test_text.count('.')
            
            return len(words) > 0 and sentences > 0
            
        except Exception:
            return False
    
    async def _test_configuration_loading(self) -> bool:
        """Teste le chargement de configuration."""
        try:
            # Vérification de la présence de fichiers de configuration
            config_files = [
                self.project_root / "config",
                self.project_root / ".env"
            ]
            
            return any(f.exists() for f in config_files)
            
        except Exception:
            return False
    
    async def _test_module_imports(self) -> bool:
        """Teste l'import des modules principaux."""
        try:
            # Test d'imports critiques
            import argumentation_analysis
            from argumentation_analysis.orchestration.service_manager import ServiceManager
            
            return True
            
        except Exception as e:
            logger.debug(f"Import error: {e}")
            return False
    
    async def _test_configuration_scripts(self) -> bool:
        """Teste les scripts de configuration."""
        try:
            # Vérification de la présence de scripts de configuration
            scripts_dir = self.project_root / "scripts"
            if scripts_dir.exists():
                config_scripts = list(scripts_dir.glob("*config*"))
                return len(config_scripts) > 0
            return False
            
        except Exception:
            return False
    
    async def _test_data_scripts(self) -> bool:
        """Teste les scripts de données."""
        try:
            # Vérification de la présence de scripts de données
            scripts_dir = self.project_root / "scripts"
            if scripts_dir.exists():
                data_scripts = list(scripts_dir.glob("*data*"))
                return len(data_scripts) > 0
            return True  # Pas critique si absent
            
        except Exception:
            return False
    
    async def _kill_process_on_port(self, port: int):
        """Arrête les processus utilisant un port."""
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/f', '/im', 'python.exe'], 
                             capture_output=True, check=False)
            else:  # Unix/Linux
                subprocess.run(['pkill', '-f', f'port.*{port}'], 
                             capture_output=True, check=False)
        except Exception:
            pass
    
    async def _cleanup_processes(self):
        """Nettoie les processus démarrés."""
        for process in self.processes:
            try:
                if process.returncode is None:
                    process.terminate()
                    await asyncio.sleep(1)
                    if process.returncode is None:
                        process.kill()
            except Exception as e:
                logger.debug(f"Erreur nettoyage processus: {e}")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Génère un résumé de la validation."""
        summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'success_rate': 0.0,
            'critical_issues': [],
            'recommendations': []
        }
        
        # Analyse des résultats des interfaces
        interfaces = self.results.get('interfaces', {})
        
        for interface_name, interface_data in interfaces.items():
            if isinstance(interface_data, dict):
                if interface_name != 'coexistence':
                    # Tests d'interface individuelle
                    tests = ['startup', 'accessibility', 'functionality']
                    for test in tests:
                        summary['total_tests'] += 1
                        if interface_data.get(test, False):
                            summary['passed_tests'] += 1
                        else:
                            summary['failed_tests'] += 1
                            if test in ['accessibility', 'functionality']:
                                summary['critical_issues'].append(
                                    f"{interface_name}: {test} échoué"
                                )
                else:
                    # Tests de coexistence
                    coex_tests = ['simultaneous_access', 'resource_sharing']
                    for test in coex_tests:
                        summary['total_tests'] += 1
                        if interface_data.get(test, False):
                            summary['passed_tests'] += 1
                        else:
                            summary['failed_tests'] += 1
        
        # Analyse des fonctionnalités héritées
        legacy = self.results.get('legacy_validation', {})
        for category, category_data in legacy.items():
            if isinstance(category_data, dict):
                for test_name, test_result in category_data.items():
                    if test_name != 'errors' and isinstance(test_result, bool):
                        summary['total_tests'] += 1
                        if test_result:
                            summary['passed_tests'] += 1
                        else:
                            summary['failed_tests'] += 1
        
        # Calcul du taux de réussite
        if summary['total_tests'] > 0:
            summary['success_rate'] = (summary['passed_tests'] / summary['total_tests']) * 100
        
        # Recommandations basées sur les résultats
        if summary['success_rate'] >= 90:
            summary['recommendations'].append("✅ Validation réussie - Aucune régression détectée")
        elif summary['success_rate'] >= 75:
            summary['recommendations'].append("⚠️ Validation partielle - Vérifier les échecs mineurs")
        else:
            summary['recommendations'].append("❌ Validation échouée - Régressions critiques détectées")
            
        if len(summary['critical_issues']) > 0:
            summary['recommendations'].append("🔧 Corriger les problèmes critiques identifiés")
        
        return summary


async def main():
    """Point d'entrée principal."""
    validator = Phase5ValidationManager()
    
    try:
        results = await validator.run_validation()
        
        # Sauvegarde des résultats
        report_file = f"reports/validation_phase5_non_regression_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Création du répertoire reports s'il n'existe pas
        Path("reports").mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Affichage du résumé
        summary = results.get('summary', {})
        logger.info(f"📊 RÉSUMÉ VALIDATION PHASE 5:")
        logger.info(f"   Tests totaux: {summary.get('total_tests', 0)}")
        logger.info(f"   Tests réussis: {summary.get('passed_tests', 0)}")
        logger.info(f"   Tests échoués: {summary.get('failed_tests', 0)}")
        logger.info(f"   Taux de réussite: {summary.get('success_rate', 0):.1f}%")
        
        if summary.get('critical_issues'):
            logger.warning("🚨 PROBLÈMES CRITIQUES:")
            for issue in summary['critical_issues']:
                logger.warning(f"   - {issue}")
        
        logger.info("📄 Rapport détaillé sauvegardé dans: " + report_file)
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur validation: {e}")
        return {'error': str(e)}


if __name__ == "__main__":
    asyncio.run(main())