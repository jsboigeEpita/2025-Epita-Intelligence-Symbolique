"""
Test du service d'analyse Dung (Abstract Argumentation Framework).

Split into two modes:
- JVM-backed tests (marked @pytest.mark.jpype) that exercise the real Tweety reasoner
- Tests of the real ``DungAnalysisService`` with only its Java/Tweety boundary
  doubled (#2755): the extensions come from a scripted agent, and what the
  service computes itself (status, sorting, graph properties, options, the
  JVM refusal) runs for real without a JVM
"""

import sys
import types

import pytest


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
        """Initialize the Dung service, skip if JVM not available.

        #2526: once the JVM runs, a service that cannot be built is a failure.
        The former ``except Exception: pytest.skip`` turned the NameError of
        ``api/services.py`` into four skips for seven months.
        """
        if not _is_jvm_available():
            pytest.skip("JVM not started — run without --disable-jvm-session")

        from api.dependencies import get_dung_analysis_service

        self.service = get_dung_analysis_service()

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
# Real service, Java/Tweety boundary doubled (no JVM required)
# ============================================================


class _Argument:
    """Stand-in for org.tweetyproject.arg.dung.syntax.Argument."""

    def __init__(self, name):
        self._name = name

    def getName(self):
        return self._name

    def __str__(self):
        return self._name

    # JPype compares Java objects with equals(): same name, same argument.
    def __eq__(self, other):
        return isinstance(other, _Argument) and other._name == self._name

    def __hash__(self):
        return hash(self._name)


class _Attack:
    def __init__(self, attacker, attacked):
        self._attacker = attacker
        self._attacked = attacked

    def getAttacker(self):
        return self._attacker

    def getAttacked(self):
        return self._attacked


class _Theory:
    def __init__(self):
        self.nodes = []
        self.attacks = []

    def getNodes(self):
        return list(self.nodes)

    def getAttacks(self):
        return list(self.attacks)


def _scripted_agent(extensions):
    """An ``EnhancedDungAgent`` whose extensions are scripted.

    Computing extensions is Tweety's job and is covered by
    ``TestDungServiceDirect``; here the reasoner's answer is fixed so the
    service's own logic is what the assertions measure.
    """

    def _args(names):
        return [_Argument(name) for name in names]

    class ScriptedDungAgent:
        def __init__(self):
            self.af = _Theory()

        def add_argument(self, name):
            self.af.nodes.append(_Argument(name))

        def add_attack(self, source, target):
            self.af.attacks.append(_Attack(_Argument(source), _Argument(target)))

        def get_grounded_extension(self):
            return _args(extensions["grounded"])

        def get_preferred_extensions(self):
            return [_args(ext) for ext in extensions["preferred"]]

        def get_stable_extensions(self):
            return [_args(ext) for ext in extensions["stable"]]

        def get_complete_extensions(self):
            return [_args(ext) for ext in extensions["complete"]]

        def get_admissible_sets(self):
            return [_args(ext) for ext in extensions["admissible"]]

    return ScriptedDungAgent


_NO_EXTENSIONS = {
    "grounded": [],
    "preferred": [],
    "stable": [],
    "complete": [],
    "admissible": [],
}


@pytest.fixture
def java_boundary(monkeypatch):
    """Double jpype and the Tweety-backed agent; keep ``api.services`` real."""
    import jpype

    fake_agent_module = types.ModuleType("abs_arg_dung.enhanced_agent")
    fake_agent_module.EnhancedDungAgent = _scripted_agent(_NO_EXTENSIONS)
    monkeypatch.setitem(sys.modules, "abs_arg_dung.enhanced_agent", fake_agent_module)
    monkeypatch.setattr(jpype, "isJVMStarted", lambda: True)
    monkeypatch.setattr(jpype, "JClass", lambda name: name)
    return monkeypatch


def _service(extensions):
    from api.services import DungAnalysisService

    service = DungAnalysisService()
    service.agent_class = _scripted_agent(extensions)
    return service


