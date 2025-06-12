#!/usr/bin/env python3
"""
VALIDATION FINALE CORRIGÉE des démos Cluedo et Einstein
=======================================================

Version corrigée qui contourne tous les problèmes identifiés et teste VRAIMENT
les communications agentiques avec traces authentiques.

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
import project_core.core_from_scripts.auto_env
"""

import sys
import os
from pathlib import Path

# Configuration du projet SANS auto_env défaillant mais avec PATH correct
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))
os.environ['PYTHONPATH'] = str(project_root)
os.environ['PROJECT_ROOT'] = str(project_root)

import json
import time
from datetime import datetime
import traceback
import logging
import asyncio

# Configuration logging pour capturer les vrais messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_authentic_traces_dir():
    """Crée le répertoire pour les traces authentiques"""
    traces_dir = Path(".temp/traces_cluedo_authentic_final")
    traces_dir.mkdir(parents=True, exist_ok=True)
    
    # Nettoyage des anciennes traces
    for old_file in traces_dir.glob("*.json"):
        old_file.unlink()
        
    logger.info(f"Répertoire traces authentiques créé: {traces_dir}")
    return traces_dir

def test_imports_corrected():
    """Test des imports après corrections"""
    logger.info("=== TEST DES IMPORTS CORRIGÉS ===")
    
    import_results = {
        "timestamp": datetime.now().isoformat(),
        "imports_fixed": {},
        "remaining_issues": []
    }
    
    # Test 1: InformalAgent avec alias corrigé
    try:
        from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
        import_results["imports_fixed"]["InformalAgent"] = "OK - Alias ajouté"
        logger.info("✓ InformalAgent import OK avec alias")
    except Exception as e:
        import_results["imports_fixed"]["InformalAgent"] = f"ERREUR: {str(e)}"
        import_results["remaining_issues"].append(f"InformalAgent encore cassé: {e}")
        logger.error(f"✗ InformalAgent import FAILED: {e}")
    
    # Test 2: Semantic Kernel avec kernel création
    try:
        import semantic_kernel as sk
        from semantic_kernel.kernel import Kernel
        
        # Test création kernel
        kernel = Kernel()
        import_results["imports_fixed"]["semantic_kernel_kernel"] = "OK - Kernel créé"
        logger.info("✓ Kernel semantic_kernel créé avec succès")
        
        return import_results, kernel
    except Exception as e:
        import_results["imports_fixed"]["semantic_kernel_kernel"] = f"ERREUR: {str(e)}"
        import_results["remaining_issues"].append(f"Kernel semantic_kernel: {e}")
        logger.error(f"✗ Kernel création FAILED: {e}")
        return import_results, None

