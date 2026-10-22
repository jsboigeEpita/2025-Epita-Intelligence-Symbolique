# -*- coding: utf-8 -*-
"""#3153 — the Dung decoder must tell OUT from UNDEC in the grounded labelling.

Measured on doc_B (R1107): the grounded frame ``dung_4`` holds 40 nodes and 4
attacks — ``arg_6→arg_1``, ``arg_6→arg_3``, ``arg_1→arg_6``, ``arg_11→arg_4``.
The grounded extension excludes arg_1, arg_3, arg_4 and arg_6; the preferred
frame puts arg_1 and arg_3 in extension 0 and arg_6 in extension 1. The old
reader (``rejected_from_framework``) called every node absent from the accepted
set *rejected* — so a mutual attack, a stand-off the graph does NOT settle,
became four formal rejections, and Act III promoted their targets to P1
« the most solid formal verdict ».

The contract pinned here (offline, synthetic, no corpus text, no LLM, no JVM):

* the decoder computes the grounded labelling (in / out / undec) from the
  frame's own attack graph; only an **out** argument (attacked by an **in**)
  is a rejection;
* an **undec** argument is a finding, not a rejection: the record names it,
  and a preferred/stable extension containing it makes it *credulously
  accepted*;
* a frame whose graph cannot be decoded is non-concluable — never a guessed
  labelling;
* on an acyclic frame the rejections are unchanged (the #1912 axis keeps its
  genuine verdicts);
* Act III reads the decoder: the Dung weak points and the P1 (decisive) item
  name the out argument alone.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from argumentation_analysis.reporting.restitution.native_dung import (
    decode_native_dung,
)


def _undecided(decoding: Any) -> dict:
    """The undecided record, asserted to EXIST (born-red on assertions).

    The pre-fix ``NativeDungDecoding`` carries no such field; reading it
    through a default would turn that absence into a vacuous {} and could
    pass a control test that should redden the very day the field is lost.
    """
    assert hasattr(decoding, "undecided_by_arg"), (
        "#3153: the decoder must expose the undecided arguments — a "
        "stand-off the graph does not settle is a finding, and dropping the "
        "record hides it"
    )
    return decoding.undecided_by_arg


def _credulous(decoding: Any) -> dict:
    assert hasattr(decoding, "credulously_accepted"), (
        "#3153: an undecided argument present in a preferred/stable "
        "extension must be reportable as credulously accepted"
    )
    return decoding.credulously_accepted


# The doc_B shape: one graph, an unattacked attacker (arg_11), a mutual
# attack (arg_1 ↔ arg_6), arg_3 attacked only by the undecided arg_6, and
# arg_4 attacked by the unattacked arg_11.
ARGS = ["arg_1", "arg_3", "arg_4", "arg_6", "arg_11"]
ATTACKS = [
    ["arg_6", "arg_1"],
    ["arg_6", "arg_3"],
    ["arg_1", "arg_6"],
    ["arg_11", "arg_4"],
]


def _state(frameworks: dict, args: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        identified_arguments=(
            args
            if args is not None
            else {
                "arg_1": "Thèse synthétique un.",
                "arg_3": "Thèse synthétique trois.",
                "arg_4": "Thèse synthétique quatre.",
                "arg_6": "Thèse synthétique six.",
                "arg_11": "Thèse synthétique onze.",
            }
        ),
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks=frameworks,
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
        analysis_coverage={},
    )


def _doc_b_like_state() -> SimpleNamespace:
    """Grounded + preferred frames over the measured graph."""
    return _state(
        {
            "fw_grounded": {
                "name": "verification_grounded",
                "arguments": list(ARGS),
                "attacks": [list(a) for a in ATTACKS],
                # grounded extension: the unattacked node only
                "extensions": {"all_members": ["arg_11"]},
            },
            "fw_preferred": {
                "name": "verification_preferred",
                "arguments": list(ARGS),
                "attacks": [list(a) for a in ATTACKS],
                # two extensions: {arg_11, arg_1, arg_3} and {arg_11, arg_6}
                "extensions": {
                    "e0": ["arg_11", "arg_1", "arg_3"],
                    "e1": ["arg_11", "arg_6"],
                },
            },
        }
    )


class TestGroundedLabelling:
    def test_the_measured_graph_labels_out_and_undec(self):
        # Lazy import: the pre-fix tree must redden on assertions, not on a
        # module-level ImportError of a symbol that does not exist yet.
        from argumentation_analysis.reporting.restitution.native_dung import (
            grounded_labelling,
        )

        fw = {
            "name": "verification_grounded",
            "arguments": list(ARGS),
            "attacks": [list(a) for a in ATTACKS],
            "extensions": {"all_members": ["arg_11"]},
        }
        labelling = grounded_labelling(fw)
        assert labelling == {
            "arg_11": "in",
            "arg_1": "undec",
            "arg_3": "undec",
            "arg_4": "out",
            "arg_6": "undec",
        }, (
            "#3153: the grounded labelling of the measured graph is arg_11 in, "
            f"arg_4 out, the mutual-attack stand-off undec; got {labelling!r}"
        )

    def test_undecodable_graph_is_none_not_a_guess(self):
        from argumentation_analysis.reporting.restitution.native_dung import (
            grounded_labelling,
        )

        # No honest labelling is possible: the attack list carries a
        # non-pair entry. The decoder must say unknown, never guess.
        assert (
            grounded_labelling(
                {
                    "name": "verification_grounded",
                    "arguments": ["arg_1"],
                    "attacks": [["arg_1"]],
                    "extensions": {"all_members": []},
                }
            )
            is None
        )


class TestDecoderTellsOutFromUndec:
    def test_witness_one_rejection_three_undecided(self):
        # #3153 DoD witness, born red: before the fix the decoder returns
        # FOUR rejections (arg_1, arg_3, arg_4, arg_6); after it returns one,
        # plus the three undecided.
        decoding = decode_native_dung(_doc_b_like_state())
        assert set(decoding.rejected_by_arg) == {"arg_4"}, (
            "#3153: grounded non-membership is not rejection — arg_1/arg_3/"
            "arg_6 are undecided (mutual attack / attacked by an undecided "
            f"argument), only arg_4 is out; got {decoding.rejected_by_arg!r}"
        )
        assert set(_undecided(decoding)) == {"arg_1", "arg_3", "arg_6"}, (
            "#3153: the stand-off must be RECORDED as undecided — hiding it "
            f"is the pendulum the issue forbids; got {_undecided(decoding)!r}"
        )
        # Preferred/stable extensions contain them: credulously accepted.
        assert _credulous(decoding) == {
            "arg_1": "preferred",
            "arg_3": "preferred",
            "arg_6": "preferred",
        }, (
            "#3153: an undecided argument present in a preferred extension "
            "must be reportable as credulously accepted; got "
            f"{_credulous(decoding)!r}"
        )

    def test_control_acyclic_frame_rejections_unchanged(self):
        # DoD control: no cycle → out == absent from the accepted extension.
        state = _state(
            {
                "fw_pref": {
                    "name": "verification_preferred",
                    "arguments": ["arg_1", "arg_2"],
                    "attacks": [["arg_2", "arg_1"]],
                    "extensions": {"all_members": ["arg_2"]},
                }
            }
        )
        decoding = decode_native_dung(state)
        assert decoding.rejected_by_arg == {"arg_1": "preferred"}
        assert _undecided(decoding) == {}

    def test_self_attack_is_undecided_not_rejected(self):
        # A self-attacking node is undecided in the grounded labelling (it is
        # attacked by nothing in). The #1912 rule this refines — a decodable
        # empty extension is CONCLUABLE, never "unknown" — still holds:
        # non_concluable stays empty and the finding names the stand-off.
        state = _state(
            {
                "fw_g": {
                    "name": "verification_grounded",
                    "arguments": ["arg_1"],
                    "attacks": [["arg_1", "arg_1"]],
                    "extensions": {"all_members": []},
                }
            }
        )
        decoding = decode_native_dung(state)
        assert decoding.non_concluable == []
        assert decoding.rejected_by_arg == {}
        assert _undecided(decoding) == {"arg_1": "grounded"}

    def test_undecodable_graph_contributes_no_verdict_and_says_so(self):
        state = _state(
            {
                "fw_g": {
                    "name": "verification_grounded",
                    "arguments": ["arg_1", "arg_2"],
                    "attacks": [["arg_1"]],  # malformed pair
                    "extensions": {"all_members": ["arg_1"]},
                }
            }
        )
        decoding = decode_native_dung(state)
        assert decoding.rejected_by_arg == {}
        assert _undecided(decoding) == {}
        assert decoding.non_concluable == ["grounded"], (
            "#3153: a graph the decoder cannot read is non-concluable — the "
            "honest unknown, never a guessed labelling"
        )

    def test_sidecars_never_contribute_a_labelling(self):
        state = _state(
            {
                "fw_aba": {
                    "name": "aba_preferred",
                    "arguments": ["arg_1", "arg_2"],
                    "attacks": [["arg_2", "arg_1"]],
                    "extensions": {"aba_extensions": [["arg_2"]]},
                }
            }
        )
        decoding = decode_native_dung(state)
        assert decoding.rejected_by_arg == {}
        assert _undecided(decoding) == {}
        assert decoding.non_concluable == []


class TestAct2SaysTheStandOff:
    def test_the_conflict_is_named_not_folded_into_the_rejection(self):
        # #3153 requested 2: an undecided argument is read as "the graph does
        # not settle this conflict", and an accepted extension containing it
        # makes it credulously accepted. The prose COUNTS (#1908), never names.
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_formal_findings,
        )

        findings = [
            f for f in _collect_formal_findings(_doc_b_like_state()) if f.kind == "dung"
        ]
        assert len(findings) == 1, (
            "#3153: the Dung axis must yield exactly one reading, got "
            f"{[f.kind for f in findings]!r}"
        )
        verdict, detail = findings[0].verdict, findings[0].detail
        assert (
            "1 des 5" in verdict
        ), f"#3153: the rejection count is one, got {verdict!r}"
        assert "3 en suspens" in verdict, (
            "#3153: the three undecided arguments must be counted in the "
            f"reading — hiding the stand-off is the pendulum; got {verdict!r}"
        )
        assert "sans fragiliser aucun argument" not in verdict, (
            "#3153: 'no argument is weakened' is false when the graph leaves "
            f"three poles in conflict; got {verdict!r}"
        )
        assert "acceptés par crédulité" in detail, (
            "#3153: an undecided argument an accepted extension contains is "
            f"credulously accepted — the reading must say so; got {detail!r}"
        )
        for opaque in ("arg_1", "arg_3", "arg_6", "arg_4"):
            assert opaque not in verdict and opaque not in detail, (
                "#1908/#3153: the Dung reading counts, it never names — "
                f"{opaque} leaked into {verdict!r} / {detail!r}"
            )


class TestAct3ReadsTheLabelling:
    def test_weak_points_and_p1_name_only_the_out_argument(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            build_act3_evidence,
            build_act3_prompt,
        )

        ev = build_act3_evidence(_doc_b_like_state())
        # DoD render leg, structural half: the PROMPT the writer receives is
        # rebuilt here with zero LLM calls and zero network (the prompt is the
        # whole reader-facing contract — what the model may then say). The
        # claim inventory lists every id, so the claim is scoped to the P1
        # statement, which is what carries « the most solid formal verdict ».
        prompt = build_act3_prompt(ev)
        assert isinstance(prompt, str) and prompt
        assert ev.salience is not None and ev.salience.ranked
        p1_statement = ev.salience.ranked[0].statement
        assert "arg_4" in p1_statement, (
            "#3153: P1 must carry the out argument — it is the only genuine "
            f"formal verdict on this frame; got {p1_statement!r}"
        )
        for undecided in ("arg_1", "arg_3", "arg_6"):
            assert undecided not in p1_statement, (
                f"#3153: {undecided} is undecided, not rejected — it must not "
                f"reach P1 « most solid formal verdict »; got {p1_statement!r}"
            )
        dung_targets = {
            wp.target_arg_id for wp in ev.weak_points if wp.source == "dung"
        }
        assert dung_targets == {"arg_4"}, (
            "#3153: Act III turned the stand-off into formal rejections; the "
            f"Dung weak points must name arg_4 alone, got {sorted(dung_targets)!r}"
        )
        # P1 = the decisif-weighted head of the ranking (salience contract).
        assert ev.salience is not None and ev.salience.ranked, (
            "#3153: the salience ranking must still surface the formal "
            "verdict on the out argument"
        )
        p1 = ev.salience.ranked[0]
        assert "arg_4" in p1.cites, f"#3153: P1 must cite arg_4, got {p1.cites!r}"
        for undecided in ("arg_1", "arg_3", "arg_6"):
            assert undecided not in p1.cites, (
                "#3153: the stand-off argument "
                f"{undecided} sits in P1 « most solid formal verdict » — "
                "undecided is not rejected"
            )
