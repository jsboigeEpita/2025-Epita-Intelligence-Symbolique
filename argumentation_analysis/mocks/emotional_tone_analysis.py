# -*- coding: utf-8 -*-
"""Mock pour une analyse de tonalité émotionnelle."""

import logging
import re
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class MockEmotionalToneAnalyzer:
    """
    Mock d'un analyseur de tonalité émotionnelle.
    Simule la détection d'émotions primaires et secondaires dans un texte.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        # Configuration des mots-clés pour différentes émotions
        self.emotion_keywords: Dict[str, List[str]] = self.config.get(
            "emotion_keywords",
            {
                "Joie (Mock)": [
                    "heureux",
                    "joyeux",
                    "joyeuse",
                    "content",
                    "ravi",
                    "enthousiaste",
                ],
                "Tristesse (Mock)": [
                    "triste",
                    "malheureux",
                    "déprimé",
                    "peiné",
                    "abattu",
                ],
                "Colère (Mock)": ["colère", "furieux", "irrité", "enragé", "mécontent"],
                "Peur (Mock)": ["peur", "effrayé", "craintif", "anxieux", "inquiet"],
                "Surprise (Mock)": ["surprise", "étonné", "stupéfait", "abasourdi"],
                "Dégoût (Mock)": ["dégoût", "répugnance", "aversion"],
            },
        )
        self.intensity_threshold = self.config.get("intensity_threshold", 0.6)
        self.strong_keywords = self.config.get(
            "strong_keywords",
            [
                "furieux",
                "ravi",
                "effrayé",
                "déprimé",
                "enthousiaste",
                "enragé",
                "stupéfait",
            ],
        )
        logger.info(
            "MockEmotionalToneAnalyzer initialisé avec config: %s (keywords: %d, threshold: %.2f)",
            self.config,
            len(self.emotion_keywords),
            self.intensity_threshold,
        )

    def analyze_tone(self, text: str) -> Dict[str, Any]:
        """
        Simule l'analyse de la tonalité émotionnelle du texte.

        Args:
            text: Le texte à analyser.

        Returns:
            Un dictionnaire contenant les émotions détectées et leur intensité simulée.
        """
        if not isinstance(text, str):
            logger.warning(
                "MockEmotionalToneAnalyzer.analyze_tone a reçu une entrée non textuelle."
            )
            return {
                "error": "Entrée non textuelle",
                "emotions_detected": {},
                "dominant_emotion": "Inconnue",
            }

        logger.info("MockEmotionalToneAnalyzer analyse le texte : %s...", text[:100])

        emotions_scores: Dict[str, float] = {
            emotion: 0.0 for emotion in self.emotion_keywords
        }
        detected_emotion_details: List[Dict[str, Any]] = []

        text_lower = text.lower()

        for emotion, keywords in self.emotion_keywords.items():
            keyword_found_count = 0
            has_strong_keyword = False
            for keyword in keywords:
                matches = list(re.finditer(rf"\b{re.escape(keyword)}\b", text_lower))
                if matches:
                    keyword_found_count += len(matches)
                    if keyword in self.strong_keywords:
                        has_strong_keyword = True
                    for match in matches:
                        detected_emotion_details.append(
                            {
                                "emotion": emotion,
                                "keyword": keyword,
                                "indices": (match.start(), match.end()),
                            }
                        )

            if keyword_found_count > 0:
                score = min(1.0, 0.3 * keyword_found_count + 0.1)
                if has_strong_keyword:
                    score = min(1.0, score + 0.2)
                emotions_scores[emotion] = score

        dominant_emotion = "Neutre (Mock)"
        max_score = 0.0
        for emotion, score in emotions_scores.items():
            if (
                score > max_score and score >= 0.1
            ):  # Un minimum de score pour être considéré
                max_score = score
                dominant_emotion = emotion

        # Si le score max n'atteint pas un certain seuil, on peut considérer la tonalité comme mixte ou neutre.
        if max_score < self.intensity_threshold and dominant_emotion != "Neutre (Mock)":
            dominant_emotion = f"Mixte (dominant: {dominant_emotion.split(' ')[0]}, score: {max_score:.2f})"
        elif max_score == 0.0:
            dominant_emotion = "Neutre (Mock)"

        logger.info(
            f"MockEmotionalToneAnalyzer a détecté les scores: {emotions_scores}, dominant: {dominant_emotion}"
        )
        return {
            "emotions_scores": emotions_scores,
            "dominant_emotion": dominant_emotion,
            "details": detected_emotion_details,  # Pourrait être utile pour le débogage ou des analyses plus fines
        }

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle de l'analyseur de tonalité émotionnelle."""
        return self.config
