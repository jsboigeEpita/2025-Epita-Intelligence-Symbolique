"""CI smoke tests for soutenance demo scripts.

Runs the demo pipeline with mocked LLM responses to catch regressions
in import paths, function signatures, and metric extraction logic.
No API calls are made.

Usage:
    pytest tests/soutenance/ -v -m soutenance_demo
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

pytestmark = pytest.mark.soutenance_demo

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from examples.soutenance._shared import (
    CORPORA,
    check_tolerance,
    extract_metrics,
    get_outputs_dir,
    print_summary,
)


def _make_mock_state():
    """Create a mock UnifiedAnalysisState with realistic data."""
    state = MagicMock()
    state.arguments = [MagicMock() for _ in range(20)]
    state.identified_fallacies = [MagicMock() for _ in range(13)]
    state.jtms_beliefs = {"b1": MagicMock(), "b2": MagicMock(),
                          "b3": MagicMock(), "b4": MagicMock()}
    state.counter_arguments = [MagicMock() for _ in range(8)]
    state.dung_frameworks = {"f1": MagicMock()}
    state.aspic_analyses = {"a1": MagicMock()}
    state.fol_formulas = []
    state.pl_formulas = {"p1": MagicMock()}
    state.modal_analyses = {}
    state.belief_revisions = {"r1": MagicMock()}
    return state


class TestSharedModule:
    """Test _shared.py utilities."""

    def test_corpora_has_three_entries(self):
        assert set(CORPORA.keys()) == {"A", "B", "C"}

    def test_each_corpus_has_required_fields(self):
        for cid, info in CORPORA.items():
            assert "src_idx" in info, f"{cid} missing src_idx"
            assert "label" in info, f"{cid} missing label"
            assert "desc" in info, f"{cid} missing desc"
            assert "tolerance" in info, f"{cid} missing tolerance"

    def test_tolerance_bands_have_valid_ranges(self):
        for cid, info in CORPORA.items():
            for key, band in info["tolerance"].items():
                if "delta" in band:
                    assert band["delta"] >= 0, f"{cid}.{key}: delta must be >= 0"
                    assert band["target"] > 0, f"{cid}.{key}: target must be > 0"
                elif "min" in band:
                    assert band["min"] > 0, f"{cid}.{key}: min must be > 0"


class TestMetricExtraction:
    """Test extract_metrics with mock state."""

    def test_extracts_all_metrics(self):
        state = _make_mock_state()
        metrics = extract_metrics(state, "A")
        assert metrics["arguments_found"] == 20
        assert metrics["fallacies_found"] == 13
        assert metrics["unique_formal_categories"] == 4  # dung, aspic, pl, belief_rev
        assert metrics["jtms_beliefs"] == 4
        assert metrics["counter_arguments"] == 8

    def test_handles_none_state(self):
        metrics = extract_metrics(None, "A")
        assert metrics["arguments_found"] == 0
        assert metrics["fallacies_found"] == 0
        assert metrics["corpus_id"] == "A"

    def test_handles_empty_attrs(self):
        state = MagicMock()
        state.arguments = None
        state.identified_fallacies = None
        state.jtms_beliefs = None
        state.counter_arguments = None
        state.dung_frameworks = None
        metrics = extract_metrics(state, "B")
        assert metrics["arguments_found"] == 0
        assert metrics["corpus_label"] == "corpus_dense_B"

    def test_corpus_id_in_metrics(self):
        for cid in ("A", "B", "C"):
            metrics = extract_metrics(None, cid)
            assert metrics["corpus_id"] == cid
            assert metrics["corpus_label"] == CORPORA[cid]["label"]


class TestToleranceCheck:
    """Test check_tolerance logic."""

    def test_corpus_a_within_band(self):
        metrics = {
            "arguments_found": 20,
            "fallacies_found": 13,
            "unique_formal_categories": 5,
        }
        warnings = check_tolerance(metrics, "A")
        assert warnings == []

    def test_corpus_a_below_band(self):
        metrics = {
            "arguments_found": 15,
            "fallacies_found": 8,
            "unique_formal_categories": 5,
        }
        warnings = check_tolerance(metrics, "A")
        assert len(warnings) == 2  # args and fallacies out of band

    def test_corpus_b_tolerance(self):
        metrics = {
            "arguments_found": 17,
            "fallacies_found": 17,
            "unique_formal_categories": 5,
        }
        warnings = check_tolerance(metrics, "B")
        assert warnings == []

    def test_corpus_c_tolerance(self):
        metrics = {
            "arguments_found": 10,
            "fallacies_found": 14,
            "unique_formal_categories": 3,
        }
        warnings = check_tolerance(metrics, "C")
        assert warnings == []

    def test_formal_categories_below_min(self):
        metrics = {
            "arguments_found": 20,
            "fallacies_found": 13,
            "unique_formal_categories": 2,  # min is 3
        }
        warnings = check_tolerance(metrics, "A")
        assert any("formal_categories" in w for w in warnings)


class TestOutputDirectory:
    """Test get_outputs_dir creates correct paths."""

    def test_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "examples.soutenance._shared._PROJECT_ROOT", tmp_path
        )
        out = get_outputs_dir("A")
        assert out.exists()
        assert "corpus_dense_A" in str(out)

    def test_all_corpora_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "examples.soutenance._shared._PROJECT_ROOT", tmp_path
        )
        for cid in ("A", "B", "C"):
            out = get_outputs_dir(cid)
            assert out.exists()
            assert CORPORA[cid]["label"] in str(out)


class TestImportPaths:
    """Verify all demo scripts import correctly."""

    def test_import_shared(self):
        from examples.soutenance._shared import CORPORA
        assert isinstance(CORPORA, dict)

    def test_import_corpus_a(self):
        from examples.soutenance.run_corpus_a import CORPUS_ID, run_demo
        assert CORPUS_ID == "A"
        assert callable(run_demo)

    def test_import_corpus_b(self):
        from examples.soutenance.run_corpus_b import CORPUS_ID, run_demo
        assert CORPUS_ID == "B"
        assert callable(run_demo)

    def test_import_corpus_c(self):
        from examples.soutenance.run_corpus_c import CORPUS_ID, run_demo
        assert CORPUS_ID == "C"
        assert callable(run_demo)
