# tests/unit/argumentation_analysis/core/communication/test_strategic_broadcast_junction_1555.py
"""Track C2 of #1500 — #1555: the strategic→tactical broadcast junction.

``test_broadcast_bus_fix_1500.py`` established the *plumbing* (Fix B: ``publish``
fans out to ``global_handlers`` so a registered listener receives the broadcast
firsthand) and CC #1531 made the *hole* visible (the ``NO subscriber`` warning).
Neither **closed** the hole for production: the tactical coordinator — the one
tier meant to consume strategic decisions — never subscribed. Its
``_subscribe_to_strategic_directives`` had the handler commented out, logged
``"Abonné aux directives stratégiques."`` (affirming the subscription it just
disabled), and called ``subscribe_to_directives`` — a method that did not exist.

The mechanism (issue #1555, established firsthand on ``main``): three pieces.
(1) The handler was commented (coordinator.py); (2) ``subscribe_to_directives``
did not exist — the only subscription primitive is ``subscribe_to_operational_updates``
(``tactical_adapter.py:623``), which uses the **channel** path
(``get_channel(HIERARCHICAL).subscribe``); (3) the publisher emits on the
**topic** path (``middleware.publish(topic_id="objectives.<type>")``), and these
two paths do not meet. ``publish`` delivers to topic subscribers + ``global_handlers``
(pub_sub.py:386/399, middleware.py:419-434) — NEVER to a channel's subscribers.

So the fix is the junction of DoD item 4, **Option A**: the tactical tier
subscribes to the topic ``objectives.strategic_decision`` via
``middleware.subscribe`` (the topic path the publisher actually uses). The shape
mirrors ``subscribe_to_operational_updates`` (adapter method, filter_criteria,
returns a subscription id); the transport is the topic path, because a channel
mirror would leave the broadcast reaching 0 agents. Option B (make the strategic
tier emit on the channel) is rejected — it is exactly the delivery-semantics
change forbidden by ``strategic_adapter.py:177-179``.

These tests prove the production junction firsthand, LLM-free and JVM-free: a
real ``TacticalCoordinator`` subscribes in its ``__init__``, a real
``StrategicAdapter`` broadcasts on the same shared middleware, and the decision
lands in tactical state (a genuine effect, anti-#1019 / anti-pendule: not a
debug listener invented to bump a counter). The no-subscriber guard stays armed
on topics nobody listens to (DoD bullet 3).

Content uses opaque IDs only (corpus_A) — privacy discipline.
"""

from __future__ import annotations

import logging

from argumentation_analysis.core.communication.message import MessagePriority
from argumentation_analysis.core.communication.middleware import (
    create_default_middleware,
)
from argumentation_analysis.core.communication.strategic_adapter import (
    StrategicAdapter,
)
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import (
    TacticalCoordinator,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)

# ── DoD bullet 1+2 — production reception, firsthand, same run ──────────────


class TestStrategicDecisionReachesTacticalFirsthand:
    """A real ``TacticalCoordinator`` receives a strategic broadcast and acts
    on it (records the decision in tactical state). This is the closed hole:
    not a debug listener, a production component that does something.
    """

    def test_tactical_coordinator_records_strategic_decision(self) -> None:
        mw = create_default_middleware()
        tactical_state = TacticalState()
        # Construction subscribes the coordinator to the strategic_decision
        # topic (via _subscribe_to_strategic_directives → subscribe_to_directives).
        TacticalCoordinator(tactical_state=tactical_state, middleware=mw)
        strategic = StrategicAdapter("strategic_manager", mw)

        # Same shared middleware, same run: emission then reception.
        strategic.broadcast_objective(
            "strategic_decision",
            {
                "decision_type": "final_conclusion",
                "conclusion": "corpus_A_coherent",
                "evaluation": {"score": 0.8},
            },
            priority=MessagePriority.HIGH,
        )

        # Firsthand reception — a REAL effect on production state, not a flag.
        received = [
            a
            for a in tactical_state.tactical_actions_log
            if a.get("type") == "strategic_decision_received"
        ]
        assert len(received) == 1, (
            f"expected the tactical coordinator to record the strategic "
            f"decision firsthand; actions log = {tactical_state.tactical_actions_log!r}"
        )
        assert "corpus_A_coherent" in received[0]["description"]
        assert "final_conclusion" in received[0]["description"]


# ── DoD bullet 3 — the no-subscriber guard stays armed ──────────────────────


class TestNoSubscriberGuardArmedAndScoped:
    """The CC #1531 ``NO subscriber`` warning must NOT fire on the now-wired
    ``strategic_decision`` path, and MUST still fire on a topic with nobody
    listening. It must not be neutralized (DoD bullet 3).
    """

    def test_no_warning_when_tactical_subscribed(self, caplog: logging.Logger) -> None:
        mw = create_default_middleware()
        TacticalCoordinator(middleware=mw)
        strategic = StrategicAdapter("strategic_manager", mw)
        with caplog.at_level(
            logging.WARNING, logger="StrategicAdapter.strategic_manager"
        ):
            strategic.broadcast_objective(
                "strategic_decision", {"decision_type": "final_conclusion"}
            )
        assert "NO subscriber" not in caplog.text

    def test_warning_still_fires_when_nobody_listens(
        self, caplog: logging.Logger
    ) -> None:
        # A topic with NO production subscriber → the guard fires. Do not
        # neutralize it.
        mw = create_default_middleware()
        with caplog.at_level(
            logging.WARNING, logger="StrategicAdapter.strategic_manager"
        ):
            StrategicAdapter("strategic_manager", mw).broadcast_objective(
                "global_strategy", {"goal": "opaque"}
            )
        assert "NO subscriber" in caplog.text


# ── Anti-pendule — topic-scoped subscription, not a fabricated catch-all ─────


class TestSubscriptionIsTopicScoped:
    """The junction is a **topic** subscription (Option A), not a
    ``register_global_handler`` invented to bump the reception counter. A
    topic-scoped subscriber receives ``strategic_decision`` and ignores an
    unrelated objective type — proving the scope is real, not a wildcard.
    """

    def test_tactical_ignores_unrelated_objective_type(self) -> None:
        mw = create_default_middleware()
        tactical_state = TacticalState()
        TacticalCoordinator(tactical_state=tactical_state, middleware=mw)
        strategic = StrategicAdapter("strategic_manager", mw)

        # An objective type the coordinator did NOT subscribe to.
        strategic.broadcast_objective("global_strategy", {"goal": "opaque"})

        decisions = [
            a
            for a in tactical_state.tactical_actions_log
            if a.get("type") == "strategic_decision_received"
        ]
        assert decisions == [], (
            "a topic-scoped subscriber must not catch unrelated objective "
            "types — that would be a global catch-all (the fabricated-counter "
            "anti-pattern), not a topic junction"
        )

    def test_subscribe_to_directives_uses_topic_path(self) -> None:
        """Mutation guard: the subscription lands on the topic the publisher
        uses (``objectives.strategic_decision``), reachable via ``publish`` —
        not stranded on a channel that ``publish`` never delivers to.
        """
        mw = create_default_middleware()
        TacticalCoordinator(middleware=mw)
        # The topic must exist and carry the tactical subscriber.
        topic = mw.publish_subscribe.topics.get("objectives.strategic_decision")
        assert topic is not None, (
            "subscribe_to_directives must subscribe on the topic path — the "
            "topic objectives.strategic_decision was not created"
        )
        assert topic.get_subscriber_count() >= 1
