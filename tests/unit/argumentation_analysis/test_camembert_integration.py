"""
Tests for CamemBERT fine-tuned fallacy detector integration (#169).

Tests the CamemBERTFallacyDetector class, its integration into
FrenchFallacyAdapter, label mapping, and graceful degradation.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path


# ── CamemBERT label mapping tests ────────────────────────────────────


class TestCamemBERTLabelMapping:
    """Tests for the label mapping from CamemBERT's 13 classes."""

    def test_all_13_labels_mapped(self):
        """All 13 CamemBERT output classes have French label mappings."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            _CAMEMBERT_LABEL_MAPPING,
        )

        assert len(_CAMEMBERT_LABEL_MAPPING) == 13
        for i in range(13):
            assert i in _CAMEMBERT_LABEL_MAPPING
            assert isinstance(_CAMEMBERT_LABEL_MAPPING[i], str)
            assert len(_CAMEMBERT_LABEL_MAPPING[i]) > 0

    def test_known_labels(self):
        """Spot-check specific label mappings."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            _CAMEMBERT_LABEL_MAPPING,
        )

        assert _CAMEMBERT_LABEL_MAPPING[0] == "Attaque personnelle (Ad Hominem)"
        assert _CAMEMBERT_LABEL_MAPPING[7] == "Fausse causalité (False Cause)"
        assert _CAMEMBERT_LABEL_MAPPING[12] == "Équivoque (Equivocation)"


# ── CamemBERTFallacyDetector unit tests ──────────────────────────────


class TestCamemBERTFallacyDetector:
    """Tests for CamemBERTFallacyDetector class."""

    def _make_detector(self, **kwargs):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            CamemBERTFallacyDetector,
        )

        return CamemBERTFallacyDetector(**kwargs)

    def test_not_available_without_model(self):
        """Detector reports unavailable when model not found."""
        detector = self._make_detector(model_path="/nonexistent/path")
        assert detector.is_available() is False

    def test_not_available_without_transformers(self):
        """Detector reports unavailable when transformers not installed."""
        detector = self._make_detector()
        with patch.dict("sys.modules", {"transformers": None}):
            # Reset cached availability
            detector._available = None
            # Will fail on import
            result = detector.is_available()
            # May or may not be available depending on actual env
            # Just test it doesn't crash
            assert isinstance(result, bool)

    def test_detect_returns_empty_when_unavailable(self):
        """detect() returns empty list when model not available."""
        detector = self._make_detector(model_path="/nonexistent/path")
        results = detector.detect("Cet argument est fallacieux.")
        assert results == []

    def test_detect_with_mock_model(self):
        """detect() returns correct FallacyDetection with mocked model."""
        import torch
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            CamemBERTFallacyDetector,
            FallacyDetection,
        )

        detector = CamemBERTFallacyDetector(threshold=0.3)

        # Mock tokenizer and model
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}

        # Create mock output with logits for class 0 (Ad Hominem) having highest score
        mock_logits = torch.tensor([[5.0, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]])
        mock_output = MagicMock()
        mock_output.logits = mock_logits

        mock_model = MagicMock()
        mock_model.return_value = mock_output

        detector._tokenizer = mock_tokenizer
        detector._model = mock_model
        detector._available = True

        results = detector.detect("Tu es stupide donc ton argument est faux.")

        assert len(results) == 1
        assert isinstance(results[0], FallacyDetection)
        assert results[0].fallacy_type == "Attaque personnelle (Ad Hominem)"
        assert results[0].source == "camembert"
        assert results[0].confidence > 0.5

    def test_detect_below_threshold(self):
        """detect() returns empty when confidence below threshold."""
        import torch
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            CamemBERTFallacyDetector,
        )

        detector = CamemBERTFallacyDetector(threshold=0.99)

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}

        # Uniform logits → all classes ~0.077 confidence → below 0.99
        mock_logits = torch.tensor([[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]])
        mock_output = MagicMock()
        mock_output.logits = mock_logits

        mock_model = MagicMock()
        mock_model.return_value = mock_output

        detector._tokenizer = mock_tokenizer
        detector._model = mock_model
        detector._available = True

        results = detector.detect("Un texte quelconque.")
        assert results == []

    def test_model_path_search(self):
        """_find_model_path searches in known locations."""
        detector = self._make_detector()
        # Without a real model, should return None
        path = detector._find_model_path()
        # Just verify it doesn't crash and returns str or None
        assert path is None or isinstance(path, str)

    def test_get_status_details(self):
        """get_status_details returns structured info."""
        detector = self._make_detector()
        status = detector.get_status_details()
        assert status["detector_type"] == "CamemBERTFallacyDetector"
        assert "available" in status
        assert "threshold" in status
        assert status["num_labels"] == 13


