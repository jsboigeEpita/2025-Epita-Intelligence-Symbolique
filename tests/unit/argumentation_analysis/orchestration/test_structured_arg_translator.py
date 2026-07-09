"""TR-1 #1419 / FP-17 #1236 — text→structured translator (bipolar/ABA) unit tests.

Validates the anti-théâtre contract (#1019):
- Relations returned by the LLM are validated against the REAL argument
  inventory; fabricated pairs referencing unknown ids are DROPPED.
- An empty / failed LLM extraction yields an empty result, so the formalism
  stays ``absent_no_translator`` (honest absence) — never a fabricated evaluation.
- The handler wiring persists genuine relations into ``context``, which lets
  ``_record_structured_arg_status`` label the axis ``evaluated``.

No JVM, no real LLM. Synthetic atoms only (privacy HARD — no corpus tokens).
"""

from __future__ import annotations

import sys
import types
from typing import Any, Dict, List, Tuple

import pytest

from argumentation_analysis.orchestration.structured_arg_translator import (
    _build_inventory,
    _validate_aspic_rules,
    _validate_contraries,
    _validate_setaf_attacks,
    _validate_supports,
    _validate_weighted_attacks,
    translate_to_aba_contraries,
    translate_to_aspic_rules,
    translate_to_bipolar_supports,
    translate_to_setaf_attacks,
    translate_to_weighted_attacks,
)


def _atom(text: str, prefix: str = "arg") -> str:
    """Trivial deterministic atom_fn for validation tests (no _pl_atom import)."""
    return f"{prefix}:{text}"


# -- _build_inventory --------------------------------------------------------


class TestBuildInventory:
    def test_enumerates_cleanly(self):
        arg_by_id, listed = _build_inventory(["alpha", "beta", "gamma"])
        assert arg_by_id == {"arg1": "alpha", "arg2": "beta", "arg3": "gamma"}
        assert [e["id"] for e in listed] == ["arg1", "arg2", "arg3"]

    def test_skips_empty_and_non_strings(self):
        arg_by_id, _ = _build_inventory(["alpha", "", "   ", None, "beta"])  # type: ignore[arg-type]
        assert arg_by_id == {"arg1": "alpha", "arg2": "beta"}

    def test_empty_input_returns_empty(self):
        assert _build_inventory([])[0] == {}

    def test_caps_at_twenty(self):
        args = [f"a{i}" for i in range(50)]
        arg_by_id, _ = _build_inventory(args)
        assert len(arg_by_id) == 20
        assert arg_by_id["arg1"] == "a0"
        assert arg_by_id["arg20"] == "a19"


# -- validation: the anti-théâtre guard --------------------------------------


