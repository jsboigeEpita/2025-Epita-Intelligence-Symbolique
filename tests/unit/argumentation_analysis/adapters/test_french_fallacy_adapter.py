"""
Tests for FrenchFallacyAdapter (3-tier hybrid fallacy detection).

Tests validate:
- Module and class imports
- Symbolic detection tier (with/without spaCy)
- NLI detection tier availability check
- LLM detection tier availability check
- Ensemble merging logic
- FallacyAnalysisResult data class
- Adapter detect() returns correct structure
- CapabilityRegistry registration
- Graceful degradation when no tiers available
"""

from unittest.mock import MagicMock, patch

import pytest


class TestImports:
    """Test that adapter classes are importable."""

    def test_import_adapter(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        assert FrenchFallacyAdapter is not None

    def test_import_symbolic_detector(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            SymbolicFallacyDetector,
        )

        assert SymbolicFallacyDetector is not None

    def test_import_nli_detector(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        assert NLIFallacyDetector is not None

    def test_import_llm_detector(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        assert LLMFallacyDetector is not None

    def test_import_data_classes(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyDetection,
            FallacyAnalysisResult,
        )

        assert FallacyDetection is not None
        assert FallacyAnalysisResult is not None

    def test_implements_abstract_interface(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )
        from argumentation_analysis.core.interfaces.fallacy_detector import (
            AbstractFallacyDetector,
        )

        assert issubclass(FrenchFallacyAdapter, AbstractFallacyDetector)


class TestFallacyDetection:
    """Test FallacyDetection data class."""

    def test_creation(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyDetection,
        )

        d = FallacyDetection(
            fallacy_type="Ad Hominem",
            confidence=0.95,
            source="symbolic",
            matched_rule="tu es idiot",
        )
        assert d.fallacy_type == "Ad Hominem"
        assert d.confidence == 0.95
        assert d.source == "symbolic"

    def test_optional_fields(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyDetection,
        )

        d = FallacyDetection(fallacy_type="test", confidence=0.5, source="nli")
        assert d.matched_rule is None
        assert d.description is None


class TestFallacyAnalysisResult:
    """Test FallacyAnalysisResult data class and to_dict()."""

    def test_empty_result(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyAnalysisResult,
        )

        result = FallacyAnalysisResult(text="test")
        d = result.to_dict()
        assert d["text"] == "test"
        assert d["detected_fallacies"] == {}
        assert d["total_fallacies"] == 0
        assert d["tiers_used"] == []

    def test_result_with_fallacies(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyAnalysisResult,
            FallacyDetection,
        )

        result = FallacyAnalysisResult(
            text="test",
            fallacies=[
                FallacyDetection("Ad Hominem", 1.0, "symbolic", "tu es"),
                FallacyDetection("Pente glissante", 0.8, "nli"),
            ],
            tiers_used=["symbolic", "nli"],
        )
        d = result.to_dict()
        assert d["total_fallacies"] == 2
        assert "Ad Hominem" in d["detected_fallacies"]
        assert d["detected_fallacies"]["Ad Hominem"]["confidence"] == 1.0


class TestSymbolicDetector:
    """Test the symbolic (spaCy) fallacy detector."""

    def test_is_available_without_spacy(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            SymbolicFallacyDetector,
        )

        detector = SymbolicFallacyDetector()
        with patch.dict("sys.modules", {"spacy": None}):
            detector._available = None  # Reset cache
            # May or may not be available depending on environment
            result = detector.is_available()
            assert isinstance(result, bool)

    def test_mine_arguments_fallback(self):
        """Without spaCy, mine_arguments returns text as single claim."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            SymbolicFallacyDetector,
        )

        detector = SymbolicFallacyDetector()
        detector._available = False
        result = detector.mine_arguments("Test text here")
        assert result["claims"] == ["Test text here"]
        assert result["premises"] == []

    def test_detect_empty_when_unavailable(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            SymbolicFallacyDetector,
        )

        detector = SymbolicFallacyDetector()
        detector._available = False
        assert detector.detect("test") == []


class TestNLIDetector:
    """Test the NLI zero-shot fallacy detector."""

    def test_default_model_name(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector()
        assert "mDeBERTa" in detector._model_name or "xnli" in detector._model_name

    def test_custom_model_name(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector(model_name="custom/model")
        assert detector._model_name == "custom/model"

    def test_custom_threshold(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector(threshold=0.8)
        assert detector.threshold == 0.8

    def test_detect_empty_when_unavailable(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector()
        detector._available = False
        assert detector.detect("test") == []

    def test_detect_with_mock_pipeline(self):
        """Test NLI detection with mocked transformers pipeline."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector(threshold=0.5)
        detector._available = True

        mock_result = {
            "labels": ["Attaque personnelle (Ad Hominem)", "Pente glissante"],
            "scores": [0.85, 0.3],
        }
        mock_classifier = MagicMock(return_value=mock_result)
        detector._classifier = mock_classifier

        results = detector.detect("Tu es un idiot, ton argument est faux")
        assert len(results) == 1  # Only Ad Hominem passes threshold
        assert results[0].fallacy_type == "Attaque personnelle (Ad Hominem)"
        assert results[0].confidence == 0.85
        assert results[0].source == "nli"


class TestLLMDetector:
    """Test the LLM zero-shot fallacy detector."""

    def test_unavailable_without_service_discovery(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        detector = LLMFallacyDetector(service_discovery=None)
        assert detector.is_available() is False

    def test_detect_empty_when_unavailable(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        detector = LLMFallacyDetector()
        assert detector.detect("test") == []


class TestFrenchFallacyAdapter:
    """Test the main adapter class."""

    def test_creation_defaults(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False, enable_nli=False, enable_llm=False
        )
        assert not adapter.is_available()

    def test_get_available_tiers_none(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False, enable_nli=False, enable_llm=False
        )
        assert adapter.get_available_tiers() == []

    def test_detect_no_tiers(self):
        """Detect with no available tiers returns empty result."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False, enable_nli=False, enable_llm=False
        )
        result = adapter.detect("test text")
        assert result["total_fallacies"] == 0
        assert result["tiers_used"] == ["none"]

    def test_detect_with_mocked_symbolic(self):
        """Detect with symbolic tier returns correct structure."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
            FallacyDetection,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True, enable_nli=False, enable_llm=False
        )
        # Mock the symbolic detector
        mock_detections = [FallacyDetection("Ad Hominem", 1.0, "symbolic", "tu es nul")]
        adapter._symbolic.detect = MagicMock(return_value=mock_detections)
        adapter._symbolic._available = True
        adapter._symbolic.mine_arguments = MagicMock(
            return_value={"claims": ["test"], "premises": []}
        )

        result = adapter.detect("tu es nul donc ton argument est faux")
        assert result["total_fallacies"] == 1
        assert "Ad Hominem" in result["detected_fallacies"]
        assert "symbolic" in result["tiers_used"]

    def test_ensemble_symbolic_overrides_nli(self):
        """Symbolic detection (confidence=1.0) overrides NLI on same type."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
            FallacyDetection,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True, enable_nli=True, enable_llm=False
        )
        symbolic_result = [FallacyDetection("Ad Hominem", 1.0, "symbolic", "tu es nul")]
        nli_result = [FallacyDetection("Ad Hominem", 0.7, "nli")]

        adapter._symbolic.detect = MagicMock(return_value=symbolic_result)
        adapter._symbolic._available = True
        adapter._symbolic.mine_arguments = MagicMock(
            return_value={"claims": ["test"], "premises": []}
        )
        adapter._nli.detect = MagicMock(return_value=nli_result)
        adapter._nli._available = True

        result = adapter.detect("tu es nul")
        assert result["total_fallacies"] == 1
        fallacy = result["detected_fallacies"]["Ad Hominem"]
        assert fallacy["confidence"] == 1.0
        assert "symbolic" in fallacy["source"]

    def test_explanation_generated(self):
        """Detect generates a textual explanation."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
            FallacyDetection,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True, enable_nli=False, enable_llm=False
        )
        adapter._symbolic.detect = MagicMock(
            return_value=[FallacyDetection("Ad Hominem", 1.0, "symbolic")]
        )
        adapter._symbolic._available = True
        adapter._symbolic.mine_arguments = MagicMock(
            return_value={"claims": ["x"], "premises": []}
        )

        result = adapter.detect("test")
        assert "sophisme" in result["explanation"].lower()

    def test_no_fallacies_explanation(self):
        """No fallacies generates appropriate message."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True, enable_nli=False, enable_llm=False
        )
        adapter._symbolic.detect = MagicMock(return_value=[])
        adapter._symbolic._available = True
        adapter._symbolic.mine_arguments = MagicMock(
            return_value={"claims": ["x"], "premises": []}
        )

        result = adapter.detect("Ceci est un argument valide.")
        assert result["total_fallacies"] == 0
        assert "aucun" in result["explanation"].lower()


class TestCapabilityRegistration:
    """Test CapabilityRegistry integration."""

    def test_register_french_fallacy_adapter(self):
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        registry = CapabilityRegistry()
        registry.register_service(
            "french_fallacy_detector",
            FrenchFallacyAdapter,
            capabilities=[
                "fallacy_detection",
                "neural_fallacy_detection",
                "symbolic_fallacy_detection",
            ],
        )
        services = registry.find_services_for_capability("fallacy_detection")
        assert len(services) == 1
        assert services[0].name == "french_fallacy_detector"
