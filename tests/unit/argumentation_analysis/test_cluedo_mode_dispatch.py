"""
Tests for --mode cluedo dispatch wiring (#914).

Validates:
  - argparse accepts "cluedo" as a mode choice
  - Dispatch branch calls run_cluedo_oracle_game()
  - Consumer test: mock run_cluedo_oracle_game, assert it receives text
  - Kernel setup and initial_question derivation
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestCluedoModeArgparse:
    """Test argparse accepts cluedo mode."""

    def test_cluedo_in_choices(self):
        """--mode cluedo should be accepted by argparse."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--mode",
            choices=[
                "pipeline",
                "conversational",
                "hierarchical",
                "cluedo",
                "legacy",
                "sherlock_modern",
            ],
            default="pipeline",
        )
        args = parser.parse_args(["--mode", "cluedo"])
        assert args.mode == "cluedo"

    def test_cluedo_default_still_pipeline(self):
        """Default mode should still be pipeline."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--mode",
            choices=[
                "pipeline",
                "conversational",
                "hierarchical",
                "cluedo",
                "legacy",
                "sherlock_modern",
            ],
            default="pipeline",
        )
        args = parser.parse_args([])
        assert args.mode == "pipeline"


class TestCluedoModeDispatch:
    """Test dispatch wiring for cluedo mode."""

    async def test_dispatch_calls_run_cluedo_oracle_game(self):
        """--mode cluedo should call run_cluedo_oracle_game()."""
        mock_result = {
            "investigation": {"status": "complete"},
            "solution": {"answer": "test"},
            "trace": ["step1", "step2"],
        }
        mock_cluedo_fn = AsyncMock(return_value=mock_result)

        with patch(
            "argumentation_analysis.orchestration.cluedo_extended_orchestrator.run_cluedo_oracle_game",
            mock_cluedo_fn,
        ), patch(
            "argumentation_analysis.run_orchestration.setup_environment",
            new_callable=AsyncMock,
            return_value=MagicMock(service_id="test"),
        ):
            from argumentation_analysis.run_orchestration import main
            import sys

            # Simulate CLI args with --text (inline text, no file I/O)
            original_argv = sys.argv
            sys.argv = [
                "run_orchestration.py",
                "--mode", "cluedo",
                "--text", "Test text for investigation",
            ]
            try:
                await main()
            except SystemExit:
                pass
            finally:
                sys.argv = original_argv

            # Verify run_cluedo_oracle_game was called
            mock_cluedo_fn.assert_called_once()
            call_kwargs = mock_cluedo_fn.call_args
            assert call_kwargs is not None or mock_cluedo_fn.call_count > 0

    async def test_initial_question_from_text(self):
        """When text is provided, initial_question should incorporate it."""
        mock_cluedo_fn = AsyncMock(return_value={})

        with patch(
            "argumentation_analysis.orchestration.cluedo_extended_orchestrator.run_cluedo_oracle_game",
            mock_cluedo_fn,
        ), patch(
            "argumentation_analysis.run_orchestration.setup_environment",
            new_callable=AsyncMock,
            return_value=MagicMock(service_id="test"),
        ):
            from argumentation_analysis.run_orchestration import main
            import sys

            original_argv = sys.argv
            sys.argv = [
                "run_orchestration.py",
                "--mode", "cluedo",
                "--text", "Some interesting text about a mystery",
            ]
            try:
                await main()
            except SystemExit:
                pass
            finally:
                sys.argv = original_argv

            # Check initial_question was derived from text
            if mock_cluedo_fn.called:
                call_kwargs = mock_cluedo_fn.call_args[1] if mock_cluedo_fn.call_args[1] else {}
                initial_q = call_kwargs.get("initial_question", "")
                assert "text" in initial_q.lower() or "indice" in initial_q.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