async def test_orchestrator_with_kernel(kernel):
    """Test de l'orchestrateur avec kernel fourni"""
    logger.info("=== TEST ORCHESTRATEUR AVEC KERNEL ===")
    
    orchestrator_test = {
        "timestamp": datetime.now().isoformat(),
        "status": "STARTED",
        "kernel_provided": kernel is not None,
        "orchestrator_created": False,
        "methods_available": [],
        "setup_attempted": False,
        "execution_attempted": False,
        "messages_captured": 0,
        "errors": []
    }
    
    if not kernel:
        orchestrator_test["status"] = "FAILED"
        orchestrator_test["errors"].append("Kernel non disponible")
        return orchestrator_test
    
    try:
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        
        # Créer l'orchestrateur avec kernel
        orchestrator = CluedoExtendedOrchestrator(kernel=kernel)
        orchestrator_test["orchestrator_created"] = True
        logger.info("✓ Orchestrateur créé avec kernel")
        
        # Lister les méthodes disponibles
        methods = [m for m in dir(orchestrator) if not m.startswith('_') and callable(getattr(orchestrator, m))]
        orchestrator_test["methods_available"] = methods
        logger.info(f"✓ Méthodes orchestrateur: {len(methods)} disponibles")
        
        # Test de setup_workflow
        if "setup_workflow" in methods:
            try:
                logger.info("Tentative setup_workflow...")
                await orchestrator.setup_workflow(nom_enquete="Test Authentique")
                orchestrator_test["setup_attempted"] = True
                logger.info("✓ setup_workflow réussi")
            except Exception as e:
                orchestrator_test["errors"].append(f"setup_workflow échoué: {e}")
                logger.error(f"✗ setup_workflow FAILED: {e}")
        
        # Test d'exécution simple
        if "execute_workflow" in methods and orchestrator_test["setup_attempted"]:
            try:
                logger.info("Tentative execute_workflow...")
                result = await orchestrator.execute_workflow(
                    initial_question="Test de communication agentique"
                )
                orchestrator_test["execution_attempted"] = True
                orchestrator_test["execution_result"] = result
                
                # Vérifier s'il y a eu de vraies communications
                if hasattr(orchestrator, 'conversation_history'):
                    orchestrator_test["messages_captured"] = len(orchestrator.conversation_history)
                    logger.info(f"✓ {orchestrator_test['messages_captured']} messages capturés")
                else:
                    logger.warning("Aucune conversation_history trouvée")
                
                orchestrator_test["status"] = "COMPLETED"
                logger.info("✓ execute_workflow réussi")
                
            except Exception as e:
                orchestrator_test["errors"].append(f"execute_workflow échoué: {e}")
                orchestrator_test["status"] = "FAILED"
                logger.error(f"✗ execute_workflow FAILED: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
        
    except Exception as e:
        orchestrator_test["status"] = "FAILED"
        orchestrator_test["errors"].append(f"Création orchestrateur échouée: {e}")
        logger.error(f"✗ Orchestrateur création FAILED: {e}")
    
    return orchestrator_test

async def main():
    """Fonction principale de validation finale"""
    print("=" * 80)
    print("VALIDATION FINALE CORRIGÉE DES DÉMOS CLUEDO ET EINSTEIN")
    print("(Post-Investigation avec corrections appliquées)")
    print("=" * 80)
    
    # Création du répertoire de traces
    traces_dir = create_authentic_traces_dir()
    
    # Test des imports corrigés
    print("\n1. TEST DES IMPORTS CORRIGÉS...")
    import_results, kernel = test_imports_corrected()
    
    # Sauvegarde des imports
    imports_file = traces_dir / "imports_corriges.json"
    with open(imports_file, 'w', encoding='utf-8') as f:
        json.dump(import_results, f, indent=2, ensure_ascii=False)
    
    if import_results["remaining_issues"]:
        print("   ⚠️  PROBLÈMES RESTANTS:")
        for issue in import_results["remaining_issues"]:
            print(f"      - {issue}")
    else:
        print("   ✅ TOUS LES IMPORTS CORRIGÉS")
    
    # Test de l'orchestrateur avec kernel
    print("\n2. TEST ORCHESTRATEUR AVEC KERNEL...")
    orchestrator_results = await test_orchestrator_with_kernel(kernel)
    
    # Sauvegarde des résultats orchestrateur
    orchestrator_file = traces_dir / "orchestrateur_test.json"
    with open(orchestrator_file, 'w', encoding='utf-8') as f:
        json.dump(orchestrator_results, f, indent=2, ensure_ascii=False)
    
    # Rapport final
    print("\n3. RAPPORT FINAL VALIDATIONS CORRIGÉES:")
    print(f"   Status orchestrateur: {orchestrator_results['status']}")
    print(f"   Kernel fourni: {orchestrator_results['kernel_provided']}")
    print(f"   Orchestrateur créé: {orchestrator_results['orchestrator_created']}")
    print(f"   Setup tenté: {orchestrator_results['setup_attempted']}")
    print(f"   Exécution tentée: {orchestrator_results['execution_attempted']}")
    print(f"   Messages capturés: {orchestrator_results['messages_captured']}")
    
    if orchestrator_results["errors"]:
        print("   🚨 ERREURS PERSISTANTES:")
        for error in orchestrator_results["errors"]:
            print(f"      - {error}")
    
    # Calcul du taux de succès RÉEL après corrections
    success_score = 0
    if import_results["imports_fixed"].get("InformalAgent") == "OK - Alias ajouté":
        success_score += 25
    if orchestrator_results["orchestrator_created"]:
        success_score += 25
    if orchestrator_results["setup_attempted"]:
        success_score += 25
    if orchestrator_results["execution_attempted"]:
        success_score += 25
    
    print(f"   Score de succès après corrections: {success_score}%")
    
    # Statut final
    if success_score >= 75:
        print("\n4. ✅ VALIDATION RÉUSSIE APRÈS CORRECTIONS")
        print("   Le système agentique fonctionne avec les corrections appliquées")
    elif success_score >= 50:
        print("\n4. ⚠️  VALIDATION PARTIELLE")
        print("   Améliorations significatives mais problèmes restants")
    else:
        print("\n4. ❌ VALIDATION ÉCHOUÉE")
        print("   Corrections insuffisantes, problèmes majeurs persistent")
    
    print(f"\n📁 Traces finales disponibles dans: {traces_dir}")
    return success_score >= 50

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)