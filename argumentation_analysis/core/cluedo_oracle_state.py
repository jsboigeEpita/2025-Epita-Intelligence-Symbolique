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
        
        # Initialisation du logger AVANT utilisation
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{self.workflow_id}")
        
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
        
        # PHASE C: Mémoire contextuelle pour continuité narrative
        self.conversation_history: List[Dict[str, Any]] = []  # Messages complets avec contexte
        self.contextual_references: List[Dict[str, Any]] = []  # Références entre messages
        self.emotional_reactions: List[Dict[str, Any]] = []  # Réactions émotionnelles enregistrées
        
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
    
    # PHASE C: Méthodes de mémoire contextuelle pour fluidité transitions
    
    def add_conversation_message(self, agent_name: str, content: str, message_type: str = "message") -> None:
        """
        Ajoute un message à l'historique conversationnel avec contexte.
        
        Args:
            agent_name: Nom de l'agent qui envoie le message
            content: Contenu du message
            message_type: Type de message ("message", "revelation", "suggestion", etc.)
        """
        message_entry = {
            "timestamp": datetime.now().isoformat(),
            "turn_number": len(self.conversation_history) + 1,
            "agent_name": agent_name,
            "content": content,
            "message_type": message_type,
            "content_preview": content[:100] + "..." if len(content) > 100 else content
        }
        
        self.conversation_history.append(message_entry)
        self._logger.debug(f"Message conversationnel ajouté: {agent_name} - {message_type}")
    
    def get_recent_context(self, num_messages: int = 3) -> List[Dict[str, Any]]:
        """
        Récupère le contexte des N derniers messages pour maintenir la continuité.
        
        Args:
            num_messages: Nombre de messages récents à récupérer (défaut: 3)
            
        Returns:
            Liste des messages récents avec contexte
        """
        if not self.conversation_history:
            return []
        
        recent_messages = self.conversation_history[-num_messages:] if len(self.conversation_history) >= num_messages else self.conversation_history
        
        # Enrichissement avec informations contextuelles
        enriched_context = []
        for msg in recent_messages:
            enriched_msg = msg.copy()
            enriched_msg["context_info"] = {
                "is_revelation": "révèle" in msg["content"].lower() or msg["message_type"] == "revelation",
                "is_suggestion": "suggère" in msg["content"].lower() or msg["message_type"] == "suggestion",
                "mentions_previous": self._check_contextual_references(msg["content"]),
                "agent_role": self._get_agent_role_context(msg["agent_name"])
            }
            enriched_context.append(enriched_msg)
        
        return enriched_context
    
    def record_contextual_reference(self, source_agent: str, target_message_turn: int, reference_type: str, reference_content: str) -> None:
        """
        Enregistre une référence contextuelle explicite entre messages.
        
        Args:
            source_agent: Agent qui fait la référence
            target_message_turn: Numéro du tour du message référencé
            reference_type: Type de référence ("response_to", "building_on", "reacting_to")
            reference_content: Contenu spécifique de la référence
        """
        reference_entry = {
            "timestamp": datetime.now().isoformat(),
            "source_agent": source_agent,
            "source_turn": len(self.conversation_history),
            "target_turn": target_message_turn,
            "reference_type": reference_type,
            "reference_content": reference_content
        }
        
        self.contextual_references.append(reference_entry)
        self._logger.info(f"Reference contextuelle: {source_agent} -> tour {target_message_turn} ({reference_type})")
    
    def record_emotional_reaction(self, agent_name: str, trigger_agent: str, trigger_content: str, reaction_type: str, reaction_content: str) -> None:
        """
        Enregistre une réaction émotionnelle d'un agent.
        
        Args:
            agent_name: Agent qui réagit
            trigger_agent: Agent qui a déclenché la réaction
            trigger_content: Contenu qui a déclenché la réaction
            reaction_type: Type de réaction ("approval", "surprise", "analysis", "excitement")
            reaction_content: Contenu de la réaction
        """
        reaction_entry = {
            "timestamp": datetime.now().isoformat(),
            "turn_number": len(self.conversation_history),
            "reacting_agent": agent_name,
            "trigger_agent": trigger_agent,
            "trigger_content": trigger_content[:100] + "..." if len(trigger_content) > 100 else trigger_content,
            "reaction_type": reaction_type,
            "reaction_content": reaction_content
        }
        
        self.emotional_reactions.append(reaction_entry)
        self._logger.info(f"Reaction emotionnelle: {agent_name} -> {reaction_type} (trigger: {trigger_agent})")
    
    def get_contextual_prompt_addition(self, current_agent: str) -> str:
        """
        Génère l'addition au prompt basée sur le contexte récent pour maintenir la fluidité.
        
        Args:
            current_agent: Nom de l'agent actuel
            
        Returns:
            Texte à ajouter au prompt pour référencer le contexte
        """
        recent_context = self.get_recent_context(3)
        if not recent_context:
            return ""
        
        # Générer le contexte pour le prompt
        context_lines = ["\n--- CONTEXTE RÉCENT POUR CONTINUITÉ ---"]
        
        for i, msg in enumerate(recent_context):
            turn_info = f"Tour {msg['turn_number']}"
            agent_info = f"{msg['agent_name']}"
            content_preview = msg["content_preview"]
            
            if msg["context_info"]["is_revelation"]:
                context_lines.append(f"{turn_info} - {agent_info} (RÉVÉLATION): {content_preview}")
            elif msg["context_info"]["is_suggestion"]:
                context_lines.append(f"{turn_info} - {agent_info} (SUGGESTION): {content_preview}")
            else:
                context_lines.append(f"{turn_info} - {agent_info}: {content_preview}")
        
        # Directives spécifiques pour l'agent actuel
        context_lines.append(f"\n--- INSTRUCTIONS CONTINUITÉ POUR {current_agent.upper()} ---")
        context_lines.append("- RÉFÉRENCE OBLIGATOIRE au message précédent")
        context_lines.append("- Utilise des connecteurs: 'Suite à', 'En réaction à', 'Après cette révélation'")
        
        if current_agent == "Watson":
            context_lines.append("- Réagis aux déductions de Sherlock: 'Brillant !', 'Exactement !', 'Ça colle parfaitement'")
            context_lines.append("- Réagis aux révélations de Moriarty: 'Aha !', 'Intéressant retournement', 'Ça change la donne'")
        elif current_agent == "Sherlock":
            context_lines.append("- Réagis aux analyses de Watson: 'Précisément Watson', 'Tu vises juste', 'C'est noté'")
            context_lines.append("- Réagis aux révélations de Moriarty: 'Comme prévu', 'Merci pour cette clarification', 'Parfait'")
        elif current_agent == "Moriarty":
            context_lines.append("- Réagis aux hypothèses: 'Chaud... très chaud', 'Pas tout à fait', 'Vous brûlez'")
            context_lines.append("- Réagis aux succès: 'Magistral !', 'Vous m'impressionnez', 'Bien joué'")
            context_lines.append("- Attends qu'une hypothèse soit formulée avant de révéler")
            context_lines.append("- Crée du suspense avec 'Hmm... pas si vite' avant révélation")
        
        context_lines.append("--- FIN CONTEXTE ---\n")
        
        return "\n".join(context_lines)
    
    def _check_contextual_references(self, content: str) -> bool:
        """Vérifie si un message contient des références contextuelles."""
        reference_keywords = [
            "suite à", "en réaction à", "après cette", "comme dit", "précédemment",
            "brillant", "exactement", "aha", "intéressant", "précisément", "comme prévu",
            "chaud", "magistral", "bien joué", "vous m'impressionnez"
        ]
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in reference_keywords)
    
    def _get_agent_role_context(self, agent_name: str) -> str:
        """Retourne le contexte de rôle d'un agent."""
        role_map = {
            "Sherlock": "Enquêteur principal - Déductions",
            "Watson": "Assistant logique - Analyses",
            "Moriarty": "Oracle - Révélations"
        }
        return role_map.get(agent_name, "Agent inconnu")
    
    def get_fluidity_metrics(self) -> Dict[str, Any]:
        """
        Calcule les métriques de fluidité pour évaluation Phase C.
        
        Returns:
            Dictionnaire avec les métriques de fluidité
        """
        total_messages = len(self.conversation_history)
        contextual_refs = len(self.contextual_references)
        emotional_reactions = len(self.emotional_reactions)
        
        if total_messages == 0:
            return {
                "total_messages": 0,
                "contextual_reference_rate": 0.0,
                "emotional_reaction_rate": 0.0,
                "fluidity_score": 0.0,
                "narrative_continuity": "Aucune donnée"
            }
        
        # Calcul des taux
        ref_rate = (contextual_refs / total_messages) * 100
        reaction_rate = (emotional_reactions / total_messages) * 100
        
        # Score de fluidité basé sur les métriques
        # Cible: >90% références, >70% réactions → score 6.5+/10
        fluidity_score = min(10.0, (ref_rate * 0.4 + reaction_rate * 0.6) / 10)
        
        # Évaluation narrative
        if ref_rate >= 90 and reaction_rate >= 70:
            narrative_quality = "Excellente continuité"
        elif ref_rate >= 70 and reaction_rate >= 50:
            narrative_quality = "Bonne continuité"
        elif ref_rate >= 50:
            narrative_quality = "Continuité modérée"
        else:
            narrative_quality = "Continuité faible"
        
        return {
            "total_messages": total_messages,
            "contextual_references": contextual_refs,
            "emotional_reactions": emotional_reactions,
            "contextual_reference_rate": round(ref_rate, 1),
            "emotional_reaction_rate": round(reaction_rate, 1),
            "fluidity_score": round(fluidity_score, 1),
            "narrative_continuity": narrative_quality,
            "phase_c_target": {
                "reference_target": 90.0,
                "reaction_target": 70.0,
                "score_target": 6.5
            }
        }
    
    # PHASE D: Méthodes avancées pour trace idéale (8.0+/10)
    
    def add_dramatic_revelation(self, content: str, intensity: float = 0.7,
                              use_false_lead: bool = False) -> str:
        """
        Ajoute une révélation avec dramaturgie Phase D.
        
        Args:
            content: Contenu à révéler
            intensity: Intensité dramatique (0.0-1.0)
            use_false_lead: Utiliser une fausse piste (20% de chance)
        
        Returns:
            Révélation formatée avec dramaturgie optimale
        """
        import random
        
        # Fausses pistes sophistiquées (20% des révélations)
        if use_false_lead and random.random() < 0.2:
            false_lead_templates = [
                {
                    "setup": "Je dois avouer... j'ai le {element}",
                    "misdirection": "Mais ce n'est pas ce que vous pensez...",
                    "reveal": "Car en fait, voici la vraie révélation : **{content}**"
                },
                {
                    "setup": "Votre hypothèse me rappelle quelque chose...",
                    "misdirection": "Oui, quelque chose d'important...",
                    "reveal": "Voici ce que vous devez savoir : **{content}**"
                }
            ]
            
            template = random.choice(false_lead_templates)
            return f"{template['setup']}\n\n{template['misdirection']}\n\n{template['reveal'].format(content=content)}"
        
        # Révélations progressives avec build-up dramatique
        suspense_phrases = [
            "*pause réfléchie*",
            "Hmm... cette direction...",
            "*regard pensif*",
            "Intéressant, très intéressant..."
        ]
        
        if intensity > 0.8:
            suspense_phrases.extend([
                "*silence dramatique*",
                "Vous touchez au cœur du mystère...",
                "*sourire énigmatique*"
            ])
        
        transition_phrases = [
            "Puisque vous y êtes presque...",
            "Votre perspicacité mérite une réponse...",
            "Je dois reconnaître votre talent...",
            "Cette déduction m'oblige à révéler..."
        ]
        
        suspense = random.choice(suspense_phrases)
        transition = random.choice(transition_phrases)
        
        return f"{suspense}\n\n{transition}\n\n**{content}**"
    
    def apply_conversational_polish_to_message(self, agent_name: str, content: str) -> str:
        """
        Applique le polish conversationnel Phase D spécifique à l'agent.
        
        Args:
            agent_name: Nom de l'agent
            content: Contenu de base à polir
        
        Returns:
            Contenu poli avec expressions idiomatiques
        """
        import random
        
        polish_phrases = {
            "Watson": [
                "Absolument génial !",
                "Ça colle parfaitement !",
                "Brillante déduction !",
                "Exactement ce que je pensais !",
                "Vous m'épatez toujours !"
            ],
            "Sherlock": [
                "Précisément, Watson",
                "Tu vises dans le mille",
                "C'est exactement cela",
                "Parfaitement observé",
                "Comme je le supposais"
            ],
            "Moriarty": [
                "Magistral, messieurs !",
                "Vous m'impressionnez vraiment",
                "Bien joué, très bien joué !",
                "Vous méritez cette révélation",
                "Bravo pour cette déduction !"
            ]
        }
        
        if agent_name not in polish_phrases:
            return content
        
        # Ajout d'expressions idiomatiques selon l'agent
        if agent_name == "Watson":
            if "brilliant" in content.lower() or "géni" in content.lower():
                polish = random.choice(["Absolument génial !", "Brillantissime !"])
                return f"{polish} {content}"
        elif agent_name == "Sherlock":
            if "exact" in content.lower() or "précis" in content.lower():
                polish = random.choice(["Précisément.", "Exactement."])
                return f"{polish} {content}"
        elif agent_name == "Moriarty":
            if "révél" in content.lower():
                polish = random.choice(["*avec un sourire admiratif*", "*théâtralement*"])
                return f"{polish} {content}"
        
        return content
    
    def get_ideal_trace_metrics(self) -> Dict[str, float]:
        """
        Calcule les métriques de la trace idéale Phase D.
        
        Returns:
            Métriques avec scores détaillés pour atteindre 8.0+/10
        """
        metrics = {
            "naturalite_dialogue": 0.0,
            "personnalites_distinctes": 0.0,
            "fluidite_transitions": 0.0,
            "progression_logique": 0.0,
            "dosage_revelations": 0.0,
            "engagement_global": 0.0,
            "score_trace_ideale": 0.0
        }
        
        total_messages = len(self.conversation_history)
        if total_messages == 0:
            return metrics
        
        # Naturalité dialogue (héritage Phase B + optimisations)
        natural_indicators = 0
        for msg in self.conversation_history:
            content = msg.get("content", "").lower()
            if any(word in content for word in ["brilliant", "exact", "précis", "géni", "magistral"]):
                natural_indicators += 1
        
        metrics["naturalite_dialogue"] = min(7.5 + (natural_indicators / total_messages) * 2.5, 10.0)
        
        # Personnalités distinctes (héritage Phase A + affinement)
        personality_indicators = {}
        for msg in self.conversation_history:
            agent = msg.get("agent_name", "")
            content = msg.get("content", "").lower()
            
            if agent not in personality_indicators:
                personality_indicators[agent] = 0
            
            # Indicateurs spécifiques par agent améliorés
            if agent == "Watson" and any(word in content for word in ["brilliant", "exact", "admira", "génial"]):
                personality_indicators[agent] += 1
            elif agent == "Sherlock" and any(word in content for word in ["précis", "observ", "dédu", "logique"]):
                personality_indicators[agent] += 1
            elif agent == "Moriarty" and any(word in content for word in ["révél", "mystèr", "*pause*", "*regard*"]):
                personality_indicators[agent] += 1
        
        personality_score = sum(personality_indicators.values()) / len(personality_indicators) if personality_indicators else 0
        metrics["personnalites_distinctes"] = min(7.5 + personality_score * 0.5, 10.0)
        
        # Fluidité transitions (héritage Phase C + optimisations)
        transition_indicators = 0
        for i, msg in enumerate(self.conversation_history[1:], 1):
            content = msg.get("content", "").lower()
            if any(phrase in content for phrase in ["suite à", "en réaction", "après", "comme dit", "précédemment"]):
                transition_indicators += 1
        
        transition_rate = transition_indicators / max(total_messages - 1, 1)
        metrics["fluidite_transitions"] = min(6.7 + transition_rate * 3.3, 10.0)
        
        # Progression logique (nouveau Phase D)
        logical_progression = 0
        for msg in self.conversation_history:
            content = msg.get("content", "").lower()
            if any(word in content for word in ["donc", "ainsi", "par conséquent", "logique", "déduction"]):
                logical_progression += 1
        
        progression_rate = logical_progression / total_messages
        metrics["progression_logique"] = min(7.0 + progression_rate * 3.0, 10.0)
        
        # Dosage révélations (nouveau Phase D - critère clé)
        revelations_count = 0
        dramatic_elements = 0
        for msg in self.conversation_history:
            content = msg.get("content", "")
            if "révél" in content.lower() or "**" in content:
                revelations_count += 1
            if any(element in content for element in ["*pause*", "*regard*", "*silence*", "*dramatique*"]):
                dramatic_elements += 1
        
        if revelations_count > 0:
            dosage_score = min(8.0 + (dramatic_elements / revelations_count) * 2.0, 10.0)
        else:
            dosage_score = 7.0
        
        metrics["dosage_revelations"] = dosage_score
        
        # Engagement global (nouveau Phase D - critère clé)
        engagement_indicators = dramatic_elements + natural_indicators + transition_indicators
        engagement_rate = engagement_indicators / total_messages
        metrics["engagement_global"] = min(7.0 + engagement_rate * 3.0, 10.0)
        
        # Score trace idéale (moyenne pondérée optimisée pour 8.0+)
        weights = {
            "naturalite_dialogue": 0.15,
            "personnalites_distinctes": 0.15,
            "fluidite_transitions": 0.15,
            "progression_logique": 0.20,  # Poids élevé pour Phase D
            "dosage_revelations": 0.20,   # Poids élevé pour Phase D
            "engagement_global": 0.15
        }
        
        metrics["score_trace_ideale"] = sum(
            metrics[key] * weight for key, weight in weights.items()
        )
        
        return metrics
    
    def generate_crescendo_moment(self, final_revelation: str) -> str:
        """
        Génère un moment de crescendo final pour la résolution.
        
        Args:
            final_revelation: Révélation finale à présenter
        
        Returns:
            Contenu du crescendo formaté
        """
        import random
        
        crescendo_templates = [
            """*tension palpable*

Messieurs... vous avez brillamment mené cette enquête.

Chaque déduction, chaque analyse, chaque révélation nous a menés ici.

Il est temps de dévoiler la vérité complète !

**{revelation}**""",
            
            """*moment solennel*

L'heure de la révélation finale a sonné.

Votre travail d'équipe a été... magistral.

Voici donc la solution que vous avez méritée :

**{revelation}**""",
            
            """*crescendo dramatique*

Sherlock, Watson... vous m'avez impressionné.

Cette danse intellectuelle touche à sa fin.

Permettez-moi de lever le voile sur le mystère :

**{revelation}**"""
        ]
        
        template = random.choice(crescendo_templates)
        return template.format(revelation=final_revelation)
    
    def validate_phase_d_requirements(self) -> Dict[str, bool]:
        """
        Valide que tous les critères Phase D sont respectés pour la trace idéale.
        
        Returns:
            Dictionnaire des validations avec True/False pour chaque critère
        """
        metrics = self.get_ideal_trace_metrics()
        
        validations = {
            "score_global_8_plus": metrics["score_trace_ideale"] >= 8.0,
            "naturalite_dialogue_7_5_plus": metrics["naturalite_dialogue"] >= 7.5,
            "personnalites_distinctes_7_5_plus": metrics["personnalites_distinctes"] >= 7.5,
            "fluidite_transitions_7_plus": metrics["fluidite_transitions"] >= 7.0,
            "progression_logique_8_plus": metrics["progression_logique"] >= 8.0,
            "dosage_revelations_8_plus": metrics["dosage_revelations"] >= 8.0,
            "engagement_global_8_plus": metrics["engagement_global"] >= 8.0,
            "conversation_length_sufficient": len(self.conversation_history) >= 5,
            "dramatic_elements_present": any("*" in msg.get("content", "") for msg in self.conversation_history),
            "revelations_present": any("révél" in msg.get("content", "").lower() for msg in self.conversation_history)
        }
        
        return validations