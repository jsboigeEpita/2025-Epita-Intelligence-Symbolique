"""
Script d'activation du mock JPype.
À importer avant toute utilisation de JPype dans les tests.
"""

# Importer le mock pour l'activer
from tests.mocks import jpype_mock

print("Mock JPype activé")
