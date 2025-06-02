# argumentation_analysis/analytics/stats_calculator.py
"""
Ce module fournit des fonctions pour calculer des statistiques descriptives
sur les résultats d'analyse d'argumentation. Il est conçu pour être utilisé
dans le cadre du projet d'analyse d'argumentation afin de quantifier
divers aspects des arguments analysés, tels que les scores de confiance moyens,
la richesse contextuelle, etc., regroupés par corpus ou autres critères.
"""
from typing import Dict, List, Any, Tuple

def calculate_average_scores(grouped_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, float]]:
    """
    Calcule les scores moyens pour chaque corpus à partir des résultats groupés.

    Cette fonction prend un dictionnaire de résultats groupés par corpus et calcule
    les scores moyens pour différentes métriques (par exemple, score de confiance,
    richesse contextuelle, etc.) pour chaque corpus. Les scores non numériques
    sont ignorés.

    :param grouped_results: Un dictionnaire où les clés sont les noms des corpus
                            et les valeurs sont des listes de dictionnaires.
                            Chaque dictionnaire dans la liste représente un
                            résultat d'analyse pour un extrait et peut contenir
                            diverses métriques et scores.
                            Exemple:
                            {
                                "CorpusA": [
                                    {"id": "doc1", "confidence_score": 0.8, "richness_score": 0.9},
                                    {"id": "doc2", "confidence_score": 0.7, "richness_score": 0.85},
                                ],
                                "CorpusB": [
                                    {"id": "doc3", "confidence_score": 0.9, "richness_score": 0.95},
                                ]
                            }
    :type grouped_results: Dict[str, List[Dict[str, Any]]]
    :return: Un dictionnaire où les clés sont les noms des corpus et les valeurs sont
             des dictionnaires contenant les scores moyens calculés pour ce corpus.
             Les clés internes du dictionnaire de scores moyens dépendront des métriques
             numériques présentes dans les données d'entrée et seront préfixées par "average_".
             Si un corpus n'a aucun résultat ou aucun score numérique, son dictionnaire
             de moyennes sera vide.
             Exemple de retour:
             {
                 "CorpusA": {
                     "average_confidence_score": 0.75,
                     "average_richness_score": 0.875
                 },
                 "CorpusB": {
                     "average_confidence_score": 0.9,
                     "average_richness_score": 0.95
                 }
             }
    :rtype: Dict[str, Dict[str, float]]
    :raises TypeError: Si `grouped_results` n'est pas un dictionnaire ou si les
                       valeurs ne sont pas des listes de dictionnaires comme attendu.
                       (Note: la gestion explicite des erreurs n'est pas implémentée
                       dans cette version, mais des erreurs de type peuvent survenir
                       avec des entrées malformées.)
    """
    average_scores_by_corpus: Dict[str, Dict[str, float]] = {}

    # Itération sur chaque corpus fourni dans les résultats groupés
    for corpus_name, results_list in grouped_results.items():
        if not results_list:
            # Si un corpus n'a pas de résultats, on lui assigne un dictionnaire vide de moyennes
            average_scores_by_corpus[corpus_name] = {}
            continue
        
        score_sums: Dict[str, float] = {} # Pour stocker la somme des scores pour chaque métrique
        score_counts: Dict[str, int] = {} # Pour compter le nombre d'occurrences de chaque métrique

        # Itération sur chaque élément de résultat (par exemple, analyse d'un document) dans le corpus
        for result_item in results_list:
            for key, value in result_item.items():
                # On ne calcule la moyenne que pour les valeurs numériques (int ou float)
                if isinstance(value, (int, float)):
                    score_sums[key] = score_sums.get(key, 0.0) + float(value)
                    score_counts[key] = score_counts.get(key, 0) + 1
        
        corpus_averages: Dict[str, float] = {}
        # Calcul de la moyenne pour chaque métrique collectée
        for score_name, total_sum in score_sums.items():
            count = score_counts.get(score_name, 0)
            if count > 0:
                corpus_averages[f"average_{score_name}"] = total_sum / count
            else:
                # Ce cas est peu probable si score_name est dans score_sums,
                # car cela implique qu'il a été compté au moins une fois.
                # Cependant, par sécurité, on assigne 0.0 si le compte est nul.
                corpus_averages[f"average_{score_name}"] = 0.0

        average_scores_by_corpus[corpus_name] = corpus_averages

    return average_scores_by_corpus