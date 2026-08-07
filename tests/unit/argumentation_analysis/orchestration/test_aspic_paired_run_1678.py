"""#1678 — paired run: the contradictions channel flips ASPIC+ from inert to
arbitrating on the SAME input (DoD item 1).

The coordinator's anti-pendule (#1678): delivering premises without
contradictions yields 6 arguments, 0 attack, 1 extension containing everything —
"trivially consistent", ``extensions`` non-empty and ``evaluated`` yet still
zero arbitration. That is the fake-green #1671/#1674 just removed, under a
harder-to-see form. "Non-empty" is not "has arbitrated".

This test pins the discrimination on the real JVM (no mock handler): the SAME
inventory, fed through ``_invoke_aspic``, must show **0 attack** when the
translator emits only positive rules, and **≥1 attack** (≥2 extensions) when it
adds a contradiction. The translator is mocked (no network); the handler runs
on the real JVM. ext_count stays a description — no label derives from it alone.

Privacy: synthetic atoms only (a, b, c) — no corpus content.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import argumentation_analysis.orchestration.invoke_callables as mod
from argumentation_analysis.orchestration.structured_arg_translator import (
    TranslationResult,
    CAUSE_EVALUATED,
)

pytestmark = [pytest.mark.jpype, pytest.mark.tweety]

_TRANSLATOR = "argumentation_analysis.orchestration.structured_arg_translator.translate_to_aspic_rules"

_LONG_TEXT = "A sufficiently long synthetic source text for the FOL/formal phases. " * 6


def _ctx() -> dict:
    # No caller-supplied rules/axioms → _invoke_aspic derives them via the
    # translator (mocked) + the leaf-axiom derivation (#1678 manque 1).
    return {"arguments": ["claim one", "claim two", "claim three"]}


class TestPairedRunContradictionFlipsAxis:
    """DoD item 1 — without the channel 0 attack, with it ≥1, justified."""

    async def test_without_channel_zero_attack(self):
        """Translator emits only positive rules ⇒ 0 attack (the inert axis)."""
        positive_only = TranslationResult(
            relations=[{"head": "c", "body": ["a"], "name": "def_rule_1"}],
            cause=CAUSE_EVALUATED,
        )
        with patch(_TRANSLATOR, AsyncMock(return_value=positive_only)):
            out = await mod._invoke_aspic(_LONG_TEXT, _ctx())

        # The leaf atom (a) is derived as an ordinary premise ⇒ the rule fires
        # ⇒ ≥1 argument, but uncontested ⇒ ONE extension, ZERO attack.
        assert out["statistics"]["attacks_count"] == 0, out
        assert out["statistics"]["extensions_count"] == 1
        assert out["attacks"] == []

    async def test_with_channel_attack_appears(self):
        """Translator adds a contradiction ⇒ ≥1 attack, ≥2 extensions."""
        with_channel = TranslationResult(
            relations=[
                {"head": "c", "body": ["a"], "name": "def_rule_1"},
                # A contradiction: an attacker (b) contests the conclusion c.
                {
                    "head": "c",
                    "body": ["b"],
                    "name": "def_con_1",
                    "head_negated": True,
                },
            ],
            cause=CAUSE_EVALUATED,
        )
        with patch(_TRANSLATOR, AsyncMock(return_value=with_channel)):
            out = await mod._invoke_aspic(_LONG_TEXT, _ctx())

        assert out["statistics"]["attacks_count"] >= 1, out
        assert out["statistics"]["extensions_count"] >= 2, out
        scopes = [a["scope"] for a in out["attacks"]]
        assert "rebut" in scopes, f"expected a rebut, got {scopes}"

    async def test_premises_alone_do_not_fabricate_arbitration(self):
        """Anti-pendule (#1678): premises without contradictions ⇒ non-empty but
        still zero attack. ``extensions`` non-empty is NOT "has arbitrated"."""
        positive_only = TranslationResult(
            relations=[
                {"head": "c", "body": ["a"], "name": "def_rule_1"},
                {"head": "d", "body": ["b"], "name": "def_rule_2"},
            ],
            cause=CAUSE_EVALUATED,
        )
        with patch(_TRANSLATOR, AsyncMock(return_value=positive_only)):
            out = await mod._invoke_aspic(_LONG_TEXT, _ctx())

        # Two independent positive rules: non-empty extensions, but ZERO attack —
        # the axis has produced arguments without arbitrating anything.
        assert out["statistics"]["attacks_count"] == 0, out
        assert out["attacks"] == []


class TestExtCountStaysDescriptive:
    """DoD item 4 (#1671/#1674) — ext_count describes, no label derives from it."""

    async def test_single_extension_with_attack_is_not_consistent_sur_vide(self):
        """An undercut yields ONE extension yet a real attack — ext_count==1 must
        not read as 'uncontested'. The attack list, not ext_count, carries the
        arbitration signal."""
        with_undercut = TranslationResult(
            relations=[
                {"head": "c", "body": ["a"], "name": "def_rule_1"},
                {
                    "head": "def_rule_1",
                    "body": ["b"],
                    "name": "def_unc_1",
                    "head_negated": True,
                },
            ],
            cause=CAUSE_EVALUATED,
        )
        with patch(_TRANSLATOR, AsyncMock(return_value=with_undercut)):
            out = await mod._invoke_aspic(_LONG_TEXT, _ctx())

        # An undercut is asymmetric: it can collapse to one extension, yet a
        # genuine attack is present. ext_count alone would read "uncontested";
        # the attacks list says otherwise.
        scopes = [a["scope"] for a in out["attacks"]]
        assert "undercut" in scopes, out
        # The arbitration signal is the attack set, decoupled from ext_count.
        assert out["statistics"]["attacks_count"] >= 1
