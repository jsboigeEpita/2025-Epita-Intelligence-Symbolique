# -*- coding: utf-8 -*-
"""
Ce module fournit des mocks pour les détecteurs de sophismes.
Il contient des objets et fonctions simulés (mocks) utilisés pour les tests
ou pour remplacer des dépendances complexes lors du développement ou de
certaines configurations d'exécution.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MockFallacyDetector:
    """
    Un mock pour un détecteur de sophismes, simulant la détection 
    lorsque les vrais outils ne sont pas disponibles ou pour les tests.
    """
    def __init__(self, model_name: str = "mock_fallacy_model", language: str = "fr"):
        self.model_name = model_name
        self.language = language
        logger.info(f"MockFallacyDetector initialisé avec model='{model_name}', language='{language}'.")

    def detect(self, text: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Simule la détection de sophismes dans le texte.
        Combine des logiques de HEAD et MERGE_HEAD.

        :param text: Le texte à analyser.
        :type text: str
        :param context: Contexte supplémentaire pour l'analyse (optionnel, actuellement non utilisé dans ce mock).
        :type context: Dict[str, Any], optional
        :return: Une liste de dictionnaires, chaque dictionnaire représentant un sophisme détecté.
        :rtype: List[Dict[str, Any]]
        """
        if not isinstance(text, str):
            logger.warning("MockFallacyDetector.detect a reçu une entrée non textuelle.")
            return []
            
        logger.info(f"MockFallacyDetector.detect appelée pour le texte : '{text[:70]}...'")
        
        detected_fallacies: List[Dict[str, Any]] = []
        text_lower = text.lower()

        # Logique de détection inspirée de MERGE_HEAD, adaptée au format de HEAD
        if "exemple de sophisme spécifique pour test" in text_lower:
            detected_fallacies.append({
                "fallacy_type": "Specific Mock Fallacy",
                "description": "Détection simulée pour un texte spécifique.",
                "severity": "Basse", # Format HEAD
                "confidence": 0.90,
                "context_text": text[:150]
            })
        
        if "un autre texte pour varier" in text_lower:
            detected_fallacies.extend([
                {
                    "fallacy_type": "Generalisation Hative (Mock)",
                    "description": "Mock de généralisation hâtive.",
                    "severity": "Moyenne", # Format HEAD
                    "confidence": 0.65,
                    "context_text": text[:100]
                },
                {
                    "fallacy_type": "Ad Populum (Mock)",
                    "description": "Appel à la popularité simulé.",
                    "severity": "Faible", # Ajusté, MERGE_HEAD avait "Faible"
                    "confidence": 0.55,
                    "context_text": text[50:150] # Slicing simple
                }
            ])
        
        # Logique de HEAD pour "argument invalide"
        if "argument invalide" in text_lower:
            detected_fallacies.append({
                "fallacy_type": "Argument Invalide (Simulé)",
                "description": "Le raisonnement présenté semble contenir une faille logique simulée.",
                "severity": 0.8,
                "confidence": 0.80,
                "context_text": text[:100] 
            })
        
        # Logique de HEAD pour "personnellement" et "attaque"
        if "personnellement" in text_lower and "attaque" in text_lower:
            start_index = text_lower.find("personnellement")
            end_index = text_lower.find("attaque") + len("attaque")
            context_slice = text[max(0, start_index-20) : min(len(text), end_index+20)]
            detected_fallacies.append({
                "fallacy_type": "Ad Hominem (Simulé)",
                "description": "Une attaque personnelle simulée semble être présente.",
                "severity": "Moyenne",
                "confidence": 0.65,
                "context_text": context_slice
            })
            
        # Logique pour le cas de test Ad Hominem spécifique
        logger.info(f"VALIDATION_CORRECTIF: Recherche de sophisme Ad Hominem simulé pour le texte : '{text_lower}'")
        if "auteur" in text_lower and ("condamné" in text_lower or "fraude" in text_lower):
            detected_fallacies.append({
                "fallacy_type": "Ad Hominem (Simulé)",
                "description": "Attaque envers l'auteur basée sur ses actions passées (fraude fiscale).",
                "severity": 0.8,
                "confidence": 0.95,
                "context_text": text
            })

        if not detected_fallacies and "sophisme générique" in text_lower:
             detected_fallacies.append({
                "fallacy_type": "Generic Mock Fallacy", # Nom de HEAD
                "description": "Un sophisme générique simulé pour illustrer.", # Description de HEAD
                "severity": "Indéterminée", # Format HEAD, ajusté pour le test
                "confidence": 0.50, # Confiance de MERGE_HEAD pour générique
                "context_text": text[:150] if text else "Texte non disponible."
            })

        logger.info(f"{len(detected_fallacies)} sophismes simulés détectés par MockFallacyDetector.")
        return detected_fallacies

    def detect_fallacies(self, text: str) -> List[Dict[str, Any]]:
        """
        Wrapper pour la compatibilité avec l'interface attendue.
        """
        return self.detect(text)

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Retourne les capacités simulées du détecteur de sophismes. (Version HEAD)
        """
        return {
            "name": "MockFallacyDetector",
            "version": "1.0.0",
            "supported_languages": [self.language, "en"],
            "description": "Détecteur de sophismes simulé pour les tests.",
            "detects_specific_fallacies": [ # Mis à jour avec les types fusionnés
                "Specific Mock Fallacy (Simulé)",
                "Generalisation Hative (Simulé)",
                "Ad Populum (Simulé)",
                "Argument Invalide (Simulé)", 
                "Ad Hominem (Simulé)", 
                "Sophisme Générique (Simulé)"
            ],
            "output_format": {
                "fallacy_type": "str",
                "description": "str",
                "severity": "str (Haute/Moyenne/Basse/Faible/Indéterminée)", # Ajusté
                "confidence": "float (0.0-1.0)",
                "context_text": "str"
            }
        }

logger.debug("Mocks pour la détection de sophismes définis.")
