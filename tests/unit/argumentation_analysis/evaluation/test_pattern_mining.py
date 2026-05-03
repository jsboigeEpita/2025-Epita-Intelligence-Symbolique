"""Tests for argumentation_analysis.evaluation.pattern_mining."""

import json
from pathlib import Path

import pytest

from argumentation_analysis.evaluation.pattern_mining import (
    FORMAL_DETECTORS,
    AtmsBranchingDetector,
    DungTopologyDetector,
    FormalPatternDetector,
    JtmsRetractionRateDetector,
    cooccurrence_matrix,
    cross_coverage,
    fallacy_spectrum,
    run_formal_detectors,
    trick_vs_influence_ratio,
)

# ---------------------------------------------------------------------------
# Fixtures — synthetic signatures
# ---------------------------------------------------------------------------


def _sig(fallacies, cluster="A", **extra_state):
    """Build a minimal signature dict for testing."""
    fallacy_dict = {}
    for i, (ftype, family) in enumerate(fallacies):
        fallacy_dict[f"f{i}"] = {
            "type": ftype,
            "family": family,
            "source_arg": f"arg_{i % 3}",
        }

    state = {
        "identified_fallacies": fallacy_dict,
        "dung_frameworks": extra_state.get("dung_frameworks", {}),
        "atms_contexts": extra_state.get("atms_contexts", []),
        "jtms_beliefs": extra_state.get("jtms_beliefs", {}),
        "jtms_retraction_chain": extra_state.get("jtms_retraction_chain", []),
        "fol_analysis_results": extra_state.get("fol_analysis_results", []),
    }
    return {
        "opaque_id": f"test_{cluster}",
        "metadata": {"cluster_id": cluster},
        "state": state,
    }


@pytest.fixture
def sigs_political():
    """3 signatures in cluster 'political' with mixed fallacies."""
    return [
        _sig(
            [("ad_hominem", "relevance"), ("straw_man", "distortion")],
            cluster="political",
        ),
        _sig(
            [("slippery_slope", "causal"), ("false_dilemma", "presumption")],
            cluster="political",
        ),
        _sig(
            [("ad_hominem", "relevance"), ("hasty_generalization", "inductive")],
            cluster="political",
        ),
    ]


@pytest.fixture
def sigs_media():
    """2 signatures in cluster 'media' with influence-heavy fallacies."""
    return [
        _sig(
            [("appeal_to_emotion", "emotion"), ("bandwagon", "relevance")],
            cluster="media",
        ),
        _sig(
            [("appeal_to_emotion", "emotion"), ("appeal_to_authority", "authority")],
            cluster="media",
        ),
    ]


# ---------------------------------------------------------------------------
# fallacy_spectrum
# ---------------------------------------------------------------------------


class TestFallacySpectrum:
    def test_distribution(self, sigs_political):
        result = fallacy_spectrum(sigs_political, by="cluster_id")
        assert "political" in result
        spec = result["political"]
        # ad_hominem appears twice in 6 total → 0.3333
        assert spec.get("ad_hominem", 0) == pytest.approx(0.3333, abs=0.01)

    def test_empty_signatures(self):
        result = fallacy_spectrum([], by="cluster_id")
        assert result == {}

    def test_multiple_clusters(self, sigs_political, sigs_media):
        all_sigs = sigs_political + sigs_media
        result = fallacy_spectrum(all_sigs, by="cluster_id")
        assert "political" in result
        assert "media" in result


# ---------------------------------------------------------------------------
# trick_vs_influence_ratio
# ---------------------------------------------------------------------------