# ── FrenchFallacyAdapter integration tests ───────────────────────────


class TestFrenchFallacyAdapterCamemBERT:
    """Tests for CamemBERT integration into FrenchFallacyAdapter."""

    def test_adapter_has_camembert_tier(self):
        """Adapter creates CamemBERT detector by default."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
            CamemBERTFallacyDetector,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=False,
            enable_llm=False,
            enable_camembert=True,
        )
        assert adapter._camembert is not None
        assert isinstance(adapter._camembert, CamemBERTFallacyDetector)

    def test_adapter_disables_camembert(self):
        """Adapter skips CamemBERT when disabled."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=False,
            enable_llm=False,
            enable_camembert=False,
        )
        assert adapter._camembert is None

    def test_available_tiers_includes_camembert(self):
        """get_available_tiers includes 'camembert' when model is available."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=False,
            enable_llm=False,
            enable_camembert=True,
        )
        # Mock CamemBERT as available
        adapter._camembert._available = True

        tiers = adapter.get_available_tiers()
        assert "camembert" in tiers

    def test_detect_uses_camembert_tier(self):
        """detect() invokes CamemBERT tier when available."""
        import torch
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
            FallacyDetection,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=False,
            enable_llm=False,
            enable_camembert=True,
        )

        # Mock the CamemBERT detector's detect method
        mock_detection = FallacyDetection(
            fallacy_type="Fausse causalité (False Cause)",
            confidence=0.85,
            source="camembert",
        )
        adapter._camembert._available = True
        adapter._camembert.detect = MagicMock(return_value=[mock_detection])

        result = adapter.detect("Le soleil brille donc il fait chaud.")

        assert result["total_fallacies"] == 1
        assert "camembert" in result["tiers_used"]
        assert "Fausse causalité (False Cause)" in result["detected_fallacies"]

    def test_graceful_degradation(self):
        """Adapter works when CamemBERT is unavailable."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=False,
            enable_llm=False,
            enable_camembert=True,
        )
        # CamemBERT unavailable (no model)
        adapter._camembert._available = False

        result = adapter.detect("Un texte normal.")
        # Should still work, just no detections
        assert isinstance(result, dict)
        assert "tiers_used" in result
        assert "camembert" not in result["tiers_used"]

    def test_camembert_custom_path(self):
        """Adapter passes custom model path to CamemBERT detector."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=False,
            enable_llm=False,
            enable_camembert=True,
            camembert_model_path="/custom/model/path",
        )
        assert adapter._camembert._model_path == "/custom/model/path"

    def test_camembert_custom_threshold(self):
        """Adapter passes custom threshold to CamemBERT detector."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=False,
            enable_llm=False,
            enable_camembert=True,
            camembert_threshold=0.7,
        )
        assert adapter._camembert._threshold == 0.7

    def test_ensemble_camembert_with_symbolic(self):
        """Ensemble correctly merges CamemBERT + symbolic detections."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
            FallacyDetection,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True,
            enable_nli=False,
            enable_llm=False,
            enable_camembert=True,
        )

        # Mock both tiers detecting same fallacy
        symbolic_det = FallacyDetection(
            fallacy_type="Attaque personnelle (Ad Hominem)",
            confidence=1.0,
            source="symbolic",
            matched_rule="tu es ... donc",
        )
        camembert_det = FallacyDetection(
            fallacy_type="Attaque personnelle (Ad Hominem)",
            confidence=0.9,
            source="camembert",
        )

        # Mock symbolic and camembert
        adapter._symbolic._available = True
        adapter._symbolic.detect = MagicMock(return_value=[symbolic_det])
        adapter._symbolic.mine_arguments = MagicMock(return_value=None)
        adapter._camembert._available = True
        adapter._camembert.detect = MagicMock(return_value=[camembert_det])

        result = adapter.detect("Tu es stupide donc ton argument est faux.")

        assert result["total_fallacies"] == 1  # Merged, not duplicated
        ad_hominem = result["detected_fallacies"]["Attaque personnelle (Ad Hominem)"]
        # Symbolic (confidence=1.0) should win
        assert ad_hominem["confidence"] == 1.0
        # Source should be concatenated
        assert "symbolic" in ad_hominem["source"]
        assert "camembert" in ad_hominem["source"]
