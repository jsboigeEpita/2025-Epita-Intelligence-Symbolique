# -*- coding: utf-8 -*-
from typing import Dict, Any


class ChaoticPlugin:
    """
    Un plugin de test conçu pour simuler des scénarios d'erreur contrôlés.
    """

    def process_or_fail(self, fail: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Traite les arguments ou lève une ValueError si fail est True.

        Args:
            fail: Si True, lève une ValueError.
            **kwargs: Données supplémentaires.

        Returns:
            Le dictionnaire traité avec un statut "processed".

        Raises:
            ValueError: Si fail est True.
        """
        if fail:
            raise ValueError("Échec intentionnel simulé par le ChaoticPlugin.")

        result = dict(kwargs)
        result["status"] = "processed"
        return result
