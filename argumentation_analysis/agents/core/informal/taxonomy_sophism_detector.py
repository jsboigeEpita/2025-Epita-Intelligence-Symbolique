#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Détecteur de sophismes unifié utilisant la vraie taxonomie.

Ce module implémente un mécanisme unifié de détection de sophismes qui :
- S'appuie sur la taxonomie réelle (400+ sophismes) 
- Utilise les clés de la taxonomie pour désigner les sophismes
- Présente les branches principales puis approfondit au bon niveau de spécificité
- Remplace les mécanismes éparpillés et les mocks
"""

import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Import de l'InformalAnalysisPlugin pour accéder à la taxonomie
from .informal_definitions import InformalAnalysisPlugin

logger = logging.getLogger("TaxonomySophismDetector")


class TaxonomySophismDetector:
    """
    Détecteur de sophismes unifié utilisant la vraie taxonomie.
    
    Cette classe centralise toute la logique de détection de sophismes
    en utilisant la taxonomie réelle au lieu des mocks éparpillés.
    """
    
    def __init__(self, taxonomy_file_path: Optional[str] = None):
        """
        Initialise le détecteur avec accès à la taxonomie.
        
        :param taxonomy_file_path: Chemin optionnel vers le fichier CSV de taxonomie
        """
        self.logger = logging.getLogger("TaxonomySophismDetector")
        self.plugin = InformalAnalysisPlugin(taxonomy_file_path=taxonomy_file_path)
        self._taxonomy_cache = None
        
    def _get_taxonomy_df(self) -> pd.DataFrame:
        """Récupère le DataFrame de taxonomie avec cache."""
        if self._taxonomy_cache is None:
            self._taxonomy_cache = self.plugin._get_taxonomy_dataframe()
        return self._taxonomy_cache
    
    def get_main_branches(self) -> List[Dict[str, Any]]:
        """
        Récupère les branches principales de la taxonomie (niveau 0/1).
        
        :return: Liste des branches principales avec leurs clés taxonomiques
        """
        try:
            df = self._get_taxonomy_df()
            
            # Trouver les nœuds racines (depth=0 ou depth=1)
            main_branches = df[df['depth'].isin([0, 1])].copy()
            
            branches = []
            for _, row in main_branches.iterrows():
                branch = {
                    'taxonomy_key': int(row.name),  # PK
                    'name': row.get('Name', ''),
                    'nom_vulgarise': row.get('nom_vulgarisé', ''),
                    'famille': row.get('Famille', ''),
                    'description_courte': row.get('text_fr', ''),
                    'depth': int(row.get('depth', 0)),
                    'path': row.get('path', '')
                }
                branches.append(branch)
            
            self.logger.info(f"Branches principales récupérées: {len(branches)}")
            return branches
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des branches principales: {e}")
            return []
    
    def explore_branch(self, taxonomy_key: int, max_depth: int = 3) -> Dict[str, Any]:
        """
        Explore une branche de la taxonomie pour approfondir la spécificité.
        
        :param taxonomy_key: Clé taxonomique de la branche à explorer
        :param max_depth: Profondeur maximale d'exploration
        :return: Structure hiérarchique de la branche
        """
        try:
            # Utiliser la méthode du plugin pour explorer la hiérarchie
            result = self.plugin._internal_explore_hierarchy(
                current_pk=taxonomy_key,
                df=self._get_taxonomy_df(),
                max_children=20
            )
            
            if result.get('error'):
                self.logger.warning(f"Erreur d'exploration pour la clé {taxonomy_key}: {result['error']}")
                return result
            
            # Enrichir avec les sous-branches si nécessaire
            if result.get('children') and max_depth > 1:
                for child in result['children']:
                    child_key = child.get('pk')
                    if child_key:
                        child['sub_branches'] = self.explore_branch(child_key, max_depth - 1)
            
            self.logger.debug(f"Branche {taxonomy_key} explorée avec {len(result.get('children', []))} enfants")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exploration de la branche {taxonomy_key}: {e}")
            return {
                'current_node': None,
                'children': [],
                'error': f"Erreur d'exploration: {e}"
            }
    
    def detect_sophisms_from_taxonomy(self, text: str, max_sophisms: int = 10) -> List[Dict[str, Any]]:
        """
        Détecte les sophismes dans un texte en utilisant la taxonomie.
        
        Méthode principale qui remplace tous les détecteurs éparpillés.
        
        :param text: Texte à analyser
        :param max_sophisms: Nombre maximum de sophismes à détecter
        :return: Liste des sophismes détectés avec leurs clés taxonomiques
        """
        detected_sophisms = []
        
        try:
            df = self._get_taxonomy_df()
            text_lower = text.lower()
            
            # 1. Analyse lexicale basée sur les noms et descriptions
            for pk, row in df.iterrows():
                confidence = 0.0
                matches = []
                
                # Vérifier les correspondances avec les noms
                name = str(row.get('Name', '')).lower()
                nom_vulgarise = str(row.get('nom_vulgarisé', '')).lower()
                description = str(row.get('text_fr', '')).lower()
                
                # Correspondance avec le nom vulgarisé (plus probable)
                if nom_vulgarise and nom_vulgarise in text_lower:
                    confidence += 0.7
                    matches.append(f"Nom vulgarisé: '{nom_vulgarise}'")
                
                # Correspondance avec le nom officiel
                if name and name in text_lower:
                    confidence += 0.5
                    matches.append(f"Nom officiel: '{name}'")
                
                # Correspondance avec des mots-clés de la description
                if description:
                    desc_words = [w for w in description.split() if len(w) > 4]
                    for word in desc_words[:5]:  # Limiter aux 5 premiers mots significatifs
                        if word in text_lower:
                            confidence += 0.1
                            matches.append(f"Mot-clé: '{word}'")
                
                # Si on a des correspondances significatives
                if confidence >= 0.3:
                    sophism = {
                        'taxonomy_key': int(pk),
                        'name': row.get('Name', ''),
                        'nom_vulgarise': row.get('nom_vulgarisé', ''),
                        'famille': row.get('Famille', ''),
                        'description': row.get('text_fr', ''),
                        'confidence': min(confidence, 1.0),
                        'matches': matches,
                        'depth': int(row.get('depth', 0)),
                        'path': row.get('path', ''),
                        'detection_method': 'taxonomy_lexical'
                    }
                    detected_sophisms.append(sophism)
            
            # 2. Trier par confiance et limiter
            detected_sophisms.sort(key=lambda x: x['confidence'], reverse=True)
            detected_sophisms = detected_sophisms[:max_sophisms]
            
            # 3. Enrichir avec le contexte taxonomique
            for sophism in detected_sophisms:
                taxonomy_key = sophism['taxonomy_key']
                
                # Ajouter les détails de la branche
                branch_details = self.explore_branch(taxonomy_key, max_depth=2)
                sophism['branch_context'] = branch_details
                
                # Ajouter les sophismes apparentés (frères/sœurs)
                parent_context = self._get_parent_context(taxonomy_key)
                sophism['related_sophisms'] = parent_context.get('siblings', [])
            
            self.logger.info(f"Détection terminée: {len(detected_sophisms)} sophismes trouvés")
            return detected_sophisms
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la détection de sophismes: {e}")
            return []
    
    def _get_parent_context(self, taxonomy_key: int) -> Dict[str, Any]:
        """
        Récupère le contexte parent d'un sophisme (frères/sœurs).
        
        :param taxonomy_key: Clé taxonomique du sophisme
        :return: Contexte parent avec les sophismes apparentés
        """
        try:
            df = self._get_taxonomy_df()
            
            if taxonomy_key not in df.index:
                return {'siblings': []}
            
            current_row = df.loc[taxonomy_key]
            current_path = current_row.get('path', '')
            
            if not current_path:
                return {'siblings': []}
            
            # Trouver le path parent
            path_parts = str(current_path).split('.')
            if len(path_parts) <= 1:
                return {'siblings': []}
            
            parent_path = '.'.join(path_parts[:-1])
            
            # Trouver les frères/sœurs (même parent)
            siblings = df[df['path'].astype(str).str.startswith(parent_path + '.', na=False)]
            siblings = siblings[siblings.index != taxonomy_key]  # Exclure soi-même
            
            siblings_list = []
            for _, sibling in siblings.iterrows():
                sibling_info = {
                    'taxonomy_key': int(sibling.name),
                    'name': sibling.get('Name', ''),
                    'nom_vulgarise': sibling.get('nom_vulgarisé', ''),
                    'description_courte': sibling.get('text_fr', '')
                }
                siblings_list.append(sibling_info)
            
            return {
                'parent_path': parent_path,
                'siblings': siblings_list[:5]  # Limiter à 5 frères/sœurs
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du contexte parent: {e}")
            return {'siblings': []}
    
    def get_sophism_details_by_key(self, taxonomy_key: int) -> Dict[str, Any]:
        """
        Récupère les détails complets d'un sophisme par sa clé taxonomique.
        
        :param taxonomy_key: Clé taxonomique du sophisme
        :return: Détails complets du sophisme
        """
        try:
            result = self.plugin._internal_get_node_details(
                pk=taxonomy_key,
                df=self._get_taxonomy_df()
            )
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des détails pour la clé {taxonomy_key}: {e}")
            return {'error': f"Erreur: {e}"}
    
    def search_sophisms_by_pattern(self, pattern: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Recherche des sophismes par motif dans les noms et descriptions.
        
        :param pattern: Motif à rechercher
        :param max_results: Nombre maximum de résultats
        :return: Liste des sophismes correspondants
        """
        try:
            df = self._get_taxonomy_df()
            pattern_lower = pattern.lower()
            
            matching_sophisms = []
            
            for pk, row in df.iterrows():
                score = 0.0
                
                # Recherche dans les différents champs
                name = str(row.get('Name', '')).lower()
                nom_vulgarise = str(row.get('nom_vulgarisé', '')).lower()
                description = str(row.get('text_fr', '')).lower()
                famille = str(row.get('Famille', '')).lower()
                
                if pattern_lower in nom_vulgarise:
                    score += 0.8
                if pattern_lower in name:
                    score += 0.6
                if pattern_lower in description:
                    score += 0.4
                if pattern_lower in famille:
                    score += 0.3
                
                if score > 0:
                    sophism = {
                        'taxonomy_key': int(pk),
                        'name': row.get('Name', ''),
                        'nom_vulgarise': row.get('nom_vulgarisé', ''),
                        'famille': row.get('Famille', ''),
                        'description': row.get('text_fr', ''),
                        'match_score': score,
                        'depth': int(row.get('depth', 0)),
                        'path': row.get('path', '')
                    }
                    matching_sophisms.append(sophism)
            
            # Trier par score et limiter
            matching_sophisms.sort(key=lambda x: x['match_score'], reverse=True)
            return matching_sophisms[:max_results]
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche par motif: {e}")
            return []


def create_unified_detector(taxonomy_file_path: Optional[str] = None) -> TaxonomySophismDetector:
    """
    Factory function pour créer le détecteur unifié.
    
    :param taxonomy_file_path: Chemin optionnel vers le fichier de taxonomie
    :return: Instance du détecteur unifié
    """
    return TaxonomySophismDetector(taxonomy_file_path=taxonomy_file_path)


# Instance globale pour l'utilisation dans l'agent informel
_global_detector = None

def get_global_detector(taxonomy_file_path: Optional[str] = None) -> TaxonomySophismDetector:
    """
    Récupère l'instance globale du détecteur (singleton pattern).
    
    :param taxonomy_file_path: Chemin optionnel vers le fichier de taxonomie
    :return: Instance globale du détecteur
    """
    global _global_detector
    if _global_detector is None:
        _global_detector = TaxonomySophismDetector(taxonomy_file_path=taxonomy_file_path)
    return _global_detector