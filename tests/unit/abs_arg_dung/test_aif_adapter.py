# tests/unit/abs_arg_dung/test_aif_adapter.py
"""Unit tests for the AIF → Dung adapter.

These tests cover:

1. Pure projection (``aif_attacks_to_dung_af``):
   - the Nixon Diamond via AIF relations
   - the AIF "all-three-kinds" mixed attack pattern
   - duplicate-attack de-duplication
   - implicit-argument auto-registration (mirrors ICCMA parser)
   - unknown-kind rejection
   - self-attack preservation (anti-#1019: silent drops forbidden)

2. Backend verification (``verify_aif_to_dung``):
   - the projection is reachable through ``verify_aif_to_dung``
   - the pure-Python backend always runs and reports an ``available=True``
     ``backend_python`` slot
   - the Tweety backend is either available (and agrees) or honestly
     degraded (no fabricated verdict)
   - disagreements are reported verbatim, never reconciled (I5 / #1502)

3. Sequential-arrival trajectory (``aif_labelling_trajectory``, #1524):
   - one step per arrival, growing prefix
   - attack activation latency (an attack is dormant until BOTH endpoints land)
   - the three dynamics that make the trajectory a non-trivial substrate:
     acceptance, refutation (in -> out), reinstatement (undec -> in)
   - per-step dual-backend verification, disagreements verbatim (I5 / #1502)
   - ``verify=False`` never fabricates agreement (``agree is None``)
   - degraded-honest labelling when no grounded extension is available
   - the final step coincides with the static M1 projection (#1520 continuity)
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from abs_arg_dung.aif_adapter import (
    AIF_KIND_REBUT,
    AIF_KIND_UNDERCUT,
    AIF_KIND_UNDERMINE,
    LABEL_IN,
    LABEL_OUT,
    LABEL_UNDEC,
    AIFAttack,
    _labelling_from_report,
    aif_attacks_to_dung_af,
    aif_label_transitions,
    aif_labelling_trajectory,
    render_aif_trajectory,
    verify_aif_to_dung,
)

# ---------------------------------------------------------------------------
# Pure projection
# ---------------------------------------------------------------------------


def test_nixon_diamond_via_aif_undermines() -> None:
    """A→B→C→A (each via undermine) is the canonical AIF reduction of
    the Nixon Diamond. The projection must produce the three-edge
    cycle and recover the same grounded extension the Dung backend
    would deliver on the flat framework."""
    args = ["arg_A", "arg_B", "arg_C"]
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_B", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_C", "arg_A", AIF_KIND_UNDERMINE),
    ]
    proj_args, proj_atts = aif_attacks_to_dung_af(args, attacks)
    assert proj_args == ["arg_A", "arg_B", "arg_C"]
    assert proj_atts == [
        ("arg_A", "arg_B"),
        ("arg_B", "arg_C"),
        ("arg_C", "arg_A"),
    ]


def test_mixed_aif_kinds_collapse_to_binary() -> None:
    """The three AIF kinds must collapse to the same flat edge in Dung.

    The information loss is structural — the projection preserves the
    *fact* of attack but not the *kind*. Verifies that mixing kinds
    targeting the same pair does not produce duplicate Dung edges.
    """
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT),
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERCUT),
    ]
    _, proj_atts = aif_attacks_to_dung_af(["arg_A", "arg_B"], attacks)
    assert proj_atts == [("arg_A", "arg_B")]


def test_duplicate_aif_attacks_dedup() -> None:
    """Two identical AIF attacks must not produce two Dung edges."""
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT),
        AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT),
    ]
    _, proj_atts = aif_attacks_to_dung_af(["arg_A", "arg_B"], attacks)
    assert proj_atts == [("arg_A", "arg_B")]


def test_implicit_argument_autoregistered() -> None:
    """Arguments appearing only in attack edges must be auto-registered
    (mirrors the ICCMA parser behaviour)."""
    _, proj_atts = aif_attacks_to_dung_af(
        ["arg_A"],
        [AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT)],
    )
    assert proj_atts == [("arg_A", "arg_B")]


def test_unknown_aif_kind_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown AIF attack kind"):
        aif_attacks_to_dung_af(
            ["arg_A", "arg_B"],
            [AIFAttack("arg_A", "arg_B", "doxelclash")],
        )


def test_self_attack_preserved() -> None:
    """Self-attacks are semantically meaningful in Dung (an argument
    that attacks itself is in no admissible set). They must NOT be
    silently dropped — silent drops are a classic anti-#1019 trap."""
    attacks = [AIFAttack("arg_A", "arg_A", AIF_KIND_REBUT)]
    _, proj_atts = aif_attacks_to_dung_af(["arg_A"], attacks)
    assert proj_atts == [("arg_A", "arg_A")]


