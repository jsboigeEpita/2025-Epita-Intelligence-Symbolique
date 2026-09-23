"""#2116 (lot A6, dispatch R1007 D2): the withdrawn surfaces must stay gone.

Born-red: every find_spec here returns a spec BEFORE the withdrawal (the
modules exist on main) and must return None after. These islands had zero
production importers (measured in the #2116 dossier and re-measured at
execution time); the guard keeps them from being quietly resurrected.
"""

import importlib.util
from pathlib import Path


def _spec(name):
    return importlib.util.find_spec(name)


def _importable_entries(search_locations):
    """What a namespace package could import: every entry but ``__pycache__``.

    Git removes a deleted package's sources but not its untracked
    ``__pycache__/``. On a checkout that ran the code before the withdrawal,
    that leftover directory is enough for ``find_spec`` to resolve the name as
    an empty namespace package, although nothing under it can be imported
    (Python ignores ``__pycache__`` bytecode without its source). #2436
    measured it: the guide's verification step stopped on this guard on
    ai-01, whose checkout still held ``integrations/__pycache__/``.
    """
    return sorted(
        entry.name
        for location in search_locations
        for entry in Path(location).iterdir()
        if entry.name != "__pycache__"
    )


def test_integrations_namespace_is_gone():
    # The SK JTMS surface that production actually mounts lives in
    # plugins/semantic_kernel/ — integrations/ was a second, dead montage.
    spec = _spec("argumentation_analysis.integrations")
    if spec is None:
        return
    assert spec.origin in (None, "namespace"), f"a real package is back: {spec.origin}"
    assert not _importable_entries(spec.submodule_search_locations)


def test_the_leftover_reader_can_fail(tmp_path):
    """Non-vacuity: a cache-only directory reads as empty; a module or a
    subpackage next to the cache does not."""
    (tmp_path / "__pycache__").mkdir()
    assert _importable_entries([tmp_path]) == []
    (tmp_path / "revived.py").write_text("", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    assert _importable_entries([tmp_path]) == ["revived.py", "sub"]


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
