# tests/unit/argumentation_analysis/models/test_agent_communication_model.py
"""Tests for AgentCommunicationModel — enums, MessageMetadata, AgentMessage,
CommunicationProtocol, SyncOperation, and utility functions."""

import json
import pytest
from datetime import datetime, timedelta

from argumentation_analysis.models.agent_communication_model import (
    MessageType,
    MessagePriority,
    CommunicationProtocolType,
    SyncOperationType,
    MessageMetadata,
    AgentMessage,
    CommunicationProtocol,
    SyncOperation,
    create_sherlock_watson_protocol,
    create_validation_request_message,
    create_critique_request_message,
    create_sync_request_message,
)


# ── Enums ──


class TestEnums:
    def test_message_type_values(self):
        assert MessageType.BELIEF_SHARE.value == "belief_share"
        assert MessageType.VALIDATION_REQUEST.value == "validation_request"
        assert MessageType.ERROR_NOTIFICATION.value == "error_notification"

    def test_message_priority_values(self):
        assert MessagePriority.LOW.value == "low"
        assert MessagePriority.URGENT.value == "urgent"

    def test_protocol_type_values(self):
        assert CommunicationProtocolType.DIRECT.value == "direct"
        assert CommunicationProtocolType.BROADCAST.value == "broadcast"

    def test_sync_operation_type_values(self):
        assert SyncOperationType.INCREMENTAL.value == "incremental"
        assert SyncOperationType.MERGE.value == "merge"


# ── MessageMetadata ──


class TestMessageMetadata:
    def _make_metadata(self, **kwargs):
        defaults = {
            "message_id": "",
            "timestamp": datetime(2026, 1, 1, 12, 0),
            "sender_id": "sherlock",
            "receiver_id": "watson",
            "message_type": MessageType.BELIEF_SHARE,
            "priority": MessagePriority.NORMAL,
        }
        defaults.update(kwargs)
        return MessageMetadata(**defaults)

    def test_auto_id_generation(self):
        m = self._make_metadata()
        assert m.message_id.startswith("msg_")

    def test_explicit_id(self):
        m = self._make_metadata(message_id="my_id")
        assert m.message_id == "my_id"

    def test_default_statuses(self):
        m = self._make_metadata()
        assert m.delivery_status == "pending"
        assert m.processed_status == "unprocessed"

    def test_mark_delivered(self):
        m = self._make_metadata()
        m.mark_delivered()
        assert m.delivery_status == "delivered"

    def test_mark_processed(self):
        m = self._make_metadata()
        m.mark_processed()
        assert m.processed_status == "processed"

    def test_mark_failed(self):
        m = self._make_metadata()
        m.mark_failed("timeout")
        assert m.delivery_status == "failed"
        assert m.processed_status == "error"
        assert m.investigation_context["failure_reason"] == "timeout"

    def test_increment_retry(self):
        m = self._make_metadata(max_retries=2)
        assert m.increment_retry() is True   # retry_count = 1
        assert m.increment_retry() is True   # retry_count = 2
        assert m.increment_retry() is False  # retry_count = 3 > max_retries=2

    def test_is_expired_no_timeout(self):
        m = self._make_metadata()
        assert m.is_expired() is False

    def test_is_expired_with_timeout(self):
        m = self._make_metadata(
            timestamp=datetime.now() - timedelta(minutes=10),
            response_timeout=timedelta(minutes=5),
        )
        assert m.is_expired() is True

    def test_is_not_expired(self):
        m = self._make_metadata(
            timestamp=datetime.now(),
            response_timeout=timedelta(minutes=5),
        )
        assert m.is_expired() is False

    def test_to_dict(self):
        m = self._make_metadata(session_id="s1")
        d = m.to_dict()
        assert d["sender_id"] == "sherlock"
        assert d["receiver_id"] == "watson"
        assert d["message_type"] == "belief_share"
        assert d["priority"] == "normal"
        assert d["session_id"] == "s1"

    def test_to_dict_response_timeout(self):
        m = self._make_metadata(response_timeout=timedelta(seconds=30))
        d = m.to_dict()
        assert d["response_timeout"] == 30.0

    def test_from_dict_roundtrip(self):
        m = self._make_metadata(
            message_id="test_id",
            session_id="s1",
            response_timeout=timedelta(seconds=60),
        )
        d = m.to_dict()
        restored = MessageMetadata.from_dict(d)
        assert restored.message_id == "test_id"
        assert restored.session_id == "s1"
        assert restored.response_timeout == timedelta(seconds=60)
        assert restored.message_type == MessageType.BELIEF_SHARE


