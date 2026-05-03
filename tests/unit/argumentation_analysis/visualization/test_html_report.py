"""Snapshot tests for the HTML report renderer."""

import json
import pathlib

import pytest

FIXTURE_PATH = pathlib.Path(__file__).parent.parent.parent.parent / "golden" / "fixtures" / "spectacular" / "doc_a_golden.json"


@pytest.fixture
def golden_state():
    if not FIXTURE_PATH.exists():
        pytest.skip("Golden fixture not available")
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class TestHTMLReport:
    """Snapshot tests verifying HTML report structure on golden fixture."""

    def test_renders_without_error(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert len(html) > 1000
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_self_contained_single_file(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert html.count("<!DOCTYPE") == 1

    def test_executive_summary_present(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "Arguments" in html
        assert "Fallacies" in html
        assert "Counter-Args" in html
        assert "JTMS Beliefs" in html
        assert "ATMS Contexts" in html

    def test_argument_extraction_section(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "Argument Extraction" in html
        assert "arg_p1" in html
        assert "arg_c1" in html
        assert "Quality" in html

    def test_fallacy_detection_with_heatmap(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "Fallacy Detection" in html
        assert "heatmap-cell" in html
        assert "ad_hominem" in html
        assert "slippery_slope" in html

    def test_dung_graph_interactive(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "dung-graph" in html
        assert "cytoscape" in html
        assert "grounded" in html
        assert "preferred" in html
        assert "status_assignment" not in html  # internal key, not displayed raw

    def test_atms_tree_interactive(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "atms-tree" in html
        assert "d3.v7" in html
        assert "contradictory" in html
        assert "consistent" in html
        assert "ctx_absolute_freedom" in html

    def test_jtms_belief_network(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "JTMS" in html
        assert "Retraction" in html
        assert "cascade_1" in html
        assert "IN" in html
        assert "OUT" in html

    def test_counter_arguments_section(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "Counter-Arguments" in html
        assert "reductio" in html
        assert "counter_example" in html

    def test_governance_vote_section(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "Governance" in html
        assert "Majority" in html or "majority" in html
        assert "Borda" in html or "borda" in html
        assert "Condorcet" in html or "condorcet" in html

    def test_narrative_synthesis_section(self, golden_state):
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "Narrative Synthesis" in html
        assert "narrative" in html  # CSS class

    def test_renders_to_file(self, golden_state, tmp_path):
        from argumentation_analysis.visualization.html_report import render_html_report

        output = tmp_path / "report.html"
        html = render_html_report(golden_state, output_path=str(output))
        assert output.exists()
        assert output.read_text(encoding="utf-8") == html

    def test_three_interactive_viz_present(self, golden_state):
        """Verify at least 3 interactive viz: Dung graph, ATMS tree, heatmap."""
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        viz_checks = [
            ("Dung graph (cytoscape.js)", "cytoscape" in html and "dung-graph" in html),
            ("ATMS tree (D3.js)", "d3.v7" in html and "atms-tree" in html),
            ("Fallacy heatmap (CSS gradient)", "heatmap-cell" in html),
        ]
        for name, present in viz_checks:
            assert present, f"Missing interactive viz: {name}"

    def test_render_performance(self, golden_state):
        """Rendering should complete in < 2 seconds."""
        import time
        from argumentation_analysis.visualization.html_report import render_html_report

        start = time.monotonic()
        render_html_report(golden_state)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"Rendering took {elapsed:.2f}s (expected < 2s)"

    def test_no_pattern_section_without_data(self, golden_state):
        """Pattern Mining section should NOT appear when pattern_data is None."""
        from argumentation_analysis.visualization.html_report import render_html_report

        html = render_html_report(golden_state)
        assert "Discourse Pattern Mining" not in html

    def test_pattern_section_with_data(self, golden_state):
        """Pattern Mining section appears when pattern_data is provided."""
        from argumentation_analysis.visualization.html_report import render_html_report

        pattern = {
            "spectrum": {
                "propaganda": {"ad_hominem": 0.5, "appeal_to_fear": 0.3},
                "debate": {"straw_man": 0.4, "false_dilemma": 0.6},
            },
            "asymmetry": {
                "propaganda": {"tricherie_share": 0.2, "influence_share": 0.8, "asymmetry": 0.6},
                "debate": {"tricherie_share": 0.5, "influence_share": 0.5, "asymmetry": 0.0},
            },
            "cooccurrence_pairs": [
                {"a": "ad_hominem", "b": "appeal_to_fear", "support": 5, "lift": 2.3, "jaccard": 0.45},
            ],
            "cross_coverage": {
                "ad_hominem": {"fol_invalid": 0.0, "dung_unsupported": 1.0, "jtms_retraction": 0.0},
            },
        }
        html = render_html_report(golden_state, pattern_data=pattern)
        assert "Discourse Pattern Mining" in html
        assert "Fallacy Spectra by Cluster" in html
        assert "propaganda" in html
        assert "debate" in html
        assert "Tricherie" in html
        assert "Influence" in html
        assert "Co-occurrence" in html
        assert "ad_hominem" in html
        assert "Cross-coverage" in html

    def test_pattern_section_partial_data(self, golden_state):
        """Pattern section renders with only spectrum (no asymmetry/cooccurrence)."""
        from argumentation_analysis.visualization.html_report import render_html_report

        pattern = {
            "spectrum": {"cluster_a": {"red_herring": 1.0}},
        }
        html = render_html_report(golden_state, pattern_data=pattern)
        assert "Discourse Pattern Mining" in html
        assert "Fallacy Spectra by Cluster" in html
        assert "red_herring" in html
        # Asymmetry and co-occurrence should be absent
        assert "Asymmetry" not in html
        assert "Co-occurrence" not in html
