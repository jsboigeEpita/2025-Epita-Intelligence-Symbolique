#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service pour l'analyse des frameworks d'argumentation.
"""

from typing import List, Dict, Any
import logging
import time
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
        self.logger.debug("Initializing FrameworkService...")
        try:
            # Initialise le pont TweetyProject (singleton)
            self.tweety_bridge = TweetyBridge.get_instance()
            self.logger.info(
                "--- FrameworkService INITIALIZED with real TweetyBridge ---"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize TweetyBridge: {e}", exc_info=True)
            self.tweety_bridge = None
        self.logger.debug("FrameworkService initialization complete.")

    def analyze_dung_framework(
        self, arguments: List[str], attacks: List[List[str]]
    ) -> Dict[str, Any]:
        """
        Analyse un framework d'argumentation de Dung en utilisant la vraie logique métier via TweetyProject.
        """
        self.logger.debug(
            f"Entering analyze_dung_framework with {len(arguments)} arguments and {len(attacks)} attacks."
        )
        start_time = time.time()

        if not self.tweety_bridge:
            self.logger.error("TweetyBridge not initialized. Cannot perform analysis.")
            return {
                "error": "TweetyBridge not initialized. Cannot perform analysis.",
                "status_code": 500,
            }

        self.logger.debug("Forwarding analysis request to the real AFHandler.")

        try:
            # Appel de la logique réelle via le handler
            self.logger.debug(
                "Calling tweety_bridge.af_handler.analyze_dung_framework..."
            )
            result = self.tweety_bridge.af_handler.analyze_dung_framework(
                arguments=arguments, attacks=attacks, semantics="preferred"
            )
            end_time = time.time()
            self.logger.debug(
                f"Analysis successful. Duration: {end_time - start_time:.4f} seconds."
            )
            return result
        except Exception as e:
            end_time = time.time()
            self.logger.error(
                f"An error occurred during framework analysis after {end_time - start_time:.4f} seconds: {e}",
                exc_info=True,
            )
            return {"error": f"An unexpected error occurred: {e}", "status_code": 500}

    def is_healthy(self) -> bool:
        """
        #1864 : contrat de santé exigé par le dict AppServices.is_healthy() du
        serveur MCP — implémenté sur l'état réel mesuré dans __init__ (le pont
        est construit ou il ne l'est pas), même forme que les services frères
        (FallacyService : ``is_initialized or bool(self.fallacy_patterns)``).
        Le pont est toute la capacité du service : analyze_dung_framework rend
        une erreur 500 sans lui. Ne mesure pas « JVM démarrée » — c'est le
        rôle de la clé ``jvm`` du même dict ; ici, seulement que le pont (et
        son ensure JVM) s'est construit.
        """
        return self.tweety_bridge is not None