class TestTrickVsInfluence:
    def test_influence_heavy_cluster(self, sigs_media):
        result = trick_vs_influence_ratio(sigs_media, by="cluster_id")
        media = result["media"]
        assert media["influence_share"] > 0
        assert media["asymmetry"] > 0  # More influence than tricherie

    def test_mixed_cluster(self, sigs_political):
        result = trick_vs_influence_ratio(sigs_political, by="cluster_id")
        pol = result["political"]
        assert "tricherie_share" in pol
        assert "influence_share" in pol
        assert "ratio" in pol
        assert "asymmetry" in pol

    def test_all_influence_asymmetry_one(self):
        sigs = [
            _sig(
                [("appeal_to_emotion", "emotion"), ("bandwagon", "relevance")],
                cluster="all_inf",
            )
        ]
        result = trick_vs_influence_ratio(sigs, by="cluster_id")
        assert result["all_inf"]["asymmetry"] == pytest.approx(1.0, abs=0.01)

    def test_empty(self):
        result = trick_vs_influence_ratio([])
        assert result == {}


# ---------------------------------------------------------------------------
# cooccurrence_matrix
# ---------------------------------------------------------------------------


class TestCooccurrenceMatrix:
    def test_basic_cooccurrence(self):
        """2 docs with arg containing [A,B] each → support(A,B)=2, lift>1."""
        sigs = [
            {
                "metadata": {"cluster_id": "X"},
                "state": {
                    "identified_fallacies": {
                        "f0": {
                            "type": "ad_hominem",
                            "family": "rel",
                            "source_arg": "arg_shared",
                        },
                        "f1": {
                            "type": "straw_man",
                            "family": "dist",
                            "source_arg": "arg_shared",
                        },
                    },
                },
            },
            {
                "metadata": {"cluster_id": "X"},
                "state": {
                    "identified_fallacies": {
                        "f0": {
                            "type": "ad_hominem",
                            "family": "rel",
                            "source_arg": "arg_shared",
                        },
                        "f1": {
                            "type": "straw_man",
                            "family": "dist",
                            "source_arg": "arg_shared",
                        },
                    },
                },
            },
            _sig(
                [("false_dilemma", "pres")],
                cluster="X",
            ),
        ]
        result = cooccurrence_matrix(sigs, unit="argument")
        pairs = result["pairs"]
        hm_sm = [p for p in pairs if p["a"] == "ad_hominem" and p["b"] == "straw_man"]
        assert len(hm_sm) == 1
        assert hm_sm[0]["support"] == 2
        assert hm_sm[0]["lift"] >= 1.0

    def test_doc_level(self):
        sigs = [
            _sig(
                [("ad_hominem", "rel"), ("straw_man", "dist")],
                cluster="X",
            ),
        ]
        result = cooccurrence_matrix(sigs, unit="doc")
        assert result["unit_count"] >= 1

    def test_no_pairs(self):
        sigs = [_sig([("ad_hominem", "rel")], cluster="X")]
        result = cooccurrence_matrix(sigs, unit="argument")
        assert result["pairs"] == []

    def test_top_n(self):
        sigs = [_sig([("a", "x"), ("b", "x")], cluster="X")]
        result = cooccurrence_matrix(sigs, top_n=1)
        assert len(result["pairs"]) <= 1


# ---------------------------------------------------------------------------
# Formal detectors
# ---------------------------------------------------------------------------


class TestDungTopologyDetector:
    def test_empty(self):
        det = DungTopologyDetector()
        result = det.detect({"state": {}})
        assert result["n_args"] == 0.0
        assert result["density"] == 0.0

    def test_with_framework(self):
        sig = {
            "state": {
                "dung_frameworks": {
                    "fw1": {
                        "arguments": ["a1", "a2", "a3"],
                        "attacks": [
                            {"from": "a1", "to": "a2"},
                            {"from": "a2", "to": "a3"},
                        ],
                        "extensions": {
                            "grounded": ["a1", "a3"],
                            "preferred": [["a1", "a3"]],
                        },
                    }
                }
            }
        }
        det = DungTopologyDetector()
        result = det.detect(sig)
        assert result["n_args"] == 3.0
        assert result["n_attacks"] == 2.0
        assert result["density"] > 0
        assert result["max_extension_size"] == 2.0

    def test_no_division_by_zero(self):
        """0 args → density=0, no crash."""
        sig = {
            "state": {
                "dung_frameworks": {
                    "fw1": {
                        "arguments": [],
                        "attacks": [],
                        "extensions": {},
                    }
                }
            }
        }
        result = DungTopologyDetector().detect(sig)
        assert result["density"] == 0.0


