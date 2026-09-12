"""#2100 — real-execution guard for TaxonomyExplorerPlugin.detect_and_classify.

The method's nominal path (a detected sophism whose taxonomy key is mapped to
a family) used to call ``self._calculate_context_relevance`` — a method that
does not exist (the defined one is ``_calculate_contextual_relevance``). The
defect was invisible because nothing executed the path: a mocked detector
never takes it, and the plugin itself was unconstructible
(``get_global_detector()`` built ``InformalAnalysisPlugin`` without its then
required ``kernel`` argument). This guard is deliberately mock-free: it
constructs the real plugin over the real taxonomy CSV and feeds it a text
that reaches the family-scoring branch.
"""

import pytest

from argumentation_analysis.plugin_framework.core.plugins.standard.taxonomy_explorer.plugin import (
    TaxonomyExplorerPlugin,
)


@pytest.fixture(scope="module")
def plugin() -> TaxonomyExplorerPlugin:
    return TaxonomyExplorerPlugin()


def _named_mapped_fallacy(plugin: TaxonomyExplorerPlugin):
    """A (pk, vulgarised name) whose detection provably reaches the family branch."""
    df = plugin.detector._get_taxonomy_df()
    for pk, name in df["nom_vulgarisé"].dropna().items():
        if pk in plugin._family_mapping_cache:
            return int(pk), str(name)
    pytest.skip("no fallacy in the taxonomy is both named and family-mapped")


async def test_detect_and_classify_reaches_family_scoring_on_real_detection(plugin):
    pk, vulgarised = _named_mapped_fallacy(plugin)
    text = (
        "Ce discours ne repond pas a l'objection : il repose sur une "
        f"mention de type {vulgarised} plutot que sur un argument."
    )

    results = await plugin.detect_and_classify(text)

    hits = [r for r in results if r["taxonomy_key"] == pk]
    assert hits, (
        f"expected pk {pk} ({vulgarised!r}) among detections, got "
        f"{[(r['taxonomy_key'], r['nom_vulgarise']) for r in results]}"
    )
    hit = hits[0]
    expected_family = plugin._family_mapping_cache[pk]
    assert hit["family"] == expected_family
    assert hit["detection_method"] == f"taxonomy_family_{expected_family}"
    assert isinstance(hit["context_relevance"], float)
    assert 0.0 <= hit["context_relevance"] <= 1.0
    assert hit["severity"] in {"Critique", "Haute", "Moyenne", "Faible", "Négligeable"}
    assert isinstance(hit["family_pattern_score"], float)
