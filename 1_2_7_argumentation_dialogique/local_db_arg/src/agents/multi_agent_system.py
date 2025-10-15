from typing import Dict, List, Any
import logging
from datetime import datetime

from ..core.models import DialogueType
from .dialogue_agent import DialogueAgent
from ..protocols.persuasion_protocol import PersuasionProtocol
from ..protocols.inquiry_protocol import InquiryProtocol


class MultiAgentDialogueSystem:
    """Système de gestion pour dialogues multi-agents"""

    def __init__(self):
        self.agents: Dict[str, DialogueAgent] = {}
        self.active_dialogues: Dict[str, Dict] = {}
        self.dialogue_archive: List[Dict] = []
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("MultiAgentSystem")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def register_agent(self, agent: DialogueAgent) -> None:
        """Enregistre un agent dans le système"""
        self.agents[agent.id] = agent
        self.logger.info(f"Agent {agent.id} enregistré")

    def create_dialogue(
        self,
        agent1_id: str,
        agent2_id: str,
        topic: str,
        dialogue_type: DialogueType = DialogueType.INQUIRY,
    ) -> str:
        """Crée un nouveau dialogue entre deux agents"""
        if agent1_id not in self.agents or agent2_id not in self.agents:
            raise ValueError("Agents non trouvés")

        agent1 = self.agents[agent1_id]
        agent2 = self.agents[agent2_id]

        # Configure les protocoles
        if dialogue_type == DialogueType.PERSUASION:
            protocol = PersuasionProtocol(dialogue_type)
        else:
            protocol = InquiryProtocol(dialogue_type)

        agent1.protocol = protocol
        agent2.protocol = protocol

        dialogue_id = agent1.initiate_dialogue(topic, agent2)

        self.active_dialogues[dialogue_id] = {
            "participants": [agent1_id, agent2_id],
            "topic": topic,
            "type": dialogue_type.value,
            "started": datetime.now(),
            "current_speaker": agent1_id,
        }

        return dialogue_id

    def run_dialogue(self, dialogue_id: str, max_turns: int = 20) -> Dict[str, Any]:
        """Exécute un dialogue jusqu'à terminaison ou limite de tours"""
        if dialogue_id not in self.active_dialogues:
            raise ValueError("Dialogue non trouvé")

        dialogue_info = self.active_dialogues[dialogue_id]
        agent1_id, agent2_id = dialogue_info["participants"]
        agent1, agent2 = self.agents[agent1_id], self.agents[agent2_id]

        current_agent, other_agent = agent1, agent2
        turn_count = 0

        # Le dialogue commence avec le mouvement initial de agent1
        last_move = agent1.dialogue_history[-1] if agent1.dialogue_history else None

        while turn_count < max_turns and last_move:
            turn_count += 1

            # L'autre agent traite le mouvement et répond
            response = other_agent.process_move(last_move)

            if not response:  # Dialogue terminé
                break

            last_move = response
            current_agent, other_agent = other_agent, current_agent

        # Archive le dialogue
        summary = self._create_dialogue_summary(dialogue_id, agent1, agent2)
        self.dialogue_archive.append(summary)

        if dialogue_id in self.active_dialogues:
            del self.active_dialogues[dialogue_id]

        return summary

    def _create_dialogue_summary(
        self, dialogue_id: str, agent1: DialogueAgent, agent2: DialogueAgent
    ) -> Dict[str, Any]:
        """Crée un résumé complet du dialogue"""
        all_moves = sorted(
            agent1.dialogue_history + agent2.dialogue_history, key=lambda x: x.timestamp
        )

        return {
            "dialogue_id": dialogue_id,
            "participants": [agent1.id, agent2.id],
            "total_moves": len(all_moves),
            "moves": [
                {
                    "speaker": move.speaker,
                    "act": move.act.value,
                    "content": str(move.content),
                    "timestamp": move.timestamp.isoformat(),
                }
                for move in all_moves
            ],
            "agent1_summary": agent1.get_dialogue_summary(),
            "agent2_summary": agent2.get_dialogue_summary(),
        }

    def get_active_dialogues(self) -> Dict[str, Dict]:
        """Retourne les dialogues actifs"""
        return self.active_dialogues.copy()

    def get_dialogue_archive(self) -> List[Dict]:
        """Retourne l'archive des dialogues"""
        return self.dialogue_archive.copy()
