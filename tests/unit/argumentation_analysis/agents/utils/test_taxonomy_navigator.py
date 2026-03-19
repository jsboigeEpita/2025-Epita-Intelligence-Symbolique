# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.utils.taxonomy_navigator
Covers TaxonomyNavigator class: node lookup, tree traversal, preview generation.
"""

import pytest
import json
from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_taxonomy_data():
    """A small taxonomy tree for testing."""
    return [
        {
            "PK": "1",
            "path": "1",
            "depth": "1",
            "nom_vulgarisé": "Logique",
            "text_fr": "Logique",
            "desc_fr": "La logique formelle",
        },
        {
            "PK": "1.1",
            "path": "1.1",
            "depth": "2",
            "nom_vulgarisé": "Déduction",
            "text_fr": "Déduction",
            "desc_fr": "Raisonnement déductif",
        },
        {
            "PK": "1.2",
            "path": "1.2",
            "depth": "2",
            "nom_vulgarisé": "Induction",
            "text_fr": "Induction",
            "desc_fr": "Raisonnement inductif",
        },
        {
            "PK": "1.1.1",
            "path": "1.1.1",
            "depth": "3",
            "nom_vulgarisé": "Modus Ponens",
            "text_fr": "Modus Ponens",
            "desc_fr": "Si P alors Q",
        },
        {
            "PK": "1.1.2",
            "path": "1.1.2",
            "depth": "3",
            "nom_vulgarisé": "Modus Tollens",
            "text_fr": "Modus Tollens",
            "desc_fr": "Si P alors Q, non Q",
        },
        {
            "PK": "2",
            "path": "2",
            "depth": "1",
            "nom_vulgarisé": "Rhétorique",
            "text_fr": "Rhétorique",
            "desc_fr": "L'art de la persuasion",
        },
        {
            "PK": "2.1",
            "path": "2.1",
            "depth": "2",
            "nom_vulgarisé": "Ethos",
            "text_fr": "Ethos",
            "desc_fr": "Appel à la crédibilité",
        },
    ]


@pytest.fixture
def navigator(sample_taxonomy_data):
    return TaxonomyNavigator(sample_taxonomy_data)


@pytest.fixture
def empty_navigator():
    return TaxonomyNavigator([])


@pytest.fixture
def none_navigator():
    return TaxonomyNavigator(None)


# ============================================================
# Initialization
# ============================================================


class TestTaxonomyNavigatorInit:
    def test_init_with_data(self, navigator, sample_taxonomy_data):
        assert len(navigator.taxonomy_data) == len(sample_taxonomy_data)

    def test_init_empty(self, empty_navigator):
        assert navigator is not None or empty_navigator is not None
        assert len(empty_navigator.taxonomy_data) == 0

    def test_init_none(self, none_navigator):
        assert len(none_navigator.taxonomy_data) == 0

    def test_node_map_built(self, navigator):
        assert "1" in navigator.node_map
        assert "1.1" in navigator.node_map
        assert "2" in navigator.node_map

    def test_path_map_built(self, navigator):
        assert "1" in navigator.path_map
        assert "1.1.1" in navigator.path_map
        assert "2.1" in navigator.path_map

    def test_node_without_pk(self):
        data = [{"path": "x", "depth": "1", "nom_vulgarisé": "No PK"}]
        nav = TaxonomyNavigator(data)
        assert len(nav.node_map) == 0
        assert "x" in nav.path_map

    def test_node_without_path(self):
        data = [{"PK": "x", "depth": "1", "nom_vulgarisé": "No path"}]
        nav = TaxonomyNavigator(data)
        assert "x" in nav.node_map
        assert len(nav.path_map) == 0


# ============================================================
# get_node
# ============================================================


class TestGetNode:
    def test_existing_node(self, navigator):
        node = navigator.get_node("1")
        assert node is not None
        assert node["PK"] == "1"
        assert node["nom_vulgarisé"] == "Logique"

    def test_nested_node(self, navigator):
        node = navigator.get_node("1.1.1")
        assert node is not None
        assert node["nom_vulgarisé"] == "Modus Ponens"

    def test_nonexistent_node(self, navigator):
        assert navigator.get_node("999") is None

    def test_empty_navigator(self, empty_navigator):
        assert empty_navigator.get_node("1") is None


# ============================================================
# get_node_by_path
# ============================================================


class TestGetNodeByPath:
    def test_existing_path(self, navigator):
        node = navigator.get_node_by_path("1.1")
        assert node is not None
        assert node["PK"] == "1.1"

    def test_nonexistent_path(self, navigator):
        assert navigator.get_node_by_path("999.999") is None

    def test_root_path(self, navigator):
        node = navigator.get_node_by_path("2")
        assert node is not None
        assert node["nom_vulgarisé"] == "Rhétorique"


# ============================================================
# get_root_nodes
# ============================================================


class TestGetRootNodes:
    def test_root_nodes(self, navigator):
        roots = navigator.get_root_nodes()
        assert len(roots) == 2
        pks = {r["PK"] for r in roots}
        assert pks == {"1", "2"}

    def test_root_nodes_empty(self, empty_navigator):
        assert empty_navigator.get_root_nodes() == []

    def test_root_nodes_no_depth_1(self):
        data = [{"PK": "a", "path": "a", "depth": "2", "nom_vulgarisé": "Leaf"}]
        nav = TaxonomyNavigator(data)
        assert nav.get_root_nodes() == []

    def test_root_nodes_invalid_depth(self):
        data = [{"PK": "a", "path": "a", "depth": "invalid"}]
        nav = TaxonomyNavigator(data)
        assert nav.get_root_nodes() == []


# ============================================================
# get_children
# ============================================================


class TestGetChildren:
    def test_children_of_root(self, navigator):
        children = navigator.get_children("1")
        assert len(children) == 2
        pks = {c["PK"] for c in children}
        assert pks == {"1.1", "1.2"}

    def test_children_of_internal_node(self, navigator):
        children = navigator.get_children("1.1")
        assert len(children) == 2
        pks = {c["PK"] for c in children}
        assert pks == {"1.1.1", "1.1.2"}

    def test_children_of_leaf(self, navigator):
        children = navigator.get_children("1.1.1")
        assert children == []

    def test_children_of_nonexistent(self, navigator):
        assert navigator.get_children("999") == []

    def test_children_second_root(self, navigator):
        children = navigator.get_children("2")
        assert len(children) == 1
        assert children[0]["PK"] == "2.1"


# ============================================================
# get_parent
# ============================================================


class TestGetParent:
    def test_parent_of_child(self, navigator):
        parent = navigator.get_parent("1.1")
        assert parent is not None
        assert parent["PK"] == "1"

    def test_parent_of_grandchild(self, navigator):
        parent = navigator.get_parent("1.1.1")
        assert parent is not None
        assert parent["PK"] == "1.1"

    def test_parent_of_root(self, navigator):
        assert navigator.get_parent("1") is None

    def test_parent_of_nonexistent(self, navigator):
        assert navigator.get_parent("999") is None


# ============================================================
# is_leaf
# ============================================================


class TestIsLeaf:
    def test_leaf_node(self, navigator):
        assert navigator.is_leaf("1.1.1") is True
        assert navigator.is_leaf("1.1.2") is True
        assert navigator.is_leaf("2.1") is True

    def test_internal_node(self, navigator):
        assert navigator.is_leaf("1") is False
        assert navigator.is_leaf("1.1") is False
        assert navigator.is_leaf("2") is False

    def test_nonexistent_node_is_leaf(self, navigator):
        # No children found → returns True (empty list is truthy for `not`)
        assert navigator.is_leaf("999") is True


# ============================================================
# get_branch_as_str
# ============================================================


class TestGetBranchAsStr:
    def test_branch_with_children(self, navigator):
        result = navigator.get_branch_as_str("1")
        assert "Logique" in result
        assert "Déduction" in result
        assert "Induction" in result

    def test_branch_leaf(self, navigator):
        result = navigator.get_branch_as_str("1.1.1")
        assert "Modus Ponens" in result

    def test_branch_nonexistent(self, navigator):
        assert navigator.get_branch_as_str("999") == "Node not found."

    def test_branch_contains_ids(self, navigator):
        result = navigator.get_branch_as_str("1.1")
        assert "ID: 1.1" in result
        assert "ID: 1.1.1" in result

    def test_branch_indentation(self, navigator):
        result = navigator.get_branch_as_str("1")
        lines = result.split("\n")
        # Root should not have leading spaces
        assert lines[0].startswith("- ")
        # Children should be indented
        assert lines[1].startswith("  - ")


# ============================================================
# get_taxonomy_preview
# ============================================================


class TestGetTaxonomyPreview:
    def test_preview_depth_1(self, navigator):
        preview = navigator.get_taxonomy_preview(depth=1)
        assert "Logique" in preview
        assert "Rhétorique" in preview
        # Depth 2 children should NOT appear
        assert "Déduction" not in preview

    def test_preview_depth_2(self, navigator):
        preview = navigator.get_taxonomy_preview(depth=2)
        assert "Logique" in preview
        assert "Déduction" in preview
        assert "Induction" in preview
        assert "Ethos" in preview
        # Depth 3 should NOT appear
        assert "Modus Ponens" not in preview

    def test_preview_depth_3(self, navigator):
        preview = navigator.get_taxonomy_preview(depth=3)
        assert "Modus Ponens" in preview
        assert "Modus Tollens" in preview

    def test_preview_with_details(self, navigator):
        preview = navigator.get_taxonomy_preview(depth=1, details=True, language="fr")
        assert "ID:" in preview

    def test_preview_without_details(self, navigator):
        preview = navigator.get_taxonomy_preview(depth=1, details=False, language="fr")
        assert "ID:" not in preview

    def test_preview_empty(self, empty_navigator):
        assert (
            empty_navigator.get_taxonomy_preview() == "Taxonomy data is not available."
        )


# ============================================================
# get_taxonomy_as_json
# ============================================================


class TestGetTaxonomyAsJson:
    def test_json_output(self, navigator, sample_taxonomy_data):
        result = navigator.get_taxonomy_as_json()
        parsed = json.loads(result)
        assert len(parsed) == len(sample_taxonomy_data)
        assert parsed[0]["PK"] == "1"

    def test_json_empty(self, empty_navigator):
        assert empty_navigator.get_taxonomy_as_json() == "[]"

    def test_json_valid_format(self, navigator):
        result = navigator.get_taxonomy_as_json()
        # Should not raise
        parsed = json.loads(result)
        assert isinstance(parsed, list)
