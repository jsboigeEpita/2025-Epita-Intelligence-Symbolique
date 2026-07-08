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
from typing import Any, Dict, List

import pytest

from argumentation_analysis.orchestration.structured_arg_translator import (
    _build_inventory,
    _validate_contraries,
    _validate_supports,
    translate_to_aba_contraries,
    translate_to_bipolar_supports,
)


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