# ── AgentMessage ──


class TestAgentMessage:
    def _make_message(self, msg_type=MessageType.BELIEF_SHARE, payload=None):
        if payload is None:
            payload = {"belief_id": "b1", "belief_data": {"val": True}}
        metadata = MessageMetadata(
            message_id="",
            timestamp=datetime.now(),
            sender_id="sherlock",
            receiver_id="watson",
            message_type=msg_type,
            priority=MessagePriority.NORMAL,
        )
        return AgentMessage(metadata=metadata, payload=payload)

    def test_creation_with_valid_payload(self):
        msg = self._make_message()
        assert msg.checksum is not None
        assert msg.schema_version == "1.0"

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValueError, match="manque les champs"):
            self._make_message(
                msg_type=MessageType.BELIEF_SHARE,
                payload={"wrong_field": "value"},
            )

    def test_validation_request_missing_fields(self):
        with pytest.raises(ValueError):
            self._make_message(
                msg_type=MessageType.VALIDATION_REQUEST,
                payload={"target_belief": "b1"},  # missing validation_criteria
            )

    def test_verify_integrity(self):
        msg = self._make_message()
        assert msg.verify_integrity() is True

    def test_integrity_fails_after_modification(self):
        msg = self._make_message()
        msg.payload["extra"] = "tampered"
        assert msg.verify_integrity() is False

    def test_is_response_to_reply(self):
        original = self._make_message()
        reply_metadata = MessageMetadata(
            message_id="reply1",
            timestamp=datetime.now(),
            sender_id="watson",
            receiver_id="sherlock",
            message_type=MessageType.STATUS_UPDATE,
            priority=MessagePriority.NORMAL,
            reply_to=original.metadata.message_id,
        )
        reply = AgentMessage(
            metadata=reply_metadata,
            payload={"status_type": "ack", "status_data": {}},
        )
        assert reply.is_response_to(original) is True

    def test_is_response_to_correlation(self):
        original = self._make_message()
        reply_metadata = MessageMetadata(
            message_id="reply2",
            timestamp=datetime.now(),
            sender_id="watson",
            receiver_id="sherlock",
            message_type=MessageType.STATUS_UPDATE,
            priority=MessagePriority.NORMAL,
            correlation_id=original.metadata.message_id,
        )
        reply = AgentMessage(
            metadata=reply_metadata,
            payload={"status_type": "ack", "status_data": {}},
        )
        assert reply.is_response_to(original) is True

    def test_create_response_validation(self):
        request = self._make_message(
            msg_type=MessageType.VALIDATION_REQUEST,
            payload={"target_belief": "b1", "validation_criteria": {"strict": True}},
        )
        response = request.create_response(
            {"validation_result": True},
            response_type=MessageType.VALIDATION_RESPONSE,
        )
        assert response.metadata.message_type == MessageType.VALIDATION_RESPONSE
        assert response.metadata.sender_id == "watson"
        assert response.metadata.receiver_id == "sherlock"
        assert response.payload["original_request_id"] == request.metadata.message_id

    def test_create_response_auto_type(self):
        request = self._make_message(
            msg_type=MessageType.CRITIQUE_REQUEST,
            payload={"target_hypothesis": "h1", "critique_scope": ["logic"]},
        )
        response = request.create_response({"critique_result": "ok"})
        assert response.metadata.message_type == MessageType.CRITIQUE_RESPONSE

    def test_create_response_unknown_type_defaults_to_status(self):
        msg = self._make_message(
            msg_type=MessageType.BELIEF_SHARE,
            payload={"belief_id": "b1", "belief_data": {}},
        )
        response = msg.create_response({"status_type": "ack", "status_data": {}})
        assert response.metadata.message_type == MessageType.STATUS_UPDATE

    def test_add_and_get_context(self):
        msg = self._make_message()
        msg.add_context("investigation_phase", "hypothesis")
        assert msg.get_context("investigation_phase") == "hypothesis"
        assert msg.get_context("missing", "default") == "default"

    def test_to_dict(self):
        msg = self._make_message()
        d = msg.to_dict()
        assert "metadata" in d
        assert "payload" in d
        assert "checksum" in d
        assert d["schema_version"] == "1.0"

    def test_from_dict_roundtrip(self):
        msg = self._make_message()
        d = msg.to_dict()
        restored = AgentMessage.from_dict(d)
        assert restored.metadata.sender_id == "sherlock"
        assert restored.payload["belief_id"] == "b1"
        assert restored.checksum == msg.checksum

    def test_str_representation(self):
        msg = self._make_message()
        s = str(msg)
        assert "belief_share" in s
        assert "sherlock" in s
        assert "watson" in s


