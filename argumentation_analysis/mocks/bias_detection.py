# -*- coding: utf-8 -*-
"""Mock pour un détecteur de biais."""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MockBiasDetector:
    """
    Mock d'un détecteur de biais.
    Simule l'identification de différents types de biais dans un texte.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        self.min_context_length = self.config.get("min_context_length", 20)
        self.bias_patterns = self.config.get(
            "bias_patterns",
            {
                "Biais de Confirmation (Mock)": [
                    r"il est évident que",
                    r"tout le monde sait que",
                ],
                "Généralisation Hâtive (Mock)": [
                    r"toujours",
                    r"jamais",
                    r"tous les",
                    r"personne ne",
                ],
                "Biais d'Autorité (Mock)": [r"selon l'expert", r"le docteur a dit"],
                "Faux Dilemme (Mock)": [
                    r"soit A ou soit B",
                    r"il n'y a que deux options",
                ],
            },
        )
        logger.info(
            "MockBiasDetector initialisé avec config: %s (patterns: %d)",
            self.config,
            len(self.bias_patterns),
        )

    def detect_biases(self, text: str) -> List[Dict[str, Any]]:
        """
        Simule la détection de biais dans le texte.

        Args:
            text: Le texte à analyser.

        Returns:
            Une liste de dictionnaires, chacun représentant un biais potentiel trouvé.
        """
        if not isinstance(text, str):
            logger.warning(
                "MockBiasDetector.detect_biases a reçu une entrée non textuelle."
            )
            return []

        logger.info("MockBiasDetector analyse le texte : %s...", text[:100])

        detected_biases: List[Dict[str, Any]] = []

        for bias_type, patterns in self.bias_patterns.items():
            for pattern in patterns:
                try:
                    # Utiliser \b pour s'assurer que le pattern est un mot/groupe entier si pertinent
                    # Pour des expressions comme "tous les", \b au début et à la fin est bon.
                    # Pour "toujours", \b au début et à la fin.
                    # Pour "il est évident que", \b au début.
                    # La regex doit être construite avec soin. Ici, on simplifie.
                    # On va ajouter \b autour de patterns qui sont des mots seuls.
                    # Pour les phrases, on cherche l'occurrence.

                    # Heuristique simple pour \b: si le pattern ne contient pas d'espace, on l'encadre.
                    search_pattern = (
                        rf"\b{pattern}\b" if " " not in pattern else pattern
                    )

                    matches = list(re.finditer(search_pattern, text, re.IGNORECASE))
                    for match in matches:
                        # Extraire un contexte autour du match
                        context_start = max(0, match.start() - 30)
                        context_end = min(len(text), match.end() + 30)
                        context_snippet = text[context_start:context_end]

                        if len(context_snippet) >= self.min_context_length:
                            detected_biases.append(
                                {
                                    "bias_type": bias_type,
                                    "detected_pattern": pattern,
                                    "context_snippet": context_snippet,
                                    "severity_simulated": "Moyen"
                                    if "Généralisation" in bias_type
                                    else "Faible",
                                    "confidence": 0.65
                                    + (
                                        0.1 * patterns.index(pattern) % 0.2
                                    ),  # Varie un peu
                                    "source_indices": (match.start(), match.end()),
                                }
                            )
                except re.error as e:
                    logger.error(
                        f"Erreur de regex pour le pattern '{pattern}' du biais '{bias_type}': {e}"
                    )

        # Si aucun biais spécifique n'est trouvé mais que le texte est long et contient des superlatifs
        if not detected_biases and len(text) > 100:
            superlatives = [
                "le meilleur",
                "le pire",
                "absolument incroyable",
                "totalement faux",
            ]
            for sup in superlatives:
                if sup in text.lower():
                    detected_biases.append(
                        {
                            "bias_type": "Exagération Potentielle (Mock)",
                            "detected_pattern": sup,
                            "context_snippet": text[
                                max(0, text.lower().find(sup) - 20) : min(
                                    len(text), text.lower().find(sup) + len(sup) + 20
                                )
                            ],
                            "severity_simulated": "Faible",
                            "confidence": 0.55,
                            "source_indices": (
                                text.lower().find(sup),
                                text.lower().find(sup) + len(sup),
                            ),
                        }
                    )
                    break  # Un seul de ce type suffit

        logger.info(
            f"MockBiasDetector a trouvé {len(detected_biases)} biais potentiels."
        )
        return detected_biases

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle du détecteur de biais."""
        return self.config
