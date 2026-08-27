# -*- coding: utf-8 -*-
"""#1912 (third site): the synthesis plugin's Dung rejections are native-only.

The narrative synthesis plugin carried the THIRD copy of the generic Dung
resolver (``_dung_rejected_args``, flagged in PR #1916): it iterated every
``state.dung_frameworks`` entry and decoded its extension shape with a
lenient union — a sidecar shape (ABA/SetAF/weighted/social, each with its
own extension key) either collapsed to ``accepted = ∅`` (every sidecar
argument falsely rejected) or was read as native acceptance. Those false
rejections fed ``compute_argument_convergence`` as "rejet Dung" signals,
contaminating the convergence verdict the same way Acts II/III were
contaminated (#1894: 221 false rejections on the real corpus).

The guard pins, through the plugin's public surface (convergence signals)
plus module-shape checks that fail on assertions, not on ImportError:

- the #1912 witness (zero-attack native preferred + ABA sidecar projecting
  the same arg ids) produces ZERO "rejet Dung" convergence signals;
- no combination of ABA/SetAF/weighted/social sidecars can add, clear or
  relabel a native rejection (all four shapes projecting decoys);
- a genuinely attacked native argument KEEPS its "rejet Dung" signal (the
  axis is repaired, not zeroed) and free-text labels still resolve to
  canonical arg ids (track RR behavior preserved);
- the generic local resolver is GONE and the module delegates to the same
  shared decoder object the two acts use.

Privacy HARD: synthetic opaque arguments only (arg_N, asm_N).
"""

from __future__ import annotations

import types
from typing import Any

from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    compute_argument_convergence,
)


def _state(**fields: Any) -> types.SimpleNamespace:
    ns = types.SimpleNamespace()
    ns.identified_arguments = fields.get("identified_arguments", {})
    ns.dung_frameworks = fields.get("dung_frameworks", {})
    ns.identified_fallacies = fields.get("identified_fallacies", {})
    ns.argument_quality_scores = fields.get("argument_quality_scores", {})
    ns.counter_arguments = fields.get("counter_arguments", [])
    ns.jtms_beliefs = fields.get("jtms_beliefs", {})
    return ns


def _dung_signal_args(state: Any) -> set:
    """arg_ids carrying a "rejet Dung" convergence signal."""
    result = compute_argument_convergence(state)
    return {
        arg_id
        for arg_id, data in result.items()
        if any(m == "rejet Dung" for m, _ in data.get("signals", []))
    }


def _witness_state() -> types.SimpleNamespace:
    """Zero-attack native preferred (both accepted) + ABA sidecar projecting
    the same arg ids — the honest verdict is NO Dung rejection at all."""
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


def _all_sidecars_state() -> types.SimpleNamespace:
    """Native rejection (arg_1) + every sidecar shape projecting decoys on
    the same arg ids. Native-only truth: exactly arg_1 rejected."""
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
                "extensions": {"aba_extensions": [["arg_1", "arg_2"]]},
            },
            "fw_setaf": {
                "name": "setaf_grounded",
                "arguments": ["arg_3"],
                "attacks": [],
                "extensions": {"setaf_extensions": []},
            },
            "fw_weighted": {
                "name": "weighted_grounded",
                "arguments": ["arg_3"],
                "attacks": [],
                "extensions": {"weighted_extensions": [["arg_3"]]},
            },
            "fw_social": {
                "name": "social_af",
                "arguments": ["arg_1", "arg_3"],
                "attacks": [],
                "extensions": {
                    "social_ranking": [],
                    "social_scores": {"arg_1": 3.0, "arg_3": 1.0},
                },
            },
        },
    )


def _regression_state() -> types.SimpleNamespace:
    """A genuine native rejection: arg_2 attacks arg_1 — arg_1 is REALLY
    rejected under preferred semantics."""
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


# ---------------------------------------------------------------------------
# 1. Born-red witness — the issue's exact scenario, plugin-side
# ---------------------------------------------------------------------------


class TestWitnessZeroAttackPlusAba:
    def test_no_dung_signal_for_zero_attack_framework(self):
        signals = _dung_signal_args(_witness_state())
        assert signals == set(), (
            "#1912 third site: the ABA sidecar's extension shape leaked into "
            "the synthesis convergence as a fabricated 'rejet Dung' signal — "
            "a zero-attack framework rejects nothing, got "
            f"{sorted(signals)!r}"
        )


# ---------------------------------------------------------------------------
# 2. No sidecar combination changes the native convergence verdict
# ---------------------------------------------------------------------------


class TestSidecarCombinationsPowerless:
    def test_dung_signal_is_native_only(self):
        signals = _dung_signal_args(_all_sidecars_state())
        assert signals == {"arg_1"}, (
            "#1912 third site: sidecar entries added or cleared 'rejet Dung' "
            f"convergence signals — expected exactly arg_1, got {sorted(signals)!r}"
        )


# ---------------------------------------------------------------------------
# 3. Regression — the axis is repaired, not zeroed
# ---------------------------------------------------------------------------


class TestGenuineNativeRejectionSurvives:
    def test_attacked_native_argument_keeps_its_signal(self):
        signals = _dung_signal_args(_regression_state())
        assert signals == {"arg_1"}, (
            "#1912 anti-pendule: a genuinely attacked native argument MUST "
            "keep its 'rejet Dung' signal — zeroing the axis would pass the "
            "witness without repairing it"
        )

    def test_free_text_labels_still_resolve_to_canonical_ids(self):
        # Track RR behavior: Dung frameworks built with free-text labels must
        # still map back to canonical arg ids so the signal matches.
        text_a1 = "The policy increases unemployment and harms workers"
        text_a2 = "Renewable energy is the future of power generation"
        state = _state(
            identified_arguments={"arg_1": text_a1, "arg_2": text_a2},
            dung_frameworks={
                "fw1": {
                    "name": "verification_grounded",
                    "arguments": [text_a1, text_a2],
                    "attacks": [[text_a2, text_a1]],
                    "semantics": "grounded",
                    "extensions": {"all_members": [text_a2]},
                }
            },
        )
        signals = _dung_signal_args(state)
        assert signals == {"arg_1"}, (
            "track RR regression: free-text Dung labels must resolve back to "
            f"canonical arg ids, got {sorted(signals)!r}"
        )


# ---------------------------------------------------------------------------
# 4. One decoder — the third local resolver is gone
# ---------------------------------------------------------------------------


class TestSingleDecoder:
    def test_no_local_resolver_survives(self):
        import argumentation_analysis.plugins.narrative_synthesis_plugin as nsp

        assert not hasattr(nsp, "_dung_rejected_args"), (
            "#1912 third site: the generic local resolver still lives in the "
            "synthesis plugin — it must delegate to the shared decoder"
        )

    def test_module_delegates_to_the_shared_decoder_object(self):
        import argumentation_analysis.plugins.narrative_synthesis_plugin as nsp
        from argumentation_analysis.reporting.restitution import native_dung

        fn = getattr(nsp, "decode_native_dung", None)
        assert fn is not None, (
            "#1912 third site: the plugin must re-export the shared decoder "
            "for traceability"
        )
        assert fn is native_dung.decode_native_dung, (
            "#1912 third site: the plugin's decoder is not the shared "
            "module's function"
        )
