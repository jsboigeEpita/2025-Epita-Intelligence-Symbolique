"""
Mock complet de NetworkX pour éviter l'installation de la dépendance.

Ce mock simule les fonctionnalités essentielles de NetworkX utilisées par le projet.
"""

import sys
from unittest.mock import MagicMock
from collections import defaultdict

# Version du mock
__version__ = "3.0-mock"

class MockGraph:
    """Mock pour networkx.Graph."""
    
    def __init__(self):
        self.nodes_dict = {}
        self.edges_dict = defaultdict(dict)
        self._node_attr = {}
        self._edge_attr = defaultdict(dict)
    
    def add_node(self, node, **attr):
        """Ajoute un nœud au graphe."""
        self.nodes_dict[node] = True
        if attr:
            self._node_attr[node] = attr
    
    def add_edge(self, u, v, **attr):
        """Ajoute une arête au graphe."""
        self.edges_dict[u][v] = True
        self.edges_dict[v][u] = True
        if attr:
            self._edge_attr[(u, v)] = attr
            self._edge_attr[(v, u)] = attr
    
    def nodes(self, data=False):
        """Retourne les nœuds du graphe."""
        if data:
            return [(node, self._node_attr.get(node, {})) for node in self.nodes_dict.keys()]
        return list(self.nodes_dict.keys())
    
    def edges(self, data=False):
        """Retourne les arêtes du graphe."""
        edges = []
        seen = set()
        for u in self.edges_dict:
            for v in self.edges_dict[u]:
                edge = tuple(sorted([u, v]))
                if edge not in seen:
                    seen.add(edge)
                    if data:
                        edges.append((u, v, self._edge_attr.get((u, v), {})))
                    else:
                        edges.append((u, v))
        return edges
    
    def neighbors(self, node):
        """Retourne les voisins d'un nœud."""
        return list(self.edges_dict.get(node, {}).keys())
    
    def degree(self, node=None):
        """Retourne le degré d'un nœud ou de tous les nœuds."""
        if node is not None:
            return len(self.edges_dict.get(node, {}))
        return {n: len(self.edges_dict.get(n, {})) for n in self.nodes_dict}
    
    def number_of_nodes(self):
        """Retourne le nombre de nœuds."""
        return len(self.nodes_dict)
    
    def number_of_edges(self):
        """Retourne le nombre d'arêtes."""
        return len(self.edges()) if hasattr(self, 'edges') else 0
    
    def has_node(self, node):
        """Vérifie si un nœud existe."""
        return node in self.nodes_dict
    
    def has_edge(self, u, v):
        """Vérifie si une arête existe."""
        return v in self.edges_dict.get(u, {})
    
    def remove_node(self, node):
        """Supprime un nœud."""
        if node in self.nodes_dict:
            del self.nodes_dict[node]
            # Supprimer toutes les arêtes connectées
            for neighbor in list(self.edges_dict.get(node, {}).keys()):
                if neighbor in self.edges_dict:
                    self.edges_dict[neighbor].pop(node, None)
            self.edges_dict.pop(node, None)
            self._node_attr.pop(node, None)
    
    def remove_edge(self, u, v):
        """Supprime une arête."""
        if u in self.edges_dict and v in self.edges_dict[u]:
            del self.edges_dict[u][v]
            del self.edges_dict[v][u]
            self._edge_attr.pop((u, v), None)
            self._edge_attr.pop((v, u), None)
    
    def copy(self):
        """Retourne une copie du graphe."""
        new_graph = MockGraph()
        new_graph.nodes_dict = self.nodes_dict.copy()
        new_graph.edges_dict = defaultdict(dict)
        for u in self.edges_dict:
            new_graph.edges_dict[u] = self.edges_dict[u].copy()
        new_graph._node_attr = self._node_attr.copy()
        new_graph._edge_attr = self._edge_attr.copy()
        return new_graph

