"""
Tests for JTMS core module (integrated from 1.4.1-JTMS).

Tests validate:
- Module import without errors
- Belief creation and truth value management
- Justification propagation
- Non-monotonic SCC detection
- JTMS explain and visualize APIs
- CapabilityRegistry registration
"""

import pytest


class TestJTMSImport:
    """Test that the JTMS core module imports correctly."""

    def test_import_from_package(self):
        """JTMS classes importable from services.jtms package."""
        from argumentation_analysis.services.jtms import Belief, Justification, JTMS

        assert Belief is not None
        assert Justification is not None
        assert JTMS is not None

    def test_import_from_core(self):
        """JTMS classes importable from jtms_core directly."""
        from argumentation_analysis.services.jtms.jtms_core import (
            Belief,
            Justification,
            JTMS,
        )

        assert Belief is not None
        assert Justification is not None
        assert JTMS is not None

    def test_jtms_service_import(self):
        """jtms_service.py imports JTMS from the new location (no sys.path hack)."""
        from argumentation_analysis.services.jtms_service import JTMSService

        assert JTMSService is not None


class TestBeliefBasics:
    """Test Belief creation and truth values."""

    def test_belief_creation(self):
        """Belief starts with name and None truth value."""
        from argumentation_analysis.services.jtms import Belief

        b = Belief("test")
        assert b.name == "test"
        assert b.valid is None
        assert b.non_monotonic is False

    def test_belief_str_unknown(self):
        """Belief string representation for unknown state."""
        from argumentation_analysis.services.jtms import Belief

        b = Belief("X")
        assert "UNKNOWN" in str(b)

    def test_belief_str_valid(self):
        """Belief string representation for valid state."""
        from argumentation_analysis.services.jtms import Belief

        b = Belief("X")
        b.valid = True
        assert "VALID" in str(b)

    def test_belief_str_invalid(self):
        """Belief string representation for invalid state."""
        from argumentation_analysis.services.jtms import Belief

        b = Belief("X")
        b.valid = False
        assert "INVALID" in str(b)

    def test_belief_repr(self):
        """Belief repr returns name."""
        from argumentation_analysis.services.jtms import Belief

        b = Belief("mybelief")
        assert repr(b) == "mybelief"


class TestJTMSOperations:
    """Test JTMS add/remove/justify operations."""

    def test_add_belief(self):
        """Adding a belief registers it."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        assert "A" in jtms.beliefs

    def test_add_duplicate_belief(self):
        """Adding same belief twice does not create duplicates."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("A")
        assert len(jtms.beliefs) == 1

    def test_remove_belief(self):
        """Removing a belief removes it from the system."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.remove_belief("A")
        assert "A" not in jtms.beliefs

    def test_remove_unknown_belief_raises(self):
        """Removing a non-existent belief raises KeyError."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        with pytest.raises(KeyError):
            jtms.remove_belief("nonexistent")

    def test_set_belief_validity(self):
        """Setting truth value works."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.set_belief_validity("A", True)
        assert jtms.beliefs["A"].valid is True

    def test_set_unknown_belief_raises(self):
        """Setting validity on unknown belief raises KeyError."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        with pytest.raises(KeyError):
            jtms.set_belief_validity("X", True)


