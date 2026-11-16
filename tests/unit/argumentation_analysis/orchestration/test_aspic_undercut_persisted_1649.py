"""#1649 — the ASPIC+ undercut ledger must live in the state, not the log.

State on 15/11 (after cycle 11): the consumer (``_invoke_aspic``) builds
``aspic_undercut_emitted / considered / total`` and the per-emission decisions
plus the per-counter refusal reasons, and puts them on the phase payload — but
the writer ``_write_aspic_to_state`` did not copy them into the ASPIC entry, so
the cycle reading counted the undercuts from ``attacks`` and cross-checked the
log line. "A cycle reading should not need the log."

Anti-#1019 discipline: absence stays absence. The consumer sets the three
counters on every payload it returns (a 0 there IS a measured zero), while the
decisions/reasons keys ride the payload only when non-empty — so a payload
without any of the five keys (an older payload, or a run where the consumer
did not run) must write NONE of them: never a fabricated 0.

Privacy: synthetic values only (``counter_1``, ``arg_1`` — no corpus tokens).
"""

from __future__ import annotations

from typing import Any, Dict

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_aspic_to_state,
)

_UNDERCUT_KEYS = (
    "aspic_undercut_emitted",
    "aspic_undercut_considered",
    "aspic_undercut_total",
    "aspic_undercut_decisions",
    "aspic_undercut_reasons",
)


def _new_state() -> UnifiedAnalysisState:
    """A fresh state for a single writer probe."""
    return UnifiedAnalysisState("aspic-undercut-persisted-1649 synthetic probe")


