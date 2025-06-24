# Script de test minimal pour isoler l'exécution de pytest

# Active l'environnement conda
conda activate projet-is

# Exécute pytest directement sur un test simple, sans aucun des wrappers du projet
echo "Lancement de pytest directement..."
python -m pytest tests/integration/workers/test_simple.py