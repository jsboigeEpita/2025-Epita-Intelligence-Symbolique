# -*- coding: utf-8 -*-
"""Mock pour un détecteur de preuves (evidence)."""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MockEvidenceDetector:
    """
    Mock d'un détecteur de preuves.
    Simule l'identification de phrases ou de données factuelles soutenant une affirmation.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        self.min_evidence_length = self.config.get("min_evidence_length", 15)
        self.evidence_keywords = self.config.get(
            "evidence_keywords",
            ["selon l'étude", "les données montrent que", "par exemple", "il a été prouvé que", "comme en témoigne"]
        )
        logger.info(
            "MockEvidenceDetector initialisé avec config: %s (min_length: %d, keywords: %s)",
            self.config, self.min_evidence_length, self.evidence_keywords
        )

    def detect_evidence(self, text: str, claims: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Simule la détection de preuves dans le texte, potentiellement en lien avec des revendications.

        Args:
            text: Le texte à analyser.
            claims: Une liste optionnelle de revendications précédemment identifiées.
                    (Non utilisé activement dans ce mock simple pour lier les preuves aux revendications).

        Returns:
            Une liste de dictionnaires, chacun représentant un élément de preuve trouvé.
        """
        if not isinstance(text, str):
            logger.warning("MockEvidenceDetector.detect_evidence a reçu une entrée non textuelle.")
            return []

        logger.info("MockEvidenceDetector analyse le texte : %s...", text[:100])
        
        evidences: List[Dict[str, Any]] = []

        # Scénario 1: Utiliser des mots-clés pour identifier des preuves
        for keyword in self.evidence_keywords:
            # Logique de recherche de pattern plus flexible
            search_pattern = re.escape(keyword)
            if keyword.isalnum(): # Si le mot-clé est un mot simple, utiliser les frontières de mot
                search_pattern = rf"\b{search_pattern}\b"
            
            matches = list(re.finditer(search_pattern, text, re.IGNORECASE))
            for match in matches:
                evidence_text_start = match.end()
                
                # Essayer de trouver la fin de la phrase (point) ou une citation
                period_match = text.find('.', evidence_text_start)
                # Pourrait aussi chercher des guillemets fermants si le keyword en ouvre.
                
                if period_match != -1:
                    evidence_text_end = period_match + 1
                else:
                    evidence_text_end = min(len(text), evidence_text_start + 150) # Portion plus longue pour les preuves
                
                evidence_content = text[evidence_text_start:evidence_text_end].strip()
                # Enlever la ponctuation non désirée au début
                evidence_content = re.sub(r"^[ ,:]+", "", evidence_content)
                
                if len(evidence_content) >= self.min_evidence_length:
                    evidences.append({
                        "type": "Preuve par Mot-Clé (Mock)",
                        "evidence_text": evidence_content,
                        "keyword_used": keyword,
                        "strength_simulated": 0.80, # Simuler une force de preuve
                        "source_indices": (match.start(), evidence_text_end)
                    })

        # Scénario 2: Identifier des phrases contenant des chiffres ou des pourcentages (simplifié)
        # et qui sont suffisamment longues. Éviter les doublons.
        if not evidences: # Seulement si aucun mot-clé n'a fonctionné
            potential_evidences = []
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            for sentence in sentences:
                if len(sentence) >= self.min_evidence_length:
                    if re.search(r'\d+', sentence) or "%" in sentence: # Contient un chiffre ou %
                        # Vérifier si cette phrase n'est pas déjà couverte
                        is_covered = False 
                        # (Logique de non-doublon omise car dans `if not evidences`)
                        
                        potential_evidences.append({
                            "type": "Preuve Factuelle (Chiffre/%) (Mock)",
                            "evidence_text": sentence,
                            "strength_simulated": 0.70,
                            "source_indices": (text.find(sentence), text.find(sentence) + len(sentence))
                        })
            if potential_evidences:
                evidences.extend(potential_evidences)
        
        # Scénario 3: Si toujours rien, et qu'une partie du texte semble être une citation (entre guillemets)
        if not evidences:
            quote_matches = list(re.finditer(r'"([^"]+)"', text)) # Guillemets doubles simples
            for q_match in quote_matches:
                quoted_text = q_match.group(1).strip()
                if len(quoted_text) >= self.min_evidence_length:
                    evidences.append({
                        "type": "Preuve par Citation (Mock)",
                        "evidence_text": quoted_text,
                        "strength_simulated": 0.75,
                        "source_indices": (q_match.start(1), q_match.end(1))
                    })

        logger.info(f"MockEvidenceDetector a trouvé {len(evidences)} éléments de preuve.")
        return evidences

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle du détecteur de preuves."""
        return self.config