#!/usr/bin/env python3
"""
Validation Rapide Phase 5 - Test de Non-Régression
=================================================

Test rapide pour vérifier l'état actuel du système et identifier les régressions.
"""

import requests
import json
import logging
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def test_current_interfaces():
    """Teste les interfaces actuellement disponibles."""
    results = {
        'timestamp': datetime.now().isoformat(),
        'interfaces_tested': {},
        'regression_detected': False,
        'summary': {}
    }
    
    # Test des ports courants
    ports_to_test = [3000, 3001, 8000, 8080, 5000]
    
    for port in ports_to_test:
        logger.info(f"🔍 Test port {port}")
        interface_result = test_interface_on_port(port)
        if interface_result['accessible']:
            results['interfaces_tested'][str(port)] = interface_result
            logger.info(f"✅ Interface trouvée sur port {port}")
    
    # Test des fonctionnalités de base
    logger.info("🧪 Test des fonctionnalités existantes")
    functionality_tests = test_basic_functionalities()
    results['functionality_tests'] = functionality_tests
    
    # Test des imports critiques
    logger.info("📦 Test des imports critiques")
    import_tests = test_critical_imports()
    results['import_tests'] = import_tests
    
    # Analyse des régressions
    results['regression_detected'] = analyze_regressions(results)
    results['summary'] = generate_quick_summary(results)
    
    return results

def test_interface_on_port(port):
    """Teste une interface sur un port donné."""
    result = {
        'port': port,
        'accessible': False,
        'status_endpoint': False,
        'examples_endpoint': False,
        'interface_type': 'unknown',
        'response_time': None
    }
    
    try:
        # Test de base - page d'accueil
        start_time = datetime.now()
        response = requests.get(f'http://localhost:{port}/', timeout=5)
        end_time = datetime.now()
        
        if response.status_code == 200:
            result['accessible'] = True
            result['response_time'] = (end_time - start_time).total_seconds()
            
            # Détection du type d'interface
            if 'Argumentation Analysis' in response.text:
                result['interface_type'] = 'flask_interface'
            elif 'React' in response.text:
                result['interface_type'] = 'react_interface'
            
            # Test endpoint /status
            try:
                status_response = requests.get(f'http://localhost:{port}/status', timeout=3)
                if status_response.status_code == 200:
                    result['status_endpoint'] = True
                    status_data = status_response.json()
                    result['status_data'] = status_data
            except:
                pass
            
            # Test endpoint /api/examples
            try:
                examples_response = requests.get(f'http://localhost:{port}/api/examples', timeout=3)
                if examples_response.status_code == 200:
                    result['examples_endpoint'] = True
                    examples_data = examples_response.json()
                    result['examples_count'] = len(examples_data.get('examples', []))
            except:
                pass
                
    except Exception as e:
        logger.debug(f"Port {port} non accessible: {e}")
    
    return result

def test_basic_functionalities():
    """Teste les fonctionnalités de base du système."""
    results = {
        'service_manager_import': False,
        'config_loading': False,
        'file_structure': False,
        'data_directories': False
    }
    
    # Test d'import ServiceManager
    try:
        from argumentation_analysis.orchestration.service_manager import ServiceManager
        results['service_manager_import'] = True
        logger.info("✅ ServiceManager importable")
    except Exception as e:
        logger.warning(f"❌ ServiceManager non importable: {e}")
    
    # Test de structure de fichiers
    try:
        project_root = Path(__file__).parent
        critical_dirs = ['interface_web', 'services', 'scripts', 'tests']
        
        existing_dirs = [d for d in critical_dirs if (project_root / d).exists()]
        results['file_structure'] = len(existing_dirs) >= 3
        results['existing_directories'] = existing_dirs
        
        if results['file_structure']:
            logger.info(f"✅ Structure de fichiers OK: {existing_dirs}")
        else:
            logger.warning(f"❌ Structure de fichiers incomplète: {existing_dirs}")
            
    except Exception as e:
        logger.error(f"Erreur test structure: {e}")
    
    # Test des répertoires de données
    try:
        data_dirs = ['data', 'results', 'logs']
        project_root = Path(__file__).parent
        
        existing_data_dirs = [d for d in data_dirs if (project_root / d).exists()]
        results['data_directories'] = len(existing_data_dirs) >= 1
        results['existing_data_dirs'] = existing_data_dirs
        
    except Exception as e:
        logger.error(f"Erreur test répertoires: {e}")
    
    return results

