import sys
import os
import json
import logging
import pytest
from unittest.mock import MagicMock, patch

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TestEnhancedContextualFallacyAnalyzerPytest")

# Import du module à tester
from ..logic.contextual_fallacy_analyzer import (
    EnhancedContextualFallacyAnalyzer,
    HAS_TRANSFORMERS,
)


@pytest.fixture
def mock_dependencies(mocker):
    """Fixture to mock heavy dependencies like torch and transformers."""
    # Mock 'torch'
    mock_torch = MagicMock()
    mocker.patch.dict(sys.modules, {"torch": mock_torch})

    # Mock 'transformers'
    mock_transformers = MagicMock()
    mock_auto_tokenizer = MagicMock()
    mock_auto_tokenizer.from_pretrained.return_value = MagicMock()
    mock_transformers.AutoTokenizer = mock_auto_tokenizer

    mock_auto_model = MagicMock()
    mock_auto_model.from_pretrained.return_value = MagicMock()
    mock_transformers.AutoModelForSequenceClassification = mock_auto_model

    mock_pipeline = MagicMock()
    mock_transformers.pipeline = mock_pipeline

    mocker.patch.dict(sys.modules, {"transformers": mock_transformers})

    # Patch the HAS_TRANSFORMERS flag in the module under test
    mocker.patch(
        "plugins.AnalysisToolsPlugin.logic.contextual_fallacy_analyzer.HAS_TRANSFORMERS",
        True,
    )

    return mock_torch, mock_transformers


@pytest.fixture
def analyzer_instance(mock_dependencies):
    """Fixture pour initialiser EnhancedContextualFallacyAnalyzer pour chaque test."""
    logger.debug("Initialisation de EnhancedContextualFallacyAnalyzer pour un test.")
    analyzer = EnhancedContextualFallacyAnalyzer(model_name="distilbert-base-uncased")
    return analyzer


def test_initialization(analyzer_instance):
    """Test l'initialisation de l'analyseur."""
    assert analyzer_instance is not None
    assert analyzer_instance.logger is not None
    assert analyzer_instance.model_name is not None
    assert analyzer_instance.feedback_history is not None
    assert analyzer_instance.context_embeddings_cache is not None
    assert analyzer_instance.last_analysis_fallacies is not None
    assert analyzer_instance.nlp_models is not None
    assert analyzer_instance.learning_data is not None


def test_analyze_context(analyzer_instance):
    """Test l'analyse contextuelle."""
    text = "Les experts affirment que ce produit est sûr et efficace."
    context = "Discours commercial pour un produit controversé"

    with patch.object(
        analyzer_instance,
        "_analyze_context_deeply",
        return_value={
            "context_type": "commercial",
            "context_subtypes": ["publicitaire"],
            "audience_characteristics": ["grand public"],
            "formality_level": "moyen",
            "confidence": 0.8,
        },
    ) as mock_analyze_context, patch.object(
        analyzer_instance,
        "_identify_potential_fallacies_with_nlp",
        return_value=[
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "experts",
                "context_text": text,
                "confidence": 0.7,
                "detection_method": "keyword_matching",
            }
        ],
    ) as mock_identify_fallacies, patch.object(
        analyzer_instance,
        "_filter_by_context_semantic",
        return_value=[
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "experts",
                "context_text": text,
                "confidence": 0.8,
                "detection_method": "keyword_matching",
                "contextual_relevance": "Élevée",
                "context_adjustment": 0.1,
            }
        ],
    ) as mock_filter_context, patch.object(
        analyzer_instance, "_analyze_fallacy_relations", return_value=[]
    ) as mock_analyze_relations:
        result = analyzer_instance.analyze_context(text, context)

        mock_analyze_context.assert_called_once_with(context)
        mock_identify_fallacies.assert_called_once_with(text)
        mock_filter_context.assert_called_once()
        mock_analyze_relations.assert_called_once()

        assert isinstance(result, dict)
        assert "context_analysis" in result
        assert result["context_analysis"]["context_type"] == "commercial"
        assert result["potential_fallacies_count"] == 1
        assert result["contextual_fallacies_count"] == 1
        assert len(result["contextual_fallacies"]) == 1
        assert result["contextual_fallacies"][0]["fallacy_type"] == "Appel à l'autorité"


def test_analyze_context_deeply(analyzer_instance):
    """Test l'analyse approfondie du contexte."""
    context = "Discours politique lors d'une campagne électorale"
    with patch.object(
        analyzer_instance, "_determine_context_type", return_value="politique"
    ) as mock_determine_context:
        result = analyzer_instance._analyze_context_deeply(context)
        mock_determine_context.assert_called_once_with(context)
        assert isinstance(result, dict)
        assert result["context_type"] == "politique"
        assert result["formality_level"] in ["élevé", "moyen", "faible"]


def test_identify_potential_fallacies_with_nlp(analyzer_instance):
    """Test l'identification des sophismes potentiels avec NLP."""
    text = "Les experts affirment que ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
    with patch.object(
        analyzer_instance,
        "_identify_potential_fallacies",
        return_value=[
            {
                "fallacy_type": "Appel à l'autorité",
                "keyword": "experts",
                "context_text": text[:50],
                "confidence": 0.7,
                "detection_method": "keyword_matching",
            },
            {
                "fallacy_type": "Appel à la popularité",
                "keyword": "millions",
                "context_text": text[50:],
                "confidence": 0.6,
                "detection_method": "keyword_matching",
            },
        ],
    ) as mock_identify_fallacies:
        result = analyzer_instance._identify_potential_fallacies_with_nlp(text)
        mock_identify_fallacies.assert_called_once_with(text)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["fallacy_type"] == "Appel à l'autorité"
        popularity_fallacy = next(
            (f for f in result if f["fallacy_type"] == "Appel à la popularité"), None
        )
        assert popularity_fallacy is not None