class TestJustificationPropagation:
    """Test justification-based truth propagation."""

    def test_simple_justification(self):
        """A valid premise justifies its conclusion."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.set_belief_validity("A", True)
        jtms.add_justification(["A"], [], "B")
        assert jtms.beliefs["B"].valid is True

    def test_justification_with_invalid_premise(self):
        """Unvalidated premise does not justify conclusion."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        # A is None (unknown), not True
        jtms.add_justification(["A"], [], "B")
        assert jtms.beliefs["B"].valid is None

    def test_justification_with_out_list(self):
        """Out-list blocks justification when those beliefs are valid."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("C")
        jtms.add_belief("B")
        jtms.set_belief_validity("A", True)
        jtms.set_belief_validity("C", True)
        # B justified by A unless C is valid
        jtms.add_justification(["A"], ["C"], "B")
        assert jtms.beliefs["B"].valid is None

    def test_chain_propagation(self):
        """Truth propagates through a chain A→B→C."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.add_belief("C")
        jtms.add_justification(["A"], [], "B")
        jtms.add_justification(["B"], [], "C")
        jtms.set_belief_validity("A", True)
        assert jtms.beliefs["B"].valid is True
        assert jtms.beliefs["C"].valid is True

    def test_retraction(self):
        """Retracting a premise retracts downstream beliefs."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.set_belief_validity("A", True)
        jtms.add_justification(["A"], [], "B")
        assert jtms.beliefs["B"].valid is True
        jtms.set_belief_validity("A", None)
        assert jtms.beliefs["B"].valid is None

    def test_auto_create_beliefs_nonstrict(self):
        """Non-strict mode auto-creates beliefs in justifications."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS(strict=False)
        jtms.add_justification(["X"], [], "Y")
        assert "X" in jtms.beliefs
        assert "Y" in jtms.beliefs

    def test_strict_mode_raises(self):
        """Strict mode raises on unknown beliefs in justifications."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS(strict=True)
        with pytest.raises(KeyError):
            jtms.add_justification(["unknown"], [], "target")


class TestNonMonotonic:
    """Test SCC-based non-monotonic detection."""

    def test_circular_dependency_marks_non_monotonic(self):
        """Circular justification A→B→A marks beliefs as non-monotonic."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.set_belief_validity("A", True)
        jtms.add_justification(["A"], [], "B")
        jtms.add_justification(["B"], [], "A")
        # Both should be non-monotonic due to SCC
        assert jtms.beliefs["A"].non_monotonic is True
        assert jtms.beliefs["B"].non_monotonic is True

    def test_non_circular_not_non_monotonic(self):
        """Linear chain does not mark beliefs as non-monotonic."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.add_justification(["A"], [], "B")
        assert jtms.beliefs["A"].non_monotonic is False
        assert jtms.beliefs["B"].non_monotonic is False


class TestExplainAndVisualize:
    """Test explain and visualize APIs."""

    def test_explain_no_justification(self):
        """Explain belief with no justification."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        result = jtms.explain_belief("A")
        assert result == "No justification"

    def test_explain_with_justification(self):
        """Explain belief with a justification."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.set_belief_validity("A", True)
        jtms.add_justification(["A"], [], "B")
        result = jtms.explain_belief("B")
        assert "Justification" in result
        assert "IN:" in result
        assert "A" in result

    def test_explain_unknown_raises(self):
        """Explain unknown belief raises KeyError."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        with pytest.raises(KeyError):
            jtms.explain_belief("nonexistent")

    def test_show_no_error(self):
        """show() runs without error."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.set_belief_validity("A", True)
        jtms.show()  # Should not raise


class TestJTMSRegistration:
    """Test CapabilityRegistry integration."""

    def test_register_jtms_service(self):
        """JTMS registers in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.services.jtms import JTMS

        registry = CapabilityRegistry()
        registry.register_service(
            "jtms",
            JTMS,
            capabilities=["belief_maintenance", "non_monotonic_reasoning"],
        )
        services = registry.find_services_for_capability("belief_maintenance")
        assert len(services) == 1
        assert services[0].name == "jtms"

        all_caps = registry.get_all_capabilities()
        assert "belief_maintenance" in all_caps
        assert "non_monotonic_reasoning" in all_caps


# ── Tri-état à l'affichage (#2094 item 1) ──


