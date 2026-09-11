"""#1647 — SetAF's defining property must be observable, not assumed.

SetAF exists for the **joint** attack: a SET of arguments attacking a target
without any member attacking it alone. Measured on three real corpora (coord,
R783): 43 attacks, **43 singletons, zero collective** — every run restated Dung.

The chain was honest about the *absence* of input (``_STRUCTURED_ARG_ABSENT_REASON``
already names "lifted to singletons") but blind on the *presence* branch: a
non-empty ``set_attacks`` list whose every attacker set is a singleton was filed
``evaluated`` — a status whose own definition promises "collective attacks" —
and the absence ledger only surfaces ``degraded`` entries, so nothing downstream
could tell a degenerate run from a genuine one.

These tests pin the property. The first four fail on the unfixed father.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.orchestration import state_writers
from argumentation_analysis.orchestration.state_writers import (
    _record_structured_arg_status,
)

_SINGLETONS = [
    {"attackers": ["a"], "target": "b"},
    {"attackers": ["b"], "target": "c"},
    {"attackers": ["c"], "target": "a"},
]
_ONE_COLLECTIVE = [
    {"attackers": ["a"], "target": "b"},
    {"attackers": ["a", "b"], "target": "c"},
]
_SUBSTANTIVE_OUTPUT = {"extensions": [["a", "b"]], "semantics": "preferred"}


class _State:
    """Minimal recorder sink — same shape the writer looks for."""

    def __init__(self) -> None:
        self.structured_arg_status: dict = {}

    def add_structured_arg_status(
        self, capability, status, degraded, reason, extension_count=0
    ) -> None:
        self.structured_arg_status[capability] = {
            "capability": capability,
            "status": status,
            "degraded": degraded,
            "reason": reason,
            "extension_count": extension_count,
        }


def _record(ctx: dict, capability: str = "setaf_reasoning") -> dict:
    st = _State()
    _record_structured_arg_status(st, capability, _SUBSTANTIVE_OUTPUT, ctx)
    return st.structured_arg_status[capability]


class TestSetafDegenerateIsLabelled:
    def test_singleton_only_run_is_not_evaluated(self):
        info = _record({"set_attacks": _SINGLETONS})
        assert info["status"] == "evaluated_degenerate", (
            "#1647: three singleton attacks restate Dung — filing them "
            f"`evaluated` (whose definition promises collective attacks) hides "
            f"the degenerate case, got {info['status']!r}"
        )
        assert info["degraded"] is True

    def test_reason_names_the_absent_property(self):
        info = _record({"set_attacks": _SINGLETONS})
        reason = info["reason"].lower()
        assert (
            "collective" in reason and "singleton" in reason
        ), f"the reason must name what is missing, got: {info['reason']!r}"

    def test_reason_distinguishes_shaped_input_from_supplied_input(self):
        shaped = _record(
            {
                "set_attacks": _SINGLETONS,
                state_writers._translation_cause_key("setaf_reasoning"): (
                    "no_genuine_relations"
                ),
            }
        )
        supplied = _record({"set_attacks": _SINGLETONS})
        assert "pairwise attack graph" in shaped["reason"]
        assert "pairwise attack graph" not in supplied["reason"]


class TestScopeGuards:
    """What must NOT change."""

    def test_one_collective_attack_keeps_the_axis_evaluated(self):
        info = _record({"set_attacks": _ONE_COLLECTIVE})
        assert info["status"] == "evaluated"
        assert info["degraded"] is False

    def test_other_capabilities_are_untouched(self):
        info = _record({"contraries": {"a": ["b"]}}, capability="aba_reasoning")
        assert info["status"] == "evaluated"
        assert info["degraded"] is False

    def test_absent_input_still_takes_the_existing_branch(self):
        info = _record({})
        assert info["status"] != "evaluated_degenerate"

    def test_counter_is_mechanical(self):
        # Imported here, not at module scope: on the unfixed father this file
        # must collect so its behavioural tests can go red on their assertions
        # rather than the whole module erroring at collection.
        from argumentation_analysis.orchestration.state_writers import (
            _setaf_collective_count,
        )

        assert _setaf_collective_count(_SINGLETONS) == 0
        assert _setaf_collective_count(_ONE_COLLECTIVE) == 1
        assert _setaf_collective_count(None) is None
        assert _setaf_collective_count([{"target": "b"}]) == 0


class TestLedgerSurfacesIt:
    def test_degenerate_axis_reaches_the_act3_absence_ledger(self):
        # The ledger only surfaces `degraded` entries — this is the link that
        # makes the label observable in the restitution rather than in the
        # state alone.
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _collect_absent_dimensions,
        )

        st = SimpleNamespace(
            structured_arg_status={
                "setaf_reasoning": _record({"set_attacks": _SINGLETONS})
            }
        )
        absent = {d.capability for d in _collect_absent_dimensions(st)}
        assert "setaf_reasoning" in absent, (
            "a degenerate SetAF run must appear in the honest-absence ledger, "
            f"got {absent!r}"
        )


class _WriteState:
    """Sink for the real writer — records the curated entry and the ledger."""

    def __init__(self) -> None:
        self.dung_frameworks: dict = {}
        self.structured_arg_status: dict = {}

    def add_dung_framework(self, name, arguments, attacks, extensions):
        self.dung_frameworks[name] = {
            "name": name,
            "arguments": arguments,
            "attacks": attacks,
            "extensions": extensions,
        }
        return name

    def add_structured_arg_status(
        self, capability, status, degraded, reason, extension_count=0
    ) -> None:
        self.structured_arg_status[capability] = {
            "capability": capability,
            "status": status,
            "degraded": degraded,
            "reason": reason,
            "extension_count": extension_count,
        }


class TestCollectiveFormSurvivesTheWrite:
    """DoD item 2 — read the attacked-the-write form back out of the state."""

    def _write(self, attacks, arguments):
        from argumentation_analysis.orchestration.state_writers import (
            _write_setaf_to_state,
        )

        st = _WriteState()
        output = {
            "semantics": "preferred",
            "arguments": arguments,
            "attacks": attacks,
            "extensions": [arguments[:2]],
        }
        _write_setaf_to_state(output, st, {"set_attacks": attacks})
        return st, st.dung_frameworks["setaf_preferred"]

    def test_collective_attack_is_readable_from_the_written_entry(self):
        attacks = [{"attackers": ["arg a", "arg b"], "target": "arg c"}]
        _, entry = self._write(attacks, ["arg a", "arg b", "arg c"])
        assert entry["formalism_specific"]["set_attacks"] == attacks, (
            "#1647 DoD: the collective form must survive the write value-equal "
            "to what the handler returned"
        )
        assert len(entry["formalism_specific"]["set_attacks"][0]["attackers"]) >= 2

    def test_the_binary_projection_is_not_widened(self):
        # Anti-pendulum (R974): the fix must not grow the Dung container to
        # admit the SetAF form — the sidecar stays the only carrier.
        attacks = [{"attackers": ["arg a", "arg b"], "target": "arg c"}]
        st, entry = self._write(attacks, ["arg a", "arg b", "arg c"])
        assert entry["attacks"] == []
        assert st.structured_arg_status["setaf_reasoning"]["status"] == "evaluated"

    def test_singleton_only_run_is_labelled_and_still_written(self):
        # Labelled, not dropped: the degenerate run keeps its data and gains
        # a status a downstream reader can act on.
        attacks = [{"attackers": ["arg a"], "target": "arg b"}]
        st, entry = self._write(attacks, ["arg a", "arg b"])
        assert (
            st.structured_arg_status["setaf_reasoning"]["status"]
            == "evaluated_degenerate"
        )
        assert entry["formalism_specific"]["set_attacks"] == attacks


class TestDegenerateRunIsNotCountedAsUsed:
    def test_capability_leaves_capabilities_used(self):
        # The pipeline splitter is driven by the `degraded` boolean, not by the
        # status label — so the new label flows through it with no reader
        # migration. Pinned here because that is the whole point of the label.
        from argumentation_analysis.orchestration.unified_pipeline import (
            _collect_degraded_capabilities,
        )

        st = SimpleNamespace(
            structured_arg_status={
                "setaf_reasoning": _record({"set_attacks": _SINGLETONS})
            }
        )
        degraded, used = _collect_degraded_capabilities(
            {}, st, ["setaf_reasoning", "aba_reasoning"]
        )
        assert "setaf_reasoning" in degraded
        assert "setaf_reasoning" not in used
        assert "aba_reasoning" in used


class TestProducerLogStopsNamingJoint:
    def test_log_reports_the_split_not_genuine_joint(self, monkeypatch, caplog):
        import asyncio
        import logging as _logging

        from argumentation_analysis.orchestration import structured_arg_translator

        # Inventory ids are arg1..argN (structured_arg_translator._build_inventory):
        # a proposal citing anything else is dropped wholesale, and then the
        # producer log never fires — which would make this test vacuous.
        async def _fake_extract(input_text, arguments, kind):
            return {"attacks": [{"attackers": ["arg1"], "target": "arg2"}]}

        monkeypatch.setattr(
            structured_arg_translator, "_llm_extract_relations", _fake_extract
        )
        with caplog.at_level(_logging.INFO):
            asyncio.run(
                structured_arg_translator.translate_to_setaf_attacks(
                    "texte", ["arg a", "arg b"]
                )
            )
        log = caplog.text
        assert "genuine joint" not in log, (
            "#1647: the log named *joint* a count that includes singletons — "
            f"the instrument must not name a property it never tested: {log!r}"
        )
        assert "singleton" in log
