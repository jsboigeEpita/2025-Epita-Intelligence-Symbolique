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

import pytest

import argumentation_analysis.orchestration.invoke_callables as mod

pytestmark = [pytest.mark.jpype, pytest.mark.tweety]

_LONG_TEXT = "A sufficiently long synthetic source text for the FOL/formal phases. " * 6


def _ctx(defeasible_rules: list) -> dict:
    """A context that hands ``_invoke_aspic`` the rules DIRECTLY.

    Supplying BOTH ``defeasible_rules`` (non-empty) AND ``strict_rules``
    (non-empty) neutralizes the auto-shape branches — the ``if not defeasible``
    and ``if not strict`` blocks that otherwise build
    ``supported_N``/``argument_chain``/``plausible_conclusion_N`` from raw args.
    Those scaffolding atoms never coincide with the contradiction's target and
    make the framework non-deterministic across environments (local vs CI).
    Passing a trivial empty-body strict rule (``{"head": "strict_seed", "body": []}``)
    keeps the strict layer non-empty (truthy) without adding conflicting atoms.
    """
    return {
        "arguments": ["claim one", "claim two", "claim three"],
        "defeasible_rules": list(defeasible_rules),
        # Non-empty → skips the strict auto-shape (which would build
        # ``supported_*``/``argument_chain`` from args and pollute the framework).
        "strict_rules": [{"head": "strict_seed", "body": []}],
        "phase_extract_output": {"claims": []},
        "phase_hierarchical_fallacy_output": {"fallacies": []},
    }


class TestPairedRunContradictionFlipsAxis:
    """DoD item 1 — without the channel 0 attack, with it ≥1, justified."""

    async def test_without_channel_zero_attack(self):
        """Positive rules only ⇒ 0 attack (the inert axis).

        The leaf atom (a) is derived as an ordinary premise (manque 1) ⇒ the
        rule fires ⇒ ≥1 argument, but uncontested ⇒ ONE extension, ZERO attack.
        """
        out = await mod._invoke_aspic(
            _LONG_TEXT,
            _ctx([{"head": "c", "body": ["a"], "name": "def_rule_1"}]),
        )
        assert out["statistics"]["attacks_count"] == 0, out
        assert out["statistics"]["dung_attacks_count"] == 0, out
        assert out["attacks"] == []

    async def test_with_channel_attack_appears(self):
        """A contradiction (attacker b contests conclusion c) ⇒ ≥1 attack."""
        out = await mod._invoke_aspic(
            _LONG_TEXT,
            _ctx(
                [
                    {"head": "c", "body": ["a"], "name": "def_rule_1"},
                    {
                        "head": "c",
                        "body": ["b"],
                        "name": "def_con_1",
                        "head_negated": True,
                    },
                ]
            ),
        )
        assert out["statistics"]["attacks_count"] >= 1, out
        assert out["statistics"]["dung_attacks_count"] >= 1, out
        scopes = [a["scope"] for a in out["attacks"]]
        assert "rebut" in scopes, f"expected a rebut, got {scopes}"

    async def test_premises_alone_do_not_fabricate_arbitration(self):
        """Anti-pendule (#1678): premises without contradictions ⇒ ZERO attack.

        Two independent positive rules: non-empty extensions, but ZERO attack —
        the axis has produced arguments without arbitrating anything.``extensions``
        non-empty is NOT "has arbitrated".
        """
        out = await mod._invoke_aspic(
            _LONG_TEXT,
            _ctx(
                [
                    {"head": "c", "body": ["a"], "name": "def_rule_1"},
                    {"head": "d", "body": ["b"], "name": "def_rule_2"},
                ]
            ),
        )
        assert out["statistics"]["attacks_count"] == 0, out
        assert out["attacks"] == []


class TestExtCountStaysDescriptive:
    """DoD item 4 (#1671/#1674) — ext_count describes, no label derives from it."""

    async def test_single_extension_with_attack_is_not_consistent_sur_vide(self):
        """An undercut yields ONE extension yet a real attack — ext_count==1 must
        not read as 'uncontested'. The attack list, not ext_count, carries the
        arbitration signal."""
        out = await mod._invoke_aspic(
            _LONG_TEXT,
            _ctx(
                [
                    {"head": "c", "body": ["a"], "name": "def_rule_1"},
                    {
                        "head": "def_rule_1",
                        "body": ["b"],
                        "name": "def_unc_1",
                        "head_negated": True,
                    },
                ]
            ),
        )
        scopes = [a["scope"] for a in out["attacks"]]
        assert "undercut" in scopes, out
        # The arbitration signal is the attack set, decoupled from ext_count.
        assert out["statistics"]["attacks_count"] >= 1
