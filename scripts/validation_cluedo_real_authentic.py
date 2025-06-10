#!/usr/bin/env python3
"""
VRAIE validation des démos Cluedo et Einstein (Post-Investigation)
===============================================================

Suite à l'investigation qui a exposé la supercherie précédente, 
ce script effectue une validation RÉELLE avec des résultats authentiques.

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import scripts.core.auto_env  # Auto-activation environnement intelligent

import json
import time
from datetime import datetime
from pathlib import Path
import traceback
import logging

# Configuration logging pour capturer les vrais messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_authentic_traces_dir():
    """Crée le répertoire pour les traces authentiques"""
    traces_dir = Path(".temp/traces_cluedo_authentic")
    traces_dir.mkdir(parents=True, exist_ok=True)
    
    # Nettoyage des anciennes fausses traces
    for old_file in traces_dir.glob("*.json"):
        old_file.unlink()
        
    logger.info(f"Répertoire traces authentiques créé: {traces_dir}")
    return traces_dir

def diagnose_agent_communication():
    """Diagnostic des vrais problèmes de communication entre agents"""
    logger.info("=== DIAGNOSTIC AUTHENTIQUE DES AGENTS ===")
    
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "issues_found": [],
        "imports_status": {},
        "agent_files_status": {}
    }
    
    # Test des imports critiques
    try:
        from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
        diagnostics["imports_status"]["InformalAgent"] = "OK"
        logger.info("✓ InformalAgent import OK")
    except Exception as e:
        diagnostics["imports_status"]["InformalAgent"] = f"ERREUR: {str(e)}"
        diagnostics["issues_found"].append(f"Import InformalAgent échoué: {e}")
        logger.error(f"✗ InformalAgent import FAILED: {e}")
    
    try:
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        diagnostics["imports_status"]["CluedoExtendedOrchestrator"] = "OK"
        logger.info("✓ CluedoExtendedOrchestrator import OK")
    except Exception as e:
        diagnostics["imports_status"]["CluedoExtendedOrchestrator"] = f"ERREUR: {str(e)}"
        diagnostics["issues_found"].append(f"Import CluedoExtendedOrchestrator échoué: {e}")
        logger.error(f"✗ CluedoExtendedOrchestrator import FAILED: {e}")
    
    # Test semantic_kernel
    try:
        import semantic_kernel
        diagnostics["imports_status"]["semantic_kernel"] = "OK"
        logger.info("✓ semantic_kernel import OK")
    except Exception as e:
        diagnostics["imports_status"]["semantic_kernel"] = f"ERREUR: {str(e)}"
        diagnostics["issues_found"].append(f"Import semantic_kernel échoué: {e}")
        logger.error(f"✗ semantic_kernel import FAILED: {e}")
    
    return diagnostics

def attempt_real_cluedo_investigation():
    """Tentative d'enquête Cluedo RÉELLE avec capture de tous les échanges"""
    logger.info("=== TENTATIVE D'ENQUÊTE CLUEDO RÉELLE ===")
    
    investigation_log = {
        "timestamp": datetime.now().isoformat(),
        "status": "STARTED",
        "messages_exchanged": 0,
        "agents_communications": [],
        "solution_found": None,
        "errors": [],
        "real_traces": []
    }
    
    try:
        # Import de l'orchestrateur
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        
        # Configuration d'un cas de test simple
        test_case = {
            "characters": ["Colonel Mustard", "Miss Scarlet", "Professor Plum"],
            "weapons": ["Candlestick", "Knife", "Revolver"],
            "rooms": ["Library", "Kitchen", "Study"],
            "solution": {
                "character": "Colonel Mustard",
                "weapon": "Candlestick", 
                "room": "Library"
            }
        }
        
        logger.info(f"Cas de test configuré: {test_case}")
        investigation_log["test_case"] = test_case
        
        # Création de l'orchestrateur avec surveillance des communications
        orchestrator = CluedoExtendedOrchestrator()
        logger.info("Orchestrateur Cluedo créé")
        
        # Tentative de lancement d'une enquête RÉELLE
        logger.info("Lancement enquête avec surveillance des communications...")
        
        start_time = time.time()
        result = orchestrator.run_investigation(test_case)
        end_time = time.time()
        
        investigation_log["execution_time"] = end_time - start_time
        investigation_log["status"] = "COMPLETED"
        investigation_log["solution_found"] = result
        
        # Capture des vraies communications (si elles existent)
        if hasattr(orchestrator, 'conversation_history'):
            investigation_log["messages_exchanged"] = len(orchestrator.conversation_history)
            investigation_log["agents_communications"] = orchestrator.conversation_history
            logger.info(f"Messages réels capturés: {len(orchestrator.conversation_history)}")
        else:
            investigation_log["messages_exchanged"] = 0
            investigation_log["issues_found"] = ["Aucune trace de conversation_history dans l'orchestrateur"]
            logger.warning("Aucune trace de conversation_history trouvée")
        
        if result and result != {}:
            logger.info(f"✓ Solution trouvée: {result}")
        else:
            logger.warning("✗ Solution nulle ou vide")
            investigation_log["errors"].append("Solution nulle ou vide")
        
    except Exception as e:
        investigation_log["status"] = "FAILED"
        investigation_log["errors"].append(f"Exception: {str(e)}")
        investigation_log["traceback"] = traceback.format_exc()
        logger.error(f"✗ Enquête échouée: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    return investigation_log

def main():
    """Fonction principale de validation authentique"""
    print("=" * 80)
    print("VRAIE VALIDATION DES DÉMOS CLUEDO ET EINSTEIN")
    print("(Post-Investigation - Résultats Authentiques)")
    print("=" * 80)
    
    # Création du répertoire de traces authentiques
    traces_dir = create_authentic_traces_dir()
    
    # Diagnostic des agents
    print("\n1. DIAGNOSTIC DES AGENTS...")
    diagnostics = diagnose_agent_communication()
    
    # Sauvegarde du diagnostic
    diag_file = traces_dir / "diagnostic_authentique.json"
    with open(diag_file, 'w', encoding='utf-8') as f:
        json.dump(diagnostics, f, indent=2, ensure_ascii=False)
    
    print(f"   Diagnostic sauvegardé: {diag_file}")
    
    if diagnostics["issues_found"]:
        print("   ⚠️  PROBLÈMES DÉTECTÉS:")
        for issue in diagnostics["issues_found"]:
            print(f"      - {issue}")
    else:
        print("   ✓ Imports OK")
    
    # Tentative d'enquête réelle
    print("\n2. TENTATIVE D'ENQUÊTE CLUEDO RÉELLE...")
    investigation = attempt_real_cluedo_investigation()
    
    # Sauvegarde de l'enquête
    investigation_file = traces_dir / "investigation_authentique.json"
    with open(investigation_file, 'w', encoding='utf-8') as f:
        json.dump(investigation, f, indent=2, ensure_ascii=False)
    
    print(f"   Investigation sauvegardée: {investigation_file}")
    
    # Rapport final
    print("\n3. RAPPORT FINAL AUTHENTIQUE:")
    print(f"   Status: {investigation['status']}")
    print(f"   Messages échangés: {investigation['messages_exchanged']}")
    print(f"   Solution trouvée: {investigation.get('solution_found', 'None')}")
    
    if investigation["errors"]:
        print("   🚨 ERREURS DÉTECTÉES:")
        for error in investigation["errors"]:
            print(f"      - {error}")
    
    # Calcul du taux de succès RÉEL
    success_rate = 0.0
    if investigation["status"] == "COMPLETED" and investigation["messages_exchanged"] > 0:
        if investigation.get("solution_found") and investigation["solution_found"] != {}:
            success_rate = 100.0
    
    print(f"   Taux de succès RÉEL: {success_rate}%")
    
    # Recommandations
    print("\n4. RECOMMANDATIONS:")
    if success_rate == 0.0:
        print("   📋 ACTIONS CORRECTIVES NÉCESSAIRES:")
        print("      - Examiner le code des agents pour les blocages LLM")
        print("      - Vérifier la configuration semantic_kernel")
        print("      - Corriger les imports manquants")
        print("      - Tester les appels LLM individuellement")
    else:
        print("   ✅ VALIDATION RÉUSSIE - Système opérationnel")
    
    print(f"\n📁 Traces authentiques disponibles dans: {traces_dir}")
    return success_rate > 0.0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)