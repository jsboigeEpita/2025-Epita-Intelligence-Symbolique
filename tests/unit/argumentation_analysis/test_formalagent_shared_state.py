"""Unit tests for FormalAgent shared state wiring (#545).

Tests verify:
- atomic_propositions and fol_shared_signature exposed in state snapshot
- FormalAgent instructions reference ETAPE 0 (consult shared atoms)
- Snapshot includes shared fields when populated
- Summarized snapshot includes counts
"""

import json

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState


class TestStateSnapshotSharedFields:

    def test_full_snapshot_includes_atomic_propositions(self):
        state = UnifiedAnalysisState("test text")
        state.atomic_propositions["src0"] = ["is_raining", "ground_wet"]

        snap = state.get_state_snapshot(summarize=False)
        assert "atomic_propositions" in snap
        assert snap["atomic_propositions"]["src0"] == ["is_raining", "ground_wet"]

    def test_full_snapshot_includes_fol_shared_signature(self):
        state = UnifiedAnalysisState("test text")
        state.fol_shared_signature["src0"] = {
            "sorts": {"Person": ["socrates"]},
            "predicates": {"Mortal": ["Person"]},
            "constants_raw": {"socrates": "philosopher"},
        }

        snap = state.get_state_snapshot(summarize=False)
        assert "fol_shared_signature" in snap
        assert "Person" in snap["fol_shared_signature"]["src0"]["sorts"]

    def test_summarized_snapshot_includes_counts(self):
        state = UnifiedAnalysisState("test text")
        state.atomic_propositions["src0"] = ["a", "b", "c"]
        state.fol_shared_signature["src0"] = {"sorts": {"Person": ["socrates"]}}
        state.fol_shared_signature["src1"] = {"sorts": {"Thing": ["x"]}}

        snap = state.get_state_snapshot(summarize=True)
        assert "atomic_propositions_count" in snap
        assert snap["atomic_propositions_count"] == 3
        assert "fol_shared_signature_sources" in snap
        assert set(snap["fol_shared_signature_sources"]) == {"src0", "src1"}

    def test_empty_shared_fields_in_snapshot(self):
        state = UnifiedAnalysisState("test text")
        snap = state.get_state_snapshot(summarize=False)

        assert "atomic_propositions" in snap
        assert snap["atomic_propositions"] == {}
        assert "fol_shared_signature" in snap
        assert snap["fol_shared_signature"] == {}


class TestFormalAgentInstructions:

    def test_formal_agent_instructions_mention_etape_0(self):
        """FormalAgent instructions should include ETAPE 0 for shared atoms."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        formal_instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "ETAPE 0" in formal_instructions
        assert "atomic_propositions" in formal_instructions
        assert "fol_shared_signature" in formal_instructions

    def test_formal_agent_instructions_mention_shared_atoms_usage(self):
        """Instructions should tell FormalAgent to use shared atoms when available."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        formal_instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "atomes partages" in formal_instructions
        assert "coherence inter-arguments" in formal_instructions

    def test_formal_agent_instructions_preserve_existing_etapes(self):
        """Existing ETAPE 1-4 should still be present."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        formal_instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "ETAPE 1" in formal_instructions
        assert "ETAPE 2" in formal_instructions
        assert "ETAPE 3" in formal_instructions
        assert "ETAPE 4" in formal_instructions
        assert "translate_to_pl" in formal_instructions
        assert "translate_to_fol" in formal_instructions

    def test_formal_agent_instructions_guide_atom_inclusion(self):
        """Instructions should tell agent to include shared atoms in translator input."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        formal_instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "inclus-les" in formal_instructions or "guide" in formal_instructions


class TestEndToEndSharedStateFlow:

    def test_pl_pipeline_populates_then_formalagent_reads(self):
        """PL 2-pass stores atoms → snapshot exposes them → FormalAgent reads."""
        state = UnifiedAnalysisState("Socrates argues about justice.")

        # Simulate PL 2-pass pipeline storing atoms
        state.atomic_propositions["test_corpus"] = [
            "socrates_argues",
            "justice_matters",
            "truth_seeker",
        ]

        # FormalAgent reads via snapshot
        snap = state.get_state_snapshot(summarize=False)
        atoms = snap.get("atomic_propositions", {}).get("test_corpus", [])

        assert len(atoms) == 3
        assert "socrates_argues" in atoms

    def test_fol_pipeline_populates_then_formalagent_reads(self):
        """FOL 2-pass stores signature → snapshot exposes it → FormalAgent reads."""
        state = UnifiedAnalysisState("Plato and Socrates debate.")

        # Simulate FOL 2-pass pipeline storing signature
        state.fol_shared_signature["test_corpus"] = {
            "sorts": {"Philosopher": ["socrates", "plato"]},
            "predicates": {"Argues": ["Philosopher"], "Mortal": ["Philosopher"]},
            "constants_raw": {"socrates": "the thinker", "plato": "the student"},
        }

        # FormalAgent reads via snapshot
        snap = state.get_state_snapshot(summarize=False)
        sig = snap.get("fol_shared_signature", {}).get("test_corpus", {})

        assert "Philosopher" in sig["sorts"]
        assert "Argues" in sig["predicates"]
        assert len(sig["sorts"]["Philosopher"]) == 2
