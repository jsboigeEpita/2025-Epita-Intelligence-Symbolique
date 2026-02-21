"""
Test du service d'analyse Dung (Abstract Argumentation Framework).

Converti depuis un test subprocess (qui bloquait) vers un test direct
in-process utilisant get_dung_analysis_service() avec la JVM disponible.
"""
import pytest
import os


def _is_jvm_available():
    """Check if JVM/JPype is available (not mocked) for Dung service tests."""
    try:
        import jpype
        # When --disable-jvm-session mocks jpype, isJVMStarted returns a MagicMock (truthy)
        result = jpype.isJVMStarted()
        return result is True  # Strict check: MagicMock is not True
    except (ImportError, AttributeError):
        return False


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
        """Scenario 1: Simple framework a→b→c."""
        result = self.service.analyze_framework(
            ["a", "b", "c"],
            [("a", "b"), ("b", "c")],
            options={"compute_extensions": True},
        )
        assert "extensions" in result
        assert result["extensions"]["grounded"] == ["a", "c"]
        assert result["extensions"]["preferred"] == [["a", "c"]]

    def test_cyclic_framework(self):
        """Scenario 2: Cyclic framework a↔b."""
        result = self.service.analyze_framework(
            ["a", "b"],
            [("a", "b"), ("b", "a")],
            options={"compute_extensions": True},
        )
        assert result["extensions"]["grounded"] == []
        assert sorted([sorted(e) for e in result["extensions"]["preferred"]]) == [["a"], ["b"]]

    def test_empty_framework(self):
        """Scenario 3: Empty framework (no args, no attacks)."""
        result = self.service.analyze_framework(
            [], [], options={"compute_extensions": True}
        )
        assert result["extensions"]["grounded"] == []
        assert result["extensions"]["preferred"] == []

    def test_self_attacking_argument(self):
        """Scenario 4: Self-attacking argument a→a, a→b."""
        result = self.service.analyze_framework(
            ["a", "b"],
            [("a", "a"), ("a", "b")],
            options={"compute_extensions": True},
        )
        # Grounded extension is empty: a self-attacks (out), b is attacked by a
        # but not defended by anyone, so b is also out of the grounded extension.
        assert result["extensions"]["grounded"] == []
        assert result["argument_status"]["a"]["credulously_accepted"] is False
        assert "a" in result["graph_properties"]["self_attacking_nodes"]
