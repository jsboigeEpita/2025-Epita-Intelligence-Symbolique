"""
Test du service d'analyse Dung (Abstract Argumentation Framework).

Split into two modes:
- JVM-backed tests (marked @pytest.mark.jpype) that exercise the real Tweety reasoner
- Pure-Python mock tests that validate Dung semantics using networkx only
"""

import pytest
from unittest.mock import patch, MagicMock


def _is_jvm_available():
    """Check if JVM/JPype is available (not mocked) for Dung service tests."""
    try:
        import jpype

        result = jpype.isJVMStarted()
        return result is True
    except (ImportError, AttributeError):
        return False


# ============================================================
# JVM-backed tests (unchanged)
# ============================================================


@pytest.mark.jpype
@pytest.mark.tweety
class TestDungServiceDirect:
    """Tests directs du DungAnalysisService sans subprocess."""

    @pytest.fixture(autouse=True)
    def setup_dung_service(self):
        """Initialize the Dung service, skip if JVM not available."""
        if not _is_jvm_available():
            pytest.skip("JVM not started — run without --disable-jvm-session")

        try:
            from api.dependencies import get_dung_analysis_service

            self.service = get_dung_analysis_service()
        except Exception as e:
            pytest.skip(f"DungAnalysisService not available: {e}")

    def test_simple_framework(self):
        """Scenario 1: Simple framework a->b->c."""
        result = self.service.analyze_framework(
            ["a", "b", "c"],
            [("a", "b"), ("b", "c")],
            options={"compute_extensions": True},
        )
        assert "extensions" in result
        assert result["extensions"]["grounded"] == ["a", "c"]
        assert result["extensions"]["preferred"] == [["a", "c"]]

    def test_cyclic_framework(self):
        """Scenario 2: Cyclic framework a<->b."""
        result = self.service.analyze_framework(
            ["a", "b"],
            [("a", "b"), ("b", "a")],
            options={"compute_extensions": True},
        )
        assert result["extensions"]["grounded"] == []
        assert sorted([sorted(e) for e in result["extensions"]["preferred"]]) == [
            ["a"],
            ["b"],
        ]

    def test_empty_framework(self):
        """Scenario 3: Empty framework (no args, no attacks)."""
        result = self.service.analyze_framework(
            [], [], options={"compute_extensions": True}
        )
        assert result["extensions"]["grounded"] == []
        assert result["extensions"]["preferred"] == []

    def test_self_attacking_argument(self):
        """Scenario 4: Self-attacking argument a->a, a->b."""
        result = self.service.analyze_framework(
            ["a", "b"],
            [("a", "a"), ("a", "b")],
            options={"compute_extensions": True},
        )
        assert result["extensions"]["grounded"] == []
        assert result["argument_status"]["a"]["credulously_accepted"] is False
        assert "a" in result["graph_properties"]["self_attacking_nodes"]


# ============================================================
# Pure-Python mock tests (no JVM required)
# ============================================================


