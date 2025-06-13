# argumentation_analysis/orchestration/cluedo_components/suggestion_handler.py
import logging
from typing import Optional, Dict, Any

from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent

logger = logging.getLogger(__name__)

class SuggestionHandler:
    """
    Gère l'extraction et le traitement des suggestions Cluedo faites par les agents.
    """
    def __init__(self, moriarty_agent: MoriartyInterrogatorAgent):
        self.moriarty_agent = moriarty_agent

    def extract_cluedo_suggestion(self, message_content: str) -> Optional[Dict[str, str]]:
        """
        Extrait une suggestion Cluedo d'un message (suspect, arme, lieu).
        
        Args:
            message_content: Contenu du message à analyser
            
        Returns:
            Dict avec suspect/arme/lieu ou None si pas de suggestion détectée
        """
        content_lower = message_content.lower()
        
        suggestion_keywords = ['suggère', 'propose', 'accuse', 'pense que', 'suspect', 'suppose']
        if not any(keyword in content_lower for keyword in suggestion_keywords):
            return None
        
        suspects = ["colonel moutarde", "professeur violet", "mademoiselle rose", "docteur orchidée"]
        armes = ["poignard", "chandelier", "revolver", "corde"]
        lieux = ["salon", "cuisine", "bureau", "bibliothèque"]
        
        found_suspect = next((s.title() for s in suspects if s in content_lower), None)
        found_arme = next((a.title() for a in armes if a in content_lower), None)
        found_lieu = next((l.title() for l in lieux if l in content_lower), None)
        
        if sum(x is not None for x in [found_suspect, found_arme, found_lieu]) >= 2:
            return {
                "suspect": found_suspect or "Indéterminé",
                "arme": found_arme or "Indéterminée", 
                "lieu": found_lieu or "Indéterminé"
            }
        
        return None

    async def force_moriarty_oracle_revelation(self, suggestion: Dict[str, str], suggesting_agent: str) -> Optional[Dict[str, Any]]:
        """
        Force Moriarty à révéler ses cartes pour une suggestion donnée.
        
        Args:
            suggestion: Dict avec suspect/arme/lieu
            suggesting_agent: Nom de l'agent qui fait la suggestion
            
        Returns:
            Réponse Oracle de Moriarty ou None si erreur
        """
        try:
            logger.info(f"🔮 Force Oracle révélation: {suggestion} par {suggesting_agent}")
            
            oracle_result = self.moriarty_agent.validate_suggestion_cluedo(
                suspect=suggestion.get('suspect', ''),
                arme=suggestion.get('arme', ''),
                lieu=suggestion.get('lieu', ''),
                suggesting_agent=suggesting_agent
            )
            
            if oracle_result.authorized and oracle_result.data and oracle_result.data.can_refute:
                revealed_cards = oracle_result.revealed_information or []
                content = f"*sourire énigmatique* Ah, {suggesting_agent}... Je possède {', '.join(revealed_cards)} ! Votre théorie s'effondre."
                return {
                    "content": content, "type": "oracle_revelation", "revealed_cards": revealed_cards,
                    "can_refute": True, "suggestion": suggestion
                }
            else:
                content = f"*silence inquiétant* Intéressant, {suggesting_agent}... Je ne peux rien révéler sur cette suggestion."
                return {
                    "content": content, "type": "oracle_no_refutation", "revealed_cards": [],
                    "can_refute": False, "suggestion": suggestion, "warning": "Suggestion potentiellement correcte"
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur Oracle révélation: {e}", exc_info=True)
            error_content = f"*confusion momentanée* Pardonnez-moi, {suggesting_agent}... Un mystère technique m'empêche de répondre."
            return {
                "content": error_content, "type": "oracle_error", "revealed_cards": [],
                "can_refute": False, "error": str(e)
            }