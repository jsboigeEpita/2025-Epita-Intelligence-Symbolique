#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test minimal pour vérifier l'importation des modules principaux et la configuration de base.
Ce script est destiné à être exécuté manuellement pour un diagnostic rapide.
Il n'est pas conçu comme un test pytest standard.
"""

import os
import sys
import importlib

# Configuration de base du logging pour ce script
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ajouter le répertoire racine au chemin Python
# Cela est crucial pour que les imports relatifs dans le projet fonctionnent.
current_script_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_script_path) # Remonter de /tests à /
if project_root not in sys.path:
    sys.path.insert(0, project_root)
logging.info(f"Répertoire racine du projet ajouté au PYTHONPATH: {project_root}")


# Vérifier l'importation des modules clés
modules_to_check = {
    "argumentation_analysis.core.jvm_setup": False,
    "argumentation_analysis.core.state_manager_plugin": False, # Ancien nom potentiel
    "argumentation_analysis.core.shared_state": False, # Nouveau nom potentiel pour state_manager
    "argumentation_analysis.agents.core.informal.informal_agent": False,
    "argumentation_analysis.agents.core.extract.extract_agent": False,
    "argumentation_analysis.orchestration.analysis_runner": False,
    "semantic_kernel": False,
    "pandas": False,
    "numpy": False,
    "jpype": False
}

print("\n--- Vérification des importations des modules clés ---")
for module_name in modules_to_check:
    try:
        importlib.import_module(module_name)
        modules_to_check[module_name] = True
        print(f"[OK] Module {module_name} importé avec succès.")
    except ImportError as e:
        print(f"[ERREUR] Erreur lors de l'importation du module {module_name}: {e}")
    except Exception as e:
        print(f"[ERREUR FATALE] Erreur inattendue lors de l'importation de {module_name}: {e}")


# Test d'importation spécifique pour state_manager (si l'erreur persiste)
STATE_MANAGER_AVAILABLE = False
try:
    # Tenter d'importer ce qui pourrait être le nouveau nom ou l'ancienne structure
    from argumentation_analysis.core import shared_state as state_manager_module
    # Ou si c'est un plugin:
    # from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
    print("[OK] Module contenant state_manager/shared_state importé avec succès.")
    STATE_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"[ERREUR] Erreur lors de l'importation spécifique de state_manager/shared_state: {e}")
except Exception as e:
    print(f"[ERREUR FATALE] Erreur inattendue lors de l'importation spécifique de state_manager/shared_state: {e}")


print("\n--- Résumé des importations ---")
for module, status in modules_to_check.items():
    print(f"{module}: {'Importé' if status else 'Échec import'}")

if all(modules_to_check.values()):
    print("\n[SUCCÈS] Tous les modules clés ont été importés avec succès.")
else:
    print("\n[ÉCHEC] Au moins un module clé n'a pas pu être importé.")

if not STATE_MANAGER_AVAILABLE:
     print("[ATTENTION] state_manager (ou shared_state) n'a pas pu être importé spécifiquement.")

print("\nTest minimal terminé.")

# Ce script n'est pas un test pytest, donc pas de `pytest.main()` ici.
# Il peut être exécuté avec `python tests/test_minimal.py`