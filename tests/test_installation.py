print("Test d'installation réussi")

# Essayons d'importer quelques bibliothèques importantes
try:
    import jpype
    print("JPype importé avec succès")
except ImportError as e:
    print(f"Erreur lors de l'importation de JPype: {e}")

try:
    import numpy
    print("NumPy importé avec succès")
except ImportError as e:
    print(f"Erreur lors de l'importation de NumPy: {e}")

try:
    import torch
    print("PyTorch importé avec succès")
except ImportError as e:
    print(f"Erreur lors de l'importation de PyTorch: {e}")

try:
    import transformers
    print("Transformers importé avec succès")
except ImportError as e:
    print(f"Erreur lors de l'importation de Transformers: {e}")

try:
    import networkx
    print("NetworkX importé avec succès")
except ImportError as e:
    print(f"Erreur lors de l'importation de NetworkX: {e}")