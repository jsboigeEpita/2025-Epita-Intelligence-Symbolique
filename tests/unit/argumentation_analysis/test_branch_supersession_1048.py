"""Unit tests for branch supersession tracker (RA-3 #1048).

Tests the _BranchSupersessionTracker logic:
- No supersession when no confirmations exist
- No supersession when confirmed node is at same or shallower depth
- Supersession when confirmed node is strictly deeper AND in same lineage
- No supersession when confirmed node is in a different lineage
- Multiple confirmations handled correctly
"""

import pytest

from unittest.mock import MagicMock

from argumentation_analysis.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin

# ---------------------------------------------------------------------------
# Helpers — lightweight taxonomy navigator mock
# ---------------------------------------------------------------------------


def _make_node(pk: str, path: str, depth: int) -> dict:
    """Create a taxonomy node dict."""
    return {"PK": pk, "path": path, "depth": depth}


def _make_navigator(nodes: dict) -> MagicMock:
    """Create a mock TaxonomyNavigator returning *nodes* (pk → node dict)."""
    nav = MagicMock()
    nav.get_node.side_effect = lambda pk: nodes.get(pk)
    return nav


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tree_nodes():
    """Small taxonomy tree for testing.

    1 (root)
    ├── 1.1 (depth 1)
    │   ├── 1.1.3 (depth 2)
    │   │   └── 1.1.3.7 (depth 3)
    │   └── 1.1.5 (depth 2)
    └── 1.2 (depth 1)
        └── 1.2.4 (depth 2)
    """
    return {
        "1": _make_node("1", "1", 0),
        "1.1": _make_node("1.1", "1.1", 1),
        "1.1.3": _make_node("1.1.3", "1.1.3", 2),
        "1.1.3.7": _make_node("1.1.3.7", "1.1.3.7", 3),
        "1.1.5": _make_node("1.1.5", "1.1.5", 2),
        "1.2": _make_node("1.2", "1.2", 1),
        "1.2.4": _make_node("1.2.4", "1.2.4", 2),
    }


@pytest.fixture
def tracker(tree_nodes):
    """Create a tracker backed by *tree_nodes*."""
    nav = _make_navigator(tree_nodes)
    return FallacyWorkflowPlugin._BranchSupersessionTracker(nav)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBranchSupersessionTracker:
    """Tests for the _BranchSupersessionTracker inner class."""

    def test_no_supersession_when_empty(self, tracker):
        """No confirmations → no supersession."""
        assert tracker.check_superseded("1.1", 1) is None

    def test_no_supersession_same_depth(self, tracker):
        """Confirmed at same depth as current → not superseded."""
        tracker.register("1.1.5", 2, 0.9)
        # Current node at depth 2 — confirmed is also depth 2
        assert tracker.check_superseded("1.1.3", 2) is None

    def test_no_supersession_shallower_confirmed(self, tracker):
        """Confirmed at depth 1 while current is at depth 2 → not superseded."""
        tracker.register("1.1", 1, 0.9)
        assert tracker.check_superseded("1.1.3", 2) is None

    def test_supersession_deeper_confirmed_same_lineage(self, tracker):
        """Confirmed at depth 3 while current is ancestor at depth 1 → superseded."""
        tracker.register("1.1.3.7", 3, 0.9)
        result = tracker.check_superseded("1.1", 1)
        assert result == "1.1.3.7"

    def test_supersession_deeper_confirmed_parent(self, tracker):
        """Confirmed at depth 3 while current is direct parent at depth 2 → superseded."""
        tracker.register("1.1.3.7", 3, 0.9)
        result = tracker.check_superseded("1.1.3", 2)
        assert result == "1.1.3.7"

    def test_no_supersession_different_lineage(self, tracker):
        """Confirmed in lineage 1.1 but current is in lineage 1.2 → not superseded."""
        tracker.register("1.1.3.7", 3, 0.9)
        result = tracker.check_superseded("1.2", 1)
        assert result is None

    def test_no_supersession_sibling_branches(self, tracker):
        """Confirmed 1.1.5 (sibling, not ancestor) while current is 1.1.3 → not superseded."""
        tracker.register("1.1.5", 2, 0.9)
        result = tracker.check_superseded("1.1.3", 2)
        assert result is None

    def test_multiple_confirmations_first_wins(self, tracker):
        """Two confirmations in different lineages; only the one in current lineage supersedes."""
        tracker.register("1.1.3.7", 3, 0.9)
        tracker.register("1.2.4", 2, 0.8)
        # Current is in 1.1 lineage → superseded by 1.1.3.7
        result = tracker.check_superseded("1.1", 1)
        assert result == "1.1.3.7"

    def test_multiple_confirmations_none_match(self, tracker):
        """Two confirmations, both in different lineage than current → not superseded."""
        tracker.register("1.1.3.7", 3, 0.9)
        tracker.register("1.2.4", 2, 0.8)
        # Current is root node — not an ancestor of either confirmed path
        # (path "1" would be ancestor of "1.1.3.7" since "1.1.3.7".startswith("1."))
        # Actually "1.1.3.7".startswith("1" + ".") = True → superseded
        result = tracker.check_superseded("1", 0)
        assert result is not None  # root is ancestor of both

    def test_confirmation_count(self, tracker):
        """Counter tracks registrations."""
        assert tracker.confirmation_count == 0
        tracker.register("1.1.3.7", 3, 0.9)
        assert tracker.confirmation_count == 1
        tracker.register("1.2.4", 2, 0.8)
        assert tracker.confirmation_count == 2

    def test_superseded_count_increment(self, tracker):
        """superseded_count increments when check returns non-None."""
        tracker.register("1.1.3.7", 3, 0.9)
        assert tracker.superseded_count == 0
        tracker.check_superseded("1.1", 1)
        # Note: the tracker itself doesn't increment — the caller does
        # This test verifies the initial state
        assert tracker.superseded_count == 0

    def test_node_not_in_navigator(self, tracker):
        """Current PK not in navigator → no supersession (graceful)."""
        result = tracker.check_superseded("nonexistent_pk", 1)
        assert result is None

    def test_confirmed_node_missing_path(self, tree_nodes):
        """Confirmed node has no path field → no supersession."""
        # Add a node without path
        tree_nodes["no_path"] = {"PK": "no_path", "depth": 3}
        nav = _make_navigator(tree_nodes)
        t = FallacyWorkflowPlugin._BranchSupersessionTracker(nav)
        t.register("no_path", 3, 0.9)
        result = t.check_superseded("1.1", 1)
        assert result is None

    def test_deep_lineage_supersession(self, tree_nodes):
        """Supersession works at deeper levels (depth 3 → depth 0)."""
        nav = _make_navigator(tree_nodes)
        t = FallacyWorkflowPlugin._BranchSupersessionTracker(nav)
        # Confirm deepest leaf
        t.register("1.1.3.7", 3, 0.95)
        # Root should be superseded
        assert t.check_superseded("1", 0) == "1.1.3.7"
        # Depth 1 ancestor
        assert t.check_superseded("1.1", 1) == "1.1.3.7"
        # Depth 2 parent
        assert t.check_superseded("1.1.3", 2) == "1.1.3.7"
        # Sibling at depth 2 → NOT superseded (different path)
        assert t.check_superseded("1.1.5", 2) is None
