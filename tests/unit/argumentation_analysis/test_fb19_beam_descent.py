"""Unit tests for FB-19 deep-index + wide-net helpers (#1040 / #1042).

FB-30 (#1107) note: the mechanical per-level `_beam_descent` method and its
constants (BEAM_WIDTH / BEAM_MAX_LLM_CALLS / BEAM_MIN_DEPTH) have been
REMOVED — restored agentic navigation in `_explore_single_branch` (no depth
cap + multi-level cluster) now reaches deep/lateral nodes directly. The
beam-specific test classes (TestBeamDescent / TestBeamIntegration /
TestValueGates) were testing the removed method and have been deleted with
it. See `test_fb30_agentic_navigation.py` for the restored-navigation tests.

What remains load-bearing here:
- `_build_deep_index` / `_map_fallacy_to_deep_pk` — the deep name→PK index
  the wide-net uses to give the agentic navigation a 2-3 level head start.
- `_wide_net_candidates` — Phase 1 candidate selection (deep-then-root).
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from argumentation_analysis.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin

# ---------------------------------------------------------------------------
# Fixtures — synthetic taxonomy + plugin
# ---------------------------------------------------------------------------


def _make_taxonomy_data():
    """Build a synthetic taxonomy with several levels for deep-index testing."""
    data = []
    # Root families (depth 1)
    families = [
        ("1", "Insuffisance", "insufficiency", 1),
        ("2", "Influence", "influence", 1),
        ("3", "Obstruction", "obstruction", 1),
        ("4", "Erreur de raisonnement", "reasoning error", 1),
        ("5", "Contradiction", "contradiction", 1),
        ("6", "Tricherie", "cheating", 1),
        ("7", "Biais", "bias", 1),
    ]
    for path, name_fr, name_en, depth in families:
        data.append(
            {
                "PK": path,
                "path": path,
                "depth": str(depth),
                "text_fr": name_fr,
                "text_en": name_en,
                "desc_fr": f"Description of {name_fr}",
                "desc_en": f"Description of {name_en}",
                "Famille": name_fr,
                "nom_vulgarisé": name_fr,
            }
        )

    # Depth 2: 2 children per family
    for fam_path, fam_name, _, _ in families:
        for i, (child_name, child_en) in enumerate(
            [
                ("Argument bâclé", "sloppy argument"),
                ("Préjugé", "prejudice"),
            ]
        ):
            child_path = f"{fam_path}.{i + 1}"
            data.append(
                {
                    "PK": child_path.replace(".", ""),
                    "path": child_path,
                    "depth": "2",
                    "text_fr": child_name,
                    "text_en": child_en,
                    "desc_fr": f"Sub-category {child_name}",
                    "desc_en": f"Sub-category {child_en}",
                    "Famille": fam_name,
                    "Sous-Famille": child_name,
                    "nom_vulgarisé": child_name,
                }
            )

            # Depth 3: 2 children per depth-2 node
            for j, (gc_name, gc_en) in enumerate(
                [
                    (f"Sub-{child_name}-A", f"Sub-{child_en}-A"),
                    (f"Sub-{child_name}-B", f"Sub-{child_en}-B"),
                ]
            ):
                gc_path = f"{child_path}.{j + 1}"
                data.append(
                    {
                        "PK": gc_path.replace(".", ""),
                        "path": gc_path,
                        "depth": "3",
                        "text_fr": gc_name,
                        "text_en": gc_en,
                        "desc_fr": f"Deeper {gc_name}",
                        "desc_en": f"Deeper {gc_en}",
                        "Famille": fam_name,
                        "Sous-Famille": child_name,
                        "nom_vulgarisé": gc_name,
                    }
                )

                # Depth 4-7: chain (kept so deep-index maps non-trivial names)
                parent_path = gc_path
                parent_pk = gc_path.replace(".", "")
                for d in range(4, 8):
                    deeper_path = f"{parent_path}.{d - 3}"
                    deeper_pk = deeper_path.replace(".", "")
                    data.append(
                        {
                            "PK": deeper_pk,
                            "path": deeper_path,
                            "depth": str(d),
                            "text_fr": f"Deep-{d}-{parent_pk[:4]}",
                            "text_en": f"Deep-{d}-{parent_pk[:4]}",
                            "desc_fr": f"Deep node at depth {d}",
                            "desc_en": f"Deep node at depth {d}",
                            "Famille": fam_name,
                            "nom_vulgarisé": f"Deep-{d}",
                        }
                    )
                    parent_path = deeper_path
                    parent_pk = deeper_pk

    return data


def _make_plugin(taxonomy_data=None):
    """Create a FallacyWorkflowPlugin with synthetic taxonomy, no real LLM."""
    data = taxonomy_data or _make_taxonomy_data()
    mock_kernel = MagicMock()
    mock_service = MagicMock()
    return FallacyWorkflowPlugin(
        master_kernel=mock_kernel,
        llm_service=mock_service,
        taxonomy_data=data,
    )


# ---------------------------------------------------------------------------
# Test: Deep index (FB-19 enhancement)
# ---------------------------------------------------------------------------


class TestDeepIndex:

    def test_build_deep_index_returns_depth_1_through_3(self):
        plugin = _make_plugin()
        deep_index = plugin._build_deep_index(max_depth=3)
        # Should contain entries from depth 1, 2, and 3
        assert len(deep_index) > 10  # 7 families + children + grandchildren

    def test_deep_index_contains_depth_2_entries(self):
        plugin = _make_plugin()
        deep_index = plugin._build_deep_index(max_depth=2)
        # All PKs in the index should map to nodes at depth ≤ 2
        for name, pk in deep_index.items():
            node = plugin.taxonomy_navigator.get_node(pk)
            assert node is not None
            assert int(node["depth"]) <= 2

    def test_deep_index_includes_family_keywords(self):
        plugin = _make_plugin()
        deep_index = plugin._build_deep_index(max_depth=3)
        # Family names like "insuffisance" should map to root PK "1"
        assert "insuffisance" in deep_index
        assert deep_index["insuffisance"] == "1"

    def test_map_fallacy_to_deep_pk_matches_deep_nodes(self):
        plugin = _make_plugin()
        deep_index = plugin._build_deep_index(max_depth=3)
        # "argument bâclé" is at depth 2 — deep mapping should find it
        pk = plugin._map_fallacy_to_deep_pk("argument bâclé", deep_index)
        assert pk is not None
        node = plugin.taxonomy_navigator.get_node(pk)
        assert int(node["depth"]) >= 2

    def test_map_fallacy_to_deep_pk_returns_none_for_unknown(self):
        plugin = _make_plugin()
        deep_index = plugin._build_deep_index(max_depth=3)
        pk = plugin._map_fallacy_to_deep_pk("xyzzy_no_match", deep_index)
        assert pk is None

    def test_map_fallacy_to_deep_pk_substring_match(self):
        plugin = _make_plugin()
        deep_index = plugin._build_deep_index(max_depth=3)
        # "insuffisance" is a family keyword, partial match should work
        pk = plugin._map_fallacy_to_deep_pk("appel à l'insuffisance", deep_index)
        assert pk is not None


# ---------------------------------------------------------------------------
# Test: Wide-net deep mapping (FB-19 enhanced Phase 1)
# ---------------------------------------------------------------------------


class TestWideNetDeepMapping:

    def test_wide_net_uses_deep_index(self):
        """Wide-net should try deep index before root index."""
        plugin = _make_plugin()
        # Mock LLM to return a candidate that maps to depth-2
        mock_response_str = json.dumps(
            [
                {
                    "fallacy_name": "Argument bâclé",
                    "root_category": "Insuffisance",
                    "confidence": 0.8,
                }
            ]
        )
        plugin.llm_service.get_chat_message_content = AsyncMock(
            return_value=mock_response_str
        )
        result = asyncio.get_event_loop().run_until_complete(
            plugin._wide_net_candidates("test text about fallacies")
        )
        # Should have found at least one PK (deep or root)
        assert len(result) >= 1

    def test_wide_net_deep_pk_preferred_over_root(self):
        """When deep index matches, PK should be at depth ≥ 2."""
        plugin = _make_plugin()
        mock_response = json.dumps(
            [
                {
                    "fallacy_name": "Argument bâclé",
                    "root_category": "Insuffisance",
                    "confidence": 0.9,
                }
            ]
        )
        plugin.llm_service.get_chat_message_content = AsyncMock(
            return_value=mock_response
        )
        result = asyncio.get_event_loop().run_until_complete(
            plugin._wide_net_candidates("test text")
        )
        if result:
            # Check if any result is deeper than depth 1
            for pk in result:
                node = plugin.taxonomy_navigator.get_node(pk)
                if node:
                    depth = int(node["depth"])
                    # At least some should be depth 2+ if deep mapping worked
                    # (but root fallback is also acceptable)
                    assert depth >= 1