class TestValidateSupports:
    def test_keeps_valid_pairs_mapped_to_canonical_text(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta", "arg3": "Gamma"}
        data = {"supports": [
            {"source": "arg1", "target": "arg2", "rationale": "r"},
            {"source": "arg3", "target": "arg1", "rationale": "r"},
        ]}
        out = _validate_supports(data, arg_by_id)
        assert out == [["Alpha", "Beta"], ["Gamma", "Alpha"]]

    def test_drops_pairs_referencing_unknown_ids(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"supports": [
            {"source": "arg1", "target": "arg9"},   # unknown target → dropped
            {"source": "argX", "target": "arg2"},   # unknown source → dropped
            {"source": "arg1", "target": "arg2"},   # valid → kept
        ]}
        out = _validate_supports(data, arg_by_id)
        assert out == [["Alpha", "Beta"]]

    def test_drops_self_support(self):
        arg_by_id = {"arg1": "Alpha"}
        out = _validate_supports(
            {"supports": [{"source": "arg1", "target": "arg1"}]}, arg_by_id
        )
        assert out == []

    def test_dedups_identical_pairs(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"supports": [
            {"source": "arg1", "target": "arg2"},
            {"source": "arg1", "target": "arg2"},
        ]}
        out = _validate_supports(data, arg_by_id)
        assert out == [["Alpha", "Beta"]]

    def test_empty_or_malformed_returns_empty(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        assert _validate_supports({}, arg_by_id) == []
        assert _validate_supports({"supports": []}, arg_by_id) == []
        assert _validate_supports({"supports": "not-a-list"}, arg_by_id) == []
        assert _validate_supports(
            {"supports": [{"source": 1}]}, arg_by_id  # type: ignore[list-item]
        ) == []


class TestValidateContraries:
    def test_keeps_valid_pairs_mapped_to_canonical_text(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"contraries": [
            {"assumption": "arg1", "contrary": "not Alpha", "rationale": "r"},
        ]}
        out = _validate_contraries(data, arg_by_id)
        assert out == {"Alpha": "not Alpha"}

    def test_drops_unknown_assumption_ids(self):
        arg_by_id = {"arg1": "Alpha"}
        data = {"contraries": [
            {"assumption": "arg9", "contrary": "x"},   # unknown → dropped
            {"assumption": "arg1", "contrary": "y"},   # valid → kept
        ]}
        out = _validate_contraries(data, arg_by_id)
        assert out == {"Alpha": "y"}

    def test_drops_empty_contrary(self):
        arg_by_id = {"arg1": "Alpha"}
        out = _validate_contraries(
            {"contraries": [{"assumption": "arg1", "contrary": "   "}]}, arg_by_id
        )
        assert out == {}

    def test_last_write_wins_on_duplicate_assumption(self):
        arg_by_id = {"arg1": "Alpha"}
        data = {"contraries": [
            {"assumption": "arg1", "contrary": "first"},
            {"assumption": "arg1", "contrary": "second"},
        ]}
        assert _validate_contraries(data, arg_by_id) == {"Alpha": "second"}


# -- translator: LLM mocked --------------------------------------------------


def _patch_llm(monkeypatch, payload: Dict[str, Any]) -> None:
    """Redirect the internal LLM call to return ``payload`` (no network)."""

    async def _fake(input_text: str, arguments: List[str], relation_kind: str):
        return payload

    monkeypatch.setattr(
        "argumentation_analysis.orchestration.structured_arg_translator."
        "_llm_extract_relations",
        _fake,
    )


class TestTranslatorEmptyStaysHonest:
    """Empty / failed LLM extraction → empty result → formalism stays
    absent_no_translator (anti-théâtre #1019)."""

    async def test_bipolar_empty_llm_output_returns_empty(self, monkeypatch):
        _patch_llm(monkeypatch, {"supports": []})
        out = await translate_to_bipolar_supports("some text", ["a", "b"])
        assert out == []

    async def test_bipolar_no_inventory_returns_empty(self, monkeypatch):
        _patch_llm(monkeypatch, {"supports": [{"source": "arg1", "target": "arg2"}]})
        out = await translate_to_bipolar_supports("text", [])
        assert out == []

    async def test_aba_empty_llm_output_returns_empty(self, monkeypatch):
        _patch_llm(monkeypatch, {"contraries": []})
        out = await translate_to_aba_contraries("some text", ["a", "b"])
        assert out == {}

    async def test_bipolar_only_fabricated_relations_dropped(self, monkeypatch):
        # Every pair references ids absent from the inventory → all dropped.
        _patch_llm(monkeypatch, {"supports": [
            {"source": "arg9", "target": "arg8"},
            {"source": "phantom", "target": "ghost"},
        ]})
        out = await translate_to_bipolar_supports("text", ["a", "b"])
        assert out == []

    async def test_aba_only_fabricated_assumptions_dropped(self, monkeypatch):
        _patch_llm(monkeypatch, {"contraries": [
            {"assumption": "arg9", "contrary": "x"},
        ]})
        out = await translate_to_aba_contraries("text", ["a", "b"])
        assert out == {}


class TestTranslatorReturnsValidatedRelations:
    async def test_bipolar_returns_validated_supports(self, monkeypatch):
        _patch_llm(monkeypatch, {"supports": [
            {"source": "arg1", "target": "arg2", "rationale": "r"},
            {"source": "arg2", "target": "arg3", "rationale": "r"},
            {"source": "arg1", "target": "arg9"},  # dropped (unknown)
        ]})
        out = await translate_to_bipolar_supports(
            "text", ["Alpha", "Beta", "Gamma"]
        )
        assert out == [["Alpha", "Beta"], ["Beta", "Gamma"]]

    async def test_aba_returns_validated_contraries(self, monkeypatch):
        _patch_llm(monkeypatch, {"contraries": [
            {"assumption": "arg1", "contrary": "not Alpha"},
            {"assumption": "argX", "contrary": "dropped"},  # dropped
        ]})
        out = await translate_to_aba_contraries("text", ["Alpha", "Beta"])
        assert out == {"Alpha": "not Alpha"}


# -- handler wiring: context persists (no JVM) -------------------------------


def _inject_fake_logic_modules(monkeypatch, bipolar_payload, aba_payload):
    """Inject fake BipolarHandler / ABAHandler modules so the handlers run
    without a JVM, returning canned reasoner output."""
    fake_bipolar = types.ModuleType("argumentation_analysis.agents.core.logic.bipolar_handler")

    class _FakeBipolarHandler:
        def analyze_bipolar_framework(self, args, attacks, supports, fw_type):
            return bipolar_payload

    fake_bipolar.BipolarHandler = _FakeBipolarHandler  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.bipolar_handler",
        fake_bipolar,
    )

    fake_aba = types.ModuleType("argumentation_analysis.agents.core.logic.aba_handler")

    class _FakeABAHandler:
        def analyze_aba_framework(self, assumptions, rules, contraries, semantics):
            return aba_payload

    fake_aba.ABAHandler = _FakeABAHandler  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules, "argumentation_analysis.agents.core.logic.aba_handler", fake_aba
    )


