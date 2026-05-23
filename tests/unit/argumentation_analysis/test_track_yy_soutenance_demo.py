"""Tests for Track YY (#681): Soutenance Demo Script.

Covers:
  1. Dry-run mode: all 11 sections present, privacy-clean
  2. JSON output: valid JSON with correct structure
  3. Single-step mode: renders only requested section
  4. Live-mode extractor: privacy-clean conversion from raw pipeline output
  5. No source text leakage in output
"""

import json
import importlib.util
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

_DEMO_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "02_core_system_demos"
    / "run_soutenance_demo.py"
)
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])

_spec = importlib.util.spec_from_file_location("run_soutenance_demo", _DEMO_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

MOCK_RESULT = _mod.MOCK_RESULT
run_demo = _mod.run_demo
_extract_live_result = _mod._extract_live_result
_RENDERERS = _mod._RENDERERS


class TestDryRunMode:
    """Verify dry-run produces complete privacy-clean output."""

    def test_all_sections_present(self):
        result = run_demo(["--dry-run", "--quiet"])
        assert len(result["sections"]) == 11
        expected_keys = [
            "1_extraction",
            "2_fallacies",
            "3_formal_logic",
            "4_dung",
            "5_jtms",
            "6_counter_args",
            "7_debate",
            "8_governance",
            "9_convergence",
            "10_adjudication",
            "11_insight",
        ]
        for key in expected_keys:
            assert key in result["sections"], f"Missing section: {key}"

    def test_mode_is_dry_run(self):
        result = run_demo(["--dry-run", "--quiet"])
        assert result["mode"] == "dry-run"

    def test_timestamp_present(self):
        result = run_demo(["--dry-run", "--quiet"])
        assert "timestamp" in result
        assert result["timestamp"] != ""

    def test_pipeline_summary(self):
        result = run_demo(["--dry-run", "--quiet"])
        summary = result["pipeline_summary"]
        assert summary["phases_total"] == 22
        assert summary["phases_completed"] == 22
        assert summary["workflow"] == "spectacular_analysis"


class TestJsonOutput:
    """Verify JSON output is valid and complete."""

    def test_json_output_valid(self, capsys):
        result = run_demo(["--dry-run", "--json", "--quiet"])
        captured = capsys.readouterr()
        json_start = captured.out.find("{")
        assert json_start >= 0
        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(captured.out, json_start)
        assert parsed["mode"] == "dry-run"
        assert len(parsed["sections"]) == 11

    def test_json_no_ansi_codes(self, capsys):
        run_demo(["--dry-run", "--json"])
        captured = capsys.readouterr()
        json_start = captured.out.find("{")
        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(captured.out, json_start)
        serialized = json.dumps(parsed)
        assert "\033[" not in serialized


class TestSingleStepMode:
    """Verify --step N renders only that section."""

    def test_step_1_only(self, capsys):
        run_demo(["--dry-run", "--quiet", "--step", "1"])
        captured = capsys.readouterr()
        assert "Section 1" in captured.out
        assert "Section 2" not in captured.out

    def test_step_9_convergence(self, capsys):
        run_demo(["--dry-run", "--quiet", "--step", "9"])
        captured = capsys.readouterr()
        assert "Signal" in captured.out
        assert "LIVING" in captured.out

    def test_invalid_step(self, capsys):
        run_demo(["--dry-run", "--quiet", "--step", "99"])
        captured = capsys.readouterr()
        assert "Invalid step" in captured.out

    def test_step_range(self, capsys):
        for step in range(1, 12):
            run_demo(["--dry-run", "--quiet", "--step", str(step)])
            captured = capsys.readouterr()
            assert f"Section {step}" in captured.out


class TestPrivacyClean:
    """Verify no source text leaks into output."""

    # Patterns that should NEVER appear in the output JSON
    FORBIDDEN_PATTERNS = [
        "mythe invent",
        "economie s'effondrera",
        "George Soros",
        "rechauffement climatique",
        "media",
        "charbon",
    ]

    def test_mock_data_no_source_text(self):
        serialized = json.dumps(MOCK_RESULT)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert (
                pattern.lower() not in serialized.lower()
            ), f"Source text leak: '{pattern}' found in mock data"

    def test_dry_run_output_no_source_text(self, tmp_path):
        outfile = tmp_path / "test_output.json"
        result = run_demo(["--dry-run", "--quiet", "--output", str(outfile)])
        content = outfile.read_text(encoding="utf-8")
        for pattern in self.FORBIDDEN_PATTERNS:
            assert (
                pattern.lower() not in content.lower()
            ), f"Source text leak: '{pattern}' in output"

    def test_output_file_created(self, tmp_path):
        outfile = tmp_path / "demo_out.json"
        run_demo(["--dry-run", "--quiet", "--output", str(outfile)])
        assert outfile.exists()
        data = json.loads(outfile.read_text(encoding="utf-8"))
        assert "sections" in data


class TestLiveExtractor:
    """Verify _extract_live_result converts pipeline output correctly."""

    def test_extracts_arguments(self):
        state = MagicMock()
        state.identified_arguments = {"arg_1": "desc1", "arg_2": "desc2"}
        state.identified_claims = {"c1": "claim1"}
        state.argument_quality_scores = {
            "arg_1": {"overall": 0.85},
            "arg_2": {"overall": 0.70},
        }
        state.identified_fallacies = {}
        state.propositional_analysis_results = {}
        state.fol_analysis_results = {}
        state.modal_analysis_results = {}
        state.dung_frameworks = {}
        state.jtms_beliefs = {}
        state.counter_arguments = {}

        raw = {"unified_state": state, "summary": {"total": 22, "completed": 20}}
        result = _extract_live_result(raw)

        sec1 = result["sections"]["1_extraction"]
        assert len(sec1["arguments"]) == 2
        assert sec1["arguments"][0]["id"] == "arg_1"
        assert sec1["arguments"][0]["quality"] == 0.85

    def test_extracts_fallacies(self):
        state = MagicMock()
        state.identified_arguments = {}
        state.identified_claims = {}
        state.argument_quality_scores = {}
        state.identified_fallacies = {
            "f1": {
                "type": "Ad hominem",
                "family": "Pertinence",
                "confidence": 0.9,
                "target_argument_id": "arg_3",
            },
        }
        state.propositional_analysis_results = {}
        state.fol_analysis_results = {}
        state.modal_analysis_results = {}
        state.dung_frameworks = {}
        state.jtms_beliefs = {}
        state.counter_arguments = {}

        raw = {"unified_state": state, "summary": {"total": 22, "completed": 22}}
        result = _extract_live_result(raw)

        sec2 = result["sections"]["2_fallacies"]
        assert len(sec2["fallacies"]) == 1
        assert sec2["fallacies"][0]["type"] == "Ad hominem"
        assert sec2["families_represented"] == 1

    def test_extracts_jtms_retractions(self):
        state = MagicMock()
        state.identified_arguments = {}
        state.identified_claims = {}
        state.argument_quality_scores = {}
        state.identified_fallacies = {}
        state.propositional_analysis_results = {}
        state.fol_analysis_results = {}
        state.modal_analysis_results = {}
        state.dung_frameworks = {}
        state.jtms_beliefs = {
            "jtms_1": {
                "name": "arg_3:Some text excerpt",
                "valid": False,
                "justifications": [],
            },
            "jtms_2": {"name": "arg_4:Other text", "valid": True, "justifications": []},
        }
        state.counter_arguments = {}

        raw = {"unified_state": state, "summary": {"total": 22, "completed": 22}}
        result = _extract_live_result(raw)

        sec5 = result["sections"]["5_jtms"]
        assert sec5["beliefs_total"] == 2
        assert len(sec5["cascades"]) == 1
        assert sec5["cascades"][0]["target"] == "arg_3"
        assert sec5["cascades"][0]["after"] == "OUT"

    def test_live_result_privacy_clean(self):
        state = MagicMock()
        state.identified_arguments = {"arg_1": "desc"}
        state.identified_claims = {}
        state.argument_quality_scores = {}
        state.identified_fallacies = {}
        state.propositional_analysis_results = {}
        state.fol_analysis_results = {}
        state.modal_analysis_results = {}
        state.dung_frameworks = {}
        state.jtms_beliefs = {}
        state.counter_arguments = {}

        raw = {"unified_state": state, "summary": {"total": 22, "completed": 22}}
        result = _extract_live_result(raw)
        serialized = json.dumps(result)

        for pattern in TestPrivacyClean.FORBIDDEN_PATTERNS:
            assert pattern.lower() not in serialized.lower()


class TestRenderers:
    """Verify all 11 renderers execute without error."""

    def test_all_renderers_present(self):
        assert len(_RENDERERS) == 11

    @pytest.mark.parametrize("section_key", list(_RENDERERS.keys()))
    def test_renderer_executes(self, section_key, capsys):
        section_data = MOCK_RESULT["sections"][section_key]
        _RENDERERS[section_key](section_data)
        captured = capsys.readouterr()
        assert len(captured.out) > 0


class TestMockDataIntegrity:
    """Verify mock data has the expected structure."""

    def test_convergence_signals_count(self):
        signals = MOCK_RESULT["sections"]["9_convergence"]["signals"]
        assert len(signals) == 5

    def test_all_signals_living(self):
        signals = MOCK_RESULT["sections"]["9_convergence"]["signals"]
        for sig in signals:
            assert "LIVING" in sig["status"]

    def test_dung_has_three_semantics(self):
        dung = MOCK_RESULT["sections"]["4_dung"]
        assert "grounded" in dung["extensions"]
        assert "preferred" in dung["extensions"]
        assert "stable" in dung["extensions"]

    def test_governance_three_methods(self):
        gov = MOCK_RESULT["sections"]["8_governance"]
        assert len(gov["voting_methods"]) == 3
        methods = {v["method"] for v in gov["voting_methods"]}
        assert methods == {"Majority", "Borda", "Condorcet"}

    def test_counter_args_four_strategies(self):
        counter = MOCK_RESULT["sections"]["6_counter_args"]
        assert len(counter["strategies"]) == 4

    def test_jtms_two_cascades(self):
        jtms = MOCK_RESULT["sections"]["5_jtms"]
        assert len(jtms["cascades"]) == 2
