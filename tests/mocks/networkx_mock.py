"""
Mock pour la bibliothèque networkx.
"""
from unittest.mock import MagicMock

# Mock pour les fonctions et classes couramment utilisées de networkx
DiGraph = MagicMock()
MultiDiGraph = MagicMock() # Au cas où
spring_layout = MagicMock(return_value={0: (0.1, 0.2), 1: (0.8, 0.9)}) # Retourne un dict de positions
draw_networkx_nodes = MagicMock()
draw_networkx_edges = MagicMock()
draw_networkx_labels = MagicMock()
# ... ajoutez d'autres mocks au besoin

# Mock pour le module networkx lui-même
class NetworkXMock(MagicMock):
    DiGraph = DiGraph
    MultiDiGraph = MultiDiGraph
    spring_layout = spring_layout
    draw_networkx_nodes = draw_networkx_nodes
    draw_networkx_edges = draw_networkx_edges
    draw_networkx_labels = draw_networkx_labels
    # Simuler d'autres attributs/fonctions si nécessaire
    # Par exemple, si le code accède à des exceptions spécifiques de networkx:
    # NetworkXError = type('NetworkXError', (Exception,), {})

# Ce mock sera inséré dans sys.modules['networkx'] par conftest.py