class TestHandlerWiringPersistsToContext:
    """The lazy translator call inside _invoke_bipolar/_invoke_aba must persist
    genuine relations into ``context`` so _record_structured_arg_status sees them
    and labels the axis ``evaluated``."""

    async def test_bipolar_translates_and_persists_supports(self, monkeypatch):
        _inject_fake_logic_modules(
            monkeypatch,
            bipolar_payload={"framework_type": "necessity", "supports": []},
            aba_payload={},
        )

        async def _fake_supports(text, args):
            return [["Alpha", "Beta"]]

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_bipolar_supports",
            _fake_supports,
        )
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_bipolar,
        )

        ctx: Dict[str, Any] = {"arguments": ["Alpha", "Beta"]}
        await _invoke_bipolar("source text", ctx)
        assert ctx.get("supports") == [["Alpha", "Beta"]]

    async def test_bipolar_does_not_override_caller_supplied_supports(self, monkeypatch):
        # If the caller already supplied genuine supports, the translator must
        # NOT run / NOT override them.
        called = {"n": 0}

        async def _fake_supports(text, args):
            called["n"] += 1
            return [["should", "not", "be", "used"]]

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_bipolar_supports",
            _fake_supports,
        )
        _inject_fake_logic_modules(
            monkeypatch,
            bipolar_payload={"framework_type": "necessity", "supports": []},
            aba_payload={},
        )
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_bipolar,
        )

        genuine = [["Alpha", "Gamma"]]
        ctx: Dict[str, Any] = {"arguments": ["Alpha", "Beta"], "supports": genuine}
        await _invoke_bipolar("text", ctx)
        assert ctx["supports"] is genuine  # unchanged
        assert called["n"] == 0  # translator never invoked

    async def test_aba_translates_and_persists_contraries(self, monkeypatch):
        _inject_fake_logic_modules(
            monkeypatch, bipolar_payload={}, aba_payload={"extensions": []}
        )

        async def _fake_contraries(text, args):
            return {"Alpha": "not Alpha"}

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_aba_contraries",
            _fake_contraries,
        )
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_aba,
        )

        ctx: Dict[str, Any] = {"arguments": ["Alpha", "Beta"]}
        await _invoke_aba("source text", ctx)
        assert ctx.get("contraries") == {"Alpha": "not Alpha"}

    async def test_bipolar_honest_absent_when_translator_returns_empty(self, monkeypatch):
        # Translator yields nothing → context["supports"] is NOT set → the gate
        # keeps absent_no_translator.
        _inject_fake_logic_modules(
            monkeypatch,
            bipolar_payload={"framework_type": "necessity", "supports": []},
            aba_payload={},
        )

        async def _fake_supports(text, args):
            return []

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_bipolar_supports",
            _fake_supports,
        )
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_bipolar,
        )

        ctx: Dict[str, Any] = {"arguments": ["Alpha", "Beta"]}
        await _invoke_bipolar("text", ctx)
        assert "supports" not in ctx


# -- TR-2 #1425: ASPIC+ defeasible-rule translator ---------------------------


