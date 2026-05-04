"""Unit tests for quality_evaluator virtue detectors — edge cases and fallback paths.

Target: argumentation_analysis/agents/core/quality/quality_evaluator.py (60% → 80%+)
Tests the individual detect_* functions and ArgumentQualityEvaluator.evaluate().
Uses mocked _load_deps to avoid torch DLL crash and test fallback heuristics.
"""

import pytest
from unittest.mock import patch

import argumentation_analysis.agents.core.quality.quality_evaluator as qe


# Patch _load_deps to always return False (force fallback heuristics)
# This prevents the torch DLL crash on Windows
@pytest.fixture(autouse=True)
def mock_load_deps():
    with patch.object(qe, "_load_deps", return_value=False):
        # Also ensure globals are set to fallback state
        qe._nlp = None
        qe._flesch_reading_ease = None
        qe._DEPS_AVAILABLE = False
        yield


class TestDetectClarte:
    def test_short_words_clear(self):
        score, comment = qe.detect_clarte("Le chat est sur le lit.")
        assert 0.0 <= score <= 1.0
        assert score >= 0.5  # Short words → clear

    def test_long_words_complex(self):
        text = "anticonstitutionnellement institutionnalisations disproportionnellement"
        score, _ = qe.detect_clarte(text)
        assert score <= 0.5  # Long words → unclear

    def test_empty_text(self):
        score, _ = qe.detect_clarte("")
        assert 0.0 <= score <= 1.0


class TestDetectPertinence:
    def test_with_connectors(self):
        text = "Il pleut donc le sol est mouillé car l'eau tombe."
        score, comment = qe.detect_pertinence(text)
        assert score >= 0.5
        assert "connecteur" in comment.lower()

    def test_no_connectors(self):
        text = "Il fait beau. Le soleil brille."
        score, comment = qe.detect_pertinence(text)
        assert score <= 0.2

    def test_single_connector(self):
        text = "Cependant, le résultat est mitigé."
        score, _ = qe.detect_pertinence(text)
        assert score == 0.5


class TestDetectPresenceSources:
    def test_with_citations(self):
        text = "Selon l'étude (Smith, 2020), le résultat est positif. Voir [1]."
        score, comment = qe.detect_presence_sources(text)
        assert score >= 0.5
        assert "source" in comment.lower()

    def test_no_sources(self):
        text = "Je pense que c'est vrai."
        score, _ = qe.detect_presence_sources(text)
        assert score == 0.0

    def test_single_source(self):
        text = "Selon Dupont, le résultat est clair."
        score, _ = qe.detect_presence_sources(text)
        assert score == 0.5


class TestDetectRefutationConstructive:
    def test_with_refutation(self):
        text = "Certains pensent que X est vrai, cependant les faits montrent le contraire."
        score, comment = qe.detect_refutation_constructive(text)
        assert score == 1.0
        assert "réfutation" in comment.lower()

    def test_no_refutation(self):
        text = "Le ciel est bleu. Les oiseaux chantent."
        score, _ = qe.detect_refutation_constructive(text)
        assert score == 0.0


class TestDetectStructureLogique:
    def test_structured_text(self):
        text = "Il pleut car le ciel est gris. Donc nous restons. Cependant, demain sera beau."
        score, _ = qe.detect_structure_logique(text)
        assert score == 1.0

    def test_unstructured_text(self):
        text = "Bonjour le monde."
        score, _ = qe.detect_structure_logique(text)
        assert score == 0.0

    def test_single_connector(self):
        text = "Il pleut mais c'est normal."
        score, _ = qe.detect_structure_logique(text)
        assert score == 0.5


class TestDetectAnalogiePertinente:
    def test_with_analogy(self):
        text = "C'est comme si le monde entier Changeait. Tel que prévu."
        score, comment = qe.detect_analogie_pertinente(text)
        assert score == 1.0

    def test_no_analogy(self):
        text = "Le résultat est 42."
        score, _ = qe.detect_analogie_pertinente(text)
        assert score == 0.0


