#!/usr/bin/env python3
"""
Script de diagnostic pour identifier le cycle d'import BaseLogicAgent.
"""

import sys
import traceback

def test_import_baselogicagent():
    """Test direct d'import BaseLogicAgent."""
    print("=== TEST IMPORT DIRECT BaseLogicAgent ===")
    try:
        from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
        print("OK Import BaseLogicAgent réussi")
        return True
    except Exception as e:
        print(f"ERREUR import BaseLogicAgent: {e}")
        traceback.print_exc()
        return False

def test_import_belief_set():
    """Test import BeliefSet."""
    print("\n=== TEST IMPORT BeliefSet ===")
    try:
        from argumentation_analysis.agents.core.logic.belief_set import BeliefSet
        print("OK Import BeliefSet réussi")
        return True
    except Exception as e:
        print(f"ERREUR import BeliefSet: {e}")
        traceback.print_exc()
        return False

def test_import_fol_agent():
    """Test import FOLLogicAgent."""
    print("\n=== TEST IMPORT FOLLogicAgent ===")
    try:
        from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
        print("OK Import FOLLogicAgent réussi")
        return True
    except Exception as e:
        print(f"ERREUR import FOLLogicAgent: {e}")
        traceback.print_exc()
        return False

def test_import_logic_module():
    """Test import du module logic complet."""
    print("\n=== TEST IMPORT MODULE LOGIC ===")
    try:
        import argumentation_analysis.agents.core.logic
        print("OK Import module logic réussi")
        return True
    except Exception as e:
        print(f"ERREUR import module logic: {e}")
        traceback.print_exc()
        return False

def show_import_chain():
    """Affiche la chaîne d'imports pour comprendre le cycle."""
    print("\n=== ANALYSE CHAÎNE D'IMPORTS ===")
    
    modules_to_check = [
        'argumentation_analysis.agents.core.abc.agent_bases',
        'argumentation_analysis.agents.core.logic.belief_set',
        'argumentation_analysis.agents.core.logic.fol_logic_agent',
        'argumentation_analysis.agents.core.logic'
    ]
    
    for module_name in modules_to_check:
        if module_name in sys.modules:
            print(f"OK Module {module_name} déjà chargé")
        else:
            print(f"NON Module {module_name} NON chargé")

def main():
    """Diagnostic principal."""
    print("DIAGNOSTIC CYCLE D'IMPORT BaseLogicAgent")
    print("=" * 50)
    
    # Vérifier état initial
    show_import_chain()
    
    # Tests progressifs
    success_count = 0
    tests = [
        test_import_belief_set,
        test_import_baselogicagent,
        test_import_fol_agent,
        test_import_logic_module
    ]
    
    for test in tests:
        if test():
            success_count += 1
        print("-" * 30)
    
    print(f"\nRESULTATS: {success_count}/{len(tests)} tests réussis")
    
    # État final
    print("\n=== ÉTAT FINAL MODULES ===")
    show_import_chain()

if __name__ == "__main__":
    main()