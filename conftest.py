print("INFO: conftest.py (RACINE): Fichier en cours de lecture par pytest.")

import sys
import os

# Ajout précoce du chemin pour trouver argumentation_analysis
# car initialize_jvm est dans ce package.
# __file__ ici est d:/2025-Epita-Intelligence-Symbolique/conftest.py
# project_root_for_path sera d:/2025-Epita-Intelligence-Symbolique
current_script_dir_for_path = os.path.dirname(os.path.abspath(__file__))
project_root_for_path = current_script_dir_for_path # Le conftest racine EST à la racine du projet
if project_root_for_path not in sys.path:
    sys.path.insert(0, project_root_for_path)
    print(f"INFO: conftest.py (RACINE): Ajout de {project_root_for_path} à sys.path.")
else:
    print(f"INFO: conftest.py (RACINE): {project_root_for_path} déjà dans sys.path.")

initialize_jvm_func = None
try:
    from argumentation_analysis.core.jvm_setup import initialize_jvm as init_jvm_actual
    initialize_jvm_func = init_jvm_actual
    print("INFO: conftest.py (RACINE): Import de 'initialize_jvm' réussi.")
except Exception as e_import_jvm_setup:
    print(f"ERREUR CRITIQUE: conftest.py (RACINE): Échec de l'import de 'initialize_jvm': {e_import_jvm_setup}")

USE_REAL_JVM = True # Forcer l'utilisation de la vraie JVM pour le test
jpype_real_jvm_initialized_value = "0" # Défaut à non initialisé

if initialize_jvm_func is None:
    print("ERREUR CRITIQUE: conftest.py (RACINE): initialize_jvm_func non disponible. La JVM ne sera pas démarrée par ce conftest.")
elif USE_REAL_JVM:
    print("INFO: conftest.py (RACINE): Tentative d'initialisation de la VRAIE JVM...")
    try:
        if initialize_jvm_func():
            print("INFO: conftest.py (RACINE): VRAIE JVM initialisée avec succès par initialize_jvm_func().")
            jpype_real_jvm_initialized_value = "1"
        else:
            print("ERREUR: conftest.py (RACINE): initialize_jvm_func() a retourné False (échec de l'initialisation).")
            # jpype_real_jvm_initialized_value reste "0"
    except Exception as e_init_jvm_conftest:
        print(f"ERREUR CRITIQUE: conftest.py (RACINE) lors de l'appel à initialize_jvm_func: {e_init_jvm_conftest}")
        # jpype_real_jvm_initialized_value reste "0"
else:
    print("INFO: conftest.py (RACINE): USE_REAL_JVM est False. Initialisation de la vraie JVM sautée.")
    # jpype_real_jvm_initialized_value reste "0"

os.environ["JPYPE_REAL_JVM_INITIALIZED"] = jpype_real_jvm_initialized_value
print(f"INFO: conftest.py (RACINE): os.environ['JPYPE_REAL_JVM_INITIALIZED'] défini à '{jpype_real_jvm_initialized_value}'.")

print("INFO: conftest.py (RACINE): Initialisation minimale terminée. Les fixtures Flask originales sont ci-dessous mais commentées.")

# Les fixtures originales de ce fichier sont laissées commentées pour l'instant
# pour se concentrer sur le problème de la JVM.
# import pytest
# from argumentation_analysis.services.web_api.app import app as flask_app
#
# @pytest.fixture(scope='module')
# def app():
#     """Instance of Main flask app"""
#     flask_app.config.update({
#         "TESTING": True,
#     })
#     return flask_app
#
# @pytest.fixture(scope='module')
# def client(app):
#     """A test client for the app."""
#     return app.test_client()