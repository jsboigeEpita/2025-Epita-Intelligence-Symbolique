"""Standalone CLI: cross-check the Dung argumentation backends.

This script is the offline counterpart to the in-process
``_compare_dung_backends`` wiring in
:mod:`argumentation_analysis.orchestration.invoke_callables`. It compares
the pure-Python backend (:mod:`abs_arg_dung.backends`) against the
Tweety-based ``DungAgent`` (sanctuary #893, JPype) on the same set of
synthetic frameworks, so any disagreement is reported verbatim without
auto-reconciliation (anti-pendule #1019).

Usage::

    # Run on canonical 7-framework regression set
    python scripts/compare_dung_backends.py --suite classics

    # Run on a synthetic Stochastic Block Model (scaling demo)
    python scripts/compare_dung_backends.py --suite sbm --num-blocks 5 --block-size 10

    # Run on an ICCMA .af file
    python scripts/compare_dung_backends.py --suite iccma --af path/to/example.af

    # Show only disagreements
    python scripts/compare_dung_backends.py --suite classics --only-disagreements

Privacy: this CLI touches **only synthetic frameworks**. It never reads
the encrypted corpus.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure the project root is on sys.path so `abs_arg_dung.backends` resolves.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from abs_arg_dung.backends import (  # noqa: E402
    backend_python,
    generate_classic_examples,
    generate_er,
    generate_sbm,
    parse_iccma_af_file,
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

Extension = List[str]
Extensions = Dict[str, List[Extension]]  # semantics -> extensions
BackendReport = Dict[str, object]


def _empty_extensions() -> Extensions:
    return {"grounded": [], "complete": [], "stable": []}


def _extensions_match(
    a: Extensions,
    b: Extensions,
) -> Tuple[bool, Dict[str, Dict[str, bool]]]:
    """Per-semantics: same set of extensions (order-insensitive)."""
    out: Dict[str, Dict[str, bool]] = {}
    for sem in ("grounded", "complete", "stable"):
        set_a = {tuple(sorted(ext)) for ext in a.get(sem, [])}
        set_b = {tuple(sorted(ext)) for ext in b.get(sem, [])}
        out[sem] = {"agree": set_a == set_b}
    return all(v["agree"] for v in out.values()), out


def _disagreements(
    args: List[str],
    atts: List[Tuple[str, str]],
    report_py: BackendReport,
    report_tw: BackendReport,
) -> List[str]:
    """Return a list of human-readable disagreement strings."""
    py_ext: Extensions = report_py.get("extensions") or _empty_extensions()  # type: ignore[assignment]
    tw_ext: Extensions = report_tw.get("extensions") or _empty_extensions()  # type: ignore[assignment]
    lines: List[str] = []
    for sem in ("grounded", "complete", "stable"):
        py_set = sorted({tuple(sorted(ext)) for ext in py_ext.get(sem, [])})
        tw_set = sorted({tuple(sorted(ext)) for ext in tw_ext.get(sem, [])})
        if py_set != tw_set:
            lines.append(f"[DISAGREE {sem}]")
            lines.append(f"  python: {py_set}")
            lines.append(f"  tweety: {tw_set}")
    if not lines:
        return []
    af_summary = f"n_args={len(args)}, n_atks={len(atts)}"
    return [f"Disagreement on ({af_summary}):"] + lines


# ---------------------------------------------------------------------------
# Backend runners
# ---------------------------------------------------------------------------

def _run_python(args: List[str], atts: List[Tuple[str, str]]) -> BackendReport:
    r = backend_python(args, atts)
    # Cast to BackendReport type for callers.
    return r  # type: ignore[return-value]


def _run_python_grounded_only(
    args: List[str], atts: List[Tuple[str, str]]
) -> BackendReport:
    """Variant for big frameworks (>25 args): skip complete/stable enumeration
    (which is O(2^n) in the worst case) and only compute the grounded extension
    (O(V*(V+E)) polynomial)."""
    import time
    from abs_arg_dung.backends import compute_grounded
    t0 = time.monotonic()
    grounded = compute_grounded(args, atts)
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    return {
        "backend": "python",
        "available": True,
        "note": "pure-stdlib, JVM-free (grounded-only mode for big AFs)",
        "extensions": {"grounded": [grounded], "complete": [], "stable": []},
        "elapsed_ms": round(elapsed_ms, 3),
    }


def _try_run_tweety(
    args: List[str],
    atts: List[Tuple[str, str]],
) -> Tuple[bool, BackendReport | None]:
    """Invoke the Tweety-based ``DungAgent`` facade. Returns ``(ok, report)``.

    Tweety requires a JVM via JPype. If unavailable, return ``(False, None)``
    and the comparison degrades to pure-Python only.
    """
    try:
        from abs_arg_dung.agent import DungAgent  # sanctuary #893  # noqa: E402
        from adapters.dung_student_provider import DungStudentProvider  # noqa: F401, E402
    except Exception:
        return False, None

    try:
        agent = DungAgent()  # type: ignore[no-untyped-call]
        for a in args:
            agent.add_argument(a)
        for src, tgt in atts:
            agent.add_attack(src, tgt)
        report: BackendReport = {
            "backend": "tweety",
            "available": True,
            "note": "abs_arg_dung.DungAgent via JPype (Tweety 1.28)",
            "extensions": {
                "grounded": [sorted(agent.get_grounded_extension())],
                "complete": [sorted(ext) for ext in agent.get_complete_extensions()],
                "stable": [sorted(ext) for ext in agent.get_stable_extensions()],
            },
            "elapsed_ms": 0.0,
        }
        return True, report
    except Exception as exc:  # pragma: no cover — JVM-dependent
        return False, {"backend": "tweety", "available": False, "note": f"error: {exc}"}


# ---------------------------------------------------------------------------
# Suite dispatch
# ---------------------------------------------------------------------------

def _suite_classics() -> List[Tuple[str, List[str], List[Tuple[str, str]]]]:
    out: List[Tuple[str, List[str], List[Tuple[str, str]]]] = []
    for name, (a, atts) in generate_classic_examples().items():
        out.append((name, a, atts))
    return out


def _suite_sbm(
    num_blocks: int,
    block_size: int,
    p_in: float,
    p_out: float,
    seed: int,
) -> List[Tuple[str, List[str], List[Tuple[str, str]]]]:
    block_sizes = [block_size] * num_blocks
    args, atts = generate_sbm(block_sizes, p_in=p_in, p_out=p_out, seed=seed)
    return [(f"sbm[{'x'.join(map(str, block_sizes))}@{p_in},{p_out}@{seed}]", args, atts)]


def _suite_er(num_args: int, p: float, seed: int) -> List[Tuple[str, List[str], List[Tuple[str, str]]]]:
    args, atts = generate_er(num_args, p=p, seed=seed)
    return [(f"er[{num_args}@{p}@{seed}]", args, atts)]


def _suite_iccma(path: str) -> List[Tuple[str, List[str], List[Tuple[str, str]]]]:
    args, atts = parse_iccma_af_file(path)
    return [(f"iccma[{Path(path).name}]", args, atts)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cross-check Dung backends on synthetic frameworks (no real corpus).",
    )
    p.add_argument(
        "--suite", choices=["classics", "sbm", "er", "iccma"], required=True,
        help="Which suite of frameworks to evaluate.",
    )
    p.add_argument("--af", type=str, default=None, help="Path to .af file (--suite iccma)")
    # SBM options
    p.add_argument("--num-blocks", type=int, default=4)
    p.add_argument("--block-size", type=int, default=10)
    p.add_argument("--p-in", type=float, default=0.3)
    p.add_argument("--p-out", type=float, default=0.05)
    # ER options
    p.add_argument("--num-args", type=int, default=50)
    p.add_argument("--p-er", type=float, default=0.05)
    # Random
    p.add_argument("--seed", type=int, default=42)
    # Output
    p.add_argument(
        "--only-disagreements", action="store_true",
        help="Print only disagreement lines; suppress the per-framework headers.",
    )
    p.add_argument(
        "--grounded-only", action="store_true",
        help="Skip complete/stable enumeration (O(2^n) in the worst case); "
             "useful for SBM scaling demos with >25 arguments.",
    )
    p.add_argument(
        "--json", type=str, default=None,
        help="Write the full report (one row per framework) as JSON to this path.",
    )
    return p


def main(argv: List[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.suite == "classics":
        suite = _suite_classics()
    elif args.suite == "sbm":
        suite = _suite_sbm(args.num_blocks, args.block_size, args.p_in, args.p_out, args.seed)
    elif args.suite == "er":
        suite = _suite_er(args.num_args, args.p_er, args.seed)
    elif args.suite == "iccma":
        if not args.af:
            print("--suite iccma requires --af <path>", file=sys.stderr)
            return 2
        suite = _suite_iccma(args.af)
    else:
        raise SystemExit(f"unknown suite: {args.suite}")

    # Probe once if Tweety is available.
    tweety_ok = False
    if suite:
        _, tweety_report = _try_run_tweety(suite[0][1], suite[0][2])
        if tweety_report is not None and bool(tweety_report.get("available", False)):
            tweety_ok = True

    rows = []
    for name, f_args, f_atts in suite:
        py_report: BackendReport = (
            _run_python_grounded_only(f_args, f_atts)
            if args.grounded_only
            else _run_python(f_args, f_atts)
        )
        tw_report: BackendReport = {"backend": "tweety", "available": False, "note": "Tweety not available"}
        if tweety_ok:
            ok, tw = _try_run_tweety(f_args, f_atts)
            if ok and tw is not None:
                tw_report = tw
            else:
                tweety_ok = False

        py_ext: Extensions = py_report["extensions"]  # type: ignore[assignment]
        tw_ext: Extensions = tw_report.get("extensions", _empty_extensions())  # type: ignore[assignment]

        agree, per_sem = _extensions_match(py_ext, tw_ext)
        rows.append({
            "framework": name,
            "n_args": len(f_args),
            "n_attacks": len(f_atts),
            "agree": agree,
            "per_semantics": per_sem,
            "python": {"available": py_report["available"], "elapsed_ms": py_report["elapsed_ms"]},
            "tweety": {"available": tw_report["available"], "note": tw_report.get("note", "")},
        })
        if not args.only_disagreements or not agree:
            print(f"\n=== {name} (n_args={len(f_args)}, n_attacks={len(f_atts)}) ===")
            print(f"  python ({py_report['elapsed_ms']:.1f}ms):")
            for sem, exts in py_ext.items():
                print(f"    {sem:>8}: {exts}")
            if tw_report.get("available"):
                print(f"  tweety:")
                for sem, exts in tw_ext.items():
                    print(f"    {sem:>8}: {exts}")
            if not agree:
                for line in _disagreements(f_args, f_atts, py_report, tw_report):
                    print(f"  {line}")

    n_disagree = sum(1 for r in rows if not r["agree"])
    print(f"\nSummary: {len(rows)} frameworks; {n_disagree} disagreements; tweety={'yes' if tweety_ok else 'no'}")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"Written: {args.json}")
    # do not gate on disagreements (anti-#1019: report verbatim, never reconcile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
