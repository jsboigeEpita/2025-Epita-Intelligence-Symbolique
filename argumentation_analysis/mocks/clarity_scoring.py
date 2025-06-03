# -*- coding: utf-8 -*-
"""Mock pour un score de clarté."""

import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MockClarityScorer:
    """
    Mock d'un évaluateur de clarté.
    Simule l'évaluation de la clarté d'un texte basé sur des heuristiques simples.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        # Pénalités pour manque de clarté
        self.clarity_penalties: Dict[str, float] = self.config.get(
            "clarity_penalties",
            {
                "long_sentences_avg": -0.1, # Si longueur moyenne des phrases > 25 mots
                "complex_words_ratio": -0.15, # Si ratio de mots complexes (ex: >3 syllabes) > 0.1
                "passive_voice_ratio": -0.05, # Si ratio de phrases à la voix passive > 0.2
                "jargon_count": -0.2,         # Par occurrence de mot de jargon détecté
                "ambiguity_keywords": -0.1    # Par occurrence de mot ambigu
            }
        )
        self.jargon_list = self.config.get("jargon_list", ["synergie", "paradigm shift", "holistique", "disruptif"])
        self.ambiguity_keywords = self.config.get("ambiguity_keywords", ["peut-être", "possiblement", "certains", "quelques"])
        self.max_avg_sentence_length = self.config.get("max_avg_sentence_length", 25)
        self.max_complex_word_ratio = self.config.get("max_complex_word_ratio", 0.1)
        self.max_passive_voice_ratio = self.config.get("max_passive_voice_ratio", 0.2)

        logger.info(
            "MockClarityScorer initialisé avec config: %s", self.config
        )

    def score_clarity(self, text: str) -> Dict[str, Any]:
        """
        Simule l'évaluation de la clarté du texte.

        Args:
            text: Le texte à évaluer.

        Returns:
            Un dictionnaire contenant le score de clarté simulé et les facteurs l'influençant.
        """
        if not isinstance(text, str) or not text.strip():
            logger.warning("MockClarityScorer.score_clarity a reçu une entrée non textuelle ou vide.")
            return {"error": "Entrée non textuelle ou vide", "clarity_score": 0.0, "factors": {}}

        logger.info("MockClarityScorer évalue le texte : %s...", text[:100])
        
        clarity_score: float = 1.0 # Score de base parfait
        factors: Dict[str, Any] = {penalty: 0 for penalty in self.clarity_penalties}
        text_lower = text.lower()

        words = re.findall(r'\b\w+\b', text_lower)
        num_words = len(words)
        if num_words == 0:
            return {"clarity_score": 0.0, "factors": factors, "interpretation": self._interpret_score(0.0)}

        sentences = [s.strip() for s in text.split('.') if s.strip()] # Simpliste
        num_sentences = len(sentences) if len(sentences) > 0 else 1

        # Longueur moyenne des phrases
        avg_sentence_length = num_words / num_sentences
        if avg_sentence_length > self.max_avg_sentence_length:
            clarity_score += self.clarity_penalties["long_sentences_avg"]
            factors["long_sentences_avg"] = round(avg_sentence_length,1)

        # Mots complexes (simplifié: mots > 9 lettres comme proxy pour >3 syllabes)
        complex_words = [w for w in words if len(w) > 9]
        complex_word_ratio = len(complex_words) / num_words
        if complex_word_ratio > self.max_complex_word_ratio:
            clarity_score += self.clarity_penalties["complex_words_ratio"]
            factors["complex_words_ratio"] = round(complex_word_ratio, 2)
        
        # Voix passive (très simplifié: recherche de "est/sont/été suivi par participe passé")
        # Ceci est un placeholder, une vraie détection est complexe.
        passive_indicators = len(re.findall(r"\b(est|sont|été|fut|furent)\s+\w+é(e?s?)\b", text_lower))
        passive_voice_ratio = passive_indicators / num_sentences
        if passive_voice_ratio > self.max_passive_voice_ratio:
            clarity_score += self.clarity_penalties["passive_voice_ratio"]
            factors["passive_voice_ratio"] = round(passive_voice_ratio, 2)

        # Jargon
        jargon_found_count = 0
        for jargon_word in self.jargon_list:
            jargon_found_count += text_lower.count(jargon_word)
        if jargon_found_count > 0:
            clarity_score += self.clarity_penalties["jargon_count"] * jargon_found_count
            factors["jargon_count"] = jargon_found_count
            
        # Mots ambigus
        ambiguity_found_count = 0
        for amb_word in self.ambiguity_keywords:
             ambiguity_found_count += len(re.findall(rf"\b{re.escape(amb_word)}\b", text_lower))
        if ambiguity_found_count > 0:
            clarity_score += self.clarity_penalties["ambiguity_keywords"] * ambiguity_found_count
            factors["ambiguity_keywords"] = ambiguity_found_count
        
        final_score = min(max(clarity_score, 0.0), 1.0) # Normaliser entre 0 et 1

        logger.info(f"MockClarityScorer score calculé: {final_score:.2f}, facteurs: {factors}")
        return {
            "clarity_score": final_score,
            "factors": factors,
            "interpretation": self._interpret_score(final_score)
        }

    def _interpret_score(self, score: float) -> str:
        if score >= 0.8:
            return "Très clair (Mock)"
        elif score >= 0.6:
            return "Clair (Mock)"
        elif score >= 0.4:
            return "Peu clair (Mock)"
        else:
            return "Pas clair du tout (Mock)"

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle de l'évaluateur de clarté."""
        return self.config