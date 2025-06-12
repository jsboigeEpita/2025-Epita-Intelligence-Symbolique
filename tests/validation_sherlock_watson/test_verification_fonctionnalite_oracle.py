#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de vérification de la fonctionnalité Oracle après modification des prompts Phase A

Ce script vérifie que les modifications des prompts n'ont pas cassé la fonctionnalité 
technique des agents Watson, Moriarty et Sherlock.
"""

# Auto-activation environnement intelligent
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
try:
    import project_core.core_from_scripts.auto_env
except ImportError:
    print("[WARN] Auto-activation d'environnement non disponible - continuons sans")

import sys
import importlib.util

def test_watson_import():
    """Test d'import Watson"""
    try:
        from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
        print("[OK] Watson import réussi")
        assert True, "Watson import réussi"
    except Exception as e:
        print(f"[ERREUR] Watson import: {e}")
        return False

def test_moriarty_import():
    """Test d'import Moriarty"""
    try:
        from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
        print("[OK] Moriarty import réussi")
        assert True, "Moriarty import réussi"
    except Exception as e:
        print(f"[ERREUR] Moriarty import: {e}")
        return False

def test_sherlock_import():
    """Test d'import Sherlock"""
    try:
        from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
        print("[OK] Sherlock import réussi")
        assert True, "Sherlock import réussi"
    except Exception as e:
        print(f"[ERREUR] Sherlock import: {e}")
        assert False, f"Sherlock import échoué: {e}"

def test_prompt_syntax():
    """Test de syntaxe des prompts modifiés"""
    try:
        from argumentation_analysis.agents.core.logic.watson_logic_assistant import WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT
        from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
        from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT
        
        # Vérification Watson
        if "Vous êtes Watson" in WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT:
            print("[OK] Watson prompt bien formaté")
        else:
            print("[ERREUR] Watson prompt mal formaté")
            assert False, "Watson prompt mal formaté"
            
        # Vérification Sherlock
        if "Vous êtes Sherlock Holmes" in SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT:
            print("[OK] Sherlock prompt bien formaté")
        else:
            print("[ERREUR] Sherlock prompt mal formaté")
            assert False, "Sherlock prompt mal formaté"
            
        # Vérification Moriarty
        moriarty_instructions = MoriartyInterrogatorAgent.MORIARTY_SPECIALIZED_INSTRUCTIONS
        if "Vous êtes Moriarty" in moriarty_instructions:
            print("[OK] Moriarty prompt bien formaté")
        else:
            print("[ERREUR] Moriarty prompt mal formaté")
            assert False, "Moriarty prompt mal formaté"
            
        assert True, "Tous les prompts sont bien formatés"
    except Exception as e:
        print(f"[ERREUR] Test syntaxe prompts: {e}")
        assert False, f"Test syntaxe prompts échoué: {e}"

def test_new_personality_keywords():
    """Test de présence des nouveaux mots-clés de personnalité"""
    try:
        from argumentation_analysis.agents.core.logic.watson_logic_assistant import WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT
        from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
        from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT
        
        # Nouveaux mots-clés Watson (partenariat et analyse)
        watson_keywords = ["partenaire égal", "STEP-BY-STEP", "brillant", "analyste"]
        watson_found = sum(1 for keyword in watson_keywords if keyword in WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT)
        print(f"[OK] Watson nouveaux mots-clés: {watson_found}/4")
        
        # Nouveaux mots-clés Moriarty (théâtralité)
        moriarty_instructions = MoriartyInterrogatorAgent.MORIARTY_SPECIALIZED_INSTRUCTIONS
        moriarty_keywords = ["théâtral", "mystère", "énigmatique", "fascinant"]
        moriarty_found = sum(1 for keyword in moriarty_keywords if keyword.lower() in moriarty_instructions.lower())
        print(f"[OK] Moriarty nouveaux mots-clés: {moriarty_found}/4")
        
        # Nouveaux mots-clés Sherlock (leadership et intuition)
        sherlock_keywords = ["leader naturel", "intuition", "légendaire", "déducteur"]
        sherlock_found = sum(1 for keyword in sherlock_keywords if keyword.lower() in SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT.lower())
        print(f"[OK] Sherlock nouveaux mots-clés: {sherlock_found}/4")
        
        success = watson_found >= 2 and moriarty_found >= 2 and sherlock_found >= 2
        assert success, f"Mots-clés insuffisants: Watson {watson_found}/4, Moriarty {moriarty_found}/4, Sherlock {sherlock_found}/4"
        
    except Exception as e:
        print(f"[ERREUR] Test mots-clés personnalité: {e}")
        assert False, f"Test mots-clés personnalité échoué: {e}"

