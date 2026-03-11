# -*- coding: utf-8 -*-
"""
Ce module fournit des fonctions pour simuler la génération de résultats d'analyse rhétorique.
Utilisé pour les tests, les démonstrations, ou lorsque les vrais moteurs d'analyse ne sont pas disponibles.
"""

import logging
import random
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

MOCK_FALLACY_TYPES = [
    "Ad Hominem (Mock)",
    "Homme de Paille (Mock)",
    "Fausse Dichotomie (Mock)",
    "Appel à l'Ignorance (Mock)",
    "Pente Glissante (Mock)",
    "Généralisation Hâtive (Mock)",
]

MOCK_RHETORICAL_DEVICES = [
    "Métaphore (Mock)",
    "Anaphore (Mock)",
    "Question Rhétorique (Mock)",
    "Hyperbole (Mock)",
    "Ironie (Mock)",
]


def generate_mock_fallacy_detection(
    text_snippet: str, num_fallacies: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Génère une liste simulée de sophismes détectés pour un extrait de texte.

    :param text_snippet: Un aperçu du texte pour lequel simuler la détection.
    :type text_snippet: str
    :param num_fallacies: Nombre de sophismes à simuler. Si None, un nombre aléatoire (0-3) sera choisi.
    :type num_fallacies: Optional[int]
    :return: Une liste de dictionnaires, chaque dictionnaire représentant un sophisme simulé.
    :rtype: List[Dict[str, Any]]
    """
    if num_fallacies is None:
        num_to_generate = random.randint(0, 3)
    else:
        num_to_generate = num_fallacies

    detected_fallacies = []
    if (
        not text_snippet
    ):  # Si le texte est vide, ne pas générer de sophisme basé sur le contexte.
        snippet_for_context = "Contexte non disponible car texte d'entrée vide."
    else:
        snippet_for_context = (
            text_snippet[:100] + "..." if len(text_snippet) > 100 else text_snippet
        )

    for i in range(num_to_generate):
        fallacy_type = random.choice(MOCK_FALLACY_TYPES)
        detected_fallacies.append(
            {
                "fallacy_type": fallacy_type,
                "description": f"Description simulée pour {fallacy_type}.",
                "severity": random.choice(["Basse", "Moyenne", "Haute"]) + " (Mock)",
                "confidence": round(random.uniform(0.5, 0.95), 2),
                "context_text": f"Sophisme simulé '{fallacy_type}' trouvé près de : \"{snippet_for_context}\"",
                "start_char": random.randint(
                    0, max(0, len(text_snippet) - 20)
                ),  # Position de début simulée
                "end_char": random.randint(
                    10, max(10, len(text_snippet))
                ),  # Position de fin simulée
            }
        )
    logger.debug(
        f"Simulation de {len(detected_fallacies)} sophismes pour le texte (aperçu): '{snippet_for_context}'"
    )
    return detected_fallacies


def generate_mock_coherence_evaluation(text_snippet: str) -> Dict[str, Any]:
    """
    Génère une évaluation simulée de la cohérence pour un extrait de texte.

    :param text_snippet: Un aperçu du texte.
    :type text_snippet: str
    :return: Un dictionnaire contenant les scores de cohérence simulés.
    :rtype: Dict[str, Any]
    """
    score = round(random.uniform(0.4, 0.9), 2)
    evaluation = {
        "coherence_score": score,
        "assessment": f"La cohérence du texte (aperçu: '{text_snippet[:50]}...') est évaluée à {score} (Mock).",
        "potential_issues": [],
    }
    if score < 0.6:
        evaluation["potential_issues"].append(
            "Possibles ruptures de cohérence ou transitions abruptes (Mock)."
        )
    logger.debug(f"Simulation de l'évaluation de cohérence: score {score}")
    return evaluation


def generate_mock_rhetorical_analysis(
    text_snippet: str, extract_name: str, source_name: str
) -> Dict[str, Any]:
    """
    Génère un résultat d'analyse rhétorique complet et simulé pour un extrait.

    :param text_snippet: Le texte (ou un aperçu) à analyser.
    :type text_snippet: str
    :param extract_name: Nom de l'extrait.
    :type extract_name: str
    :param source_name: Nom de la source.
    :type source_name: str
    :return: Un dictionnaire représentant l'analyse rhétorique simulée.
    :rtype: Dict[str, Any]
    """
    logger.info(
        f"Génération d'une analyse rhétorique simulée pour: {extract_name} (source: {source_name})"
    )

    fallacies = generate_mock_fallacy_detection(text_snippet)
    coherence = generate_mock_coherence_evaluation(text_snippet)

    num_devices = random.randint(1, len(MOCK_RHETORICAL_DEVICES))
    rhetorical_devices_detected = random.sample(MOCK_RHETORICAL_DEVICES, num_devices)

    analysis_result = {
        "extract_name": extract_name,
        "source_name": source_name,
        "original_text_snippet": (
            text_snippet[:200] + "..." if len(text_snippet) > 200 else text_snippet
        ),
        "fallacies_detected": fallacies,
        "coherence_evaluation": coherence,
        "rhetorical_devices": rhetorical_devices_detected,
        "overall_assessment": {
            "summary": f"Analyse rhétorique simulée pour '{extract_name}'. "
            f"{len(fallacies)} sophismes et {len(rhetorical_devices_detected)} figures de style trouvés (Mock).",
            "clarity_score": round(random.uniform(0.5, 0.95), 2),
            "persuasiveness_score": round(random.uniform(0.4, 0.9), 2),
            "confidence_score": round(
                random.uniform(0.6, 0.98), 2
            ),  # Confiance globale de l'analyse simulée
        },
        "timestamp": datetime.datetime.now().isoformat(),
    }
    logger.debug(f"Analyse rhétorique simulée générée pour '{extract_name}'.")
    return analysis_result