class TestValidateAspicRules:
    def test_keeps_valid_rule_mapped_to_atoms(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta", "arg3": "Gamma"}
        data = {"rules": [
            {"premises": ["arg1", "arg2"], "conclusion": "arg3", "rationale": "r"},
        ]}
        out = _validate_aspic_rules(data, arg_by_id, _atom)
        assert out == [
            {
                "head": "arg:Gamma",
                "body": ["arg:Alpha", "arg:Beta"],
                "name": "def_rule_1",
            }
        ]

    def test_drops_rule_with_unknown_premise(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"rules": [
            {"premises": ["arg1", "arg9"], "conclusion": "arg2"},  # arg9 unknown
        ]}
        assert _validate_aspic_rules(data, arg_by_id, _atom) == []

    def test_drops_rule_with_unknown_conclusion(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"rules": [
            {"premises": ["arg1"], "conclusion": "arg9"},  # unknown conclusion
        ]}
        assert _validate_aspic_rules(data, arg_by_id, _atom) == []

    def test_drops_rule_with_no_premises(self):
        arg_by_id = {"arg1": "Alpha"}
        data = {"rules": [{"premises": [], "conclusion": "arg1"}]}
        assert _validate_aspic_rules(data, arg_by_id, _atom) == []

    def test_removes_conclusion_from_premises_keeps_rest(self):
        arg_by_id = {"arg1": "Alpha", "arg3": "Gamma"}
        data = {"rules": [
            {"premises": ["arg1", "arg3"], "conclusion": "arg3"},  # arg3 dropped
        ]}
        out = _validate_aspic_rules(data, arg_by_id, _atom)
        assert out == [
            {"head": "arg:Gamma", "body": ["arg:Alpha"], "name": "def_rule_1"}
        ]

    def test_drops_self_only_rule(self):
        arg_by_id = {"arg3": "Gamma"}
        data = {"rules": [{"premises": ["arg3"], "conclusion": "arg3"}]}
        assert _validate_aspic_rules(data, arg_by_id, _atom) == []

    def test_dedups_identical_rules(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"rules": [
            {"premises": ["arg1"], "conclusion": "arg2"},
            {"premises": ["arg1"], "conclusion": "arg2"},
        ]}
        out = _validate_aspic_rules(data, arg_by_id, _atom)
        assert out == [
            {"head": "arg:Beta", "body": ["arg:Alpha"], "name": "def_rule_1"}
        ]

    def test_dedups_repeated_body_atoms(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"rules": [
            {"premises": ["arg1", "arg1"], "conclusion": "arg2"},
        ]}
        out = _validate_aspic_rules(data, arg_by_id, _atom)
        assert out[0]["body"] == ["arg:Alpha"]

    def test_premises_as_string_normalized(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"rules": [{"premises": "arg1", "conclusion": "arg2"}]}
        out = _validate_aspic_rules(data, arg_by_id, _atom)
        assert out == [
            {"head": "arg:Beta", "body": ["arg:Alpha"], "name": "def_rule_1"}
        ]

    def test_empty_or_malformed_returns_empty(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        assert _validate_aspic_rules({}, arg_by_id, _atom) == []
        assert _validate_aspic_rules({"rules": []}, arg_by_id, _atom) == []
        assert _validate_aspic_rules({"rules": "nope"}, arg_by_id, _atom) == []
        assert _validate_aspic_rules(
            {"rules": [{"premises": 1, "conclusion": "arg1"}]},  # type: ignore[dict-item]
            arg_by_id,
            _atom,
        ) == []


class TestAspicTranslator:
    async def test_empty_llm_output_returns_empty(self, monkeypatch):
        _patch_llm(monkeypatch, {"rules": []})
        out = await translate_to_aspic_rules("some text", ["a", "b"])
        assert out == []

    async def test_no_inventory_returns_empty(self, monkeypatch):
        _patch_llm(monkeypatch, {"rules": [
            {"premises": ["arg1"], "conclusion": "arg2"},
        ]})
        out = await translate_to_aspic_rules("text", [])
        assert out == []

    async def test_only_fabricated_rules_dropped(self, monkeypatch):
        _patch_llm(monkeypatch, {"rules": [
            {"premises": ["arg8"], "conclusion": "arg9"},   # unknown ids
            {"premises": ["phantom"], "conclusion": "ghost"},
        ]})
        out = await translate_to_aspic_rules("text", ["a", "b"])
        assert out == []

    async def test_returns_validated_rules_with_real_atoms(self, monkeypatch):
        # Uses the real _pl_atom; assert head/body are the deterministic atoms
        # for the cited canonical argument texts.
        from argumentation_analysis.orchestration.invoke_callables import _pl_atom

        _patch_llm(monkeypatch, {"rules": [
            {"premises": ["arg1", "arg2"], "conclusion": "arg3"},
            {"premises": ["arg1"], "conclusion": "arg9"},  # dropped (unknown)
        ]})
        out = await translate_to_aspic_rules("text", ["Alpha", "Beta", "Gamma"])
        assert len(out) == 1
        assert out[0]["head"] == _pl_atom("Gamma", prefix="arg")
        assert out[0]["body"] == [
            _pl_atom("Alpha", prefix="arg"),
            _pl_atom("Beta", prefix="arg"),
        ]
        assert out[0]["name"] == "def_rule_1"


def _inject_fake_aspic_module(monkeypatch, payload):
    """Inject a fake ASPICHandler so _invoke_aspic runs without a JVM."""
    fake = types.ModuleType("argumentation_analysis.agents.core.logic.aspic_handler")

    class _FakeASPICHandler:
        def analyze_aspic_framework(self, strict, defeasible, axioms=None):
            return payload

    fake.ASPICHandler = _FakeASPICHandler  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.aspic_handler",
        fake,
    )


class TestAspicHandlerWiring:
    """The lazy translator call inside _invoke_aspic must persist genuine
    defeasible rules into ``context`` so _record_structured_arg_status labels the
    axis ``evaluated`` — and must stay absent when nothing genuine is derived."""

    async def test_translates_and_persists_defeasible_rules(self, monkeypatch):
        _inject_fake_aspic_module(monkeypatch, {"extensions": []})
        genuine = [{"head": "arg:h", "body": ["arg:b"], "name": "def_rule_1"}]

        async def _fake_rules(text, args):
            return genuine

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_aspic_rules",
            _fake_rules,
        )
        from argumentation_analysis.orchestration.invoke_callables import _invoke_aspic

        ctx: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["Alpha", "Beta"]}
        }
        await _invoke_aspic("source text", ctx)
        assert ctx.get("defeasible_rules") == genuine

    async def test_does_not_override_caller_supplied_rules(self, monkeypatch):
        called = {"n": 0}

        async def _fake_rules(text, args):
            called["n"] += 1
            return [{"head": "arg:x", "body": ["arg:y"], "name": "should_not_be_used"}]

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_aspic_rules",
            _fake_rules,
        )
        _inject_fake_aspic_module(monkeypatch, {"extensions": []})
        from argumentation_analysis.orchestration.invoke_callables import _invoke_aspic

        genuine = [{"head": "arg:real", "body": ["arg:prem"], "name": "def_rule_1"}]
        ctx: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["Alpha", "Beta"]},
            "defeasible_rules": genuine,
        }
        await _invoke_aspic("text", ctx)
        assert ctx["defeasible_rules"] is genuine  # unchanged
        assert called["n"] == 0  # translator never invoked

    async def test_honest_absent_when_translator_returns_empty(self, monkeypatch):
        _inject_fake_aspic_module(monkeypatch, {"extensions": []})

        async def _fake_rules(text, args):
            return []

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_aspic_rules",
            _fake_rules,
        )
        from argumentation_analysis.orchestration.invoke_callables import _invoke_aspic

        ctx: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["Alpha", "Beta"]}
        }
        await _invoke_aspic("text", ctx)
        # Nothing genuine → context key stays unset → gate keeps absent_no_translator.
        assert "defeasible_rules" not in ctx


