# tests/unit/argumentation_analysis/core/test_logique_complexe_states.py
"""Tests for EinsteinsRiddleState and LogiqueBridgeState."""

import pytest

from argumentation_analysis.core.logique_complexe_states import (
    EinsteinsRiddleState,
    LogiqueBridgeState,
)

# ── EinsteinsRiddleState ──


class TestEinsteinsRiddleStateInit:
    def test_init_defaults(self):
        state = EinsteinsRiddleState()
        assert state.positions == [1, 2, 3, 4, 5]
        assert len(state.couleurs) == 5
        assert len(state.nationalites) == 5
        assert len(state.animaux) == 5
        assert len(state.boissons) == 5
        assert len(state.metiers) == 5

    def test_solution_generated(self):
        state = EinsteinsRiddleState()
        assert len(state.solution_secrete) == 5
        for pos in range(1, 6):
            assert pos in state.solution_secrete
            house = state.solution_secrete[pos]
            assert "couleur" in house
            assert "nationalite" in house
            assert "animal" in house
            assert "boisson" in house
            assert "metier" in house

    def test_initial_reasoning_state(self):
        state = EinsteinsRiddleState()
        assert state.clauses_logiques == []
        assert state.deductions_watson == []
        assert len(state.contraintes_formulees) == 0
        assert state.requetes_executees == []
        assert state.solution_partielle == {}
        assert state.etapes_raisonnement == 0

    def test_custom_context(self):
        state = EinsteinsRiddleState(initial_context={"mode": "test"})
        assert state.initial_context["mode"] == "test"


class TestEinsteinsRiddleConstraints:
    @pytest.fixture
    def state(self):
        return EinsteinsRiddleState()

    def test_get_contraintes_complexes(self, state):
        contraintes = state.get_contraintes_complexes()
        assert len(contraintes) == 15
        assert any("Anglais" in c for c in contraintes)
        assert any("Norvégien" in c for c in contraintes)

    def test_ajouter_clause_nouvelle(self, state):
        assert (
            state.ajouter_clause_logique(
                "forall(X, couleur(X, rouge) => nation(X, anglais))"
            )
            is True
        )
        assert len(state.clauses_logiques) == 1
        assert len(state.deductions_watson) == 1

    def test_ajouter_clause_duplicate(self, state):
        state.ajouter_clause_logique("clause1")
        assert state.ajouter_clause_logique("clause1") is False
        assert len(state.clauses_logiques) == 1

    def test_deductions_incremented(self, state):
        state.ajouter_clause_logique("c1")
        state.ajouter_clause_logique("c2")
        assert state.deductions_watson[0]["etape"] == 1
        assert state.deductions_watson[1]["etape"] == 2

    def test_clause_source(self, state):
        state.ajouter_clause_logique("c1", source="Sherlock")
        assert state.deductions_watson[0]["source"] == "Sherlock"


class TestEinsteinsRiddleQuery:
    @pytest.fixture
    def state(self):
        return EinsteinsRiddleState()

    def test_execute_existence_query(self, state):
        result = state.executer_requete_logique("existe(X, couleur(X, rouge))")
        assert result["type"] == "existence"
        assert result["resultat"] is True

    def test_execute_universal_query(self, state):
        result = state.executer_requete_logique("forall(X, prop(X))")
        assert result["type"] == "universel"
        assert result["resultat"] is False

    def test_execute_satisfiability_query(self, state):
        result = state.executer_requete_logique("some_other_query")
        assert result["type"] == "satisfiabilite"
        assert result["resultat"] is True

    def test_query_recorded(self, state):
        state.executer_requete_logique("q1")
        state.executer_requete_logique("q2")
        assert len(state.requetes_executees) == 2
        assert state.requetes_executees[0]["etape"] == 1


