"""Tests for run_capstone_c1._extract_phase_metrics — verify FOL and Dung counters.

Grounded from issue #941:
- FOL state uses "consistent" (not "satisfiable" which is PL-only)
- Dung state shape is {df_id: {name, arguments, attacks, extensions: {sem: [members]}}}
"""
import pytest


# Import the function under test
from scripts.run_capstone_c1 import _extract_phase_metrics


class TestExtractPhaseMetricsFOL:
    """Verify FOL counter reads 'consistent' from state entries."""

    def test_fol_list_consistent_true(self):
        """FOL entries with consistent=True should count as verified."""
        snapshot = {
            "fol_analysis_results": [
                {"formulas": ["P(x)"], "consistent": True},
                {"formulas": ["Q(x)", "R(x)"], "consistent": True},
            ]
        }
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["fol_formulas"] == 3
        assert metrics["fol_verified"] == 3

    def test_fol_list_consistent_false_still_counted(self):
        """FOL entries with consistent=False should still count formulas."""
        snapshot = {
            "fol_analysis_results": [
                {"formulas": ["P(x)"], "consistent": False},
            ]
        }
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["fol_formulas"] == 1
        # consistent is not None → counted as verified (the formula was checked)
        assert metrics["fol_verified"] == 1

    def test_fol_list_satisfiable_key_ignored(self):
        """FOL entries using old 'satisfiable' key should NOT be counted as verified.
        This verifies we don't regress to the old bug."""
        snapshot = {
            "fol_analysis_results": [
                {"formulas": ["P(x)"], "satisfiable": True},
            ]
        }
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["fol_formulas"] == 1
        # No "consistent" key → consistent is None → not counted
        assert metrics["fol_verified"] == 0

    def test_fol_dict_consistent(self):
        """Single FOL dict result uses 'consistent'."""
        snapshot = {
            "fol_analysis_results": {
                "formulas": ["P(x)", "Q(x)"],
                "consistent": True,
            }
        }
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["fol_formulas"] == 2
        assert metrics["fol_verified"] == 2

    def test_fol_empty(self):
        """Empty FOL results should yield 0."""
        snapshot = {"fol_analysis_results": []}
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["fol_formulas"] == 0
        assert metrics["fol_verified"] == 0


class TestExtractPhaseMetricsDung:
    """Verify Dung counter reads extensions from framework entries."""

    def test_dung_single_framework_with_extensions(self):
        """Single framework with extensions should count correctly."""
        snapshot = {
            "dung_frameworks": {
                "dung_001": {
                    "name": "Test Framework",
                    "arguments": ["a1", "a2", "a3"],
                    "attacks": [["a2", "a1"]],
                    "extensions": {
                        "grounded": ["a1", "a3"],
                        "preferred": [["a1", "a3"], ["a2"]],
                    },
                },
            }
        }
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["dung_framework_count"] == 1
        # grounded: 2 members, preferred: 2 lists (counted as 2)
        assert metrics["dung_total_extensions"] == 4
        assert "dung_001" in metrics["dung_extensions"]

    def test_dung_multiple_frameworks(self):
        """Multiple frameworks should aggregate correctly."""
        snapshot = {
            "dung_frameworks": {
                "dung_001": {
                    "name": "FW1",
                    "arguments": ["a1"],
                    "attacks": [],
                    "extensions": {"grounded": ["a1"]},
                },
                "dung_002": {
                    "name": "FW2",
                    "arguments": ["b1", "b2"],
                    "attacks": [["b2", "b1"]],
                    "extensions": {
                        "grounded": ["b1"],
                        "preferred": [["b1"], ["b2"]],
                    },
                },
            }
        }
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["dung_framework_count"] == 2
        # dung_001: 1, dung_002: 3
        assert metrics["dung_total_extensions"] == 4

    def test_dung_empty_extensions(self):
        """Framework with empty extensions dict should yield 0."""
        snapshot = {
            "dung_frameworks": {
                "dung_001": {
                    "name": "Empty",
                    "arguments": ["a1"],
                    "attacks": [],
                    "extensions": {},
                },
            }
        }
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["dung_framework_count"] == 1
        assert metrics["dung_total_extensions"] == 0
        # No entry in dung_extensions detail (0 extensions)
        assert metrics["dung_extensions"] == {}

    def test_dung_no_extensions_key(self):
        """Framework without 'extensions' key should not crash."""
        snapshot = {
            "dung_frameworks": {
                "dung_001": {
                    "name": "No Extensions",
                    "arguments": ["a1"],
                    "attacks": [],
                },
            }
        }
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["dung_framework_count"] == 1
        assert metrics["dung_total_extensions"] == 0

    def test_dung_missing_field(self):
        """No dung_frameworks at all should yield 0."""
        snapshot = {}
        metrics = _extract_phase_metrics(snapshot)
        assert metrics.get("dung_framework_count", 0) == 0
        assert metrics.get("dung_total_extensions", 0) == 0


class TestExtractPhaseMetricsPL:
    """Verify PL counter still works (unchanged by FOL fix)."""

    def test_pl_satisfiable(self):
        """PL uses 'satisfiable' — should be unaffected."""
        snapshot = {
            "propositional_analysis_results": [
                {"formulas": ["p & q"], "satisfiable": True},
            ]
        }
        metrics = _extract_phase_metrics(snapshot)
        assert metrics["pl_formulas"] == 1
        assert metrics["pl_verified"] == 1
