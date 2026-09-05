"""#2041 — a path string where loaded rows belong: the factory must build a
LIVE navigator, and the constructor must refuse a str loudly.

The defect (verified in reading, swallowed in running): the exploration
branch of ``PluginBenchmarkSuite._create_instance`` passed
``os.path.join(...)`` — always a non-empty string — to
``TaxonomyNavigator(taxonomy_data: List[Dict[str, Any]])``, whose
``_build_node_map`` iterates items calling ``.get("PK")``:
``AttributeError: 'str' object has no attribute 'get'`` on the first
character. The factory's blanket ``except Exception`` then logged a warning
and returned None — the crash read as « plugin not benchmarkable ».

This is the crash-symptom twin of the #2035 ``cites`` bug (a string
iterated as a sequence — there silently absurd output, here a crash). The
family sweep is the other deliverable of #2041; these tests pin the known
site through the FACTORY path (not the bare constructor), per the issue.
"""

from __future__ import annotations

import pytest


class TestExplorationFactoryBuildsALiveNavigator:
    """DoD 1: construction through the factory, born-red pre-fix (the
    factory returned None — the swallowed crash)."""

    def test_factory_returns_a_working_exploration_plugin(self):
        from argumentation_analysis.evaluation.plugin_benchmark import (
            PluginBenchmarkSuite,
        )

        plugin = PluginBenchmarkSuite()._instantiate_plugin("exploration")
        assert plugin is not None, (
            "#2041: the exploration branch of the plugin factory crashed "
            "(path string given to TaxonomyNavigator) and the blanket "
            "except swallowed it into 'not benchmarkable'"
        )

    def test_factory_navigator_is_populated_not_empty(self):
        # An empty navigator would be a silent false-negative on the whole
        # taxonomy — strictly worse than the crash (anti-pendule, issue).
        from argumentation_analysis.evaluation.plugin_benchmark import (
            PluginBenchmarkSuite,
        )

        plugin = PluginBenchmarkSuite()._instantiate_plugin("exploration")
        assert plugin is not None
        nav = plugin.taxonomy_navigator
        assert len(nav.node_map) == 1408, (
            f"expected the full vendored taxonomy (1408 rows), got "
            f"{len(nav.node_map)} nodes"
        )
        assert nav.get_node("328") is not None


class TestConstructorGuardRefusesAString:
    """DoD 4: if a guard is added, a clear TypeError beats an AttributeError
    on a character — and no legitimate caller passes a string."""

    def test_string_raises_type_error_with_clear_message(self):
        from argumentation_analysis.agents.utils.taxonomy_navigator import (
            TaxonomyNavigator,
        )

        with pytest.raises(TypeError, match="TaxonomyNavigator"):
            TaxonomyNavigator("some/path/to/taxonomy.csv")

    def test_loaded_rows_still_build_normally(self):
        import csv
        from pathlib import Path

        from argumentation_analysis.agents.utils.taxonomy_navigator import (
            TaxonomyNavigator,
        )
        from argumentation_analysis.paths import DATA_DIR

        csv_path = Path(DATA_DIR) / "argumentum_fallacies_taxonomy.csv"
        with open(csv_path, "r", encoding="utf-8") as f:
            nav = TaxonomyNavigator(list(csv.DictReader(f)))
        assert nav.get_node("328") is not None
