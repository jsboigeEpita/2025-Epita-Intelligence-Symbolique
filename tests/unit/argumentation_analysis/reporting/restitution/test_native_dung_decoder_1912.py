# -*- coding: utf-8 -*-
"""#1912 guard: sidecar formalisms must never fabricate native Dung rejections.

Non-Dung formalisms (ABA/ADF/SetAF/weighted/social/…) share the
``state.dung_frameworks`` container with native Dung verification entries.
Both Act II and Act III used to iterate **every** entry and decode its
extension shape with a generic resolver: a sidecar shape the resolver did
not understand collapsed to ``accepted = ∅`` and every sidecar argument was
reported **rejected by Dung** — 221 false rejections measured on the real
corpus (#1894 forensic), invalidating the whole Dung axis of the verdict.

The guard pins, through the acts' public builders only (no import of the
decoder module — the pre-fix tree must run this file and FAIL on
assertions, not on an ImportError):

- the issue's born-red witness (zero-attack native preferred + ABA sidecar
  projecting the same arg ids) produces ZERO Dung rejections in Act II
  (beat, trace, formal finding) and Act III (weak points);
- no combination of ABA/SetAF/weighted/social sidecars can change the
  native Dung accepted/rejected counts (regression witness included: a
  genuinely attacked native argument stays reported rejected);
- an unknown or malformed **native** extension shape is non-concluable —
  it contributes no rejection and Act II says so; never "accepted = ∅"
  (all rejected), never a guessed set;
- Act II and Act III share ONE decoder: no local ``_dung_rejected_by_arg``
  survives in either module, and both import the same function object.

Privacy HARD: synthetic opaque arguments only (arg_N, asm_N) — the real
witness stays local/gitignored.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    _collect_dung_trace,
    _collect_formal_findings,
    build_act2_evidence,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
)


def _state(**fields: Any) -> SimpleNamespace:
    """Lightweight state stub carrying the fields both acts read."""
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _witness_state() -> SimpleNamespace:
    """The issue's born-red witness.

    ``verification_preferred``: 2 args, 0 attacks, both accepted — the honest
    native verdict is ``2 accepted / 0 rejected``. ``aba_preferred`` projects
    the SAME arg ids with an ABA-shaped extension listing only arg_1: the old
    generic resolver read it as a native acceptance set and rejected arg_2.
    """
    return _state(
        identified_arguments={
            "arg_1": "Thèse synthétique un.",
            "arg_2": "Thèse synthétique deux.",
        },
        dung_frameworks={
            "fw_native": {
                "name": "verification_preferred",
                "arguments": ["arg_1", "arg_2"],
                "attacks": [],
                "extensions": {"all_members": ["arg_1", "arg_2"]},
            },
            "fw_aba": {
                "name": "aba_preferred",
                "arguments": ["arg_1", "arg_2"],
                "attacks": [],
                "extensions": {"aba_extensions": [["arg_1"]]},
            },
        },
    )


def _regression_state() -> SimpleNamespace:
    """A genuine native Dung rejection: arg_2 attacks arg_1, extension keeps
    arg_2 only — arg_1 is REALLY rejected under preferred semantics. A fix
    that zeroed Dung rejections everywhere would pass the witness and break
    the axis for real."""
    return _state(
        identified_arguments={
            "arg_1": "Thèse attaquée.",
            "arg_2": "Attaque tenable.",
        },
        dung_frameworks={
            "fw_native": {
                "name": "verification_preferred",
                "arguments": ["arg_1", "arg_2"],
                "attacks": [["arg_2", "arg_1"]],
                "extensions": {"all_members": ["arg_2"]},
            }
        },
    )


def _all_sidecars_state() -> SimpleNamespace:
    """Native rejection + every sidecar shape projecting decoy verdicts on
    the same arg ids. The native-only truth: arg_1 rejected (preferred),
    nothing else — no sidecar may add, clear or relabel a Dung rejection."""
    return _state(
        identified_arguments={
            "arg_1": "Thèse un.",
            "arg_2": "Thèse deux.",
            "arg_3": "Thèse trois.",
        },
        dung_frameworks={
            "fw_native": {
                "name": "verification_preferred",
                "arguments": ["arg_1", "arg_2"],
                "attacks": [["arg_2", "arg_1"]],
                "extensions": {"all_members": ["arg_2"]},
            },
            "fw_aba": {
                "name": "aba_preferred",
                "arguments": ["arg_1", "arg_2"],
                "attacks": [],
                # decoy: would "accept" arg_1 under the old generic union
                "extensions": {"aba_extensions": [["arg_1", "arg_2"]]},
            },
            "fw_setaf": {
                "name": "setaf_grounded",
                "arguments": ["arg_3"],
                "attacks": [],
                # decoy: empty extensions list -> old resolver: accepted=∅
                "extensions": {"setaf_extensions": []},
            },
            "fw_weighted": {
                "name": "weighted_grounded",
                "arguments": ["arg_3"],
                "attacks": [],
                # decoy: accepts arg_3 — not a Dung acceptance
                "extensions": {"weighted_extensions": [["arg_3"]]},
            },
            "fw_social": {
                "name": "social_af",
                "arguments": ["arg_1", "arg_3"],
                "attacks": [],
                # decoy: scores dict (non-list value) + empty ranking
                "extensions": {
                    "social_ranking": [],
                    "social_scores": {"arg_1": 3.0, "arg_3": 1.0},
                },
            },
        },
    )


# ---------------------------------------------------------------------------
# 1. Born-red witness — the issue's exact scenario
# ---------------------------------------------------------------------------


class TestWitnessZeroAttackPlusAba:
    def test_act2_trace_reports_zero_rejections(self):
        trace = _collect_dung_trace(_witness_state())
        assert trace.available is True
        assert sorted(trace.accepted_members) == ["arg_1", "arg_2"], (
            "#1912: the zero-attack native preferred framework accepts both "
            "arguments — anything else reads a sidecar as native Dung"
        )
        assert trace.rejected_args == {}, (
            "#1912: the ABA sidecar's extension shape leaked into the native "
            "trace as Dung rejections — a zero-attack framework rejects "
            f"nothing, got {trace.rejected_args!r}"
        )

    def test_act2_no_formal_finding_claims_a_rejection(self):
        findings = _collect_formal_findings(_witness_state())
        for f in findings:
            assert "rejeté" not in f.verdict, (
                "#1912: Act II rendered a Dung rejection for a zero-attack "
                f"framework — the sidecar contamination, verdict was {f.verdict!r}"
            )

    def test_act2_beats_carry_no_dung_rejection(self):
        ev = build_act2_evidence(_witness_state())
        for mvt in ev.movements:
            for a in mvt.arguments:
                assert a.dung_rejected is None, (
                    "#1912: argument beat carries a Dung rejection fabricated "
                    f"by the ABA sidecar: {a.arg_id} -> {a.dung_rejected!r}"
                )

    def test_act3_no_dung_weak_point(self):
        ev = build_act3_evidence(_witness_state())
        dung_wps = [wp for wp in ev.weak_points if wp.source == "dung"]
        assert dung_wps == [], (
            "#1912: Act III turned the sidecar's false rejection into a "
            "structuring weak point — the reader would target a claim Dung "
            "never rejected"
        )


# ---------------------------------------------------------------------------
# 2. No sidecar combination changes native counts (all four shapes)
# ---------------------------------------------------------------------------


class TestSidecarCombinationsPowerless:
    def test_act2_trace_counts_are_native_only(self):
        trace = _collect_dung_trace(_all_sidecars_state())
        assert trace.rejected_args == {"arg_1": "preferred"}, (
            "#1912: sidecar entries changed the native Dung counts — "
            f"expected exactly arg_1 rejected (preferred), got {trace.rejected_args!r}"
        )

    def test_act3_weak_points_are_native_only(self):
        ev = build_act3_evidence(_all_sidecars_state())
        dung_targets = {
            wp.target_arg_id for wp in ev.weak_points if wp.source == "dung"
        }
        assert dung_targets == {"arg_1"}, (
            "#1912: sidecar entries added or cleared Act III weak points — "
            f"expected exactly arg_1, got {sorted(dung_targets)!r}"
        )


# ---------------------------------------------------------------------------
# 3. Regression witness — genuine native rejections survive the fix
# ---------------------------------------------------------------------------


class TestGenuineNativeRejectionSurvives:
    def test_act2_beat_and_trace_keep_the_real_rejection(self):
        state = _regression_state()
        trace = _collect_dung_trace(state)
        assert trace.rejected_args == {"arg_1": "preferred"}
        ev = build_act2_evidence(state)
        beats = {a.arg_id: a.dung_rejected for m in ev.movements for a in m.arguments}
        assert beats["arg_1"] == "preferred", (
            "#1912 anti-pendule: a genuinely attacked native argument MUST "
            "stay reported rejected — zeroing Dung rejections everywhere "
            "would pass the witness without repairing the axis"
        )

    def test_act3_keeps_the_real_weak_point(self):
        ev = build_act3_evidence(_regression_state())
        dung_targets = {
            wp.target_arg_id for wp in ev.weak_points if wp.source == "dung"
        }
        assert dung_targets == {"arg_1"}


# ---------------------------------------------------------------------------
# 4. Unknown native extension shape -> non-concluable, never "all rejected"
# ---------------------------------------------------------------------------


class TestUnknownNativeShapeNonConcluable:
    def test_malformed_shape_yields_no_rejection_and_says_so(self):
        state = _state(
            identified_arguments={"arg_1": "Thèse unique."},
            dung_frameworks={
                "fw_1": {
                    "name": "verification_preferred",
                    "arguments": ["arg_1"],
                    "attacks": [],
                    # unknown shape: a dict value the decoder cannot read
                    "extensions": {"bizarre": {"not": "a list"}},
                }
            },
        )
        trace = _collect_dung_trace(state)
        assert trace.rejected_args == {}, (
            "#1912: an undecodable native extension collapsed to "
            "accepted=∅ and rejected everything — must be non-concluable"
        )
        assert trace.non_concluable is True, (
            "#1912: the trace must SAY the extension is non-concluable — "
            "silence is indistinguishable from 'nothing rejected'"
        )
        findings = _collect_formal_findings(state)
        dung = [f for f in findings if f.kind == "dung"]
        assert dung, "#1912: a non-concluable native framework must surface"
        assert (
            "non conclu" in dung[0].verdict.lower()
        ), f"#1912: the finding must state non-concluable, got {dung[0].verdict!r}"

    def test_empty_extension_dict_is_non_concluable_not_all_rejected(self):
        # add_dung_framework(extensions=None) stores {} — no extension info
        # at all must not become "every argument rejected".
        state = _state(
            identified_arguments={"arg_1": "Thèse unique."},
            dung_frameworks={
                "fw_1": {
                    "name": "verification_preferred",
                    "arguments": ["arg_1"],
                    "attacks": [],
                    "extensions": {},
                }
            },
        )
        trace = _collect_dung_trace(state)
        assert trace.rejected_args == {}
        assert trace.non_concluable is True

    def test_decodable_empty_extension_still_rejects_genuinely(self):
        # all_members=[] IS decodable: the solver accepted nothing — that is
        # a real verdict, not an unknown shape. It must keep rejecting.
        state = _state(
            identified_arguments={"arg_1": "Thèse unique."},
            dung_frameworks={
                "fw_1": {
                    "name": "verification_grounded",
                    "arguments": ["arg_1"],
                    "attacks": [["arg_1", "arg_1"]],
                    "extensions": {"all_members": []},
                }
            },
        )
        trace = _collect_dung_trace(state)
        assert trace.non_concluable is False
        assert trace.rejected_args == {"arg_1": "grounded"}, (
            "#1912: a decodable empty extension is a genuine empty "
            "acceptance — collapsing it to non-concluable would hide real "
            "rejections behind honesty theater"
        )


# ---------------------------------------------------------------------------
# 4b. Rework R868 (#1916 review): a malformed MEMBER inside a decodable
#     shape is non-concluable — the strict rule holds at EVERY depth, and
#     the primary trace never mixes native semantics.
# ---------------------------------------------------------------------------


class TestMalformedMemberIsNonConcluable:
    """An invalid member (non-string) inside a KNOWN shape must decode to
    None — same rule as an unknown shape. Silently filtering it turns bad
    data into a plausible partial verdict (R868: measured
    ``{"all_members": ["arg_1", 7]}`` -> ``{arg_1}`` -> arg_2 fabricated
    rejected). One test per decoder site, the invalid member INSIDE a
    decodable shape."""

    def test_all_members_with_non_string_member_is_none(self):
        # Site 1 — the canonical all_members list.
        from argumentation_analysis.reporting.restitution.native_dung import (
            decode_accepted_members,
        )

        assert decode_accepted_members({"all_members": ["arg_1", 7]}) is None, (
            "#1912 rework: a non-string member inside all_members was "
            "silently filtered into a partial verdict — the shape carries "
            "invalid data, the only honest answer is non-concluable"
        )

    def test_multi_extension_dict_with_non_string_member_is_none(self):
        # Site 2 — the multi-extension dict path (union of list values).
        from argumentation_analysis.reporting.restitution.native_dung import (
            decode_accepted_members,
        )

        assert decode_accepted_members({"e": [["arg_1", 7]]}) is None, (
            "#1912 rework: a non-string member inside a dict extension list "
            "was silently filtered — depth-1 members must meet the same "
            "strict rule as depth-0"
        )

    def test_bare_list_with_non_string_member_is_none(self):
        # Site 3 — the bare list path (already strict pre-rework; pinned so
        # the three paths cannot diverge again).
        from argumentation_analysis.reporting.restitution.native_dung import (
            decode_accepted_members,
        )

        assert decode_accepted_members(["arg_1", 7]) is None, (
            "#1912 rework: the bare-list path is the reference strict "
            "behaviour — the other two paths must match it, not diverge"
        )


class TestPrimaryTraceSingleSemantics:
    """The primary trace's accepted AND rejected members must come from the
    SAME framework. Pre-rework, accepted came from the primary (preferred)
    while rejected came from the aggregate of ALL verification_* — measured:
    semantics=preferred, accepted=[arg_1, arg_2], rejected={arg_2: grounded},
    the same argument accepted AND rejected with zero sidecars (R868)."""

    def test_no_argument_is_simultaneously_accepted_and_rejected(self):
        state = _state(
            identified_arguments={
                "arg_1": "Thèse un.",
                "arg_2": "Thèse deux.",
            },
            dung_frameworks={
                "fw_pref": {
                    "name": "verification_preferred",
                    "arguments": ["arg_1", "arg_2"],
                    "attacks": [],
                    "extensions": {"all_members": ["arg_1", "arg_2"]},
                },
                "fw_grd": {
                    "name": "verification_grounded",
                    "arguments": ["arg_1", "arg_2"],
                    "attacks": [["arg_2", "arg_1"]],
                    "extensions": {"all_members": ["arg_1"]},
                },
            },
        )
        trace = _collect_dung_trace(state)
        assert trace.available is True
        assert trace.semantics_label == "preferred"
        assert sorted(trace.accepted_members) == ["arg_1", "arg_2"]
        assert trace.rejected_args == {}, (
            "#1912 rework: the trace announces preferred and decodes its "
            "accepted members from the preferred framework, but its rejected "
            "args came from the aggregate of ALL verification_* — arg_2 was "
            "simultaneously accepted (preferred) and rejected (grounded). "
            "A trace with one semantics label must carry one framework's "
            f"verdict; got {trace.rejected_args!r}"
        )


# ---------------------------------------------------------------------------
# 5. One decoder — the duplicated local resolvers are gone
# ---------------------------------------------------------------------------


class TestSingleDecoder:
    def test_no_local_resolver_survives_in_either_act(self):
        import argumentation_analysis.reporting.restitution.act2_narrative_plugin as a2
        import argumentation_analysis.reporting.restitution.act3_conclusion_plugin as a3

        assert not hasattr(a2, "_dung_rejected_by_arg"), (
            "#1912: Act II still carries its local Dung resolver — the DoD "
            "requires delegation to the single shared decoder"
        )
        assert not hasattr(a3, "_dung_rejected_by_arg"), (
            "#1912: Act III still carries the duplicated local resolver "
            "(the 'kept local' comment marked the debt) — must be delegated"
        )

    def test_both_acts_import_the_same_decoder_object(self):
        import argumentation_analysis.reporting.restitution.act2_narrative_plugin as a2
        import argumentation_analysis.reporting.restitution.act3_conclusion_plugin as a3
        from argumentation_analysis.reporting.restitution import native_dung

        a2_fn = getattr(a2, "decode_native_dung", None)
        a3_fn = getattr(a3, "decode_native_dung", None)
        assert a2_fn is not None and a3_fn is not None, (
            "#1912: both acts must re-export the shared decoder for " "traceability"
        )
        assert (
            a2_fn is native_dung.decode_native_dung
        ), "#1912: Act II's decoder is not the shared module's function"
        assert (
            a3_fn is native_dung.decode_native_dung
        ), "#1912: Act III's decoder is not the shared module's function"

    def test_decoder_skips_every_known_sidecar_name(self):
        from argumentation_analysis.reporting.restitution import native_dung

        for sidecar_name in (
            "aba_preferred",
            "setaf_grounded",
            "weighted_grounded",
            "social_af",
            "adf_grounded",
            "eaf_grounded",
            "delp_grounded",
        ):
            fw = {
                "name": sidecar_name,
                "arguments": ["arg_1"],
                "attacks": [],
                "extensions": {},
            }
            assert not native_dung.is_native_dung_framework(
                fw
            ), f"#1912: {sidecar_name} must not be native Dung evidence"
        assert native_dung.is_native_dung_framework({"name": "verification_preferred"})
