"""
Documentation System - Mappeur de Connaissances et Dépendances
==============================================================

Crée une cartographie interactive des connaissances et des interdépendances
du projet d'IA symbolique pour faciliter la navigation et la compréhension.

Fonctionnalités :
- Graphique de dépendances interactif
- Carte des connaissances par domaine
- Visualisation des flux de données
- Recommandations d'apprentissage personnalisées
"""

import json
import networkx as nx
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass
from collections import defaultdict, deque
import math


@dataclass
class KnowledgeNode:
    """Nœud de connaissance dans la carte"""
    id: str
    name: str
    category: str
    type: str
    complexity: int
    importance: float = 0.0
    prerequisites: Set[str] = None
    connections: Set[str] = None
    learning_order: int = 0
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = set()
        if self.connections is None:
            self.connections = set()


class KnowledgeMapper:
    """Mappeur de connaissances pour le projet IA symbolique"""
    
    def __init__(self, analysis_file: str = "project_analysis.json"):
        self.analysis_file = analysis_file
        self.analysis_data = None
        self.knowledge_graph = nx.DiGraph()
        self.knowledge_nodes: Dict[str, KnowledgeNode] = {}
        self.learning_paths: Dict[str, List[str]] = {}
        self.domain_clusters = {}
        
        self._load_analysis()
        self._build_knowledge_graph()
    
    def _load_analysis(self):
        """Charge les données d'analyse"""
        try:
            with open(self.analysis_file, 'r', encoding='utf-8') as f:
                self.analysis_data = json.load(f)
            print(f" Analyse chargée pour le mapping des connaissances")
        except Exception as e:
            print(f" Erreur lors du chargement: {e}")
            raise
    
    def _build_knowledge_graph(self):
        """Construit le graphe de connaissances"""
        print(" Construction du graphe de connaissances...")
        
        # 1. Créer les nœuds de connaissance
        self._create_knowledge_nodes()
        
        # 2. Établir les connexions
        self._establish_connections()
        
        # 3. Calculer l'importance des nœuds
        self._calculate_importance()
        
        # 4. Déterminer l'ordre d'apprentissage
        self._determine_learning_order()
        
        # 5. Créer les clusters de domaines
        self._create_domain_clusters()
    
    def _create_knowledge_nodes(self):
        """Crée les nœuds de connaissance à partir des modules"""
        for module_path, module_data in self.analysis_data['modules'].items():
            node_id = self._get_node_id(module_path)
            
            node = KnowledgeNode(
                id=node_id,
                name=module_data['name'],
                category=module_data['category'],
                type=module_data['type'],
                complexity=module_data['complexity_score']
            )
            
            self.knowledge_nodes[node_id] = node
            self.knowledge_graph.add_node(node_id, **node.__dict__)
    
    def _establish_connections(self):
        """Établit les connexions entre les nœuds"""
        dependency_graph = self.analysis_data['dependency_graph']
        
        for module_path, dependencies in dependency_graph.items():
            source_id = self._get_node_id(module_path)
            
            for dep in dependencies:
                target_id = self._get_node_id(dep)
                
                if target_id in self.knowledge_nodes:
                    # Ajouter l'arête de dépendance
                    self.knowledge_graph.add_edge(target_id, source_id, 
                                                 relationship='dependency')
                    
                    # Mettre à jour les connexions
                    self.knowledge_nodes[source_id].prerequisites.add(target_id)
                    self.knowledge_nodes[target_id].connections.add(source_id)
    
    def _calculate_importance(self):
        """Calcule l'importance de chaque nœud"""
        print(" Calcul de l'importance des nœuds...")
        
        # Utiliser PageRank pour mesurer l'importance
        pagerank_scores = nx.pagerank(self.knowledge_graph)
        
        # Calculer aussi la centralité
        try:
            centrality_scores = nx.betweenness_centrality(self.knowledge_graph)
        except:
            centrality_scores = {node: 0 for node in self.knowledge_graph.nodes()}
        
        # Combiner les scores
        for node_id in self.knowledge_nodes:
            pr_score = pagerank_scores.get(node_id, 0)
            centrality_score = centrality_scores.get(node_id, 0)
            
            # Score combiné (normaliser entre 0 et 1)
            importance = (pr_score * 0.7) + (centrality_score * 0.3)
            self.knowledge_nodes[node_id].importance = importance
    
    def _determine_learning_order(self):
        """Détermine l'ordre d'apprentissage optimal"""
        print(" Détermination de l'ordre d'apprentissage...")
        
        # Tri topologique pour l'ordre d'apprentissage
        try:
            topo_order = list(nx.topological_sort(self.knowledge_graph))
            
            for i, node_id in enumerate(topo_order):
                if node_id in self.knowledge_nodes:
                    self.knowledge_nodes[node_id].learning_order = i
        except nx.NetworkXError:
            # Graphe cyclique, utiliser une approche alternative
            self._handle_cyclic_dependencies()
    
    def _handle_cyclic_dependencies(self):
        """Gère les dépendances cycliques"""
        print(" Dépendances cycliques détectées, utilisation d'une approche alternative...")
        
        # Détecter les cycles
        cycles = list(nx.simple_cycles(self.knowledge_graph))
        
        # Assigner un ordre basé sur la complexité et l'importance
        nodes_by_priority = sorted(
            self.knowledge_nodes.values(),
            key=lambda n: (n.complexity, -n.importance)
        )
        
        for i, node in enumerate(nodes_by_priority):
            node.learning_order = i
    
    def _create_domain_clusters(self):
        """Crée des clusters par domaine de connaissance"""
        print(" Création des clusters de domaines...")
        
        # Grouper par catégorie
        for node in self.knowledge_nodes.values():
            if node.category not in self.domain_clusters:
                self.domain_clusters[node.category] = {
                    'nodes': [],
                    'complexity_avg': 0,
                    'importance_avg': 0,
                    'entry_points': [],
                    'advanced_nodes': []
                }
            
            cluster = self.domain_clusters[node.category]
            cluster['nodes'].append(node.id)
        
        # Calculer les statistiques par cluster
        for category, cluster in self.domain_clusters.items():
            nodes = [self.knowledge_nodes[nid] for nid in cluster['nodes']]
            
            cluster['complexity_avg'] = sum(n.complexity for n in nodes) / len(nodes)
            cluster['importance_avg'] = sum(n.importance for n in nodes) / len(nodes)
            
            # Points d'entrée (faible complexité, peu de prérequis)
            cluster['entry_points'] = [
                n.id for n in nodes 
                if n.complexity <= cluster['complexity_avg'] * 0.7 
                and len(n.prerequisites) <= 1
            ]
            
            # Nœuds avancés (haute complexité ou importance)
            cluster['advanced_nodes'] = [
                n.id for n in nodes
                if n.complexity >= cluster['complexity_avg'] * 1.3
                or n.importance >= cluster['importance_avg'] * 1.5
            ]
    
    def generate_learning_paths(self) -> Dict[str, List[str]]:
        """Génère des parcours d'apprentissage personnalisés"""
        print(" Génération des parcours d'apprentissage...")
        
        self.learning_paths = {
            'beginner': self._create_beginner_path(),
            'agent_developer': self._create_agent_developer_path(),
            'orchestration_expert': self._create_orchestration_path(),
            'rhetorical_analyst': self._create_rhetorical_path(),
            'complete_mastery': self._create_complete_path()
        }
        
        return self.learning_paths
    
    def _create_beginner_path(self) -> List[str]:
        """Parcours pour débutants"""
        path = []
        
        # Commencer par les entry points de chaque domaine principal
        main_categories = ['extract', 'informal', 'logic']
        
        for category in main_categories:
            if category in self.domain_clusters:
                entry_points = self.domain_clusters[category]['entry_points']
                if entry_points:
                    # Prendre le point d'entrée le plus simple
                    simplest = min(entry_points, 
                                 key=lambda nid: self.knowledge_nodes[nid].complexity)
                    path.append(simplest)
        
        return path
    
    def _create_agent_developer_path(self) -> List[str]:
        """Parcours pour développeurs d'agents"""
        path = []
        
        # Focus sur les agents et leurs dépendances
        agent_nodes = [
            nid for nid, node in self.knowledge_nodes.items()
            if node.type == 'agent'
        ]
        
        # Trier par ordre d'apprentissage et complexité
        agent_nodes.sort(key=lambda nid: (
            self.knowledge_nodes[nid].learning_order,
            self.knowledge_nodes[nid].complexity
        ))
        
        return agent_nodes[:8]  # Top 8 pour ne pas surcharger
    
    def _create_orchestration_path(self) -> List[str]:
        """Parcours pour l'orchestration"""
        path = []
        
        orchestration_nodes = [
            nid for nid, node in self.knowledge_nodes.items()
            if 'orchestration' in node.category or node.type == 'orchestration'
        ]
        
        # Ajouter les niveaux hiérarchiques dans l'ordre
        levels = ['operational', 'tactical', 'strategic']
        for level in levels:
            level_nodes = [
                nid for nid in orchestration_nodes
                if level in self.knowledge_nodes[nid].category
            ]
            path.extend(sorted(level_nodes, 
                             key=lambda nid: self.knowledge_nodes[nid].complexity)[:2])
        
        return path
    
    def _create_rhetorical_path(self) -> List[str]:
        """Parcours pour l'analyse rhétorique"""
        rhetorical_nodes = [
            nid for nid, node in self.knowledge_nodes.items()
            if 'rhetorical' in node.category or 'fallacy' in node.name.lower()
        ]
        
        return sorted(rhetorical_nodes, 
                     key=lambda nid: self.knowledge_nodes[nid].learning_order)
    
    def _create_complete_path(self) -> List[str]:
        """Parcours complet pour maîtrise totale"""
        all_nodes = list(self.knowledge_nodes.keys())
        return sorted(all_nodes, 
                     key=lambda nid: self.knowledge_nodes[nid].learning_order)
    
    def get_recommendations(self, user_knowledge: List[str]) -> Dict[str, Any]:
        """Obtient des recommandations basées sur les connaissances actuelles"""
        known_nodes = set(user_knowledge)
        
        # Trouver les prochaines étapes possibles
        next_steps = []
        for node_id, node in self.knowledge_nodes.items():
            if node_id not in known_nodes:
                # Vérifier si les prérequis sont satisfaits
                if node.prerequisites.issubset(known_nodes):
                    next_steps.append({
                        'node_id': node_id,
                        'name': node.name,
                        'category': node.category,
                        'complexity': node.complexity,
                        'importance': node.importance,
                        'missing_prereqs': 0
                    })
                else:
                    # Calculer combien de prérequis manquent
                    missing = len(node.prerequisites - known_nodes)
                    next_steps.append({
                        'node_id': node_id,
                        'name': node.name,
                        'category': node.category,
                        'complexity': node.complexity,
                        'importance': node.importance,
                        'missing_prereqs': missing
                    })
        
        # Trier par recommandation (prérequis satisfaits d'abord, puis par importance)
        next_steps.sort(key=lambda x: (x['missing_prereqs'], -x['importance'], x['complexity']))
        
        return {
            'ready_to_learn': [s for s in next_steps if s['missing_prereqs'] == 0][:5],
            'need_prerequisites': [s for s in next_steps if s['missing_prereqs'] > 0][:5],
            'progress_percentage': len(known_nodes) / len(self.knowledge_nodes) * 100,
            'mastered_categories': self._get_mastered_categories(known_nodes)
        }
    
    def _get_mastered_categories(self, known_nodes: Set[str]) -> List[str]:
        """Détermine les catégories maîtrisées"""
        mastered = []
        
        for category, cluster in self.domain_clusters.items():
            category_nodes = set(cluster['nodes'])
            mastery_ratio = len(known_nodes & category_nodes) / len(category_nodes)
            
            if mastery_ratio >= 0.7:  # 70% de maîtrise
                mastered.append(category)
        
        return mastered
    
    def export_interactive_map(self, output_file: str = "knowledge_map.html"):
        """Exporte une carte interactive en HTML"""
        print(f" Génération de la carte interactive...")
        
        # Préparer les données pour la visualisation
        nodes_data = []
        edges_data = []
        
        # Nœuds
        for node_id, node in self.knowledge_nodes.items():
            nodes_data.append({
                'id': node_id,
                'label': node.name,
                'category': node.category,
                'type': node.type,
                'complexity': node.complexity,
                'importance': node.importance,
                'size': 10 + (node.importance * 50),  # Taille proportionnelle à l'importance
                'color': self._get_category_color(node.category)
            })
        
        # Arêtes
        for edge in self.knowledge_graph.edges():
            edges_data.append({
                'from': edge[0],
                'to': edge[1],
                'arrows': 'to'
            })
        
        # Générer le HTML avec vis.js
        html_content = self._generate_interactive_html(nodes_data, edges_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f" Carte interactive générée: {output_file}")
        return output_file
    
    def _get_category_color(self, category: str) -> str:
        """Obtient une couleur pour une catégorie"""
        colors = {
            'extract': '#FF6B6B',
            'informal': '#4ECDC4',
            'logic': '#45B7D1',
            'rhetorical': '#96CEB4',
            'orchestration': '#FFEAA7',
            'operational': '#DDA0DD',
            'tactical': '#98D8C8',
            'strategic': '#F7DC6F',
            'general': '#BDC3C7'
        }
        return colors.get(category, '#95A5A6')
    
    def _generate_interactive_html(self, nodes_data: List[Dict], edges_data: List[Dict]) -> str:
        """Génère le HTML pour la carte interactive"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Carte des Connaissances - IA Symbolique</title>
            <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                #knowledge-map {{ width: 100%; height: 600px; border: 1px solid #ddd; }}
                .controls {{ margin-bottom: 20px; }}
                .legend {{ margin-top: 20px; display: flex; flex-wrap: wrap; gap: 15px; }}
                .legend-item {{ display: flex; align-items: center; }}
                .legend-color {{ width: 20px; height: 20px; margin-right: 5px; border-radius: 3px; }}
                .info-panel {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1>🧠 Carte des Connaissances - IA Symbolique</h1>
            
            <div class="controls">
                <button onclick="fitNetwork()">🔍 Ajuster la vue</button>
                <button onclick="togglePhysics()">⚡ Activer/Désactiver la physique</button>
                <select onchange="filterByCategory(this.value)">
                    <option value="">Toutes les catégories</option>
                    <option value="extract">Extraction</option>
                    <option value="informal">Analyse Informelle</option>
                    <option value="logic">Logique Formelle</option>
                    <option value="rhetorical">Rhétorique</option>
                    <option value="orchestration">Orchestration</option>
                </select>
            </div>
            
            <div id="knowledge-map"></div>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #FF6B6B;"></div>
                    <span>Extraction</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #4ECDC4;"></div>
                    <span>Analyse Informelle</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #45B7D1;"></div>
                    <span>Logique Formelle</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #96CEB4;"></div>
                    <span>Rhétorique</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #FFEAA7;"></div>
                    <span>Orchestration</span>
                </div>
            </div>
            
            <div class="info-panel" id="info-panel">
                <h3>ℹ️ Instructions</h3>
                <ul>
                    <li><strong>Cliquez</strong> sur un nœud pour voir ses détails</li>
                    <li><strong>Faites glisser</strong> pour déplacer les nœuds</li>
                    <li><strong>Utilisez la molette</strong> pour zoomer</li>
                    <li><strong>La taille</strong> des nœuds représente leur importance</li>
                    <li><strong>Les flèches</strong> indiquent les dépendances</li>
                </ul>
            </div>
            
            <script>
                // Données des nœuds et arêtes
                const nodes = new vis.DataSet({json.dumps(nodes_data)});
                const edges = new vis.DataSet({json.dumps(edges_data)});
                
                // Configuration du réseau
                const container = document.getElementById('knowledge-map');
                const data = {{ nodes: nodes, edges: edges }};
                const options = {{
                    nodes: {{
                        shape: 'dot',
                        scaling: {{
                            min: 10,
                            max: 30
                        }},
                        font: {{
                            size: 12,
                            face: 'Arial'
                        }}
                    }},
                    edges: {{
                        width: 2,
                        color: {{inherit: 'from'}},
                        smooth: {{
                            type: 'continuous'
                        }}
                    }},
                    physics: {{
                        stabilization: {{iterations: 150}}
                    }},
                    interaction: {{
                        hover: true,
                        tooltipDelay: 200
                    }}
                }};
                
                // Créer le réseau
                const network = new vis.Network(container, data, options);
                
                // Event listeners
                network.on("selectNode", function(params) {{
                    if (params.nodes.length > 0) {{
                        const nodeId = params.nodes[0];
                        const nodeData = nodes.get(nodeId);
                        showNodeInfo(nodeData);
                    }}
                }});
                
                // Fonctions utilitaires
                function showNodeInfo(node) {{
                    const infoPanel = document.getElementById('info-panel');
                    infoPanel.innerHTML = `
                        <h3>📄 ${{node.label}}</h3>
                        <p><strong>Catégorie:</strong> ${{node.category}}</p>
                        <p><strong>Type:</strong> ${{node.type}}</p>
                        <p><strong>Complexité:</strong> ${{node.complexity}}</p>
                        <p><strong>Importance:</strong> ${{(node.importance * 100).toFixed(1)}}%</p>
                    `;
                }}
                
                function fitNetwork() {{
                    network.fit();
                }}
                
                let physicsEnabled = true;
                function togglePhysics() {{
                    physicsEnabled = !physicsEnabled;
                    network.setOptions({{physics: {{enabled: physicsEnabled}}}});
                }}
                
                function filterByCategory(category) {{
                    if (category === '') {{
                        nodes.forEach(node => {{
                            nodes.update({{id: node.id, hidden: false}});
                        }});
                    }} else {{
                        nodes.forEach(node => {{
                            const hidden = node.category !== category;
                            nodes.update({{id: node.id, hidden: hidden}});
                        }});
                    }}
                }}
            </script>
        </body>
        </html>
        """
    
    def export_knowledge_summary(self, output_file: str = "knowledge_summary.json"):
        """Exporte un résumé des connaissances"""
        summary = {
            'metadata': {
                'total_nodes': len(self.knowledge_nodes),
                'total_connections': self.knowledge_graph.number_of_edges(),
                'domain_clusters': len(self.domain_clusters)
            },
            'domain_clusters': self.domain_clusters,
            'learning_paths': self.learning_paths,
            'top_important_nodes': self._get_top_nodes_by_importance(10),
            'entry_points_by_domain': self._get_entry_points_by_domain(),
            'complexity_distribution': self._get_complexity_distribution()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        
        print(f" Résumé des connaissances exporté: {output_file}")
        return output_file
    
    def _get_top_nodes_by_importance(self, n: int) -> List[Dict]:
        """Obtient les n nœuds les plus importants"""
        sorted_nodes = sorted(
            self.knowledge_nodes.values(),
            key=lambda x: x.importance,
            reverse=True
        )
        
        return [
            {
                'id': node.id,
                'name': node.name,
                'category': node.category,
                'importance': node.importance,
                'complexity': node.complexity
            }
            for node in sorted_nodes[:n]
        ]
    
    def _get_entry_points_by_domain(self) -> Dict[str, List[str]]:
        """Obtient les points d'entrée par domaine"""
        return {
            domain: cluster['entry_points']
            for domain, cluster in self.domain_clusters.items()
        }
    
    def _get_complexity_distribution(self) -> Dict[str, int]:
        """Distribution de la complexité"""
        distribution = {'low': 0, 'medium': 0, 'high': 0}
        
        for node in self.knowledge_nodes.values():
            if node.complexity < 10:
                distribution['low'] += 1
            elif node.complexity < 25:
                distribution['medium'] += 1
            else:
                distribution['high'] += 1
        
        return distribution
    
    def _get_node_id(self, module_path: str) -> str:
        """Génère un ID de nœud à partir du chemin de module"""
        return module_path.replace('/', '_').replace('.py', '')


def main():
    """Fonction principale"""
    print(" Mappeur de Connaissances IA Symbolique")
    print("=" * 50)
    
    try:
        mapper = KnowledgeMapper()
        
        # Générer les parcours d'apprentissage
        learning_paths = mapper.generate_learning_paths()
        print(f" {len(learning_paths)} parcours d'apprentissage générés")
        
        # Exporter la carte interactive
        interactive_map = mapper.export_interactive_map()
        
        # Exporter le résumé
        summary_file = mapper.export_knowledge_summary()
        
        print(f"\n Mapping des connaissances terminé !")
        print(f" Carte interactive: {interactive_map}")
        print(f" Résumé: {summary_file}")
        
        # Afficher quelques statistiques
        print(f"\n STATISTIQUES")
        print(f" Nœuds de connaissance: {len(mapper.knowledge_nodes)}")
        print(f" Connexions: {mapper.knowledge_graph.number_of_edges()}")
        print(f" Domaines: {len(mapper.domain_clusters)}")
        
        # Afficher les parcours
        print(f"\n PARCOURS D'APPRENTISSAGE")
        for path_name, path in learning_paths.items():
            print(f"• {path_name}: {len(path)} étapes")
        
    except Exception as e:
        print(f" Erreur: {e}")
        raise


if __name__ == "__main__":
    main()