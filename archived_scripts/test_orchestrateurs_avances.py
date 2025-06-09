#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test des orchestrateurs avancés et démonstrations Einstein-Sherlock-Watson
"""

import sys
import traceback

def test_orchestrateur_einstein():
    """Test de l'orchestrateur Einstein-Sherlock-Watson"""
    try:
        sys.path.append('.')
        from argumentation_analysis.agents.orchestration.einstein_sherlock_watson_demo import EinsteinSherlockWatsonOrchestrator
        print("[OK] Orchestrateur Einstein-Sherlock-Watson charge")
        return True
    except Exception as e:
        print(f"[ERREUR] Einstein orchestrateur: {e}")
        traceback.print_exc()
        return False

def test_orchestrateurs_unitaires():
    """Test des orchestrateurs dans les tests unitaires"""
    try:
        # Vérifie si les tests d'orchestration existent
        import os
        paths = [
            "tests/unit/argumentation_analysis/orchestration",
            "argumentation_analysis/agents/runners/test/orchestration",
            "tests/validation_sherlock_watson"
        ]
        
        for path in paths:
            if os.path.exists(path):
                files = os.listdir(path)
                print(f"[INFO] {path}: {len(files)} fichiers")
                if any('orchestr' in f.lower() for f in files):
                    print(f"[OK] Tests orchestration detectes dans {path}")
            else:
                print(f"[INFO] Chemin inexistant: {path}")
        
        return True
    except Exception as e:
        print(f"[ERREUR] Tests orchestrateurs: {e}")
        return False

def test_cluedo_extended():
    """Test des fonctionnalités Cluedo étendues"""
    try:
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset, CluedoSuggestion
        from argumentation_analysis.agents.core.oracle.dataset_access_manager import CluedoDatasetManager
        
        print("[OK] CluedoDataset et CluedoSuggestion charges")
        print("[OK] CluedoDatasetManager charge")
        
        # Test de création d'un dataset basique
        dataset = CluedoDataset()
        print(f"[INFO] Dataset Cluedo cree avec {len(dataset.suspects)} suspects")
        
        return True
    except Exception as e:
        print(f"[ERREUR] Cluedo extended: {e}")
        traceback.print_exc()
        return False

def test_phase_d_extensions():
    """Test des extensions Phase D"""
    try:
        import argumentation_analysis.agents.core.oracle.phase_d_extensions
        print("[OK] Extensions Phase D chargees")
        return True
    except Exception as e:
        print(f"[ERREUR] Phase D extensions: {e}")
        traceback.print_exc()
        return False

def list_validation_tests():
    """Liste les tests de validation disponibles"""
    try:
        import os
        validation_path = "tests/validation_sherlock_watson"
        if os.path.exists(validation_path):
            files = os.listdir(validation_path)
            tests_by_phase = {}
            
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    if 'phase_a' in file:
                        tests_by_phase.setdefault('Phase A', []).append(file)
                    elif 'phase_b' in file:
                        tests_by_phase.setdefault('Phase B', []).append(file)
                    elif 'phase_c' in file:
                        tests_by_phase.setdefault('Phase C', []).append(file)
                    elif 'phase_d' in file:
                        tests_by_phase.setdefault('Phase D', []).append(file)
                    elif 'oracle' in file:
                        tests_by_phase.setdefault('Oracle', []).append(file)
                    elif 'group' in file:
                        tests_by_phase.setdefault('Groupes', []).append(file)
                    else:
                        tests_by_phase.setdefault('Autres', []).append(file)
            
            print("\n=== TESTS DE VALIDATION DISPONIBLES ===")
            for phase, files in tests_by_phase.items():
                print(f"{phase}: {len(files)} tests")
                for file in files[:3]:  # Affiche les 3 premiers
                    print(f"  - {file}")
                if len(files) > 3:
                    print(f"  ... et {len(files)-3} autres")
            
            return len(files) > 0
        return False
    except Exception as e:
        print(f"[ERREUR] Liste validation tests: {e}")
        return False

if __name__ == "__main__":
    print("=== TEST ORCHESTRATEURS AVANCES ===")
    
    einstein_ok = test_orchestrateur_einstein()
    orchestrateurs_ok = test_orchestrateurs_unitaires()
    cluedo_extended_ok = test_cluedo_extended()
    phase_d_ok = test_phase_d_extensions()
    validation_tests_ok = list_validation_tests()
    
    print("\n=== RESULTAT ORCHESTRATEURS AVANCES ===")
    print(f"Einstein orchestrateur: {'[OK]' if einstein_ok else '[ERREUR]'}")
    print(f"Tests orchestrateurs: {'[OK]' if orchestrateurs_ok else '[ERREUR]'}")
    print(f"Cluedo extended: {'[OK]' if cluedo_extended_ok else '[ERREUR]'}")
    print(f"Phase D extensions: {'[OK]' if phase_d_ok else '[ERREUR]'}")
    print(f"Tests validation: {'[OK]' if validation_tests_ok else '[ERREUR]'}")
    
    if all([einstein_ok, orchestrateurs_ok, cluedo_extended_ok, phase_d_ok]):
        print("\n[SUCCES] Orchestrateurs avances operationnels!")
    else:
        print("\n[ATTENTION] Certains orchestrateurs avances ont des problemes")