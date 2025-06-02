#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utilitaires pour le traitement des données d'analyse d'argumentation.
"""

from typing import Dict, List, Any

def group_results_by_corpus(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Regroupe les résultats d'analyse par corpus.

    Args:
        results (List[Dict[str, Any]]): Liste des résultats d'analyse.
            Chaque résultat est un dictionnaire qui doit contenir une clé "source_name"
            indiquant le nom de la source du texte analysé.

    Returns:
        Dict[str, List[Dict[str, Any]]]: Dictionnaire des résultats regroupés par corpus.
            Les clés sont les noms des corpus (ex: "Discours d'Hitler", "Débats Lincoln-Douglas", "Autres corpus")
            et les valeurs sont des listes de résultats d'analyse correspondants.
    """
    corpus_results: Dict[str, List[Dict[str, Any]]] = {}
    
    for result in results:
        source_name = result.get("source_name", "Inconnu")
        
        # Déterminer le corpus en fonction du nom de la source
        if "Hitler" in source_name:
            corpus = "Discours d'Hitler"
        elif "Lincoln" in source_name or "Douglas" in source_name:
            corpus = "Débats Lincoln-Douglas"
        else:
            corpus = "Autres corpus"
        
        if corpus not in corpus_results:
            corpus_results[corpus] = []
        
        corpus_results[corpus].append(result)
    
    return corpus_results