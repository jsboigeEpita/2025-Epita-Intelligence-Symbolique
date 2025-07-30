#!/usr/bin/env python3
"""
Test de compatibilité pour les corrections d'imports semantic_kernel

Ce script teste que tous les imports problématiques ont été correctement
corrigés et que le module de compatibilité fonctionne.
"""

import sys
import traceback
from typing import List, Tuple

def test_import(module_path: str, description: str) -> Tuple[bool, str]:
    """
    Teste un import et retourne le résultat.
    
    Args:
        module_path: Chemin du module à importer
        description: Description du test
        
    Returns:
        Tuple (succès, message)
    """
    try:
        exec(f"import {module_path}")
        return True, f"[OK] {description}: Import réussi"
    except Exception as e:
        return False, f"[ERREUR] {description}: {str(e)}"

def test_specific_imports() -> List[Tuple[bool, str]]:
    """
    Teste des imports spécifiques depuis les modules corrigés.
    
    Returns:
        Liste des résultats de test
    """
    results = []
    
    # Test du module de compatibilité
    try:
        from argumentation_analysis.utils.semantic_kernel_compatibility import (
            Agent, ChatCompletionAgent, AgentGroupChat, 
            SelectionStrategy, TerminationStrategy
        )
        results.append((True, "[OK] Module de compatibilité: Toutes les classes importées"))
    except Exception as e:
        results.append((False, f"[ERREUR] Module de compatibilité: {str(e)}"))
    
    # Test des agents corrigés
    try:
        from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
        results.append((True, "[OK] WatsonLogicAssistant: Import réussi"))
    except Exception as e:
        results.append((False, f"[ERREUR] WatsonLogicAssistant: {str(e)}"))
    
    try:
        from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
        results.append((True, "[OK] SherlockEnqueteAgent: Import réussi"))
    except Exception as e:
        results.append((False, f"[ERREUR] SherlockEnqueteAgent: {str(e)}"))
    
    # Test des orchestrateurs corrigés
    try:
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        results.append((True, "[OK] CluedoExtendedOrchestrator: Import réussi"))
    except Exception as e:
        results.append((False, f"[ERREUR] CluedoExtendedOrchestrator: {str(e)}"))
    
    try:
        import argumentation_analysis.core.strategies
        results.append((True, "[OK] Strategies: Import réussi"))
    except Exception as e:
        results.append((False, f"[ERREUR] Strategies: {str(e)}"))
    
    return results

def test_semantic_kernel_version() -> Tuple[bool, str]:
    """
    Teste la version de semantic_kernel et vérifie les modules disponibles.
    
    Returns:
        Tuple (succès, message)
    """
    try:
        import semantic_kernel
        version = getattr(semantic_kernel, '__version__', 'Unknown')
        
        # Vérifier les modules disponibles
        available_modules = [attr for attr in dir(semantic_kernel) if not attr.startswith('_')]
        
        # Vérifier que le module agents n'est PAS disponible (comme attendu)
        agents_available = hasattr(semantic_kernel, 'agents')
        
        message = f"[OK] Semantic Kernel {version}\n"
        message += f"   Modules disponibles: {', '.join(available_modules)}\n"
        message += f"   Module 'agents' disponible: {agents_available} (attendu: False)"
        
        return True, message
        
    except Exception as e:
        return False, f"[ERREUR] Erreur lors de la vérification de semantic_kernel: {str(e)}"

def main():
    """Point d'entrée principal du test."""
    print("[TEST] COMPATIBILITE DES CORRECTIONS SEMANTIC_KERNEL")
    print("=" * 60)
    
    # Test de la version semantic_kernel
    print("\n[INFO] VERSION ET MODULES SEMANTIC_KERNEL:")
    success, message = test_semantic_kernel_version()
    print(message)
    
    # Test des imports spécifiques
    print("\n[INFO] TESTS D'IMPORTS SPECIFIQUES:")
    results = test_specific_imports()
    
    success_count = 0
    total_count = len(results)
    
    for success, message in results:
        print(message)
        if success:
            success_count += 1
    
    # Test des modules principaux
    print("\n[INFO] TESTS D'IMPORTS GENERAUX:")
    main_modules = [
        ("argumentation_analysis.utils.semantic_kernel_compatibility", "Module de compatibilité"),
        ("argumentation_analysis.orchestration.cluedo_extended_orchestrator", "Orchestrateur étendu"),
        ("argumentation_analysis.core.strategies", "Stratégies"),
        ("argumentation_analysis.agents.core.logic.watson_logic_assistant", "Agent Watson"),
        ("argumentation_analysis.agents.core.pm.sherlock_enquete_agent", "Agent Sherlock")
    ]
    
    for module_path, description in main_modules:
        success, message = test_import(module_path, description)
        print(message)
        if success:
            success_count += 1
        total_count += 1
    
    # Résumé final
    print("\n" + "=" * 60)
    print(f"[RESUME] {success_count}/{total_count} tests reussis")
    
    if success_count == total_count:
        print("[SUCCES] TOUS LES TESTS SONT PASSES - Corrections reussies!")
        return 0
    else:
        print(f"[ATTENTION] {total_count - success_count} test(s) echoue(s) - Verification necessaire")
        return 1

if __name__ == "__main__":
    sys.exit(main())