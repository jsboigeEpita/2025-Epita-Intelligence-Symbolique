"""Integration tests for build_pattern_report.py (C.4 — Issue #412).

Uses synthetic fixture signatures to validate report generation,
SVG output, and privacy guard without requiring real corpus data.
"""

import json
import pathlib
import textwrap

import pytest

from argumentation_analysis.evaluation.pattern_mining import (
    FORMAL_DETECTORS,
    cooccurrence_matrix,
    cross_coverage,
    fallacy_spectrum,
    run_formal_detectors,
    trick_vs_influence_ratio,
)

# ---------------------------------------------------------------------------
# Synthetic fixture signatures
# ---------------------------------------------------------------------------


def _make_signature(
    cluster_id: str = "test_cluster",
    fallacies: dict | None = None,
    dung_args: int = 0,
    dung_attacks: int = 0,
    jtms_retractions: int = 0,
    fol_valid: bool = True,
) -> dict:
    """Build a minimal synthetic signature for testing."""
    fallacies = fallacies or {}
    identified = {}
    for i, (ftype, src) in enumerate(fallacies.items()):
        identified[f"f{i}"] = {"type": ftype, "source_arg": src}

    dung_fw = {}
    if dung_args > 0:
        dung_fw["fw0"] = {
            "arguments": [f"arg{j}" for j in range(dung_args)],
            "attacks": [
                {"from": f"arg{j}", "to": f"arg{j+1}"}
                for j in range(min(dung_attacks, dung_args - 1))
            ],
            "extensions": {"grounded": [[f"arg{j}" for j in range(dung_args)]]},
        }

    jtms_beliefs = {f"b{j}": {"justification": f"j{j}"} for j in range(dung_args)}
    state = {
        "identified_fallacies": identified,
        "dung_frameworks": dung_fw,
        "jtms_beliefs": jtms_beliefs,
        "jtms_retraction_chain": [
            {"from": f"b{j}", "to": f"b{j+1}"} for j in range(jtms_retractions)
        ],
        "fol_analysis_results": [] if fol_valid else [{"valid": False}],
        "atms_contexts": [],
    }
    return {"metadata": {"cluster_id": cluster_id}, "state": state}


@pytest.fixture
def synthetic_signatures():
    """3 documents across 2 clusters with varied fallacy profiles."""
    return [
        _make_signature(
            "propaganda",
            {"ad_hominem": "arg0", "appeal_to_fear": "arg1", "straw_man": "arg0"},
            dung_args=4,
            dung_attacks=3,
            jtms_retractions=2,
            fol_valid=False,
        ),
        _make_signature(
            "propaganda",
            {"ad_hominem": "arg0", "bandwagon": "arg2", "cherry_picking": "arg3"},
            dung_args=2,
            dung_attacks=1,
            jtms_retractions=0,
        ),
        _make_signature(
            "debate",
            {"straw_man": "arg0", "false_dilemma": "arg1", "red_herring": "arg2"},
            dung_args=3,
            dung_attacks=2,
            jtms_retractions=1,
            fol_valid=False,
        ),
    ]


@pytest.fixture
def sig_dir(tmp_path, synthetic_signatures):
    """Write synthetic signatures to temp directory as JSON files."""
    for i, sig in enumerate(synthetic_signatures):
        (tmp_path / f"signature_{i:03d}.json").write_text(
            json.dumps(sig), encoding="utf-8"
        )
    return tmp_path


# ---------------------------------------------------------------------------
# Test: pattern_mining functions on synthetic data
# ---------------------------------------------------------------------------


class TestPatternMining:
    """Verify pattern_mining functions produce valid output on synthetic data."""

    def test_fallacy_spectrum_returns_clusters(self, synthetic_signatures):
        spectrum = fallacy_spectrum(synthetic_signatures)
        assert "propaganda" in spectrum
        assert "debate" in spectrum
        # Relative frequencies should sum to ~1.0 per cluster
        for cid, types in spectrum.items():
            total = sum(types.values())
            assert 0.0 < total <= 1.01, f"Cluster {cid} sum={total}"

    def test_fallacy_spectrum_values(self, synthetic_signatures):
        spectrum = fallacy_spectrum(synthetic_signatures)
        # propaganda cluster has ad_hominem in both docs → should have highest freq
        prop = spectrum["propaganda"]
        assert "ad_hominem" in prop
        assert prop["ad_hominem"] > 0

    def test_trick_vs_influence_ratio(self, synthetic_signatures):
        asym = trick_vs_influence_ratio(synthetic_signatures)
        assert "propaganda" in asym
        assert "debate" in asym
        for cid, d in asym.items():
            assert "tricherie_share" in d
            assert "influence_share" in d
            assert "asymmetry" in d
            assert -1.0 <= d["asymmetry"] <= 1.0

    def test_cooccurrence_matrix(self, synthetic_signatures):
        coocc = cooccurrence_matrix(synthetic_signatures, top_n=10)
        assert "pairs" in coocc
        assert "unit_count" in coocc
        # With co-occurring fallacies in same source_arg, we should get some pairs
        assert coocc["unit_count"] >= 0

    def test_cross_coverage(self, synthetic_signatures):
        xcov = cross_coverage(synthetic_signatures)
        assert isinstance(xcov, dict)
        # New structure: {ftype: {"per_signature_rate": {...}, "per_occurrence_rate": {...}}}
        if xcov:
            for ftype, rates in xcov.items():
                assert "per_signature_rate" in rates
                assert "per_occurrence_rate" in rates
                for rate_family in ["per_signature_rate", "per_occurrence_rate"]:
                    for sig_name in [
                        "fol_invalid",
                        "dung_unsupported",
                        "jtms_retraction",
                    ]:
                        assert sig_name in rates[rate_family]

    def test_formal_detectors(self, synthetic_signatures):
        for sig in synthetic_signatures:
            results = run_formal_detectors(sig)
            assert len(results) == len(FORMAL_DETECTORS)
            for det in FORMAL_DETECTORS:
                assert det.name in results
                metrics = results[det.name]
                assert all(isinstance(v, float) for v in metrics.values())