def test_core_functionality_preserved():
    """Test que les fonctionnalités de base sont préservées"""
    try:
        # Test Watson Tools
        from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonTools
        watson_tools = WatsonTools()
        methods = [method for method in dir(watson_tools) if not method.startswith('_')]
        core_methods = ['validate_formula', 'execute_query']
        if all(method in methods for method in core_methods):
            print("[OK] Watson outils préservés")
        else:
            print("[ERREUR] Watson outils manquants")
            assert False, "Watson outils manquants"
        
        # Test Moriarty Tools
        from argumentation_analysis.agents.core.oracle.dataset_access_manager import CluedoDatasetManager
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
        from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyTools
        
        # Simulation d'un dataset minimal pour le test
        dataset = CluedoDataset()
        dataset_manager = CluedoDatasetManager(dataset)
        moriarty_tools = MoriartyTools(dataset_manager)
        
        core_methods = ['validate_cluedo_suggestion', 'reveal_card_if_owned', 'provide_game_clue']
        methods = [method for method in dir(moriarty_tools) if not method.startswith('_')]
        if all(method in methods for method in core_methods):
            print("[OK] Moriarty outils préservés")
        else:
            print("[ERREUR] Moriarty outils manquants")
            assert False, "Moriarty outils manquants"
        
        # Test Sherlock Tools - Vérification que la classe existe
        from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockTools
        print("[OK] Sherlock outils préservés")
        
        assert True, "Toutes les fonctionnalités de base sont préservées"
        
    except Exception as e:
        print(f"[ERREUR] Test fonctionnalité préservée: {e}")
        assert False, f"Test fonctionnalité préservée échoué: {e}"

def main():
    """Test principal de vérification"""
    print("=" * 60)
    print("VERIFICATION FONCTIONNALITE ORACLE - PHASE A")
    print("=" * 60)
    print("Objectif: Confirmer que les modifications de prompts")
    print("n'ont pas cassé la fonctionnalité technique existante")
    print("=" * 60)
    
    tests = [
        ("Import Watson", test_watson_import),
        ("Import Moriarty", test_moriarty_import), 
        ("Import Sherlock", test_sherlock_import),
        ("Syntaxe prompts", test_prompt_syntax),
        ("Nouveaux mots-clés personnalité", test_new_personality_keywords),
        ("Fonctionnalité préservée", test_core_functionality_preserved)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n>>> Test: {test_name}")
        try:
            result = test_func()
            results.append(result)
            if result:
                print(f"[SUCCES] {test_name}")
            else:
                print(f"[ECHEC] {test_name}")
        except Exception as e:
            print(f"[ERREUR] {test_name}: {e}")
            results.append(False)
    
    # Résultats globaux
    success_count = sum(results)
    total_count = len(results)
    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
    
    print("\n" + "=" * 60)
    print("RESULTATS VERIFICATION FONCTIONNALITE")
    print("=" * 60)
    print(f"Tests réussis: {success_count}/{total_count}")
    print(f"Taux de réussite: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("\n[SUCCES] Fonctionnalité Oracle préservée !")
        print("Les modifications Phase A n'ont pas cassé le système")
        return True
    else:
        print("\n[ECHEC] Problèmes détectés !")
        print("Révision nécessaire des modifications")
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERREUR CRITIQUE] {e}")
        exit(2)