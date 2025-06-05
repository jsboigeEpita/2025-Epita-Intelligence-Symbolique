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
        # Combine and sort all matches to process them in order
        all_matches = sorted(premise_matches + conclusion_matches, key=lambda m: m.start())

        i = 0
        while i < len(all_matches):
            p_match = all_matches[i]
            if "prémisse" not in p_match.group(0).lower():
                i += 1
                continue

            # Find the next conclusion
            c_match = None
            if i + 1 < len(all_matches) and "conclusion" in all_matches[i+1].group(0).lower():
                c_match = all_matches[i+1]
            
            if c_match:
                premise_text_start = p_match.end()
                premise_text_end = c_match.start()
                premise_content = text[premise_text_start:premise_text_end].strip()

                conclusion_text_start = c_match.end()

                # Find the end of the conclusion (next premise or end of text)
                conclusion_text_end = len(text)
                if i + 2 < len(all_matches):
                    conclusion_text_end = all_matches[i+2].start()
                
                final_conclusion_content = text[conclusion_text_start:conclusion_text_end].strip()

                # Delimit by sentence end
                sentence_end_match = re.search(r'[.!?]', final_conclusion_content)
                if sentence_end_match:
                    final_conclusion_content = final_conclusion_content[:sentence_end_match.end()]

                if len(premise_content) >= self.min_length and len(final_conclusion_content) >= self.min_length:
                    arguments.append({
                        "type": "Argument Explicite (Mock)",
                        "premise": premise_content,
                        "conclusion": final_conclusion_content,
                        "confidence": 0.85,
                        "details": "Prémisse et conclusion explicitement marquées."
                    })
                i += 2 # Move past the premise and conclusion
            else:
                i += 1 # Move to the next match

        # Scénario 2: Texte contenant "donc" ou "par conséquent" comme indicateur de conclusion
        conclusion_indicators = ["donc", "par conséquent", "ainsi"]
        for indicator in conclusion_indicators:
            indicator_match = list(re.finditer(rf"\b{indicator}\b", text, re.IGNORECASE))
            for match in indicator_match:
                premise_part = text[:match.start()].strip()
                conclusion_part = text[match.end():].strip()

                # Simplification: prendre la dernière phrase pour la prémisse et la première pour la conclusion
                premise_sentences = [s.strip() for s in re.split(r'[.!?]', premise_part) if s.strip()]
                conclusion_sentences = [s.strip() for s in re.split(r'[.!?]', conclusion_part) if s.strip()]

                if premise_sentences and conclusion_sentences:
                    final_premise = premise_sentences[-1].rstrip(' ,')
                    final_conclusion = conclusion_sentences[0].lstrip(' ,')
                    if len(final_premise) >= self.min_length and len(final_conclusion) >= self.min_length:
                        # Éviter les doublons si déjà trouvé par la méthode explicite
                        is_duplicate = False
                        for arg in arguments:
                            if arg.get("type") == "Argument Explicite (Mock)":
                                norm_arg_premise = arg.get("premise", "").strip(" .!?").lower()
                                norm_arg_conclusion = arg.get("conclusion", "").strip(" .!?").lower()
                                norm_final_premise = final_premise.strip(" .!?").lower()
                                norm_final_conclusion = final_conclusion.strip(" .!?").lower()
                                
                                if norm_arg_premise == norm_final_premise and norm_arg_conclusion == norm_final_conclusion:
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