class TestDungServiceBoundaryDoubled:
    """The four scenarios of TestDungServiceDirect, on the real service."""

    def test_refuses_without_a_jvm(self, java_boundary):
        import jpype

        from api.services import DungAnalysisService

        java_boundary.setattr(jpype, "isJVMStarted", lambda: False)
        with pytest.raises(RuntimeError, match="JVM"):
            DungAnalysisService()

    def test_simple_framework(self, java_boundary):
        """Scenario 1: a->b->c. The reasoner's answer comes unsorted."""
        service = _service(
            {
                "grounded": ["c", "a"],
                "preferred": [["a", "c"]],
                "stable": [["a", "c"]],
                "complete": [["a", "c"]],
                "admissible": [["a", "c"], [], ["a"]],
            }
        )
        result = service.analyze_framework(
            ["a", "b", "c"],
            [("a", "b"), ("b", "c")],
            options={"compute_extensions": True},
        )

        assert result["extensions"]["grounded"] == ["a", "c"]
        assert result["extensions"]["preferred"] == [["a", "c"]]
        assert result["extensions"]["admissible"] == [[], ["a"], ["a", "c"]]
        assert result["argument_status"]["a"] == {
            "credulously_accepted": True,
            "skeptically_accepted": True,
            "grounded_accepted": True,
            "stable_accepted": True,
        }
        assert result["argument_status"]["b"] == {
            "credulously_accepted": False,
            "skeptically_accepted": False,
            "grounded_accepted": False,
            "stable_accepted": False,
        }
        assert result["graph_properties"] == {
            "num_arguments": 3,
            "num_attacks": 2,
            "has_cycles": False,
            "cycles": [],
            "self_attacking_nodes": [],
        }

    def test_cyclic_framework(self, java_boundary):
        """Scenario 2: a<->b. Credulous, not skeptical."""
        service = _service(
            {
                "grounded": [],
                "preferred": [["b"], ["a"]],
                "stable": [["b"], ["a"]],
                "complete": [[], ["a"], ["b"]],
                "admissible": [[], ["a"], ["b"]],
            }
        )
        result = service.analyze_framework(
            ["a", "b"],
            [("a", "b"), ("b", "a")],
            options={"compute_extensions": True},
        )

        assert result["extensions"]["grounded"] == []
        assert result["extensions"]["preferred"] == [["a"], ["b"]]
        for name in ("a", "b"):
            assert result["argument_status"][name] == {
                "credulously_accepted": True,
                "skeptically_accepted": False,
                "grounded_accepted": False,
                "stable_accepted": False,
            }
        properties = result["graph_properties"]
        assert properties["has_cycles"] is True
        assert [sorted(cycle) for cycle in properties["cycles"]] == [["a", "b"]]

    def test_empty_framework(self, java_boundary):
        """Scenario 3: no arguments, no attacks."""
        service = _service(_NO_EXTENSIONS)
        result = service.analyze_framework([], [], options={"compute_extensions": True})

        assert result["extensions"]["grounded"] == []
        assert result["extensions"]["preferred"] == []
        assert result["argument_status"] == {}
        assert result["graph_properties"]["num_arguments"] == 0

    def test_self_attacking_argument(self, java_boundary):
        """Scenario 4: a->a, a->b. No stable extension to accept from."""
        service = _service(
            {
                "grounded": [],
                "preferred": [[]],
                "stable": [],
                "complete": [[]],
                "admissible": [[]],
            }
        )
        result = service.analyze_framework(
            ["a", "b"],
            [("a", "a"), ("a", "b")],
            options={"compute_extensions": True},
        )

        assert result["argument_status"]["a"] == {
            "credulously_accepted": False,
            "skeptically_accepted": False,
            "grounded_accepted": False,
            "stable_accepted": False,
        }
        assert result["graph_properties"]["self_attacking_nodes"] == ["a"]
        assert result["graph_properties"]["has_cycles"] is True

    def test_extensions_only_on_request(self, java_boundary):
        """Without ``compute_extensions`` the reasoner is not asked."""
        service = _service(
            {
                "grounded": ["a"],
                "preferred": [["a"]],
                "stable": [["a"]],
                "complete": [["a"]],
                "admissible": [["a"]],
            }
        )
        result = service.analyze_framework(["a"], [])

        assert "extensions" not in result
        assert result["argument_status"] == {}
        assert result["graph_properties"]["num_arguments"] == 1