class TestAtmsBranchingDetector:
    def test_empty(self):
        result = AtmsBranchingDetector().detect({"state": {}})
        assert result["max_depth"] == 0.0
        assert result["contradiction_rate"] == 0.0

    def test_with_contexts(self):
        sig = {
            "state": {
                "atms_contexts": [
                    {"assumptions": ["a1", "a2"], "status": "consistent"},
                    {"assumptions": ["a3"], "status": "contradictory"},
                ]
            }
        }
        result = AtmsBranchingDetector().detect(sig)
        assert result["max_depth"] == 2.0
        assert result["avg_assumptions"] == 1.5
        assert result["contradiction_rate"] == 0.5


class TestJtmsRetractionRateDetector:
    def test_empty(self):
        result = JtmsRetractionRateDetector().detect({"state": {}})
        assert result["n_beliefs"] == 0.0
        assert result["retraction_rate"] == 0.0

    def test_with_retractions(self):
        sig = {
            "state": {
                "jtms_beliefs": {
                    "b1": {"status": "IN", "justification": "j1"},
                    "b2": {"status": "OUT", "justification": "j2"},
                    "b3": {"status": "IN", "justification": "j1"},
                },
                "jtms_retraction_chain": [{"cascade_id": "c1"}],
            }
        }
        result = JtmsRetractionRateDetector().detect(sig)
        assert result["n_beliefs"] == 3.0
        assert result["retraction_rate"] == pytest.approx(0.3333, abs=0.01)


# ---------------------------------------------------------------------------
# run_formal_detectors
# ---------------------------------------------------------------------------


class TestRunFormalDetectors:
    def test_default_registry(self):
        sig = {
            "state": {"dung_frameworks": {}, "atms_contexts": [], "jtms_beliefs": {}}
        }
        result = run_formal_detectors(sig)
        assert "dung_topology" in result
        assert "atms_branching" in result
        assert "jtms_retraction_rate" in result

    def test_custom_detector(self):
        class DummyDetector:
            name = "dummy"

            def detect(self, sig):
                return {"value": 42.0}

        result = run_formal_detectors({}, detectors=[DummyDetector()])
        assert result["dummy"]["value"] == 42.0

    def test_detector_error_handled(self):
        class FailingDetector:
            name = "fail"

            def detect(self, sig):
                raise ValueError("boom")

        result = run_formal_detectors({}, detectors=[FailingDetector()])
        assert result["fail"]["error"] == 1.0


# ---------------------------------------------------------------------------
# cross_coverage
# ---------------------------------------------------------------------------


class TestCrossCoverage:
    def test_with_formal_signals(self):
        sig = {
            "state": {
                "identified_fallacies": {
                    "f1": {
                        "type": "ad_hominem",
                        "family": "relevance",
                        "source_arg": "a1",
                    },
                },
                "fol_analysis_results": [{"valid": False}],
                "jtms_retraction_chain": [{"cascade_id": "c1"}],
                "dung_frameworks": {},
            }
        }
        result = cross_coverage([sig])
        assert "ad_hominem" in result
        assert result["ad_hominem"]["fol_invalid"] == 1.0
        assert result["ad_hominem"]["jtms_retraction"] == 1.0

    def test_empty(self):
        result = cross_coverage([])
        assert result == {}

    def test_no_formal_signals(self):
        sigs = [
            _sig([("ad_hominem", "rel")], cluster="X"),
        ]
        result = cross_coverage(sigs)
        for ftype, signals in result.items():
            for rate in signals.values():
                assert rate == 0.0


# ---------------------------------------------------------------------------
# Registry count
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_three_built_in_detectors(self):
        assert len(FORMAL_DETECTORS) == 3

    def test_all_implement_protocol(self):
        for det in FORMAL_DETECTORS:
            assert isinstance(det, FormalPatternDetector)
            assert hasattr(det, "name")
            assert callable(det.detect)
