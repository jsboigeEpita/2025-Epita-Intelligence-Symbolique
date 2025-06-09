#!/usr/bin/env python3
"""Test d'import de tous les modules de démonstration"""

# Auto-activation environnement intelligent
import scripts.core.auto_env

import sys
import traceback

# Ajouter le chemin des scripts de démonstration
sys.path.insert(0, 'examples/scripts_demonstration')

module_list = [
    'custom_data_processor',
    'demo_agents_logiques',
    'demo_cas_usage',
    'demo_integrations',
    'demo_outils_utils',
    'demo_services_core',
    'demo_tests_validation',
    'demo_utils',
    'test_elimination_mocks_validation',
    'test_final_validation_ascii'
]

success = 0
failed = []

print("TEST D'IMPORTATION DES MODULES DE DÉMONSTRATION")
print("=" * 50)

for mod in module_list:
    try:
        exec(f'import modules.{mod}')
        print(f'[OK] {mod}')
        success += 1
    except Exception as e:
        print(f'[FAIL] {mod}: {e}')
        failed.append((mod, str(e)))

print("=" * 50)
print(f'RÉSULTAT: {success}/{len(module_list)} modules importables')

if failed:
    print("\nMODULES ÉCHOUÉS:")
    for mod, error in failed:
        print(f"  - {mod}: {error}")