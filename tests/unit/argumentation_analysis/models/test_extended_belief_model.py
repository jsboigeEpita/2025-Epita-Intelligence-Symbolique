# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.models.extended_belief_model
Covers BeliefType, ConfidenceLevel, EvidenceQuality enums,
ModificationHistory, BeliefMetadata, and ExtendedBeliefModel dataclasses.
"""

import pytest
from datetime import datetime, timedelta
from argumentation_analysis.models.extended_belief_model import (
    BeliefType,
    ConfidenceLevel,
    EvidenceQuality,
    ModificationHistory,
    BeliefMetadata,
    ExtendedBeliefModel,
)

# ============================================================
# BeliefType enum
# ============================================================


class TestBeliefType:
    """Tests for the BeliefType enum."""

    def test_all_values(self):
        expected = {
            "fact",
            "hypothesis",
            "evidence",
            "deduction",
            "assumption",
            "constraint",
            "validation",
            "critique",
        }
        assert {bt.value for bt in BeliefType} == expected

    def test_from_value(self):
        assert BeliefType("fact") is BeliefType.FACT
        assert BeliefType("hypothesis") is BeliefType.HYPOTHESIS

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            BeliefType("nonexistent")

    def test_member_count(self):
        assert len(BeliefType) == 8


# ============================================================
# ConfidenceLevel enum
# ============================================================


class TestConfidenceLevel:
    """Tests for the ConfidenceLevel enum."""

    def test_very_low_range(self):
        assert ConfidenceLevel.VERY_LOW.contains(0.0)
        assert ConfidenceLevel.VERY_LOW.contains(0.1)
        assert not ConfidenceLevel.VERY_LOW.contains(0.2)

    def test_low_range(self):
        assert ConfidenceLevel.LOW.contains(0.2)
        assert ConfidenceLevel.LOW.contains(0.3)
        assert not ConfidenceLevel.LOW.contains(0.4)

    def test_medium_range(self):
        assert ConfidenceLevel.MEDIUM.contains(0.4)
        assert ConfidenceLevel.MEDIUM.contains(0.5)
        assert not ConfidenceLevel.MEDIUM.contains(0.6)

    def test_high_range(self):
        assert ConfidenceLevel.HIGH.contains(0.6)
        assert ConfidenceLevel.HIGH.contains(0.7)
        assert not ConfidenceLevel.HIGH.contains(0.8)

    def test_very_high_range(self):
        assert ConfidenceLevel.VERY_HIGH.contains(0.8)
        assert ConfidenceLevel.VERY_HIGH.contains(0.99)
        assert not ConfidenceLevel.VERY_HIGH.contains(1.0)

    def test_boundary_values(self):
        # Each boundary belongs to the upper bucket (lower-inclusive)
        assert ConfidenceLevel.LOW.contains(0.2)
        assert not ConfidenceLevel.VERY_LOW.contains(0.2)
        assert ConfidenceLevel.MEDIUM.contains(0.4)
        assert not ConfidenceLevel.LOW.contains(0.4)

    def test_negative_value(self):
        for level in ConfidenceLevel:
            assert not level.contains(-0.1)

    def test_member_count(self):
        assert len(ConfidenceLevel) == 5


# ============================================================
# EvidenceQuality enum
# ============================================================


class TestEvidenceQuality:
    """Tests for the EvidenceQuality enum."""

    def test_all_values(self):
        expected = {
            "unreliable",
            "circumstantial",
            "corroborated",
            "verified",
            "proven",
        }
        assert {eq.value for eq in EvidenceQuality} == expected

    def test_from_value(self):
        assert EvidenceQuality("proven") is EvidenceQuality.PROVEN

    def test_member_count(self):
        assert len(EvidenceQuality) == 5


# ============================================================
# ModificationHistory
# ============================================================


class TestModificationHistory:
    """Tests for the ModificationHistory dataclass."""

    @pytest.fixture
    def sample_modification(self):
        return ModificationHistory(
            timestamp=datetime(2025, 1, 15, 10, 30, 0),
            modification_type="updated",
            agent_id="agent_watson",
            previous_confidence=0.5,
            new_confidence=0.8,
            reason="New evidence found",
            metadata={"source": "interview"},
        )

    def test_basic_creation(self, sample_modification):
        assert sample_modification.modification_type == "updated"
        assert sample_modification.agent_id == "agent_watson"
        assert sample_modification.previous_confidence == 0.5
        assert sample_modification.new_confidence == 0.8

    def test_default_values(self):
        mod = ModificationHistory(
            timestamp=datetime.now(),
            modification_type="created",
            agent_id="agent_x",
        )
        assert mod.previous_confidence is None
        assert mod.new_confidence is None
        assert mod.reason == ""
        assert mod.metadata == {}

    def test_to_dict(self, sample_modification):
        d = sample_modification.to_dict()
        assert d["modification_type"] == "updated"
        assert d["agent_id"] == "agent_watson"
        assert d["previous_confidence"] == 0.5
        assert d["new_confidence"] == 0.8
        assert d["reason"] == "New evidence found"
        assert d["metadata"] == {"source": "interview"}
        assert d["timestamp"] == "2025-01-15T10:30:00"

    def test_from_dict(self):
        data = {
            "timestamp": "2025-06-01T12:00:00",
            "modification_type": "validated",
            "agent_id": "sherlock",
            "previous_confidence": 0.3,
            "new_confidence": 0.9,
            "reason": "Proof found",
            "metadata": {"key": "value"},
        }
        mod = ModificationHistory.from_dict(data)
        assert mod.timestamp == datetime(2025, 6, 1, 12, 0, 0)
        assert mod.modification_type == "validated"
        assert mod.agent_id == "sherlock"
        assert mod.new_confidence == 0.9

    def test_from_dict_minimal(self):
        data = {
            "timestamp": "2025-01-01T00:00:00",
            "modification_type": "created",
            "agent_id": "system",
        }
        mod = ModificationHistory.from_dict(data)
        assert mod.previous_confidence is None
        assert mod.new_confidence is None
        assert mod.reason == ""
        assert mod.metadata == {}

    def test_roundtrip(self, sample_modification):
        d = sample_modification.to_dict()
        restored = ModificationHistory.from_dict(d)
        assert restored.modification_type == sample_modification.modification_type
        assert restored.agent_id == sample_modification.agent_id
        assert restored.previous_confidence == sample_modification.previous_confidence
        assert restored.new_confidence == sample_modification.new_confidence
        assert restored.reason == sample_modification.reason


# ============================================================
# BeliefMetadata
# ============================================================


class TestBeliefMetadata:
    """Tests for the BeliefMetadata dataclass."""

    @pytest.fixture
    def sample_metadata(self):
        now = datetime(2025, 3, 1, 9, 0, 0)
        return BeliefMetadata(
            belief_type=BeliefType.HYPOTHESIS,
            source_agent="watson",
            creation_timestamp=now,
            last_modified=now,
            confidence_level=ConfidenceLevel.MEDIUM,
            evidence_quality=EvidenceQuality.CIRCUMSTANTIAL,
        )

    def test_creation(self, sample_metadata):
        assert sample_metadata.belief_type is BeliefType.HYPOTHESIS
        assert sample_metadata.source_agent == "watson"
        assert sample_metadata.confidence_level is ConfidenceLevel.MEDIUM
        assert sample_metadata.evidence_quality is EvidenceQuality.CIRCUMSTANTIAL

    def test_default_lists(self, sample_metadata):
        assert sample_metadata.related_evidence == []
        assert sample_metadata.supporting_beliefs == []
        assert sample_metadata.contradicting_beliefs == []
        assert sample_metadata.critique_notes == []
        assert sample_metadata.justification_chain == []
        assert sample_metadata.shared_with_agents == []
        assert sample_metadata.conflict_resolutions == []

    def test_default_dicts(self, sample_metadata):
        assert sample_metadata.investigation_context == {}
        assert sample_metadata.dependency_graph == {}
        assert sample_metadata.sync_status == {}

    def test_default_strings(self, sample_metadata):
        assert sample_metadata.validation_status == "pending"
        assert sample_metadata.truth_maintenance_status == "active"

    def test_default_nones(self, sample_metadata):
        assert sample_metadata.validation_agent is None
        assert sample_metadata.validation_confidence is None

    def test_update_confidence_level(self, sample_metadata):
        old_modified = sample_metadata.last_modified
        sample_metadata.update_confidence_level(0.85)
        assert sample_metadata.confidence_level is ConfidenceLevel.VERY_HIGH
        assert sample_metadata.last_modified >= old_modified

    def test_update_confidence_level_low(self, sample_metadata):
        sample_metadata.update_confidence_level(0.15)
        assert sample_metadata.confidence_level is ConfidenceLevel.VERY_LOW

    def test_add_related_evidence(self, sample_metadata):
        sample_metadata.add_related_evidence("ev1")
        assert "ev1" in sample_metadata.related_evidence
        # No duplicates
        sample_metadata.add_related_evidence("ev1")
        assert sample_metadata.related_evidence.count("ev1") == 1

    def test_add_supporting_belief(self, sample_metadata):
        sample_metadata.add_supporting_belief("b1")
        assert "b1" in sample_metadata.supporting_beliefs
        sample_metadata.add_supporting_belief("b1")
        assert len(sample_metadata.supporting_beliefs) == 1

    def test_add_contradicting_belief(self, sample_metadata):
        sample_metadata.add_contradicting_belief("c1")
        assert "c1" in sample_metadata.contradicting_beliefs
        sample_metadata.add_contradicting_belief("c1")
        assert len(sample_metadata.contradicting_beliefs) == 1

    def test_set_validation_result(self, sample_metadata):
        sample_metadata.set_validation_result("sherlock", "validated", 0.95)
        assert sample_metadata.validation_status == "validated"
        assert sample_metadata.validation_agent == "sherlock"
        assert sample_metadata.validation_confidence == 0.95

    def test_set_validation_result_no_confidence(self, sample_metadata):
        sample_metadata.set_validation_result("watson", "invalidated")
        assert sample_metadata.validation_status == "invalidated"
        assert sample_metadata.validation_confidence is None

    def test_add_critique(self, sample_metadata):
        sample_metadata.add_critique("Weak premise")
        assert "Weak premise" in sample_metadata.critique_notes
        sample_metadata.add_critique("Missing evidence")
        assert len(sample_metadata.critique_notes) == 2

    def test_share_with_agent(self, sample_metadata):
        sample_metadata.share_with_agent("sherlock", "synced")
        assert "sherlock" in sample_metadata.shared_with_agents
        assert sample_metadata.sync_status["sherlock"] == "synced"

    def test_share_with_agent_no_duplicate(self, sample_metadata):
        sample_metadata.share_with_agent("sherlock", "pending")
        sample_metadata.share_with_agent("sherlock", "synced")
        assert sample_metadata.shared_with_agents.count("sherlock") == 1
        assert sample_metadata.sync_status["sherlock"] == "synced"

    def test_to_dict(self, sample_metadata):
        d = sample_metadata.to_dict()
        assert d["belief_type"] == "hypothesis"
        assert d["source_agent"] == "watson"
        assert d["confidence_level"] == "MEDIUM"
        assert d["evidence_quality"] == "circumstantial"
        assert d["validation_status"] == "pending"
        assert d["truth_maintenance_status"] == "active"

    def test_from_dict(self):
        data = {
            "belief_type": "fact",
            "source_agent": "sherlock",
            "creation_timestamp": "2025-01-01T00:00:00",
            "last_modified": "2025-01-02T00:00:00",
            "confidence_level": "HIGH",
            "evidence_quality": "verified",
            "related_evidence": ["ev1"],
            "supporting_beliefs": ["b1"],
            "validation_status": "validated",
            "validation_agent": "watson",
        }
        meta = BeliefMetadata.from_dict(data)
        assert meta.belief_type is BeliefType.FACT
        assert meta.confidence_level is ConfidenceLevel.HIGH
        assert meta.evidence_quality is EvidenceQuality.VERIFIED
        assert "ev1" in meta.related_evidence
        assert meta.validation_agent == "watson"

    def test_roundtrip(self, sample_metadata):
        sample_metadata.add_related_evidence("ev1")
        sample_metadata.share_with_agent("sherlock")
        d = sample_metadata.to_dict()
        restored = BeliefMetadata.from_dict(d)
        assert restored.belief_type is sample_metadata.belief_type
        assert restored.source_agent == sample_metadata.source_agent
        assert restored.related_evidence == sample_metadata.related_evidence
        assert restored.shared_with_agents == sample_metadata.shared_with_agents


# ============================================================
# ExtendedBeliefModel
# ============================================================


class TestExtendedBeliefModel:
    """Tests for the ExtendedBeliefModel dataclass."""

    @pytest.fixture
    def sample_belief(self):
        meta = BeliefMetadata(
            belief_type=BeliefType.EVIDENCE,
            source_agent="watson",
            creation_timestamp=datetime(2025, 1, 1),
            last_modified=datetime(2025, 1, 1),
            confidence_level=ConfidenceLevel.HIGH,
            evidence_quality=EvidenceQuality.VERIFIED,
        )
        return ExtendedBeliefModel(
            belief_id="b001",
            belief_name="suspect_at_scene",
            content="The suspect was seen at the crime scene.",
            confidence=0.75,
            metadata=meta,
        )

    @pytest.fixture
    def default_belief(self):
        return ExtendedBeliefModel(
            belief_id="b002",
            belief_name="weapon_found",
            content="A weapon was found nearby.",
            confidence=0.5,
        )

    def test_creation_with_metadata(self, sample_belief):
        assert sample_belief.belief_id == "b001"
        assert sample_belief.belief_name == "suspect_at_scene"
        assert sample_belief.confidence == 0.75
        assert sample_belief.valid is None
        assert sample_belief.metadata.belief_type is BeliefType.EVIDENCE

    def test_creation_default_metadata(self, default_belief):
        assert default_belief.metadata is not None
        assert default_belief.metadata.belief_type is BeliefType.FACT
        assert default_belief.metadata.source_agent == "unknown"
        assert (
            default_belief.metadata.evidence_quality is EvidenceQuality.CIRCUMSTANTIAL
        )

    def test_creation_records_history(self, default_belief):
        assert len(default_belief.modification_history) >= 1
        assert default_belief.modification_history[0].modification_type == "created"

    def test_get_confidence_level(self, sample_belief):
        assert sample_belief._get_confidence_level(0.1) is ConfidenceLevel.VERY_LOW
        assert sample_belief._get_confidence_level(0.3) is ConfidenceLevel.LOW
        assert sample_belief._get_confidence_level(0.5) is ConfidenceLevel.MEDIUM
        assert sample_belief._get_confidence_level(0.7) is ConfidenceLevel.HIGH
        assert sample_belief._get_confidence_level(0.9) is ConfidenceLevel.VERY_HIGH

    def test_get_confidence_level_out_of_range(self, sample_belief):
        # 1.0 is not contained in any range, returns MEDIUM fallback
        result = sample_belief._get_confidence_level(1.0)
        assert result is ConfidenceLevel.MEDIUM

    def test_update_confidence(self, sample_belief):
        sample_belief.update_confidence(0.9, "sherlock", "New witness testimony")
        assert sample_belief.confidence == 0.9
        assert sample_belief.metadata.confidence_level is ConfidenceLevel.VERY_HIGH
        # History should have creation + update
        updates = [
            m
            for m in sample_belief.modification_history
            if m.modification_type == "updated"
        ]
        assert len(updates) == 1
        assert updates[0].previous_confidence == 0.75
        assert updates[0].new_confidence == 0.9

    def test_validate(self, sample_belief):
        sample_belief.validate("sherlock", 0.95, "Confirmed by DNA evidence")
        assert sample_belief.valid is True
        assert sample_belief.metadata.validation_status == "validated"
        assert sample_belief.metadata.validation_confidence == 0.95
        assert any("Validation:" in c for c in sample_belief.metadata.critique_notes)

    def test_validate_without_notes(self, sample_belief):
        sample_belief.validate("sherlock")
        assert sample_belief.valid is True
        assert sample_belief.metadata.validation_status == "validated"

    def test_invalidate(self, sample_belief):
        sample_belief.invalidate("watson", "Alibi confirmed")
        assert sample_belief.valid is False
        assert sample_belief.metadata.validation_status == "invalidated"
        assert sample_belief.metadata.truth_maintenance_status == "invalidated"

    def test_add_justification(self, sample_belief):
        sample_belief.add_justification("j001", "watson")
        assert "j001" in sample_belief.justifications
        assert "j001" in sample_belief.metadata.justification_chain

    def test_add_justification_no_duplicate(self, sample_belief):
        sample_belief.add_justification("j001", "watson")
        sample_belief.add_justification("j001", "watson")
        assert sample_belief.justifications.count("j001") == 1

    def test_add_dependency(self, sample_belief):
        sample_belief.add_dependency("b010", "watson")
        assert "b010" in sample_belief.depends_on
        assert "b010" in sample_belief.metadata.dependency_graph.get("depends_on", [])

    def test_add_dependency_no_duplicate(self, sample_belief):
        sample_belief.add_dependency("b010", "watson")
        sample_belief.add_dependency("b010", "watson")
        assert sample_belief.depends_on.count("b010") == 1

    def test_add_support(self, sample_belief):
        sample_belief.add_support("b020", "sherlock")
        assert "b020" in sample_belief.supports
        assert "b020" in sample_belief.metadata.dependency_graph.get("supports", [])

    def test_add_support_no_duplicate(self, sample_belief):
        sample_belief.add_support("b020", "sherlock")
        sample_belief.add_support("b020", "sherlock")
        assert sample_belief.supports.count("b020") == 1

    def test_derive_from_rule(self, sample_belief):
        sample_belief.derive_from_rule("modus_ponens", ["b100", "b101"], "sherlock")
        assert sample_belief.is_derived is True
        assert sample_belief.derivation_rule == "modus_ponens"
        assert "b100" in sample_belief.depends_on
        assert "b101" in sample_belief.depends_on
        assert any("modus_ponens" in t for t in sample_belief.computation_trace)

    def test_derive_from_rule_no_duplicate_deps(self, sample_belief):
        sample_belief.depends_on.append("b100")
        sample_belief.derive_from_rule("rule1", ["b100", "b200"], "watson")
        assert sample_belief.depends_on.count("b100") == 1
        assert "b200" in sample_belief.depends_on

    def test_record_modification(self, sample_belief):
        initial_count = len(sample_belief.modification_history)
        sample_belief.record_modification("custom_action", "agent_x", "Test reason")
        assert len(sample_belief.modification_history) == initial_count + 1
        last = sample_belief.modification_history[-1]
        assert last.modification_type == "custom_action"
        assert last.agent_id == "agent_x"

    def test_get_modification_summary_empty(self):
        belief = ExtendedBeliefModel.__new__(ExtendedBeliefModel)
        belief.modification_history = []
        belief.metadata = BeliefMetadata(
            belief_type=BeliefType.FACT,
            source_agent="test",
            creation_timestamp=datetime.now(),
            last_modified=datetime.now(),
            confidence_level=ConfidenceLevel.MEDIUM,
            evidence_quality=EvidenceQuality.CIRCUMSTANTIAL,
        )
        summary = belief.get_modification_summary()
        assert summary["total_modifications"] == 0

    def test_get_modification_summary(self, sample_belief):
        sample_belief.update_confidence(0.9, "sherlock", "Updated")
        summary = sample_belief.get_modification_summary()
        assert summary["total_modifications"] >= 2
        assert "created" in summary["modification_types"]
        assert "updated" in summary["modification_types"]
        assert (
            "watson" in summary["involved_agents"]
            or "unknown" in summary["involved_agents"]
        )

    def test_is_consistent_with_no_conflict(self, sample_belief, default_belief):
        report = sample_belief.is_consistent_with(default_belief)
        assert report["is_consistent"] is True

    def test_is_consistent_with_direct_contradiction(self):
        b1 = ExtendedBeliefModel(
            belief_id="b1", belief_name="guilty", content="Guilty", confidence=0.8
        )
        b2 = ExtendedBeliefModel(
            belief_id="b2",
            belief_name="not_guilty",
            content="Not guilty",
            confidence=0.8,
        )
        report = b1.is_consistent_with(b2)
        assert report["is_consistent"] is False
        assert report["conflict_type"] == "direct_contradiction"

    def test_is_consistent_with_direct_contradiction_reversed(self):
        b1 = ExtendedBeliefModel(
            belief_id="b1",
            belief_name="not_guilty",
            content="Not guilty",
            confidence=0.8,
        )
        b2 = ExtendedBeliefModel(
            belief_id="b2", belief_name="guilty", content="Guilty", confidence=0.8
        )
        report = b1.is_consistent_with(b2)
        assert report["is_consistent"] is False
        assert report["conflict_type"] == "direct_contradiction"

    def test_is_consistent_with_validation_conflict(self):
        b1 = ExtendedBeliefModel(
            belief_id="b1", belief_name="alibi", content="Alibi", confidence=0.7
        )
        b2 = ExtendedBeliefModel(
            belief_id="b2", belief_name="alibi", content="Alibi", confidence=0.7
        )
        b1.valid = True
        b2.valid = False
        report = b1.is_consistent_with(b2)
        assert report["is_consistent"] is False
        assert report["conflict_type"] == "validation_conflict"
        assert report["validation_consistency"] is False

    def test_is_consistent_with_validation_consistent(self):
        b1 = ExtendedBeliefModel(
            belief_id="b1", belief_name="alibi", content="Alibi", confidence=0.7
        )
        b2 = ExtendedBeliefModel(
            belief_id="b2", belief_name="alibi", content="Alibi", confidence=0.7
        )
        b1.valid = True
        b2.valid = True
        report = b1.is_consistent_with(b2)
        assert report["is_consistent"] is True
        assert report["validation_consistency"] is True

    def test_is_consistent_with_high_confidence_difference(self):
        b1 = ExtendedBeliefModel(
            belief_id="b1", belief_name="x", content="X", confidence=0.1
        )
        b2 = ExtendedBeliefModel(
            belief_id="b2", belief_name="y", content="Y", confidence=0.9
        )
        report = b1.is_consistent_with(b2)
        assert report["confidence_difference"] == pytest.approx(0.8)
        assert report["conflict_type"] == "confidence_conflict"
        assert report["conflict_details"].get("high_confidence_difference") is True

    def test_to_dict_with_history(self, sample_belief):
        d = sample_belief.to_dict(include_history=True)
        assert d["belief_id"] == "b001"
        assert d["belief_name"] == "suspect_at_scene"
        assert d["confidence"] == 0.75
        assert "modification_history" in d
        assert "modification_summary" in d
        assert d["metadata"]["belief_type"] == "evidence"

    def test_to_dict_without_history(self, sample_belief):
        d = sample_belief.to_dict(include_history=False)
        assert "modification_history" not in d
        assert "modification_summary" not in d

    def test_from_dict(self, sample_belief):
        d = sample_belief.to_dict(include_history=True)
        restored = ExtendedBeliefModel.from_dict(d)
        assert restored.belief_id == sample_belief.belief_id
        assert restored.belief_name == sample_belief.belief_name
        assert restored.confidence == sample_belief.confidence
        assert restored.metadata.belief_type is sample_belief.metadata.belief_type

    def test_from_dict_minimal(self):
        data = {
            "belief_id": "bx",
            "belief_name": "test",
            "content": "Test content",
            "confidence": 0.5,
        }
        belief = ExtendedBeliefModel.from_dict(data)
        assert belief.belief_id == "bx"
        assert belief.justifications == []
        assert belief.is_derived is False

    def test_from_dict_with_metadata(self):
        data = {
            "belief_id": "b99",
            "belief_name": "complex",
            "content": "Complex belief",
            "confidence": 0.6,
            "metadata": {
                "belief_type": "deduction",
                "source_agent": "watson",
                "creation_timestamp": "2025-01-01T00:00:00",
                "last_modified": "2025-01-02T00:00:00",
                "confidence_level": "HIGH",
                "evidence_quality": "corroborated",
            },
            "justifications": ["j1", "j2"],
            "depends_on": ["d1"],
            "is_derived": True,
            "derivation_rule": "modus_tollens",
        }
        belief = ExtendedBeliefModel.from_dict(data)
        assert belief.metadata.belief_type is BeliefType.DEDUCTION
        assert belief.justifications == ["j1", "j2"]
        assert belief.is_derived is True
        assert belief.derivation_rule == "modus_tollens"

    def test_str_valid_true(self, sample_belief):
        sample_belief.valid = True
        s = str(sample_belief)
        assert "suspect_at_scene" in s
        assert "evidence" in s

    def test_str_valid_false(self, sample_belief):
        sample_belief.valid = False
        s = str(sample_belief)
        assert "suspect_at_scene" in s

    def test_str_valid_none(self, default_belief):
        s = str(default_belief)
        assert "weapon_found" in s

    def test_repr(self, sample_belief):
        r = repr(sample_belief)
        assert "ExtendedBeliefModel" in r
        assert "b001" in r
        assert "suspect_at_scene" in r

    def test_default_fields(self, default_belief):
        assert default_belief.justifications == []
        assert default_belief.depends_on == []
        assert default_belief.supports == []
        assert default_belief.is_derived is False
        assert default_belief.derivation_rule is None
        assert default_belief.computation_trace == []

    def test_full_workflow(self):
        """Integration test: create, update, validate, derive."""
        belief = ExtendedBeliefModel(
            belief_id="w001",
            belief_name="witness_statement",
            content="Witness saw the suspect",
            confidence=0.4,
        )
        assert belief.metadata.confidence_level is ConfidenceLevel.MEDIUM

        belief.update_confidence(0.7, "watson", "Corroborated by CCTV")
        assert belief.confidence == 0.7

        belief.add_justification("cctv_footage", "watson")
        belief.add_dependency("cctv_evidence", "watson")
        belief.add_support("timeline_match", "sherlock")

        belief.validate("sherlock", 0.9, "All evidence aligns")
        assert belief.valid is True

        summary = belief.get_modification_summary()
        assert summary["total_modifications"] >= 5
        assert "watson" in summary["involved_agents"]
        assert "sherlock" in summary["involved_agents"]

        d = belief.to_dict()
        restored = ExtendedBeliefModel.from_dict(d)
        assert restored.belief_id == "w001"
        assert restored.valid is True
