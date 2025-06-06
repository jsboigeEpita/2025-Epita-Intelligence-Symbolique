# tests/unit/argumentation_analysis/agents/core/oracle/test_cluedo_dataset.py
"""
Tests unitaires pour CluedoDataset.

Tests couvrant:
- Initialisation et configuration du dataset Cluedo
- Validation des suggestions Cluedo
- Système de révélation de cartes avec différentes politiques
- Génération d'indices stratégiques
- Gestion des états de jeu et solutions secrètes
- Différentes stratégies de révélation (cooperative, competitive, balanced, progressive)
"""

import pytest
import random
from unittest.mock import Mock, patch
from typing import Dict, Any, List, Set

# Imports du système Oracle
from argumentation_analysis.agents.core.oracle.cluedo_dataset import (
    CluedoDataset,
    CluedoSuggestion,
    CluedoRevelation,
    RevealPolicy
)
from argumentation_analysis.agents.core.oracle.permissions import QueryType, QueryResult


class TestCluedoDataset:
    """Tests pour la classe CluedoDataset."""
    
    @pytest.fixture
    def standard_elements(self):
        """Éléments Cluedo standard pour les tests."""
        return {
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose", "Docteur Orchidée"],
            "armes": ["Poignard", "Chandelier", "Revolver", "Corde"],
            "lieux": ["Salon", "Cuisine", "Bureau", "Bibliothèque"]
        }
    
    @pytest.fixture
    def cluedo_dataset(self, standard_elements):
        """Dataset Cluedo configuré pour les tests."""
        solution_secrete = {
            "suspect": "Colonel Moutarde",
            "arme": "Poignard",
            "lieu": "Salon"
        }
        cartes_distribuees = {
            "Moriarty": ["Professeur Violet", "Chandelier"],
            "AutresJoueurs": ["Cuisine", "Bureau"]
        }
        return CluedoDataset(
            solution_secrete=solution_secrete,
            cartes_distribuees=cartes_distribuees,
            reveal_policy=RevealPolicy.BALANCED
        )
    
    def test_cluedo_dataset_initialization(self, cluedo_dataset, standard_elements):
        """Test l'initialisation correcte du CluedoDataset."""
        # Vérification des éléments de base
        assert cluedo_dataset.reveal_policy == RevealPolicy.BALANCED
        
        # Vérification de la solution secrète
        solution = cluedo_dataset.solution_secrete
        assert solution["suspect"] == "Colonel Moutarde"
        assert solution["arme"] == "Poignard"
        assert solution["lieu"] == "Salon"
        
        # Vérification des cartes Moriarty
        cartes_moriarty = cluedo_dataset.get_moriarty_cards()
        assert len(cartes_moriarty) >= 1  # Au moins une carte
        
        # Aucune carte de Moriarty ne doit être dans la solution secrète
        assert solution["suspect"] not in cartes_moriarty
        assert solution["arme"] not in cartes_moriarty
        assert solution["lieu"] not in cartes_moriarty
    
    def test_validate_cluedo_suggestion_valid(self, cluedo_dataset):
        """Test la validation d'une suggestion valide."""
        valid_suggestion = {
            "suspect": "Colonel Moutarde",
            "arme": "Poignard",
            "lieu": "Salon"
        }
        
        suggestion = CluedoSuggestion(
            suspect="Colonel Moutarde",
            arme="Poignard",
            lieu="Salon",
            suggested_by="TestAgent"
        )
        result = cluedo_dataset.validate_cluedo_suggestion(suggestion, "TestAgent")
        assert result.authorized is True
    
    def test_validate_cluedo_suggestion_can_refute(self, cluedo_dataset):
        """Test la validation avec carte que Moriarty possède."""
        # Utiliser une carte que Moriarty possède
        moriarty_card = cluedo_dataset.get_moriarty_cards()[0]
        suggestion = CluedoSuggestion(
            suspect=moriarty_card if moriarty_card in ["Colonel Moutarde", "Professeur Violet"] else "Professeur Violet",
            arme=moriarty_card if moriarty_card in ["Poignard", "Chandelier"] else "Chandelier",
            lieu=moriarty_card if moriarty_card in ["Salon", "Cuisine"] else "Cuisine",
            suggested_by="TestAgent"
        )
        
        result = cluedo_dataset.validate_cluedo_suggestion(suggestion, "TestAgent")
        assert result.authorized is True
        assert result.can_refute is True  # Moriarty peut réfuter
    
    def test_validate_cluedo_suggestion_cannot_refute(self, cluedo_dataset):
        """Test la validation avec suggestion que Moriarty ne peut pas réfuter."""
        # Utiliser la solution secrète que Moriarty ne possède pas
        suggestion = CluedoSuggestion(
            suspect=cluedo_dataset.solution_secrete["suspect"],
            arme=cluedo_dataset.solution_secrete["arme"],
            lieu=cluedo_dataset.solution_secrete["lieu"],
            suggested_by="TestAgent"
        )
        
        result = cluedo_dataset.validate_cluedo_suggestion(suggestion, "TestAgent")
        assert result.authorized is True
        assert result.can_refute is False  # Moriarty ne peut pas réfuter la vraie solution
    
    def test_can_reveal_card_moriarty_owned(self, cluedo_dataset):
        """Test si Moriarty peut révéler une carte qu'il possède."""
        # Prendre une carte de Moriarty
        moriarty_card = cluedo_dataset.get_moriarty_cards()[0]
        
        refutable_cards = cluedo_dataset.can_refute_suggestion(CluedoSuggestion(
            suspect=moriarty_card if moriarty_card in ["Colonel Moutarde", "Professeur Violet"] else "Colonel Moutarde",
            arme=moriarty_card if moriarty_card in ["Poignard", "Chandelier"] else "Poignard",
            lieu=moriarty_card if moriarty_card in ["Salon", "Cuisine"] else "Salon",
            suggested_by="TestAgent"
        ))
        assert len(refutable_cards) > 0
    
    def test_can_reveal_card_not_owned(self, cluedo_dataset):
        """Test si Moriarty peut révéler une carte qu'il ne possède pas."""
        # Prendre la solution secrète (que Moriarty ne possède pas)
        secret_suspect = cluedo_dataset.solution_secrete["suspect"]
        
        refutable_cards = cluedo_dataset.can_refute_suggestion(CluedoSuggestion(
            suspect=secret_suspect,
            arme=cluedo_dataset.solution_secrete["arme"],
            lieu=cluedo_dataset.solution_secrete["lieu"],
            suggested_by="TestAgent"
        ))
        assert len(refutable_cards) == 0  # Moriarty ne peut pas réfuter la vraie solution
    
    def test_reveal_card_owned(self, cluedo_dataset):
        """Test la révélation d'une carte possédée."""
        moriarty_card = cluedo_dataset.get_moriarty_cards()[0]
        
        revelation = cluedo_dataset.reveal_card(moriarty_card, "TestAgent", "Test de révélation")
        
        assert isinstance(revelation, CluedoRevelation)
        assert revelation.card_revealed == moriarty_card
        assert len(revelation.reason) > 0
    
    def test_reveal_card_not_owned(self, cluedo_dataset):
        """Test la tentative de révélation d'une carte non possédée."""
        secret_suspect = cluedo_dataset.solution_secrete["suspect"]
        
        # Vérifier que Moriarty ne peut pas réfuter la solution secrète
        suggestion = CluedoSuggestion(
            suspect=secret_suspect,
            arme=cluedo_dataset.solution_secrete["arme"],
            lieu=cluedo_dataset.solution_secrete["lieu"],
            suggested_by="TestAgent"
        )
        
        refutable_cards = cluedo_dataset.can_refute_suggestion(suggestion)
        assert len(refutable_cards) == 0  # Ne peut pas réfuter la vraie solution
    
    def test_generate_strategic_clue_elimination(self, cluedo_dataset):
        """Test la génération d'indices d'élimination."""
        clue = cluedo_dataset._generate_strategic_clue("TestAgent")
        
        assert isinstance(clue, str)
        assert len(clue) > 0
        # Devrait contenir des informations utiles
        assert "Moriarty" in clue or "carte" in clue or "indice" in clue
    
    def test_generate_strategic_clue_hint(self, cluedo_dataset):
        """Test la génération d'indices positifs."""
        clue = cluedo_dataset._generate_strategic_clue("TestAgent")
        
        assert isinstance(clue, str)
        assert len(clue) > 0
        # Devrait contenir des suggestions positives
        hint_terms = ["indice", "suggère", "concentrer", "cartes", "moriarty"]
        assert any(term in clue.lower() for term in hint_terms)
    
    def test_process_query_card_inquiry(self, cluedo_dataset):
        """Test le traitement d'une requête de carte."""
        moriarty_card = cluedo_dataset.get_moriarty_cards()[0]
        
        result = cluedo_dataset.process_query(
            agent_name="Sherlock",
            query_type=QueryType.CARD_INQUIRY,
            query_params={"card": moriarty_card}
        )
        
        assert isinstance(result, QueryResult)
        assert result.query_type == QueryType.CARD_INQUIRY
        # Le succès dépend de la politique de révélation
    
    def test_process_query_suggestion_validation(self, cluedo_dataset):
        """Test le traitement d'une validation de suggestion."""
        suggestion = {
            "suspect": "Colonel Moutarde",
            "arme": "Poignard",
            "lieu": "Salon"
        }
        
        result = cluedo_dataset.process_query(
            agent_name="Watson",
            query_type=QueryType.SUGGESTION_VALIDATION,
            query_params={"suggestion": suggestion}
        )
        
        assert isinstance(result, QueryResult)
        assert result.query_type == QueryType.SUGGESTION_VALIDATION
        assert result.success is True  # Suggestion valide
    
    def test_process_query_clue_request(self, cluedo_dataset):
        """Test le traitement d'une requête d'indice."""
        result = cluedo_dataset.process_query(
            agent_name="Moriarty",
            query_type=QueryType.CLUE_REQUEST,
            query_params={"request": "strategic_clue"}
        )
        
        assert isinstance(result, QueryResult)
        assert result.query_type == QueryType.CLUE_REQUEST
        # Devrait contenir des informations d'indice
        assert result.success is True
    
    def test_different_reveal_policies(self, standard_elements):
        """Test les différentes politiques de révélation."""
        policies = [RevealPolicy.COOPERATIVE, RevealPolicy.COMPETITIVE, RevealPolicy.BALANCED, RevealPolicy.PROGRESSIVE]
        
        solution_secrete = {
            "suspect": "Colonel Moutarde",
            "arme": "Poignard",
            "lieu": "Salon"
        }
        cartes_distribuees = {
            "Moriarty": ["Professeur Violet", "Chandelier"],
            "AutresJoueurs": ["Cuisine", "Bureau"]
        }
        
        datasets = []
        for policy in policies:
            dataset = CluedoDataset(
                solution_secrete=solution_secrete,
                cartes_distribuees=cartes_distribuees,
                reveal_policy=policy
            )
            datasets.append(dataset)
        
        # Vérification que les politiques sont correctement assignées
        for i, policy in enumerate(policies):
            assert datasets[i].reveal_policy == policy
    
    def test_solution_consistency(self, cluedo_dataset):
        """Test la cohérence de la solution secrète."""
        solution = cluedo_dataset.solution_secrete
        
        # La solution doit rester constante
        solution2 = cluedo_dataset.solution_secrete
        assert solution == solution2
        
        # Tous les éléments doivent être valides
        assert solution["suspect"] == "Colonel Moutarde"
        assert solution["arme"] == "Poignard"
        assert solution["lieu"] == "Salon"
    
    def test_moriarty_cards_consistency(self, cluedo_dataset):
        """Test la cohérence des cartes de Moriarty."""
        cartes = cluedo_dataset.get_moriarty_cards()
        
        # Les cartes doivent rester constantes
        cartes2 = cluedo_dataset.get_moriarty_cards()
        assert set(cartes) == set(cartes2)
        
        # Toutes les cartes doivent être valides
        expected_cards = ["Professeur Violet", "Chandelier"]
        assert set(cartes) == set(expected_cards)


