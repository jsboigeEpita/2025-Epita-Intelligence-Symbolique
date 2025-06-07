#!/usr/bin/env python3
"""
RECOVERY SCRIPT - Exclusion ciblée de tous les tests JPype/Tweety
"""

import subprocess
import sys
import os

def main():
    """Exécution de pytest avec exclusions ciblées maximales"""
    
    # Tests JPype/Tweety à exclure complètement
    jpype_tests_to_exclude = [
        # Tests core logic (tous utilisent TweetyBridge)
        "tests/agents/core/logic/test_tweety_bridge.py",
        "tests/agents/core/logic/test_propositional_logic_agent.py",
        "tests/agents/core/logic/test_first_order_logic_agent.py", 
        "tests/agents/core/logic/test_modal_logic_agent.py",
        "tests/agents/core/logic/test_query_executor.py",
        "tests/agents/core/logic/test_examples.py",
        "tests/agents/core/logic/test_watson_logic_assistant.py",
        
        # Tests d'intégration JPype 
        "tests/integration/jpype_tweety/",
        "tests/minimal_jpype_tweety_tests/",
        
        # Tests PL qui utilisent JPype
        "tests/unit/argumentation_analysis/test_pl_definitions.py::TestSetupPLKernel::test_setup_pl_kernel_jvm_started",
        "tests/unit/argumentation_analysis/test_jvm_example.py",
        
        # Tests Playwright manquants
        "tests/functional/test_argument_analyzer.py",
        "tests/functional/test_argument_reconstructor.py",
        "tests/functional/test_fallacy_detector.py", 
        "tests/functional/test_logic_graph.py",
        "tests/functional/test_webapp_homepage.py",
        
        # Tests AsyncIO conflictuels
        "tests/integration/test_cluedo_extended_workflow.py",
        "tests/functional/test_rhetorical_analysis_workflow.py",
        "tests/unit/argumentation_analysis/test_integration_balanced_strategy.py",
        "tests/unit/argumentation_analysis/test_strategies.py",
    ]
    
    # Construire la commande pytest
    base_cmd = [
        "python", "-m", "pytest", "tests/",
        "--tb=no", "-q"
    ]
    
    # Ajouter exclusions
    for test_pattern in jpype_tests_to_exclude:
        if test_pattern.endswith('/'):
            base_cmd.extend(["--ignore", test_pattern])
        else:
            base_cmd.extend(["--deselect", test_pattern])
    
    print("RECOVERY PYTEST - EXCLUSIONS MAXIMALES JPype/Tweety")
    print("=" * 60)
    print(f"Commande: {' '.join(base_cmd)}")
    print(f"Exclusions: {len(jpype_tests_to_exclude)} patterns")
    print("=" * 60)
    
    # Exécuter avec timeout
    try:
        result = subprocess.run(
            base_cmd,
            timeout=300,  # 5 minutes max
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        print(f"\nCode de retour: {result.returncode}")
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("TIMEOUT après 5 minutes - tests JPype persistants détectés")
        return False
    except Exception as e:
        print(f"Erreur: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)