# ── CommunicationProtocol ──


class TestCommunicationProtocol:
    @pytest.fixture
    def protocol(self):
        return CommunicationProtocol(
            protocol_id="test_proto",
            protocol_type=CommunicationProtocolType.DIRECT,
            name="Test Protocol",
            supported_message_types=[
                MessageType.BELIEF_SHARE,
                MessageType.VALIDATION_REQUEST,
            ],
        )

    def test_add_agent(self, protocol):
        assert protocol.add_agent("sherlock", "investigator") is True
        assert "sherlock" in protocol.participating_agents
        assert protocol.protocol_roles["sherlock"] == "investigator"

    def test_add_agent_duplicate(self, protocol):
        protocol.add_agent("sherlock")
        assert protocol.add_agent("sherlock") is False

    def test_remove_agent(self, protocol):
        protocol.add_agent("sherlock")
        assert protocol.remove_agent("sherlock") is True
        assert "sherlock" not in protocol.participating_agents

    def test_remove_unknown_agent(self, protocol):
        assert protocol.remove_agent("unknown") is False

    def test_can_send_message_ok(self, protocol):
        protocol.add_agent("sherlock")
        ok, reason = protocol.can_send_message("sherlock", MessageType.BELIEF_SHARE)
        assert ok is True
        assert reason == "Autorisé"

    def test_can_send_inactive(self, protocol):
        protocol.is_active = False
        ok, reason = protocol.can_send_message("sherlock", MessageType.BELIEF_SHARE)
        assert ok is False
        assert "inactif" in reason.lower()

    def test_can_send_non_participant(self, protocol):
        ok, reason = protocol.can_send_message("unknown", MessageType.BELIEF_SHARE)
        assert ok is False
        assert "non participant" in reason.lower()

    def test_can_send_unsupported_type(self, protocol):
        protocol.add_agent("sherlock")
        ok, reason = protocol.can_send_message("sherlock", MessageType.ERROR_NOTIFICATION)
        assert ok is False
        assert "non supporté" in reason

    def test_get_routing_strategy(self, protocol):
        protocol.message_routing = {MessageType.BELIEF_SHARE: "broadcast"}
        assert protocol.get_routing_strategy(MessageType.BELIEF_SHARE) == "broadcast"

    def test_get_routing_default(self, protocol):
        assert protocol.get_routing_strategy(MessageType.STATUS_UPDATE) == "direct"

    def test_validate_message_valid(self, protocol):
        protocol.add_agent("sherlock")
        metadata = MessageMetadata(
            message_id="", timestamp=datetime.now(),
            sender_id="sherlock", receiver_id="watson",
            message_type=MessageType.BELIEF_SHARE,
            priority=MessagePriority.NORMAL,
        )
        msg = AgentMessage(
            metadata=metadata,
            payload={"belief_id": "b1", "belief_data": {}},
        )
        valid, errors = protocol.validate_message(msg)
        assert valid is True
        assert len(errors) == 0

    def test_validate_message_non_participant(self, protocol):
        metadata = MessageMetadata(
            message_id="", timestamp=datetime.now(),
            sender_id="unknown", receiver_id="watson",
            message_type=MessageType.BELIEF_SHARE,
            priority=MessagePriority.NORMAL,
        )
        msg = AgentMessage(
            metadata=metadata,
            payload={"belief_id": "b1", "belief_data": {}},
        )
        valid, errors = protocol.validate_message(msg)
        assert valid is False
        assert len(errors) > 0

    def test_update_usage(self, protocol):
        assert protocol.last_used is None
        protocol.update_usage()
        assert protocol.last_used is not None

    def test_to_dict(self, protocol):
        protocol.add_agent("sherlock")
        d = protocol.to_dict()
        assert d["protocol_id"] == "test_proto"
        assert d["protocol_type"] == "direct"
        assert "sherlock" in d["participating_agents"]

    def test_from_dict_roundtrip(self, protocol):
        protocol.add_agent("sherlock", "investigator")
        d = protocol.to_dict()
        restored = CommunicationProtocol.from_dict(d)
        assert restored.protocol_id == "test_proto"
        assert "sherlock" in restored.participating_agents
        assert restored.protocol_roles["sherlock"] == "investigator"


