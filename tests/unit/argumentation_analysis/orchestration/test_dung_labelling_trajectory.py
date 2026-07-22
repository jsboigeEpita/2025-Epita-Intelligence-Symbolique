"""Unit tests for the Dung labelling trajectory (Track S6-A2 #1506).

JVM/LLM-free: the engine reuses ``abs_arg_dung.backends.compute_grounded`` (pure
Python), so every test runs on synthetic opaque atoms. The tests assert the
trajectory DYNAMICS firsthand (acceptance, refutation in->out, reinstatement
undec->in) — the non-trivial behaviour that makes the trajectory a genuine
strate-6 substrate rather than a flat list.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.orchestration.dung_labelling_trajectory import (
    build_discourse_exemplar,
    label_transitions,
    labelling_from_grounded,
    labelling_trajectory,
    render_trajectory,
)


class TestLabellingFromGrounded:
    def test_single_unattacked_argument_is_in(self) -> None:
        lab = labelling_from_grounded(["a"], [])
        assert lab.in_args == frozenset({"a"})
        assert lab.out_args == frozenset()
        assert lab.undec_args == frozenset()

    def test_chain_grounds_alternating(self) -> None:
        # a -> b -> c: grounded = {a, c}; b is out.
        lab = labelling_from_grounded(["a", "b", "c"], [("a", "b"), ("b", "c")])
        assert lab.in_args == frozenset({"a", "c"})
        assert lab.out_args == frozenset({"b"})
        assert lab.undec_args == frozenset()

    def test_mutual_attack_cycle_is_all_undec(self) -> None:
        # a <-> b: grounded = {}; both undecided (no unattacked seed).
        lab = labelling_from_grounded(["a", "b"], [("a", "b"), ("b", "a")])
        assert lab.in_args == frozenset()
        assert lab.out_args == frozenset()
        assert lab.undec_args == frozenset({"a", "b"})

    def test_unknown_attack_endpoints_ignored(self) -> None:
        # Attacks referencing args not in the set are dropped (defensive).
        lab = labelling_from_grounded(["a"], [("a", "ghost"), ("ghost", "a")])
        assert lab.in_args == frozenset({"a"})

    def test_as_map_covers_every_argument(self) -> None:
        lab = labelling_from_grounded(["a", "b", "c"], [("a", "b")])
        m = lab.as_map()
        assert set(m) == {"a", "b", "c"}
        assert m["a"] == "in"
        assert m["b"] == "out"
        # c is isolated (unattacked) -> trivially acceptable -> in the grounded
        # extension, NOT undecided.
        assert m["c"] == "in"


class TestLabellingTrajectory:
    def test_trajectory_length_equals_arrival_count(self) -> None:
        args = ["a", "b", "c"]
        atts = [("a", "b")]
        traj = labelling_trajectory(args, atts, ["a", "b", "c"])
        assert len(traj) == 3
        assert [s.step for s in traj] == [1, 2, 3]

    def test_refutation_dynamic_in_to_out(self) -> None:
        # Thesis accepted at step 1; refuted (in -> out) when the counter lands.
        args = ["prop_thesis", "prop_counter"]
        atts = [("prop_counter", "prop_thesis")]
        traj = labelling_trajectory(args, atts, ["prop_thesis", "prop_counter"])
        assert traj[0].labelling.in_args == frozenset({"prop_thesis"})
        assert "prop_thesis" in traj[0].labelling.in_args
        # After the counter arrives, the thesis is out (counter in, defends nothing
        # else; thesis attacked by the accepted counter).
        assert traj[1].labelling.in_args == frozenset({"prop_counter"})
        assert traj[1].labelling.out_args == frozenset({"prop_thesis"})

    def test_prefix_only_keeps_arrived_attacks(self) -> None:
        # An attack whose target has not arrived yet must not affect the prefix.
        args = ["a", "b"]
        atts = [("b", "a")]  # b refutes a, but a arrives first.
        traj = labelling_trajectory(args, atts, ["a", "b"])
        # Step 1: only {a}, no attack within prefix -> a in.
        assert traj[0].labelling.in_args == frozenset({"a"})
        # Step 2: b arrives, attacks a; b unattacked -> in, a out.
        assert traj[1].labelling.in_args == frozenset({"b"})
        assert traj[1].labelling.out_args == frozenset({"a"})

    def test_arrival_order_not_a_permutation_raises(self) -> None:
        with pytest.raises(ValueError, match="permutation"):
            labelling_trajectory(["a", "b"], [], ["a", "c"])

    def test_deterministic_repeat(self) -> None:
        args = ["a", "b", "c"]
        atts = [("a", "b"), ("b", "c")]
        t1 = labelling_trajectory(args, atts, ["a", "b", "c"])
        t2 = labelling_trajectory(args, atts, ["a", "b", "c"])
        assert [s.labelling for s in t1] == [s.labelling for s in t2]


class TestLabelTransitions:
    def test_transitions_start_at_arrival(self) -> None:
        traj = labelling_trajectory(["a", "b"], [("b", "a")], ["a", "b"])
        tr = label_transitions(traj)
        # a arrives step1 (in), then out step2 -> (in, out).
        assert tr["a"] == ("in", "out")
        # b arrives step2 (in) -> (in,).
        assert tr["b"] == ("in",)


class TestDiscourseExemplar:
    """The canonical S6-A2 exemplar: acceptance + refutation + reinstatement."""

    def test_exemplar_uses_opaque_ids_no_raw_text(self) -> None:
        ex = build_discourse_exemplar()
        # Privacy HARD: opaque prop_* tokens, never source content.
        for a in ex.arguments:
            assert a.startswith("prop_"), f"non-opaque id leaked: {a!r}"

    def test_exemplar_trajectory_shows_full_dynamics(self) -> None:
        ex = build_discourse_exemplar()
        traj = labelling_trajectory(ex.arguments, ex.attacks, ex.arrival_order)
        tr = label_transitions(traj)

        # Refutation: thesis accepted early, refuted (in -> out) when the
        # counter lands (step 4).
        assert tr["prop_thesis"][0] == "in"  # accepted at arrival
        assert tr["prop_thesis"][-1] == "out"  # refuted by the end

        # Reinstatement: a cycle member is undecided, then reinstated (undec ->
        # in) when the defender lands (step 5).
        assert tr["prop_cycle_b"][0] == "undec"  # undecided on arrival (cycle)
        assert tr["prop_cycle_b"][-1] == "in"  # reinstated by the defender

        # The defender, once landed, is accepted (unattacked seed).
        assert tr["prop_defender"] == ("in",)

    def test_render_trajectory_is_non_empty(self) -> None:
        ex = build_discourse_exemplar()
        traj = labelling_trajectory(ex.arguments, ex.attacks, ex.arrival_order)
        rendered = render_trajectory(traj)
        assert "step" in rendered
        assert rendered.count("\n") >= len(ex.arguments)
