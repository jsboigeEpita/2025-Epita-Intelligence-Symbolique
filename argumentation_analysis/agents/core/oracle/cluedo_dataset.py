# argumentation_analysis/agents/core/oracle/cluedo_dataset.py
"""
Dataset spécialisé pour les jeux Cluedo avec révélations contrôlées.

Ce module implémente la gestion des données spécifiques au jeu Cluedo,
incluant la distribution des cartes, la solution secrète, et l'historique
des révélations.
"""

import logging
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

from .permissions import QueryType, QueryResult, ValidationResult, RevealPolicy


@dataclass
class CluedoRevelation:
    """Enregistrement d'une révélation de carte."""
    timestamp: datetime
    card_revealed: str
    revealed_to: str
    revealed_by: str
    reason: str
    query_type: QueryType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CluedoSuggestion:
    """Structure pour une suggestion Cluedo."""
    suspect: str
    arme: str
    lieu: str
    suggested_by: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, str]:
        """Convertit la suggestion en dictionnaire."""
        return {
            "suspect": self.suspect,
            "arme": self.arme,
            "lieu": self.lieu
        }
    
    def get_elements(self) -> List[str]:
        """Retourne tous les éléments de la suggestion."""
        return [self.suspect, self.arme, self.lieu]


class CluedoDataset:
    """
    Dataset spécialisé pour jeux Cluedo avec révélations contrôlées.
    
    Gère la solution secrète, les cartes distribuées aux différents joueurs,
    et l'historique des révélations selon la stratégie configurée.
    """
    
    def __init__(self,
                 solution_secrete: Dict[str, str] = None,
                 cartes_distribuees: Dict[str, List[str]] = None,
                 moriarty_cards: List[str] = None,
                 reveal_policy: RevealPolicy = RevealPolicy.BALANCED):
        """
        Initialise le dataset Cluedo.
        
        Args:
            solution_secrete: La vraie solution {"suspect": "X", "arme": "Y", "lieu": "Z"}
            cartes_distribuees: Cartes par joueur/agent {"Moriarty": [...], "AutresJoueurs": [...]}
            moriarty_cards: Liste des cartes de Moriarty (alternative à cartes_distribuees)
            reveal_policy: Politique de révélation
        """
        # Support both cartes_distribuees and moriarty_cards for backward compatibility
        if moriarty_cards is not None:
            self.cartes_distribuees = {"Moriarty": moriarty_cards}
        elif cartes_distribuees is not None:
            self.cartes_distribuees = cartes_distribuees
        else:
            self.cartes_distribuees = {"Moriarty": ["knife", "rope", "candlestick"]}
            
        if solution_secrete is None:
            solution_secrete = {"suspect": "scarlet", "weapon": "candlestick", "room": "library"}
        
        self.solution_secrete = solution_secrete
        self.reveal_policy = reveal_policy
        self.revelations_historique: List[CluedoRevelation] = []
        self.access_restrictions = {
            "solution_secrete": ["orchestrator_only"],
            "cartes_moriarty": ["MoriartyInterrogatorAgent"],
            "cartes_autres_joueurs": ["simulation_only"]
        }
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Statistiques de jeu
        self.suggestions_history: List[CluedoSuggestion] = []
        self.cards_revealed_count = 0
        self.total_queries = 0
        
        self._logger.info(f"CluedoDataset initialisé avec {len(self.get_moriarty_cards())} cartes Moriarty")
    
    def get_moriarty_cards(self) -> List[str]:
        """Retourne les cartes que possède Moriarty."""
        return self.cartes_distribuees.get("Moriarty", [])
    
    def get_autres_joueurs_cards(self) -> List[str]:
        """Retourne les cartes des autres joueurs simulés."""
        return self.cartes_distribuees.get("AutresJoueurs", [])
    
    def get_all_distributed_cards(self) -> List[str]:
        """Retourne toutes les cartes distribuées (non secrètes)."""
        all_cards = []
        for cards in self.cartes_distribuees.values():
            all_cards.extend(cards)
        return all_cards
    
    def can_refute_suggestion(self, suggestion: CluedoSuggestion) -> List[str]:
        """
        Vérifie quelles cartes Moriarty peut révéler pour réfuter une suggestion.
        
        Args:
            suggestion: La suggestion à vérifier
            
        Returns:
            Liste des cartes que Moriarty peut révéler
        """
        moriarty_cards = self.get_moriarty_cards()
        refutable_cards = []
        
        for element in suggestion.get_elements():
            if element in moriarty_cards:
                refutable_cards.append(element)
        
        self._logger.debug(f"Suggestion {suggestion.to_dict()} - Cartes réfutables: {refutable_cards}")
        return refutable_cards
    
    def reveal_card(self, card: str, to_agent: str, reason: str, query_type: QueryType = QueryType.SUGGESTION_VALIDATION) -> CluedoRevelation:
        """
        Enregistre une révélation de carte.
        
        Args:
            card: La carte révélée
            to_agent: L'agent à qui la carte est révélée
            reason: Raison de la révélation
            query_type: Type de requête ayant causé la révélation
            
        Returns:
            L'enregistrement de révélation créé
        """
        revelation = CluedoRevelation(
            timestamp=datetime.now(),
            card_revealed=card,
            revealed_to=to_agent,
            revealed_by="MoriartyInterrogatorAgent",
            reason=reason,
            query_type=query_type
        )
        
        self.revelations_historique.append(revelation)
        self.cards_revealed_count += 1
        
        self._logger.info(f"Carte révélée: {card} à {to_agent} - Raison: {reason}")
        return revelation
    
    def apply_revelation_strategy(self, refutable_cards: List[str], requesting_agent: str) -> List[str]:
        """
        Applique la stratégie de révélation pour déterminer quelles cartes révéler.
        
        Args:
            refutable_cards: Cartes que Moriarty peut révéler
            requesting_agent: Agent qui fait la demande
            
        Returns:
            Cartes à révéler selon la stratégie
        """
        if not refutable_cards:
            return []
        
        if self.reveal_policy == RevealPolicy.COOPERATIVE:
            # Mode coopératif: révèle toutes les cartes possibles
            return refutable_cards
        
        elif self.reveal_policy == RevealPolicy.COMPETITIVE:
            # Mode compétitif: révèle le minimum (1 carte si possible)
            return [refutable_cards[0]] if refutable_cards else []
        
        elif self.reveal_policy == RevealPolicy.PROGRESSIVE:
            # Mode progressif: révèle selon le nombre de suggestions précédentes
            suggestions_count = len(self.suggestions_history)
            if suggestions_count < 3:
                # Début: révèle 1 carte maximum
                return [refutable_cards[0]] if refutable_cards else []
            elif suggestions_count < 6:
                # Milieu: révèle jusqu'à 2 cartes
                return refutable_cards[:2]
            else:
                # Fin: plus coopératif
                return refutable_cards
        
        else:  # BALANCED (par défaut)
            # Mode équilibré: révèle 1-2 cartes selon contexte
            if len(refutable_cards) == 1:
                return refutable_cards
            elif len(refutable_cards) == 2:
                # Révèle les 2 si beaucoup de suggestions déjà faites
                if len(self.suggestions_history) > 4:
                    return refutable_cards
                else:
                    return [refutable_cards[0]]
            else:
                # Plus de 2 cartes: révèle 2 maximum
                return refutable_cards[:2]
    
    def validate_cluedo_suggestion(self, suggestion: CluedoSuggestion, requesting_agent: str) -> ValidationResult:
        """
        Valide une suggestion Cluedo selon les règles du jeu et la stratégie Oracle.
        
        Args:
            suggestion: La suggestion à valider
            requesting_agent: Agent qui fait la suggestion
            
        Returns:
            Résultat de validation avec cartes révélées si nécessaire
        """
        self.suggestions_history.append(suggestion)
        self.total_queries += 1
        
        # Vérification des cartes que Moriarty peut réfuter
        refutable_cards = self.can_refute_suggestion(suggestion)
        
        if not refutable_cards:
            # Moriarty ne peut pas réfuter - suggestion valide pour Moriarty
            self._logger.info(f"Suggestion {suggestion.to_dict()} ne peut pas être réfutée par Moriarty")
            return ValidationResult(
                can_refute=False,
                suggestion_valid=True,
                authorized=True,
                reason="Moriarty ne possède aucune de ces cartes",
                refuting_agent="MoriartyInterrogatorAgent"
            )
        
        # Application de la stratégie de révélation
        cards_to_reveal = self.apply_revelation_strategy(refutable_cards, requesting_agent)
        
        # Création des révélations
        revealed_cards_info = []
        for card in cards_to_reveal:
            revelation = self.reveal_card(
                card=card,
                to_agent=requesting_agent,
                reason=f"Réfutation suggestion: {suggestion.to_dict()}",
                query_type=QueryType.SUGGESTION_VALIDATION
            )
            
            # Déterminer le type d'élément (suspect, arme, lieu)
            element_type = "inconnu"
            if card == suggestion.suspect:
                element_type = "suspect"
            elif card == suggestion.arme:
                element_type = "arme"
            elif card == suggestion.lieu:
                element_type = "lieu"
            
            revealed_cards_info.append({
                "type": element_type,
                "value": card,
                "revealed_to": requesting_agent,
                "timestamp": revelation.timestamp.isoformat()
            })
        
        result = ValidationResult(
            can_refute=True,
            revealed_cards=revealed_cards_info,
            suggestion_valid=False,  # La suggestion est réfutée
            authorized=True,
            reason=f"Moriarty révèle {len(cards_to_reveal)} carte(s): {', '.join(cards_to_reveal)}",
            refuting_agent="MoriartyInterrogatorAgent"
        )
        
        self._logger.info(f"Suggestion {suggestion.to_dict()} réfutée par révélation de {len(cards_to_reveal)} carte(s)")
        return result
    
    def process_query(self, agent_name: str, query_type: QueryType, query_params: Dict[str, Any]) -> QueryResult:
        """
        Traite une requête générique sur le dataset.
        
        Args:
            agent_name: Nom de l'agent demandeur
            query_type: Type de requête
            query_params: Paramètres de la requête
            
        Returns:
            Résultat de la requête
        """
        self.total_queries += 1
        
        try:
            if query_type == QueryType.SUGGESTION_VALIDATION:
                # Validation d'une suggestion Cluedo
                suggestion_data = query_params.get("suggestion", {})
                suggestion = CluedoSuggestion(
                    suspect=suggestion_data.get("suspect", ""),
                    arme=suggestion_data.get("arme", ""),
                    lieu=suggestion_data.get("lieu", ""),
                    suggested_by=agent_name
                )
                
                validation_result = self.validate_cluedo_suggestion(suggestion, agent_name)
                
                return QueryResult(
                    success=True,
                    data=validation_result,
                    message=validation_result.reason,
                    query_type=query_type,
                    metadata={"suggestion": suggestion.to_dict()}
                )
            
            elif query_type == QueryType.CLUE_REQUEST:
                # Demande d'indice général
                clue = self._generate_strategic_clue(agent_name)
                return QueryResult(
                    success=True,
                    data={"clue": clue},
                    message=f"Indice fourni: {clue}",
                    query_type=query_type
                )
            
            elif query_type == QueryType.CARD_INQUIRY:
                # Enquête sur une carte spécifique
                card = query_params.get("card", "")
                owns_card = card in self.get_moriarty_cards()
                
                if owns_card and self._should_reveal_card_ownership(card, agent_name):
                    revelation = self.reveal_card(
                        card=card,
                        to_agent=agent_name,
                        reason="Enquête directe sur la carte",
                        query_type=QueryType.CARD_INQUIRY
                    )
                    return QueryResult(
                        success=True,
                        data={"owns_card": True, "revelation": revelation},
                        message=f"Moriarty possède la carte: {card}",
                        query_type=query_type
                    )
                else:
                    return QueryResult(
                        success=True,
                        data={"owns_card": False},
                        message=f"Moriarty ne révèle pas d'information sur: {card}",
                        query_type=query_type
                    )
            
            else:
                return QueryResult(
                    success=False,
                    message=f"Type de requête non supporté: {query_type}",
                    query_type=query_type
                )
        
        except Exception as e:
            self._logger.error(f"Erreur lors du traitement de la requête {query_type}: {e}")
            return QueryResult(
                success=False,
                message=f"Erreur: {str(e)}",
                query_type=query_type
            )
    
    def _should_reveal_card_ownership(self, card: str, requesting_agent: str) -> bool:
        """Détermine si Moriarty doit révéler qu'il possède une carte."""
        # Politique simple: révèle selon la stratégie de révélation
        if self.reveal_policy == RevealPolicy.COOPERATIVE:
            return True
        elif self.reveal_policy == RevealPolicy.COMPETITIVE:
            return False
        else:
            # Pour BALANCED et PROGRESSIVE: révèle après plusieurs requêtes
            return self.total_queries > 5
    def get_solution(self) -> Dict[str, str]:
        """
        Retourne la solution secrète du Cluedo.
        
        Returns:
            La solution secrète avec suspect, weapon et room
        """
        return self.solution_secrete.copy()
    
    def _generate_strategic_clue(self, requesting_agent: str) -> str:
        """Génère un indice stratégique selon la politique de révélation."""
        moriarty_cards = self.get_moriarty_cards()
        
        if not moriarty_cards:
            return "Moriarty n'a pas d'indice à partager actuellement."
        
        if self.reveal_policy == RevealPolicy.COOPERATIVE:
            # Mode coopératif: donne un indice précis
            card = random.choice(moriarty_cards)
            return f"Moriarty possède la carte: {card}"
        
        elif self.reveal_policy == RevealPolicy.COMPETITIVE:
            # Mode compétitif: indice vague
            return "Moriarty observe attentivement les déductions..."
        
        else:
            # Modes BALANCED/PROGRESSIVE: indice modérément utile
            if len(self.revelations_historique) < 2:
                return "Moriarty suggère de se concentrer sur les éléments non encore explorés."
            else:
                # Donne un indice sur une catégorie
                categories = ["suspects", "armes", "lieux"]
                category = random.choice(categories)
                return f"Moriarty indique que ses cartes incluent des {category}."
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du dataset."""
        return {
            "total_queries": self.total_queries,
            "suggestions_count": len(self.suggestions_history),
            "revelations_count": len(self.revelations_historique),
            "cards_revealed": self.cards_revealed_count,
            "moriarty_cards_count": len(self.get_moriarty_cards()),
            "autres_joueurs_cards_count": len(self.get_autres_joueurs_cards()),
            "reveal_policy": self.reveal_policy.value,
            "solution_secrete": self.solution_secrete
        }
    
    def get_revealed_cards_to_agent(self, agent_name: str) -> List[str]:
        """Retourne les cartes révélées à un agent spécifique."""
        return [
            rev.card_revealed 
            for rev in self.revelations_historique 
            if rev.revealed_to == agent_name
        ]
    
    def is_game_solvable_by_elimination(self) -> bool:
        """Vérifie si le jeu peut être résolu par élimination complète."""
        all_cards = self.get_all_distributed_cards()
        revealed_cards = [rev.card_revealed for rev in self.revelations_historique]
        
        # Le jeu est résolvable si toutes les cartes non-secrètes ont été révélées
        return set(all_cards).issubset(set(revealed_cards))