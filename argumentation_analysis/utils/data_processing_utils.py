#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ce module fournit des fonctions utilitaires pour le traitement et la manipulation
des données issues de l'analyse d'argumentation. Il comprend des fonctions pour
regrouper, filtrer et transformer les résultats d'analyse afin de faciliter
leur exploitation et leur présentation.
"""

from typing import Dict, List, Any

def group_results_by_corpus(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Regroupe une liste de résultats d'analyse en fonction du corpus d'origine.

    La fonction identifie le corpus de chaque résultat en se basant sur la clé
    `source_name` présente dans chaque dictionnaire de résultat. Des corpus prédéfinis
    sont utilisés ("Discours d'Hitler", "Débats Lincoln-Douglas"), et tout autre
    résultat est classé dans "Autres corpus".

    :param results: Une liste de dictionnaires, où chaque dictionnaire représente
                    un résultat d'analyse et doit contenir une clé "source_name".
    :type results: List[Dict[str, Any]]
    :return: Un dictionnaire où les clés sont les noms des corpus et les valeurs
             sont des listes de résultats d'analyse appartenant à ce corpus.
    :rtype: Dict[str, List[Dict[str, Any]]]
    :raises TypeError: Si `results` n'est pas une liste.
    :raises KeyError: Si un dictionnaire dans `results` ne contient pas la clé "source_name"
                      (bien que géré avec `.get()` pour éviter une levée directe ici,
                       une utilisation stricte pourrait le nécessiter).
    """
    corpus_results: Dict[str, List[Dict[str, Any]]] = {}
    
    # Vérification initiale du type de l'argument d'entrée.
    if not isinstance(results, list):
        raise TypeError("L'argument 'results' doit être une liste.")

    for result in results:
        # Assurer que chaque 'result' est un dictionnaire, sinon ignorer ou lever une exception.
        if not isinstance(result, dict):
            # Optionnel: logger un avertissement ou lever une exception plus spécifique.
            # print(f"Avertissement: élément non-dictionnaire ignoré: {result}")
            continue

        source_name = result.get("source_name", "Inconnu")
        
        # Logique de classification des corpus basée sur des mots-clés dans 'source_name'.
        # Cette section pourrait être étendue ou configurée via des paramètres externes
        # pour plus de flexibilité si le nombre de corpus ou les critères de classification augmentent.
        if "Hitler" in source_name:
            corpus = "Discours d'Hitler"
        elif "Lincoln" in source_name or "Douglas" in source_name:
            corpus = "Débats Lincoln-Douglas"
        else:
            corpus = "Autres corpus"  # Catégorie par défaut pour les sources non classifiées.
        
        # Initialisation de la liste pour un nouveau corpus si non existant.
        if corpus not in corpus_results:
            corpus_results[corpus] = []
        
        corpus_results[corpus].append(result)
    
    return corpus_results