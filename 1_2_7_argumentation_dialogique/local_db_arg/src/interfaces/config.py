import json
import yaml
from typing import Dict, Any

from ..core.models import DialogueType, Proposition, Argument
from ..core.knowledge_base import KnowledgeBase
from ..agents.dialogue_agent import DialogueAgent
from ..protocols.persuasion_protocol import PersuasionProtocol
from ..protocols.inquiry_protocol import InquiryProtocol


class DialogueSystemConfig:
    """Configuration du système de dialogue"""

    @staticmethod
    def load_from_file(filepath: str) -> Dict[str, Any]:
        """Charge la configuration depuis un fichier"""
        with open(filepath, "r", encoding="utf-8") as f:
            if filepath.endswith(".yaml") or filepath.endswith(".yml"):
                return yaml.safe_load(f)
            else:
                return json.load(f)

    @staticmethod
    def create_agent_from_config(config: Dict[str, Any]) -> DialogueAgent:
        """Crée un agent depuis une configuration"""
        # Crée la base de connaissances
        kb = KnowledgeBase()

        # Ajoute les propositions
        for prop_data in config.get("propositions", []):
            prop = Proposition(
                content=prop_data["content"],
                truth_value=prop_data.get("truth_value"),
                confidence=prop_data.get("confidence", 1.0),
            )
            kb.add_proposition(prop)

        # Ajoute les arguments
        for arg_data in config.get("arguments", []):
            premises = [Proposition(p) for p in arg_data["premises"]]
            conclusion = Proposition(arg_data["conclusion"])
            arg = Argument(
                id=arg_data.get("id", ""),
                premises=premises,
                conclusion=conclusion,
                strength=arg_data.get("strength", 1.0),
            )
            kb.add_argument(arg)

        # Détermine le protocole
        dialogue_type = DialogueType(config.get("dialogue_type", "inquiry"))
        if dialogue_type == DialogueType.PERSUASION:
            protocol = PersuasionProtocol(dialogue_type)
        else:
            protocol = InquiryProtocol(dialogue_type)

        return DialogueAgent(
            agent_id=config["id"],
            knowledge_base=kb,
            protocol=protocol,
            strategy=config.get("strategy", "collaborative"),
        )
