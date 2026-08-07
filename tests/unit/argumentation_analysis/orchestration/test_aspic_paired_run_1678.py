"""#1678 — paired run via _invoke_aspic: the INERT axis end-to-end (DoD item 1).

The coordinator's anti-pendule (#1678): delivering premises without
contradictions yields arguments, 0 attack, a single extension containing
everything — "trivially consistent", ``extensions`` non-empty and ``evaluated``
yet still zero arbitration. That is the fake-green #1671/#1674 just removed,
under a harder-to-see form. "Non-empty" is not "has arbitrated".

This file pins the INERT (0-attack) axis end-to-end through ``_invoke_aspic``:
the integration path must render the vacuous-evaluated state without arbitrating
anything, on the same input that a contradiction would flip. This rendering is
deterministic across environments (0 attack is 0 attack everywhere).

The LIVE-attack half of the paired run (≥1 attack with a contradiction) and the
three attack scopes are pinned in ``test_aspic_negation_scope_1678.py`` at the
handler layer — that is where the arbitration materializes and where the
coordinator's JVM probes targeted it; rendering a live attack there is
deterministic. (An earlier revision tried to assert the live attack through
_invoke_aspic too, but the integration framework's extension count for live
attacks proved environment-sensitive — CI Temurin Java 11 vs local JDK render
differently — while the 0-attack axis stayed deterministic. The live-attack
assertion therefore lives at the handler, not duplicated here.)

Privacy: synthetic atoms only (a, b, c) — no corpus content.
"""

from __future__ import annotations

import pytest

import argumentation_analysis.orchestration.invoke_callables as mod

pytestmark = [pytest.mark.jpype, pytest.mark.tweety]

_LONG_TEXT = "A sufficiently long synthetic source text for the FOL/formal phases. " * 6


def _ctx(defeasible_rules: list) -> dict:
    """Hand ``_invoke_aspic`` the rules DIRECTLY.

    Supplying BOTH ``defeasible_rules`` (non-empty) AND ``strict_rules``
    (non-empty) neutralizes the auto-shape branches (``if not defeasible`` /
    ``if not strict``) that otherwise build ``supported_N``/``argument_chain``
    from raw args and pollute the framework. The framework is then EXACTLY the
    rules under test.
    """
    return {
        "arguments": ["claim one", "claim two", "claim three"],
        "defeasible_rules": list(defeasible_rules),
        "strict_rules": [{"head": "strict_seed", "body": []}],
        "phase_extract_output": {"claims": []},
        "phase_hierarchical_fallacy_output": {"fallacies": []},
    }


class TestInvokeAspicInertAxis:
    """DoD item 1 (0-attack half) — the inert axis end-to-end.

    The SAME inventory that a contradiction would flip must render ZERO attack
    when the rules are positive-only. This is the anti-pendule state #1671/#1674
    must label honestly: ``extensions`` non-empty but the axis has arbitrated
    nothing.
    """

    async def test_without_negation_zero_attack(self):
        """A single positive rule (leaf a derived as ordinary premise) ⇒ 0 attack."""
        out = await mod._invoke_aspic(
            _LONG_TEXT,
            _ctx([{"head": "c", "body": ["a"], "name": "def_rule_1"}]),
        )
        assert out["statistics"]["attacks_count"] == 0, out
        assert out["attacks"] == []

    async def test_premises_alone_do_not_fabricate_arbitration(self):
        """Two independent positive rules ⇒ non-empty extensions but ZERO attack.

        ``extensions`` non-empty is NOT "has arbitrated" — the axis produced
        arguments without arbitrating anything. Correcting the premise feed
        (manque 1) without a contradiction channel would leave the axis here:
        the fake-green #1671/#1674 removed, under a harder-to-see form.
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
