#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service pour l'analyse des frameworks d'argumentation.
"""

from typing import List, Dict, Any
import logging
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

class FrameworkService:
    """
    Fournit la logique métier pour l'analyse des frameworks d'argumentation.
    """
    def __init__(self):
        """
        Initialise le service en se connectant au pont Tweety.
        """
        self.logger = logging.getLogger("WebAPI.FrameworkService")
        try:
            # Initialise le pont TweetyProject (singleton)
            self.tweety_bridge = TweetyBridge.get_instance()
            self.logger.info("--- FrameworkService INITIALIZED with real TweetyBridge ---")
        except Exception as e:
            self.logger.error(f"Failed to initialize TweetyBridge: {e}", exc_info=True)
            self.tweety_bridge = None

    def analyze_dung_framework(self, arguments: List[str], attacks: List[List[str]]) -> Dict[str, Any]:
        """
        Analyse un framework d'argumentation de Dung en utilisant la vraie logique métier via TweetyProject.
        """
        if not self.tweety_bridge:
            return {
                "error": "TweetyBridge not initialized. Cannot perform analysis.",
                "status_code": 500
            }
        
        self.logger.info("Forwarding analysis request to the real AFHandler.")
        
        try:
            # Appel de la logique réelle via le handler
            result = self.tweety_bridge.af_handler.analyze_dung_framework(
                arguments=arguments,
                attacks=attacks,
                semantics="preferred"
            )
            return result
        except Exception as e:
            self.logger.error(f"An error occurred during framework analysis: {e}", exc_info=True)
            return {
                "error": f"An unexpected error occurred: {e}",
                "status_code": 500
            }