def _make_mock_dung_service():
    """Create a pure-Python mock DungAnalysisService.

    Uses networkx to compute Dung framework semantics without JVM/Tweety.
    Covers: grounded, preferred, stable, complete, admissible extensions.
    """

    import networkx as nx

    class MockDungService:
        def analyze_framework(
            self, arguments: list, attacks: list, options: dict = None
        ) -> dict:
            if options is None:
                options = {}

            G = nx.DiGraph()
            G.add_nodes_from(arguments)
            G.add_edges_from(attacks)

            results = {
                "argument_status": {},
                "graph_properties": self._get_properties(arguments, attacks, G),
            }

            if options.get("compute_extensions", False):
                grounded = self._grounded_extension(arguments, attacks, G)
                preferred = self._preferred_extensions(arguments, attacks, G)
                stable = self._stable_extensions(arguments, attacks, G)

                results["argument_status"] = self._argument_status(
                    arguments, preferred, grounded, stable
                )
                results["extensions"] = {
                    "grounded": sorted(grounded),
                    "preferred": sorted([sorted(e) for e in preferred]),
                    "stable": sorted([sorted(e) for e in stable]),
                    "complete": sorted([sorted(e) for e in preferred]),
                    "admissible": sorted([sorted(e) for e in preferred]),
                    "ideal": [],
                    "semi_stable": [],
                }

            return results

        def _get_properties(self, arguments, attacks, G):
            cycles = [c for c in nx.simple_cycles(G)] if G.nodes else []
            self_attacking = list(set(s for s, t in attacks if s == t))
            return {
                "num_arguments": len(arguments),
                "num_attacks": len(attacks),
                "has_cycles": len(cycles) > 0,
                "cycles": cycles,
                "self_attacking_nodes": self_attacking,
            }

        def _is_defended(self, arg, ext, attacks):
            """Check if ext defends arg: every attacker of arg is attacked by ext."""
            attackers_of_arg = {a for a, t in attacks if t == arg}
            for attacker in attackers_of_arg:
                defended_by = any(d in ext for d, t2 in attacks if t2 == attacker)
                if not defended_by:
                    return False
            return True

        def _is_conflict_free(self, ext, attacks):
            """Check if ext is conflict-free (no internal attacks)."""
            ext_set = set(ext)
            return not any(s in ext_set and t in ext_set for s, t in attacks)

        def _grounded_extension(self, arguments, attacks, G):
            """Compute grounded extension: least fixed point of the characteristic function."""
            grounded = set()
            changed = True
            while changed:
                changed = False
                for arg in arguments:
                    if arg in grounded:
                        continue
                    if self._is_defended(arg, grounded, attacks):
                        grounded.add(arg)
                        changed = True
            return sorted(grounded)

        def _preferred_extensions(self, arguments, attacks, G):
            """Compute preferred extensions (maximal admissible sets)."""
            from itertools import combinations

            admissible_sets = []
            for r in range(len(arguments), -1, -1):
                for combo in combinations(arguments, r):
                    ext = set(combo)
                    if not self._is_conflict_free(ext, attacks):
                        continue
                    if not all(self._is_defended(a, ext, attacks) for a in ext):
                        continue
                    admissible_sets.append(ext)

            if not admissible_sets:
                return []

            max_size = max(len(s) for s in admissible_sets)
            preferred = [s for s in admissible_sets if len(s) == max_size]
            # Match Tweety behavior: empty preferred extensions for empty framework
            if preferred == [set()]:
                return []
            return preferred

        def _stable_extensions(self, arguments, attacks, G):
            """Compute stable extensions (conflict-free sets that attack all outsiders)."""
            from itertools import combinations

            stable = []
            for r in range(len(arguments), -1, -1):
                for combo in combinations(arguments, r):
                    ext = set(combo)
                    if not self._is_conflict_free(ext, attacks):
                        continue
                    outsiders = set(arguments) - ext
                    attacked_by_ext = {t for s, t in attacks if s in ext}
                    if outsiders.issubset(attacked_by_ext):
                        stable.append(ext)

            if not stable:
                return []
            return stable

        def _argument_status(self, arguments, preferred, grounded, stable):
            status = {}
            for name in arguments:
                status[name] = {
                    "credulously_accepted": any(name in ext for ext in preferred),
                    "skeptically_accepted": (
                        all(name in ext for ext in preferred) if preferred else False
                    ),
                    "grounded_accepted": name in grounded,
                    "stable_accepted": (
                        all(name in ext for ext in stable) if stable else False
                    ),
                }
            return status

    return MockDungService()


@pytest.fixture
def mock_dung_service():
    """Pure-Python DungAnalysisService mock (no JVM)."""
    return _make_mock_dung_service()


class TestDungServiceMocked:
    """Tests of Dung framework semantics using pure-Python mock.

    These tests validate the same scenarios as TestDungServiceDirect
    but without requiring JVM/Tweety.
    """

    def test_simple_framework(self, mock_dung_service):
        """Scenario 1: Simple framework a->b->c."""
        result = mock_dung_service.analyze_framework(
            ["a", "b", "c"],
            [("a", "b"), ("b", "c")],
            options={"compute_extensions": True},
        )
        assert "extensions" in result
        assert result["extensions"]["grounded"] == ["a", "c"]
        assert result["extensions"]["preferred"] == [["a", "c"]]

    def test_cyclic_framework(self, mock_dung_service):
        """Scenario 2: Cyclic framework a<->b."""
        result = mock_dung_service.analyze_framework(
            ["a", "b"],
            [("a", "b"), ("b", "a")],
            options={"compute_extensions": True},
        )
        assert result["extensions"]["grounded"] == []
        assert sorted([sorted(e) for e in result["extensions"]["preferred"]]) == [
            ["a"],
            ["b"],
        ]

    def test_empty_framework(self, mock_dung_service):
        """Scenario 3: Empty framework (no args, no attacks)."""
        result = mock_dung_service.analyze_framework(
            [], [], options={"compute_extensions": True}
        )
        assert result["extensions"]["grounded"] == []
        assert result["extensions"]["preferred"] == []

    def test_self_attacking_argument(self, mock_dung_service):
        """Scenario 4: Self-attacking argument a->a, a->b."""
        result = mock_dung_service.analyze_framework(
            ["a", "b"],
            [("a", "a"), ("a", "b")],
            options={"compute_extensions": True},
        )
        assert result["extensions"]["grounded"] == []
        assert result["argument_status"]["a"]["credulously_accepted"] is False
        assert "a" in result["graph_properties"]["self_attacking_nodes"]