class TestEinsteinsRiddleProgression:
    @pytest.fixture
    def state(self):
        return EinsteinsRiddleState()

    def test_insufficient_progression(self, state):
        prog = state.verifier_progression_logique()
        assert prog["force_logique_formelle"] is False
        assert prog["clauses_formulees"] == 0

    def test_sufficient_progression(self, state):
        for i in range(10):
            state.ajouter_clause_logique(f"clause_{i}")
        for i in range(5):
            state.executer_requete_logique(f"query_{i}")
        prog = state.verifier_progression_logique()
        assert prog["force_logique_formelle"] is True

    def test_obtenir_etat_progression(self, state):
        etat = state.obtenir_etat_progression()
        assert "contraintes_disponibles" in etat
        assert "clauses_watson" in etat
        assert "progression_logique" in etat
        assert "etapes_restantes" in etat
        assert etat["etapes_restantes"] == 15


class TestEinsteinsRiddleSolution:
    @pytest.fixture
    def state(self):
        return EinsteinsRiddleState()

    def test_propose_without_enough_logic(self, state):
        result = state.proposer_solution_complexe(state.solution_secrete)
        assert result["acceptee"] is False
        assert "logique" in result["raison"].lower()

    def test_propose_correct_with_enough_logic(self, state):
        for i in range(10):
            state.ajouter_clause_logique(f"clause_{i}")
        for i in range(5):
            state.executer_requete_logique(f"query_{i}")
        result = state.proposer_solution_complexe(state.solution_secrete)
        assert result["acceptee"] is True

    def test_propose_wrong_with_enough_logic(self, state):
        for i in range(10):
            state.ajouter_clause_logique(f"clause_{i}")
        for i in range(5):
            state.executer_requete_logique(f"query_{i}")
        wrong = {
            1: {
                "couleur": "X",
                "nationalite": "X",
                "animal": "X",
                "boisson": "X",
                "metier": "X",
            }
        }
        result = state.proposer_solution_complexe(wrong)
        assert result["acceptee"] is False
        assert "incorrecte" in result["raison"].lower()

    def test_generer_indices_complexes(self, state):
        indices = state._generer_indices_complexes()
        assert len(indices) >= 1
        assert any("existe" in i.lower() for i in indices)


# ── LogiqueBridgeState ──


class TestLogiqueBridgeStateInit:
    def test_init(self):
        state = LogiqueBridgeState()
        assert state.cannibales_gauche == 5
        assert state.missionnaires_gauche == 5
        assert state.cannibales_droite == 0
        assert state.missionnaires_droite == 0
        assert state.bateau_position == "gauche"
        assert state.capacite_bateau == 3


class TestLogiqueBridgeValidation:
    @pytest.fixture
    def state(self):
        return LogiqueBridgeState()

    def test_valid_initial_state(self, state):
        assert state.etat_valide(5, 5, 0, 0) is True

    def test_valid_equal_both_sides(self, state):
        assert state.etat_valide(2, 2, 3, 3) is True

    def test_invalid_negative(self, state):
        assert state.etat_valide(-1, 5, 6, 0) is False

    def test_invalid_cannibals_outnumber_left(self, state):
        assert state.etat_valide(3, 2, 2, 3) is False  # 3c > 2m left

    def test_invalid_cannibals_outnumber_right(self, state):
        assert state.etat_valide(2, 3, 3, 2) is False  # 3c > 2m right

    def test_valid_zero_missionaries(self, state):
        # If missionaries = 0, cannibals don't outnumber
        assert state.etat_valide(3, 0, 2, 5) is True

    def test_not_at_objective(self, state):
        assert state.etat_objectif() is False

    def test_at_objective(self, state):
        state.cannibales_gauche = 0
        state.missionnaires_gauche = 0
        state.cannibales_droite = 5
        state.missionnaires_droite = 5
        assert state.etat_objectif() is True

    def test_generer_actions(self, state):
        actions = state.generer_actions_possibles()
        assert len(actions) > 0
        # Each action has at least 1 person
        for c, m in actions:
            assert c + m >= 1
            assert c + m <= state.capacite_bateau
            assert c >= 0
            assert m >= 0
