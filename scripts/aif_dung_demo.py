"""AIF → Dung adapter demo.

M1 #1520 — self-contained demo of the AIF-attacks → Dung-labelling
substrate. Runs three synthetic AIF scenarios through the adapter and
prints a per-scenario summary of the verification vs both backends.

Usage::

    PYTHONPATH=. python scripts/aif_dung_demo.py

Privacy: all examples are synthetic, with opaque IDs (``arg_A``…).
No encrypted corpus, no raw text.
"""

from __future__ import annotations

import json
from typing import Any, List

from abs_arg_dung.aif_adapter import (
    AIF_KIND_REBUT,
    AIF_KIND_UNDERCUT,
    AIF_KIND_UNDERMINE,
    AIFAttack,
    verify_aif_to_dung,
)


def _scn_nixon() -> tuple[str, list[str], list[AIFAttack]]:
    """Nixon Diamond via three undermines (mutual attack)."""
    args = ["arg_A", "arg_B", "arg_C"]
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_B", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_C", "arg_A", AIF_KIND_UNDERMINE),
    ]
    return ("nixon_diamond_aif", args, attacks)


def _scn_rebut_chain() -> tuple[str, list[str], list[AIFAttack]]:
    """Linear rebut chain: A→B→C→D (each rebuts the next)."""
    args = ["arg_A", "arg_B", "arg_C", "arg_D"]
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT),
        AIFAttack("arg_B", "arg_C", AIF_KIND_REBUT),
        AIFAttack("arg_C", "arg_D", AIF_KIND_REBUT),
    ]
    return ("rebut_chain", args, attacks)


def _scn_mixed_undercut_undermine_rebut() -> tuple[str, list[str], list[AIFAttack]]:
    """Mixed-kind fan-in: A and B both attack C, A undercuts B."""
    args = ["arg_A", "arg_B", "arg_C"]
    attacks = [
        AIFAttack("arg_A", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_B", "arg_C", AIF_KIND_REBUT),
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERCUT),
    ]
    return ("mixed_fan_in", args, attacks)


def _summarise(summary: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON-friendly summary stripped of the full extension dumps."""
    py = summary["backend_python"]
    tw = summary["backend_tweety"]
    return {
        "framework": {
            "args": summary["framework"][0],
            "attacks": [list(a) for a in summary["framework"][1]],
        },
        "backend_python": {
            "available": py["available"],
            "grounded": py["extensions"]["grounded"],
            "complete": py["extensions"]["complete"],
            "stable": py["extensions"]["stable"],
            "elapsed_ms": py["elapsed_ms"],
        },
        "backend_tweety_present": tw is not None,
        "backend_tweety_available": (tw or {}).get("available", False),
        "backend_tweety_note": (tw or {}).get("note", ""),
        "agree": summary["agree"],
        "disagreements": summary["disagreements"],
    }


def main() -> int:
    scenarios: List[tuple[str, list[str], list[AIFAttack]]] = [
        _scn_nixon(),
        _scn_rebut_chain(),
        _scn_mixed_undercut_undermine_rebut(),
    ]

    out: dict[str, Any] = {"scenarios": []}
    for name, args, attacks in scenarios:
        summary = verify_aif_to_dung(args, attacks)
        out["scenarios"].append({"name": name, **_summarise(summary)})

    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