# -- SetAF (collective / joint attacks) --------------------------------------


class TestValidateSetafAttacks:
    def test_keeps_valid_joint_attack_mapped_to_text(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta", "arg3": "Gamma"}
        data = {"attacks": [
            {"attackers": ["arg1", "arg2"], "target": "arg3", "rationale": "r"},
        ]}
        out = _validate_setaf_attacks(data, arg_by_id)
        assert out == [{"attackers": ["Alpha", "Beta"], "target": "Gamma"}]

    def test_drops_attack_with_unknown_attacker(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [
            {"attackers": ["arg1", "arg9"], "target": "arg2"},  # arg9 unknown
        ]}
        assert _validate_setaf_attacks(data, arg_by_id) == []

    def test_drops_attack_with_unknown_target(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [
            {"attackers": ["arg1"], "target": "arg9"},  # unknown target
        ]}
        assert _validate_setaf_attacks(data, arg_by_id) == []

    def test_drops_attack_with_no_attackers(self):
        arg_by_id = {"arg1": "Alpha"}
        data = {"attacks": [{"attackers": [], "target": "arg1"}]}
        assert _validate_setaf_attacks(data, arg_by_id) == []

    def test_removes_target_from_attackers_keeps_rest(self):
        arg_by_id = {"arg1": "Alpha", "arg3": "Gamma"}
        data = {"attacks": [
            {"attackers": ["arg1", "arg3"], "target": "arg3"},  # arg3 removed
        ]}
        out = _validate_setaf_attacks(data, arg_by_id)
        assert out == [{"attackers": ["Alpha"], "target": "Gamma"}]

    def test_drops_self_only_attack(self):
        arg_by_id = {"arg3": "Gamma"}
        data = {"attacks": [{"attackers": ["arg3"], "target": "arg3"}]}
        assert _validate_setaf_attacks(data, arg_by_id) == []

    def test_dedups_identical_attacks(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [
            {"attackers": ["arg1"], "target": "arg2"},
            {"attackers": ["arg1"], "target": "arg2"},
        ]}
        out = _validate_setaf_attacks(data, arg_by_id)
        assert out == [{"attackers": ["Alpha"], "target": "Beta"}]

    def test_dedups_repeated_attackers(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [
            {"attackers": ["arg1", "arg1"], "target": "arg2"},
        ]}
        out = _validate_setaf_attacks(data, arg_by_id)
        assert out[0]["attackers"] == ["Alpha"]

    def test_dedups_attacker_order_independence(self):
        # SetAF attacker set is a SET: {arg1,arg2} == {arg2,arg1} → one attack.
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta", "arg3": "Gamma"}
        data = {"attacks": [
            {"attackers": ["arg1", "arg2"], "target": "arg3"},
            {"attackers": ["arg2", "arg1"], "target": "arg3"},
        ]}
        out = _validate_setaf_attacks(data, arg_by_id)
        assert len(out) == 1

    def test_attackers_as_string_normalized(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [{"attackers": "arg1", "target": "arg2"}]}
        out = _validate_setaf_attacks(data, arg_by_id)
        assert out == [{"attackers": ["Alpha"], "target": "Beta"}]

    def test_empty_or_malformed_returns_empty(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        assert _validate_setaf_attacks({}, arg_by_id) == []
        assert _validate_setaf_attacks({"attacks": []}, arg_by_id) == []
        assert _validate_setaf_attacks({"attacks": "nope"}, arg_by_id) == []
        assert _validate_setaf_attacks(
            {"attacks": [{"attackers": 1, "target": "arg1"}]},  # type: ignore[dict-item]
            arg_by_id,
        ) == []


class TestSetafTranslator:
    async def test_empty_llm_output_returns_empty(self, monkeypatch):
        _patch_llm(monkeypatch, {"attacks": []})
        out = await translate_to_setaf_attacks("some text", ["a", "b"])
        assert out == []

    async def test_no_inventory_returns_empty(self, monkeypatch):
        _patch_llm(monkeypatch, {"attacks": [
            {"attackers": ["arg1"], "target": "arg2"},
        ]})
        out = await translate_to_setaf_attacks("text", [])
        assert out == []

    async def test_only_fabricated_attacks_dropped(self, monkeypatch):
        _patch_llm(monkeypatch, {"attacks": [
            {"attackers": ["arg8"], "target": "arg9"},   # unknown ids
            {"attackers": ["phantom"], "target": "ghost"},
        ]})
        out = await translate_to_setaf_attacks("text", ["a", "b"])
        assert out == []

    async def test_returns_validated_attacks_with_real_texts(self, monkeypatch):
        # SetAF attacks use canonical argument TEXTS (no PL-atom mapping).
        _patch_llm(monkeypatch, {"attacks": [
            {"attackers": ["arg1", "arg2"], "target": "arg3"},
            {"attackers": ["arg1"], "target": "arg9"},  # dropped (unknown)
        ]})
        out = await translate_to_setaf_attacks("text", ["Alpha", "Beta", "Gamma"])
        assert out == [{"attackers": ["Alpha", "Beta"], "target": "Gamma"}]


def _inject_fake_setaf_module(monkeypatch, payload):
    """Inject fake SetAFHandler + TweetyInitializer so _invoke_setaf runs w/o JVM."""
    fake_handler = types.ModuleType(
        "argumentation_analysis.agents.core.logic.setaf_handler"
    )

    class _FakeSetAFHandler:
        def __init__(self, initializer: Any) -> None:
            self.initializer = initializer

        def analyze_setaf(self, args, attacks, semantics="grounded"):
            return payload

    fake_handler.SetAFHandler = _FakeSetAFHandler  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.setaf_handler",
        fake_handler,
    )

    fake_init = types.ModuleType(
        "argumentation_analysis.agents.core.logic.tweety_initializer"
    )

    class _FakeTweetyInitializer:
        pass

    fake_init.TweetyInitializer = _FakeTweetyInitializer  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.tweety_initializer",
        fake_init,
    )


