# tests/unit/argumentation_analysis/orchestration/test_logique_complexe_plugin.py
"""Tests for LogiqueComplexePlugin — Einstein's Riddle puzzle plugin."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_state():
    """Create a mock EinsteinsRiddleState."""
    state = MagicMock()
    state.positions = [1, 2, 3, 4, 5]
    state.couleurs = ["Rouge", "Verte", "Blanche", "Jaune", "Bleue"]
    state.nationalites = ["Anglais", "Suédois", "Danois", "Norvégien", "Allemand"]
    state.animaux = ["Chien", "Chat", "Oiseau", "Cheval", "Poisson"]
    state.boissons = ["Thé", "Café", "Lait", "Bière", "Eau"]
    state.metiers = ["Avocat", "Médecin", "Ingénieur", "Architecte", "Professeur"]
    state.clauses_logiques = []
    state.solution_secrete = {
        1: {"couleur": "Jaune", "nationalité": "Norvégien"},
        2: {"couleur": "Bleue", "nationalité": "Danois"},
        3: {"couleur": "Rouge", "nationalité": "Anglais"},
    }
    state.solution_partielle = {}
    return state


@pytest.fixture
def plugin(mock_state):
    from argumentation_analysis.orchestration.plugins.logique_complexe_plugin import LogiqueComplexePlugin
    return LogiqueComplexePlugin(state_instance=mock_state)


# ============================================================================
# Init Tests
# ============================================================================

class TestLogiqueComplexePluginInit:

    def test_init_stores_state(self, plugin, mock_state):
        assert plugin._state is mock_state

    def test_init_creates_logger(self, plugin):
        assert plugin._logger is not None

    def test_init_logger_name(self, plugin):
        assert "LogiqueComplexePlugin" in plugin._logger.name


# ============================================================================
# get_enigme_description Tests
# ============================================================================

class TestGetEnigmeDescription:

    def test_returns_string(self, plugin):
        result = plugin.get_enigme_description()
        assert isinstance(result, str)

    def test_contains_enigme(self, plugin):
        result = plugin.get_enigme_description()
        assert "Énigme" in result

    def test_contains_domaines(self, plugin, mock_state):
        result = plugin.get_enigme_description()
        assert "positions" in result
        assert "couleurs" in result
        assert "nationalités" in result

    def test_contains_objectif(self, plugin):
        result = plugin.get_enigme_description()
        assert "poisson" in result


# ============================================================================
# get_contraintes_logiques Tests
# ============================================================================

class TestGetContraintesLogiques:

    def test_returns_string(self, plugin, mock_state):
        mock_state.get_contraintes_complexes.return_value = ["c1", "c2", "c3"]
        result = plugin.get_contraintes_logiques()
        assert isinstance(result, str)

    def test_contains_count(self, plugin, mock_state):
        mock_state.get_contraintes_complexes.return_value = ["c1", "c2"]
        result = plugin.get_contraintes_logiques()
        assert "'nombre_total': 2" in result

    def test_calls_state_method(self, plugin, mock_state):
        mock_state.get_contraintes_complexes.return_value = []
        plugin.get_contraintes_logiques()
        mock_state.get_contraintes_complexes.assert_called_once()


# ============================================================================
# formuler_clause_logique Tests
# ============================================================================

class TestFormulerClauseLogique:

    def test_clause_too_short(self, plugin):
        result = plugin.formuler_clause_logique("abc")
        assert "Erreur" in result
        assert "trop courte" in result

    def test_clause_added_successfully(self, plugin, mock_state):
        mock_state.ajouter_clause_logique.return_value = True
        mock_state.verifier_progression_logique.return_value = {"clauses_formulees": 1}
        result = plugin.formuler_clause_logique(
            "∀x (Maison(x) ∧ Couleur(x,Rouge) → Nationalité(x,Anglais))",
            justification="Constraint 1"
        )
        assert "ajoutée avec succès" in result
        assert "Constraint 1" in result

    def test_clause_already_exists(self, plugin, mock_state):
        mock_state.ajouter_clause_logique.return_value = False
        result = plugin.formuler_clause_logique("existing clause here text")
        assert "déjà existante" in result

    def test_clause_with_empty_justification(self, plugin, mock_state):
        mock_state.ajouter_clause_logique.return_value = True
        mock_state.verifier_progression_logique.return_value = {"clauses_formulees": 1}
        result = plugin.formuler_clause_logique("a valid clause longer than 10 chars")
        assert "ajoutée" in result

    def test_clause_strips_whitespace(self, plugin):
        result = plugin.formuler_clause_logique("   short   ")
        assert "Erreur" in result  # "short" < 10 chars


# ============================================================================
# executer_requete_tweety Tests
# ============================================================================

class TestExecuterRequeteTweety:

    def test_insufficient_clauses(self, plugin, mock_state):
        mock_state.clauses_logiques = ["c1", "c2"]  # < 3
        result = plugin.executer_requete_tweety("query")
        assert "Erreur" in result
        assert "au moins 3" in result

    def test_successful_query(self, plugin, mock_state):
        mock_state.clauses_logiques = ["c1", "c2", "c3"]
        mock_state.executer_requete_logique.return_value = {"result": True}
        mock_state.verifier_progression_logique.return_value = {"requetes_executees": 1}
        result = plugin.executer_requete_tweety("∀x Position(x)")
        assert "exécutée" in result

    def test_query_with_type(self, plugin, mock_state):
        mock_state.clauses_logiques = ["c1", "c2", "c3"]
        mock_state.executer_requete_logique.return_value = {"result": "sat"}
        mock_state.verifier_progression_logique.return_value = {"requetes_executees": 2}
        result = plugin.executer_requete_tweety("query", type_requete="satisfiabilite")
        assert "exécutée" in result


# ============================================================================
# verifier_deduction_partielle Tests
# ============================================================================

class TestVerifierDeductionPartielle:

    def test_invalid_position(self, plugin, mock_state):
        result = plugin.verifier_deduction_partielle(99, {"couleur": "Rouge"})
        assert "Erreur" in result
        assert "invalide" in result

    def test_correct_deduction(self, plugin, mock_state):
        result = plugin.verifier_deduction_partielle(
            3, {"couleur": "Rouge", "nationalité": "Anglais"}
        )
        assert "correcte" in result
        assert "2/2" in result

    def test_incorrect_deduction(self, plugin, mock_state):
        result = plugin.verifier_deduction_partielle(
            1, {"couleur": "Rouge"}  # Position 1 is Jaune
        )
        assert "incorrecte" in result
        assert "0/1" in result

    def test_partial_deduction(self, plugin, mock_state):
        result = plugin.verifier_deduction_partielle(
            1, {"couleur": "Jaune", "nationalité": "Anglais"}  # couleur correct, nat wrong
        )
        assert "1/2" in result

    def test_correct_updates_solution_partielle(self, plugin, mock_state):
        chars = {"couleur": "Rouge", "nationalité": "Anglais"}
        plugin.verifier_deduction_partielle(3, chars)
        assert mock_state.solution_partielle[3] == chars


# ============================================================================
# proposer_solution_complete Tests
# ============================================================================

class TestProposerSolutionComplete:

    def test_solution_accepted(self, plugin, mock_state):
        mock_state.proposer_solution_complexe.return_value = {
            "acceptee": True,
            "message": "Correct!",
            "score_logique": 0.95,
        }
        result = plugin.proposer_solution_complete({1: {"couleur": "Rouge"}})
        assert "acceptée" in result
        assert "0.95" in result

    def test_solution_rejected_no_formal_logic(self, plugin, mock_state):
        mock_state.proposer_solution_complexe.return_value = {
            "acceptee": False,
            "raison": "Insufficient logic",
        }
        mock_state.verifier_progression_logique.return_value = {
            "force_logique_formelle": False,
            "clauses_formulees": 1,
            "requetes_executees": 0,
        }
        result = plugin.proposer_solution_complete({})
        assert "rejetée" in result
        assert "clauses" in result

    def test_solution_rejected_with_formal_logic(self, plugin, mock_state):
        mock_state.proposer_solution_complexe.return_value = {
            "acceptee": False,
            "raison": "Wrong answer",
        }
        mock_state.verifier_progression_logique.return_value = {
            "force_logique_formelle": True,
        }
        result = plugin.proposer_solution_complete({})
        assert "incorrecte" in result


# ============================================================================
# obtenir_progression_logique Tests
# ============================================================================

class TestObtenirProgressionLogique:

    def test_returns_string(self, plugin, mock_state):
        mock_state.obtenir_etat_progression.return_value = {"progress": "50%"}
        result = plugin.obtenir_progression_logique()
        assert isinstance(result, str)
        assert "50%" in result


# ============================================================================
# generer_indice_complexe Tests
# ============================================================================

class TestGenererIndiceComplexe:

    def test_returns_string(self, plugin):
        result = plugin.generer_indice_complexe()
        assert isinstance(result, str)

    def test_contains_constraint(self, plugin):
        result = plugin.generer_indice_complexe()
        assert "Constraint" in result or "Indice" in result

    def test_contains_formalization_instruction(self, plugin):
        result = plugin.generer_indice_complexe()
        assert "TweetyProject" in result


# ============================================================================
# valider_syntaxe_tweety Tests
# ============================================================================

class TestValiderSyntaxeTweety:

    def test_valid_clause(self, plugin):
        result = plugin.valider_syntaxe_tweety(
            "∀x (Maison(x) ∧ Couleur(x,Rouge) → Nationalité(x,Anglais))"
        )
        assert "valide" in result

    def test_missing_operators(self, plugin):
        result = plugin.valider_syntaxe_tweety("Maison(x) has Couleur Rouge for the test")
        assert "invalide" in result
        assert "opérateurs" in result

    def test_missing_predicates(self, plugin):
        result = plugin.valider_syntaxe_tweety("∀x (P(x) → Q(x))")
        assert "invalide" in result
        assert "prédicats" in result

    def test_too_short(self, plugin):
        result = plugin.valider_syntaxe_tweety("∀x Maison")
        assert "invalide" in result
        assert "trop simple" in result

    def test_all_errors_combined(self, plugin):
        result = plugin.valider_syntaxe_tweety("short")
        assert "invalide" in result

    def test_valid_with_exists(self, plugin):
        result = plugin.valider_syntaxe_tweety(
            "∃x (Position(x,3) ∧ Boisson(x,Lait))"
        )
        assert "valide" in result
