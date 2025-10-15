import unittest
from unittest.mock import MagicMock, patch, call
from argumentation_analysis.orchestration.hierarchical.strategic.manager import (
    StrategicManager,
)
from argumentation_analysis.orchestration.hierarchical.strategic.state import (
    StrategicState,
)
from argumentation_analysis.core.communication import MessageMiddleware, MessagePriority


class TestHierarchicalFullStrategy(unittest.TestCase):
    def setUp(self):
        """Set up the test environment before each test."""
        # Mock the dependencies
        self.mock_strategic_state = MagicMock(spec=StrategicState)
        self.mock_strategic_state.strategic_plan = {}
        self.mock_strategic_state.global_metrics = {}
        self.mock_strategic_state.global_objectives = []
        self.mock_middleware = MagicMock(spec=MessageMiddleware)

        # Instantiate the StrategicManager with mocked dependencies
        self.strategic_manager = StrategicManager(
            strategic_state=self.mock_strategic_state, middleware=self.mock_middleware
        )
        # Mock the adapter directly on the instance
        self.strategic_manager.adapter = MagicMock()

    def test_initialize_analysis_happy_path(self):
        """
        Test the successful initialization of an analysis.
        This test ensures that when initialize_analysis is called:
        1. The text is correctly set in the state.
        2. Initial objectives, strategic plan, and resources are defined and allocated.
        3. A directive is issued to the tactical coordinator with the correct plan.
        """
        # Arrange
        test_text = "This is a test text for analysis."

        # Act
        result = self.strategic_manager.initialize_analysis(test_text)

        # Assert
        # Verify that the state was updated correctly
        self.mock_strategic_state.set_raw_text.assert_called_once_with(test_text)
        self.mock_strategic_state.add_global_objective.assert_called()
        self.mock_strategic_state.update_strategic_plan.assert_called_once()
        self.mock_strategic_state.update_resource_allocation.assert_called_once()
        self.mock_strategic_state.log_strategic_decision.assert_called()

        # Verify that the directive was issued to the tactical coordinator
        self.strategic_manager.adapter.issue_directive.assert_called_once()
        # call_args[1] holds the keyword arguments dictionary
        directive_call_args = self.strategic_manager.adapter.issue_directive.call_args[
            1
        ]

        # Check the arguments of the issue_directive call
        self.assertEqual(directive_call_args["directive_type"], "new_strategic_plan")
        self.assertIn("plan", directive_call_args["parameters"])
        self.assertIn("objectives", directive_call_args["parameters"])
        self.assertEqual(directive_call_args["recipient_id"], "tactical_coordinator")
        self.assertEqual(directive_call_args["priority"], MessagePriority.HIGH)

        self.assertIsNotNone(result)

    def test_process_tactical_feedback_with_issues(self):
        """
        Tests the manager's ability to process feedback containing issues and
        make strategic adjustments.
        """
        # Arrange
        feedback_with_issues = {
            "progress_metrics": {"completion": 0.5},
            "issues": [{"type": "resource_shortage", "resource": "informal_analyzer"}],
        }

        # Act
        result = self.strategic_manager.process_tactical_feedback(feedback_with_issues)

        # Assert
        # Verify state updates
        self.mock_strategic_state.update_global_metrics.assert_called_once_with(
            {"completion": 0.5}
        )

        # Verify that adjustments were applied
        self.mock_strategic_state.update_resource_allocation.assert_called_once()

        # Verify that a directive with adjustments was sent
        self.strategic_manager.adapter.issue_directive.assert_called_once()
        directive_call_args = self.strategic_manager.adapter.issue_directive.call_args[
            1
        ]
        self.assertEqual(directive_call_args["directive_type"], "strategic_adjustment")
        self.assertIn("resource_reallocation", directive_call_args["parameters"])

        # Verify the result structure
        self.assertIn("strategic_adjustments", result)

    def test_evaluate_final_results(self):
        """
        Tests the manager's ability to evaluate final results and formulate a conclusion.
        """
        # Arrange
        final_results = {
            "obj-1": {"success_rate": 0.9},
            "obj-2": {"success_rate": 0.8},
        }

        # Configure the mock state to return predefined objectives
        self.mock_strategic_state.global_objectives = [
            {"id": "obj-1", "description": "Identify main arguments"},
            {"id": "obj-2", "description": "Detect fallacies"},
        ]

        # Act
        result = self.strategic_manager.evaluate_final_results(final_results)

        # Assert
        # Verify that the final conclusion was set in the state
        self.mock_strategic_state.set_final_conclusion.assert_called_once()

        # Verify that a decision was logged
        self.mock_strategic_state.log_strategic_decision.assert_called()

        # Verify that the conclusion was published
        self.strategic_manager.adapter.publish_strategic_decision.assert_called_once()

        # Check the result structure
        self.assertIn("conclusion", result)
        self.assertIn("evaluation", result)
        self.assertAlmostEqual(result["evaluation"]["overall_success_rate"], 0.85)
        self.assertIn("Analyse réussie", result["conclusion"])
        self.assertIn("final_state", result)


if __name__ == "__main__":
    unittest.main()
