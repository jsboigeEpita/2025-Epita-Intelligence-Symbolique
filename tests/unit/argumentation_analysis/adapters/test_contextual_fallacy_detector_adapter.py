"""
Tests for adapters/contextual_fallacy_detector_adapter.py.

Covers the ContextualFallacyDetectorAdapter that wraps ContextualFallacyDetector.
"""

import pytest
from unittest.mock import MagicMock

from argumentation_analysis.adapters.contextual_fallacy_detector_adapter import (
    ContextualFallacyDetectorAdapter,
)
from argumentation_analysis.core.interfaces.fallacy_detector import (
    AbstractFallacyDetector,
)


class TestContextualFallacyDetectorAdapter:
    """Tests for the adapter class."""

    def _make_adapter(self, detect_return=None):
        mock_detector = MagicMock()
        if detect_return is not None:
            mock_detector.detect.return_value = detect_return
        else:
            mock_detector.detect.return_value = {"fallacies": [], "count": 0}
        return ContextualFallacyDetectorAdapter(mock_detector), mock_detector

    def test_is_abstract_fallacy_detector(self):
        """Adapter implements AbstractFallacyDetector."""
        adapter, _ = self._make_adapter()
        assert isinstance(adapter, AbstractFallacyDetector)

    def test_detect_delegates_to_wrapped(self):
        """detect() calls the underlying detector."""
        expected = {"fallacies": [{"type": "ad_hominem"}], "count": 1}
        adapter, mock = self._make_adapter(detect_return=expected)
        result = adapter.detect("Some argumentative text")
        mock.detect.assert_called_once_with("Some argumentative text")
        assert result == expected

    def test_detect_with_empty_text(self):
        """Works with empty text input."""
        adapter, mock = self._make_adapter(detect_return={"fallacies": []})
        result = adapter.detect("")
        mock.detect.assert_called_once_with("")
        assert result == {"fallacies": []}

    def test_detect_passes_through_complex_result(self):
        """Passes through complex nested results."""
        complex_result = {
            "fallacies": [
                {"type": "straw_man", "confidence": 0.85, "span": [10, 50]},
                {"type": "appeal_to_emotion", "confidence": 0.72, "span": [60, 120]},
            ],
            "count": 2,
            "context": {"genre": "political", "severity": "high"},
        }
        adapter, _ = self._make_adapter(detect_return=complex_result)
        result = adapter.detect("Some political speech")
        assert result == complex_result

    def test_detect_propagates_exception(self):
        """Exceptions from underlying detector propagate."""
        adapter, mock = self._make_adapter()
        mock.detect.side_effect = RuntimeError("Model not loaded")
        with pytest.raises(RuntimeError, match="Model not loaded"):
            adapter.detect("test")

    def test_stores_detector_reference(self):
        """Adapter stores reference to the wrapped detector."""
        adapter, mock = self._make_adapter()
        assert adapter._detector is mock

    def test_detect_long_text(self):
        """Works with long text input."""
        long_text = "A" * 10000
        adapter, mock = self._make_adapter(detect_return={"fallacies": []})
        adapter.detect(long_text)
        mock.detect.assert_called_once_with(long_text)