# ── SyncOperation ──


class TestSyncOperation:
    @pytest.fixture
    def sync_op(self):
        return SyncOperation(
            operation_id="sync_001",
            operation_type=SyncOperationType.INCREMENTAL,
            source_agent="sherlock",
            target_agents=["watson"],
        )

    def test_auto_id(self):
        op = SyncOperation(
            operation_id="",
            operation_type=SyncOperationType.FULL,
            source_agent="s",
            target_agents=["t"],
        )
        assert op.operation_id.startswith("sync_")

    def test_initial_state(self, sync_op):
        assert sync_op.status == "pending"
        assert sync_op.progress == 0.0
        assert sync_op.is_active is True
        assert sync_op.is_completed is False

    def test_start(self, sync_op):
        assert sync_op.start() is True
        assert sync_op.status == "running"
        assert sync_op.start_time is not None
        assert len(sync_op.operation_log) >= 1

    def test_start_only_from_pending(self, sync_op):
        sync_op.status = "running"
        assert sync_op.start() is False

    def test_complete(self, sync_op):
        sync_op.start()
        sync_op.complete({"merged": 10})
        assert sync_op.status == "completed"
        assert sync_op.progress == 1.0
        assert sync_op.sync_results["merged"] == 10
        assert sync_op.is_completed is True
        assert sync_op.is_active is False

    def test_fail(self, sync_op):
        sync_op.start()
        sync_op.fail("network error")
        assert sync_op.status == "failed"
        assert sync_op.is_completed is True

    def test_cancel(self, sync_op):
        sync_op.start()
        sync_op.cancel("user request")
        assert sync_op.status == "cancelled"
        assert sync_op.is_completed is True

    def test_update_progress(self, sync_op):
        sync_op.update_progress(0.5, "halfway")
        assert sync_op.progress == 0.5

    def test_progress_clamped(self, sync_op):
        sync_op.update_progress(1.5)
        assert sync_op.progress == 1.0
        sync_op.update_progress(-0.5)
        assert sync_op.progress == 0.0

    def test_add_conflict(self, sync_op):
        sync_op.add_conflict({"conflict_id": "c1", "type": "belief_mismatch"})
        assert len(sync_op.conflicts_detected) == 1
        assert sync_op.conflicts_detected[0]["conflict_id"] == "c1"

    def test_resolve_conflict(self, sync_op):
        sync_op.resolve_conflict("c1", {"strategy": "automatic", "result": "merged"})
        assert len(sync_op.conflicts_resolved) == 1
        assert sync_op.conflicts_resolved[0]["conflict_id"] == "c1"

    def test_duration_seconds(self, sync_op):
        assert sync_op.duration_seconds == 0.0
        sync_op.start()
        assert sync_op.duration_seconds >= 0.0

    def test_log_event(self, sync_op):
        sync_op.log_event("test", {"key": "value"})
        assert len(sync_op.operation_log) == 1
        assert sync_op.operation_log[0]["event_type"] == "test"

    def test_get_summary(self, sync_op):
        sync_op.items_synchronized = 5
        sync_op.items_skipped = 2
        summary = sync_op.get_summary()
        assert summary["operation_id"] == "sync_001"
        assert summary["items_synchronized"] == 5
        assert summary["items_skipped"] == 2
        assert summary["status"] == "pending"

    def test_to_dict(self, sync_op):
        d = sync_op.to_dict()
        assert d["operation_id"] == "sync_001"
        assert d["operation_type"] == "incremental"
        assert d["source_agent"] == "sherlock"
        assert "summary" in d

    def test_from_dict_roundtrip(self, sync_op):
        sync_op.start()
        sync_op.add_conflict({"conflict_id": "c1", "type": "test"})
        sync_op.items_synchronized = 10
        d = sync_op.to_dict()
        restored = SyncOperation.from_dict(d)
        assert restored.operation_id == "sync_001"
        assert restored.status == "running"
        assert restored.items_synchronized == 10
        assert len(restored.conflicts_detected) == 1


