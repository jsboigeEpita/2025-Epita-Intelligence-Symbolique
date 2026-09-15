"""#2116 (lot A6, dispatch R1007 D2): the withdrawn surfaces must stay gone.

Born-red: every find_spec here returns a spec BEFORE the withdrawal (the
modules exist on main) and must return None after. These islands had zero
production importers (measured in the #2116 dossier and re-measured at
execution time); the guard keeps them from being quietly resurrected.
"""

import importlib.util


def _spec(name):
    return importlib.util.find_spec(name)


def test_integrations_namespace_is_gone():
    # The SK JTMS surface that production actually mounts lives in
    # plugins/semantic_kernel/ — integrations/ was a second, dead montage.
    assert _spec("argumentation_analysis.integrations") is None


def test_effectiveness_analyzer_module_is_gone():
    # The live twin is reporting_pipeline._analyze_agent_effectiveness; the
    # analytics module was a divergent duplicate with zero production callers.
    assert _spec("argumentation_analysis.analytics.effectiveness_analyzer") is None


def test_viz_trio_is_gone():
    # html_report stays — it is the only visualization module ever imported
    # in production. The chart trio had zero importers and zero tests.
    for mod in ("quality_viz", "dung_viz", "pipeline_viz"):
        assert _spec(f"argumentation_analysis.visualization.{mod}") is None


def test_visualization_package_exports_only_html_report():
    import argumentation_analysis.visualization as viz

    assert viz.__all__ == ["render_html_report"]
