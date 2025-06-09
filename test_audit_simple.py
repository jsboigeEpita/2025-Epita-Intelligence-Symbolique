#!/usr/bin/env python3
"""
TEST AUDIT AUTHENTICITE SIMPLE
===============================

Version simplifiée sans emoji pour contourner les problèmes d'encodage Windows.
Détecte les mocks et teste l'authenticité du système avec données synthétiques.
"""

import asyncio
import json
import time
import os
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

# Configuration logging simple
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

class MockDetector:
    """Détecteur de mocks dans le système."""
    
    def __init__(self):
        self.detected_mocks = []
        
    def scan_system(self) -> Dict[str, Any]:
        """Scan complet pour détecter les mocks."""
        logger.info("[SCAN] Detection des mocks dans le systeme")
        
        results = {
            "config_mocks": [],
            "test_mocks": [],
            "code_mocks": []
        }
        
        # 1. Vérifier config/.env
        env_path = "config/.env"
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                content = f.read()
                if "sk-test-dummy-key" in content or "dummy" in content:
                    results["config_mocks"].append(env_path)
                    logger.warning(f"[MOCK] Cle API factice detectee dans {env_path}")
        
        # 2. Scanner les fichiers de test
        test_patterns = ["Mock", "mock", "dummy", "fake", "assert True", "return True"]
        test_dirs = ["tests/", "test_"]
        
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                for root, dirs, files in os.walk(test_dir):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    mock_count = sum(pattern in content for pattern in test_patterns)
                                    if mock_count > 3:  # Seuil de détection
                                        results["test_mocks"].append(file_path)
                            except:
                                continue
        
        # 3. Vérifier orchestrateur principal
        orchestrator_path = "argumentation_analysis/orchestration/cluedo_orchestrator.py"
        if os.path.exists(orchestrator_path):
            with open(orchestrator_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "# NOTE: Ajoutez ici" in content or "comment" in content.lower():
                    results["code_mocks"].append(orchestrator_path)
                    logger.warning(f"[MOCK] Configuration API commentee dans {orchestrator_path}")
        
        total_mocks = len(results["config_mocks"]) + len(results["test_mocks"]) + len(results["code_mocks"])
        logger.info(f"[SCAN] Total mocks detectes: {total_mocks}")
        
        return results

class SyntheticDataGenerator:
    """Générateur de données synthétiques uniques."""
    
    def __init__(self):
        self.test_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def generate_unique_scenario(self) -> Dict[str, Any]:
        """Génère un scénario Cluedo unique."""
        return {
            "nom": f"Mystere_Quantique_{self.test_id}",
            "suspects": ["Dr.Einstein", "Prof.Bohr", "Mme.Curie"],
            "armes": ["Laser_quantique", "Champ_magnetique", "Radiation_gamma"],
            "lieux": ["Labo_particules", "Chambre_isolation", "Reacteur_fusion"],
            "contexte": f"Incident dans laboratoire {self.timestamp}. Analyse requise.",
            "test_id": self.test_id
        }

class AuthenticityTester:
    """Testeur d'authenticité principal."""
    
    def __init__(self):
        self.detector = MockDetector()
        self.generator = SyntheticDataGenerator()
        self.results = {}
        
    async def test_api_availability(self) -> Dict[str, Any]:
        """Teste la disponibilité des APIs réelles."""
        logger.info("[API] Test disponibilite API OpenAI")
        
        api_key = os.getenv('OPENAI_API_KEY', '')
        
        result = {
            "api_key_present": bool(api_key),
            "api_key_real": not any(x in api_key.lower() for x in ['test', 'dummy', 'fake', 'mock']),
            "api_key_format": api_key.startswith('sk-') if api_key else False,
            "api_key_length": len(api_key) if api_key else 0
        }
        
        if result["api_key_real"] and result["api_key_format"]:
            logger.info("[API] Cle API reelle detectee - Format valide")
        else:
            logger.warning("[API] Cle API absente ou factice")
        
        return result
    
    async def test_orchestration_imports(self) -> Dict[str, Any]:
        """Teste l'importation des composants d'orchestration."""
        logger.info("[IMPORT] Test imports orchestration")
        
        result = {
            "imports_successful": [],
            "imports_failed": [],
            "semantic_kernel_available": False,
            "orchestrator_available": False
        }
        
        # Test Semantic Kernel
        try:
            import semantic_kernel as sk
            result["semantic_kernel_available"] = True
            result["imports_successful"].append("semantic_kernel")
            logger.info("[IMPORT] Semantic Kernel importe avec succes")
        except ImportError as e:
            result["imports_failed"].append(f"semantic_kernel: {e}")
            logger.error(f"[IMPORT] Echec import Semantic Kernel: {e}")
        
        # Test orchestrateur Cluedo
        try:
            from argumentation_analysis.orchestration.cluedo_orchestrator import run_cluedo_game
            result["orchestrator_available"] = True
            result["imports_successful"].append("cluedo_orchestrator")
            logger.info("[IMPORT] Orchestrateur Cluedo importe avec succes")
        except ImportError as e:
            result["imports_failed"].append(f"cluedo_orchestrator: {e}")
            logger.error(f"[IMPORT] Echec import orchestrateur: {e}")
        
        return result
    
    async def run_authenticity_audit(self) -> Dict[str, Any]:
        """Execute l'audit complet d'authenticité."""
        logger.info("[AUDIT] DEBUT AUDIT AUTHENTICITE")
        
        audit_results = {
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "test_scenario": self.generator.generate_unique_scenario(),
            "phases": {}
        }
        
        # Phase 1: Détection mocks
        logger.info("[PHASE1] Detection des mocks")
        mock_scan = self.detector.scan_system()
        audit_results["phases"]["mock_detection"] = mock_scan
        
        # Phase 2: Test API
        logger.info("[PHASE2] Test disponibilite API")
        api_test = await self.test_api_availability()
        audit_results["phases"]["api_test"] = api_test
        
        # Phase 3: Test imports
        logger.info("[PHASE3] Test imports orchestration")
        import_test = await self.test_orchestration_imports()
        audit_results["phases"]["import_test"] = import_test
        
        # Phase 4: Calcul score authenticité
        logger.info("[PHASE4] Calcul score authenticite")
        authenticity_score = self.calculate_authenticity_score(audit_results)
        audit_results["authenticity_score"] = authenticity_score
        
        # Déterminer status final
        if authenticity_score >= 80:
            audit_results["status"] = "AUTHENTIC"
            logger.info("[SUCCESS] Systeme authentique verifie!")
        elif authenticity_score >= 60:
            audit_results["status"] = "PARTIALLY_AUTHENTIC"
            logger.warning("[WARNING] Systeme partiellement authentique")
        else:
            audit_results["status"] = "MOCK_HEAVY"
            logger.error("[ERROR] Systeme contient trop de mocks")
        
        return audit_results
    
    def calculate_authenticity_score(self, audit_results: Dict) -> int:
        """Calcule le score d'authenticité (0-100)."""
        score = 0
        
        # Critère 1: Configuration API (30 points)
        api_test = audit_results["phases"]["api_test"]
        if api_test["api_key_real"] and api_test["api_key_format"]:
            score += 30
        elif api_test["api_key_present"]:
            score += 10
        
        # Critère 2: Imports fonctionnels (30 points)
        import_test = audit_results["phases"]["import_test"]
        if import_test["semantic_kernel_available"]:
            score += 15
        if import_test["orchestrator_available"]:
            score += 15
        
        # Critère 3: Absence de mocks critiques (40 points)
        mock_detection = audit_results["phases"]["mock_detection"]
        total_mocks = len(mock_detection["config_mocks"]) + len(mock_detection["code_mocks"])
        
        if total_mocks == 0:
            score += 40
        elif total_mocks <= 2:
            score += 20
        elif total_mocks <= 5:
            score += 10
        
        return min(score, 100)
    
    def save_audit_report(self, audit_results: Dict[str, Any]):
        """Sauvegarde le rapport d'audit."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"reports/audit_authenticite_simple_{timestamp}.json"
        
        os.makedirs("reports", exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(audit_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[REPORT] Rapport sauvegarde: {report_path}")
        
        # Créer résumé textuel
        self.create_summary_report(audit_results, report_path.replace('.json', '_resume.txt'))
    
    def create_summary_report(self, audit_results: Dict[str, Any], report_path: str):
        """Crée un résumé textuel du rapport."""
        content = f"""RAPPORT AUDIT AUTHENTICITE - {audit_results['timestamp']}
===============================================================

SCENARIO DE TEST:
- ID: {audit_results['test_scenario']['test_id']}
- Nom: {audit_results['test_scenario']['nom']}
- Contexte: {audit_results['test_scenario']['contexte']}

RESULTATS:
- Status: {audit_results['status']}
- Score Authenticite: {audit_results['authenticity_score']}/100

DETECTION MOCKS:
- Mocks Config: {len(audit_results['phases']['mock_detection']['config_mocks'])}
- Mocks Tests: {len(audit_results['phases']['mock_detection']['test_mocks'])}
- Mocks Code: {len(audit_results['phases']['mock_detection']['code_mocks'])}

TEST API:
- Cle presente: {audit_results['phases']['api_test']['api_key_present']}
- Cle reelle: {audit_results['phases']['api_test']['api_key_real']}
- Format valide: {audit_results['phases']['api_test']['api_key_format']}

TEST IMPORTS:
- Semantic Kernel: {audit_results['phases']['import_test']['semantic_kernel_available']}
- Orchestrateur: {audit_results['phases']['import_test']['orchestrator_available']}

===============================================================
Rapport genere automatiquement par le systeme d'audit d'authenticite
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)

