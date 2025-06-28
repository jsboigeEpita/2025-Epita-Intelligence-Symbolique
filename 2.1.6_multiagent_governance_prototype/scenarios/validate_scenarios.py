"""
Scenario validation script for Multiagent Governance Prototype.
Usage:
    python validate_scenarios.py
Checks all scenario files in the current directory for correctness.
"""
import os
import json
from metrics.metrics import validate_scenario

def main():
    scenario_files = [f for f in os.listdir('.') if f.endswith('.json')]
    all_valid = True
    for fname in scenario_files:
        with open(fname) as f:
            scenario = json.load(f)
        valid, msg = validate_scenario(scenario)
        if valid:
            print(f"[OK] {fname}")
        else:
            print(f"[ERROR] {fname}: {msg}")
            all_valid = False
    if not all_valid:
        print("Some scenarios are invalid.")
        exit(1)
    else:
        print("All scenarios are valid.")

if __name__ == '__main__':
    main() 