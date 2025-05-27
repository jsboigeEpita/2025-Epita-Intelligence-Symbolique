#!/usr/bin/env python3
"""
Mock pour networkx
"""

from unittest.mock import Mock, MagicMock

class Graph(Mock):
    """Mock pour networkx.Graph"""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.nodes = Mock()
        self.edges = Mock()
        self.add_node = Mock()
        self.add_edge = Mock()
        self.remove_node = Mock()
        self.remove_edge = Mock()
        self.neighbors = Mock(return_value=[])
        self.degree = Mock(return_value=0)

class DiGraph(Graph):
    """Mock pour networkx.DiGraph"""
    pass

class MultiGraph(Graph):
    """Mock pour networkx.MultiGraph"""
    pass

class MultiDiGraph(Graph):
    """Mock pour networkx.MultiDiGraph"""
    pass

# Fonctions principales
def shortest_path(*args, **kwargs):
    return []

def connected_components(*args, **kwargs):
    return []

def strongly_connected_components(*args, **kwargs):
    return []

def pagerank(*args, **kwargs):
    return {}

def betweenness_centrality(*args, **kwargs):
    return {}

def closeness_centrality(*args, **kwargs):
    return {}

def degree_centrality(*args, **kwargs):
    return {}

def clustering(*args, **kwargs):
    return {}

def transitivity(*args, **kwargs):
    return 0.0

def density(*args, **kwargs):
    return 0.0

def is_connected(*args, **kwargs):
    return True

def number_of_nodes(*args, **kwargs):
    return 0

def number_of_edges(*args, **kwargs):
    return 0

# Algorithmes
algorithms = Mock()
algorithms.shortest_path = shortest_path
algorithms.connected_components = connected_components
algorithms.strongly_connected_components = strongly_connected_components
algorithms.centrality = Mock()
algorithms.centrality.pagerank = pagerank
algorithms.centrality.betweenness_centrality = betweenness_centrality
algorithms.centrality.closeness_centrality = closeness_centrality
algorithms.centrality.degree_centrality = degree_centrality
algorithms.cluster = Mock()
algorithms.cluster.clustering = clustering
algorithms.cluster.transitivity = transitivity

# Export des principales classes et fonctions
__all__ = [
    'Graph', 'DiGraph', 'MultiGraph', 'MultiDiGraph',
    'shortest_path', 'connected_components', 'strongly_connected_components',
    'pagerank', 'betweenness_centrality', 'closeness_centrality', 'degree_centrality',
    'clustering', 'transitivity', 'density', 'is_connected',
    'number_of_nodes', 'number_of_edges', 'algorithms'
]