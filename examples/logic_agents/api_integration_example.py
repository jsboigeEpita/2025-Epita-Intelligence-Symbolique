#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple d'intégration avec l'API Web pour les agents logiques.

Cet exemple montre comment:
1. Se connecter à l'API Web
2. Convertir un texte en ensemble de croyances
3. Exécuter des requêtes sur l'ensemble de croyances
4. Générer des requêtes pertinentes
5. Interpréter les résultats

Prérequis:
- Requests installé (pip install requests)
- API Web des agents logiques accessible
"""

import json
import logging
import sys
import time
from typing import Dict, List, Any, Optional, Union

import requests

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("APIIntegrationExample")

class LogicAgentsAPI:
    """
    Client pour l'API Web des agents logiques.
    """
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialise le client API.
        
        Args:
            base_url: URL de base de l'API
            api_key: Clé API pour l'authentification
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        logger.info(f"Client API initialisé avec l'URL de base: {base_url}")
    
    def create_belief_set(self, text: str, logic_type: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convertit un texte en ensemble de croyances.
        
        Args:
            text: Texte à convertir
            logic_type: Type de logique ("propositional", "first_order", "modal")
            options: Options de conversion (optionnel)
            
        Returns:
            Réponse de l'API contenant l'ensemble de croyances créé
        """
        if options is None:
            options = {"include_explanation": True}
        
        payload = {
            "text": text,
            "logic_type": logic_type,
            "options": options
        }
        
        logger.info(f"Conversion du texte en ensemble de croyances ({logic_type})...")
        response = self._make_request("POST", "/api/logic/belief-set", payload)
        
        belief_set_id = response["belief_set"]["id"]
        logger.info(f"Ensemble de croyances créé avec ID: {belief_set_id}")
        
        return response
    
    def execute_query(self, belief_set_id: str, query: str, logic_type: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Exécute une requête sur un ensemble de croyances.
        
        Args:
            belief_set_id: ID de l'ensemble de croyances
            query: Requête à exécuter
            logic_type: Type de logique
            options: Options d'exécution (optionnel)
            
        Returns:
            Réponse de l'API contenant le résultat de la requête
        """
        if options is None:
            options = {"include_explanation": True}
        
        payload = {
            "belief_set_id": belief_set_id,
            "query": query,
            "logic_type": logic_type,
            "options": options
        }
        
        logger.info(f"Exécution de la requête: {query}")
        response = self._make_request("POST", "/api/logic/query", payload)
        
        result = response["result"]["result"]
        logger.info(f"Résultat: {result}")
        
        return response
    
    def generate_queries(self, belief_set_id: str, text: str, logic_type: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Génère des requêtes pertinentes pour un ensemble de croyances.
        
        Args:
            belief_set_id: ID de l'ensemble de croyances
            text: Texte source
            logic_type: Type de logique
            options: Options de génération (optionnel)
            
        Returns:
            Réponse de l'API contenant les requêtes générées
        """
        if options is None:
            options = {"max_queries": 5}
        
        payload = {
            "belief_set_id": belief_set_id,
            "text": text,
            "logic_type": logic_type,
            "options": options
        }
        
        logger.info("Génération de requêtes pertinentes...")
        response = self._make_request("POST", "/api/logic/generate-queries", payload)
        
        queries = response["queries"]
        logger.info(f"Requêtes générées: {queries}")
        
        return response
    
    def interpret_results(self, belief_set_id: str, logic_type: str, queries: List[str], results: List[Dict[str, Any]], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Interprète les résultats de plusieurs requêtes.
        
        Args:
            belief_set_id: ID de l'ensemble de croyances
            logic_type: Type de logique
            queries: Liste des requêtes exécutées
            results: Liste des résultats des requêtes
            options: Options d'interprétation (optionnel)
            
        Returns:
            Réponse de l'API contenant l'interprétation des résultats
        """
        if options is None:
            options = {"include_explanation": True}
        
        payload = {
            "belief_set_id": belief_set_id,
            "logic_type": logic_type,
            "queries": queries,
            "results": results,
            "options": options
        }
        
        logger.info("Interprétation des résultats...")
        response = self._make_request("POST", "/api/logic/interpret", payload)
        
        interpretation = response["interpretation"]
        logger.info(f"Interprétation: {interpretation}")
        
        return response
    
    def _make_request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Effectue une requête à l'API.
        
        Args:
            method: Méthode HTTP (GET, POST, etc.)
            endpoint: Endpoint de l'API
            payload: Données à envoyer (optionnel)
            
        Returns:
            Réponse de l'API
            
        Raises:
            Exception: Si la requête échoue
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=payload)
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête à l'API: {str(e)}")
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"Détails de l'erreur: {json.dumps(error_data, indent=2)}")
                except:
                    logger.error(f"Réponse d'erreur: {e.response.text}")
            
            raise

def process_propositional_logic_example(api_client: LogicAgentsAPI) -> None:
    """
    Traite un exemple de logique propositionnelle.
    
    Args:
        api_client: Client API
    """
    logger.info("=== Exemple de logique propositionnelle ===")
    
    # Texte à analyser
    text = """
    Si le ciel est nuageux, alors il va pleuvoir.
    Le ciel est nuageux.
    """
    
    # Convertir le texte en ensemble de croyances
    belief_set_response = api_client.create_belief_set(text, "propositional")
    belief_set_id = belief_set_response["belief_set"]["id"]
    belief_set_content = belief_set_response["belief_set"]["content"]
    
    logger.info(f"Contenu de l'ensemble de croyances: {belief_set_content}")
    
    # Exécuter une requête spécifique
    query = "pluie"
    query_response = api_client.execute_query(belief_set_id, query, "propositional")
    
    # Générer des requêtes pertinentes
    generate_response = api_client.generate_queries(belief_set_id, text, "propositional")
    queries = generate_response["queries"]
    
    # Exécuter les requêtes générées
    results = []
    for q in queries:
        result = api_client.execute_query(belief_set_id, q, "propositional")
        results.append(result["result"])
    
    # Interpréter les résultats
    api_client.interpret_results(belief_set_id, "propositional", queries, results)

def process_first_order_logic_example(api_client: LogicAgentsAPI) -> None:
    """
    Traite un exemple de logique du premier ordre.
    
    Args:
        api_client: Client API
    """
    logger.info("=== Exemple de logique du premier ordre ===")
    
    # Texte à analyser
    text = """
    Tous les hommes sont mortels.
    Socrate est un homme.
    """
    
    # Convertir le texte en ensemble de croyances
    belief_set_response = api_client.create_belief_set(text, "first_order")
    belief_set_id = belief_set_response["belief_set"]["id"]
    belief_set_content = belief_set_response["belief_set"]["content"]
    
    logger.info(f"Contenu de l'ensemble de croyances: {belief_set_content}")
    
    # Exécuter une requête spécifique
    query = "Mortel(socrate)"
    query_response = api_client.execute_query(belief_set_id, query, "first_order")
    
    # Générer des requêtes pertinentes
    generate_response = api_client.generate_queries(belief_set_id, text, "first_order")
    queries = generate_response["queries"]
    
    # Exécuter les requêtes générées
    results = []
    for q in queries:
        result = api_client.execute_query(belief_set_id, q, "first_order")
        results.append(result["result"])
    
    # Interpréter les résultats
    api_client.interpret_results(belief_set_id, "first_order", queries, results)

def process_modal_logic_example(api_client: LogicAgentsAPI) -> None:
    """
    Traite un exemple de logique modale.
    
    Args:
        api_client: Client API
    """
    logger.info("=== Exemple de logique modale ===")
    
    # Texte à analyser
    text = """
    Si une proposition est nécessairement vraie, alors elle est vraie.
    Si une proposition est vraie, alors elle est possiblement vraie.
    La somme des angles d'un triangle est nécessairement égale à 180 degrés.
    """
    
    # Convertir le texte en ensemble de croyances
    belief_set_response = api_client.create_belief_set(text, "modal")
    belief_set_id = belief_set_response["belief_set"]["id"]
    belief_set_content = belief_set_response["belief_set"]["content"]
    
    logger.info(f"Contenu de l'ensemble de croyances: {belief_set_content}")
    
    # Exécuter une requête spécifique
    query = "<>(somme_angles_triangle_180)"
    query_response = api_client.execute_query(belief_set_id, query, "modal")
    
    # Générer des requêtes pertinentes
    generate_response = api_client.generate_queries(belief_set_id, text, "modal")
    queries = generate_response["queries"]
    
    # Exécuter les requêtes générées
    results = []
    for q in queries:
        result = api_client.execute_query(belief_set_id, q, "modal")
        results.append(result["result"])
    
    # Interpréter les résultats
    api_client.interpret_results(belief_set_id, "modal", queries, results)

def main():
    """
    Fonction principale.
    """
    try:
        # Configuration de l'API
        api_base_url = "https://api.example.com"  # Remplacez par l'URL réelle de l'API
        api_key = "votre_clé_api"  # Remplacez par votre clé API
        
        # Créer le client API
        api_client = LogicAgentsAPI(api_base_url, api_key)
        
        # Traiter les exemples
        process_propositional_logic_example(api_client)
        process_first_order_logic_example(api_client)
        process_modal_logic_example(api_client)
        
        logger.info("Traitement terminé avec succès")
    
    except Exception as e:
        logger.error(f"Une erreur est survenue: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()