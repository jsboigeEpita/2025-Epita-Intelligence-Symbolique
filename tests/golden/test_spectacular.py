"""Golden structural regression tests for the spectacular workflow (#365).

These tests verify that the spectacular analysis pipeline output satisfies
minimum structural requirements. They run against a pre-recorded synthetic
fixture (no API keys, no JVM, no encrypted dataset needed in CI).

Definition of Done (#365):
  - ≥28 populated fields on doc_A state snapshot
  - state.atms_contexts has ≥3 hypotheses
  - state.dung_frameworks has non-trivial structure
  - state.fol_analysis_results has ≥5 formulas
  - state.jtms_retraction_chain has ≥1 cascade
  - state.narrative_synthesis present and cites ≥5 fields
"""

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "spectacular"
GOLDEN_PATH = FIXTURE_DIR / "doc_a_golden.json"


@pytest.fixture(scope="module")
def golden():
    """Load the doc_A golden fixture once per module."""
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def state(golden):
    """Shortcut to the state_snapshot inside the golden fixture."""
    return golden["state_snapshot"]


# ── Helpers ──


def _non_empty_count(data: dict) -> int:
    """Count keys whose value is non-empty (list/dict with items, non-empty str, non-zero number)."""
    count = 0
    for v in data.values():
        if isinstance(v, (list, dict, str)) and v:
            count += 1
        elif isinstance(v, (int, float)) and v != 0:
            count += 1
        elif isinstance(v, bool) and v:
            count += 1
    return count


FIELD_TERMS = {
    "identified_arguments": ["argument", "reasoning chain"],
    "identified_fallacies": ["fallac", "ad hominem", "slippery slope", "straw man"],
    "dung_frameworks": ["Dung", "abstract argumentation", "extension"],
    "fol_analysis_results": ["FOL", "first_order", "first order"],
    "propositional_analysis_results": ["propositional logic"],
    "modal_analysis_results": ["modal", "S5"],
    "jtms_beliefs": ["JTMS", "belief revision"],
    "jtms_retraction_chain": ["retraction cascade", "retracted", "cascade"],
    "atms_contexts": ["ATMS", "reasoning context", "assumption"],
    "counter_arguments": ["counter-argument", "reductio", "counter-example"],
    "governance_decisions": ["governance", "voting", "Borda", "Condorcet"],
    "argument_quality_scores": ["quality score", "quality"],
    "narrative_synthesis": ["narrative"],
    "debate_transcripts": ["debate", "opponent"],
    "aspic_results": ["ASPIC"],
    "neural_fallacy_scores": ["neural"],
    "nl_to_logic_translations": ["translation"],
    "formal_synthesis_reports": ["formal synthesis", "synthesis report"],
    "fol_signature": ["signature"],
}


def _extract_cited_fields(narrative: str, state: dict) -> set:
    """Extract state field names that the narrative mentions by key name or descriptive terms."""
    cited = set()
    narrative_lower = narrative.lower()
    for key in state:
        # Direct key match
        if key in narrative:
            cited.add(key)
            continue
        # Descriptive term match
        terms = FIELD_TERMS.get(key, [])
        if any(term.lower() in narrative_lower for term in terms):
            cited.add(key)
    return cited


# ── Structural regression tests ──


