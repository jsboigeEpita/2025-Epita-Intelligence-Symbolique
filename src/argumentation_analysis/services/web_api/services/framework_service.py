#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service de construction de frameworks de Dung.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Set, Tuple

from argumentation_analysis.services.web_api.models.request_models import FrameworkRequest, Argument, FrameworkOptions
from argumentation_analysis.services.web_api.models.response_models import (
    FrameworkResponse, ArgumentNode, Extension, FrameworkVisualization
)

logger = logging.getLogger("FrameworkService")


class FrameworkService:
    """
    Service pour la construction et l'analyse de frameworks de Dung.
    
    Ce service implémente les algorithmes de base pour calculer
    les extensions selon différentes sémantiques.
    """
    
    def __init__(self):
        """Initialise le service de framework."""
        self.logger = logger
        self.is_initialized = True
        self.logger.info("Service de framework initialisé")
    
    def is_healthy(self) -> bool:
        """Vérifie l'état de santé du service."""
        return self.is_initialized
    
    def build_framework(self, request: FrameworkRequest) -> FrameworkResponse:
        """
        Construit un framework d'argumentation de Dung à partir d'une requête,
        calcule ses extensions sémantiques et génère une visualisation.

        :param request: L'objet `FrameworkRequest` contenant la liste des arguments
                        et les options de construction.
        :type request: FrameworkRequest
        :return: Un objet `FrameworkResponse` contenant le framework construit,
                 ses extensions, des statistiques et potentiellement des données
                 de visualisation.
        :rtype: FrameworkResponse
        """
        start_time = time.time()
        
        try:
            # Construction du graphe d'arguments
            argument_nodes = self._build_argument_nodes(request.arguments)
            attack_relations = self._build_attack_relations(request.arguments)
            support_relations = self._build_support_relations(request.arguments)
            
            # Calcul des extensions si demandé
            extensions = []
            if request.options and request.options.compute_extensions:
                extensions = self._compute_extensions(
                    argument_nodes, 
                    attack_relations, 
                    request.options.semantics
                )
                
                # Mise à jour du statut des arguments
                self._update_argument_status(argument_nodes, extensions)
            
            # Génération de la visualisation si demandée
            visualization = None
            if request.options and request.options.include_visualization:
                visualization = self._generate_visualization(
                    argument_nodes, attack_relations, support_relations
                )
            
            # Calcul des statistiques
            stats = self._calculate_statistics(argument_nodes, attack_relations, support_relations, extensions)
            
            processing_time = time.time() - start_time
            
            return FrameworkResponse(
                success=True,
                arguments=argument_nodes,
                attack_relations=attack_relations,
                support_relations=support_relations,
                extensions=extensions,
                semantics_used=request.options.semantics if request.options else "preferred",
                argument_count=stats['argument_count'],
                attack_count=stats['attack_count'],
                support_count=stats['support_count'],
                extension_count=stats['extension_count'],
                visualization=visualization,
                processing_time=processing_time,
                framework_options=request.options.dict() if request.options else {}
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la construction du framework: {e}")
            processing_time = time.time() - start_time
            
            return FrameworkResponse(
                success=False,
                arguments=[],
                attack_relations=[],
                support_relations=[],
                extensions=[],
                semantics_used="unknown",
                argument_count=0,
                attack_count=0,
                support_count=0,
                extension_count=0,
                visualization=None,
                processing_time=processing_time,
                framework_options=request.options.dict() if request.options else {}
            )
    
    def _build_argument_nodes(self, arguments: List[Argument]) -> List[ArgumentNode]:
        """Construit une liste d'objets `ArgumentNode` à partir de la liste d'arguments d'entrée.

        Calcule également les relations inverses (attacked_by, supported_by) pour chaque nœud.

        :param arguments: Liste des arguments d'entrée (objets `Argument`).
        :type arguments: List[Argument]
        :return: Une liste d'objets `ArgumentNode`.
        :rtype: List[ArgumentNode]
        """
        nodes = []
        
        for arg in arguments:
            # Calcul des relations inverses
            attacked_by = []
            supported_by = []
            
            for other_arg in arguments:
                if arg.id in (other_arg.attacks or []):
                    attacked_by.append(other_arg.id)
                if arg.id in (other_arg.supports or []):
                    supported_by.append(other_arg.id)
            
            node = ArgumentNode(
                id=arg.id,
                content=arg.content,
                status="undecided",
                attacks=arg.attacks or [],
                attacked_by=attacked_by,
                supports=arg.supports or [],
                supported_by=supported_by
            )
            nodes.append(node)
        
        return nodes
    
    def _build_attack_relations(self, arguments: List[Argument]) -> List[Dict[str, str]]:
        """Construit une liste de dictionnaires représentant les relations d'attaque.

        :param arguments: Liste des arguments d'entrée.
        :type arguments: List[Argument]
        :return: Une liste de dictionnaires, chaque dictionnaire représentant une attaque
                 avec les clés 'attacker', 'target', et 'type'.
        :rtype: List[Dict[str, str]]
        """
        relations = []
        
        for arg in arguments:
            for target_id in (arg.attacks or []):
                relations.append({
                    'attacker': arg.id,
                    'target': target_id,
                    'type': 'attack'
                })
        
        return relations
    
    def _build_support_relations(self, arguments: List[Argument]) -> List[Dict[str, str]]:
        """Construit une liste de dictionnaires représentant les relations de support.

        :param arguments: Liste des arguments d'entrée.
        :type arguments: List[Argument]
        :return: Une liste de dictionnaires, chaque dictionnaire représentant un support
                 avec les clés 'supporter', 'target', et 'type'.
        :rtype: List[Dict[str, str]]
        """
        relations = []
        
        for arg in arguments:
            for target_id in (arg.supports or []):
                relations.append({
                    'supporter': arg.id,
                    'target': target_id,
                    'type': 'support'
                })
        
        return relations
    
    def _compute_extensions(self, nodes: List[ArgumentNode], attacks: List[Dict[str, str]], semantics: str) -> List[Extension]:
        """Calcule les extensions sémantiques d'un framework d'argumentation.

        Route vers la méthode de calcul appropriée en fonction de la sémantique demandée.

        :param nodes: Liste des nœuds d'argument du framework.
        :type nodes: List[ArgumentNode]
        :param attacks: Liste des relations d'attaque.
        :type attacks: List[Dict[str, str]]
        :param semantics: La sémantique à utiliser pour le calcul (par exemple, "grounded", "preferred").
        :type semantics: str
        :return: Une liste d'objets `Extension`.
        :rtype: List[Extension]
        """
        try:
            if semantics == "grounded":
                return self._compute_grounded_extension(nodes, attacks)
            elif semantics == "complete":
                return self._compute_complete_extensions(nodes, attacks)
            elif semantics == "preferred":
                return self._compute_preferred_extensions(nodes, attacks)
            elif semantics == "stable":
                return self._compute_stable_extensions(nodes, attacks)
            elif semantics == "semi-stable":
                return self._compute_semi_stable_extensions(nodes, attacks)
            else:
                self.logger.warning(f"Sémantique inconnue: {semantics}")
                return []
        
        except Exception as e:
            self.logger.error(f"Erreur calcul extensions: {e}")
            return []
    
    def _compute_grounded_extension(self, nodes: List[ArgumentNode], attacks: List[Dict[str, str]]) -> List[Extension]:
        """Calcule l'extension grounded (fondée) unique d'un framework d'argumentation.

        :param nodes: Liste des nœuds d'argument.
        :type nodes: List[ArgumentNode]
        :param attacks: Liste des relations d'attaque.
        :type attacks: List[Dict[str, str]]
        :return: Une liste contenant l'unique extension grounded.
        :rtype: List[Extension]
        """
        # Construction du graphe d'attaque
        attack_graph = self._build_attack_graph(nodes, attacks)
        
        # Algorithme de l'extension grounded
        in_set = set()
        out_set = set()
        undecided = {node.id for node in nodes}
        
        changed = True
        while changed:
            changed = False
            
            # Arguments sans attaquants -> IN
            for arg_id in list(undecided):
                attackers = attack_graph.get(arg_id, set())
                if not attackers or attackers.issubset(out_set):
                    in_set.add(arg_id)
                    undecided.remove(arg_id)
                    changed = True
            
            # Arguments attaqués par IN -> OUT
            for arg_id in list(undecided):
                attackers = attack_graph.get(arg_id, set())
                if attackers.intersection(in_set):
                    out_set.add(arg_id)
                    undecided.remove(arg_id)
                    changed = True
        
        return [Extension(
            type="grounded",
            arguments=list(in_set),
            is_complete=True,
            is_preferred=True
        )]
    
    def _compute_complete_extensions(self, nodes: List[ArgumentNode], attacks: List[Dict[str, str]]) -> List[Extension]:
        """Calcule toutes les extensions complètes d'un framework d'argumentation.
        (Implémentation simplifiée/heuristique actuelle).

        :param nodes: Liste des nœuds d'argument.
        :type nodes: List[ArgumentNode]
        :param attacks: Liste des relations d'attaque.
        :type attacks: List[Dict[str, str]]
        :return: Une liste d'objets `Extension` représentant les extensions complètes.
        :rtype: List[Extension]
        """
        attack_graph = self._build_attack_graph(nodes, attacks)
        all_args = {node.id for node in nodes}
        
        # Génération de tous les sous-ensembles possibles
        extensions = []
        
        # Pour simplifier, on utilise une approche heuristique
        # Dans un vrai système, il faudrait implémenter l'algorithme complet
        
        # Extension vide (toujours complète)
        if self._is_complete_extension(set(), attack_graph, all_args):
            extensions.append(Extension(
                type="complete",
                arguments=[],
                is_complete=True,
                is_preferred=False
            ))
        
        # Extension grounded
        grounded = self._compute_grounded_extension(nodes, attacks)
        if grounded:
            extensions.append(Extension(
                type="complete",
                arguments=grounded[0].arguments,
                is_complete=True,
                is_preferred=len(grounded[0].arguments) > 0
            ))
        
        return extensions
    
    def _compute_preferred_extensions(self, nodes: List[ArgumentNode], attacks: List[Dict[str, str]]) -> List[Extension]:
        """Calcule les extensions préférées d'un framework d'argumentation.
        (Implémentation simplifiée actuelle : retourne l'extension grounded).

        :param nodes: Liste des nœuds d'argument.
        :type nodes: List[ArgumentNode]
        :param attacks: Liste des relations d'attaque.
        :type attacks: List[Dict[str, str]]
        :return: Une liste d'objets `Extension` représentant les extensions préférées.
        :rtype: List[Extension]
        """
        # Pour simplifier, on retourne l'extension grounded comme préférée
        grounded = self._compute_grounded_extension(nodes, attacks)
        
        if grounded:
            return [Extension(
                type="preferred",
                arguments=grounded[0].arguments,
                is_complete=True,
                is_preferred=True
            )]
        
        return []
    
    def _compute_stable_extensions(self, nodes: List[ArgumentNode], attacks: List[Dict[str, str]]) -> List[Extension]:
        """Calcule les extensions stables d'un framework d'argumentation.
        (Implémentation simplifiée actuelle : vérifie si l'extension grounded est stable).

        :param nodes: Liste des nœuds d'argument.
        :type nodes: List[ArgumentNode]
        :param attacks: Liste des relations d'attaque.
        :type attacks: List[Dict[str, str]]
        :return: Une liste d'objets `Extension` représentant les extensions stables.
        :rtype: List[Extension]
        """
        attack_graph = self._build_attack_graph(nodes, attacks)
        all_args = {node.id for node in nodes}
        
        # Une extension stable attaque tous les arguments qu'elle ne contient pas
        extensions = []
        
        # Vérification de l'extension grounded
        grounded = self._compute_grounded_extension(nodes, attacks)
        if grounded and grounded[0].arguments:
            in_set = set(grounded[0].arguments)
            out_set = all_args - in_set
            
            # Vérifier si tous les arguments OUT sont attaqués par IN
            is_stable = True
            for out_arg in out_set:
                attackers = attack_graph.get(out_arg, set())
                if not attackers.intersection(in_set):
                    is_stable = False
                    break
            
            if is_stable:
                extensions.append(Extension(
                    type="stable",
                    arguments=list(in_set),
                    is_complete=True,
                    is_preferred=True
                ))
        
        return extensions
    
    def _compute_semi_stable_extensions(self, nodes: List[ArgumentNode], attacks: List[Dict[str, str]]) -> List[Extension]:
        """Calcule les extensions semi-stables d'un framework d'argumentation.
        (Implémentation simplifiée actuelle : retourne les extensions préférées).

        :param nodes: Liste des nœuds d'argument.
        :type nodes: List[ArgumentNode]
        :param attacks: Liste des relations d'attaque.
        :type attacks: List[Dict[str, str]]
        :return: Une liste d'objets `Extension` représentant les extensions semi-stables.
        :rtype: List[Extension]
        """
        # Pour simplifier, on retourne les extensions préférées
        return self._compute_preferred_extensions(nodes, attacks)
    
    def _build_attack_graph(self, nodes: List[ArgumentNode], attacks: List[Dict[str, str]]) -> Dict[str, Set[str]]:
        """Construit une représentation du graphe d'attaque.

        :param nodes: Liste des nœuds d'argument.
        :type nodes: List[ArgumentNode]
        :param attacks: Liste des relations d'attaque.
        :type attacks: List[Dict[str, str]]
        :return: Un dictionnaire où les clés sont les IDs des arguments cibles
                 et les valeurs sont des ensembles d'IDs des arguments attaquants.
        :rtype: Dict[str, Set[str]]
        """
        graph = {node.id: set() for node in nodes}
        
        for attack in attacks:
            target = attack['target']
            attacker = attack['attacker']
            if target in graph:
                graph[target].add(attacker)
        
        return graph
    
    def _is_complete_extension(self, extension: Set[str], attack_graph: Dict[str, Set[str]], all_args: Set[str]) -> bool:
        """Vérifie si un ensemble d'arguments donné est une extension complète.
        (Implémentation simplifiée actuelle : vérifie uniquement l'absence de conflit).

        Une extension complète doit être sans conflit, défendre tous ses arguments,
        et contenir tous les arguments qu'elle défend.

        :param extension: L'ensemble d'IDs d'arguments à vérifier.
        :type extension: Set[str]
        :param attack_graph: Le graphe d'attaque.
        :type attack_graph: Dict[str, Set[str]]
        :param all_args: L'ensemble de tous les IDs d'arguments dans le framework.
        :type all_args: Set[str]
        :return: True si l'ensemble est (partiellement) considéré comme complet, False sinon.
        :rtype: bool
        """
        # Un ensemble S est complet si :
        # 1. S est sans conflit (conflict-free)
        # 2. S défend tous ses éléments
        # 3. S contient tous les arguments qu'il défend
        
        # Vérification sans conflit
        for arg in extension:
            attackers = attack_graph.get(arg, set())
            if attackers.intersection(extension):
                return False
        
        # Vérification défense (simplifié)
        return True
    
    def _update_argument_status(self, nodes: List[ArgumentNode], extensions: List[Extension]) -> None:
        """Met à jour le statut ('accepted', 'rejected', 'undecided') de chaque nœud d'argument
        en fonction des extensions calculées (principalement les extensions préférées).

        :param nodes: La liste des `ArgumentNode` à mettre à jour.
        :type nodes: List[ArgumentNode]
        :param extensions: La liste des `Extension` calculées.
        :type extensions: List[Extension]
        :return: None
        :rtype: None
        """
        # Collecte des arguments dans les extensions
        in_args = set()
        for ext in extensions:
            if ext.is_preferred:
                in_args.update(ext.arguments)
        
        # Mise à jour du statut
        for node in nodes:
            if node.id in in_args:
                node.status = "accepted"
            elif any(node.id in ext.arguments for ext in extensions):
                node.status = "undecided"
            else:
                node.status = "rejected"
    
    def _generate_visualization(self, nodes: List[ArgumentNode], attacks: List[Dict[str, str]], supports: List[Dict[str, str]]) -> FrameworkVisualization:
        """Génère les données structurées pour la visualisation du framework.

        Crée des listes de nœuds et d'arêtes formatées pour être utilisées
        par une bibliothèque de visualisation graphique.

        :param nodes: Liste des `ArgumentNode` du framework.
        :type nodes: List[ArgumentNode]
        :param attacks: Liste des relations d'attaque.
        :type attacks: List[Dict[str, str]]
        :param supports: Liste des relations de support.
        :type supports: List[Dict[str, str]]
        :return: Un objet `FrameworkVisualization` contenant les listes de nœuds et d'arêtes.
        :rtype: FrameworkVisualization
        """
        # Nœuds pour la visualisation
        vis_nodes = []
        for i, node in enumerate(nodes):
            vis_nodes.append({
                'id': node.id,
                'label': node.content[:30] + "..." if len(node.content) > 30 else node.content,
                'status': node.status,
                'x': (i % 5) * 100,  # Layout simple en grille
                'y': (i // 5) * 100,
                'color': self._get_node_color(node.status)
            })
        
        # Arêtes pour la visualisation
        vis_edges = []
        
        # Attaques
        for attack in attacks:
            vis_edges.append({
                'from': attack['attacker'],
                'to': attack['target'],
                'type': 'attack',
                'color': 'red',
                'arrows': 'to'
            })
        
        # Supports
        for support in supports:
            vis_edges.append({
                'from': support['supporter'],
                'to': support['target'],
                'type': 'support',
                'color': 'green',
                'arrows': 'to'
            })
        
        return FrameworkVisualization(
            nodes=vis_nodes,
            edges=vis_edges,
            layout={
                'type': 'grid',
                'spacing': 100
            }
        )
    
    def _get_node_color(self, status: str) -> str:
        """Retourne un code couleur hexadécimal basé sur le statut d'un argument.

        :param status: Le statut de l'argument ('accepted', 'rejected', 'undecided').
        :type status: str
        :return: Un code couleur hexadécimal.
        :rtype: str
        """
        colors = {
            'accepted': '#4CAF50',    # Vert
            'rejected': '#F44336',    # Rouge
            'undecided': '#FF9800'    # Orange
        }
        return colors.get(status, '#9E9E9E')  # Gris par défaut
    
    def _calculate_statistics(self, nodes: List[ArgumentNode], attacks: List[Dict[str, str]], supports: List[Dict[str, str]], extensions: List[Extension]) -> Dict[str, int]:
        """Calcule des statistiques de base sur le framework.

        :param nodes: Liste des nœuds d'argument.
        :type nodes: List[ArgumentNode]
        :param attacks: Liste des relations d'attaque.
        :type attacks: List[Dict[str, str]]
        :param supports: Liste des relations de support.
        :type supports: List[Dict[str, str]]
        :param extensions: Liste des extensions calculées.
        :type extensions: List[Extension]
        :return: Un dictionnaire contenant le nombre d'arguments, d'attaques,
                 de supports et d'extensions.
        :rtype: Dict[str, int]
        """
        return {
            'argument_count': len(nodes),
            'attack_count': len(attacks),
            'support_count': len(supports),
            'extension_count': len(extensions)
        }
    
    def get_supported_semantics(self) -> List[str]:
        """Retourne la liste des noms des sémantiques d'argumentation supportées.

        :return: Une liste de chaînes de caractères représentant les sémantiques.
        :rtype: List[str]
        """
        return ['grounded', 'complete', 'preferred', 'stable', 'semi-stable']
    
    def validate_framework(self, arguments: List[Argument]) -> Dict[str, Any]:
        """Valide la structure d'un framework d'argumentation.

        Vérifie la présence de cycles, d'arguments isolés et la cohérence de base.

        :param arguments: La liste des arguments (objets `Argument`) du framework.
        :type arguments: List[Argument]
        :return: Un dictionnaire contenant un booléen `is_valid`, une liste `issues`
                 (problèmes bloquants) et une liste `warnings` (problèmes non bloquants).
        :rtype: Dict[str, Any]
        """
        issues = []
        warnings = []
        
        # Vérification des cycles
        if self._has_cycles(arguments):
            warnings.append("Le framework contient des cycles d'attaque")
        
        # Vérification des arguments isolés
        isolated = self._find_isolated_arguments(arguments)
        if isolated:
            warnings.append(f"Arguments isolés détectés: {', '.join(isolated)}")
        
        # Vérification de la cohérence
        if not self._is_coherent(arguments):
            issues.append("Incohérence détectée dans les relations")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def _has_cycles(self, arguments: List[Argument]) -> bool:
        """Détecte la présence de cycles dans les relations d'attaque du framework.

        Utilise un algorithme de parcours en profondeur (DFS).

        :param arguments: Liste des arguments du framework.
        :type arguments: List[Argument]
        :return: True si un cycle est détecté, False sinon.
        :rtype: bool
        """
        # Implémentation simplifiée
        graph = {}
        for arg in arguments:
            graph[arg.id] = arg.attacks or []
        
        # DFS pour détecter les cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle_util(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle_util(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for arg_id in graph:
            if arg_id not in visited:
                if has_cycle_util(arg_id):
                    return True
        
        return False
    
    def _find_isolated_arguments(self, arguments: List[Argument]) -> List[str]:
        """Trouve les arguments qui n'ont aucune relation d'attaque ou de support
        (ni en tant que source, ni en tant que cible).

        :param arguments: Liste des arguments du framework.
        :type arguments: List[Argument]
        :return: Une liste d'IDs des arguments isolés.
        :rtype: List[str]
        """
        isolated = []
        all_ids = {arg.id for arg in arguments}
        
        for arg in arguments:
            has_relations = bool(arg.attacks or arg.supports)
            is_targeted = any(
                arg.id in (other.attacks or []) or arg.id in (other.supports or [])
                for other in arguments if other.id != arg.id
            )
            
            if not has_relations and not is_targeted:
                isolated.append(arg.id)
        
        return isolated
    
    def _is_coherent(self, arguments: List[Argument]) -> bool:
        """Vérifie la cohérence de base du framework (par exemple, pas d'auto-attaque/support).

        :param arguments: Liste des arguments du framework.
        :type arguments: List[Argument]
        :return: True si le framework est considéré comme cohérent (selon les règles de base),
                 False sinon.
        :rtype: bool
        """
        # Vérification basique : pas d'auto-attaque
        for arg in arguments:
            if arg.id in (arg.attacks or []) or arg.id in (arg.supports or []):
                return False
        
        return True