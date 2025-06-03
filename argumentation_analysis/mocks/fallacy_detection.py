# -*- coding: utf-8 -*-
"""
Ce module fournit des mocks pour les détecteurs de sophismes.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MockFallacyDetector:
    """
    Un mock pour un détecteur de sophismes.
    Simule la détection de sophismes dans un texte donné.
    """
    def __init__(self, model_name: str = "mock_fallacy_model", language: str = "fr"):
        self.model_name = model_name
        self.language = language
        logger.info(f"MockFallacyDetector initialisé avec model='{model_name}', language='{language}'.")

    def detect_fallacies(self, text: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Simule la détection de sophismes dans le texte.

        :param text: Le texte à analyser.
        :type text: str
        :param context: Contexte supplémentaire pour l'analyse (optionnel).
        :type context: Dict[str, Any], optional
        :return: Une liste de dictionnaires, chaque dictionnaire représentant un sophisme détecté.
                 Exemple de format pour un sophisme :
                 {
                     "fallacy_type": "Ad Hominem (Mock)",
                     "description": "Attaque simulée contre la personne.",
                     "severity": "Moyenne (Mock)",
                     "confidence": 0.75,
                     "context_text": "Extrait du texte où le sophisme simulé a été trouvé."
                 }
        :rtype: List[Dict[str, Any]]
        """
        logger.debug(f"MockFallacyDetector.detect_fallacies appelée pour le texte (début): {text[:70]}...")
        
        mock_fallacies = []
        
        # Simuler la détection basée sur des mots-clés simples pour l'exemple
        if "argument invalide" in text.lower():
            mock_fallacies.append({
                "fallacy_type": "Argument Invalide (Mock)",
                "description": "Le raisonnement présenté semble contenir une faille logique simulée.",
                "severity": "Haute (Mock)",
                "confidence": 0.80,
                "context_text": text[:100] # Prend les 100 premiers caractères comme contexte
            })
        
        if "personnellement" in text.lower() and "attaque" in text.lower():
            mock_fallacies.append({
                "fallacy_type": "Ad Hominem (Mock)",
                "description": "Une attaque personnelle simulée semble être présente.",
                "severity": "Moyenne (Mock)",
                "confidence": 0.65,
                "context_text": text[text.lower().find("personnellement")-20 : text.lower().find("attaque")+30]
            })
            
        if not mock_fallacies:
             mock_fallacies.append({
                "fallacy_type": "Sophisme Générique (Mock)",
                "description": "Ceci est un sophisme générique simulé pour illustrer la détection.",
                "severity": "Basse (Mock)",
                "confidence": 0.55,
                "context_text": text[:150] if text else "Texte non disponible."
            })

        logger.info(f"{len(mock_fallacies)} sophismes simulés détectés par MockFallacyDetector.")
        return mock_fallacies

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Retourne les capacités simulées du détecteur de sophismes.
        """
        return {
            "name": "MockFallacyDetector",
            "version": "1.0.0",
            "supported_languages": [self.language, "en"],
            "description": "Détecteur de sophismes simulé pour les tests.",
            "detects_specific_fallacies": [
                "Argument Invalide (Mock)", 
                "Ad Hominem (Mock)", 
                "Sophisme Générique (Mock)"
            ],
            "output_format": {
                "fallacy_type": "str",
                "description": "str",
                "severity": "str (Haute/Moyenne/Basse)",
                "confidence": "float (0.0-1.0)",
                "context_text": "str"
            }
        }