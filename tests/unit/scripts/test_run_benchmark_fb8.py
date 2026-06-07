"""Tests for FB-8 benchmark runner FR↔EN alias map (#995).

Verifies that the fallacy type normalizer correctly maps French pipeline
labels to English canonical markers expected by the yardstick scorer.
"""

import pytest


class TestFallacyAliasMap:
    """Verify FR→EN fallacy alias normalization (#995)."""

    def test_faux_dilemme_maps_to_false_dilemma(self):
        """'Faux dilemme' (FR) must map to 'false_dilemma' (EN yardstick)."""
        from scripts.run_benchmark_fb8 import _normalize_fallacy_type

        assert _normalize_fallacy_type("Faux dilemme") == "false_dilemma"

    def test_appel_emotion_maps_to_appeal_to_emotion(self):
        """'Appel à l'émotion' (FR) must map to 'appeal_to_emotion' (EN)."""
        from scripts.run_benchmark_fb8 import _normalize_fallacy_type

        assert _normalize_fallacy_type("Appel à l'émotion") == "appeal_to_emotion"

    def test_appel_identite_maps_to_appeal_to_identity(self):
        """'Appel à l'identité' (FR) must map to 'appeal_to_identity' (EN)."""
        from scripts.run_benchmark_fb8 import _normalize_fallacy_type

        assert _normalize_fallacy_type("Appel à l'identité") == "appeal_to_identity"

    def test_argument_circulaire_maps_to_circular_reasoning(self):
        """'Argument circulaire' (FR) must map to 'circular_reasoning' (EN)."""
        from scripts.run_benchmark_fb8 import _normalize_fallacy_type

        assert _normalize_fallacy_type("Argument circulaire") == "circular_reasoning"

    def test_raison_majorite_maps_to_ad_populum(self):
        """'Raison de la majorité' (FR) must map to 'ad_populum' (EN)."""
        from scripts.run_benchmark_fb8 import _normalize_fallacy_type

        assert _normalize_fallacy_type("Raison de la majorité") == "ad_populum"

    def test_pente_glissante_maps_to_slippery_slope(self):
        """'Pente glissante' (FR) must map to 'slippery_slope' (EN)."""
        from scripts.run_benchmark_fb8 import _normalize_fallacy_type

        assert _normalize_fallacy_type("Pente glissante") == "slippery_slope"

    def test_en_snake_case_passes_through(self):
        """EN snake_case markers already in canonical form pass through."""
        from scripts.run_benchmark_fb8 import _normalize_fallacy_type

        assert _normalize_fallacy_type("circular_reasoning") == "circular_reasoning"
        assert _normalize_fallacy_type("ad_populum") == "ad_populum"

    def test_unknown_returns_lowered(self):
        """Unknown FR labels are returned lowercased (no crash)."""
        from scripts.run_benchmark_fb8 import _normalize_fallacy_type

        result = _normalize_fallacy_type("Sophisme inconnu")
        assert result == "sophisme inconnu"


class TestScorerWithAliasMap:
    """Verify the scorer correctly applies FR→EN aliases on real-ish data."""

    def test_fr_fallacies_score_against_yardstick(self):
        """French-detected fallacies must be credited against EN yardstick markers.

        This is the core #995 fix: the scorer should recognize 'Faux dilemme'
        as matching the 'false_dilemma' yardstick marker for D1 scoring.
        """
        from scripts.run_benchmark_fb8 import score_against_yardstick

        # Simulate pipeline output with FR-only fallacy labels
        pipeline_output = {
            "phases": {
                "fallacies": {
                    "f1": {
                        "family": "Faux dilemme",
                        "fallacy_type": "Faux dilemme",
                        "description": "Présente deux options alors qu'il y en a plus",
                        "confidence": 0.85,
                    },
                    "f2": {
                        "family": "Appel à l'identité",
                        "fallacy_type": "Appel à l'identité",
                        "description": "Appartenance au groupe comme preuve",
                        "confidence": 0.75,
                    },
                    "f3": {
                        "family": "Raison de la majorité",
                        "fallacy_type": "Raison de la majorité",
                        "description": "Populist rhetoric from elite position",
                        "confidence": 0.70,
                    },
                },
                "fallacies_count": 3,
                "arguments": {"arg_1": "Test arg"},
                "arguments_count": 1,
                "counter_arguments": ["CA1"],
                "propositional_analysis_results": [],
                "fol_analysis_results": [],
                "dung_frameworks": {},
                "quality_scores": {},
                "narrative_synthesis": "",
            },
        }

        scorecard = score_against_yardstick(pipeline_output)

        # D3 (Populist Rhetoric) should now score at least PARTIAL because
        # "Raison de la majorité" → "ad_populum" is recognized
        d3_score = scorecard["D3"]["score"]
        assert d3_score in ("MATCH", "PARTIAL"), (
            f"D3 should score MATCH or PARTIAL with FR ad_populum alias, "
            f"got {d3_score}. Scorer: {scorecard['D3']['synthesis']}"
        )