# ---------------------------------------------------------------------------
# Test: build_pattern_report functions
# ---------------------------------------------------------------------------


class TestReportBuilder:
    """Test report generation and SVG output."""

    def test_load_signatures(self, sig_dir, synthetic_signatures):
        from scripts.dataset.build_pattern_report import load_signatures

        loaded = load_signatures(sig_dir)
        assert len(loaded) == len(synthetic_signatures)

    def test_load_signatures_empty_dir(self, tmp_path):
        from scripts.dataset.build_pattern_report import load_signatures

        assert load_signatures(tmp_path) == []
        assert load_signatures(tmp_path / "nonexistent") == []

    def test_build_report_generates_markdown(self, sig_dir, tmp_path):
        from scripts.dataset.build_pattern_report import load_signatures, build_report

        sigs = load_signatures(sig_dir)
        report_path = tmp_path / "discourse_patterns.md"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = build_report(sigs, output_dir, report_path)
        assert result == report_path
        assert report_path.exists()

        content = report_path.read_text(encoding="utf-8")
        assert "# Discourse Pattern Report" in content
        assert "## 1. Fallacy Spectra by Cluster" in content
        assert "## 2. Tricherie" in content
        assert "## 3. Co-occurrence" in content
        assert "## 4. Formal Pattern Detectors" in content
        assert "## 5. Cross-coverage" in content
        assert "## 6. Limitations" in content

    def test_build_report_generates_svgs(self, sig_dir, tmp_path):
        from scripts.dataset.build_pattern_report import load_signatures, build_report

        sigs = load_signatures(sig_dir)
        report_path = tmp_path / "discourse_patterns.md"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        build_report(sigs, output_dir, report_path)

        svg_dir = output_dir / "discourse_patterns"
        assert svg_dir.is_dir()
        assert (svg_dir / "heatmap_fallacies.svg").exists()
        assert (svg_dir / "asymmetry_chart.svg").exists()

        # Heatmap should contain SVG markup
        heatmap = (svg_dir / "heatmap_fallacies.svg").read_text(encoding="utf-8")
        assert "<svg" in heatmap
        assert "</svg>" in heatmap

    def test_build_report_generates_radar_svgs(self, sig_dir, tmp_path):
        from scripts.dataset.build_pattern_report import load_signatures, build_report

        sigs = load_signatures(sig_dir)
        report_path = tmp_path / "discourse_patterns.md"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        build_report(sigs, output_dir, report_path)

        svg_dir = output_dir / "discourse_patterns"
        radar_files = list(svg_dir.glob("spectrum_radar_*.svg"))
        # Should have at least one radar for each cluster (up to 5)
        assert len(radar_files) >= 1

    def test_privacy_guard_blocks_forbidden_strings(self):
        from scripts.dataset.build_pattern_report import privacy_guard

        for forbidden in ["raw_text", "full_text", "source_name", '"text":', "author"]:
            with pytest.raises(SystemExit, match="1"):
                privacy_guard(f"This has {forbidden} in it")

    def test_privacy_guard_allows_clean_content(self):
        from scripts.dataset.build_pattern_report import privacy_guard

        # Should not raise
        privacy_guard("Clean content with no forbidden strings")
        privacy_guard("Fallacy spectra and co-occurrence data")


# ---------------------------------------------------------------------------
# Test: SVG generation edge cases
# ---------------------------------------------------------------------------


class TestSVGGeneration:
    """Test SVG generation with edge-case inputs."""

    def test_heatmap_empty_pairs(self):
        from scripts.dataset.build_pattern_report import generate_heatmap_svg

        svg = generate_heatmap_svg([])
        assert "<svg" in svg
        assert "No co-occurrence data" in svg

    def test_radar_empty_cluster(self):
        from scripts.dataset.build_pattern_report import generate_radar_svg

        svg = generate_radar_svg({}, "nonexistent")
        assert "<svg" in svg
        assert "No data for nonexistent" in svg

    def test_asymmetry_empty(self):
        from scripts.dataset.build_pattern_report import generate_asymmetry_svg

        svg = generate_asymmetry_svg({})
        assert "<svg" in svg
        assert "No asymmetry data" in svg

    def test_heatmap_with_data(self):
        from scripts.dataset.build_pattern_report import generate_heatmap_svg

        pairs = [
            {"a": "ad_hominem", "b": "straw_man", "lift": 2.5},
            {"a": "appeal_to_fear", "b": "bandwagon", "lift": 1.8},
            {"a": "ad_hominem", "b": "appeal_to_fear", "lift": 3.1},
        ]
        svg = generate_heatmap_svg(pairs)
        assert "<svg" in svg
        assert "ad_hominem" in svg
        assert "2.5" in svg

    def test_asymmetry_with_data(self):
        from scripts.dataset.build_pattern_report import generate_asymmetry_svg

        data = {
            "cluster_a": {
                "tricherie_share": 0.3,
                "influence_share": 0.7,
                "asymmetry": 0.4,
            },
            "cluster_b": {
                "tricherie_share": 0.6,
                "influence_share": 0.2,
                "asymmetry": -0.5,
            },
        }
        svg = generate_asymmetry_svg(data)
        assert "<svg" in svg
        assert "cluster_a" in svg