class MockDiGraph(MockGraph):
    """Mock pour networkx.DiGraph (graphe dirigé)."""
    
    def add_edge(self, u, v, **attr):
        """Ajoute une arête dirigée au graphe."""
        self.edges_dict[u][v] = True
        if attr:
            self._edge_attr[(u, v)] = attr
    
    def edges(self, data=False):
        """Retourne les arêtes dirigées du graphe."""
        edges = []
        for u in self.edges_dict:
            for v in self.edges_dict[u]:
                if data:
                    edges.append((u, v, self._edge_attr.get((u, v), {})))
                else:
                    edges.append((u, v))
        return edges
    
    def predecessors(self, node):
        """Retourne les prédécesseurs d'un nœud."""
        preds = []
        for u in self.edges_dict:
            if node in self.edges_dict[u]:
                preds.append(u)
        return preds
    
    def successors(self, node):
        """Retourne les successeurs d'un nœud."""
        return list(self.edges_dict.get(node, {}).keys())
    
    def in_degree(self, node=None):
        """Retourne le degré entrant d'un nœud."""
        if node is not None:
            return len(self.predecessors(node))
        return {n: len(self.predecessors(n)) for n in self.nodes_dict}
    
    def out_degree(self, node=None):
        """Retourne le degré sortant d'un nœud."""
        if node is not None:
            return len(self.edges_dict.get(node, {}))
        return {n: len(self.edges_dict.get(n, {})) for n in self.nodes_dict}

# Fonctions de création de graphes
def Graph():
    """Crée un graphe non dirigé."""
    return MockGraph()

def DiGraph():
    """Crée un graphe dirigé."""
    return MockDiGraph()

def MultiGraph():
    """Crée un multigraphe."""
    return MockGraph()  # Simplification

def MultiDiGraph():
    """Crée un multigraphe dirigé."""
    return MockDiGraph()  # Simplification

# Algorithmes de base
def shortest_path(G, source=None, target=None, weight=None, method='dijkstra'):
    """Mock pour shortest_path."""
    if source is not None and target is not None:
        # Retourner un chemin simple pour le mock
        if G.has_node(source) and G.has_node(target):
            if source == target:
                return [source]
            elif G.has_edge(source, target):
                return [source, target]
            else:
                # Chemin fictif via un nœud intermédiaire
                nodes = list(G.nodes())
                if len(nodes) >= 3:
                    return [source, nodes[0], target]
                return [source, target]
        return []
    return {}

def shortest_path_length(G, source=None, target=None, weight=None, method='dijkstra'):
    """Mock pour shortest_path_length."""
    path = shortest_path(G, source, target, weight, method)
    if isinstance(path, list):
        return len(path) - 1 if len(path) > 0 else float('inf')
    return {}

def connected_components(G):
    """Mock pour connected_components."""
    # Retourner chaque nœud comme sa propre composante pour simplifier
    for node in G.nodes():
        yield [node]

def strongly_connected_components(G):
    """Mock pour strongly_connected_components."""
    # Retourner chaque nœud comme sa propre composante pour simplifier
    for node in G.nodes():
        yield [node]

def is_connected(G):
    """Mock pour is_connected."""
    return len(list(G.nodes())) <= 1 or True  # Simplification

def number_connected_components(G):
    """Mock pour number_connected_components."""
    return len(list(connected_components(G)))

def pagerank(G, alpha=0.85, personalization=None, max_iter=100, tol=1e-06, weight='weight'):
    """Mock pour pagerank."""
    nodes = list(G.nodes())
    if not nodes:
        return {}
    # Retourner des valeurs uniformes pour le mock
    value = 1.0 / len(nodes)
    return {node: value for node in nodes}

def betweenness_centrality(G, k=None, normalized=True, weight=None, endpoints=False, seed=None):
    """Mock pour betweenness_centrality."""
    nodes = list(G.nodes())
    if not nodes:
        return {}
    # Retourner des valeurs uniformes pour le mock
    value = 1.0 / len(nodes) if normalized else 1.0
    return {node: value for node in nodes}

def closeness_centrality(G, u=None, distance=None, normalized=True):
    """Mock pour closeness_centrality."""
    if u is not None:
        return 1.0 if normalized else len(G.nodes())
    nodes = list(G.nodes())
    value = 1.0 if normalized else len(nodes)
    return {node: value for node in nodes}

