#!/usr/bin/env python3
"""
Script pour identifier les tests qui bloquent en utilisant des timeouts.
"""

import subprocess
import threading
import time
import sys
from pathlib import Path

def run_test_with_timeout(test_path, timeout=30):
    """Exécute un test avec un timeout."""
    print(f"Testing: {test_path}")
    
    def target():
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", test_path, "-v", "--tb=no"
            ], capture_output=True, text=True, timeout=timeout)
            return result
        except subprocess.TimeoutExpired:
            return None
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        print(f"❌ TIMEOUT: {test_path}")
        return False
    else:
        print(f"✅ OK: {test_path}")
        return True

def main():
    """Fonction principale."""
    # Tests suspects basés sur les observations précédentes
    suspect_tests = [
        "argumentation_analysis/tests/test_communication_integration.py::TestCommunicationIntegration::test_end_to_end_workflow",
        "argumentation_analysis/tests/test_communication_integration.py::TestCommunicationIntegration::test_request_response_communication",
        "argumentation_analysis/tests/test_communication_integration.py::TestCommunicationIntegration::test_tactical_operational_communication",
        "argumentation_analysis/tests/integration/test_hierarchical_interaction.py",
        "argumentation_analysis/tests/integration/test_rhetorical_analysis_flow.py::TestRhetoricalAnalysisFlow::test_complete_analysis_flow",
    ]
    
    print("🔍 Détection des tests qui bloquent...")
    print("=" * 50)
    
    blocking_tests = []
    working_tests = []
    
    for test in suspect_tests:
        if run_test_with_timeout(test, timeout=15):
            working_tests.append(test)
        else:
            blocking_tests.append(test)
        time.sleep(1)  # Pause entre les tests
    
    print("\n" + "=" * 50)
    print("📊 RÉSULTATS:")
    print(f"✅ Tests fonctionnels: {len(working_tests)}")
    print(f"❌ Tests bloquants: {len(blocking_tests)}")
    
    if blocking_tests:
        print("\n🚫 Tests qui bloquent:")
        for test in blocking_tests:
            print(f"  - {test}")
    
    if working_tests:
        print("\n✅ Tests qui fonctionnent:")
        for test in working_tests:
            print(f"  - {test}")

if __name__ == "__main__":
    main()