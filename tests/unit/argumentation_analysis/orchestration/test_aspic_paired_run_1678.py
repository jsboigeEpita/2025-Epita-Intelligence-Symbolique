"""#1678 — paired run: the contradictions channel flips ASPIC+ from inert to
arbitrating on the SAME input (DoD item 1).

The coordinator's anti-pendule (#1678): delivering premises without
contradictions yields arguments, 0 attack, a single extension containing
everything — "trivially consistent", ``extensions`` non-empty and ``evaluated``
yet still zero arbitration. That is the fake-green #1671/#1674 just removed,
under a harder-to-see form. "Non-empty" is not "has arbitrated".

Two test layers pin the discrimination on the real JVM (no mock handler):

1. **Handler-level paired run** (DoD item 1, deterministic): the SAME inventory,
   fed directly to ``ASPICHandler``, must show **0 attack** when the rules are
   positive-only, and **≥1 attack** when one adds a negated-head contradiction.
   This is the core DoD — measured at the handler because that is where the
   arbitration materializes (the coordinator's probes targeted the same layer).
2. **Integration-level paired run** (via ``_invoke_aspic``): confirms the
   0-attack axis (the inert / vacuous-evaluated state) end-to-end. The
   integration path's framework assembly (translator + auto-shape) is
   environment-sensitive in its EXTENSION COUNT for live attacks, so the
   live-attack assertion lives at the handler layer above.

Privacy: synthetic atoms only (a, b, c) — no corpus content.
"""

from __future__ import annotations

import pytest

import argumentation_analysis.orchestration.invoke_callables as mod
from argumentation_analysis.agents.core.logic.aspic_handler import ASPICHandler

pytestmark = [pytest.mark.jpype, pytest.mark.tweety]

_LONG_TEXT = "A sufficiently long synthetic source text for the FOL/formal phases. " * 6


def _handler() -> ASPICHandler:
    return ASPICHandler()  # type: ignore[no-untyped-call]


class TestPairedRunContradictionFlipsAxisHandler:
    """DoD item 1 — at the handler, the SAME inventory: 0 attack without a
    contradiction, ≥1 with. Deterministic (handler-direct, cross-JDK)."""

    def test_without_negation_zero_attack(self):
        """Positive rules only ⇒ 0 attack (the inert / vacuous-evaluated axis).

        With the leaf (a) as an ordinary premise the rule fires ⇒ ≥1 argument,
        but uncontested ⇒ ONE extension, ZERO attack. This is the state #1671/
        #1674 must label honestly: 'evaluated' but has arbitrated nothing.
        """
        out = _handler().analyze_aspic_framework(
            strict_rules=[],
            defeasible_rules=[
                {"head": "c", "body": ["a"], "name": "d_main"},
            ],
            axioms=["a"],
        )
        assert out["statistics"]["attacks_count"] == 0, out
        assert out["statistics"]["dung_attacks_count"] == 0, out
        assert out["attacks"] == []

    def test_with_negation_attack_appears(self):
        """A contradiction (b => !c) ⇒ ≥1 attack, ≥2 extensions.

        Same inventory as above plus a negated-head rule contesting the
        conclusion c. The axis flips from inert to arbitrating.
        """
        out = _handler().analyze_aspic_framework(
            strict_rules=[],
            defeasible_rules=[
                {"head": "c", "body": ["a"], "name": "d_main"},
                {
                    "head": "c",
                    "body": ["b"],
                    "name": "d_con",
                    "head_negated": True,
                },
            ],
            axioms=["a", "b"],
        )
        assert out["statistics"]["attacks_count"] >= 1, out
        assert out["statistics"]["dung_attacks_count"] >= 1, out
        scopes = [a["scope"] for a in out["attacks"]]
        assert "rebut" in scopes, f"expected a rebut, got {scopes}"


class TestInvokeAspicInertAxis:
    """The 0-attack (inert) axis end-to-end through ``_invoke_aspic``.

    Confirms the integration path renders the vacuous-evaluated state without
    arbitrating anything. The live-attack (≥1) assertion lives at the handler
    layer (TestPairedRunContradictionFlipsAxisHandler) because the integration
    framework assembly's extension count for live attacks is environment-sensitive.
    """

    @staticmethod
    def _ctx(defeasible_rules: list) -> dict:
        """Hand _invoke_aspic the rules DIRECTLY.

        Supplying BOTH ``defeasible_rules`` (non-empty) AND ``strict_rules``
        (non-empty) neutralizes the auto-shape branches (``if not defeasible`` /
        ``if not strict``) that otherwise build ``supported_N``/
        ``argument_chain`` from raw args and pollute the framework.
        """
        return {
            "arguments": ["claim one", "claim two", "claim three"],
            "defeasible_rules": list(defeasible_rules),
            "strict_rules": [{"head": "strict_seed", "body": []}],
            "phase_extract_output": {"claims": []},
            "phase_hierarchical_fallacy_output": {"fallacies": []},
        }

    async def test_without_negation_zero_attack(self):
        """Positive rules only through the full invoke path ⇒ 0 attack."""
        out = await mod._invoke_aspic(
            _LONG_TEXT,
            self._ctx([{"head": "c", "body": ["a"], "name": "def_rule_1"}]),
        )
        assert out["statistics"]["attacks_count"] == 0, out
        assert out["attacks"] == []

    async def test_premises_alone_do_not_fabricate_arbitration(self):
        """Anti-pendule (#1678): premises without contradictions ⇒ ZERO attack.

        Two independent positive rules: non-empty extensions, but ZERO attack —
        the axis has produced arguments without arbitrating anything.
        ``extensions`` non-empty is NOT "has arbitrated".
        """
        out = await mod._invoke_aspic(
            _LONG_TEXT,
            self._ctx(
                [
                    {"head": "c", "body": ["a"], "name": "def_rule_1"},
                    {"head": "d", "body": ["b"], "name": "def_rule_2"},
                ]
            ),
        )
        assert out["statistics"]["attacks_count"] == 0, out
        assert out["attacks"] == []


class TestExtCountStaysDescriptive:
    """DoD item 4 (#1671/#1674) — ext_count describes, no label derives from it.

    Measured at the handler (deterministic): an undercut yields ONE extension yet
    a real attack. ``ext_count==1`` must not read as 'uncontested'; the attack
    set, decoupled from ext_count, carries the arbitration signal.
    """

    def test_single_extension_with_attack_is_not_consistent_sur_vide(self):
        out = _handler().analyze_aspic_framework(
            strict_rules=[],
            defeasible_rules=[
                {"head": "c", "body": ["a"], "name": "d_main"},
                {
                    "head": "d_main",
                    "body": ["b"],
                    "name": "d_unc",
                    "head_negated": True,
                },
            ],
            axioms=["a", "b"],
        )
        scopes = [a["scope"] for a in out["attacks"]]
        assert "undercut" in scopes, out
        # The arbitration signal is the attack set, decoupled from ext_count.
        assert out["statistics"]["attacks_count"] >= 1