# ---------------------------------------------------------------------------
# Backend verification
# ---------------------------------------------------------------------------


def test_verify_aif_to_dung_nixon_returns_python_report() -> None:
    """``verify_aif_to_dung`` must run the pure-Python backend and
    expose its report. The Tweety slot is either populated (and agrees)
    or empty (honest degradation). Never a fabricated verdict."""
    args = ["arg_A", "arg_B", "arg_C"]
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_B", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_C", "arg_A", AIF_KIND_UNDERMINE),
    ]
    summary = verify_aif_to_dung(args, attacks)

    py = summary["backend_python"]
    assert py["backend"] == "python"
    assert py["available"] is True
    assert "grounded" in py["extensions"]

    # Grounded extension of the Nixon Diamond is empty (mutual attack
    # cycle, no argument is acceptable). Cross-check with the documented
    # Dung semantics.
    assert py["extensions"]["grounded"] == [[]]

    # ``agree`` is either True (Tweety ran + agreed) or None (Tweety
    # unavailable / JVM not initialised). It must NEVER be False-with-fake
    # agreement: if Tweety is unavailable the comparison is indeterminate.
    assert summary["agree"] in (True, None)
    if summary["agree"] is True:
        assert summary["disagreements"] == []


def test_verify_aif_to_dung_empty_attack_set() -> None:
    """Empty AIF attack list with two isolated arguments: every argument
    is acceptable, grounded = full set."""
    args = ["arg_A", "arg_B"]
    summary = verify_aif_to_dung(args, [])

    py = summary["backend_python"]
    assert sorted(py["extensions"]["grounded"][0]) == ["arg_A", "arg_B"]


def test_verify_aif_to_dung_reports_disagreements_verbatim() -> None:
    """If the two backends ever disagree, the disagreement strings
    must be returned to the caller — never silently reconciled.
    I5 / #1502 invariant."""
    args = ["arg_A", "arg_B", "arg_C", "arg_D"]
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT),
        AIFAttack("arg_C", "arg_B", AIF_KIND_REBUT),
        AIFAttack("arg_D", "arg_A", AIF_KIND_REBUT),
    ]
    summary = verify_aif_to_dung(args, attacks)
    # ``disagreements`` is always a list — empty if they agree, populated
    # if they diverge.
    assert isinstance(summary["disagreements"], list)
    if summary["agree"] is False:
        # Disagreements must surface a human-readable hint per divergent
        # semantic.
        assert len(summary["disagreements"]) >= 1
        for d in summary["disagreements"]:
            assert ":" in d
            assert "python=" in d and "tweety=" in d


# ---------------------------------------------------------------------------
# Sequential-arrival trajectory (#1524)
# ---------------------------------------------------------------------------


def _dynamics_exemplar() -> tuple[list[str], list[AIFAttack]]:
    """A discourse exhibiting all three labelling dynamics, opaque ids only.

    * ``arg_A`` opens unattacked and is accepted.
    * ``arg_B`` / ``arg_C`` form a mutual-attack 2-cycle — undecided together.
    * ``arg_D`` lands late and rebuts ``arg_A`` (refutation: in -> out).
    * ``arg_E`` lands last, unattacked, and undercuts ``arg_B`` — which
      reinstates ``arg_C`` (undec -> in).
    """
    arrival = ["arg_A", "arg_B", "arg_C", "arg_D", "arg_E"]
    attacks = [
        AIFAttack("arg_D", "arg_A", AIF_KIND_REBUT),
        AIFAttack("arg_B", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_C", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_E", "arg_B", AIF_KIND_UNDERCUT),
    ]
    return arrival, attacks


def test_trajectory_has_one_step_per_arrival() -> None:
    """The trajectory is indexed by arrivals: step k holds exactly the first
    k arguments of the stream, in order."""
    arrival, attacks = _dynamics_exemplar()
    trajectory = aif_labelling_trajectory(arrival, attacks, verify=False)

    assert [s.step for s in trajectory] == [1, 2, 3, 4, 5]
    for k, step in enumerate(trajectory, start=1):
        assert step.new_argument == arrival[k - 1]
        assert step.arrived == tuple(arrival[:k])