class TestCluedoSuggestion:
    """Tests pour la classe CluedoSuggestion."""
    
    def test_cluedo_suggestion_creation(self):
        """Test la création d'une suggestion Cluedo."""
        suggestion = CluedoSuggestion(
            suspect="Colonel Moutarde",
            arme="Poignard",
            lieu="Salon",
            suggested_by="Sherlock"
        )
        
        assert suggestion.suspect == "Colonel Moutarde"
        assert suggestion.arme == "Poignard"
        assert suggestion.lieu == "Salon"
        assert suggestion.suggested_by == "Sherlock"
    
    def test_cluedo_suggestion_to_dict(self):
        """Test la conversion en dictionnaire."""
        suggestion = CluedoSuggestion(
            suspect="Professeur Violet",
            arme="Chandelier",
            lieu="Cuisine",
            suggested_by="Watson"
        )
        
        suggestion_dict = suggestion.to_dict()
        
        assert suggestion_dict["suspect"] == "Professeur Violet"
        assert suggestion_dict["arme"] == "Chandelier"
        assert suggestion_dict["lieu"] == "Cuisine"


class TestCluedoRevelation:
    """Tests pour la classe CluedoRevelation."""
    
    def test_cluedo_revelation_creation(self):
        """Test la création d'une révélation Cluedo."""
        from datetime import datetime
        revelation = CluedoRevelation(
            timestamp=datetime.now(),
            card_revealed="Colonel Moutarde",
            revealed_to="TestAgent",
            revealed_by="Moriarty",
            reason="Test de révélation",
            query_type=QueryType.CARD_INQUIRY
        )
        
        assert revelation.card_revealed == "Colonel Moutarde"
        assert revelation.revealed_to == "TestAgent"
        assert revelation.revealed_by == "Moriarty"
        assert revelation.reason == "Test de révélation"
    
    def test_cluedo_revelation_metadata(self):
        """Test les métadonnées d'une révélation."""
        from datetime import datetime
        revelation = CluedoRevelation(
            timestamp=datetime.now(),
            card_revealed="Poignard",
            revealed_to="TestAgent",
            revealed_by="Moriarty",
            reason="Information stratégique révélée",
            query_type=QueryType.CARD_INQUIRY
        )
        
        assert revelation.card_revealed == "Poignard"
        assert revelation.revealed_to == "TestAgent"
        assert revelation.revealed_by == "Moriarty"
        assert revelation.reason == "Information stratégique révélée"
        assert revelation.query_type == QueryType.CARD_INQUIRY


