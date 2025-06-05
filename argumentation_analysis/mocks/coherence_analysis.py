# -*- coding: utf-8 -*-
"""Mock pour une analyse de cohérence."""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MockCoherenceAnalyzer:
    """
    Mock d'un analyseur de cohérence.
    Simule l'évaluation de la cohérence d'un texte basé sur des indicateurs simples.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        # Indicateurs de cohérence (positifs) et d'incohérence (négatifs)
        self.coherence_factors: Dict[str, float] = self.config.get(
            "coherence_factors",
            {
                "transition_words_ratio": 0.2,  # Ratio de mots de transition (ex: "donc", "cependant")
                "repeated_keywords_bonus": 0.15, # Si des mots-clés sont répétés de manière thématique
                "contradiction_penalty": -0.4,   # Par contradiction détectée (simplifié)
                "abrupt_topic_change_penalty": -0.2, # Si un changement de sujet abrupt est simulé
                "consistent_pronoun_referencing": 0.1 # Bonus si les références pronominales semblent cohérentes (très simplifié)
            }
        )
        self.transition_words = self.config.get(
            "transition_words", 
            ["donc", "cependant", "par conséquent", "ainsi", "de plus", "en outre", "toutefois", "néanmoins", "finalement"]
        )
        self.contradiction_pairs = self.config.get( # Paires de phrases/mots-clés contradictoires (simplifié)
            "contradiction_pairs",
            [("j'aime", "je n'aime pas"), ("c'est vrai", "c'est faux"), ("toujours", "jamais")] 
        )
        logger.info(
            "MockCoherenceAnalyzer initialisé avec config: %s", self.config
        )

    def analyze_coherence(self, text: str, previous_text_summary: str = None) -> Dict[str, Any]:
        """
        Simule l'analyse de la cohérence du texte.

        Args:
            text: Le texte à analyser.
            previous_text_summary: Un résumé optionnel du texte précédent pour évaluer la cohérence inter-textes.

        Returns:
            Un dictionnaire contenant le score de cohérence simulé et les facteurs l'influençant.
        """
        if not isinstance(text, str) or not text.strip():
            logger.warning("MockCoherenceAnalyzer.analyze_coherence a reçu une entrée non textuelle ou vide.")
            return {"error": "Entrée non textuelle ou vide", "coherence_score": 0.0, "factors": {}}

        logger.info("MockCoherenceAnalyzer évalue le texte : %s...", text[:100])
        
        coherence_score: float = 0.5 # Score de base (ni bon ni mauvais)
        factors: Dict[str, Any] = {factor: 0 for factor in self.coherence_factors}
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        num_words = len(words)

        if num_words == 0:
            return {"coherence_score": 0.0, "factors": factors, "interpretation": self._interpret_score(0.0)}

        # Mots de transition
        transition_word_count = 0
        for tw in self.transition_words:
            transition_word_count += len(re.findall(rf"\b{re.escape(tw)}\b", text_lower))
        
        if num_words > 0: # Éviter la division par zéro
            transition_ratio = transition_word_count / num_words
            if transition_ratio > 0.02: # Arbitraire: plus de 2% de mots de transition
                coherence_score += self.coherence_factors["transition_words_ratio"]
                factors["transition_words_ratio"] = round(transition_ratio, 3)

        # Répétition de mots-clés (simplifié: mots de plus de 5 lettres répétés au moins 2 fois)
        word_counts = {}
        for word in words:
            if len(word) > 5:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        repeated_keywords_count = sum(1 for count in word_counts.values() if count >= 2)
        if repeated_keywords_count > 0:
            # Appliquer un bonus fixe si au moins un mot est répété.
            # La logique originale était peut-être trop complexe pour le mock.
            coherence_score += self.coherence_factors["repeated_keywords_bonus"]
            factors["repeated_keywords_bonus"] = repeated_keywords_count

        # Contradictions (simplifié)
        contradictions_found = 0
        for pair1, pair2 in self.contradiction_pairs:
            if pair1 in text_lower and pair2 in text_lower:
                contradictions_found += 1
        if contradictions_found > 0:
            coherence_score += self.coherence_factors["contradiction_penalty"] * contradictions_found
            factors["contradiction_penalty"] = contradictions_found
            
        # Changement de sujet abrupt (simulé si un résumé du texte précédent est fourni et très différent)
        if previous_text_summary and isinstance(previous_text_summary, str):
            # Simulation très basique: si peu de mots communs entre début du texte et résumé précédent
            prev_summary_words = set(re.findall(r'\b\w+\b', previous_text_summary.lower()[:100]))
            current_text_start_words = set(words[:20]) # 20 premiers mots du texte actuel
            common_words_ratio = len(prev_summary_words.intersection(current_text_start_words)) / (len(prev_summary_words) + 1e-6)
            if common_words_ratio < 0.1 and len(prev_summary_words)>5 : # Moins de 10% de mots communs
                coherence_score += self.coherence_factors["abrupt_topic_change_penalty"]
                factors["abrupt_topic_change_penalty"] = 1
        
        # Références pronominales (placeholder, très difficile à simuler simplement)
        # On pourrait compter les pronoms et si > N, ajouter un petit bonus/malus aléatoire.
        # Pour ce mock, on va juste ajouter un petit bonus si le texte est assez long.
        # Appliquer systématiquement un petit bonus pour la cohérence des pronoms pour simplifier
        coherence_score += self.coherence_factors.get("consistent_pronoun_referencing", 0.1)
        factors["consistent_pronoun_referencing"] = 1


        final_score = min(max(coherence_score, 0.0), 1.0)

        logger.info(f"MockCoherenceAnalyzer score calculé: {final_score:.2f}, facteurs: {factors}")
        return {
            "coherence_score": final_score,
            "factors": factors,
            "interpretation": self._interpret_score(final_score)
        }

    def _interpret_score(self, score: float) -> str:
        if score >= 0.75:
            return "Très cohérent (Mock)"
        elif score >= 0.5:
            return "Cohérent (Mock)"
        elif score >= 0.25:
            return "Peu cohérent (Mock)"
        else:
            return "Incohérent (Mock)"

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle de l'analyseur de cohérence."""
        return self.config