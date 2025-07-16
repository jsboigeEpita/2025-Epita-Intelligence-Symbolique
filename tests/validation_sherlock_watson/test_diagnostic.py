#!/usr/bin/env python3
"""Test diagnostic pour identifier les échecs."""

import subprocess
import os
import sys

# Désactiver JPype temporairement
os.environ['USE_REAL_JPYPE'] = 'false'

def run_test_group(name, command):
    """Exécute un groupe de tests et affiche le résultat."""
    print(f"\n=== {name} ===")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=60
        )
        output = result.stdout + result.stderr
        print(f"Exit code: {result.returncode}")
        
        # Extraire les lignes importantes
        for line in output.split('\n'):
            if any(keyword in line.lower() for keyword in ['failed', 'error', 'passed', '=']):
                print(line.strip())
                
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT après 60s")
    except Exception as e:
        print(f"ERREUR: {e}")

# Tests par groupes
test_groups = [
    ("Oracle Tests", "python -m pytest tests/unit/argumentation_analysis/agents/core/oracle/ --tb=no"),
    ("Integration Tests", "python -m pytest tests/integration/test_oracle_integration.py --tb=no"),
    ("Logic Tests (sans Tweety)", "python -m pytest tests/agents/core/logic/test_modal_logic_agent_authentic.py --tb=no"),
]

for name, cmd in test_groups:
    run_test_group(name, cmd)