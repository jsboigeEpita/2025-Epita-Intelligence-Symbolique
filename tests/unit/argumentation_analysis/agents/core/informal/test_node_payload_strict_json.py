"""The informal plugin's node payloads are strict JSON, and one children rule serves both tools.

``explore_fallacy_hierarchy`` and ``get_fallacy_details`` built each node
summary with ``row.get(col, "")``. The default only fires when the column is
absent: an empty cell returns ``NaN``, and ``json.dumps`` writes it as the bare
token ``NaN``, which is not JSON (RFC 8259). On ``main`` ``475b2d78``, 1396 of
the 1408 explore payloads and 1368 of the 1408 details payloads carried it.

The two tools also derived a node's children from two copies of the same
cascade (#2345). The consistency test below holds them to one answer.
"""

import json

import pytest
from semantic_kernel import Kernel

from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin,
)


def _strict(raw: str):
    """Parse as RFC 8259 JSON: ``NaN`` / ``Infinity`` are refused."""

    def refuse(token):
        raise ValueError(f"non-JSON constant {token}")

    return json.loads(raw, parse_constant=refuse)


@pytest.fixture(scope="module")
def plugin() -> InformalAnalysisPlugin:
    return InformalAnalysisPlugin(kernel=Kernel(), taxonomy_file_path=None)


@pytest.fixture(scope="module")
def pks(plugin):
    pks = [int(pk) for pk in plugin._get_taxonomy_dataframe().index]
    assert len(pks) > 1000, "the population is the real taxonomy"
    return pks


def test_every_explore_payload_is_strict_json(plugin, pks):
    """Born red on ``main``: 1396 of 1408."""
    bad = []
    for pk in pks:
        try:
            _strict(plugin.explore_fallacy_hierarchy(str(pk)))
        except ValueError:
            bad.append(pk)
    assert not bad, f"{len(bad)} explore payloads are not strict JSON: {bad[:10]}"


def test_every_details_payload_is_strict_json(plugin, pks):
    """Born red on ``main``: 1368 of 1408."""
    bad = []
    for pk in pks:
        try:
            _strict(plugin.get_fallacy_details(str(pk)))
        except ValueError:
            bad.append(pk)
    assert not bad, f"{len(bad)} details payloads are not strict JSON: {bad[:10]}"


def test_explore_and_details_name_the_same_children(plugin, pks):
    """One children rule: both tools list the same children for every node."""
    disagree = []
    for pk in pks:
        explored = _strict(plugin.explore_fallacy_hierarchy(str(pk)))
        details = _strict(plugin.get_fallacy_details(str(pk)))
        from_explore = {c["pk"] for c in explored["children"]}
        from_details = {c["pk"] for c in details.get("children", [])}
        if explored.get("children_truncated"):
            if not from_explore <= from_details:
                disagree.append(pk)
        elif from_explore != from_details:
            disagree.append(pk)
    assert not disagree, f"explore and details disagree on children for {disagree[:10]}"


def test_has_children_matches_the_childs_own_children(plugin):
    """The flag on a child is the child's own children count, seen from its node."""
    root = _strict(plugin.explore_fallacy_hierarchy("0"))
    assert len(root["children"]) == 7
    for child in root["children"]:
        own = _strict(plugin.explore_fallacy_hierarchy(str(child["pk"])))["children"]
        assert child["has_children"] is bool(own), child["pk"]


def test_a_node_without_vulgarised_name_reports_an_empty_string(plugin):
    df = plugin._get_taxonomy_dataframe()
    pk = int(df[df["nom_vulgarisé"].isna()].index[0])
    node = _strict(plugin.explore_fallacy_hierarchy(str(pk)))["current_node"]
    assert node["nom_vulgarise"] == ""
    assert node["description_courte"]
