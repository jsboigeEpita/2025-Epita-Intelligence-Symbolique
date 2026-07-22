"""Standalone CLI: Dung labelling trajectory under sequential argument arrival.

Track S6-A2 (#1506) — CoursIA strate-6 Phase-A candidate substrate #1: "the
discourse as a substrate". A discourse delivers arguments one by one; under
grounded semantics each prefix induces a labelling (in/out/undec). This CLI
renders the resulting **trajectory of labelling states** and, optionally,
cross-checks the native Python backend against Tweety on the full AF (honest
degradation if the JVM is unavailable).

Privacy: touches ONLY synthetic frameworks with opaque ids. Never reads the
encrypted corpus. See the engine docstring in
:mod:`argumentation_analysis.orchestration.dung_labelling_trajectory`.

Usage::

    # Default: the canonical opaque discourse exemplar (acceptance/refutation/reinstatement)
    python scripts/labelling_trajectory.py --exemplar discourse

    # Cross-check the native grounded extension against Tweety on the full AF
    python scripts/labelling_trajectory.py --exemplar discourse --cross-check-tweety

    # Write the trajectory as JSON
    python scripts/labelling_trajectory.py --json trajectory.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure the project root is on sys.path so the engine + backends resolve.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from argumentation_analysis.orchestration.dung_labelling_trajectory import (  # noqa: E402
    DiscourseExemplar,
    build_discourse_exemplar,
    label_transitions,
    labelling_trajectory,
    render_trajectory,
)


def _trajectory_to_jsonable(exemplar: DiscourseExemplar) -> Dict[str, Any]:
    trajectory = labelling_trajectory(
        exemplar.arguments, exemplar.attacks, exemplar.arrival_order
    )
    return {
        "arguments": list(exemplar.arguments),
        "attacks": [list(a) for a in exemplar.attacks],
        "arrival_order": list(exemplar.arrival_order),
        "trajectory": [
            {
                "step": s.step,
                "arrived": list(s.arrived),
                "in": sorted(s.labelling.in_args),
                "out": sorted(s.labelling.out_args),
                "undec": sorted(s.labelling.undec_args),
            }
            for s in trajectory
        ],
        "transitions": {
            arg: list(seq) for arg, seq in sorted(label_transitions(trajectory).items())
        },
    }


def _try_tweety_grounded(
    args: List[str], atts: List[Tuple[str, str]]
) -> Tuple[bool, List[str] | None, str]:
    """Native-vs-Tweety grounded cross-check on the full AF (honest degradation).

    Mirrors ``scripts.compare_dung_backends._try_run_tweety``: lazy-imports the
    sanctuary ``DungAgent`` + idempotent ``initialize_jvm``; returns
    ``(available, grounded_extension_or_None, note)``. If the JVM/Tweety is
    unavailable, the trajectory (computed with the pure-Python backend) still
    stands — the cross-check is a validation, not a dependency.
    """

    try:
        from abs_arg_dung.agent import DungAgent  # sanctuary #893
        from argumentation_analysis.core.jvm_setup import initialize_jvm
    except Exception as exc:  # noqa: BLE001 — optional dependency
        return False, None, f"Tweety import unavailable: {exc}"
    try:
        if not initialize_jvm():
            return False, None, "JVM unavailable (initialize_jvm returned False)"
        agent = DungAgent()  # type: ignore[no-untyped-call]
        for a in args:
            agent.add_argument(a)
        for src, tgt in atts:
            agent.add_attack(src, tgt)
        ext = sorted(agent.get_grounded_extension())  # type: ignore[no-untyped-call]
        return True, ext, "abs_arg_dung.DungAgent via JPype (Tweety 1.28)"
    except Exception as exc:  # noqa: BLE001 — JVM-dependent, pragma: no cover
        return False, None, f"error: {exc}"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Dung labelling trajectory under sequential argument arrival "
            "(S6-A2 #1506 — CoursIA Phase-A candidate substrate #1). "
            "Touches only synthetic opaque-id frameworks."
        ),
    )
    p.add_argument(
        "--exemplar",
        choices=["discourse"],
        default="discourse",
        help="Which exemplar AF to run (only 'discourse' for now).",
    )
    p.add_argument(
        "--cross-check-tweety",
        action="store_true",
        help="Cross-check the native grounded extension against Tweety on the "
        "full AF (honest degradation if the JVM is unavailable).",
    )
    p.add_argument(
        "--json",
        type=str,
        default=None,
        help="Write the full trajectory (steps + transitions) as JSON to this path.",
    )
    return p


def main(argv: List[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    exemplar = build_discourse_exemplar()

    trajectory = labelling_trajectory(
        exemplar.arguments, exemplar.attacks, exemplar.arrival_order
    )

    print("=== S6-A2 labelling trajectory (opaque discourse exemplar) ===")
    for note in exemplar.notes:
        print(f"# {note}")
    print()
    print(render_trajectory(trajectory))

    print("\n--- label transitions (per argument, from its arrival) ---")
    for arg, seq in sorted(label_transitions(trajectory).items()):
        print(f"  {arg:<16}: {' -> '.join(seq)}")

    if args.cross_check_tweety:
        from abs_arg_dung.backends import compute_grounded

        native = sorted(
            compute_grounded(list(exemplar.arguments), list(exemplar.attacks))
        )
        ok, tweety_ext, note = _try_tweety_grounded(
            list(exemplar.arguments), list(exemplar.attacks)
        )
        print("\n--- native ≡ Tweety grounded cross-check (full AF) ---")
        print(f"  native (python): {native}")
        if ok and tweety_ext is not None:
            agree = set(native) == set(tweety_ext)
            print(f"  tweety:          {tweety_ext}")
            print(f"  agree: {agree}   ({note})")
        else:
            print(f"  tweety: UNAVAILABLE — {note}")
            print(
                "  (trajectory computed with the pure-Python backend; "
                "cross-check degraded, anti-théâtre #1019)"
            )

    if args.json:
        payload = _trajectory_to_jsonable(exemplar)
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWritten: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