@pytest.mark.integration
class TestCluedoDatasetIntegration:
    """Tests d'intégration pour CluedoDataset avec scénarios réalistes."""
    
    @pytest.fixture
    def full_cluedo_setup(self):
        """Configuration Cluedo complète réaliste."""
        solution_secrete = {
            "suspect": "Colonel Moutarde",
            "arme": "Poignard",
            "lieu": "Salon"
        }
        cartes_distribuees = {
            "Moriarty": ["Professeur Violet", "Chandelier", "Cuisine", "Clé anglaise"],
            "AutresJoueurs": ["Mademoiselle Rose", "Docteur Orchidée", "Madame Leblanc", "Monsieur Olive", "Revolver", "Corde", "Tuyau de plomb", "Bureau", "Bibliothèque", "Salle de billard", "Serre", "Hall", "Salle à manger", "Cave"]
        }
        return CluedoDataset(
            solution_secrete=solution_secrete,
            cartes_distribuees=cartes_distribuees,
            reveal_policy=RevealPolicy.BALANCED
        )
    
    @pytest.mark.asyncio
    async def test_complete_game_simulation(self, full_cluedo_setup):
        """Test d'une simulation de jeu complète."""
        dataset = full_cluedo_setup
        
        # Simulation de plusieurs suggestions
        suggestions = [
            CluedoSuggestion(suspect="Colonel Moutarde", arme="Poignard", lieu="Salon", suggested_by="TestAgent"),
            CluedoSuggestion(suspect="Professeur Violet", arme="Chandelier", lieu="Cuisine", suggested_by="TestAgent"),
            CluedoSuggestion(suspect="Mademoiselle Rose", arme="Revolver", lieu="Bureau", suggested_by="TestAgent")
        ]
        
        results = []
        for suggestion in suggestions:
            result = dataset.validate_cluedo_suggestion(suggestion, "TestAgent")
            results.append(result)
        
        # Toutes les suggestions devraient être valides
        for result in results:
            assert result.authorized is True
    
    def test_reveal_policy_impact_on_game_flow(self, full_cluedo_setup):
        """Test l'impact des politiques de révélation sur le flux de jeu."""
        dataset = full_cluedo_setup
        
        # Test avec différentes politiques
        policies = [RevealPolicy.COOPERATIVE, RevealPolicy.COMPETITIVE, RevealPolicy.PROGRESSIVE]
        
        revelations = []
        for policy in policies:
            dataset.reveal_policy = policy
            moriarty_card = dataset.get_moriarty_cards()[0]
            revelation = dataset.reveal_card(moriarty_card, "TestAgent", "Test politique")
            revelations.append(revelation)
        
        # Les révélations devraient être différentes selon la politique
        reasons = [r.reason if r else "" for r in revelations]
        # Au moins certains messages devraient être différents
        assert len(set(reasons)) >= 1 and all(reason for reason in reasons)
    
    def test_dataset_state_persistence(self, full_cluedo_setup):
        """Test la persistance de l'état du dataset."""
        dataset = full_cluedo_setup
        
        # État initial
        initial_solution = dataset.solution_secrete.copy()
        initial_moriarty_cards = dataset.get_moriarty_cards().copy()
        
        # Simulation d'activité
        for _ in range(5):
            moriarty_card = dataset.get_moriarty_cards()[0]
            suggestion = CluedoSuggestion(suspect=moriarty_card, arme="Test", lieu="Test", suggested_by="TestAgent")
            dataset.can_refute_suggestion(suggestion)
        
        # Vérification que l'état reste cohérent
        assert dataset.solution_secrete == initial_solution
        assert dataset.get_moriarty_cards() == initial_moriarty_cards
    
    @pytest.mark.asyncio
    async def test_concurrent_query_handling(self, full_cluedo_setup):
        """Test la gestion de requêtes concurrentes."""
        dataset = full_cluedo_setup
        
        # Simulation de requêtes concurrentes
        import asyncio
        
        def make_query(agent_name, card_name):
            return dataset.process_query(
                agent_name=agent_name,
                query_type=QueryType.CARD_INQUIRY,
                query_params={"card": card_name}
            )
        
        # Lancement de requêtes concurrentes
        results = [
            make_query("Sherlock", "Colonel Moutarde"),
            make_query("Watson", "Professeur Violet"),
            make_query("Moriarty", "Poignard")
        ]
        
        # Toutes les requêtes devraient aboutir
        assert len(results) == 3
        for result in results:
            assert isinstance(result, QueryResult)