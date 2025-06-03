# -*- coding: utf-8 -*-
"""
Utilitaires pour le traitement et la manipulation des données d'analyse d'argumentation.
"""

import logging
from typing import List, Dict, Any, DefaultDict # Ajout de DefaultDict
from collections import defaultdict

logger = logging.getLogger(__name__)

def group_results_by_corpus(results: List[Dict[str, Any]]) -> DefaultDict[str, List[Dict[str, Any]]]:
    """
    Regroupe les résultats d'analyse par corpus.

    Chaque résultat d'analyse dans la liste d'entrée doit idéalement contenir
    une clé 'corpus_name' ou une clé identifiable comme 'source_name' qui peut
    être mappée à un nom de corpus. Si aucune clé de ce type n'est trouvée,
    les résultats peuvent être groupés sous une clé par défaut (par exemple, 'Unknown Corpus').

    :param results: Une liste de dictionnaires, chaque dictionnaire étant un résultat d'analyse.
                    Chaque résultat devrait avoir une clé comme 'corpus_name' ou 'source_name'.
    :type results: List[Dict[str, Any]]
    :return: Un dictionnaire où les clés sont les noms des corpus et les valeurs
             sont des listes de résultats d'analyse appartenant à ce corpus.
             Utilise defaultdict pour faciliter l'ajout d'éléments.
    :rtype: DefaultDict[str, List[Dict[str, Any]]]
    """
    logger.info(f"Regroupement de {len(results)} résultats par corpus...")
    
    grouped_results: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    for result_item in results:
        corpus_name = result_item.get("corpus_name")
        
        if not corpus_name:
            # Tenter de déduire le corpus à partir d'autres clés si 'corpus_name' est absent
            # Ceci est une heuristique et pourrait nécessiter une logique de mappage plus complexe.
            source_name = result_item.get("source_name")
            if source_name:
                # Exemple simple de mappage (à adapter/étendre)
                if "hitler" in source_name.lower():
                    corpus_name = "Discours d'Hitler"
                elif "lincoln" in source_name.lower() or "douglas" in source_name.lower():
                    corpus_name = "Débats Lincoln-Douglas"
                # Ajouter d'autres mappages si nécessaire
                else:
                    corpus_name = source_name # Utiliser source_name comme fallback si pas de mappage
            else:
                corpus_name = "Corpus Inconnu"
                logger.debug(f"Aucun 'corpus_name' ou 'source_name' trouvé pour un résultat. Assignation à '{corpus_name}'. Item: {str(result_item)[:100]}")
        
        grouped_results[corpus_name].append(result_item)

    logger.info(f"Résultats regroupés en {len(grouped_results)} corpus.")
    for corpus, items in grouped_results.items():
        logger.debug(f"Corpus '{corpus}': {len(items)} résultats.")
        
    return grouped_results

# D'autres fonctions de traitement de données pourraient être ajoutées ici,
# par exemple, filtrage, transformation, agrégation de données d'analyse.