def test_trajectory_attack_activation_is_deferred() -> None:
    """An attack declared up front stays dormant until BOTH of its endpoints
    have arrived — that latency is what produces the dynamics."""
    arrival, attacks = _dynamics_exemplar()
    trajectory = aif_labelling_trajectory(arrival, attacks, verify=False)

    # Step 1 (only arg_A present): nothing can be active yet.
    assert trajectory[0].activated_attacks == ()
    assert trajectory[0].framework == (["arg_A"], [])

    # The 2-cycle activates only when its second half (arg_C) lands at step 3.
    assert trajectory[1].activated_attacks == ()
    assert set(trajectory[2].activated_attacks) == {
        AIFAttack("arg_B", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_C", "arg_B", AIF_KIND_UNDERMINE),
    }

    # arg_D -> arg_A activates exactly when arg_D lands (step 4).
    assert trajectory[3].activated_attacks == (
        AIFAttack("arg_D", "arg_A", AIF_KIND_REBUT),
    )

    # Every declared attack is activated exactly once across the trajectory.
    all_activated = [a for s in trajectory for a in s.activated_attacks]
    assert sorted(all_activated) == sorted(attacks)


def test_trajectory_exhibits_refutation_and_reinstatement() -> None:
    """The substrate claim, made falsifiable: statuses genuinely evolve.

    ``arg_A`` is accepted and later refuted; ``arg_C`` is undecided and later
    reinstated. A trajectory where nothing ever changes would not be a
    substrate at all — this test is what makes the claim refutable.
    """
    arrival, attacks = _dynamics_exemplar()
    trajectory = aif_labelling_trajectory(arrival, attacks, verify=False)
    transitions = aif_label_transitions(trajectory)

    # Acceptance then refutation.
    assert transitions["arg_A"] == (
        LABEL_IN,
        LABEL_IN,
        LABEL_IN,
        LABEL_OUT,
        LABEL_OUT,
    )
    # Undecided (cycle) then reinstated once its attacker is undercut.
    assert transitions["arg_C"] == (LABEL_UNDEC, LABEL_UNDEC, LABEL_IN)
    # The late unattacked arrival is accepted immediately.
    assert transitions["arg_E"] == (LABEL_IN,)


def test_trajectory_depends_on_arrival_order_but_endpoint_does_not() -> None:
    """The substrate claim in one assertion.

    Dung semantics are order-blind: the same framework yields the same final
    labelling whatever order its arguments were uttered in. The *trajectory* is
    not order-blind. What the trajectory carries is exactly the information the
    static labelling discards — if both were equal, M2 would add nothing over
    M1 (#1520) and this substrate would be redundant.
    """
    _, attacks = _dynamics_exemplar()
    attacker_last = ["arg_A", "arg_B", "arg_C", "arg_E", "arg_D"]
    attacker_first = ["arg_D", "arg_A", "arg_B", "arg_C", "arg_E"]

    traj_last = aif_labelling_trajectory(attacker_last, attacks, verify=False)
    traj_first = aif_labelling_trajectory(attacker_first, attacks, verify=False)

    final_last = traj_last[-1].labelling
    final_first = traj_first[-1].labelling
    assert final_last is not None and final_first is not None
    assert final_last.as_map() == final_first.as_map()  # order-blind endpoint

    # ...but the paths differ: the thesis is accepted for a while in one
    # ordering and rejected from its very first appearance in the other.
    transitions_last = aif_label_transitions(traj_last)
    transitions_first = aif_label_transitions(traj_first)
    assert transitions_last != transitions_first
    assert transitions_last["arg_A"][0] == LABEL_IN
    assert transitions_first["arg_A"][0] == LABEL_OUT


def test_trajectory_labelling_partition_is_total_and_disjoint() -> None:
    """At every step the labelling partitions exactly the arrived arguments —
    no argument missing, none in two classes at once."""
    arrival, attacks = _dynamics_exemplar()
    trajectory = aif_labelling_trajectory(arrival, attacks, verify=False)

    for step in trajectory:
        labelling = step.labelling
        assert labelling is not None
        in_a, out_a, undec_a = (
            labelling.in_args,
            labelling.out_args,
            labelling.undec_args,
        )
        assert in_a | out_a | undec_a == set(step.arrived)
        assert not (in_a & out_a) and not (in_a & undec_a) and not (out_a & undec_a)
        # Label vocabulary is the one shared with the #1509 substrate.
        assert set(labelling.as_map().values()) <= {LABEL_IN, LABEL_OUT, LABEL_UNDEC}


def test_trajectory_final_step_matches_static_projection() -> None:
    """The trajectory must land exactly where M1 (#1520) starts: its last step
    is the static projection of the whole discourse."""
    arrival, attacks = _dynamics_exemplar()
    trajectory = aif_labelling_trajectory(arrival, attacks, verify=False)

    assert trajectory[-1].framework == aif_attacks_to_dung_af(arrival, attacks)


def test_trajectory_verifies_each_step_against_both_backends() -> None:
    """Every step carries its own dual-backend verification (#1502 contract).

    ``agree`` is ``True`` (both ran and matched) or ``None`` (Tweety
    unavailable — indeterminate). It is never ``False`` with an empty
    disagreement list, and disagreements are never reconciled away.
    """
    arrival, attacks = _dynamics_exemplar()
    trajectory = aif_labelling_trajectory(arrival, attacks, verify=True)

    for step in trajectory:
        assert step.verification is not None
        assert step.verification["backend_python"]["available"] is True
        assert step.agree in (True, False, None)
        if step.agree is True:
            assert step.disagreements == ()
        if step.agree is False:
            # A disagreement must be reported verbatim, never silently fixed.
            assert len(step.disagreements) >= 1


def test_trajectory_unverified_never_fabricates_agreement() -> None:
    """``verify=False`` skips the cross-check; it must report indeterminate
    (``agree is None``) rather than a comfortable ``True``."""
    arrival, attacks = _dynamics_exemplar()
    trajectory = aif_labelling_trajectory(arrival, attacks, verify=False)

    for step in trajectory:
        assert step.agree is None
        assert step.disagreements == ()
        assert step.verification is None
        # The labelling is still computed — and still traceable to its source.
        assert step.labelling is not None
        assert step.labelling.source_backend == "backend_python"


def test_trajectory_rejects_duplicate_arrivals() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        aif_labelling_trajectory(["arg_A", "arg_A"], [], verify=False)


def test_trajectory_rejects_attack_endpoint_that_never_arrives() -> None:
    """An attack pointing at an argument outside the stream would be silently
    dropped at every step — exactly the kind of silent loss anti-#1019 bans."""
    with pytest.raises(ValueError, match="never arrive"):
        aif_labelling_trajectory(
            ["arg_A"],
            [AIFAttack("arg_A", "arg_ghost", AIF_KIND_REBUT)],
            verify=False,
        )


def test_trajectory_rejects_unknown_kind_upfront() -> None:
    """A bad kind fails before step 1 rather than halfway through."""
    with pytest.raises(ValueError, match="Unknown AIF attack kind"):
        aif_labelling_trajectory(
            ["arg_A", "arg_B"],
            [AIFAttack("arg_A", "arg_B", "doxelclash")],
            verify=False,
        )


def test_trajectory_preserves_self_attack() -> None:
    """A self-attacking argument is never accepted — the trajectory must show
    it as undecided rather than dropping the edge."""
    trajectory = aif_labelling_trajectory(
        ["arg_A"],
        [AIFAttack("arg_A", "arg_A", AIF_KIND_REBUT)],
        verify=False,
    )
    step = trajectory[0]
    assert step.framework == (["arg_A"], [("arg_A", "arg_A")])
    assert step.labelling is not None
    assert step.labelling.in_args == frozenset()
    assert step.labelling.undec_args == frozenset({"arg_A"})


def test_labelling_is_degraded_honest_without_grounded_extension() -> None:
    """No grounded extension in the backend report => no labelling.

    An unavailable backend must yield ``None``, not an all-undecided labelling
    invented to keep the shape pretty (anti-#1019).
    """
    empty_report: Dict[str, Any] = {
        "backend": "python",
        "available": False,
        "extensions": {},
    }
    assert _labelling_from_report(["arg_A"], [], empty_report, "backend_python") is None


def test_render_trajectory_marks_verification_state() -> None:
    """The rendered table (consumed as-is downstream) must expose the per-step
    verification verdict, not just the labels."""
    arrival, attacks = _dynamics_exemplar()
    rendered = render_aif_trajectory(
        aif_labelling_trajectory(arrival, attacks, verify=False)
    )
    lines = rendered.splitlines()
    assert lines[0].split("|")[-1].strip() == "agree"
    # Unverified steps are marked indeterminate ("?"), never "=".
    for line in lines[2:]:
        assert line.split("|")[-1].strip() == "?"
