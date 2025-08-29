# -*- coding: utf-8 -*-
from typing import Dict, Any

class ChaoticPlugin:
    """
    Un plugin de test conçu pour simuler des scénarios d'erreur contrôlés.
    """

    def process_or_fail(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un dictionnaire ou lève une ValueError si la clé "fail" est True.

        Args:
            data: Le dictionnaire d'entrée.

        Returns:
            Le dictionnaire traité avec un statut "processed".

        Raises:
            ValueError: Si data["fail"] est True.
        """
        if data.get("fail", False):
            raise ValueError("Échec intentionnel simulé par le ChaoticPlugin.")
        
        data["status"] = "processed"
        return data