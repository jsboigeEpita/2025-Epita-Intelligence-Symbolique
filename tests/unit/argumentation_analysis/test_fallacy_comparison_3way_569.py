"""Tests for #569: 3-way comparison script structure and helper functions."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestComparisonScriptStructure:
    """Verify the comparison script exists and has the right structure."""

    def test_script_exists(self):
        script = Path("scripts/compare_fallacy_detection_modes.py")
        assert script.exists()

    def test_script_has_three_mode_functions(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "compare", "scripts/compare_fallacy_detection_modes.py"
        )
        mod = importlib.util.module_from_spec(spec)
        import sys
        sys.modules["compare"] = mod
        # We can't fully import (needs crypto), just check source
        source = Path("scripts/compare_fallacy_detection_modes.py").read_text(encoding="utf-8")
        assert "async def run_mode_a_raw" in source
        assert "async def run_mode_b_taxonomy_fc" in source
        assert "async def run_mode_c_subworkflow" in source

    def test_script_has_assessment_functions(self):
        source = Path("scripts/compare_fallacy_detection_modes.py").read_text(encoding="utf-8")
        assert "_assess_depth" in source
        assert "_assess_specificity" in source
        assert "_assess_citation" in source


class TestAssessmentHelpers:
    """Test the depth, specificity, and citation assessment functions."""

    def test_depth_leaf(self):
        from scripts.compare_fallacy_detection_modes import _assess_depth
        taxonomy = [{"PK": "ad_hominem_abusif", "depth": "3", "text_fr": "Ad hominem abusif"}]
        fallacy = {"fallacy_type": "Ad hominem abusif", "taxonomy_pk": "ad_hominem_abusif"}
        assert _assess_depth(fallacy, taxonomy) == "leaf"

    def test_depth_family(self):
        from scripts.compare_fallacy_detection_modes import _assess_depth
        taxonomy = [{"PK": "ad_hominem", "depth": "1", "text_fr": "Ad hominem"}]
        fallacy = {"fallacy_type": "Ad hominem", "taxonomy_pk": "ad_hominem"}
        assert _assess_depth(fallacy, taxonomy) == "family"

    def test_depth_vague(self):
        from scripts.compare_fallacy_detection_modes import _assess_depth
        fallacy = {"fallacy_type": "Bad reasoning"}
        assert _assess_depth(fallacy, []) == "vague"

    def test_specificity_exact_subtype(self):
        from scripts.compare_fallacy_detection_modes import _assess_specificity
        fallacy = {"fallacy_type": "Ad hominem abusif circonstanciel"}
        assert _assess_specificity(fallacy) == "exact_subtype"

    def test_specificity_generic(self):
        from scripts.compare_fallacy_detection_modes import _assess_specificity
        fallacy = {"fallacy_type": "Fallacy"}
        assert _assess_specificity(fallacy) == "generic"

    def test_citation_exact_quote(self):
        from scripts.compare_fallacy_detection_modes import _assess_citation
        fallacy = {"explanation": 'The author says "this is clearly wrong" which is fallacious'}
        text = 'The author says "this is clearly wrong" in paragraph 2'
        assert _assess_citation(fallacy, text) == "exact_quote"

    def test_citation_no_citation(self):
        from scripts.compare_fallacy_detection_modes import _assess_citation
        fallacy = {"explanation": "This is an ad hominem because the author attacks the person"}
        assert _assess_citation(fallacy, "some text") == "no_citation"

    def test_extract_fallacies_from_json_array(self):
        from scripts.compare_fallacy_detection_modes import _extract_fallacies_from_text
        raw = '```json\n[{"fallacy_type": "ad hominem", "explanation": "test"}]\n```'
        result = _extract_fallacies_from_text(raw)
        assert len(result) == 1
        assert result[0]["fallacy_type"] == "ad hominem"

    def test_extract_fallacies_from_plain_json(self):
        from scripts.compare_fallacy_detection_modes import _extract_fallacies_from_text
        raw = '{"fallacy_type": "straw man", "explanation": "misrepresentation"}'
        result = _extract_fallacies_from_text(raw)
        assert len(result) == 1
        assert result[0]["fallacy_type"] == "straw man"
