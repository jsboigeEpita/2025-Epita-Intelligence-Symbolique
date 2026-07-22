# tests/unit/argumentation_analysis/core/communication/test_broadcast_bus_fix_1500.py
"""Track C2 of #1500 — shared-middleware broadcast bus hole fix.

Reproduces the R653 defect firsthand and asserts the fix. The defect: a shared
``MessageMiddleware`` built with only the HIERARCHICAL channel (as
``main_orchestrator.main()`` and ``service_manager.initialize_middleware`` did
before this track) dropped every ``PUBLICATION`` broadcast — ``determine_channel``
routes a PUBLICATION to the DATA channel, which was unregistered, so
``send_message`` logged ``Channel not found: data`` and returned False. Worse,
the ``publish()`` path's ``send_message`` was *dead* for broadcasts anyway: the
broadcast message carries ``recipient=None``, and both HIERARCHICAL and DATA
channels reject a recipient-less message ("has no recipient"). Result
(coordinator R653): "broadcasted to 0 agents", hierarchical-wide.

The fix has two parts, both asserted here:

* **Fix A** — the two shared-middleware integration sites now use
  :func:`create_default_middleware` (single source of truth, mirror of the
  PR #1479 / R652 delegation-path fix), so the shared bus registers BOTH
  HIERARCHICAL and DATA.
* **Fix B** — ``publish()`` fans the broadcast out to the middleware's
  ``global_handlers`` (the "listen to all messages" mechanism) instead of the
  dead ``send_message``. A registered listener therefore receives the broadcast
  firsthand (DoD bullet 1, anti-#1019: genuine delivery, not a cosmetic flag),
  and no ``Channel not found`` is emitted on the broadcast path (DoD bullet 2).

JVM/LLM-free: pure communication-module machinery on synthetic opaque content.
"""

from __future__ import annotations

import logging

from argumentation_analysis.core.communication.channel_interface import ChannelType
from argumentation_analysis.core.communication.hierarchical_channel import (
    HierarchicalChannel,
)
from argumentation_analysis.core.communication.message import (
    AgentLevel,
    Message,
    MessagePriority,
    MessageType,
)
from argumentation_analysis.core.communication.middleware import (
    MessageMiddleware,
    create_default_middleware,
)
from argumentation_analysis.core.communication.strategic_adapter import (
    StrategicAdapter,
)


class TestFixADefaultMiddlewareWiresBothChannels:
    """Fix A — ``create_default_middleware`` is the single source of truth for
    the shared bus channel set (HIERARCHICAL + DATA), mirroring PR #1479/R652.
    """

    def test_registers_hierarchical_and_data(self) -> None:
        mw = create_default_middleware()
        assert mw.get_channel(ChannelType.HIERARCHICAL) is not None
        assert mw.get_channel(ChannelType.DATA) is not None


class TestDefectReproductionR653:
    """The R653 defect mechanism, reproduced firsthand: a PUBLICATION routed to
    the DATA channel on a HIERARCHICAL-only (pre-fix shared) middleware logs
    ``Channel not found: data`` and the send returns False. This is the
    "before" the fix addresses.
    """

    def test_hierarchical_only_middleware_drops_publication(
        self, caplog: logging.Logger
    ) -> None:
        # Pre-fix shared-middleware setup: HIERARCHICAL channel only.
        mw = MessageMiddleware()
        mw.register_channel(HierarchicalChannel("hierarchical_channel"))
        publication = Message(
            message_type=MessageType.PUBLICATION,
            sender="strategic_alpha",
            sender_level=AgentLevel.STRATEGIC,
            content={},
            recipient=None,
            channel=None,
            priority=MessagePriority.NORMAL,
        )
        with caplog.at_level(logging.ERROR, logger="MessageMiddleware"):
            delivered = mw.send_message(publication)
        # The defect: DATA channel unregistered → "Channel not found: data".
        assert delivered is False
        assert "Channel not found: data" in caplog.text


class TestFixBBroadcastReachesListener:
    """Fix B — ``publish()`` fans the broadcast out to the middleware's global
    handlers so a registered listener (the tactical tier's natural broadcast
    reception) receives it firsthand. DoD bullet 1.
    """

    def test_broadcast_reaches_registered_listener_firsthand(self) -> None:
        mw = create_default_middleware()
        received: list[Message] = []
        mw.register_global_handler(lambda m: received.append(m))
        strategic = StrategicAdapter("strategic_alpha", mw)

        strategic.broadcast_objective("analysis", {"goal": "opaque"})

        # DoD bullet 1 — firsthand reception, not just channel registration.
        assert len(received) == 1
        msg = received[0]
        assert msg.content["objective_type"] == "analysis"
        assert msg.metadata.get("topic") == "objectives.analysis"

    def test_broadcast_without_listener_is_honest_zero(self) -> None:
        # Anti-#1019: with no listener, the broadcast reaches nobody — nothing
        # fabricated, no crash. The path runs cleanly.
        mw = create_default_middleware()
        StrategicAdapter("strategic_alpha", mw).broadcast_objective(
            "analysis", {"goal": "opaque"}
        )


class TestNoChannelNotFoundOnBroadcastPath:
    """DoD bullet 2 — the broadcast path emits no ``Channel not found`` once the
    shared middleware is wired with both channels and ``publish`` fans out via
    handlers (no dead ``send_message`` to hit the missing DATA channel).
    """

    def test_broadcast_emits_no_channel_not_found(self, caplog: logging.Logger) -> None:
        mw = create_default_middleware()
        strategic = StrategicAdapter("strategic_alpha", mw)
        with caplog.at_level(logging.ERROR, logger="MessageMiddleware"):
            strategic.broadcast_objective("analysis", {"goal": "opaque"})
        assert "Channel not found" not in caplog.text
