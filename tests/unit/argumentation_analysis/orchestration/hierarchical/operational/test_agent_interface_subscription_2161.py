# -*- coding: utf-8 -*-
"""#2161 — l'abonnement hiérarchique de OperationalAgent doit réellement livrer.

Trois défauts coexistaient dans `_subscribe_to_tasks` sans jamais faire rougir
un test (mesures R981) : le filtre soumettait des clés que `matches_filter`
ignore (`recipient`, `type`) et un membre d'enum là où le matcher compare des
`.value` (`sender_level`) — l'abonnement n'a jamais déclenché son rappel ; la
boucle d'abonnement par `topic` résolvait les capacités à la construction (le
fail-loud #2159 levait donc à chaque instanciation, avalé par l'`except` nu) ;
et le lecteur du rappel lisait `task_type` là où l'écrivain
(`tactical_adapter.assign_task`) écrit `command_type`.

DoD (R981) tenue ici :
1. triplet de construction {ERROR abonnement, INFO abonné, souscripteurs
   hiérarchique} = {0, 1, 1} sur un adaptateur réel, contrôle positif inclus ;
2. livraison bidirectionnelle : le destinataire visé traite, un autre
   destinataire ne traite PAS, un autre type ne livre PAS ;
3. le lecteur du rappel lit la clé de l'écrivain de production.
"""

import asyncio
import logging

import pytest

from argumentation_analysis.core.communication import (
    AgentLevel,
    ChannelType,
    Message,
    MessageMiddleware,
    MessageType,
    MessagePriority,
)
from argumentation_analysis.core.communication.hierarchical_channel import (
    HierarchicalChannel,
)
from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import (
    OperationalAgent,
)
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import (
    InformalAgentAdapter,
)


def _middleware_with_hierarchical() -> MessageMiddleware:
    middleware = MessageMiddleware()
    middleware.register_channel(HierarchicalChannel("hierarchical_test_2161"))
    return middleware


class _RecordingAgent(OperationalAgent):
    """Agent opérationnel minimal qui enregistre les tâches traitées."""

    def __init__(self, name: str, middleware: MessageMiddleware):
        self.processed = []
        super().__init__(name, middleware=middleware)

    def get_capabilities(self):
        return ["test_capability"]

    def can_process_task(self, task):
        return True

    async def process_task(self, task):
        return {"status": "done"}

    async def _process_task_async(self, task, sender_id):
        self.processed.append((task, sender_id))


def _tactical_command(
    recipient: str, command_type: str = "operational_task"
) -> Message:
    """Message conforme à l'écrivain de production (tactical_adapter.assign_task)."""
    return Message(
        message_type=MessageType.COMMAND,
        sender="tactical_01",
        sender_level=AgentLevel.TACTICAL,
        content={
            "command_type": command_type,
            "parameters": {
                "id": "task-1",
                "required_capabilities": ["test_capability"],
            },
            "constraints": {},
        },
        recipient=recipient,
        channel=ChannelType.HIERARCHICAL.value,
        priority=MessagePriority.NORMAL,
        metadata={},
    )


class TestConstructionTriplet:
    """DoD n°1 : le triplet mesuré {ERROR, INFO, souscripteurs} = {0, 1, 1}."""

    def test_construction_neither_errors_nor_hides_success(self, caplog):
        """Un adaptateur fail-loud (#2159) qui se construit ne doit plus se
        lire comme en échec : plus de ERROR d'abonnement, le INFO de succès
        revient, et l'abonnement hiérarchique est réel (contrôle positif :
        la sonde rend 1 souscripteur, pas 0)."""
        with caplog.at_level(logging.INFO):
            adapter = InformalAgentAdapter(config_name="simple")

        error_subscription = [
            r
            for r in caplog.records
            if r.levelno == logging.ERROR and "abonnement" in r.message
        ]
        info_subscribed = [
            r
            for r in caplog.records
            if r.levelno == logging.INFO
            and "abonné aux tâches opérationnelles" in r.message
        ]
        channel = adapter.middleware.get_channel(ChannelType.HIERARCHICAL)

        assert len(error_subscription) == 0, (
            f"la construction a loggé un échec d'abonnement: "
            f"{[r.message for r in error_subscription]}"
        )
        assert len(info_subscribed) == 1
        # Contrôle positif : le canal hiérarchique porte bien l'abonnement —
        # sans ce 1, les deux assertions précédentes ne prouvent rien.
        assert len(channel.subscribers) == 1
        registered = next(iter(channel.subscribers.values()))
        assert registered["subscriber_id"] == "InformalAgent"


class TestHierarchicalTaskDelivery:
    """DoD n°2 : livraison pour le destinataire visé, non-livraison ailleurs."""

    @pytest.fixture
    def wired(self):
        middleware = _middleware_with_hierarchical()
        agent = _RecordingAgent("operational_test_agent", middleware)
        channel = middleware.get_channel(ChannelType.HIERARCHICAL)
        return middleware, agent, channel

    async def test_command_to_target_agent_is_processed(self, wired):
        _, agent, channel = wired

        assert channel.send_message(_tactical_command("operational_test_agent"))
        await asyncio.sleep(0.1)  # laisse le create_task de handle_task tourner

        assert len(agent.processed) == 1
        task, sender = agent.processed[0]
        assert task["id"] == "task-1"
        assert sender == "tactical_01"

    async def test_command_to_another_agent_is_not_processed(self, wired):
        """Le chemin callback diffuse à tous les abonnés filtrés — le ciblage
        par destinataire doit se tenir côté consommateur (le contrat du
        matcher n'a pas de clé `recipient`, #2161)."""
        _, agent, channel = wired

        assert channel.send_message(_tactical_command("operational_other_agent"))
        await asyncio.sleep(0.1)

        assert agent.processed == []

    async def test_information_message_is_not_delivered(self, wired):
        _, agent, channel = wired

        message = _tactical_command("operational_test_agent")
        message.type = MessageType.INFORMATION
        assert channel.send_message(message)
        await asyncio.sleep(0.1)

        assert agent.processed == []

    async def test_strategic_command_is_not_delivered(self, wired):
        """Le filtre n'accepte que les COMMAND du niveau tactique."""
        _, agent, channel = wired

        message = _tactical_command("operational_test_agent")
        message.sender_level = AgentLevel.STRATEGIC
        assert channel.send_message(message)
        await asyncio.sleep(0.1)

        assert agent.processed == []

    async def test_non_operational_task_command_is_ignored(self, wired):
        """DoD n°3 : le lecteur lit la clé de l'écrivain (`command_type`) —
        une commande d'un autre type ne déclenche pas le traitement."""
        _, agent, channel = wired

        assert channel.send_message(
            _tactical_command("operational_test_agent", command_type="detect_fallacies")
        )
        await asyncio.sleep(0.1)

        assert agent.processed == []
