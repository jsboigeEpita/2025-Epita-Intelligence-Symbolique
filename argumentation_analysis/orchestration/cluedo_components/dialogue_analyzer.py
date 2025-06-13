# argumentation_analysis/orchestration/cluedo_components/dialogue_analyzer.py
from typing import List, Dict

from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState

class DialogueAnalyzer:
    """
    Analyse le contenu des dialogues pour en extraire des métadonnées
    contextuelles et de fluidité.
    """
    def __init__(self, oracle_state: CluedoOracleState):
        self.oracle_state = oracle_state

    def detect_message_type(self, content: str) -> str:
        """Détecte le type de message basé sur son contenu."""
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in ["révèle", "possède", "carte", "j'ai"]):
            return "revelation"
        elif any(keyword in content_lower for keyword in ["suggère", "propose", "suspect", "arme", "lieu"]):
            return "suggestion"
        elif any(keyword in content_lower for keyword in ["analyse", "déduction", "conclusion", "donc"]):
            return "analysis"
        elif any(keyword in content_lower for keyword in ["brillant", "exactement", "aha", "intéressant", "magistral"]):
            return "reaction"
        else:
            return "message"

    def analyze_contextual_elements(self, agent_name: str, content: str, history: List) -> None:
        """Analyse les éléments contextuels et enregistre les références/réactions."""
        content_lower = content.lower()
        
        reference_indicators = [
            ("suite à", "building_on"), ("en réaction à", "reacting_to"),
            ("après cette", "responding_to"), ("comme dit", "referencing"),
            ("précédemment", "referencing")
        ]
        
        for indicator, ref_type in reference_indicators:
            if indicator in content_lower:
                if len(history) > 1:
                    target_turn = len(history) - 1
                    self.oracle_state.record_contextual_reference(
                        source_agent=agent_name,
                        target_message_turn=target_turn,
                        reference_type=ref_type,
                        reference_content=indicator
                    )
                break
        
        emotional_patterns = self._detect_emotional_reactions(agent_name, content, history)
        for reaction in emotional_patterns:
            self.oracle_state.record_emotional_reaction(**reaction)

    def _detect_emotional_reactions(self, agent_name: str, content: str, history: List) -> List[Dict[str, str]]:
        """Détecte les réactions émotionnelles spécifiques."""
        reactions = []
        content_lower = content.lower()
        
        if len(history) < 2:
            return reactions
            
        trigger_agent = getattr(history[-2], 'author_name', history[-2].role)
        trigger_content = str(history[-2].content)
        
        agent_reactions = {
            "Watson": [
                (["brillant", "exactement", "ça colle parfaitement"], "approval"),
                (["aha", "intéressant retournement", "ça change la donne"], "surprise"),
            ],
            "Sherlock": [
                (["précisément watson", "tu vises juste", "c'est noté"], "approval"),
                (["comme prévu", "merci pour cette clarification", "parfait"], "satisfaction"),
            ],
            "Moriarty": [
                (["chaud", "très chaud", "vous brûlez"], "encouragement"),
                (["pas tout à fait", "pas si vite"], "correction"),
            ]
        }
        
        if agent_name in agent_reactions:
            for keywords, reaction_type in agent_reactions[agent_name]:
                if any(keyword in content_lower for keyword in keywords):
                    reactions.append({
                        "agent_name": agent_name, "trigger_agent": trigger_agent,
                        "trigger_content": trigger_content, "reaction_type": reaction_type,
                        "reaction_content": content[:100]
                    })
                    break
        return reactions