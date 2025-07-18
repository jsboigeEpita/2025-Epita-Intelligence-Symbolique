#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service pour l'analyse des frameworks d'argumentation.
"""

from typing import List, Dict, Any

class FrameworkService:
    """
    Fournit la logique métier pour l'analyse des frameworks d'argumentation.
    """
    def __init__(self):
        """
        Initialise le service.
        """
        pass

    def analyze_dung_framework(self, arguments: List[str], attacks: List[List[str]]) -> Dict[str, Any]:
        """
        Analyse un framework d'argumentation de Dung.
        
        NOTE: Ceci est une implémentation factice pour les tests E2E.
        """
        # Logique factice
        print(f"Analyzing framework with {len(arguments)} arguments and {len(attacks)} attacks.")
        
        # Simuler un résultat d'analyse conforme à ce que le frontend attend
        # Le frontend attend une liste de listes d'IDs d'arguments pour les extensions.
        
        # Trouver l'ID de l'argument non attaqué
        attacked_ids = {attack[1] for attack in attacks}
        accepted_args = [arg_id for arg_id in arguments if arg_id not in attacked_ids]

        result = {
            "semantics": "preferred",
            "extensions": [
                accepted_args
            ],
            "statistics": {
                "arguments_count": len(arguments),
                "attacks_count": len(attacks),
                "extensions_count": 1
            }
        }
        return result