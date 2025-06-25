# argumentation_analysis/agents/core/logic/tweety_bridge.py
"""
Pont d'interface avec le microservice Tweety pour l'exécution de requêtes logiques.

Ce module définit la classe `TweetyBridge`, qui agit comme un client HTTP pour
interagir avec le service Java TweetyProject exposé via une API REST.
"""

import logging
import requests
from typing import Tuple, Optional, Dict, List

from semantic_kernel.functions import kernel_function

# Configuration du logger
logger = logging.getLogger("Orchestration.TweetyBridge")

class TweetyBridge:
    """
    Client HTTP pour interagir avec le microservice Tweety.
    """
    
    def __init__(self, base_url: str = "http://127.0.0.1:4567"):
        """
        Initialise le client HTTP pour le service Tweety.

        Args:
            base_url (str): L'URL de base du service Tweety.
        """
        self._logger = logger
        self.base_url = base_url
        self._session = requests.Session()
        self._logger.info(f"TWEETY_BRIDGE: Client HTTP initialisé pour l'URL: {self.base_url}")

    def _post_request(self, endpoint: str, data: Dict) -> Dict:
        """Méthode générique pour les requêtes POST vers le service."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self._session.post(url, json=data, timeout=30)
            response.raise_for_status()  # Lève une exception pour les codes 4xx/5xx
            return response.json()
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Erreur de communication avec le service Tweety ({url}): {e}")
            raise RuntimeError(f"Impossible de contacter le service Tweety à {url}") from e

    @kernel_function(
        description="Exécute une requête en Logique Propositionnelle (syntaxe Tweety: !,||,=>,<=>,^^) sur un Belief Set fourni.",
        name="execute_pl_query"
    )
    def execute_pl_query(self, belief_set_content: str, query_string: str) -> str:
        """Exécute une requête en logique propositionnelle."""
        self._logger.info(f"execute_pl_query: Query='{query_string}'")
        data = {
            "belief_set": belief_set_content,
            "query": query_string
        }
        try:
            response_data = self._post_request("pl/query", data)
            # Formater la sortie pour la compatibilité
            result = response_data.get("result", False)
            return f"Query '{query_string}' is {'ACCEPTED (True)' if result else 'REJECTED (False)'}."
        except RuntimeError as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Exécute une requête en Logique du Premier Ordre sur un Belief Set fourni. Peut inclure des déclarations de signature.",
        name="execute_fol_query"
    )
    def execute_fol_query(self, belief_set_content: str, query_string: str, signature_declarations_str: Optional[str] = None) -> str:
        """Exécute une requête en logique du premier ordre."""
        self._logger.info(f"execute_fol_query: Query='{query_string}'")
        data = {
            "belief_set": belief_set_content,
            "query": query_string,
            "signature": signature_declarations_str or ""
        }
        try:
            response_data = self._post_request("fol/query", data)
            result = response_data.get("result")
            if result is None:
                return f"Tweety Result: Unknown for FOL query '{query_string}'."
            return f"Tweety Result: FOL Query '{query_string}' is {'ACCEPTED (True)' if result else 'REJECTED (False)'}."
        except RuntimeError as e:
            return f"FUNC_ERROR: {e}"

    @kernel_function(
        description="Exécute une requête en Logique Modale sur un Belief Set fourni. Spécifier la logique modale (ex: S4, K).",
        name="execute_modal_query"
    )
    def execute_modal_query(self, belief_set_content: str, query_string: str, modal_logic_str: str = "S4") -> str:
        """Exécute une requête en logique modale."""
        self._logger.info(f"execute_modal_query: Query='{query_string}', Logic: {modal_logic_str}")
        data = {
            "belief_set": belief_set_content,
            "query": query_string,
            "logic": modal_logic_str
        }
        try:
            response_data = self._post_request("modal/query", data)
            result = response_data.get("result")
            if result is None:
                return f"Tweety Result: Unknown for Modal query '{query_string}' (Logic: {modal_logic_str})."
            return f"Tweety Result: Modal Query '{query_string}' (Logic: {modal_logic_str}) is {'ACCEPTED (True)' if result else 'REJECTED (False)'}."
        except RuntimeError as e:
            return f"FUNC_ERROR: {e}"
