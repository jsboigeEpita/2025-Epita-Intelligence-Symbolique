import pytest
import os
import sys # Ajouté
from pathlib import Path # Ajouté

# Déterminer le chemin du répertoire du projet
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Chemin vers les JARs de Tweety (devrait correspondre à celui utilisé par le conftest.py racine)
TWEETY_LIBS_PATH = os.path.join(PROJECT_ROOT, "libs")

# La fixture jvm_manager et les fixtures de classes (dung_classes, qbf_classes, etc.)
# sont maintenant définies dans le conftest.py racine pour une gestion centralisée de JPype.
# Ce fichier est conservé pour d'éventuelles configurations spécifiques à ce sous-répertoire de tests,
# mais ne doit plus gérer l'initialisation de JPype ni la définition des classes Java globales.

print(f"INFO: tests/integration/jpype_tweety/conftest.py chargé. PROJECT_ROOT={PROJECT_ROOT}, TWEETY_LIBS_PATH={TWEETY_LIBS_PATH}")
print("INFO: Les fixtures JPype (jvm_manager, dung_classes, etc.) sont attendues du conftest.py racine.")