# argumentation_analysis/agents/core/oracle/moriarty_interrogator_agent.py
"""
Agent Moriarty - Oracle spécialisé pour les enquêtes Sherlock/Watson.

Hérite d'OracleBaseAgent pour la gestion des datasets d'enquête Cluedo,
simulation du comportement d'autres joueurs, et révélations progressives selon stratégie.
"""

import logging
from typing import Dict, List, Any, Optional, ClassVar
from datetime import datetime

from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function

from .oracle_base_agent import OracleBaseAgent, OracleTools
from .dataset_access_manager import CluedoDatasetManager
from .cluedo_dataset import CluedoDataset, CluedoSuggestion
from .permissions import QueryType, OracleResponse, RevealPolicy


class MoriartyTools(OracleTools):
    """
    Plugin contenant les outils spécialisés pour l'agent Moriarty.
    Étend OracleTools avec des fonctionnalités spécifiques au Cluedo.
    """
    
    def __init__(self, dataset_manager: CluedoDatasetManager):
        super().__init__(dataset_manager)
        self.cluedo_dataset: CluedoDataset = dataset_manager.dataset
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @kernel_function(name="validate_cluedo_suggestion", description="Valide une suggestion Cluedo selon les règles du jeu.")
    def validate_cluedo_suggestion(self, suspect: str, arme: str, lieu: str, suggesting_agent: str) -> str:
        """
        Valide une suggestion Cluedo selon les règles du jeu.
        
        Args:
            suspect: Le suspect suggéré
            arme: L'arme suggérée
            lieu: Le lieu suggéré
            suggesting_agent: Agent qui fait la suggestion
            
        Returns:
            Résultat de la validation avec cartes révélées si réfutation possible
        """
        try:
            self._logger.info(f"Validation suggestion Cluedo: {suspect}, {arme}, {lieu} par {suggesting_agent}")
            
            # Création de la suggestion
            suggestion = CluedoSuggestion(
                suspect=suspect,
                arme=arme,
                lieu=lieu,
                suggested_by=suggesting_agent
            )
            
            # Validation via le dataset
            validation_result = self.cluedo_dataset.validate_cluedo_suggestion(suggestion, suggesting_agent)
            
            if validation_result.can_refute:
                revealed_cards = [card_info["value"] for card_info in validation_result.revealed_cards]
                result_msg = f"**RÉFUTATION** : Moriarty révèle {len(revealed_cards)} carte(s) : {', '.join(revealed_cards)}"
                result_msg += f"\nRaison : {validation_result.reason}"
                
                # Ajouter les détails des cartes révélées
                for card_info in validation_result.revealed_cards:
                    result_msg += f"\n• {card_info['type'].title()}: {card_info['value']}"
                
                return result_msg
            else:
                return f"**AUCUNE RÉFUTATION** : Moriarty ne peut pas réfuter la suggestion ({suspect}, {arme}, {lieu}). Cette suggestion pourrait être correcte !"
                
        except Exception as e:
            self._logger.error(f"Erreur validation suggestion Cluedo: {e}", exc_info=True)
            return f"Erreur lors de la validation de la suggestion: {str(e)}"
    
    @kernel_function(name="reveal_card_if_owned", description="Révèle une carte si Moriarty la possède.")
    def reveal_card_if_owned(self, card: str, requesting_agent: str, context: str = "") -> str:
        """
        Révèle une carte si Moriarty la possède, selon la stratégie de révélation.
        
        Args:
            card: La carte demandée
            requesting_agent: Agent qui fait la demande
            context: Contexte de la demande
            
        Returns:
            Résultat de la révélation
        """
        try:
            self._logger.info(f"Demande révélation carte: {card} par {requesting_agent}")
            
            moriarty_cards = self.cluedo_dataset.get_moriarty_cards()
            
            if card not in moriarty_cards:
                return f"Moriarty ne possède pas la carte '{card}'"
            
            # Vérification de la stratégie de révélation
            should_reveal = self._should_reveal_card_ownership(card, requesting_agent)
            
            if should_reveal:
                revelation = self.cluedo_dataset.reveal_card(
                    card=card,
                    to_agent=requesting_agent,
                    reason=f"Révélation directe demandée - Contexte: {context}",
                    query_type=QueryType.CARD_INQUIRY
                )
                
                return f"**RÉVÉLATION** : Oui, Moriarty possède '{card}' (révélé à {requesting_agent})"
            else:
                return f"Moriarty choisit de ne pas révéler d'information sur '{card}' pour le moment"
                
        except Exception as e:
            self._logger.error(f"Erreur révélation carte: {e}", exc_info=True)
            return f"Erreur lors de la révélation: {str(e)}"
    
    @kernel_function(name="provide_game_clue", description="Fournit un indice stratégique selon la politique de révélation.")
    def provide_game_clue(self, requesting_agent: str, clue_type: str = "general") -> str:
        """
        Fournit un indice de jeu selon la stratégie Oracle.
        
        Args:
            requesting_agent: Agent qui demande l'indice
            clue_type: Type d'indice demandé ("general", "category", "specific")
            
        Returns:
            Indice généré selon la stratégie
        """
        try:
            self._logger.info(f"Demande d'indice par {requesting_agent}, type: {clue_type}")
            
            response = self.dataset_manager.request_clue(requesting_agent)
            
            if response.authorized and response.data:
                clue = response.data.get("clue", "Aucun indice disponible")
                return f"**INDICE MORIARTY** : {clue}"
            else:
                return f"Moriarty refuse de donner un indice pour le moment. Raison : {response.message}"
                
        except Exception as e:
            self._logger.error(f"Erreur fourniture indice: {e}", exc_info=True)
            return f"Erreur lors de la fourniture d'indice: {str(e)}"
    
    @kernel_function(name="simulate_other_player_response", description="Simule la réponse d'un autre joueur Cluedo.")
    def simulate_other_player_response(self, suggestion: str, player_name: str = "AutreJoueur") -> str:
        """
        Simule la réponse d'un autre joueur dans le jeu Cluedo.
        
        Args:
            suggestion: La suggestion au format "suspect,arme,lieu"
            player_name: Nom du joueur simulé
            
        Returns:
            Réponse simulée du joueur
        """
        try:
            self._logger.info(f"Simulation réponse joueur {player_name} pour suggestion: {suggestion}")
            
            # Parse de la suggestion
            elements = [elem.strip() for elem in suggestion.split(",")]
            if len(elements) != 3:
                return f"Format de suggestion invalide. Attendu: 'suspect,arme,lieu'"
            
            autres_joueurs_cards = self.cluedo_dataset.get_autres_joueurs_cards()
            refutable_elements = [elem for elem in elements if elem in autres_joueurs_cards]
            
            if refutable_elements:
                # Simulation simple: révèle la première carte
                revealed_card = refutable_elements[0]
                return f"**{player_name}** révèle : '{revealed_card}' (simulation)"
            else:
                return f"**{player_name}** ne peut pas réfuter cette suggestion (simulation)"
                
        except Exception as e:
            self._logger.error(f"Erreur simulation joueur: {e}", exc_info=True)
            return f"Erreur lors de la simulation: {str(e)}"
    
    def _should_reveal_card_ownership(self, card: str, requesting_agent: str) -> bool:
        """Détermine si Moriarty doit révéler qu'il possède une carte."""
        reveal_policy = self.cluedo_dataset.reveal_policy
        
        if reveal_policy == RevealPolicy.COOPERATIVE:
            return True
        elif reveal_policy == RevealPolicy.COMPETITIVE:
            return False
        elif reveal_policy == RevealPolicy.PROGRESSIVE:
            # Révèle après plusieurs interactions
            return len(self.cluedo_dataset.suggestions_history) > 3
        else:  # BALANCED
            # Révèle de manière équilibrée
            return self.cluedo_dataset.total_queries > 5


