# -*- coding: utf-8 -*-
"""#2177 — les clés de charge utile du contenu sont des chaînes sérialisables.

``DATA_DIR`` (un ``pathlib.Path``) servait de clé dans le ``content`` des
messages construits par les adaptateurs hiérarchiques. Écrivain et lecteur
étant auto-cohérents en mémoire (même objet Path des deux côtés), rien ne
cassait avant la frontière de sérialisation : ``json.dumps(Message.to_dict())``
lève ``TypeError`` sur une clé Path, et ``from_dict`` ne peut pas la relire.
Ces gardes fixent le contrat par famille d'adaptateur : chaque message
construit par un écrivain public doit passer le round-trip JSON, et la charge
utile doit vivre sous la clé chaîne ``"data"`` — contrat déjà établi pour
``InformationMessage`` (#2104, message.py) et pour ``send_report``.

La dernière garde verrouille la paire écrivain/lecteur qui déborde du paquet
communication : le handler de directives du coordinateur tactique lit
``content.get("data")`` (orchestration/hierarchical/tactical/coordinator.py,
``_subscribe_to_strategic_directives``) — l'objectif publié par
``StrategicAdapter.broadcast_objective`` doit rester lisible sous cette clé.
"""

import json
from unittest.mock import MagicMock

import pytest

from argumentation_analysis.core.communication.strategic_adapter import (
    StrategicAdapter,
)
from argumentation_analysis.core.communication.tactical_adapter import (
    TacticalAdapter,
)
from argumentation_analysis.core.communication.operational_adapter import (
    OperationalAdapter,
)


@pytest.fixture
def mock_middleware():
    m = MagicMock()
    m.send_message.return_value = True
    m.publish.return_value = []
    m.global_handlers = []
    return m


def sent_messages(mock_mw):
    """Objets Message passés à ``send_message``."""
    return [c.args[0] for c in mock_mw.send_message.call_args_list if c.args]


def published_contents(mock_mw):
    """Contenus passés à ``publish`` (kwargs ``content``)."""
    return [
        c.kwargs["content"]
        for c in mock_mw.publish.call_args_list
        if "content" in c.kwargs
    ]


def assert_message_serializes(message, expected_payload):
    """Le message doit franchir la frontière JSON et y préserver sa charge."""
    as_dict = message.to_dict()
    round_tripped = json.loads(json.dumps(as_dict))  # TypeError si clé Path (#2177)
    assert round_tripped["content"]["data"] == expected_payload


class TestOperationalWriters:
    def test_send_result_payload_serializes(self, mock_middleware):
        adapter = OperationalAdapter("operational_01", mock_middleware)
        payload = {"arguments": ["arg1", "arg2"], "confidence": 0.9}
        adapter.send_result("task-1", "analysis_result", payload, "tactical_01")

        messages = sent_messages(mock_middleware)
        assert len(messages) == 1
        assert_message_serializes(messages[0], payload)

    def test_collaboration_payload_serializes(self, mock_middleware):
        adapter = OperationalAdapter("operational_01", mock_middleware)
        payload = {"note": "review requested"}
        adapter.collaborate_with_operational(
            "peer_review", payload, ["operational_02"], group_id="group-op"
        )

        messages = sent_messages(mock_middleware)
        assert len(messages) == 1
        assert_message_serializes(messages[0], payload)


class TestStrategicWriters:
    def test_broadcast_objective_payload_serializes(self, mock_middleware):
        adapter = StrategicAdapter("strategic_01", mock_middleware)
        payload = {"goal": "analyse", "horizon": "long"}
        adapter.broadcast_objective("global_strategy", payload)

        contents = published_contents(mock_middleware)
        assert len(contents) == 1
        # publish transporte le dict de contenu, pas le Message : la frontière
        # JSON s'applique directement au contenu.
        assert json.loads(json.dumps(contents[0]))["data"] == payload

    def test_broadcast_announcement_payload_serializes(self, mock_middleware):
        adapter = StrategicAdapter("strategic_01", mock_middleware)
        payload = {"change": "policy-v2"}
        adapter.broadcast_announcement("policy_change", payload)

        contents = published_contents(mock_middleware)
        assert len(contents) == 1
        assert json.loads(json.dumps(contents[0]))["data"] == payload

    def test_provide_guidance_payload_serializes(self, mock_middleware):
        adapter = StrategicAdapter("strategic_01", mock_middleware)
        payload = {"recommendation": "focus", "priority": "high"}
        adapter.provide_guidance("req-1", payload)

        messages = sent_messages(mock_middleware)
        assert len(messages) == 1
        assert_message_serializes(messages[0], payload)

    def test_collaboration_payload_serializes(self, mock_middleware):
        adapter = StrategicAdapter("strategic_01", mock_middleware)
        payload = {"topic": "arbitrage"}
        adapter.collaborate_with_strategic(
            "consultation", payload, ["strategic_02"], group_id="group-st"
        )

        messages = sent_messages(mock_middleware)
        assert len(messages) == 1
        assert_message_serializes(messages[0], payload)


class TestTacticalWriters:
    def test_send_status_update_payload_serializes(self, mock_middleware):
        adapter = TacticalAdapter("tactical_01", mock_middleware)
        payload = {"directive_id": "dir-1", "progress": 50}
        adapter.send_status_update("task_progress", payload, "strategic_01")

        messages = sent_messages(mock_middleware)
        assert len(messages) == 1
        assert_message_serializes(messages[0], payload)

    def test_send_report_payload_serializes(self, mock_middleware):
        adapter = TacticalAdapter("tactical_01", mock_middleware)
        payload = {"text_id": "text-1", "arguments": ["arg1"]}
        adapter.send_report("analysis_complete", payload, "strategic_01")

        messages = sent_messages(mock_middleware)
        assert len(messages) == 1
        assert_message_serializes(messages[0], payload)

    def test_collaboration_payload_serializes(self, mock_middleware):
        adapter = TacticalAdapter("tactical_01", mock_middleware)
        payload = {"proposal": "merge"}
        adapter.collaborate_with_tactical(
            "coordination", payload, ["tactical_02"], group_id="group-ta"
        )

        messages = sent_messages(mock_middleware)
        assert len(messages) == 1
        assert_message_serializes(messages[0], payload)


class TestCoordinatorDirectiveContract:
    def test_published_objective_readable_under_data_key(self, mock_middleware):
        """Le handler du coordinateur tactique lit ``content.get("data")``.

        Paire écrivain/lecteur qui s'étend hors du paquet communication :
        ``broadcast_objective`` (strategic_adapter) écrit, le handler de
        directives du coordinateur (orchestration/hierarchical) lit. Les deux
        côtés doivent convenir de la même clé chaîne.
        """
        adapter = StrategicAdapter("strategic_01", mock_middleware)
        decision = {
            "decision_type": "proceed",
            "conclusion": "ok",
            "evaluation": {"score": 0.8},
        }
        adapter.broadcast_objective("strategic_decision", decision)

        contents = published_contents(mock_middleware)
        assert contents, "broadcast_objective doit franchir le middleware"
        # Même expression de lecture que le coordinateur côté lecteur.
        payload = contents[0].get("data", {}) or {}
        assert payload.get("decision_type") == "proceed"
        assert payload.get("conclusion") == "ok"