def test_filter_by_context_semantic(analyzer_instance):
    """Test le filtrage sémantique par contexte."""
    potential_fallacies = [
        {
            "fallacy_type": "Appel à l'autorité",
            "keyword": "experts",
            "context_text": "Les experts...",
            "confidence": 0.7,
            "detection_method": "keyword_matching",
        },
        {
            "fallacy_type": "Appel à la popularité",
            "keyword": "millions",
            "context_text": "Des millions...",
            "confidence": 0.6,
            "detection_method": "keyword_matching",
        },
    ]
    context_analysis = {
        "context_type": "commercial",
        "context_subtypes": ["publicitaire"],
        "audience_characteristics": ["généraliste"],
        "formality_level": "informel",
        "confidence": 0.8,
    }
    result = analyzer_instance._filter_by_context_semantic(
        potential_fallacies, context_analysis
    )
    assert isinstance(result, list)
    assert len(result) == 2
    fallacy_types = [f["fallacy_type"] for f in result]
    assert "Appel à l'autorité" in fallacy_types
    assert "Appel à la popularité" in fallacy_types
    assert "contextual_relevance" in result[0]
    assert result[0]["confidence"] >= result[1]["confidence"]


def test_analyze_fallacy_relations(analyzer_instance):
    """Test l'analyse des relations entre sophismes."""
    fallacies = [
        {
            "fallacy_type": "Appel à l'autorité",
            "confidence": 0.7,
            "context_text": "Les experts affirment...",
        },
        {
            "fallacy_type": "Appel à la popularité",
            "confidence": 0.6,
            "context_text": "Des millions de personnes...",
        },
        {
            "fallacy_type": "Appel à la peur",
            "confidence": 0.8,
            "context_text": "Si nous ne faisons rien...",
        },
    ]
    result = analyzer_instance._analyze_fallacy_relations(fallacies)
    assert isinstance(result, list)
    if len(result) > 0:
        relation = result[0]
        assert "relation_type" in relation
        assert "strength" in relation


def test_are_complementary_fallacies(analyzer_instance):
    """Test la complémentarité des sophismes."""
    assert analyzer_instance._are_complementary_fallacies(
        "Appel à l'autorité", "Appel à la popularité"
    )
    assert not analyzer_instance._are_complementary_fallacies(
        "Appel à l'autorité", "Pente glissante"
    )


def test_identify_contextual_fallacies(analyzer_instance):
    """Test l'identification des sophismes contextuels."""
    argument = "Les experts affirment que ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
    context = "Discours commercial pour un produit controversé"
    mock_analysis_result = {
        "context_analysis": {"context_type": "commercial", "confidence": 0.8},
        "potential_fallacies_count": 2,
        "contextual_fallacies_count": 2,
        "contextual_fallacies": [
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.7},
            {"fallacy_type": "Appel à la popularité", "confidence": 0.6},
        ],
        "fallacy_relations": [],
        "analysis_timestamp": "...",
    }
    with patch.object(
        analyzer_instance, "analyze_context", return_value=mock_analysis_result
    ) as mock_analyze_context:
        result = analyzer_instance.identify_contextual_fallacies(argument, context)
        mock_analyze_context.assert_called_once_with(argument, context)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["fallacy_type"] == "Appel à l'autorité"


def test_provide_feedback(analyzer_instance):
    """Test la fourniture de feedback."""
    analyzer_instance.last_analysis_fallacies = {
        "fallacy_1": {"fallacy_type": "Appel à l'autorité", "confidence": 0.7}
    }
    with patch.object(analyzer_instance, "_save_learning_data") as mock_save:
        analyzer_instance.provide_feedback("fallacy_1", True, "Bonne détection")
        mock_save.assert_called_once()
        assert len(analyzer_instance.feedback_history) == 1
        feedback = analyzer_instance.feedback_history[0]
        assert feedback["fallacy_id"] == "fallacy_1"
        assert feedback["is_correct"] is True
        assert (
            "Appel à l'autorité"
            in analyzer_instance.learning_data["confidence_adjustments"]
        )


def test_get_contextual_fallacy_examples(analyzer_instance):
    """Test l'obtention d'exemples de sophismes contextuels."""
    parent_class_mock_target = "plugins.AnalysisToolsPlugin.logic.contextual_fallacy_analyzer.BaseAnalyzer.get_contextual_fallacy_examples"

    with patch(
        parent_class_mock_target, return_value=["Exemple 1.", "Exemple 2."]
    ) as mock_parent_method, patch.object(
        analyzer_instance, "_generate_fallacy_explanation", return_value="Expl."
    ) as mock_expl, patch.object(
        analyzer_instance, "_generate_correction_suggestion", return_value="Corr."
    ) as mock_corr:
        result = analyzer_instance.get_contextual_fallacy_examples(
            "Appel à l'autorité", "commercial"
        )

        mock_parent_method.assert_called_once_with("Appel à l'autorité", "commercial")
        assert mock_expl.call_count == 2
        assert mock_corr.call_count == 2
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["explanation"] == "Expl."
