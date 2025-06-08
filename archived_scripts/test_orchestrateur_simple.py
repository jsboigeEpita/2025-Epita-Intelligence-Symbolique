#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple pour tester l'orchestrateur Sherlock/Watson
"""

import sys
import traceback

def test_import_orchestrateur():
    """Test d'import de l'orchestrateur"""
    try:
        sys.path.append('.')
        from argumentation_analysis.agents.orchestration.cluedo_sherlock_watson_demo import CluedoSherlockWatsonOrchestrator
        print("[OK] Orchestrateur Cluedo charge avec succes")
        return True
    except Exception as e:
        print(f"[ERREUR] Import orchestrateur: {e}")
        traceback.print_exc()
        return False

def test_import_agents():
    """Test d'import des agents principaux"""
    try:
        from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
        print("[OK] Sherlock Agent charge")
        
        from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
        print("[OK] Watson Agent charge")
        
        from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
        print("[OK] Moriarty Agent charge")
        
        return True
    except Exception as e:
        print(f"[ERREUR] Import agents: {e}")
        traceback.print_exc()
        return False

def test_import_oracle():
    """Test d'import des composants Oracle"""
    try:
        from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent
        print("[OK] Oracle Base Agent charge")
        
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
        print("[OK] Cluedo Dataset charge")
        
        from argumentation_analysis.agents.core.oracle.permissions import QueryType, RevealPolicy
        print("[OK] Permissions Oracle chargees")
        
        return True
    except Exception as e:
        print(f"[ERREUR] Import Oracle: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== TEST SYSTÈME SHERLOCK/WATSON/MORIARTY ===")
    
    agents_ok = test_import_agents()
    oracle_ok = test_import_oracle()
    orchestrateur_ok = test_import_orchestrateur()
    
    print("\n=== RÉSULTAT ===")
    print(f"Agents: {'[OK]' if agents_ok else '[ERREUR]'}")
    print(f"Oracle: {'[OK]' if oracle_ok else '[ERREUR]'}")
    print(f"Orchestrateur: {'[OK]' if orchestrateur_ok else '[ERREUR]'}")
    
    if agents_ok and oracle_ok and orchestrateur_ok:
        print("[SUCCES] Systeme Sherlock/Watson/Moriarty operationnel!")
    else:
        print("[ATTENTION] Problemes detectes dans le systeme")