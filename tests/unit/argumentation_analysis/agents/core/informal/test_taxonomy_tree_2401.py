"""#2401 — the taxonomy's parent relation, measured on the real CSV.

The Argumentum CSV encodes its tree in ``path``, with one exception the
``startswith(path + ".")`` child rule cannot see: the depth-1 nodes carry a
bare segment (``"1"``, ``"2"``, ...), not ``"0.1"``, and their parent is the
depth-0 root (``PK 0``, ``path "0"``). Measured on ``main`` ``f246e200``:

* ``_internal_explore_hierarchy(0)`` — the entry point the informal agent's
  prompt hands it — returned **0** children, and a first-child descent from
  there stopped at depth 0;
* every child's ``has_children`` was the literal ``False``;
* ``TaxonomyNavigator.get_children`` paired the prefix rule with
  ``depth == parent_depth + 1``, so the one row whose ``depth`` cell disagrees
  with its path (6 segments, depth 7) was unreachable from the roots the
  production funnel walks;
* ``TaxonomySophismDetector._get_parent_context`` took every path under
  ``parent + "."`` as a sibling: 2360 of the 5016 "siblings" it returned over
  the whole CSV were the node's own descendants or its nephews, and the
  depth-1 nodes got none.

The oracles here are computed from the CSV by plain string work, never by the
code under test, so an agreement cannot be tautological.
"""

import csv

import pandas as pd
import pytest

from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin,
)
from argumentation_analysis.agents.core.informal.taxonomy_sophism_detector import (
    TaxonomySophismDetector,
)
from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator
from argumentation_analysis.utils.taxonomy_loader import get_taxonomy_path


@pytest.fixture(scope="module")
def plugin():
    return InformalAnalysisPlugin()


@pytest.fixture(scope="module")
def df(plugin):
    frame = plugin._get_taxonomy_dataframe()
    assert len(frame) > 1000, "the real taxonomy must load (1408 rows measured)"
    return frame