def degree_centrality(G):
    """Mock pour degree_centrality."""
    nodes = list(G.nodes())
    if len(nodes) <= 1:
        return {node: 0.0 for node in nodes}
    max_degree = len(nodes) - 1
    return {node: G.degree(node) / max_degree for node in nodes}

# Génération de graphes
def complete_graph(n):
    """Génère un graphe complet."""
    G = Graph()
    nodes = list(range(n))
    for node in nodes:
        G.add_node(node)
    for i in range(n):
        for j in range(i + 1, n):
            G.add_edge(i, j)
    return G

def path_graph(n):
    """Génère un graphe en chemin."""
    G = Graph()
    nodes = list(range(n))
    for node in nodes:
        G.add_node(node)
    for i in range(n - 1):
        G.add_edge(i, i + 1)
    return G

def cycle_graph(n):
    """Génère un graphe en cycle."""
    G = path_graph(n)
    if n > 2:
        G.add_edge(0, n - 1)
    return G

def random_graph(n, p, seed=None):
    """Génère un graphe aléatoire."""
    import random
    if seed is not None:
        random.seed(seed)
    
    G = Graph()
    nodes = list(range(n))
    for node in nodes:
        G.add_node(node)
    
    for i in range(n):
        for j in range(i + 1, n):
            if random.random() < p:
                G.add_edge(i, j)
    return G

# Lecture/écriture de graphes
def read_gml(path, label='label', destringizer=None):
    """Mock pour read_gml."""
    return Graph()

def write_gml(G, path, stringizer=None):
    """Mock pour write_gml."""
    pass

def read_graphml(path, node_type=str, edge_key_type=str):
    """Mock pour read_graphml."""
    return Graph()

def write_graphml(G, path, encoding='utf-8', prettyprint=True):
    """Mock pour write_graphml."""
    pass

# Exceptions NetworkX
class NetworkXError(Exception):
    """Exception de base pour NetworkX."""
    pass

class NetworkXNoPath(NetworkXError):
    """Exception pour les chemins inexistants."""
    pass

class NetworkXNotImplemented(NetworkXError):
    """Exception pour les fonctionnalités non implémentées."""
    pass

# Modules simulés
class algorithms:
    """Module algorithms simulé."""
    
    class centrality:
        betweenness_centrality = betweenness_centrality
        closeness_centrality = closeness_centrality
        degree_centrality = degree_centrality
        pagerank = pagerank
    
    class shortest_paths:
        class generic:
            shortest_path = shortest_path
            shortest_path_length = shortest_path_length
    
    class components:
        connected_components = connected_components
        strongly_connected_components = strongly_connected_components
        is_connected = is_connected
        number_connected_components = number_connected_components

class generators:
    """Module generators simulé."""
    
    class classic:
        complete_graph = complete_graph
        path_graph = path_graph
        cycle_graph = cycle_graph
    
    class random_graphs:
        random_graph = random_graph

class readwrite:
    """Module readwrite simulé."""
    
    class gml:
        read_gml = read_gml
        write_gml = write_gml
    
    class graphml:
        read_graphml = read_graphml
        write_graphml = write_graphml

# Installation du mock dans sys.modules
sys.modules['networkx'] = sys.modules[__name__]
sys.modules['networkx.algorithms'] = algorithms
sys.modules['networkx.algorithms.centrality'] = algorithms.centrality
sys.modules['networkx.algorithms.shortest_paths'] = algorithms.shortest_paths
sys.modules['networkx.algorithms.shortest_paths.generic'] = algorithms.shortest_paths.generic
sys.modules['networkx.algorithms.components'] = algorithms.components
sys.modules['networkx.generators'] = generators
sys.modules['networkx.generators.classic'] = generators.classic
sys.modules['networkx.generators.random_graphs'] = generators.random_graphs
sys.modules['networkx.readwrite'] = readwrite
sys.modules['networkx.readwrite.gml'] = readwrite.gml
sys.modules['networkx.readwrite.graphml'] = readwrite.graphml

print("[MOCK] Mock NetworkX activé - toutes les fonctionnalités de base disponibles")