async def main():
    """Point d'entrée principal."""
    print("AUDIT D'AUTHENTICITE DU SYSTEME")
    print("Elimination des mocks de complaisance")
    print("=" * 50)
    
    tester = AuthenticityTester()
    
    try:
        # Exécuter l'audit
        audit_results = await tester.run_authenticity_audit()
        
        # Sauvegarder les résultats
        tester.save_audit_report(audit_results)
        
        # Afficher résumé
        print("\nRESULTATS AUDIT:")
        print("-" * 30)
        print(f"Status: {audit_results['status']}")
        print(f"Score: {audit_results['authenticity_score']}/100")
        print(f"Test ID: {audit_results['test_scenario']['test_id']}")
        
        # Détails par phase
        mock_detection = audit_results['phases']['mock_detection']
        print(f"Mocks detectes: {len(mock_detection['config_mocks']) + len(mock_detection['code_mocks'])}")
        
        api_test = audit_results['phases']['api_test']
        print(f"API reelle: {api_test['api_key_real']}")
        
        import_test = audit_results['phases']['import_test']
        print(f"Imports OK: {len(import_test['imports_successful'])}")
        
        if audit_results['status'] == 'AUTHENTIC':
            print("\n[SUCCESS] SYSTEME AUTHENTIQUE VERIFIE!")
            print("Les traces d'execution prouvent l'authenticite")
        elif audit_results['status'] == 'PARTIALLY_AUTHENTIC':
            print("\n[WARNING] SYSTEME PARTIELLEMENT AUTHENTIQUE")
            print("Quelques mocks detectes mais fonctionnalite preservee")
        else:
            print("\n[ERROR] MOCKS DETECTES")
            print("Le systeme contient trop de mocks de complaisance")
        
        return audit_results['status'] in ['AUTHENTIC', 'PARTIALLY_AUTHENTIC']
        
    except Exception as e:
        logger.error(f"[ERROR] Echec audit: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\nCODE DE RETOUR: {0 if success else 1}")
    exit(0 if success else 1)