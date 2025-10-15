# -*- coding: utf-8 -*-
"""Mock pour un extracteur d'arguments."""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MockArgumentMiner:
    """
    Mock d'un extracteur d'arguments.
    Simule l'identification de prémisses et de conclusions.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config if config else {}
        self.min_length = self.config.get("min_argument_length", 10)
        logger.info(
            "MockArgumentMiner initialisé avec config: %s (min_length: %d)",
            self.config,
            self.min_length,
        )

    def mine_arguments(self, text: str) -> List[Dict[str, Any]]:
        """
        Simule l'extraction d'arguments (prémisses, conclusions) du texte.

        Args:
            text: Le texte à analyser.

        Returns:
            Une liste de dictionnaires, chacun représentant un argument trouvé.
        """
        if not isinstance(text, str):
            logger.warning(
                "MockArgumentMiner.mine_arguments a reçu une entrée non textuelle."
            )
            return []

        logger.info("MockArgumentMiner analyse le texte : %s...", text[:100])

        arguments: List[Dict[str, Any]] = []

        # Scénario 1: Recherche de paires Prémisse/Conclusion
        pattern = re.compile(
            r"prémisse\s*:(.*?)(?:conclusion\s*:(.*?))?(?=prémisse\s*:|$)",
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(text):
            premise_content = match.group(1).strip()
            conclusion_content = match.group(2)

            if conclusion_content is not None:
                conclusion_content = conclusion_content.strip()
                if "." in conclusion_content:
                    conclusion_content = conclusion_content.split(".")[0] + "."
            else:
                conclusion_content = ""

            if len(premise_content) >= self.min_length:
                arguments.append(
                    {
                        "type": "Argument Explicite (Mock)",
                        "premise": premise_content,
                        "conclusion": conclusion_content,
                        "confidence": 0.85 if conclusion_content else 0.60,
                        "details": "Prémisse et conclusion explicitement marquées."
                        if conclusion_content
                        else "Prémisse détectée sans conclusion explicite.",
                    }
                )

        # Scénario 2: Texte contenant "donc" ou "par conséquent" comme indicateur de conclusion
        conclusion_indicators = ["donc", "par conséquent", "ainsi"]
        for indicator in conclusion_indicators:
            indicator_match = list(
                re.finditer(rf"\b{indicator}\b", text, re.IGNORECASE)
            )
            for match in indicator_match:
                premise_part = text[: match.start()].strip()
                conclusion_part = text[match.end() :].strip()

                # Simplification: prendre la dernière phrase pour la prémisse et la première pour la conclusion
                premise_sentences = [
                    s.strip() for s in re.split(r"[.!?]", premise_part) if s.strip()
                ]
                conclusion_sentences = [
                    s.strip() for s in re.split(r"[.!?]", conclusion_part) if s.strip()
                ]

                if premise_sentences and conclusion_sentences:
                    final_premise = premise_sentences[-1].rstrip(" ,")
                    final_conclusion = conclusion_sentences[0].lstrip(" ,")
                    if (
                        len(final_premise) >= self.min_length
                        and len(final_conclusion) >= self.min_length
                    ):
                        # Éviter les doublons si déjà trouvé par la méthode explicite
                        is_duplicate = False
                        for arg in arguments:
                            if arg.get("type") == "Argument Explicite (Mock)":
                                norm_arg_premise = (
                                    arg.get("premise", "").strip(" .!?").lower()
                                )
                                norm_arg_conclusion = (
                                    arg.get("conclusion", "").strip(" .!?").lower()
                                )
                                norm_final_premise = final_premise.strip(" .!?").lower()
                                norm_final_conclusion = final_conclusion.strip(
                                    " .!?"
                                ).lower()

                                if (
                                    norm_arg_premise == norm_final_premise
                                    and norm_arg_conclusion == norm_final_conclusion
                                ):
                                    is_duplicate = True
                                    break
                        if not is_duplicate:
                            arguments.append(
                                {
                                    "type": f"Argument Implicite (Mock - {indicator})",
                                    "premise": final_premise,
                                    "conclusion": final_conclusion,
                                    "confidence": 0.70,
                                    "details": f"Conclusion inférée par l'indicateur '{indicator}'.",
                                }
                            )

        # Scénario 3: Si aucun argument trouvé, considérer le texte entier comme une "affirmation"
        if not arguments and len(text) >= self.min_length:
            arguments.append(
                {
                    "type": "Affirmation Simple (Mock)",
                    "statement": text,
                    "confidence": 0.50,
                    "details": "Le texte est considéré comme une affirmation unique, faute d'indicateurs d'argument.",
                }
            )

        logger.info(f"MockArgumentMiner a trouvé {len(arguments)} arguments.")
        return arguments

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle du mineur d'arguments."""
        return self.config