def _stub_payload_with_undercuts() -> Dict[str, Any]:
    """Mirror of the payload ``_invoke_aspic`` returns (invoke_callables.py,
    the ``#1649 case 5`` block): the three counters always, the decisions and
    reasons only when non-empty. Synthetic values only.
    """
    return {
        "reasoner_type": "simple",
        "extensions": [["arg_1"], ["arg_2"]],
        "statistics": {"extensions_count": 2, "attacks_count": 1},
        "attacks": [
            {
                "attacker_rule": "wk_ca_probe",
                "attacker_premises": ["wk_ca_probe"],
                "target": "def_con_1",
                "scope": "undercut",
            }
        ],
        "aspic_undercut_emitted": 1,
        "aspic_undercut_considered": 2,
        "aspic_undercut_total": 3,
        "aspic_undercut_decisions": [
            {
                "counter_id": "counter_1",
                "counter_atom": "wk_ca_probe",
                "target_unit": "arg_1",
                "target_rule": "def_con_1",
            }
        ],
        "aspic_undercut_reasons": [
            "counter_2: attacked_component='premise' emits nothing in this "
            "step (inference only)",
            "counter_3: is_valid_attack not truthy",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# TestUndercutLedgerPersisted1649 — the writer must carry the payload's ledger
# ─────────────────────────────────────────────────────────────────────────────


class TestUndercutLedgerPersisted1649:
    """The payload's undercut ledger survives into the ASPIC state entry."""

    def test_writer_persists_undercut_counters(self) -> None:
        """emitted / considered / total land in the entry verbatim.

        Pre-fix the writer dropped all five keys on the floor: the entry had
        no undercut field at all, and a cycle reading had to recount the
        attacks and cross-check the log line.
        """
        state = _new_state()
        _write_aspic_to_state(_stub_payload_with_undercuts(), state, {})

        assert len(state.aspic_results) == 1
        entry = state.aspic_results[0]
        assert entry.get("aspic_undercut_emitted") == 1, (
            "writer dropped aspic_undercut_emitted — #1649 loss: the cycle "
            "reading cannot say how many undercuts were emitted without the "
            f"log line (entry keys: {sorted(entry.keys())})"
        )
        assert entry.get("aspic_undercut_considered") == 2
        assert entry.get("aspic_undercut_total") == 3

    def test_writer_persists_decisions_and_reasons(self) -> None:
        """The per-emission decisions and per-counter reasons land verbatim."""
        state = _new_state()
        payload = _stub_payload_with_undercuts()
        _write_aspic_to_state(payload, state, {})

        entry = state.aspic_results[0]
        assert (
            entry.get("aspic_undercut_decisions") == payload["aspic_undercut_decisions"]
        ), (
            "writer dropped aspic_undercut_decisions — the two-unit anchor "
            "(counter ↔ target rule) of each emission is lost"
        )
        decision = entry["aspic_undercut_decisions"][0]
        assert set(decision.keys()) >= {
            "counter_id",
            "counter_atom",
            "target_unit",
            "target_rule",
        }
        assert (
            entry.get("aspic_undercut_reasons") == payload["aspic_undercut_reasons"]
        ), (
            "writer dropped aspic_undercut_reasons — the named refusal per "
            "non-emitting counter is lost"
        )

    def test_keys_survive_state_snapshot(self) -> None:
        """The cycle-reading path (``get_state_snapshot(summarize=False)``)
        carries the ledger — the reading should not need the log."""
        state = _new_state()
        _write_aspic_to_state(_stub_payload_with_undercuts(), state, {})

        snapshot = state.get_state_snapshot(summarize=False)
        entries = snapshot.get("aspic_results")
        assert isinstance(entries, list) and entries, "no aspic entry in snapshot"
        entry = entries[0]
        assert entry.get("aspic_undercut_emitted") == 1
        assert entry.get("aspic_undercut_considered") == 2
        assert entry.get("aspic_undercut_total") == 3
        assert entry.get("aspic_undercut_decisions")
        assert entry.get("aspic_undercut_reasons")


# ─────────────────────────────────────────────────────────────────────────────
# TestAbsenceStaysAbsence1649 — a payload without the keys writes nothing
# ─────────────────────────────────────────────────────────────────────────────


class TestAbsenceStaysAbsence1649:
    """#1019 family: a missing field is never a measured zero."""

    def test_payload_without_keys_writes_none_of_them(self) -> None:
        """An older payload (or a run without the consumer) adds none of the
        five keys — absence stays absence, never a fabricated 0."""
        state = _new_state()
        payload = _stub_payload_with_undercuts()
        for key in _UNDERCUT_KEYS:
            payload.pop(key, None)
        _write_aspic_to_state(payload, state, {})

        assert len(state.aspic_results) == 1
        entry = state.aspic_results[0]
        present = [key for key in _UNDERCUT_KEYS if key in entry]
        assert present == [], (
            f"writer fabricated undercut fields the payload did not carry: "
            f"{present} — a missing field is never a measured zero (#1019)"
        )
        # The rest of the entry still landed (the writer did run).
        assert entry["reasoner_type"] == "simple"

    def test_measured_zero_is_persisted(self) -> None:
        """The consumer sets the three counters on EVERY payload it returns —
        a 0 there is a measured zero and must be persisted as 0, while the
        decisions/reasons keys (only present when non-empty) stay absent."""
        state = _new_state()
        payload = _stub_payload_with_undercuts()
        payload["aspic_undercut_emitted"] = 0
        payload["aspic_undercut_considered"] = 0
        payload.pop("aspic_undercut_decisions", None)
        payload.pop("aspic_undercut_reasons", None)
        _write_aspic_to_state(payload, state, {})

        entry = state.aspic_results[0]
        assert entry.get("aspic_undercut_emitted") == 0, (
            "a measured 0 (the consumer always sets the counter) must not be "
            "dropped — it is not an absence"
        )
        assert entry.get("aspic_undercut_considered") == 0
        assert entry.get("aspic_undercut_total") == 3
        assert "aspic_undercut_decisions" not in entry
        assert "aspic_undercut_reasons" not in entry

    def test_malformed_counter_is_not_persisted(self) -> None:
        """Defensive: a non-int counter (or non-list decisions/reasons) on a
        malformed payload stays out of the entry rather than crashing."""
        state = _new_state()
        payload = _stub_payload_with_undercuts()
        payload["aspic_undercut_emitted"] = "one"
        payload["aspic_undercut_decisions"] = "not-a-list"
        _write_aspic_to_state(payload, state, {})

        entry = state.aspic_results[0]
        assert "aspic_undercut_emitted" not in entry
        assert "aspic_undercut_decisions" not in entry
        assert entry.get("aspic_undercut_considered") == 2


# ─────────────────────────────────────────────────────────────────────────────
# TestAddAspicResultCompat1649 — the legacy signature stays alive
# ─────────────────────────────────────────────────────────────────────────────


class TestAddAspicResultCompat1649:
    """``add_aspic_result(reasoner, ext, stats)`` must keep working."""

    def test_3arg_call_stores_none_of_the_new_keys(self) -> None:
        """The 3-arg form keeps the legacy contract: no fabricated ledger."""
        state = _new_state()
        aid = state.add_aspic_result("grounded", ["ext1"], {"time_ms": 42})
        assert aid.startswith("aspic_")
        entry = state.aspic_results[0]
        present = [key for key in _UNDERCUT_KEYS if key in entry]
        assert present == [], f"3-arg call fabricated: {present}"

    def test_kwarg_call_stores_the_ledger(self) -> None:
        """The explicit kwargs land in the entry (the writer's pass-through
        target)."""
        state = _new_state()
        state.add_aspic_result(
            "grounded",
            ["ext1"],
            {"time_ms": 42},
            aspic_undercut_emitted=2,
            aspic_undercut_considered=4,
            aspic_undercut_total=5,
            aspic_undercut_decisions=[
                {
                    "counter_id": "counter_1",
                    "counter_atom": "wk_ca_probe",
                    "target_unit": "arg_1",
                    "target_rule": "def_con_1",
                }
            ],
            aspic_undercut_reasons=["counter_2: target 'arg_9' unresolved"],
        )
        entry = state.aspic_results[0]
        assert entry["aspic_undercut_emitted"] == 2
        assert entry["aspic_undercut_considered"] == 4
        assert entry["aspic_undercut_total"] == 5
        assert entry["aspic_undercut_decisions"][0]["counter_id"] == "counter_1"
        assert entry["aspic_undercut_reasons"] == [
            "counter_2: target 'arg_9' unresolved"
        ]
