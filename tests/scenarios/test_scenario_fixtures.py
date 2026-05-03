"""Smoke tests for scenario fixtures and manifest validation."""
import pathlib

import pytest
import yaml

try:
    from pydantic import ValidationError
except ImportError:
    pytest.skip("pydantic not available", allow_module_level=True)


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCENARIOS_DIR = REPO_ROOT / "examples" / "scenarios"
MANIFEST_PATH = SCENARIOS_DIR / "manifest.yaml"

# Import schema from scenarios directory
import sys
sys.path.insert(0, str(SCENARIOS_DIR.parent))
from scenarios.schema import ScenarioManifest, ScenarioSpec, load_manifest


class TestScenarioManifest:
    """Validate manifest structure and schema."""

    def test_manifest_file_exists(self):
        assert MANIFEST_PATH.exists(), f"Manifest not found at {MANIFEST_PATH}"

    def test_manifest_valid_yaml(self):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "scenarios" in data

    def test_manifest_validates_pydantic(self):
        manifest = load_manifest(MANIFEST_PATH)
        assert len(manifest.scenarios) == 5

    def test_all_scenario_ids_unique(self):
        manifest = load_manifest(MANIFEST_PATH)
        ids = [s.id for s in manifest.scenarios]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_all_scenario_ids_match_pattern(self):
        manifest = load_manifest(MANIFEST_PATH)
        for s in manifest.scenarios:
            assert s.id.startswith("scenario_"), f"Bad ID: {s.id}"

    def test_each_scenario_has_file(self):
        manifest = load_manifest(MANIFEST_PATH)
        for s in manifest.scenarios:
            filepath = SCENARIOS_DIR / s.file
            assert filepath.exists(), f"File missing for {s.id}: {s.file}"

    def test_each_scenario_non_empty(self):
        manifest = load_manifest(MANIFEST_PATH)
        for s in manifest.scenarios:
            filepath = SCENARIOS_DIR / s.file
            content = filepath.read_text(encoding="utf-8").strip()
            assert len(content) >= 200, f"{s.id} too short ({len(content)} chars)"

    def test_all_expected_capabilities_valid(self):
        known_capabilities = {
            "fact_extraction", "argument_quality", "nl_to_logic",
            "neural_fallacy_detection", "hierarchical_fallacy_detection",
            "propositional_logic", "first_order_logic", "modal_logic",
            "dung_extensions", "aspic_analysis", "counter_argumentation",
            "jtms_belief_revision", "debate_protocol",
            "assumption_based_reasoning", "governance_simulation",
            "formal_synthesis", "narrative_synthesis",
        }
        manifest = load_manifest(MANIFEST_PATH)
        for s in manifest.scenarios:
            for cap in s.expected_capabilities:
                assert cap in known_capabilities, f"Unknown capability '{cap}' in {s.id}"

    def test_acceptance_thresholds_reasonable(self):
        manifest = load_manifest(MANIFEST_PATH)
        for s in manifest.scenarios:
            assert 1 <= s.acceptance_min_args <= 20, f"{s.id}: min_args={s.acceptance_min_args}"
            assert 0 <= s.acceptance_min_fallacies <= 10, f"{s.id}: min_fallacies={s.acceptance_min_fallacies}"


class TestScenarioContent:
    """Validate scenario content properties."""

    def test_five_scenarios_present(self):
        manifest = load_manifest(MANIFEST_PATH)
        assert len(manifest.scenarios) == 5
        expected_themes = {"public_policy", "science", "media", "fact_checking", "philosophy"}
        actual_themes = {s.theme for s in manifest.scenarios}
        assert actual_themes == expected_themes

    def test_scenarios_are_french(self):
        manifest = load_manifest(MANIFEST_PATH)
        for s in manifest.scenarios:
            assert s.language == "fr"

    def test_no_plaintext_dataset_overlap(self):
        """Scenarios must be original content, not from the encrypted dataset."""
        # Simple heuristic: check for telltale markers of real political speeches
        forbidden_phrases = [
            "mes chers compatriotes",
            "l'etat d'urgence",
            "republique francaise",
        ]
        manifest = load_manifest(MANIFEST_PATH)
        for s in manifest.scenarios:
            filepath = SCENARIOS_DIR / s.file
            content = filepath.read_text(encoding="utf-8").lower()
            for phrase in forbidden_phrases:
                assert phrase not in content, f"{s.id}: contains '{phrase}'"

    def test_scenario_word_counts(self):
        manifest = load_manifest(MANIFEST_PATH)
        for s in manifest.scenarios:
            filepath = SCENARIOS_DIR / s.file
            content = filepath.read_text(encoding="utf-8")
            word_count = len(content.split())
            assert word_count >= 100, f"{s.id}: too few words ({word_count})"
