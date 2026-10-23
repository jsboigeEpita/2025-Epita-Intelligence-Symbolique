# -*- coding: utf-8 -*-
"""#3162 — a coalition is projected as irreducible only if it is.

``_setaf_finding`` said, for **every** set-attack with ≥ 2 attackers, that the
coalition defeats a target « qu'aucun ne renverse seul ». Its own docstring
states the condition; the code never tested it. On the R1107c state the frame
held ``{arg_3} -> arg_6`` *and* ``{arg_7, arg_3} -> arg_6``: the coalition is a
superset of an existing attack, and the Act III prompt carried a formal claim
the frame itself refutes.

Irreducibility is now read from the frame the coalition lives in: a coalition
is projected only when no proper subset of it attacks the same target there
(unary or smaller set-attack). A frame whose only joint attacks are non-minimal
yields no SETAF finding — the honest absence the docstring already intended for
unary attacks (#1019).

Anti-pendulum: genuine joint attacks stay projected. SETAF's singularity is
exactly what binary Dung cannot express (#1647, #1667).

Synthetic atoms only (privacy HARD).
"""

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
)

from .test_act3_conclusion_plugin import _formalism_specific_state

_TARGET = "claim_gamma"


def _setaf_findings(attacks):
    state = _formalism_specific_state({"set_attacks": attacks})
    return [
        f
        for f in build_act3_evidence(state).structured_findings
        if f.capability == "setaf_reasoning"
    ]


class TestIrreducibilityIsReadNotAsserted:
    def test_a_coalition_reducible_to_a_unary_attack_is_not_projected(self):
        """Born red on main: the frame carries ``{claim_alpha} -> target`` and
        the projection still claimed no member defeats it alone."""
        findings = _setaf_findings(
            [
                {"attackers": ["claim_alpha"], "target": _TARGET},
                {"attackers": ["claim_alpha", "claim_beta"], "target": _TARGET},
            ]
        )
        assert findings == []

    def test_a_smaller_coalition_also_reduces_it(self):
        """The same rule one arity up, and it is per-coalition: the
        3-coalition containing a 2-coalition that already attacks the target
        is dropped, while the 2-coalition that IS minimal stays projected."""
        findings = _setaf_findings(
            [
                {"attackers": ["claim_alpha", "claim_beta"], "target": _TARGET},
                {
                    "attackers": ["claim_alpha", "claim_beta", "claim_delta"],
                    "target": _TARGET,
                },
            ]
        )
        (finding,) = findings
        assert "une coalition de 2 arguments" in finding.statement
        assert "claim_delta" not in finding.statement

    def test_a_genuine_joint_attack_is_still_projected(self):
        """Control — nothing in the frame attacks the target but the
        coalition: SETAF says something Dung cannot, and it still says it."""
        (finding,) = _setaf_findings(
            [{"attackers": ["claim_alpha", "claim_beta"], "target": _TARGET}]
        )
        assert "qu'aucun ne renverse seul" in finding.statement
        assert _TARGET in finding.statement

    def test_an_unrelated_unary_attack_does_not_reduce_it(self):
        """Control — a unary attack on ANOTHER target says nothing about this
        coalition; the reduction must be read on the same target."""
        (finding,) = _setaf_findings(
            [
                {"attackers": ["claim_epsilon"], "target": "claim_delta"},
                {"attackers": ["claim_alpha", "claim_beta"], "target": _TARGET},
            ]
        )
        assert "qu'aucun ne renverse seul" in finding.statement
