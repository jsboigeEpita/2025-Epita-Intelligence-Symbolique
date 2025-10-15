# Fichier : argumentation_analysis/utils/path_operations.py

import os
from argumentation_analysis.paths import ROOT_DIR


def get_prompt_path(agent_name: str, filename: str = "skprompt.txt") -> str:
    """
    Construit le chemin d'accès complet au fichier de prompt d'un agent.

    Args:
        agent_name (str): Le nom du répertoire de l'agent (ex: "InformalFallacyAgent").
        filename (str, optional): Le nom du fichier de prompt.
            Defaults to "skprompt.txt".

    Returns:
        str: Le chemin d'accès complet et absolu au fichier de prompt.
    """
    return os.path.join(ROOT_DIR, "agents", "prompts", agent_name, filename)
