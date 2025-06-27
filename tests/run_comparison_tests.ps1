$env:ENABLE_COMPARISON_TESTS="true"
python -m pytest tests/comparison/test_mock_vs_real_behavior.py::TestMockVsRealComparison::test_individual_scenario_comparison