# ── Utility Functions ──


class TestUtilityFunctions:
    def test_create_sherlock_watson_protocol(self):
        proto = create_sherlock_watson_protocol()
        assert proto.protocol_id == "sherlock_watson_v1"
        assert proto.protocol_type == CommunicationProtocolType.HUB_MEDIATED
        assert MessageType.BELIEF_SHARE in proto.supported_message_types
        assert MessageType.VALIDATION_REQUEST in proto.supported_message_types
        assert MessageType.SYNC_REQUEST in proto.supported_message_types
        assert proto.response_timeout == timedelta(minutes=2)

    def test_create_validation_request_message(self):
        msg = create_validation_request_message(
            sender_id="sherlock",
            receiver_id="watson",
            belief_id="b1",
            validation_criteria={"strict": True},
            session_id="s1",
        )
        assert msg.metadata.message_type == MessageType.VALIDATION_REQUEST
        assert msg.metadata.priority == MessagePriority.HIGH
        assert msg.metadata.requires_response is True
        assert msg.payload["target_belief"] == "b1"
        assert msg.payload["validation_criteria"]["strict"] is True

    def test_create_critique_request_message(self):
        msg = create_critique_request_message(
            sender_id="watson",
            receiver_id="sherlock",
            hypothesis_data={"hypothesis": "Colonel Mustard"},
            session_id="s1",
        )
        assert msg.metadata.message_type == MessageType.CRITIQUE_REQUEST
        assert msg.metadata.requires_response is True
        assert msg.payload["target_hypothesis"]["hypothesis"] == "Colonel Mustard"
        assert "critique_scope" in msg.payload

    def test_create_sync_request_message(self):
        msg = create_sync_request_message(
            sender_id="sherlock",
            receiver_id="watson",
            sync_type="incremental",
            source_data={"beliefs": ["b1", "b2"]},
        )
        assert msg.metadata.message_type == MessageType.SYNC_REQUEST
        assert msg.payload["sync_type"] == "incremental"
        assert msg.payload["source_data"]["beliefs"] == ["b1", "b2"]


# ── Integration ──


class TestIntegration:
    def test_full_message_lifecycle(self):
        """Create protocol, send message, validate, create response."""
        # Create protocol and add agents
        proto = create_sherlock_watson_protocol()
        proto.add_agent("sherlock", "investigator")
        proto.add_agent("watson", "validator")

        # Create validation request
        msg = create_validation_request_message(
            "sherlock", "watson", "b1", {"strict": True}, "session1",
        )

        # Validate message
        valid, errors = proto.validate_message(msg)
        assert valid is True

        # Create response
        response = msg.create_response(
            {"validation_result": True, "confidence": 0.95},
            response_type=MessageType.VALIDATION_RESPONSE,
        )
        assert response.is_response_to(msg) is True
        assert response.metadata.sender_id == "watson"

        # Update protocol usage
        proto.update_usage()
        assert proto.last_used is not None

    def test_sync_operation_lifecycle(self):
        """Full sync: start, progress, conflict, resolve, complete."""
        op = SyncOperation(
            operation_id="sync_test",
            operation_type=SyncOperationType.BIDIRECTIONAL,
            source_agent="sherlock",
            target_agents=["watson", "moriarty"],
        )

        assert op.start() is True
        op.update_progress(0.3, "scanning beliefs")
        op.add_conflict({"conflict_id": "c1", "type": "belief_mismatch"})
        op.resolve_conflict("c1", {"strategy": "merge", "result": "ok"})
        op.items_synchronized = 20
        op.items_skipped = 3
        op.complete({"total_merged": 20})

        summary = op.get_summary()
        assert summary["status"] == "completed"
        assert summary["items_synchronized"] == 20
        assert summary["conflicts_detected"] == 1
        assert summary["conflicts_resolved"] == 1

        # Serialization roundtrip
        d = op.to_dict()
        json_str = json.dumps(d, default=str)
        assert len(json_str) > 100
