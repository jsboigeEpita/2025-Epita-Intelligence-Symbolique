# argumentation_analysis/analytics/stats_calculator.py
from typing import Dict, List, Any, Tuple

def calculate_average_scores(grouped_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, float]]:
    """
    Calcule les scores moyens pour chaque corpus à partir des résultats groupés.

    Cette fonction prend un dictionnaire de résultats groupés par corpus et calcule
    les scores moyens pour différentes métriques (par exemple, score de confiance,
    richesse contextuelle, etc.) pour chaque corpus.

    Args:
        grouped_results: Un dictionnaire où les clés sont les noms des corpus (chaînes de caractères)
                         et les valeurs sont des listes de dictionnaires. Chaque dictionnaire
                         dans la liste représente un résultat d'analyse pour un extrait
                         et peut contenir diverses métriques et scores.
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

    Returns:
        Un dictionnaire où les clés sont les noms des corpus et les valeurs sont
        des dictionnaires contenant les scores moyens calculés pour ce corpus.
        Les clés internes du dictionnaire de scores moyens dépendront des métriques
        présentes dans les données d'entrée et seront préfixées par "average_".
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
    """
    average_scores_by_corpus: Dict[str, Dict[str, float]] = {}

    for corpus_name, results_list in grouped_results.items():
        if not results_list:
            average_scores_by_corpus[corpus_name] = {}
            continue
        
        score_sums: Dict[str, float] = {}
        score_counts: Dict[str, int] = {}

        for result_item in results_list:
            for key, value in result_item.items():
                if isinstance(value, (int, float)): # On ne moyenne que les nombres
                    score_sums[key] = score_sums.get(key, 0.0) + float(value)
                    score_counts[key] = score_counts.get(key, 0) + 1
        
        corpus_averages: Dict[str, float] = {}
        for score_name, total_sum in score_sums.items():
            count = score_counts.get(score_name, 0)
            if count > 0:
                corpus_averages[f"average_{score_name}"] = total_sum / count
            else:
                # Si pour une raison quelconque un score a été compté mais la somme est 0 et le compte est 0 (improbable ici)
                # ou si on veut gérer le cas où un score_name existe dans score_sums mais pas score_counts (aussi improbable)
                corpus_averages[f"average_{score_name}"] = 0.0 

        average_scores_by_corpus[corpus_name] = corpus_averages

    return average_scores_by_corpus