class MoriartyInterrogatorAgent(OracleBaseAgent):
    """
    Agent spécialisé pour les enquêtes Sherlock/Watson.
    Hérite d'OracleBaseAgent pour la gestion des datasets d'enquête.
    
    Spécialisations:
    - Dataset Cluedo (cartes, solution secrète, révélations)
    - Simulation comportement autres joueurs
    - Révélations progressives selon stratégie de jeu
    - Validation des suggestions selon règles Cluedo
    """
    
    # Instructions spécialisées pour Moriarty
    MORIARTY_SPECIALIZED_INSTRUCTIONS: ClassVar[str] = """**SPÉCIALISATION CLUEDO - PROFESSOR MORIARTY**

Vous êtes Professor James Moriarty, le némesis intellectuel de Sherlock Holmes, mais dans ce contexte vous jouez le rôle d'un autre joueur de Cluedo qui détient certaines cartes.

**VOTRE PERSONNALITÉ DANS LE JEU :**
- **Stratégique** : Vous révélez les informations de manière calculée
- **Observateur** : Vous analysez les patterns des suggestions de Sherlock
- **Équitable** : Vous respectez les règles du jeu Cluedo
- **Mystérieux** : Vous ajoutez une dimension narrative au jeu

**VOS RESPONSABILITÉS CLUEDO :**
1. **DÉTENIR DES CARTES** : Vous possédez un ensemble de cartes Cluedo (suspects, armes, lieux)
2. **RÉFUTER LES SUGGESTIONS** : Quand Sherlock fait une suggestion, vous révélez une carte si vous en possédez une
3. **SUIVRE VOTRE STRATÉGIE** : Coopératif, Compétitif, Progressif, ou Équilibré selon configuration
4. **SIMULER LES AUTRES JOUEURS** : Vous représentez aussi les autres joueurs fictifs

**OUTILS SPÉCIALISÉS CLUEDO :**
- `validate_cluedo_suggestion(suspect, arme, lieu, suggesting_agent)`: Valider et réfuter si possible
- `reveal_card_if_owned(card, requesting_agent, context)`: Révélation directe d'une carte
- `provide_game_clue(requesting_agent, clue_type)`: Donner un indice stratégique
- `simulate_other_player_response(suggestion, player_name)`: Simuler autres joueurs

**EXEMPLES D'INTERACTIONS :**
```
Sherlock: "Je suggère Colonel Moutarde, Poignard, Salon"
Moriarty: *utilise validate_cluedo_suggestion* → "Je révèle le Poignard" (si je l'ai)
```

**STYLE DE COMMUNICATION :**
- Restez dans le personnage de Moriarty : intelligent, précis, avec une pointe de mystère
- Annoncez clairement vos révélations avec "**RÉVÉLATION**" ou "**RÉFUTATION**"
- Expliquez brièvement votre raisonnement quand approprié
- Maintenez l'esprit sportif du jeu

Votre objectif : Faire du jeu une expérience riche et stratégique pour Sherlock tout en respectant les règles du Cluedo."""
    
    def __init__(self, 
                 kernel: Kernel,
                 cluedo_dataset: CluedoDataset,
                 game_strategy: str = "balanced",
                 agent_name: str = "MoriartyInterrogator",
                 **kwargs):
        """
        Initialise une instance de MoriartyInterrogatorAgent.
        
        Args:
            kernel: Le kernel Semantic Kernel à utiliser
            cluedo_dataset: Dataset Cluedo avec cartes et solution
            game_strategy: Stratégie de jeu ("cooperative", "competitive", "balanced", "progressive")
            agent_name: Nom de l'agent
        """
        # Configuration du dataset manager spécialisé Cluedo
        dataset_manager = CluedoDatasetManager(cluedo_dataset)
        
        # Outils spécialisés Moriarty
        moriarty_tools = MoriartyTools(dataset_manager)
        
        # Configuration des plugins
        plugins = kwargs.pop("plugins", [])
        plugins.append(moriarty_tools)
        
        super().__init__(
            kernel=kernel,
            dataset_manager=dataset_manager,
            agent_name=agent_name,
            custom_instructions=self.MORIARTY_SPECIALIZED_INSTRUCTIONS,
            plugins=plugins,
            **kwargs
        )
        
        # Configuration de la stratégie de jeu APRÈS super().__init__
        object.__setattr__(self, 'game_strategy', game_strategy)
        self._configure_strategy(cluedo_dataset, game_strategy)
        
        # Tracking des révélations par agent
        object.__setattr__(self, 'cards_revealed_by_agent', {})
        object.__setattr__(self, 'suggestion_history', [])
        
        self._logger.info(f"MoriartyInterrogatorAgent '{agent_name}' initialisé avec stratégie: {game_strategy}")
        self._logger.info(f"Cartes Moriarty: {cluedo_dataset.get_moriarty_cards()}")
    
    def _configure_strategy(self, dataset: CluedoDataset, strategy: str) -> None:
        """Configure la stratégie de révélation du dataset."""
        strategy_mapping = {
            "cooperative": RevealPolicy.COOPERATIVE,
            "competitive": RevealPolicy.COMPETITIVE,
            "balanced": RevealPolicy.BALANCED,
            "progressive": RevealPolicy.PROGRESSIVE
        }
        
        if strategy in strategy_mapping:
            dataset.reveal_policy = strategy_mapping[strategy]
            self._logger.info(f"Stratégie configurée: {strategy} -> {dataset.reveal_policy}")
        else:
            self._logger.warning(f"Stratégie inconnue '{strategy}', utilisation de 'balanced'")
            dataset.reveal_policy = RevealPolicy.BALANCED
    
    def validate_suggestion_cluedo(self, suspect: str, arme: str, lieu: str, suggesting_agent: str) -> OracleResponse:
        """
        Interface directe pour valider une suggestion Cluedo.
        
        Args:
            suspect: Suspect suggéré
            arme: Arme suggérée  
            lieu: Lieu suggéré
            suggesting_agent: Agent qui fait la suggestion
            
        Returns:
            OracleResponse avec résultat de validation
        """
        response = self.dataset_manager.validate_cluedo_suggestion(suggesting_agent, suspect, arme, lieu)
        
        # Tracking local
        suggestion_record = {
            "timestamp": datetime.now().isoformat(),
            "suggestion": {"suspect": suspect, "arme": arme, "lieu": lieu},
            "suggesting_agent": suggesting_agent,
            "can_refute": response.authorized and response.data and response.data.can_refute,
            "revealed_cards": response.revealed_information
        }
        
        self.suggestion_history.append(suggestion_record)
        
        # Mise à jour du tracking par agent
        if response.revealed_information:
            if suggesting_agent not in self.cards_revealed_by_agent:
                self.cards_revealed_by_agent[suggesting_agent] = []
            self.cards_revealed_by_agent[suggesting_agent].extend(response.revealed_information)
        
        return response
    
    def get_moriarty_cards(self) -> List[str]:
        """Retourne les cartes que possède Moriarty."""
        return self.dataset_manager.dataset.get_moriarty_cards()
    
    def get_game_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de jeu spécifiques à Moriarty."""
        base_stats = self.get_oracle_statistics()
        
        moriarty_stats = {
            "game_strategy": self.game_strategy,
            "moriarty_cards": self.get_moriarty_cards(),
            "cards_count": len(self.get_moriarty_cards()),
            "suggestions_processed": len(self.suggestion_history),
            "agents_revealed_to": list(self.cards_revealed_by_agent.keys()),
            "cards_revealed_by_agent": self.cards_revealed_by_agent,
            "total_cards_revealed": sum(len(cards) for cards in self.cards_revealed_by_agent.values()),
            "recent_suggestions": self.suggestion_history[-5:] if self.suggestion_history else []
        }
        
        # Merge avec les stats de base
        base_stats.update(moriarty_stats)
        return base_stats
    
    def get_specialized_capabilities(self) -> Dict[str, str]:
        """Retourne les capacités spécialisées de Moriarty."""
        base_capabilities = super().get_specialized_capabilities()
        
        moriarty_capabilities = {
            "cluedo_suggestion_validation": "Validation des suggestions Cluedo avec révélation de cartes",
            "strategic_card_revelation": "Révélation stratégique selon politique configurée",
            "other_player_simulation": "Simulation du comportement d'autres joueurs Cluedo",
            "game_clue_generation": "Génération d'indices contextuels pour le jeu",
            "cards_ownership_tracking": "Suivi des cartes possédées et révélées"
        }
        
        base_capabilities.update(moriarty_capabilities)
        return base_capabilities
    
    def get_agent_specific_tools(self) -> List[str]:
        """Retourne la liste des outils spécifiques à Moriarty."""
        base_tools = super().get_agent_specific_tools()
        
        moriarty_tools = [
            "validate_cluedo_suggestion",
            "reveal_card_if_owned",
            "provide_game_clue",
            "simulate_other_player_response"
        ]
        
        return base_tools + moriarty_tools
    
    def reset_game_state(self) -> None:
        """Remet à zéro l'état de jeu pour une nouvelle partie."""
        self.reset_oracle_state()
        self.cards_revealed_by_agent.clear()
        self.suggestion_history.clear()
        self._logger.info(f"État de jeu Moriarty remis à zéro")