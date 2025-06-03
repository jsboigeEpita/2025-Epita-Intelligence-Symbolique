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
            self.config, self.min_length
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
            logger.warning("MockArgumentMiner.mine_arguments a reçu une entrée non textuelle.")
            return []

        logger.info("MockArgumentMiner analyse le texte : %s...", text[:100])
        
        arguments: List[Dict[str, Any]] = []
        
        # Simuler la recherche de "prémisse :" et "conclusion :"
        premise_matches = list(re.finditer(r"prémisse\s*:", text, re.IGNORECASE))
        conclusion_matches = list(re.finditer(r"conclusion\s*:", text, re.IGNORECASE))

        # Scénario 1: Prémisse explicite suivie d'une conclusion explicite
        for p_match in premise_matches:
            for c_match in conclusion_matches:
                if c_match.start() > p_match.end():
                    premise_text_start = p_match.end()
                    premise_text_end = c_match.start()
                    premise_content = text[premise_text_start:premise_text_end].strip()
                    
                    conclusion_text_start = c_match.end()
                    # Trouver la fin de la phrase de la conclusion
                    next_premise_start = float('inf')
                    if premise_matches.index(p_match) + 1 < len(premise_matches):
                         next_premise_start = premise_matches[premise_matches.index(p_match) + 1].start()
                    
                    conclusion_text_end = min(len(text), next_premise_start)
                    # Chercher un point pour délimiter la conclusion si possible
                    period_after_conclusion = text.find('.', conclusion_text_start, conclusion_text_end)
                    if period_after_conclusion != -1:
                        conclusion_text_end = period_after_conclusion + 1
                    
                    conclusion_content = text[conclusion_text_start:conclusion_text_end].strip()

                    if len(premise_content) >= self.min_length and len(conclusion_content) >= self.min_length:
                        arguments.append({
                            "type": "Argument Explicite (Mock)",
                            "premise": premise_content,
                            "conclusion": conclusion_content,
                            "confidence": 0.85,
                            "details": "Prémisse et conclusion explicitement marquées."
                        })
                        # Pour éviter de réutiliser les mêmes, on pourrait marquer les portions utilisées.
                        # Ce mock simple ne le fait pas.
                        break # On associe la première conclusion après la prémisse

        # Scénario 2: Texte contenant "donc" ou "par conséquent" comme indicateur de conclusion
        # et ce qui précède comme prémisse.
        conclusion_indicators = ["donc", "par conséquent", "ainsi"]
        for indicator in conclusion_indicators:
            indicator_match = list(re.finditer(rf"\b{indicator}\b", text, re.IGNORECASE))
            for match in indicator_match:
                premise_part = text[:match.start()].strip()
                conclusion_part = text[match.end():].strip()
                
                # Simplification: prendre la dernière phrase pour la prémisse et la première pour la conclusion
                premise_sentences = [s.strip() for s in premise_part.split('.') if s.strip()]
                conclusion_sentences = [s.strip() for s in conclusion_part.split('.') if s.strip()]

                if premise_sentences and conclusion_sentences:
                    final_premise = premise_sentences[-1]
                    final_conclusion = conclusion_sentences[0]
                    if len(final_premise) >= self.min_length and len(final_conclusion) >= self.min_length:
                        # Éviter les doublons si déjà trouvé par la méthode explicite
                        is_duplicate = False
                        for arg in arguments:
                            if arg["premise"] == final_premise and arg["conclusion"] == final_conclusion:
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            arguments.append({
                                "type": f"Argument Implicite (Mock - {indicator})",
                                "premise": final_premise,
                                "conclusion": final_conclusion,
                                "confidence": 0.70,
                                "details": f"Conclusion inférée par l'indicateur '{indicator}'."
                            })
        
        # Scénario 3: Si aucun argument trouvé, considérer le texte entier comme une "affirmation"
        if not arguments and len(text) >= self.min_length:
            arguments.append({
                "type": "Affirmation Simple (Mock)",
                "statement": text,
                "confidence": 0.50,
                "details": "Le texte est considéré comme une affirmation unique, faute d'indicateurs d'argument."
            })
            
        logger.info(f"MockArgumentMiner a trouvé {len(arguments)} arguments.")
        return arguments

    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle du mineur d'arguments."""
        return self.config