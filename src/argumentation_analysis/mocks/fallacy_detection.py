# -*- coding: utf-8 -*-
"""Mock pour la détection de sophismes."""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MockFallacyDetector:
    """
    Un détecteur de sophismes simulé pour les tests ou lorsque les vrais outils ne sont pas disponibles.
    """
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Simule la détection de sophismes dans un texte.

        Args:
            text (str): Le texte à analyser.

        Returns:
            List[Dict[str, Any]]: Une liste de dictionnaires représentant les sophismes détectés.
                                   Retourne une liste vide si aucun sophisme n'est "détecté".
        """
        if not isinstance(text, str):
            logger.warning("MockFallacyDetector.detect a reçu une entrée non textuelle.")
            return []
            
        logger.info(f"MockFallacyDetector.detect appelé pour le texte : '{text[:70]}...'")
        
        detected_fallacies: List[Dict[str, Any]] = []
        text_lower = text.lower()

        if "exemple de sophisme spécifique pour test" in text_lower:
            detected_fallacies.append({
                "fallacy_type": "Specific Mock Fallacy",
                "description": "Détection simulée pour un texte spécifique.",
                "severity": "Basse",
                "confidence": 0.90,
                "context_text": text[:150]
            })
        
        if "un autre texte pour varier" in text_lower:
            detected_fallacies.extend([
                {
                    "fallacy_type": "Generalisation Hative (Mock)",
                    "description": "Mock de généralisation hâtive.",
                    "severity": "Moyenne",
                    "confidence": 0.65,
                    "context_text": text[:100]
                },
                {
                    "fallacy_type": "Ad Populum (Mock)",
                    "description": "Appel à la popularité simulé.",
                    "severity": "Faible",
                    "confidence": 0.55,
                    "context_text": text[50:150] if len(text) > 50 else text # Protection de slicing
                }
            ])
        
        if not detected_fallacies and "sophisme générique" in text_lower:
             detected_fallacies.append({
                "fallacy_type": "Generic Mock Fallacy",
                "description": "Un sophisme générique simulé.",
                "severity": "Indéterminée",
                "confidence": 0.50,
                "context_text": text[:100]
            })

        logger.debug(f"MockFallacyDetector a 'détecté' {len(detected_fallacies)} sophismes.")
        return detected_fallacies