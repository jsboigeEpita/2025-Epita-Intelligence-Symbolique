#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de validation des corrections finales appliquées.
Teste spécifiquement les 5 corrections appliquées.
"""

import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Ajouter le répertoire racine au chemin Python
sys.path.append(os.path.abspath('.'))

# Activer les mocks de base
try:
    from tests.mocks.numpy_mock import activate_numpy_mock
    activate_numpy_mock()
except:
    pass

try:
    from tests.mocks.networkx_mock import activate_networkx_mock
    activate_networkx_mock()
except:
    pass

def test_correction_1_imports_mock():
    """Test Correction 1: Vérifier que les imports Mock sont présents."""
    print("Test Correction 1: Imports Mock")
    
    try:
        # Test test_tactical_monitor.py
        from tests.test_tactical_monitor import unittest, Mock, MagicMock
        print("  [OK] test_tactical_monitor.py - Imports Mock OK")
        
        # Test test_tactical_monitor_advanced.py
        from tests.test_tactical_monitor_advanced import unittest, Mock, MagicMock
        print("  [OK] test_tactical_monitor_advanced.py - Imports Mock OK")
        
        return True
    except ImportError as e:
        print(f"  [ERREUR] Erreur import Mock: {e}")
        return False

def test_correction_2_task_dependencies():
    """Test Correction 2: Vérifier que task_dependencies est configuré."""
    print("Test Correction 2: Configuration task_dependencies")
    
    try:
        from tests.test_tactical_monitor import TestProgressMonitor
        
        # Créer une instance de test
        test_instance = TestProgressMonitor()
        test_instance.setUp()
        
        # Vérifier que task_dependencies existe
        if hasattr(test_instance.tactical_state, 'task_dependencies'):
            print("  [OK] task_dependencies configuré dans test_tactical_monitor.py")
            return True
        else:
            print("  [ERREUR] task_dependencies manquant dans test_tactical_monitor.py")
            return False
            
    except Exception as e:
        print(f"  [ERREUR] Erreur test task_dependencies: {e}")
        return False

def test_correction_3_overall_coherence():
    """Test Correction 3: Vérifier le mock de _evaluate_overall_coherence."""
    print("Test Correction 3: Mock _evaluate_overall_coherence")
    
    try:
        from tests.test_tactical_monitor_advanced import TestTacticalMonitorAdvanced
        
        # Créer une instance de test
        test_instance = TestTacticalMonitorAdvanced()
        test_instance.setUp()
        
        # Tester la méthode test_evaluate_overall_coherence
        test_instance.test_evaluate_overall_coherence()
        print("  [OK] test_evaluate_overall_coherence exécuté sans erreur")
        return True
        
    except Exception as e:
        print(f"  [ERREUR] Erreur test overall_coherence: {e}")
        return False

def test_correction_4_validation_agent():
    """Test Correction 4: Vérifier MockValidationAgent."""
    print("Test Correction 4: MockValidationAgent")
    
    try:
        from tests.test_extract_agent_adapter import MockValidationAgent
        
        # Créer une instance
        mock_agent = MockValidationAgent()
        print("  [OK] MockValidationAgent créé avec succès")
        return True
        
    except Exception as e:
        print(f"  [ERREUR] Erreur MockValidationAgent: {e}")
        return False

def test_correction_5_extract_plugin():
    """Test Correction 5: Vérifier les attributs Mock ExtractPlugin."""
    print("Test Correction 5: Mock ExtractPlugin")
    
    try:
        from tests.test_extract_agent_adapter import TestExtractAgentAdapter
        
        # Créer une instance de test
        test_instance = TestExtractAgentAdapter()
        test_instance.setUp()
        
        # Vérifier les attributs du mock_extract_plugin
        required_attrs = ['extract', 'process_text', 'get_supported_formats']
        for attr in required_attrs:
            if hasattr(test_instance.mock_extract_plugin, attr):
                print(f"  [OK] mock_extract_plugin.{attr} configuré")
            else:
                print(f"  [ERREUR] mock_extract_plugin.{attr} manquant")
                return False
        
        return True
        
    except Exception as e:
        print(f"  [ERREUR] Erreur Mock ExtractPlugin: {e}")
        return False

def main():
    """Fonction principale de validation."""
    print("=" * 60)
    print("VALIDATION DES CORRECTIONS FINALES")
    print("=" * 60)
    
    corrections = [
        ("Correction 1: Imports Mock", test_correction_1_imports_mock),
        ("Correction 2: task_dependencies", test_correction_2_task_dependencies),
        ("Correction 3: overall_coherence", test_correction_3_overall_coherence),
        ("Correction 4: MockValidationAgent", test_correction_4_validation_agent),
        ("Correction 5: Mock ExtractPlugin", test_correction_5_extract_plugin),
    ]
    
    results = []
    
    for name, test_func in corrections:
        print(f"\n{name}")
        print("-" * 40)
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Erreur inattendue: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("RESULTATS FINAUX")
    print("=" * 60)
    
    success_count = sum(results)
    total_count = len(results)
    success_rate = (success_count / total_count) * 100
    
    for i, (name, _) in enumerate(corrections):
        status = "[REUSSI]" if results[i] else "[ECHEC]"
        print(f"{name}: {status}")
    
    print(f"\nTAUX DE REUSSITE: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_count == total_count:
        print("TOUTES LES CORRECTIONS VALIDEES AVEC SUCCES!")
        return 0
    else:
        print(f"{total_count - success_count} corrections necessitent encore des ajustements.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)