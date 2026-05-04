"""Tests for NLI hierarchical 2-stage taxonomy classification (#307).

All NLI model calls are mocked -- no model download required.
"""

import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.adapters.french_fallacy_adapter import (
    FallacyDetection,
    FrenchFallacyAdapter,
    NLIFallacyDetector,
    _load_taxonomy_hierarchy,
    _TAXONOMY_HIERARCHY,
    _TAXONOMY_PK_TO_NODE,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_hierarchy_cache():
    """Ensure hierarchy is freshly loaded for each test."""
    _TAXONOMY_HIERARCHY.clear()
    _TAXONOMY_PK_TO_NODE.clear()
    yield
    _TAXONOMY_HIERARCHY.clear()
    _TAXONOMY_PK_TO_NODE.clear()


@pytest.fixture()
def hierarchy():
    """Load and return the taxonomy hierarchy from taxonomy_full.csv."""
    return _load_taxonomy_hierarchy()


def _make_nli_detector(threshold: float = 0.5) -> NLIFallacyDetector:
    """Create an NLIFallacyDetector with availability forced on."""
    det = NLIFallacyDetector(threshold=threshold)
    det._available = True
    return det


def _mock_classifier_result(labels, scores):
    """Build the dict returned by a HuggingFace zero-shot pipeline."""
    return {"labels": labels, "scores": scores}


# ---------------------------------------------------------------------------
# 1. Taxonomy hierarchy loading
# ---------------------------------------------------------------------------


class TestLoadTaxonomyHierarchy:
    """Test _load_taxonomy_hierarchy() builds the correct tree."""

    def test_root_node(self, hierarchy):
        assert hierarchy, "Hierarchy should not be empty"
        assert hierarchy["label"] == "Argument fallacieux"
        assert hierarchy["depth"] == 0
        assert hierarchy["pk"] == 0

    def test_seven_families(self, hierarchy):
        families = hierarchy["children"]
        assert len(families) == 7
        family_names = {f["label"] for f in families}
        expected = {
            "Insuffisance",
            "Influence",
            "Erreur math\u00e9matique",
            "Erreur de raisonnement",
            "Abus de langage",
            "Tricherie",
            "Obstruction",
        }
        assert family_names == expected

    def test_families_have_children(self, hierarchy):
        for family in hierarchy["children"]:
            assert (
                len(family["children"]) > 0
            ), f"Family '{family['label']}' should have children"

    def test_depth_values(self, hierarchy):
        for family in hierarchy["children"]:
            assert family["depth"] == 1
            for sub in family["children"]:
                assert sub["depth"] == 2

    def test_pk_to_node_populated(self, hierarchy):
        assert len(_TAXONOMY_PK_TO_NODE) > 100, "PK lookup should have many entries"
        # Spot check: PK 1 = Insuffisance
        assert _TAXONOMY_PK_TO_NODE[1]["label"] == "Insuffisance"

    def test_caching(self, hierarchy):
        """Second call returns the same cached object."""
        h2 = _load_taxonomy_hierarchy()
        assert h2 is hierarchy

    def test_missing_csv_returns_empty(self, tmp_path):
        """If CSV is missing, returns empty dict without crashing."""
        with patch(
            "argumentation_analysis.adapters.french_fallacy_adapter._TAXONOMY_FULL_CSV",
            tmp_path / "nonexistent.csv",
        ):
            _TAXONOMY_HIERARCHY.clear()
            _TAXONOMY_PK_TO_NODE.clear()
            result = _load_taxonomy_hierarchy()
            assert result == {}


# ---------------------------------------------------------------------------
# 2. Stage 1: classify against families
# ---------------------------------------------------------------------------


class TestHierarchicalStage1:
    """Stage 1 returns top-scoring families."""

    def test_stage1_returns_family(self, hierarchy):
        det = _make_nli_detector(threshold=0.5)

        # Mock classifier: Insuffisance scores high, no children drill-down
        # because we set threshold high for stage 2
        def fake_classify(text, candidate_labels, **kw):
            if len(candidate_labels) == 7:
                # Stage 1 call
                return _mock_classifier_result(
                    [
                        "Insuffisance",
                        "Influence",
                        "Tricherie",
                        "Obstruction",
                        "Abus de langage",
                        "Erreur math\u00e9matique",
                        "Erreur de raisonnement",
                    ],
                    [0.8, 0.2, 0.1, 0.05, 0.04, 0.03, 0.02],
                )
            # Stage 2 call -- return low scores so we stay at family level
            return _mock_classifier_result(
                candidate_labels, [0.1] * len(candidate_labels)
            )

        det._classifier = MagicMock(side_effect=fake_classify)

        results = det.detect("Texte test", hierarchical=True)
        assert len(results) == 1
        # Stage 2 had low confidence, so we get family-level detection
        assert results[0].fallacy_type == "Insuffisance"
        assert results[0].source == "nli_hierarchical"

    def test_stage1_filters_low_confidence(self, hierarchy):
        det = _make_nli_detector(threshold=0.5)

        def fake_classify(text, candidate_labels, **kw):
            # All families below HIERARCHICAL_STAGE1_THRESHOLD (0.3)
            return _mock_classifier_result(
                candidate_labels, [0.1] * len(candidate_labels)
            )

        det._classifier = MagicMock(side_effect=fake_classify)

        results = det.detect("Texte test", hierarchical=True)
        assert results == []


# ---------------------------------------------------------------------------
# 3. Stage 2: drill down into children
# ---------------------------------------------------------------------------


class TestHierarchicalStage2:
    """Stage 2 drills into sub-families of top-scoring family."""

    def test_stage2_returns_specific_child(self, hierarchy):
        det = _make_nli_detector(threshold=0.3)

        call_count = {"n": 0}

        def fake_classify(text, candidate_labels, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Stage 1: Obstruction wins
                ordered = sorted(
                    candidate_labels, key=lambda x: x == "Obstruction", reverse=True
                )
                scores = [0.7] + [0.05] * (len(ordered) - 1)
                return _mock_classifier_result(ordered, scores)
            else:
                # Stage 2: "Ad hominem" is the best child
                # (Ad hominem is under Obstruction in the full taxonomy)
                best = candidate_labels[0]
                scores = [0.9] + [0.1] * (len(candidate_labels) - 1)
                return _mock_classifier_result(candidate_labels, scores)

        det._classifier = MagicMock(side_effect=fake_classify)

        results = det.detect("Tu es incompetent donc tu as tort", hierarchical=True)
        assert len(results) == 1
        r = results[0]
        assert r.source == "nli_hierarchical"
        assert r.taxonomy_pk is not None
        # Combined confidence = 0.7 * 0.9 = 0.63
        assert abs(r.confidence - 0.63) < 0.01
        # Description should mention stage-2 drill-down
        assert "stage-2" in r.description.lower() or "s1=" in r.description

    def test_stage2_low_confidence_stays_at_family(self, hierarchy):
        det = _make_nli_detector(threshold=0.5)

        call_count = {"n": 0}

        def fake_classify(text, candidate_labels, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Stage 1: Influence scores high
                ordered = sorted(
                    candidate_labels, key=lambda x: x == "Influence", reverse=True
                )
                scores = [0.6] + [0.05] * (len(ordered) - 1)
                return _mock_classifier_result(ordered, scores)
            else:
                # Stage 2: all scores below threshold (0.5)
                scores = [0.2] * len(candidate_labels)
                return _mock_classifier_result(candidate_labels, scores)

        det._classifier = MagicMock(side_effect=fake_classify)

        results = det.detect("Texte test", hierarchical=True)
        assert len(results) == 1
        assert results[0].fallacy_type == "Influence"
        assert "stage-1 only" in results[0].description.lower()


# ---------------------------------------------------------------------------
# 4. Fallback to flat when hierarchy not available
# ---------------------------------------------------------------------------


class TestHierarchicalFallback:
    """When hierarchy is unavailable, fall back to flat 28-label mode."""

    def test_fallback_to_flat_when_csv_missing(self):
        det = _make_nli_detector(threshold=0.3)

        flat_called = {"yes": False}

        def fake_classify(text, candidate_labels, **kw):
            flat_called["yes"] = True
            return _mock_classifier_result(
                candidate_labels, [0.1] * len(candidate_labels)
            )

        det._classifier = MagicMock(side_effect=fake_classify)

        with patch(
            "argumentation_analysis.adapters.french_fallacy_adapter._TAXONOMY_FULL_CSV",
            __import__("pathlib").Path("/nonexistent/taxonomy_full.csv"),
        ):
            _TAXONOMY_HIERARCHY.clear()
            _TAXONOMY_PK_TO_NODE.clear()
            results = det.detect("Texte test", hierarchical=True)

        # Should have called the classifier (flat fallback)
        assert flat_called["yes"]


# ---------------------------------------------------------------------------
# 5. Threshold filtering
# ---------------------------------------------------------------------------


class TestThresholdFiltering:
    """Verify threshold behaviour in hierarchical mode."""

    def test_stage1_threshold_configurable(self, hierarchy):
        det = _make_nli_detector(threshold=0.5)
        # Override stage-1 threshold
        det.HIERARCHICAL_STAGE1_THRESHOLD = 0.9

        def fake_classify(text, candidate_labels, **kw):
            # Highest family score is 0.85, below 0.9
            return _mock_classifier_result(
                candidate_labels, [0.85] + [0.05] * (len(candidate_labels) - 1)
            )

        det._classifier = MagicMock(side_effect=fake_classify)

        results = det.detect("Texte test", hierarchical=True)
        assert results == [], "Score 0.85 should be below threshold 0.9"

    def test_multiple_families_above_threshold(self, hierarchy):
        det = _make_nli_detector(threshold=0.3)

        call_count = {"n": 0}

        def fake_classify(text, candidate_labels, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Two families above stage-1 threshold (0.3)
                labels = list(candidate_labels)
                scores = [0.0] * len(labels)
                for i, l in enumerate(labels):
                    if l == "Insuffisance":
                        scores[i] = 0.6
                    elif l == "Tricherie":
                        scores[i] = 0.4
                    else:
                        scores[i] = 0.05
                # Sort by score descending (HF pipeline convention)
                paired = sorted(zip(labels, scores), key=lambda x: -x[1])
                labels = [p[0] for p in paired]
                scores = [p[1] for p in paired]
                return _mock_classifier_result(labels, scores)
            else:
                # Stage 2: return first child with high score
                return _mock_classifier_result(
                    candidate_labels,
                    [0.7] + [0.1] * (len(candidate_labels) - 1),
                )

        det._classifier = MagicMock(side_effect=fake_classify)

        results = det.detect("Texte test", hierarchical=True)
        # Should have 2 detections (one per family above threshold)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# 6. FrenchFallacyAdapter integration
# ---------------------------------------------------------------------------


class TestAdapterHierarchicalIntegration:
    """FrenchFallacyAdapter passes hierarchical flag to NLI tier."""

    def test_adapter_default_is_flat(self):
        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=True,
            enable_llm=False,
        )
        assert adapter._nli_hierarchical is False

    def test_adapter_hierarchical_flag(self):
        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=True,
            enable_llm=False,
            nli_hierarchical=True,
        )
        assert adapter._nli_hierarchical is True

    def test_adapter_detect_calls_nli_with_hierarchical(self):
        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=True,
            enable_llm=False,
            nli_hierarchical=True,
        )
        # Mock the NLI detector
        mock_nli = MagicMock()
        mock_nli.is_available.return_value = True
        mock_nli.detect.return_value = [
            FallacyDetection(
                fallacy_type="Insuffisance",
                confidence=0.7,
                source="nli_hierarchical",
            )
        ]
        adapter._nli = mock_nli

        result = adapter.detect("test text")
        mock_nli.detect.assert_called_once_with("test text", hierarchical=True)
        assert "nli_hierarchical" in result["tiers_used"]

    def test_adapter_detect_calls_nli_flat_by_default(self):
        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_nli=True,
            enable_llm=False,
        )
        mock_nli = MagicMock()
        mock_nli.is_available.return_value = True
        mock_nli.detect.return_value = []
        adapter._nli = mock_nli

        adapter.detect("test text")
        mock_nli.detect.assert_called_once_with("test text", hierarchical=False)