@pytest.fixture(scope="module")
def rows():
    with open(get_taxonomy_path(), encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _depth(frame: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(frame["depth"], errors="coerce")


def _is_inner(frame: pd.DataFrame, path: str) -> bool:
    """Oracle: a node is inner iff some dotted path extends it, or it is the root."""
    paths = frame["path"].astype(str)
    if (_depth(frame[paths == path]) == 0).any():
        return bool((_depth(frame) == 1).any())
    return bool(paths.str.startswith(path + ".").any())


class TestExploreHierarchyFromTheRoot:
    def test_root_children_are_the_depth_1_nodes(self, plugin, df):
        result = plugin._internal_explore_hierarchy(0, df, max_children=0)
        got = {child["pk"] for child in result["children"]}
        expected = set(df.index[_depth(df) == 1])
        assert expected, "the CSV carries depth-1 nodes"
        assert got == expected

    def test_first_child_descent_from_the_root_reaches_depth_5(self, plugin, df):
        pk, deepest = 0, 0
        for _ in range(12):
            result = plugin._internal_explore_hierarchy(pk, df)
            assert result["error"] is None, result["error"]
            deepest = max(deepest, result["current_node"]["depth"])
            if not result["children"]:
                break
            pk = result["children"][0]["pk"]
        assert deepest >= 5, f"descent from the root stopped at depth {deepest}"


class TestHasChildrenIsComputed:
    @pytest.mark.parametrize("parent_depth", [0, 1, 2, 3, 4])
    def test_flag_agrees_with_the_csv(self, plugin, df, parent_depth):
        # every child of the first node at this depth, inner and leaf alike
        parent_pk = int(df.index[_depth(df) == parent_depth][0])
        children = plugin._internal_explore_hierarchy(parent_pk, df, max_children=0)[
            "children"
        ]
        assert children, f"PK {parent_pk} has children in the CSV"
        for child in children:
            path = str(df.loc[child["pk"], "path"])
            assert child["has_children"] is _is_inner(df, path), child["pk"]

    def test_a_leaf_reports_false_and_an_inner_node_true(self, plugin, df):
        paths = df["path"].astype(str)
        leaf_pk = next(
            int(pk) for pk, p in paths.items() if int(pk) != 0 and not _is_inner(df, p)
        )
        parent_path = str(df.loc[leaf_pk, "path"]).rsplit(".", 1)[0]
        parent_pk = int(df.index[paths == parent_path][0])
        grand_path = parent_path.rsplit(".", 1)[0] if "." in parent_path else "0"
        grand_pk = int(df.index[paths == grand_path][0])

        leaf_flags = {
            c["pk"]: c["has_children"]
            for c in plugin._internal_explore_hierarchy(parent_pk, df, max_children=0)[
                "children"
            ]
        }
        inner_flags = {
            c["pk"]: c["has_children"]
            for c in plugin._internal_explore_hierarchy(grand_pk, df, max_children=0)[
                "children"
            ]
        }
        assert leaf_flags[leaf_pk] is False
        assert inner_flags[parent_pk] is True


class TestNodeDetails:
    def test_root_details_list_the_depth_1_nodes(self, plugin, df):
        details = plugin._internal_get_node_details(0, df)
        got = {child["pk"] for child in details.get("children", [])}
        assert got == set(df.index[_depth(df) == 1])

    def test_a_depth_1_node_names_the_root_as_parent(self, plugin, df):
        pk = int(df.index[_depth(df) == 1][0])
        assert plugin._internal_get_node_details(pk, df)["parent"]["pk"] == 0


def _true_siblings(frame: pd.DataFrame, pk: int) -> set:
    """Oracle: same parent by string work — one more segment under the parent's
    path, or, for a bare-segment node, the other bare-segment non-root nodes."""
    paths = frame["path"].astype(str)
    path = paths[pk]
    if "." in path:
        parent = path.rsplit(".", 1)[0]
        tails = paths.str.slice(start=len(parent) + 1)
        same = paths.str.startswith(parent + ".") & ~tails.str.contains(
            ".", regex=False
        )
    else:
        same = ~paths.str.contains(".", regex=False) & (_depth(frame) != 0)
    return {int(k) for k in frame.index[same] if int(k) != pk}


@pytest.fixture(scope="module")
def detector():
    return TaxonomySophismDetector()


class TestSiblingsShareTheParent:
    def test_every_returned_sibling_shares_the_parent(self, detector):
        frame = detector._get_taxonomy_df()
        wrong = []
        for pk in frame.index:
            got = {
                s["taxonomy_key"]
                for s in detector._get_parent_context(int(pk))["siblings"]
            }
            wrong.extend((int(pk), s) for s in got - _true_siblings(frame, int(pk)))
        assert wrong == [], f"{len(wrong)} non-siblings returned, first: {wrong[:5]}"

    def test_a_depth_1_node_has_its_siblings(self, detector):
        frame = detector._get_taxonomy_df()
        pk = int(frame.index[_depth(frame) == 1][0])
        context = detector._get_parent_context(pk)
        expected = _true_siblings(frame, pk)
        assert len(expected) >= 5, "the CSV carries 7 depth-1 nodes"
        assert context["parent_path"] == "0"
        assert len(context["siblings"]) == 5

    def test_the_cap_keeps_as_many_as_there_are(self, detector):
        # the 5-sibling cap is kept; below it, every true sibling is returned
        frame = detector._get_taxonomy_df()
        short = next(
            int(pk)
            for pk in frame.index[_depth(frame) >= 2]
            if 0 < len(_true_siblings(frame, int(pk))) < 5
        )
        got = {
            s["taxonomy_key"] for s in detector._get_parent_context(short)["siblings"]
        }
        assert got == _true_siblings(frame, short)


class TestNavigatorReachesEveryNode:
    def test_every_node_is_reachable_from_the_depth_1_roots(self, rows):
        nav = TaxonomyNavigator(rows)
        seen, stack = set(), [r["PK"] for r in nav.get_root_nodes()]
        while stack:
            pk = stack.pop()
            if pk not in seen:
                seen.add(pk)
                stack.extend(c["PK"] for c in nav.get_children(pk))
        expected = {r["PK"] for r in rows if r["depth"] != "0"}
        assert expected - seen == set()

    def test_a_depth_1_node_has_the_root_as_parent(self, rows):
        nav = TaxonomyNavigator(rows)
        root_pk = next(r["PK"] for r in rows if r["depth"] == "0")
        pk = next(r["PK"] for r in rows if r["depth"] == "1")
        assert nav.get_parent(pk)["PK"] == root_pk
        assert nav.get_parent(root_pk) is None

    def test_the_root_lists_the_depth_1_nodes(self, rows):
        nav = TaxonomyNavigator(rows)
        root_pk = next(r["PK"] for r in rows if r["depth"] == "0")
        got = {c["PK"] for c in nav.get_children(root_pk)}
        assert got == {r["PK"] for r in rows if r["depth"] == "1"}


class TestParentPathFather:
    def test_dotted_path_drops_its_last_segment(self):
        from argumentation_analysis.utils.taxonomy_tree import taxonomy_parent_path

        assert taxonomy_parent_path("5.1.2", "0") == "5.1"

    def test_bare_segment_belongs_to_the_root(self):
        from argumentation_analysis.utils.taxonomy_tree import taxonomy_parent_path

        assert taxonomy_parent_path("3", "0") == "0"
        assert taxonomy_parent_path("0", "0") is None

    def test_without_a_root_row_a_bare_segment_is_a_top(self):
        # the shape of a taxonomy with no depth-0 row (test fixtures, subsets)
        from argumentation_analysis.utils.taxonomy_tree import taxonomy_parent_path

        assert taxonomy_parent_path("3", None) is None
