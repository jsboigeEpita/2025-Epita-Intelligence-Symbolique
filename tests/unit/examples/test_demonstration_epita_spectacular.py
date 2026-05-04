"""Smoke tests for demonstration_epita_spectacular.py — #361"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent.parent / (
    "examples/02_core_system_demos/scripts_demonstration/demonstration_epita_spectacular.py"
)


def _run(args=None, timeout=30):
    cmd = [sys.executable, str(SCRIPT)]
    if args:
        cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


@pytest.mark.skipif(not SCRIPT.exists(), reason="Demo script not found")
class TestDemonstrationSpectacular:
    """Verify the spectacular demonstration script runs correctly."""

    def test_full_demo_exits_zero(self):
        r = _run(["--quiet"])
        assert r.returncode == 0, f"Exit {r.returncode}: {r.stderr[:300]}"

    def test_full_demo_contains_all_steps(self):
        r = _run(["--quiet"])
        output = r.stdout
        for step_name in (
            "Extraction & Claims",
            "Formal Logic",
            "Fallacy Detection",
            "Argumentation Frameworks",
            "Adversarial Debate",
            "Unified Synthesis",
        ):
            assert step_name in output, f"Missing step: {step_name}"

    def test_json_full_output_valid(self):
        r = _run(["--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "steps" in data
        assert len(data["steps"]) == 6
        assert data["source_id"] == "doc_A"

    def test_json_single_step(self):
        r = _run(["--json", "--step", "3"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["title"] == "Fallacy Taxonomy Detection"
        assert "detected_fallacies" in data["output"]

    def test_invalid_step_returns_error(self):
        r = _run(["--step", "9"])
        assert r.returncode != 0  # argparse exits 2 for invalid choice

    def test_step_1_has_claims(self):
        r = _run(["--quiet", "--step", "1"])
        assert "Global warming is a myth" in r.stdout
        assert "5" in r.stdout  # 5 claims

    def test_step_3_has_fallacies(self):
        r = _run(["--quiet", "--step", "3"])
        assert "Ad Hominem" in r.stdout
        assert "Slippery Slope" in r.stdout
        assert "HIGH" in r.stdout

    def test_step_4_has_dung_and_jtms(self):
        r = _run(["--quiet", "--step", "4"])
        assert "Grounded" in r.stdout
        assert "JTMS" in r.stdout
        assert (
            "retraction cascade" in r.stdout.lower() or "Retraction cascade" in r.stdout
        )

    def test_step_6_synthesis_quality(self):
        r = _run(["--quiet", "--step", "6"])
        assert "REJECTED" in r.stdout
        assert "32" in r.stdout  # 32 fields
        assert "overall" in r.stdout.lower() or "Overall" in r.stdout

    def test_mock_data_structure_integrity(self):
        """Verify the mock data can be imported and has correct structure."""
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import importlib

            mod_name = "demonstration_epita_spectacular"
            spec = importlib.util.spec_from_file_location(mod_name, SCRIPT)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            result = mod.MOCK_SPECTACULAR_RESULT
            assert len(result["steps"]) == 6
            assert (
                result["steps"]["1_extraction"]["output"]["extraction_stats"]["claims"]
                == 5
            )
            assert (
                len(
                    result["steps"]["3_fallacy_detection"]["output"][
                        "detected_fallacies"
                    ]
                )
                == 6
            )
            assert (
                len(
                    result["steps"]["4_argumentation_frameworks"]["output"]["dung"][
                        "extensions"
                    ]["grounded"]
                )
                == 3
            )
            assert result["steps"]["6_synthesis"]["output"]["field_count"] == 32
        finally:
            sys.path.pop(0)

    def test_import_run_demo_function(self):
        """Verify run_demo can be called programmatically."""
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import importlib.util

            mod_name = "demonstration_epita_spectacular"
            spec = importlib.util.spec_from_file_location(mod_name, SCRIPT)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            result = mod.run_demo(quiet=True)
            assert result is not None
            assert "steps" in result
        finally:
            sys.path.pop(0)