class TestSetafHandlerWiring:
    """The lazy translator call inside _invoke_setaf must persist genuine joint
    attacks into ``context`` so _record_structured_arg_status labels the axis
    ``evaluated`` — and must stay absent when nothing genuine is derived."""

    async def test_translates_and_persists_joint_attacks(self, monkeypatch):
        _inject_fake_setaf_module(monkeypatch, {"extensions": []})
        genuine = [{"attackers": ["Alpha"], "target": "Beta"}]

        async def _fake_attacks(text, args):
            return genuine

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_setaf_attacks",
            _fake_attacks,
        )
        from argumentation_analysis.orchestration.invoke_callables import _invoke_setaf

        ctx: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["Alpha", "Beta"]}
        }
        await _invoke_setaf("source text", ctx)
        assert ctx.get("set_attacks") == genuine

    async def test_does_not_override_caller_supplied_attacks(self, monkeypatch):
        called = {"n": 0}

        async def _fake_attacks(text, args):
            called["n"] += 1
            return [{"attackers": ["x"], "target": "should_not_be_used"}]

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_setaf_attacks",
            _fake_attacks,
        )
        _inject_fake_setaf_module(monkeypatch, {"extensions": []})
        from argumentation_analysis.orchestration.invoke_callables import _invoke_setaf

        genuine = [{"attackers": ["Alpha"], "target": "Beta"}]
        ctx: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["Alpha", "Beta"]},
            "set_attacks": genuine,
        }
        await _invoke_setaf("text", ctx)
        assert ctx["set_attacks"] is genuine  # unchanged
        assert called["n"] == 0  # translator never invoked

    async def test_honest_absent_when_translator_returns_empty(self, monkeypatch):
        _inject_fake_setaf_module(monkeypatch, {"extensions": []})

        async def _fake_attacks(text, args):
            return []

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_setaf_attacks",
            _fake_attacks,
        )
        from argumentation_analysis.orchestration.invoke_callables import _invoke_setaf

        ctx: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["Alpha", "Beta"]}
        }
        await _invoke_setaf("text", ctx)
        # Nothing genuine → context key stays unset → gate keeps absent_no_translator.
        assert "set_attacks" not in ctx


