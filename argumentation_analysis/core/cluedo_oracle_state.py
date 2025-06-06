# argumentation_analysis/core/cluedo_oracle_state.py
"""
Extension d'EnqueteCluedoState pour supporter le workflow à 3 agents avec agent Oracle.

Cette classe étend EnqueteCluedoState pour ajouter la gestion du dataset Oracle,
des permissions par agent, et du tracking des interactions 3-agents (Sherlock→Watson→Moriarty).
"""

import uuid
import random
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from .enquete_states import EnqueteCluedoState
from ..agents.core.oracle.cluedo_dataset import CluedoDataset
from ..agents.core.oracle.permissions import QueryType, OracleResponse, get_default_cluedo_permissions


class CluedoOracleState(EnqueteCluedoState):
    """
    Extension d'EnqueteCluedoState pour supporter le workflow à 3 agents
    avec agent Oracle (Moriarty) gérant les révélations de cartes.
    
    Nouvelles fonctionnalités:
    - Gestion des cartes distribuées entre Moriarty et autres joueurs
    - CluedoDataset intégré pour révélations contrôlées
    - Système de permissions par agent
    - Tracking des interactions 3-agents
    - Logging spécialisé pour les révélations Oracle
    """
    
    def __init__(self, 
                 nom_enquete_cluedo: str, 
                 elements_jeu_cluedo: dict,
                 description_cas: str, 
                 initial_context: dict, 
                 cartes_distribuees: Optional[Dict[str, List[str]]] = None,
                 workflow_id: Optional[str] = None,
                 solution_secrete_cluedo: Optional[dict] = None,
                 oracle_strategy: str = "balanced"):
        """
        Initialise l'état Oracle étendu.
        
        Args:
            nom_enquete_cluedo: Nom de l'enquête Cluedo
            elements_jeu_cluedo: Éléments du jeu {"suspects": [], "armes": [], "lieux": []}
            description_cas: Description du cas
            initial_context: Contexte initial
            cartes_distribuees: Distribution des cartes (optionnel, sera générée si absent)
            workflow_id: ID du workflow (optionnel)
            solution_secrete_cluedo: Solution secrète (optionnel, sera générée si absente)
            oracle_strategy: Stratégie Oracle ("cooperative", "competitive", "balanced", "progressive")
        """
        # Initialisation de la classe parent
        super().__init__(
            nom_enquete_cluedo=nom_enquete_cluedo,
            elements_jeu_cluedo=elements_jeu_cluedo,
            description_cas=description_cas,
            initial_context=initial_context,
            workflow_id=workflow_id,
            solution_secrete_cluedo=solution_secrete_cluedo,
            auto_generate_solution=solution_secrete_cluedo is None
        )
        
        # Extensions Oracle
        self.oracle_strategy = oracle_strategy
        self.cartes_distribuees = cartes_distribuees or self._distribute_cards()
        
        # Création du dataset Cluedo Oracle
        from ..agents.core.oracle.permissions import RevealPolicy
        policy_mapping = {
            "cooperative": RevealPolicy.COOPERATIVE,
            "competitive": RevealPolicy.COMPETITIVE,
            "balanced": RevealPolicy.BALANCED,
            "progressive": RevealPolicy.PROGRESSIVE
        }
        
        self.cluedo_dataset = CluedoDataset(
            solution_secrete=self.solution_secrete_cluedo,
            cartes_distribuees=self.cartes_distribuees,
            reveal_policy=policy_mapping.get(oracle_strategy, RevealPolicy.BALANCED)
        )
        
        # Configuration des IDs d'agents
        self.moriarty_agent_id = f"moriarty_agent_{self.workflow_id}"
        self.sherlock_agent_id = f"sherlock_agent_{self.workflow_id}"
        self.watson_agent_id = f"watson_agent_{self.workflow_id}"
        
        # Logs et tracking spécialisés Oracle
        self.revelations_log: List[Dict[str, Any]] = []
        self.oracle_queries_log: List[Dict[str, Any]] = []
        
        # Tracking interactions 3-agents
        self.interaction_pattern: List[str] = []  # ["Sherlock", "Watson", "Moriarty", ...]
        self.oracle_queries_count = 0
        self.suggestions_validated_by_oracle: List[Dict[str, Any]] = []
        
        # Permissions par agent (configuration par défaut)
        self.agent_permissions = self._initialize_permissions()
        
        # Métriques de performance 3-agents
        self.workflow_metrics = {
            "total_turns": 0,
            "oracle_interactions": 0,
            "cards_revealed": 0,
            "suggestions_count": 0,
            "start_time": datetime.now().isoformat()
        }
        
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{self.workflow_id}")
        self._logger.info(f"CluedoOracleState initialisé avec {len(self.get_moriarty_cards())} cartes Moriarty - Stratégie: {oracle_strategy}")
    
    def _distribute_cards(self) -> Dict[str, List[str]]:
        """
        Distribue les cartes entre Moriarty et joueurs simulés en excluant la solution secrète.
        
        Returns:
            Dictionnaire {"Moriarty": [...], "AutresJoueurs": [...]}
        """
        all_elements = (
            self.elements_jeu_cluedo.get("suspects", []) + 
            self.elements_jeu_cluedo.get("armes", []) + 
            self.elements_jeu_cluedo.get("lieux", [])
        )
        
        # Exclure la solution secrète  
        solution_elements = set(self.solution_secrete_cluedo.values())
        available_cards = [card for card in all_elements if card not in solution_elements]
        
        if len(available_cards) < 2:
            raise ValueError("Pas assez de cartes disponibles après exclusion de la solution secrète")
        
        # Distribution équilibrée (Moriarty prend environ 1/3 des cartes disponibles)
        moriarty_count = max(1, len(available_cards) // 3)
        moriarty_cards = random.sample(available_cards, moriarty_count)
        autres_joueurs_cards = [card for card in available_cards if card not in moriarty_cards]
        
        distribution = {
            "Moriarty": moriarty_cards,
            "AutresJoueurs": autres_joueurs_cards
        }
        
        self._logger.info(f"Distribution des cartes: Moriarty ({len(moriarty_cards)}), Autres ({len(autres_joueurs_cards)})")
        return distribution
    
    def _initialize_permissions(self) -> Dict[str, Any]:
        """Configure les permissions d'accès pour chaque agent."""
        default_permissions = get_default_cluedo_permissions()
        
        return {
            "SherlockEnqueteAgent": {
                "can_query_oracle": True,
                "max_oracle_queries_per_turn": 3,
                "allowed_query_types": ["suggestion_validation", "clue_request", "card_inquiry"],
                "permission_rule": default_permissions.get("SherlockEnqueteAgent")
            },
            "WatsonLogicAssistant": {
                "can_query_oracle": True, 
                "max_oracle_queries_per_turn": 1,
                "allowed_query_types": ["logical_validation", "constraint_check"],
                "permission_rule": default_permissions.get("WatsonLogicAssistant")
            },
            "MoriartyInterrogatorAgent": {
                "can_access_dataset": True,
                "revelation_strategy": self.oracle_strategy,
                "can_simulate_other_players": True,
                "is_oracle": True
            }
        }
    
    # Méthodes Oracle spécialisées
    
    def query_oracle(self, agent_name: str, query_type: str, query_params: Dict[str, Any]) -> OracleResponse:
        """
        Interface pour interroger l'agent Oracle.
        
        Args:
            agent_name: Nom de l'agent demandeur
            query_type: Type de requête (string sera converti en QueryType)
            query_params: Paramètres spécifiques à la requête
            
        Returns:
            OracleResponse avec autorisation et données
        """
        try:
            # Conversion du type de requête
            query_type_enum = QueryType(query_type)
        except ValueError:
            return OracleResponse(
                authorized=False,
                message=f"Type de requête invalide: {query_type}",
                agent_name=agent_name
            )
        
        # Vérification permissions
        if not self._agent_can_query_oracle(agent_name, query_type_enum):
            return OracleResponse(
                authorized=False,
                message=f"Permission refusée pour {agent_name}:{query_type}",
                agent_name=agent_name
            )
        
        # Délégation au dataset Oracle
        try:
            response = self.cluedo_dataset.process_query(agent_name, query_type_enum, query_params)
            
            # Conversion en OracleResponse
            oracle_response = OracleResponse(
                authorized=response.success,
                data=result.data if result.success else None,
                message=result.message,
                query_type=query_type_enum,
                revealed_information=self._extract_revealed_info_from_result(result),
                agent_name=agent_name,
                metadata=result.metadata
            )
            
        except Exception as e:
            self._logger.error(f"Erreur lors de la requête Oracle: {e}", exc_info=True)
            oracle_response = OracleResponse(
                authorized=False,
                message=f"Erreur Oracle: {str(e)}",
                query_type=query_type_enum,
                agent_name=agent_name,
                metadata={"error": str(e)}
            )
        
        # Logging de l'interaction
        self._log_oracle_interaction(agent_name, query_type_enum, oracle_response, query_params)
        
        self.oracle_queries_count += 1
        self.workflow_metrics["oracle_interactions"] += 1
        
        return oracle_response
    
    def _agent_can_query_oracle(self, agent_name: str, query_type: QueryType) -> bool:
        """Vérifie si un agent peut interroger l'Oracle."""
        permissions = self.agent_permissions.get(agent_name, {})
        
        if not permissions.get("can_query_oracle", False):
            return False
        
        allowed_types = permissions.get("allowed_query_types", [])
        return query_type.value in allowed_types
    
    def _extract_revealed_info_from_result(self, result) -> List[str]:
        """Extrait les informations révélées d'un QueryResult."""
        revealed_info = []
        
        if hasattr(result, 'data') and result.data:
            if isinstance(result.data, dict):
                # Pour les ValidationResult
                if "revealed_cards" in result.data:
                    revealed_cards = result.data["revealed_cards"]
                    if isinstance(revealed_cards, list):
                        for card_info in revealed_cards:
                            if isinstance(card_info, dict) and "value" in card_info:
                                revealed_info.append(card_info["value"])
                
                # Pour les révélations directes
                if "revelation" in result.data:
                    revelation = result.data["revelation"]
                    if hasattr(revelation, "card_revealed"):
                        revealed_info.append(revelation.card_revealed)
        
        return revealed_info
    
    def _log_oracle_interaction(self, agent_name: str, query_type: QueryType, response: OracleResponse, query_params: Dict[str, Any]) -> None:
        """Enregistre une interaction Oracle dans les logs spécialisés."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "turn_number": len(self.interaction_pattern),
            "querying_agent": agent_name,
            "query_type": query_type.value,
            "query_params": query_params,
            "oracle_response": {
                "authorized": response.authorized,
                "message": response.message,
                "revealed_information": response.revealed_information
            },
            "workflow_id": self.workflow_id
        }
        
        self.oracle_queries_log.append(log_entry)
        
        # Log des révélations séparément
        if response.revealed_information:
            for revealed_item in response.revealed_information:
                revelation_log = {
                    "timestamp": datetime.now().isoformat(),
                    "revealed_item": revealed_item,
                    "revealed_to": agent_name,
                    "revealed_by": "MoriartyInterrogatorAgent",
                    "query_type": query_type.value,
                    "turn_number": len(self.interaction_pattern)
                }
                self.revelations_log.append(revelation_log)
                self.workflow_metrics["cards_revealed"] += 1
    
    # Interface pour suggestions Cluedo avec Oracle
    
    def validate_suggestion_with_oracle(self, suspect: str, arme: str, lieu: str, suggesting_agent: str) -> Dict[str, Any]:
        """
        Valide une suggestion Cluedo via l'Oracle et enregistre le résultat.
        
        Args:
            suspect: Suspect suggéré
            arme: Arme suggérée
            lieu: Lieu suggéré
            suggesting_agent: Agent qui fait la suggestion
            
        Returns:
            Dictionnaire avec le résultat de validation
        """
        # Enregistrement de la suggestion
        suggestion_record = {
            "timestamp": datetime.now().isoformat(),
            "suggestion": {"suspect": suspect, "arme": arme, "lieu": lieu},
            "suggesting_agent": suggesting_agent,
            "turn_number": len(self.interaction_pattern)
        }
        
        self.suggestions_historique.append(suggestion_record)
        self.workflow_metrics["suggestions_count"] += 1
        
        # Validation via Oracle
        oracle_response = self.query_oracle(
            agent_name=suggesting_agent,
            query_type="suggestion_validation",
            query_params={
                "suggestion": {"suspect": suspect, "arme": arme, "lieu": lieu}
            }
        )
        
        # Enrichissement du record avec le résultat Oracle
        suggestion_record["oracle_response"] = {
            "authorized": oracle_response.authorized,
            "can_refute": oracle_response.data.can_refute if oracle_response.data else False,
            "revealed_cards": oracle_response.revealed_information,
            "message": oracle_response.message
        }
        
        self.suggestions_validated_by_oracle.append(suggestion_record)
        
        return suggestion_record
    
    # Méthodes d'accès aux données Oracle
    
    def get_moriarty_cards(self) -> List[str]:
        """Retourne les cartes que possède Moriarty."""
        return self.cluedo_dataset.get_moriarty_cards()
    
    def get_autres_joueurs_cards(self) -> List[str]:
        """Retourne les cartes des autres joueurs simulés."""
        return self.cluedo_dataset.get_autres_joueurs_cards()
    
    def get_revealed_cards_to_agent(self, agent_name: str) -> List[str]:
        """Retourne les cartes révélées à un agent spécifique."""
        return self.cluedo_dataset.get_revealed_cards_to_agent(agent_name)
    
    def get_oracle_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques complètes de l'Oracle."""
        dataset_stats = self.cluedo_dataset.get_statistics()
        
        stats = {
            "workflow_id": self.workflow_id,
            "oracle_strategy": self.oracle_strategy,
            "workflow_metrics": self.workflow_metrics.copy(),
            "agent_interactions": {
                "total_turns": len(self.interaction_pattern),
                "interaction_pattern": self.interaction_pattern[-10:],  # 10 dernières interactions
                "oracle_queries": self.oracle_queries_count,
                "suggestions_validated": len(self.suggestions_validated_by_oracle)
            },
            "cards_distribution": {
                "moriarty_cards": len(self.get_moriarty_cards()),
                "autres_joueurs_cards": len(self.get_autres_joueurs_cards()),
                "total_revealed": len(self.revelations_log)
            },
            "dataset_statistics": dataset_stats,
            "recent_revelations": self.revelations_log[-5:] if self.revelations_log else []
        }
        
        return stats
    
    # Gestion du workflow 3-agents
    
    def record_agent_turn(self, agent_name: str, action_type: str, action_details: Dict[str, Any] = None) -> None:
        """
        Enregistre un tour d'agent dans le pattern d'interaction.
        
        Args:
            agent_name: Nom de l'agent ("Sherlock", "Watson", "Moriarty")
            action_type: Type d'action ("suggestion", "validation", "revelation", etc.)
            action_details: Détails de l'action (optionnel)
        """
        self.interaction_pattern.append(agent_name)
        self.workflow_metrics["total_turns"] += 1
        
        # Log de l'action
        self.add_log_message(
            agent_source=agent_name,
            message_type=f"agent_turn_{action_type}",
            content={
                "action_type": action_type,
                "turn_number": len(self.interaction_pattern),
                "details": action_details or {}
            }
        )
    
    def get_current_turn_info(self) -> Dict[str, Any]:
        """Retourne les informations sur le tour actuel."""
        return {
            "turn_number": len(self.interaction_pattern),
            "last_agent": self.interaction_pattern[-1] if self.interaction_pattern else None,
            "total_oracle_queries": self.oracle_queries_count,
            "cards_revealed_count": len(self.revelations_log),
            "suggestions_count": len(self.suggestions_historique)
        }
    
    def is_game_solvable_by_elimination(self) -> bool:
        """Vérifie si le jeu peut être résolu par élimination complète."""
        return self.cluedo_dataset.is_game_solvable_by_elimination()
    
    def reset_oracle_state(self) -> None:
        """Remet à zéro l'état Oracle pour une nouvelle partie."""
        self.revelations_log.clear()
        self.oracle_queries_log.clear()
        self.interaction_pattern.clear()
        self.suggestions_validated_by_oracle.clear()
        self.oracle_queries_count = 0
        
        # Reset des métriques
        self.workflow_metrics = {
            "total_turns": 0,
            "oracle_interactions": 0,
            "cards_revealed": 0,
            "suggestions_count": 0,
            "start_time": datetime.now().isoformat()
        }
        
        # Reset de l'état parent
        self.is_solution_proposed = False
        self.final_solution = None
        
        self._logger.info(f"État Oracle {self.workflow_id} remis à zéro")
    
    # Méthodes de compatibilité avec l'orchestration existante
    
    def get_proposed_solution(self) -> Optional[Dict[str, str]]:
        """Retourne la solution proposée (compatibilité orchestration)."""
        return self.final_solution
    
    def has_solution_proposed(self) -> bool:
        """Vérifie si une solution a été proposée (compatibilité orchestration)."""
        return self.is_solution_proposed
    
    def get_game_progress_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de la progression du jeu."""
        return {
            "workflow_id": self.workflow_id,
            "oracle_strategy": self.oracle_strategy,
            "turns_completed": len(self.interaction_pattern),
            "oracle_queries": self.oracle_queries_count,
            "cards_revealed": len(self.revelations_log),
            "suggestions_made": len(self.suggestions_historique),
            "solution_proposed": self.is_solution_proposed,
            "can_solve_by_elimination": self.is_game_solvable_by_elimination(),
            "moriarty_cards_count": len(self.get_moriarty_cards()),
            "latest_interactions": self.interaction_pattern[-5:] if self.interaction_pattern else []
        }