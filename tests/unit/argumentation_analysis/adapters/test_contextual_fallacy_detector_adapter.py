"""
Tests for adapters/contextual_fallacy_detector_adapter.py.

Covers the ContextualFallacyDetectorAdapter that wraps ContextualFallacyDetector.

#2149 : la suite d'origine ne mockait que `detect()` — un `MagicMock` fabrique
n'importe quel attribut, donc elle validait un adaptateur qui appelait en
réalité une méthode absente du détecteur encapsulé. Le test sur le détecteur
**réel** (`test_detect_with_real_detector`) est celui qui tient le contrat.
"""

import pytest
from unittest.mock import MagicMock

from argumentation_analysis.adapters.contextual_fallacy_detector_adapter import (
    DEFAULT_CONTEXT_DESCRIPTION,
    ContextualFallacyDetectorAdapter,
)
from argumentation_analysis.agents.tools.analysis.new import ContextualFallacyDetector
from argumentation_analysis.core.interfaces.fallacy_detector import (
    AbstractFallacyDetector,
)


class TestContextualFallacyDetectorAdapter:
    """Tests for the adapter class."""

    def _make_adapter(self, detect_return=None):
        mock_detector = MagicMock()
        if detect_return is not None:
            mock_detector.detect_contextual_fallacies.return_value = detect_return
        else:
            mock_detector.detect_contextual_fallacies.return_value = {
                "detected_fallacies": []
            }
        return ContextualFallacyDetectorAdapter(mock_detector), mock_detector

    def test_is_abstract_fallacy_detector(self):
        """Adapter implements AbstractFallacyDetector."""
        adapter, _ = self._make_adapter()
        assert isinstance(adapter, AbstractFallacyDetector)

    def test_detect_delegates_to_wrapped(self):
        """detect() calls the underlying detector's real method."""
        expected = {"detected_fallacies": [{"fallacy_type": "Ad hominem"}]}
        adapter, mock = self._make_adapter(detect_return=expected)
        result = adapter.detect("Some argumentative text")
        mock.detect_contextual_fallacies.assert_called_once_with(
            "Some argumentative text",
            context_description=DEFAULT_CONTEXT_DESCRIPTION,
        )
        assert result == expected

    def test_detect_with_empty_text(self):
        """Works with empty text input."""
        adapter, mock = self._make_adapter(detect_return={"detected_fallacies": []})
        result = adapter.detect("")
        mock.detect_contextual_fallacies.assert_called_once_with(
            "", context_description=DEFAULT_CONTEXT_DESCRIPTION
        )
        assert result == {"detected_fallacies": []}

    def test_detect_passes_through_complex_result(self):
        """Passes through complex nested results."""
        complex_result = {
            "argument": "Some political speech",
            "detected_fallacies": [
                {"fallacy_type": "Homme de paille", "severity": 0.85},
                {"fallacy_type": "Appel à l'émotion", "severity": 0.72},
            ],
            "contextual_factors": {"domain": "politique"},
        }
        adapter, _ = self._make_adapter(detect_return=complex_result)
        result = adapter.detect("Some political speech")
        assert result == complex_result

    def test_detect_propagates_exception(self):
        """Exceptions from underlying detector propagate."""
        adapter, mock = self._make_adapter()
        mock.detect_contextual_fallacies.side_effect = RuntimeError("Model not loaded")
        with pytest.raises(RuntimeError, match="Model not loaded"):
            adapter.detect("test")

    def test_stores_detector_reference(self):
        """Adapter stores reference to the wrapped detector."""
        adapter, mock = self._make_adapter()
        assert adapter._detector is mock

    def test_detect_long_text(self):
        """Works with long text input."""
        long_text = "A" * 10000
        adapter, mock = self._make_adapter(detect_return={"detected_fallacies": []})
        adapter.detect(long_text)
        mock.detect_contextual_fallacies.assert_called_once_with(
            long_text, context_description=DEFAULT_CONTEXT_DESCRIPTION
        )

    def test_detect_with_real_detector(self):
        """#2149 : l'adaptateur doit fonctionner sur le détecteur RÉEL encapsulé.

        Avant le correctif, `detect()` appelait `self._detector.detect(text)` —
        méthode que `ContextualFallacyDetector` n'expose pas (il expose
        `detect_contextual_fallacies`). Les tests à `MagicMock` ne pouvaient pas
        le voir : un mock fabrique l'attribut manquant.
        """
        adapter = ContextualFallacyDetectorAdapter(ContextualFallacyDetector())
        result = adapter.detect(
            "Les experts sont unanimes : ce produit est sûr et efficace."
        )
        assert isinstance(result, dict)
        assert "detected_fallacies" in result
