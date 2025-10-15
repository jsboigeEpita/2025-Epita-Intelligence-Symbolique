# -*- coding: utf-8 -*-
"""Mock pour un extracteur de revendications (claims)."""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MockClaimMiner:
    """
    Mock d'un extracteur de revendications (claims).
    Simule l'identification de phrases assertives ou de points clés.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        self.min_claim_length = self.config.get("min_claim_length", 8)
        self.claim_keywords = self.config.get(
            "claim_keywords",
            [
                "il est clair que",
                "nous affirmons",
                "le point principal est",
                "il faut noter",
            ],
        )
        logger.info(
            "MockClaimMiner initialisé avec config: %s (min_length: %d, keywords: %s)",
            self.config,
            self.min_claim_length,
            self.claim_keywords,
        )

    def extract_claims(self, text: str) -> List[Dict[str, Any]]:
        """
        Simule l'extraction de revendications du texte.

        Args:
            text: Le texte à analyser.

        Returns:
            Une liste de dictionnaires, chacun représentant une revendication trouvée.
        """
        if not isinstance(text, str):
            logger.warning(
                "MockClaimMiner.extract_claims a reçu une entrée non textuelle."
            )
            return []

        logger.info("MockClaimMiner analyse le texte : %s...", text[:100])

        claims: List[Dict[str, Any]] = []
        keyword_match_found = False

        # Scénario 1: Utiliser des mots-clés pour identifier des revendications
        for keyword in self.claim_keywords:
            search_pattern = re.escape(keyword)
            if keyword.isalnum():
                search_pattern = rf"\b{search_pattern}\b"

            matches = list(re.finditer(search_pattern, text, re.IGNORECASE))
            if matches:
                keyword_match_found = True
            for match in matches:
                # Extraire la phrase ou la portion de texte suivant le mot-clé
                claim_text_start = match.end()

                # Essayer de trouver la fin de la phrase (point)
                period_match = text.find(".", claim_text_start)
                if period_match != -1:
                    claim_text_end = period_match + 1
                else:
                    # Sinon, prendre une portion de texte (ex: 100 caractères)
                    claim_text_end = min(len(text), claim_text_start + 100)

                claim_content = text[claim_text_start:claim_text_end].strip()

                if len(claim_content) >= self.min_claim_length:
                    claims.append(
                        {
                            "type": "Revendication par Mot-Clé (Mock)",
                            "claim_text": claim_content,
                            "keyword_used": keyword,
                            "confidence": 0.75,
                            "source_indices": (match.start(), claim_text_end),
                        }
                    )

        # Scénario 2: Si aucune revendication n'a été ajoutée ET aucun mot-clé n'a été trouvé,
        # considérer le texte entier comme une "Revendication Globale".
        if (
            not claims
            and not keyword_match_found
            and len(text) >= self.min_claim_length
        ):
            claims.append(
                {
                    "type": "Revendication Globale (Mock)",
                    "claim_text": text,
                    "confidence": 0.50,
                    "source_indices": (0, len(text)),
                }
            )

        logger.info(f"MockClaimMiner a trouvé {len(claims)} revendications.")
        return claims

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle de l'extracteur de revendications."""
        return self.config