# -- Weighted argumentation (source, target, weight) -------------------------


class TestValidateWeightedAttacks:
    def test_keeps_valid_attack_with_weight(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [
            {"source": "arg1", "target": "arg2", "weight": 0.8, "rationale": "r"},
        ]}
        out = _validate_weighted_attacks(data, arg_by_id)
        assert out == [("Alpha", "Beta", 0.8)]

    def test_drops_attack_with_unknown_source(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [{"source": "arg9", "target": "arg2", "weight": 0.5}]}
        assert _validate_weighted_attacks(data, arg_by_id) == []

    def test_drops_attack_with_unknown_target(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [{"source": "arg1", "target": "arg9", "weight": 0.5}]}
        assert _validate_weighted_attacks(data, arg_by_id) == []

    def test_drops_self_attack(self):
        arg_by_id = {"arg1": "Alpha"}
        data = {"attacks": [{"source": "arg1", "target": "arg1", "weight": 0.5}]}
        assert _validate_weighted_attacks(data, arg_by_id) == []

    def test_clamps_weight_above_one(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [{"source": "arg1", "target": "arg2", "weight": 1.5}]}
        out = _validate_weighted_attacks(data, arg_by_id)
        assert out == [("Alpha", "Beta", 1.0)]

    def test_clamps_weight_below_zero(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [{"source": "arg1", "target": "arg2", "weight": -0.3}]}
        out = _validate_weighted_attacks(data, arg_by_id)
        assert out == [("Alpha", "Beta", 0.0)]

    def test_drops_non_numeric_weight(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [
            {"source": "arg1", "target": "arg2", "weight": "high"},  # non-numeric
        ]}
        assert _validate_weighted_attacks(data, arg_by_id) == []

    def test_dedups_identical_attacks_keeps_first_weight(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [
            {"source": "arg1", "target": "arg2", "weight": 0.9},
            {"source": "arg1", "target": "arg2", "weight": 0.1},  # dup → dropped
        ]}
        out = _validate_weighted_attacks(data, arg_by_id)
        assert out == [("Alpha", "Beta", 0.9)]

    def test_empty_or_malformed_returns_empty(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        assert _validate_weighted_attacks({}, arg_by_id) == []
        assert _validate_weighted_attacks({"attacks": []}, arg_by_id) == []
        assert _validate_weighted_attacks({"attacks": "nope"}, arg_by_id) == []
        assert _validate_weighted_attacks(
            {"attacks": [{"source": 1, "target": "arg1", "weight": 0.5}]},  # type: ignore[dict-item]
            arg_by_id,
        ) == []


class TestWeightedTranslator:
    async def test_empty_llm_output_returns_empty(self, monkeypatch):
        _patch_llm(monkeypatch, {"attacks": []})
        out = await translate_to_weighted_attacks("some text", ["a", "b"])
        assert out == []

    async def test_no_inventory_returns_empty(self, monkeypatch):
        _patch_llm(monkeypatch, {"attacks": [
            {"source": "arg1", "target": "arg2", "weight": 0.5},
        ]})
        out = await translate_to_weighted_attacks("text", [])
        assert out == []

    async def test_only_fabricated_attacks_dropped(self, monkeypatch):
        _patch_llm(monkeypatch, {"attacks": [
            {"source": "arg8", "target": "arg9", "weight": 0.5},  # unknown ids
        ]})
        out = await translate_to_weighted_attacks("text", ["a", "b"])
        assert out == []

    async def test_returns_validated_triples_with_real_weights(self, monkeypatch):
        _patch_llm(monkeypatch, {"attacks": [
            {"source": "arg1", "target": "arg2", "weight": 0.7},
            {"source": "arg1", "target": "arg9", "weight": 0.5},  # dropped (unknown)
            {"source": "arg2", "target": "arg1", "weight": 2.0},  # clamped to 1.0
        ]})
        out = await translate_to_weighted_attacks("text", ["Alpha", "Beta"])
        assert out == [("Alpha", "Beta", 0.7), ("Beta", "Alpha", 1.0)]


def _inject_fake_weighted_module(monkeypatch, payload):
    """Inject fake WeightedHandler + TweetyInitializer so _invoke_weighted runs w/o JVM."""
    fake_handler = types.ModuleType(
        "argumentation_analysis.agents.core.logic.weighted_handler"
    )

    class _FakeWeightedHandler:
        def __init__(self, initializer: Any) -> None:
            self.initializer = initializer

        def analyze_weighted_framework(self, args, attacks, semantics="grounded"):
            return payload

    fake_handler.WeightedHandler = _FakeWeightedHandler  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.weighted_handler",
        fake_handler,
    )

    fake_init = types.ModuleType(
        "argumentation_analysis.agents.core.logic.tweety_initializer"
    )

    class _FakeTweetyInitializer:
        pass

    fake_init.TweetyInitializer = _FakeTweetyInitializer  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.tweety_initializer",
        fake_init,
    )


