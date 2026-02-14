"""
Dataset Cluedo pour les agents Oracle.

Ce module gère les données du jeu Cluedo et les interactions avec l'Oracle.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .permissions import QueryType, QueryResult, RevealPolicy, ValidationResult


@dataclass
class CluedoSuggestion:
    """Suggestion Cluedo avec suspect, arme et lieu."""

    suspect: str
    arme: str
    lieu: str
    suggested_by: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la suggestion en dictionnaire."""
        return {
            "suspect": self.suspect,
            "arme": self.arme,
            "lieu": self.lieu,
            "suggested_by": self.suggested_by,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        return f"Suggestion({self.suspect}, {self.arme}, {self.lieu}) par {self.suggested_by}"


@dataclass
class RevelationRecord:
    """Enregistrement d'une révélation de carte."""

    card_revealed: str
    revelation_type: str
    message: str
    strategic_value: float = 0.8
    revealed_to: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    query_type: Optional[QueryType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Compatibilité avec l'ancienne API
    @property
    def card(self) -> str:
        """Compatibilité avec l'ancienne API."""
        return self.card_revealed

    @property
    def reason(self) -> str:
        """Compatibilité avec l'ancienne API."""
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'enregistrement en dictionnaire."""
        return {
            "card": self.card_revealed,
            "card_revealed": self.card_revealed,
            "revelation_type": self.revelation_type,
            "message": self.message,
            "strategic_value": self.strategic_value,
            "revealed_to": self.revealed_to,
            "timestamp": self.timestamp.isoformat(),
            "query_type": self.query_type.value if self.query_type else None,
            "metadata": self.metadata,
        }


class CluedoDataset:
    """
    Dataset pour le jeu Cluedo contenant les cartes de Moriarty.

    Gère les cartes détenues par Moriarty et les révélations strategiques.
    """

    def __init__(
        self,
        moriarty_cards: Optional[List[str]] = None,
        elements_jeu: Optional[Dict[str, List[str]]] = None,
        solution_secrete: Optional[Dict[str, str]] = None,
        cartes_distribuees: Optional[Dict[str, List[str]]] = None,
    ):
        """
        Initialise le dataset avec les cartes de Moriarty.

        Args:
            moriarty_cards: Liste des cartes détenues par Moriarty
            elements_jeu: Éléments du jeu (suspects, armes, lieux)
            solution_secrete: Solution secrète du Cluedo (pour compatibilité avec anciens tests)
            cartes_distribuees: Cartes distribuées par joueur (pour compatibilité avec anciens tests)
        """
        # Éléments du jeu (passés en paramètre ou par défaut)
        if elements_jeu:
            self._elements_jeu = elements_jeu
        else:
            self._elements_jeu = {
                "suspects": [
                    "Colonel Moutarde",
                    "Docteur Olive",
                    "Madame Leblanc",
                    "Mademoiselle Rose",
                    "Professeur Violet",
                    "Monsieur Pervenche",
                ],
                "armes": [
                    "Corde",
                    "Poignard",
                    "Barre de fer",
                    "Revolver",
                    "Chandelier",
                    "Clé anglaise",
                ],
                "lieux": [
                    "Bureau",
                    "Salon",
                    "Cuisine",
                    "Salle de bal",
                    "Conservatoire",
                    "Salle de billard",
                    "Bibliothèque",
                    "Hall",
                    "Véranda",
                ],
            }

        # Gérer la solution secrète et les cartes de Moriarty
        if solution_secrete:
            # Mode compatibilité avec anciens tests : solution secrète fournie
            self._solution_secrete = solution_secrete
            if cartes_distribuees and "moriarty" in cartes_distribuees:
                self.moriarty_cards = set(cartes_distribuees["moriarty"])
            elif moriarty_cards:
                self.moriarty_cards = set(moriarty_cards)
            else:
                # Déduire les cartes de Moriarty : toutes les cartes sauf la solution secrète
                all_cards = (
                    set(self._elements_jeu["suspects"])
                    | set(self._elements_jeu["armes"])
                    | set(self._elements_jeu["lieux"])
                )
                solution_cards = {
                    solution_secrete["suspect"],
                    solution_secrete["arme"],
                    solution_secrete["lieu"],
                }
                self.moriarty_cards = all_cards - solution_cards
        else:
            # Mode normal : cartes de Moriarty fournies, calculer la solution secrète
            self.moriarty_cards = set(moriarty_cards) if moriarty_cards else set()
            self._solution_secrete = self._calculate_solution_secrete()

        self.revelations_history: List[RevelationRecord] = []
        self.total_queries = 0
        self.reveal_policy = RevealPolicy.BALANCED

        # Solution secrète (cartes que Moriarty ne détient PAS)
        self._all_suspects = set(self._elements_jeu["suspects"])
        self._all_weapons = set(self._elements_jeu["armes"])
        self._all_rooms = set(self._elements_jeu["lieux"])

        self._logger = logging.getLogger(f"CluedoDataset")
        self._logger.info(
            f"CluedoDataset initialisé avec {len(self.moriarty_cards)} cartes Moriarty"
        )

    @property
    def solution_secrete(self) -> Dict[str, str]:
        """
        Retourne la solution secrète du Cluedo.

        Returns:
            Dictionnaire avec les clés 'suspect', 'arme', 'lieu'
        """
        return self._solution_secrete.copy()

    def _calculate_solution_secrete(self) -> Dict[str, str]:
        """
        Calcule la solution secrète basée sur les cartes que Moriarty ne possède pas.

        Returns:
            Dictionnaire avec la solution secrète
        """
        # Suspects que Moriarty ne possède pas
        available_suspects = [
            s for s in self._elements_jeu["suspects"] if s not in self.moriarty_cards
        ]
        # Armes que Moriarty ne possède pas
        available_weapons = [
            a for a in self._elements_jeu["armes"] if a not in self.moriarty_cards
        ]
        # Lieux que Moriarty ne possède pas
        available_rooms = [
            l for l in self._elements_jeu["lieux"] if l not in self.moriarty_cards
        ]

        # Prendre le premier disponible pour chaque catégorie (ou une stratégie cohérente)
        return {
            "suspect": (
                available_suspects[0] if available_suspects else "Colonel Moutarde"
            ),
            "arme": available_weapons[0] if available_weapons else "Poignard",
            "lieu": available_rooms[0] if available_rooms else "Salon",
        }

    def get_moriarty_cards(self) -> List[str]:
        """Retourne la liste des cartes de Moriarty."""
        return list(self.moriarty_cards)

    def get_autres_joueurs_cards(self) -> List[str]:
        """
        MÉTHODE SÉCURISÉE - ACCÈS RESTREINT
        Cette méthode violait les règles du Cluedo. Accès désormais restreint.
        """
        raise PermissionError(
            "VIOLATION RÈGLES CLUEDO: Un joueur ne peut pas voir les cartes des autres joueurs ! "
            "Cette méthode a été désactivée pour préserver l'intégrité du jeu."
        )

    def get_revealed_cards_to_agent(self, agent_name: str) -> List[str]:
        """Retourne les cartes révélées à un agent spécifique."""
        revelations = self.get_revelations_for_agent(agent_name)
        return [r.card_revealed for r in revelations]

    def reveal_card(
        self, card: str, to_agent: str, reason: str, query_type: QueryType
    ) -> RevelationRecord:
        """
        Révèle une carte à un agent.

        Args:
            card: Carte à révéler
            to_agent: Agent à qui révéler
            reason: Raison de la révélation
            query_type: Type de requête ayant déclenché la révélation

        Returns:
            Enregistrement de la révélation
        """
        if card not in self.moriarty_cards:
            raise ValueError(f"Moriarty ne possède pas la carte: {card}")

        revelation = RevelationRecord(
            card_revealed=card,
            revelation_type="owned_card",
            message=reason,
            strategic_value=0.8,
            revealed_to=to_agent,
            timestamp=datetime.now(),
            query_type=query_type,
            metadata={"total_revelations": len(self.revelations_history) + 1},
        )

        self.revelations_history.append(revelation)
        self._logger.info(f"Carte révélée: {card} à {to_agent} (Raison: {reason})")

        return revelation

    def get_revelations_for_agent(self, agent_name: str) -> List[RevelationRecord]:
        """
        Récupère l'historique des révélations pour un agent.

        Args:
            agent_name: Nom de l'agent

        Returns:
            Liste des révélations faites à cet agent
        """
        return [r for r in self.revelations_history if r.revealed_to == agent_name]

    def validate_cluedo_suggestion(
        self, suggestion: CluedoSuggestion, agent_name: str
    ) -> ValidationResult:
        """
        Valide une suggestion Cluedo selon les cartes de Moriarty.

        Args:
            suggestion: Suggestion à valider
            agent_name: Nom de l'agent suggérant

        Returns:
            Résultat de la validation
        """
        # Vérifie quelles cartes de la suggestion Moriarty possède
        owned_cards = []
        suggestion_cards = [suggestion.suspect, suggestion.arme, suggestion.lieu]

        for card in suggestion_cards:
            if card in self.moriarty_cards:
                owned_cards.append(card)

        def _get_card_type(card_name: str) -> str:
            if card_name in self._all_suspects:
                return "suspect"
            if card_name in self._all_weapons:
                return "arme"
            if card_name in self._all_rooms:
                return "lieu"
            return "inconnu"

        if owned_cards:
            # Moriarty possède au moins une carte, il peut réfuter
            # Choisit une carte à révéler selon la stratégie
            cards_to_reveal = self._choose_cards_to_reveal(owned_cards, agent_name)

            # Enregistre les révélations
            revelations = []
            for card in cards_to_reveal:
                revelation = self.reveal_card(
                    card=card,
                    to_agent=agent_name,
                    reason=f"Réfutation de suggestion: {suggestion}",
                    query_type=QueryType.SUGGESTION_VALIDATION,
                )
                revelations.append(revelation)

            cards_to_reveal_details = [
                {"type": _get_card_type(card), "value": card}
                for card in cards_to_reveal
            ]

            return ValidationResult(
                can_refute=True,
                suggestion_valid=False,
                reason=f"Suggestion réfutée - Moriarty possède: {', '.join(cards_to_reveal)}",
                revealed_cards=cards_to_reveal_details,
                refuting_agent="Moriarty",
                authorized=True,
            )
        else:
            # Moriarty ne possède aucune carte de la suggestion
            return ValidationResult(
                can_refute=False,
                suggestion_valid=True,
                reason="Suggestion non réfutée - Moriarty ne possède aucune de ces cartes",
                revealed_cards=[],
                refuting_agent="",
                authorized=True,
            )

    def can_refute_suggestion(self, suggestion: CluedoSuggestion) -> List[str]:
        """
        Détermine si Moriarty peut réfuter une suggestion et retourne les cartes possédées.

        Args:
            suggestion: Suggestion à analyser

        Returns:
            Liste des cartes de la suggestion que Moriarty possède
        """
        owned_cards = []
        suggestion_cards = [suggestion.suspect, suggestion.arme, suggestion.lieu]

        for card in suggestion_cards:
            if card in self.moriarty_cards:
                owned_cards.append(card)

        return owned_cards

    def reveal_card_compatible(
        self, card: str, to_agent: str, reason: str
    ) -> RevelationRecord:
        """
        Version compatible de reveal_card sans query_type requis.

        Args:
            card: Carte à révéler
            to_agent: Agent à qui révéler
            reason: Raison de la révélation

        Returns:
            Enregistrement de la révélation
        """
        return self.reveal_card(card, to_agent, reason, QueryType.CARD_INQUIRY)

    def _choose_cards_to_reveal(
        self, owned_cards: List[str], requesting_agent: str
    ) -> List[str]:
        """
        Choisit quelles cartes révéler selon la stratégie.

        Args:
            owned_cards: Cartes possédées par Moriarty dans la suggestion
            requesting_agent: Agent demandeur

        Returns:
            Liste des cartes à révéler
        """
        if self.reveal_policy == RevealPolicy.COOPERATIVE:
            # Mode coopératif: révèle toutes les cartes
            return owned_cards
        elif self.reveal_policy == RevealPolicy.COMPETITIVE:
            # Mode compétitif: révèle le minimum (1 carte)
            return [owned_cards[0]]
        else:
            # Mode équilibré ou progressif: révèle selon l'historique
            previous_revelations = self.get_revelations_for_agent(requesting_agent)
            if len(previous_revelations) < 3:
                return [owned_cards[0]]  # Une seule carte au début
            else:
                return owned_cards[:2] if len(owned_cards) > 1 else owned_cards

    def _generate_strategic_clue(self, agent_name: str) -> str:
        """
        Génère un indice stratégique pour un agent.

        Args:
            agent_name: Nom de l'agent demandeur

        Returns:
            Indice généré
        """
        # Simple heuristique basée sur le nombre de révélations précédentes
        revelations_count = len(self.get_revelations_for_agent(agent_name))

        if revelations_count == 0:
            return "Observez attentivement les réactions des autres joueurs. Moriarty détient des cartes importantes."
        elif revelations_count < 3:
            return "Certaines cartes ont été révélées. Analysez les patterns et indices disponibles."
        else:
            return "Vous avez suffisamment d'informations pour déduire la solution. Utilisez les cartes révélées."

    def get_statistics(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du dataset.

        Returns:
            Dictionnaire des statistiques
        """
        return {
            "total_queries": self.total_queries,
            "total_revelations": len(self.revelations_history),
            "moriarty_cards_count": len(self.moriarty_cards),
            "reveal_policy": self.reveal_policy.value,
            "revelations_by_agent": {
                agent: len(
                    [r for r in self.revelations_history if r.revealed_to == agent]
                )
                for agent in set(r.revealed_to for r in self.revelations_history)
            },
        }

    async def process_query(
        self, agent_name: str, query_type: QueryType, query_params: Dict[str, Any]
    ) -> QueryResult:
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
                    suggested_by=agent_name,
                )

                validation_result = self.validate_cluedo_suggestion(
                    suggestion, agent_name
                )

                return QueryResult(
                    success=True,
                    data=validation_result,
                    message=validation_result.reason,
                    query_type=query_type,
                    metadata={"suggestion": suggestion.to_dict()},
                )

            elif query_type == QueryType.CLUE_REQUEST:
                # Demande d'indice général
                clue = self._generate_strategic_clue(agent_name)
                return QueryResult(
                    success=True,
                    data={"clue": clue},
                    message=f"Indice fourni: {clue}",
                    query_type=query_type,
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
                        query_type=QueryType.CARD_INQUIRY,
                    )
                    return QueryResult(
                        success=True,
                        data={"owns_card": True, "revelation": revelation},
                        message=f"Moriarty possède la carte: {card}",
                        query_type=query_type,
                    )
                else:
                    return QueryResult(
                        success=True,
                        data={"owns_card": False},
                        message=f"Moriarty ne révèle pas d'information sur: {card}",
                        query_type=query_type,
                    )

            elif query_type == QueryType.PROGRESSIVE_HINT:
                # Indices progressifs pour Enhanced Oracle functionality
                return QueryResult(
                    success=True,
                    data={"hint_request": query_params},
                    message="Requête d'indice progressif autorisée - traitement par Enhanced Oracle",
                    query_type=query_type,
                    metadata={"enhanced_processing": True},
                )

            elif query_type == QueryType.RAPID_TEST:
                # Tests rapides pour Enhanced Oracle functionality
                return QueryResult(
                    success=True,
                    data={"test_request": query_params},
                    message="Requête de test rapide autorisée - traitement par Enhanced Oracle",
                    query_type=query_type,
                    metadata={"enhanced_processing": True},
                )

            else:
                return QueryResult(
                    success=False,
                    message=f"Type de requête non supporté: {query_type}",
                    query_type=query_type,
                )

        except Exception as e:
            self._logger.error(
                f"Erreur lors du traitement de la requête {query_type}: {e}"
            )
            return QueryResult(
                success=False, message=f"Erreur: {str(e)}", query_type=query_type
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
        MÉTHODE SÉCURISÉE - ACCÈS ADMINISTRATEUR UNIQUEMENT
        La solution ne doit JAMAIS être accessible directement selon les règles du Cluedo.
        """
        raise PermissionError(
            "VIOLATION RÈGLES CLUEDO: La solution ne peut être révélée qu'à la fin du jeu ! "
            "Accès direct à la solution interdit pour préserver l'intégrité du jeu."
        )

    def export_revelations(self) -> List[Dict[str, Any]]:
        """
        Exporte l'historique des révélations.

        Returns:
            Liste des révélations au format dictionnaire
        """
        return [revelation.to_dict() for revelation in self.revelations_history]

    def reset_dataset(self):
        """Remet à zéro le dataset (révélations et compteurs)."""
        self.revelations_history.clear()
        self.total_queries = 0
        self._logger.info("Dataset CluedoDataset remis à zéro")

    @property
    def elements_jeu(self) -> Dict[str, List[str]]:
        """Retourne les éléments du jeu (compatibilité tests)."""
        return self._elements_jeu

    @property
    def suspects(self) -> List[str]:
        """Retourne la liste des suspects."""
        return self._elements_jeu["suspects"]

    @property
    def armes(self) -> List[str]:
        """Retourne la liste des armes."""
        return self._elements_jeu["armes"]

    @property
    def lieux(self) -> List[str]:
        """Retourne la liste des lieux."""
        return self._elements_jeu["lieux"]

    def is_game_solvable_by_elimination(self) -> bool:
        """
        Vérifie si le jeu peut être résolu par élimination complète.

        Returns:
            True si suffisamment de cartes ont été révélées pour permettre la résolution
        """
        # Calcul simple: si plus de 70% des cartes non-solution ont été révélées
        total_cards = (
            len(self._all_suspects) + len(self._all_weapons) + len(self._all_rooms)
        )
        solution_cards = 3  # suspect + arme + lieu
        non_solution_cards = total_cards - solution_cards

        # Si plus de 70% des cartes non-solution révélées, jeu résolvable
        return len(self.revelations_history) >= (non_solution_cards * 0.7)