class TestDetectFiabiliteSources:
    def test_with_credible_source(self):
        text = "Selon l'OMS, la santé mondiale s'améliore."
        score, comment = qe.detect_fiabilite_sources(text)
        assert score == 1.0
        assert "OMS" in comment

    def test_with_gov_source(self):
        text = "Les données de .gouv.fr confirment ceci."
        score, _ = qe.detect_fiabilite_sources(text)
        assert score == 1.0

    def test_no_credible_source(self):
        text = "Mon voisin a dit que c'était vrai."
        score, _ = qe.detect_fiabilite_sources(text)
        assert score == 0.0


class TestDetectExhaustivite:
    def test_long_text(self):
        text = "Première phrase. Deuxième phrase. Troisième phrase. Quatrième. Cinquième. Sixième."
        score, _ = qe.detect_exhaustivite(text)
        assert score == 1.0  # 6+ sentences

    def test_medium_text(self):
        text = "Première phrase. Deuxième phrase. Troisième phrase."
        score, _ = qe.detect_exhaustivite(text)
        assert score == 0.5

    def test_short_text(self):
        text = "Une phrase."
        score, _ = qe.detect_exhaustivite(text)
        assert score == 0.0


class TestDetectRedondanceFaible:
    def test_no_redundancy(self):
        text = "Le chat noir mange sa nourriture sur la table haute."
        score, _ = qe.detect_redondance_faible(text)
        assert score >= 0.5  # Mostly unique words

    def test_high_redundancy(self):
        text = "chat chat chat chat chat chat"
        score, _ = qe.detect_redondance_faible(text)
        assert score == 0.0  # Very redundant

    def test_empty_text(self):
        score, comment = qe.detect_redondance_faible("")
        assert score == 0.0
        assert "vide" in comment.lower()


class TestArgumentQualityEvaluator:
    def test_evaluate_returns_all_virtues(self):
        evaluator = qe.ArgumentQualityEvaluator()
        text = "Selon l'OMS (2024), la santé mondiale s'améliore car les traitements sont meilleurs. Cependant, certains pensent que les inégalités persistent. C'est comme si rien n'avait changé pour les plus pauvres. En effet, les données INSEE montrent des écarts croissants. Par conséquent, nous devons agir."
        result = evaluator.evaluate(text)

        assert "note_finale" in result
        assert "note_moyenne" in result
        assert "scores_par_vertu" in result
        assert "rapport_detaille" in result
        assert len(result["scores_par_vertu"]) == len(qe.VERTUES)

    def test_evaluate_empty_text(self):
        evaluator = qe.ArgumentQualityEvaluator()
        result = evaluator.evaluate("")
        assert result["note_finale"] >= 0
        assert result["note_moyenne"] >= 0

    def test_evaluate_with_custom_detectors(self):
        custom = {"custom_virtue": lambda t: (0.5, "test")}
        evaluator = qe.ArgumentQualityEvaluator(detectors=custom)
        result = evaluator.evaluate("anything")
        assert "custom_virtue" in result["scores_par_vertu"]
        assert result["scores_par_vertu"]["custom_virtue"] == 0.5

    def test_evaluate_detector_exception_handled(self):
        def failing_detector(text):
            raise ValueError("test error")

        evaluator = qe.ArgumentQualityEvaluator(detectors={"failing": failing_detector})
        result = evaluator.evaluate("test")
        assert result["scores_par_vertu"]["failing"] == 0.0
        assert "Erreur" in result["rapport_detaille"]["failing"]

    def test_note_moyenne_is_average(self):
        evaluator = qe.ArgumentQualityEvaluator()
        result = evaluator.evaluate("Test text with donc and car.")
        n = len(result["scores_par_vertu"])
        assert abs(result["note_moyenne"] - result["note_finale"] / n) < 0.01


class TestEvaluerArgument:
    def test_convenience_function(self):
        result = qe.evaluer_argument("Selon l'OMS, c'est vrai car les données le montrent.")
        assert "note_finale" in result


class TestVertuesAndDetectors:
    def test_all_vertues_have_detectors(self):
        for v in qe.VERTUES:
            assert v in qe.DETECTORS, f"Missing detector for virtue: {v}"

    def test_detector_count(self):
        assert len(qe.DETECTORS) == 9