class TestWeightedHandlerWiring:
    """The lazy translator call inside _invoke_weighted must persist genuine
    weighted attacks into ``context`` so _record_structured_arg_status labels the
    axis ``evaluated`` — and must stay absent when nothing genuine is derived."""

    async def test_translates_and_persists_weighted_attacks(self, monkeypatch):
        _inject_fake_weighted_module(monkeypatch, {"extensions": []})
        genuine: List[Tuple[str, str, float]] = [("Alpha", "Beta", 0.8)]

        async def _fake_attacks(text, args):
            return genuine

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_weighted_attacks",
            _fake_attacks,
        )
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_weighted,
        )

        ctx: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["Alpha", "Beta"]}
        }
        await _invoke_weighted("source text", ctx)
        assert ctx.get("weighted_attacks") == genuine

    async def test_does_not_override_caller_supplied_attacks(self, monkeypatch):
        called = {"n": 0}

        async def _fake_attacks(text, args):
            called["n"] += 1
            return [("x", "y", 0.5)]

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_weighted_attacks",
            _fake_attacks,
        )
        _inject_fake_weighted_module(monkeypatch, {"extensions": []})
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_weighted,
        )

        genuine: List[Tuple[str, str, float]] = [("Alpha", "Beta", 0.9)]
        ctx: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["Alpha", "Beta"]},
            "weighted_attacks": genuine,
        }
        await _invoke_weighted("text", ctx)
        assert ctx["weighted_attacks"] is genuine  # unchanged
        assert called["n"] == 0  # translator never invoked

    async def test_honest_absent_when_translator_returns_empty(self, monkeypatch):
        _inject_fake_weighted_module(monkeypatch, {"extensions": []})

        async def _fake_attacks(text, args):
            return []

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "translate_to_weighted_attacks",
            _fake_attacks,
        )
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_weighted,
        )

        ctx: Dict[str, Any] = {
            "phase_extract_output": {"arguments": ["Alpha", "Beta"]}
        }
        await _invoke_weighted("text", ctx)
        # Nothing genuine → context key stays unset → gate keeps absent_no_translator.
        assert "weighted_attacks" not in ctx
