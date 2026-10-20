# -*- coding: utf-8 -*-
"""#1649 case 5 — the WK-undercut lever, wired consumer-side in _invoke_aspic.

Design decision (measured, this lane — see the issue comment): the scope
source is the COUNTER lane's ``attacked_component`` field, not the ASPIC
translator. The translator is structurally blind to adversarial material —
its inventory only ever sees the text's own arguments — and the repaired
doc_A run proposed 0 undercuts (raw=3 kept=3, 0 contradictions/undercuts).
The counter census (38 counters) carries ``validation`` +
``target_arg_id`` in the frame's ``arg_N`` unit-id domain already; the
``attacked_component`` field does not exist yet — the wiring landed first,
and the absent case says it is absent.

Emission contract (the R1223-measured WK shape): for a counter with
``attacked_component == "inference"``, a valid attack, a target resolved
among the frame units and a defeasible rule citing that unit, ONE extra
defeasible rule ``{"name": "wk_<counter atom>", "head": <target rule NAME>,
"body": [<counter atom>], "head_negated": True}`` — the counter atom is
minted as an ordinary premise by the leaf-atom derivation, so the attacker
is derivable (#1678 attacker side). Every other path emits NOTHING and
records its reason on the payload; ``premise``/``conclusion``, an invalid
attack and an unresolved target never reach the handler as an edge.

Two tiers, per the #1678 paired-run precedent: live-attack rendering is
pinned at the handler layer (deterministic there); the wiring tier runs
under a recording fake handler (no JVM) and asserts exactly what
``_invoke_aspic`` handed the handler plus the payload.

Born red on ``main`` (source edits stashed, this file alone): the WK rule
is absent from the handed rules, the ``aspic_undercut_*`` keys are absent,
and the handler-tier run renders zero attack.

Privacy HARD: synthetic French sentences only — no corpus text.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from argumentation_analysis.orchestration import invoke_callables as ic

_UNIT_1 = (
    "Première thèse synthétique suffisamment longue pour que sa troncature à "
    "cent vingt caractères devienne un texte distinct mais préfixe-égal, ce "
    "qui est exactement la forme mesurée sur l'état réel."
)
_UNIT_2 = (
    "Seconde thèse synthétique, distincte de la première, elle aussi assez "
    "longue pour que le producteur historique la tronque en un libellé qui ne "
    "rejoint plus jamais l'unité identifiée correspondante."
)

_COUNTER_CONTENT = (
    "le passage de la prémisse à la conclusion ne tient pas : la règle "
    "d'inférence invoquée n'autorise pas ce saut"
)


class _RecordingState(SimpleNamespace):
    """State stub: unit population + trace/coverage recorders (the surfaces
    ``_invoke_aspic`` touches when the state object is present)."""

    def __init__(self, **fields: Any) -> None:
        super().__init__(**fields)
        self.trace_entries: List[Dict[str, Any]] = []
        self.coverage_rows: List[Any] = []

    def add_trace_entry(self, **kwargs: Any) -> None:
        self.trace_entries.append(kwargs)

    def record_analysis_coverage(self, *row: Any, **kwargs: Any) -> None:
        self.coverage_rows.append((row, kwargs))


def _counter(
    component: Any = "inference",
    valid: Any = True,
    target: Any = "arg_2",
    content: str = _COUNTER_CONTENT,
    cid: str = "ca_1",
) -> Dict[str, Any]:
    """The producer contract shape this wiring reads (census-measured keys)."""
    return {
        "id": cid,
        "counter_content": content,
        "attacked_component": component,
        "validation": {
            "is_valid_attack": valid,
            "original_survives": not valid,
            "counter_succeeds": bool(valid),
        },
        "target_arg_id": target,
    }


def _context(state: Any, counters: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "_state_object": state,
        "phase_extract_output": {
            "arguments": [{"text": _UNIT_1[:120]}, {"text": _UNIT_2[:120]}]
        },
        "phase_hierarchical_fallacy_output": {"fallacies": []},
        "phase_counter_output": {"llm_counter_arguments": counters},
    }


def _empty_translator(monkeypatch: pytest.MonkeyPatch) -> None:
    """No genuine translator rules: the auto-shape branch derives def_arg_i
    over the frame units (hermetic — no LLM request, #1591)."""
    import argumentation_analysis.orchestration.structured_arg_translator as sat

    async def _no_rules(*args: Any, **kwargs: Any) -> Any:
        return SimpleNamespace(relations=[], cause="no_genuine_relations", error=None)

    monkeypatch.setattr(sat, "translate_to_aspic_rules", _no_rules)


def _recording_fake_handler(
    monkeypatch: pytest.MonkeyPatch, seen: List[Dict[str, Any]]
) -> None:
    """Replace ASPICHandler on its home module: records the theory it was
    handed, answers a minimal valid payload (3014 pattern)."""
    import argumentation_analysis.agents.core.logic.aspic_handler as ah
    import argumentation_analysis.agents.core.logic.tweety_initializer as twi

    def _analyze(self: Any, *call_args: Any, **call_kwargs: Any) -> Dict[str, Any]:
        strict, defeasible, axioms = call_args
        seen.append(
            {
                "strict": list(strict or []),
                "defeasible": list(defeasible or []),
                "axioms": list(axioms or []),
            }
        )
        return {"extensions": [["arg_2"]], "statistics": {}, "attacks": []}

    fake_cls = type(
        "ASPICHandler",
        (),
        {"__init__": lambda self: None, "analyze_aspic_framework": _analyze},
    )
    monkeypatch.setattr(ah, "ASPICHandler", fake_cls)
    monkeypatch.setattr(twi, "ready_initializer", lambda: object())


def _expected_wk_rule(
    counter: Dict[str, Any], target_rule: str = "def_arg_2"
) -> Dict[str, Any]:
    atom = ic._pl_atom(str(counter["counter_content"]), prefix="wk_ca")
    return {
        "name": f"wk_{atom}",
        "head": target_rule,
        "body": [atom],
        "head_negated": True,
    }


class TestWiringThroughInvokeAspic:
    """The wiring tier (recording fake handler — no JVM): what _invoke_aspic
    handed the handler, and what the payload says about it."""

    async def test_inference_counter_yields_one_wk_rule(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        _recording_fake_handler(monkeypatch, seen)

        counter = _counter()
        out = await ic._invoke_aspic(_UNIT_1, _context(state, [counter]))

        # The auto-shape derived the two unit rules; the WK rule is the exact
        # R1223 shape, targeting the rule that cites the target unit.
        assert {
            "head": "plausible_conclusion_1",
            "body": ["arg_1"],
            "name": "def_arg_1",
        } in seen[0]["defeasible"]
        expected_wk = _expected_wk_rule(counter, "def_arg_2")
        assert {
            "head": "plausible_conclusion_2",
            "body": ["arg_2"],
            "name": "def_arg_2",
        } in seen[0]["defeasible"]
        assert expected_wk in seen[0]["defeasible"]
        assert len(seen[0]["defeasible"]) == 3, seen[0]["defeasible"]
        # Attacker derivability (#1678): the counter atom is an ordinary
        # premise — the leaf-atom derivation minted it from the WK body.
        assert expected_wk["body"][0] in seen[0]["axioms"]
        # The payload speaks: emission count, two-unit anchor, no refusal.
        assert out["aspic_undercut_emitted"] == 1
        assert out["aspic_undercut_considered"] == 1
        assert out["aspic_undercut_total"] == 1
        assert out["aspic_undercut_decisions"] == [
            {
                "counter_id": "ca_1",
                "counter_atom": expected_wk["body"][0],
                "target_unit": "arg_2",
                "target_rule": "def_arg_2",
            }
        ]
        assert "aspic_undercut_reasons" not in out
        # The trace names the counter phase among its inputs.
        aspic_trace = [t for t in state.trace_entries if t.get("phase") == "aspic"]
        assert aspic_trace, state.trace_entries
        assert "counter_arguments" in aspic_trace[-1]["reacts_to"]
        assert "undercut WK" in aspic_trace[-1]["summary"]

    @pytest.mark.parametrize("component", ["premise", "conclusion"])
    async def test_premise_and_conclusion_emit_nothing_with_reason(
        self, monkeypatch: pytest.MonkeyPatch, component: str
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        _recording_fake_handler(monkeypatch, seen)

        out = await ic._invoke_aspic(
            _UNIT_1, _context(state, [_counter(component=component)])
        )

        assert out["aspic_undercut_emitted"] == 0
        wk_rules = [
            r for r in seen[0]["defeasible"] if str(r.get("name", "")).startswith("wk_")
        ]
        assert wk_rules == [], seen[0]["defeasible"]
        assert len(out["aspic_undercut_reasons"]) == 1
        assert component in out["aspic_undercut_reasons"][0]
        assert "ca_1" in out["aspic_undercut_reasons"][0]

    async def test_invalid_attack_emits_nothing_with_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        _recording_fake_handler(monkeypatch, seen)

        out = await ic._invoke_aspic(_UNIT_1, _context(state, [_counter(valid=False)]))

        assert out["aspic_undercut_emitted"] == 0
        assert any("is_valid_attack" in r for r in out["aspic_undercut_reasons"])
        assert not any(
            str(r.get("name", "")).startswith("wk_") for r in seen[0]["defeasible"]
        )

    async def test_unresolved_target_emits_nothing_with_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        _recording_fake_handler(monkeypatch, seen)

        out = await ic._invoke_aspic(
            _UNIT_1, _context(state, [_counter(target="arg_99")])
        )

        assert out["aspic_undercut_emitted"] == 0
        assert any(
            "unresolved" in r and "arg_99" in r for r in out["aspic_undercut_reasons"]
        )
        assert not any(
            str(r.get("name", "")).startswith("wk_") for r in seen[0]["defeasible"]
        )

    async def test_absent_field_says_it_is_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The producer field does not exist today (census: 0/38 counters).
        The wiring landed first — the absent case must SAY the absence, not
        stay silent (GO: 'the absent case says it is absent')."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        _recording_fake_handler(monkeypatch, seen)

        bare = {
            "id": "ca_1",
            "counter_content": _COUNTER_CONTENT,
            "validation": {"is_valid_attack": True},
            "target_arg_id": "arg_2",
        }
        out = await ic._invoke_aspic(_UNIT_1, _context(state, [bare]))

        assert out["aspic_undercut_emitted"] == 0
        assert out["aspic_undercut_total"] == 1
        assert len(out["aspic_undercut_reasons"]) == 1
        assert "attacked_component absent" in out["aspic_undercut_reasons"][0]
        assert not any(
            str(r.get("name", "")).startswith("wk_") for r in seen[0]["defeasible"]
        )

    async def test_mixed_field_presence_names_the_silent_counters(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Once the producer sends the field on SOME counters, a counter
        missing it is a named refusal, not a silent skip."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        _recording_fake_handler(monkeypatch, seen)

        bare = {"id": "ca_bare", "counter_content": "x", "target_arg_id": "arg_2"}
        out = await ic._invoke_aspic(
            _UNIT_1, _context(state, [bare, _counter(cid="ca_ok")])
        )

        assert out["aspic_undercut_emitted"] == 1
        assert out["aspic_undercut_reasons"] == [
            "ca_bare: no attacked_component (producer mixed)"
        ]

    async def test_target_without_rule_emits_nothing_with_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A frame unit no defeasible rule cites cannot be undercut — the
        caller-supplied rule cites arg_1 only, the counter targets arg_2."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        seen: List[Dict[str, Any]] = []
        _recording_fake_handler(monkeypatch, seen)
        context = _context(state, [_counter()])
        context["defeasible_rules"] = [
            {"head": "c", "body": ["arg_1"], "name": "def_rule_1"}
        ]
        context["strict_rules"] = [{"head": "strict_seed", "body": []}]

        out = await ic._invoke_aspic(_UNIT_1, context)

        assert out["aspic_undercut_emitted"] == 0
        assert any("no defeasible rule" in r for r in out["aspic_undercut_reasons"])
        assert seen[0]["defeasible"] == [
            {"head": "c", "body": ["arg_1"], "name": "def_rule_1"}
        ]

    async def test_consideration_is_capped_and_disclosed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Family style (#2850): at most 4 counters considered, considered vs
        total disclosed on the payload — a 5th valid counter is named by the
        counts, never silently dropped."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        _recording_fake_handler(monkeypatch, seen)

        counters = [
            _counter(cid=f"ca_{i}", content=f"{_COUNTER_CONTENT} variante {i}")
            for i in range(5)
        ]
        out = await ic._invoke_aspic(_UNIT_1, _context(state, counters))

        assert out["aspic_undercut_total"] == 5
        assert out["aspic_undercut_considered"] == 4
        assert out["aspic_undercut_emitted"] == 4
        assert len(out["aspic_undercut_decisions"]) == 4
        wk_rules = [
            r for r in seen[0]["defeasible"] if str(r.get("name", "")).startswith("wk_")
        ]
        assert len(wk_rules) == 4
        # Distinct counter contents mint distinct attacker atoms (no merge).
        assert len({r["body"][0] for r in wk_rules}) == 4

    async def test_no_counters_leaves_the_axis_untouched(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A run without the counter phase (stateless context) carries the
        zero-total payload and no WK rule — nothing fabricated."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        _recording_fake_handler(monkeypatch, seen)

        out = await ic._invoke_aspic(_UNIT_1, _context(state, []))

        assert out["aspic_undercut_emitted"] == 0
        assert out["aspic_undercut_total"] == 0
        assert "aspic_undercut_decisions" not in out
        assert "aspic_undercut_reasons" not in out
        assert not any(
            str(r.get("name", "")).startswith("wk_") for r in seen[0]["defeasible"]
        )


class TestHandlerRendersTheUndercut:
    """The handler tier (real JVM handler, recording-delegating patch): the
    theory the wiring built renders EXACTLY one undercut attack — the
    #1678 precedent pins live-attack scopes at the handler layer, where they
    are deterministic. R1223 measured this shape offline: 1 attack,
    scope=undercut, attacker_rule=wk_*."""

    pytestmark = [pytest.mark.jpype, pytest.mark.tweety]

    @staticmethod
    def _delegating_recorder(
        monkeypatch: pytest.MonkeyPatch, seen: List[Dict[str, Any]]
    ) -> None:
        import argumentation_analysis.agents.core.logic.aspic_handler as ah

        real = ah.ASPICHandler.analyze_aspic_framework

        def _analyze(self: Any, *call_args: Any, **call_kwargs: Any) -> Dict[str, Any]:
            strict, defeasible, axioms = call_args
            seen.append(
                {
                    "strict": list(strict or []),
                    "defeasible": list(defeasible or []),
                    "axioms": list(axioms or []),
                }
            )
            return real(self, *call_args, **call_kwargs)

        monkeypatch.setattr(ah.ASPICHandler, "analyze_aspic_framework", _analyze)

    async def test_exactly_one_undercut_attack_anchored_to_two_units(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        self._delegating_recorder(monkeypatch, seen)

        counter = _counter()
        out = await ic._invoke_aspic(_UNIT_1, _context(state, [counter]))

        decision = out["aspic_undercut_decisions"][0]
        attacks = out["attacks"]
        undercuts = [a for a in attacks if a.get("scope") == "undercut"]
        assert len(undercuts) == 1, attacks
        attack = undercuts[0]
        # The WK contract: named after the attacking unit (the counter's
        # minted atom), undercutting the target rule by NAME.
        assert attack.get("attacker_rule") == f"wk_{decision['counter_atom']}"
        # Two-unit anchor: the attacker atom is an ordinary premise (the
        # counter side derivable) and the target rule cites the target unit.
        assert decision["counter_atom"] in seen[0]["axioms"]
        target_rules = [
            r for r in seen[0]["defeasible"] if r.get("name") == decision["target_rule"]
        ]
        assert target_rules and decision["target_unit"] in target_rules[0]["body"]

    async def test_without_the_counter_the_axis_stays_inert(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same inventory, no counter: the inert axis (0 attack) — the same
        input the counter flips, deterministic through _invoke_aspic (#1678
        paired-run precedent)."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        _empty_translator(monkeypatch)
        seen: List[Dict[str, Any]] = []
        self._delegating_recorder(monkeypatch, seen)

        out = await ic._invoke_aspic(_UNIT_1, _context(state, []))

        assert out["attacks"] == [], out["attacks"]
        assert out["aspic_undercut_emitted"] == 0