class TestGoldenFixtureIntegrity:
    """Verify the fixture file itself is well-formed."""

    def test_fixture_file_exists(self):
        assert GOLDEN_PATH.is_file()

    def test_fixture_is_valid_json(self):
        with open(GOLDEN_PATH, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_fixture_has_required_top_level_keys(self, golden):
        for key in ("workflow_name", "state_snapshot", "summary", "capabilities_used"):
            assert key in golden, f"Missing top-level key: {key}"

    def test_workflow_name_is_spectacular(self, golden):
        assert golden["workflow_name"] == "spectacular_analysis"

    def test_no_plaintext_source_content(self, golden):
        raw = golden["state_snapshot"].get("raw_text", "")
        assert raw.startswith(
            "[REDACTED"
        ), "Golden fixture must not contain plaintext source"


class TestFieldCoverage:
    """Verify ≥28 populated fields in the state snapshot."""

    def test_minimum_28_populated_fields(self, state):
        count = _non_empty_count(state)
        assert count >= 28, (
            f"Expected ≥28 non-empty fields, got {count}. "
            f"Populated: {[k for k, v in state.items() if v and v not in ([], {}, '', None, 0)]}"
        )

    def test_all_17_capabilities_present(self, golden):
        caps = golden["capabilities_used"]
        assert len(caps) == 17, f"Expected 17 capabilities, got {len(caps)}"

    def test_all_17_phases_completed(self, golden):
        summary = golden["summary"]
        assert summary["completed"] == 17
        assert summary["total"] == 17
        assert summary["failed"] == 0


class TestAtmsContexts:
    """Verify ATMS contexts have ≥3 hypotheses."""

    def test_atms_has_at_least_3_contexts(self, state):
        atms = state.get("atms_contexts", [])
        assert len(atms) >= 3, f"Expected ≥3 ATMS contexts, got {len(atms)}"

    def test_each_context_has_required_fields(self, state):
        for ctx in state["atms_contexts"]:
            assert "context_id" in ctx
            assert "assumptions" in ctx
            assert "status" in ctx
            assert ctx["status"] in ("consistent", "contradictory")

    def test_at_least_one_contradictory_context(self, state):
        statuses = [c["status"] for c in state["atms_contexts"]]
        assert (
            "contradictory" in statuses
        ), "Expected at least one contradictory ATMS context"


class TestDungFrameworks:
    """Verify Dung framework has non-trivial structure."""

    def test_dung_frameworks_present(self, state):
        dung = state.get("dung_frameworks", {})
        assert len(dung) >= 1, "Expected at least one Dung framework"

    def test_dung_has_arguments(self, state):
        fw = next(iter(state["dung_frameworks"].values()))
        assert len(fw.get("arguments", [])) >= 3

    def test_dung_has_attacks(self, state):
        fw = next(iter(state["dung_frameworks"].values()))
        assert len(fw.get("attacks", [])) >= 1, "Expected ≥1 attack relation"

    def test_dung_has_extensions(self, state):
        fw = next(iter(state["dung_frameworks"].values()))
        extensions = fw.get("extensions", {})
        assert "grounded" in extensions
        assert len(extensions["grounded"]) >= 1

    def test_dung_has_status_assignment(self, state):
        fw = next(iter(state["dung_frameworks"].values()))
        assert "status_assignment" in fw
        statuses = set(fw["status_assignment"].values())
        assert len(statuses) >= 2, "Expected ≥2 different acceptance statuses"


class TestFolAnalysis:
    """Verify FOL analysis has ≥5 formulas."""

    def test_fol_has_at_least_5_formulas(self, state):
        fol = state.get("fol_analysis_results", [])
        assert len(fol) >= 5, f"Expected ≥5 FOL formulas, got {len(fol)}"

    def test_each_fol_formula_has_result(self, state):
        for entry in state["fol_analysis_results"]:
            assert "formula" in entry
            assert "result" in entry

    def test_fol_signature_non_empty(self, state):
        sig = state.get("fol_signature", [])
        assert len(sig) >= 5, f"Expected ≥5 signature entries, got {len(sig)}"


class TestJtmsRetractionChain:
    """Verify JTMS retraction chain has ≥1 cascade."""

    def test_jtms_has_at_least_1_cascade(self, state):
        chain = state.get("jtms_retraction_chain", [])
        assert len(chain) >= 1, "Expected ≥1 JTMS retraction cascade"

    def test_each_cascade_has_required_fields(self, state):
        for cascade in state["jtms_retraction_chain"]:
            assert "cascade_id" in cascade
            assert "trigger" in cascade
            assert "reason" in cascade
            assert "downstream_effects" in cascade

    def test_cascade_has_belief_status_change(self, state):
        cascade = state["jtms_retraction_chain"][0]
        effects = cascade["downstream_effects"]
        assert len(effects) >= 1, "Expected ≥1 downstream effect in first cascade"
        first = effects[0]
        assert "belief" in first


class TestNarrativeSynthesis:
    """Verify narrative synthesis is present and cites ≥5 fields."""

    def test_narrative_synthesis_present(self, state):
        narrative = state.get("narrative_synthesis", "")
        assert (
            len(narrative) > 100
        ), "Narrative synthesis should be substantial (>100 chars)"

    def test_narrative_cites_at_least_5_fields(self, state):
        narrative = state["narrative_synthesis"]
        cited = _extract_cited_fields(narrative, state)
        assert (
            len(cited) >= 5
        ), f"Narrative should cite ≥5 state fields, cites {len(cited)}: {cited}"

    def test_narrative_references_sections(self, state):
        narrative = state["narrative_synthesis"]
        assert (
            "Section" in narrative
        ), "Narrative should include section cross-references"


class TestCrossFieldConsistency:
    """Verify cross-references between fields are consistent."""

    def test_fallacy_count_matches_neural_scores(self, state):
        fallacies = state.get("identified_fallacies", {})
        neural = state.get("neural_fallacy_scores", [])
        # Neural scores should cover at least the detected fallacies
        neural_types = {s["fallacy"] for s in neural}
        fallacy_types = {f["type"] for f in fallacies.values()}
        assert fallacy_types.issubset(
            neural_types
        ), f"Some detected fallacies not in neural scores: {fallacy_types - neural_types}"

    def test_dung_arguments_are_subset_of_identified(self, state):
        identified = set(state.get("identified_arguments", {}).keys())
        fw = next(iter(state.get("dung_frameworks", {}).values()), {})
        dung_args = set(fw.get("arguments", []))
        assert dung_args.issubset(
            identified
        ), f"Dung references unknown args: {dung_args - identified}"

    def test_counter_arguments_target_existing_args(self, state):
        identified = set(state.get("identified_arguments", {}).keys())
        for counter in state.get("counter_arguments", []):
            target = counter.get("target_arg", "")
            assert target in identified, f"Counter targets unknown arg: {target}"

    def test_jtms_beliefs_reference_args(self, state):
        identified = set(state.get("identified_arguments", {}).keys())
        for belief_id in state.get("jtms_beliefs", {}):
            if belief_id.startswith("b_arg_"):
                arg_id = belief_id[2:]
                assert arg_id in identified, f"JTMS references unknown arg: {arg_id}"
