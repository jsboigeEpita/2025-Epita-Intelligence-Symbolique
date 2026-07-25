"""AIF → Dung labelling TRAJECTORY demo (sequential arrival).

M2 #1524 — the sequential-arrival counterpart of :mod:`scripts.aif_dung_demo`
(M1 #1520). Where M1 asks "do both backends agree on *this* framework?", this
demo asks "how does each argument's status **evolve** as the discourse delivers
its arguments one at a time?".

Three scenarios:

1. ``dynamics`` — a discourse exhibiting the three labelling dynamics:
   acceptance, refutation (``in -> out``), reinstatement (``undec -> in``).
2. ``order_matters`` — the *same* argumentation framework delivered in two
   different rhetorical orders. The final labelling is identical (Dung
   semantics do not care about arrival order); the *trajectories* differ. That
   contrast is the substrate: what the trajectory carries is precisely the
   information the static labelling throws away.
3. ``degenerate_cycle`` — a 3-cycle where nothing is ever accepted, the
   negative control: a trajectory that stays flat.

Each step is verified against both Dung backends (#1502): ``=`` both agree,
``!`` they disagree (reported verbatim, never reconciled — I5), ``?``
indeterminate (Tweety/JVM unavailable — honest degradation, not a fake pass).

Usage::

    PYTHONPATH=. python scripts/aif_dung_trajectory_demo.py            # verified
    PYTHONPATH=. python scripts/aif_dung_trajectory_demo.py --no-verify  # fast

Privacy: every example is synthetic with opaque IDs (``arg_A``…). No encrypted
corpus, no raw text, no source names.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Sequence, Tuple

from abs_arg_dung.aif_adapter import (
    AIF_KIND_REBUT,
    AIF_KIND_UNDERCUT,
    AIF_KIND_UNDERMINE,
    AIFAttack,
    AIFTrajectoryStep,
    aif_label_transitions,
    aif_labelling_trajectory,
    render_aif_trajectory,
)

Scenario = Tuple[str, str, List[str], List[AIFAttack]]


def _scn_dynamics() -> Scenario:
    """Acceptance, refutation and reinstatement in a single discourse."""
    arrival = ["arg_A", "arg_B", "arg_C", "arg_D", "arg_E"]
    attacks = [
        AIFAttack("arg_D", "arg_A", AIF_KIND_REBUT),
        AIFAttack("arg_B", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_C", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_E", "arg_B", AIF_KIND_UNDERCUT),
    ]
    return (
        "dynamics",
        "arg_A accepted then refuted; arg_C undecided then reinstated",
        arrival,
        attacks,
    )


def _scn_order_first() -> Scenario:
    """The attacker arrives late — the thesis enjoys a spell of acceptance."""
    _, _, _, attacks = _scn_dynamics()
    return (
        "order_matters/attacker_last",
        "the counter lands at the end: arg_A holds, then falls",
        ["arg_A", "arg_B", "arg_C", "arg_E", "arg_D"],
        attacks,
    )


def _scn_order_second() -> Scenario:
    """The attacker arrives first — the thesis is never accepted at all."""
    _, _, _, attacks = _scn_dynamics()
    return (
        "order_matters/attacker_first",
        "the counter opens: arg_A is out from the moment it is uttered",
        ["arg_D", "arg_A", "arg_B", "arg_C", "arg_E"],
        attacks,
    )


def _scn_degenerate_cycle() -> Scenario:
    """Negative control: a 3-cycle nobody ever escapes."""
    arrival = ["arg_A", "arg_B", "arg_C"]
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_B", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_C", "arg_A", AIF_KIND_UNDERMINE),
    ]
    return (
        "degenerate_cycle",
        "mutual attack: no argument is ever accepted after the cycle closes",
        arrival,
        attacks,
    )


def _verification_tally(trajectory: Sequence[AIFTrajectoryStep]) -> Dict[str, Any]:
    """Per-step verification outcome, kept honest.

    ``indeterminate`` is counted separately from ``agree`` — a step the JVM
    could not check is not a step that passed.
    """
    agree = sum(1 for s in trajectory if s.agree is True)
    disagree = sum(1 for s in trajectory if s.agree is False)
    indeterminate = sum(1 for s in trajectory if s.agree is None)
    return {
        "steps": len(trajectory),
        "agree": agree,
        "disagree": disagree,
        "indeterminate": indeterminate,
        "disagreements": [
            {"step": s.step, "detail": list(s.disagreements)}
            for s in trajectory
            if s.disagreements
        ],
    }


def _final_labelling(trajectory: Sequence[AIFTrajectoryStep]) -> Dict[str, List[str]]:
    """The labelling once the whole discourse has landed."""
    labelling = trajectory[-1].labelling
    if labelling is None:
        return {}
    return {
        "in": sorted(labelling.in_args),
        "out": sorted(labelling.out_args),
        "undec": sorted(labelling.undec_args),
    }


def _run(scenario: Scenario, *, verify: bool) -> Dict[str, Any]:
    name, blurb, arrival, attacks = scenario
    trajectory = aif_labelling_trajectory(arrival, attacks, verify=verify)
    transitions = aif_label_transitions(trajectory)

    print(f"\n=== {name} ===")
    print(f"{blurb}")
    print(f"arrival order: {' -> '.join(arrival)}\n")
    print(render_aif_trajectory(trajectory))
    print("\nper-argument label sequence (from its own arrival onwards):")
    for argument in arrival:
        print(f"  {argument}: {' -> '.join(transitions.get(argument, ()))}")

    tally = _verification_tally(trajectory)
    print(
        f"\nverification: {tally['agree']} agree / {tally['disagree']} disagree "
        f"/ {tally['indeterminate']} indeterminate  (out of {tally['steps']} steps)"
    )
    for entry in tally["disagreements"]:
        print(f"  step {entry['step']}: {entry['detail']}")

    return {
        "name": name,
        "arrival_order": arrival,
        "transitions": {k: list(v) for k, v in transitions.items()},
        "final_labelling": _final_labelling(trajectory),
        "verification": tally,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help=(
            "skip the per-step dual-backend cross-check (fast, JVM-free). "
            "Every step then reports 'indeterminate', never a fabricated pass."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="also emit a machine-readable summary on stdout.",
    )
    args = parser.parse_args()
    verify = not args.no_verify

    scenarios: List[Scenario] = [
        _scn_dynamics(),
        _scn_order_first(),
        _scn_order_second(),
        _scn_degenerate_cycle(),
    ]
    results = [_run(scenario, verify=verify) for scenario in scenarios]

    # The point of the order_matters pair: same endpoint, different paths.
    first = next(r for r in results if r["name"].endswith("attacker_last"))
    second = next(r for r in results if r["name"].endswith("attacker_first"))
    same_endpoint = first["final_labelling"] == second["final_labelling"]
    same_path = first["transitions"] == second["transitions"]
    print("\n=== order_matters: what the trajectory adds ===")
    print(f"  identical final labelling : {same_endpoint}")
    print(f"  identical trajectory      : {same_path}")
    print(
        "  => the static labelling is order-blind; the trajectory is not — "
        "that difference is the substrate."
    )

    if args.json:
        print(
            json.dumps(
                {
                    "scenarios": results,
                    "order_matters": {
                        "same_final_labelling": same_endpoint,
                        "same_trajectory": same_path,
                    },
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