class TestTriStateDisplay:
    """Une croyance de validité `None` (indéterminée) s'affiche « unknown »,
    jamais « invalid » — aligné sur `Belief.__str__` qui rend déjà UNKNOWN."""

    def test_unknown_premise_renders_unknown_not_invalid(self):
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        # A reste None (indéterminée) : B n'est ni justifiée ni réfutée
        jtms.add_justification(["A"], [], "B")

        # Contraste avec __str__, qui rend déjà UNKNOWN pour None
        assert "UNKNOWN" in str(jtms.beliefs["A"])
        result = jtms.explain_belief("B")
        assert "A (unknown)" in result
        assert "A (invalid)" not in result

    def test_unknown_out_premise_renders_unknown(self):
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("C")
        jtms.add_belief("B")
        jtms.set_belief_validity("A", True)
        # C (blocante) reste None
        jtms.add_justification(["A"], ["C"], "B")

        result = jtms.explain_belief("B")
        assert "C (unknown)" in result
        assert "C (invalid)" not in result

    def test_result_line_is_tri_state(self):
        """Prémisse indéterminée ⇒ justification « Unknown », pas « Invalid »."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.add_justification(["A"], [], "B")

        result = jtms.explain_belief("B")
        assert "Result: Unknown" in result
        assert "Result: Invalid" not in result

    def test_refuted_justification_still_renders_invalid(self):
        """Contrôle : une prémisse False reste « invalid » — le tri-état
        n'est pas un basculement global."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.set_belief_validity("A", False)
        jtms.add_justification(["A"], [], "B")

        result = jtms.explain_belief("B")
        assert "A (invalid)" in result
        assert "Result: Invalid" in result

    def test_satisfied_justification_still_renders_valid(self):
        """Contrôle : le cas binaire valide reste « valid »/« Valid »."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.set_belief_validity("A", True)
        jtms.add_justification(["A"], [], "B")

        result = jtms.explain_belief("B")
        assert "A (valid)" in result
        assert "Result: Valid" in result

    def test_visualize_colors_unknown_grey(self, monkeypatch, tmp_path):
        """`None` rendait « rouge » (invalid) dans la visualisation — même
        défaut d'affichage que explain_belief, même correctif tri-état."""
        import argumentation_analysis.services.jtms.jtms_core as mod
        from argumentation_analysis.services.jtms import JTMS

        if not mod._HAS_PYVIS:
            pytest.skip("pyvis not installed")

        nodes = {}

        class FakeNet:
            def __init__(self, *args, **kwargs):
                pass

            def barnes_hut(self):
                pass

            def add_node(self, name, **kwargs):
                nodes[name] = kwargs

            def add_edge(self, *args, **kwargs):
                pass

            def write_html(self, path):
                pass

        monkeypatch.setattr(mod, "Network", FakeNet)

        jtms = JTMS()
        jtms.add_belief("u")  # None
        jtms.add_belief("v")  # True
        jtms.add_belief("f")  # False
        jtms.set_belief_validity("v", True)
        jtms.set_belief_validity("f", False)
        jtms.visualize(str(tmp_path / "graph.html"))

        assert nodes["u"]["color"] == "grey"
        assert nodes["v"]["color"] == "green"
        assert nodes["f"]["color"] == "red"


# ── Démontage complet au remove_belief (#2094 item 2) ──


class TestRemoveBeliefTeardown:
    """`remove_belief` détache la justification dans les DEUX sens : celles qui
    concluaient vers la croyance supprimée quittent les `implications` des
    prémisses, et celles dont la croyance supprimée était prémisse quittent les
    `implications` des co-prémisses."""

    def test_concluding_justifications_leave_premise_implications(self):
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_justification(["A", "B"], [], "C")
        assert any(j.conclusion.name == "C" for j in jtms.beliefs["A"].implications)

        jtms.remove_belief("C")

        for premise in ("A", "B"):
            dangling = [
                j
                for j in jtms.beliefs[premise].implications
                if j.conclusion.name == "C"
            ]
            assert (
                not dangling
            ), f"{premise} keeps {len(dangling)} dangling justification(s)"

    def test_later_retraction_does_not_cascade_through_removed_belief(self):
        """Une propagation postérieure ne doit pas remettre la croyance
        supprimée dans `_retraction_trace` (DoD #2094)."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_justification(["A"], [], "C")
        jtms.set_belief_validity("A", True)
        assert jtms.beliefs["C"].valid is True

        jtms.enable_tracing()
        jtms.remove_belief("C")
        jtms.set_belief_validity("A", False)

        cascaded = [
            name for entry in jtms.get_retraction_chain() for name in entry["cascaded"]
        ]
        assert "C" not in cascaded

    def test_co_premise_implications_detached_when_premise_removed(self):
        """Retirer une prémisse démonte la règle : la conclusion la perd ET la
        co-prémisse ne conserve pas de référence vers elle."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_justification(["A", "B"], [], "D")

        jtms.remove_belief("A")

        assert not jtms.beliefs["D"].justifications
        assert not jtms.beliefs["B"].implications

    def test_removed_belief_as_premise_still_cleans_conclusion(self):
        """Contrôle : le comportement déjà correct (la croyance retirée comme
        prémisse ⇒ la conclusion perd la règle) survit au démontage symétrique."""
        from argumentation_analysis.services.jtms import JTMS

        jtms = JTMS()
        jtms.add_justification(["A"], [], "D")
        jtms.set_belief_validity("A", True)
        assert jtms.beliefs["D"].valid is True

        jtms.remove_belief("A")

        assert not jtms.beliefs["D"].justifications
        jtms.beliefs["D"].compute_truth_statement()
        assert jtms.beliefs["D"].valid is None