def test_critical_imports():
    """Teste les imports critiques pour détecter les régressions."""
    results = {
        'imports_successful': [],
        'imports_failed': [],
        'total_tested': 0,
        'success_rate': 0
    }
    
    critical_imports = [
        'argumentation_analysis',
        'argumentation_analysis.orchestration.service_manager',
        'flask',
        'requests',
        'json',
        'pathlib'
    ]
    
    for module_name in critical_imports:
        results['total_tested'] += 1
        try:
            __import__(module_name)
            results['imports_successful'].append(module_name)
            logger.debug(f"✅ Import réussi: {module_name}")
        except Exception as e:
            results['imports_failed'].append({'module': module_name, 'error': str(e)})
            logger.warning(f"❌ Import échoué: {module_name} - {e}")
    
    if results['total_tested'] > 0:
        results['success_rate'] = len(results['imports_successful']) / results['total_tested'] * 100
    
    return results

def analyze_regressions(results):
    """Analyse les résultats pour détecter des régressions."""
    regression_indicators = []
    
    # Vérification des interfaces accessibles
    accessible_interfaces = [
        data for data in results['interfaces_tested'].values() 
        if data['accessible']
    ]
    
    if len(accessible_interfaces) == 0:
        regression_indicators.append("Aucune interface accessible")
    
    # Vérification des imports critiques
    import_success_rate = results['import_tests']['success_rate']
    if import_success_rate < 80:
        regression_indicators.append(f"Taux d'import critique: {import_success_rate:.1f}%")
    
    # Vérification de la structure de fichiers
    if not results['functionality_tests']['file_structure']:
        regression_indicators.append("Structure de fichiers corrompue")
    
    # Vérification ServiceManager
    if not results['functionality_tests']['service_manager_import']:
        regression_indicators.append("ServiceManager non accessible")
    
    return len(regression_indicators) > 0

def generate_quick_summary(results):
    """Génère un résumé rapide de la validation."""
    summary = {
        'accessible_interfaces': len([
            data for data in results['interfaces_tested'].values() 
            if data['accessible']
        ]),
        'functional_endpoints': 0,
        'import_success_rate': results['import_tests']['success_rate'],
        'critical_issues': [],
        'status': 'unknown'
    }
    
    # Comptage des endpoints fonctionnels
    for interface_data in results['interfaces_tested'].values():
        if interface_data['status_endpoint']:
            summary['functional_endpoints'] += 1
    
    # Détermination du statut global
    if summary['accessible_interfaces'] >= 1 and summary['import_success_rate'] >= 90:
        summary['status'] = 'operational'
    elif summary['accessible_interfaces'] >= 1 and summary['import_success_rate'] >= 70:
        summary['status'] = 'degraded'
    else:
        summary['status'] = 'critical'
    
    # Identification des problèmes critiques
    if summary['accessible_interfaces'] == 0:
        summary['critical_issues'].append("Aucune interface accessible")
    
    if summary['import_success_rate'] < 70:
        summary['critical_issues'].append("Échecs d'import critiques")
    
    if not results['functionality_tests']['service_manager_import']:
        summary['critical_issues'].append("ServiceManager non accessible")
    
    return summary

def main():
    """Point d'entrée principal."""
    logger.info("🚀 DÉMARRAGE VALIDATION RAPIDE PHASE 5")
    
    try:
        results = test_current_interfaces()
        
        # Sauvegarde des résultats
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"reports/validation_phase5_quick_{timestamp}.json"
        
        Path("reports").mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Affichage du résumé
        summary = results['summary']
        logger.info("📊 RÉSUMÉ VALIDATION RAPIDE:")
        logger.info(f"   Interfaces accessibles: {summary['accessible_interfaces']}")
        logger.info(f"   Endpoints fonctionnels: {summary['functional_endpoints']}")
        logger.info(f"   Taux d'import: {summary['import_success_rate']:.1f}%")
        logger.info(f"   Statut global: {summary['status']}")
        
        if summary['critical_issues']:
            logger.warning("🚨 PROBLÈMES CRITIQUES:")
            for issue in summary['critical_issues']:
                logger.warning(f"   - {issue}")
        else:
            logger.info("✅ Aucun problème critique détecté")
        
        # Détail des interfaces trouvées
        logger.info("🔍 INTERFACES DÉTECTÉES:")
        for port, data in results['interfaces_tested'].items():
            status = "✅ Accessible" if data['accessible'] else "❌ Inaccessible"
            interface_type = data.get('interface_type', 'unknown')
            logger.info(f"   Port {port}: {status} ({interface_type})")
        
        logger.info(f"📄 Rapport sauvegardé: {report_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur validation: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    main()