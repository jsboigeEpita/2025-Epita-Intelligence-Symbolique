"""5-run reproducibility validation for #509.

Runs the spectacular workflow N_RUNS times on each of the 3 opaque
documents (src0_ext0 / src3_ext0 / src6_ext0) and measures run-to-run
variance on fallacy count, field coverage, capability count, and duration.

Outputs raw per-run JSON + an aggregate JSON under analysis_kb/results/
(gitignored). The aggregate is the input for docs/reports/REPRODUCIBILITY_*.md.

Acceptance (Epic G DEFERRED criterion):
- fallacy count stable within ±1 across N runs per doc
- non-empty field count variance <= 2 fields per doc
"""
import argparse
import asyncio
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_epic_g_baselines import load_document_text

DOC_IDS = ["src0_ext0", "src3_ext0", "src6_ext0"]
N_RUNS_DEFAULT = 5
RUN_TIMEOUT_DEFAULT = 600  # seconds — hard cap per run (spectacular workflow can hang on Dung/AF phases)
RESULTS_DIR = Path("analysis_kb/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


async def run_once(text: str, timeout_s: int, workflow_name: str) -> dict[str, Any]:
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    start = time.time()
    results = await asyncio.wait_for(
        run_unified_analysis(text=text, workflow_name=workflow_name),
        timeout=timeout_s,
    )
    duration = time.time() - start

    state = results.get("state_snapshot", {})
    summary = results.get("summary", {})

    return {
        "duration_seconds": round(duration, 1),
        "phases_completed": summary.get("completed", 0),
        "phases_total": summary.get("total", 0),
        "non_empty_fields": sum(
            1 for v in state.values() if v not in (None, "", [], {})
        ),
        "total_fields": len(state),
        "fallacies_count": len(state.get("fallacies", [])),
        "arguments_count": len(state.get("arguments", [])),
        "jtms_beliefs_count": len(state.get("jtms_beliefs", [])),
        "capabilities_used": len(results.get("capabilities_used", [])),
    }


def run_once_isolated(doc_id: str, timeout_s: int, workflow_name: str) -> dict[str, Any]:
    """Spawn a fresh Python process to do one run — isolates JVM/asyncio/module state.

    The child invokes this same script with --child-mode and prints a JSON result
    on its last stdout line. We give the subprocess a small wall-clock buffer over
    the in-run timeout so it gets a chance to print the TimeoutError JSON itself.
    """
    cmd = [
        sys.executable, "-u", str(Path(__file__).resolve()),
        "--child-mode", doc_id,
        "--timeout", str(timeout_s),
        "--workflow", workflow_name,
    ]
    wall_clock = timeout_s + 60  # extra margin for import + load_document_text
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=wall_clock,
            env=env,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"error": f"SubprocessTimeout: exceeded {wall_clock}s wall clock"}

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-400:]
        return {
            "error": f"SubprocessExit: rc={proc.returncode}",
            "stderr_tail": tail.strip(),
            "duration_seconds": round(time.time() - start, 1),
        }

    last_json_line = None
    for line in (proc.stdout or "").splitlines()[::-1]:
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            last_json_line = line
            break
    if not last_json_line:
        return {
            "error": "SubprocessParse: no JSON line in stdout",
            "duration_seconds": round(time.time() - start, 1),
        }
    try:
        return json.loads(last_json_line)
    except json.JSONDecodeError as e:
        return {"error": f"SubprocessParse: {e}", "duration_seconds": round(time.time() - start, 1)}


async def child_main(doc_id: str, timeout_s: int, workflow_name: str) -> int:
    """Entry point for the --child-mode subprocess: one run, JSON to stdout, exit."""
    text = load_document_text(doc_id)
    if not text:
        print(json.dumps({"error": "load_failed"}))
        return 0
    try:
        res = await run_once(text, timeout_s=timeout_s, workflow_name=workflow_name)
    except asyncio.TimeoutError:
        print(json.dumps({"error": f"TimeoutError: exceeded {timeout_s}s"}))
        return 0
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        return 0
    print(json.dumps(res))
    return 0


def _range(values: list[float]) -> dict[str, Any]:
    return {
        "values": values,
        "min": min(values),
        "max": max(values),
        "range": round(max(values) - min(values), 2),
        "mean": round(statistics.fmean(values), 2),
        "stdev": round(statistics.pstdev(values), 2) if len(values) > 1 else 0.0,
    }


async def reproducibility_for_doc(
    doc_id: str, n_runs: int, timeout_s: int, workflow_name: str, isolate: bool = False
) -> dict[str, Any]:
    print(f"\n[{doc_id}] loading...")
    text = load_document_text(doc_id) if not isolate else None
    if not isolate and not text:
        print(f"[{doc_id}] ERROR: could not load")
        return {"doc_id": doc_id, "error": "load_failed"}
    if text:
        print(f"[{doc_id}] loaded {len(text)} chars")
    else:
        print(f"[{doc_id}] (isolate mode — child process loads document per run)")

    runs: list[dict[str, Any]] = []
    for i in range(1, n_runs + 1):
        print(f"[{doc_id}] run {i}/{n_runs}...", end=" ", flush=True)
        if isolate:
            res = run_once_isolated(doc_id, timeout_s=timeout_s, workflow_name=workflow_name)
            if "error" in res:
                print(res["error"])
                runs.append({"run": i, **res})
                continue
        else:
            try:
                res = await run_once(text, timeout_s=timeout_s, workflow_name=workflow_name)
            except asyncio.TimeoutError:
                print(f"TIMEOUT (>{timeout_s}s)")
                runs.append({"run": i, "error": f"TimeoutError: exceeded {timeout_s}s"})
                continue
            except Exception as exc:
                print(f"FAIL ({type(exc).__name__}: {exc})")
                runs.append({"run": i, "error": f"{type(exc).__name__}: {exc}"})
                continue
        res["run"] = i
        runs.append(res)
        print(
            f"OK ({res['duration_seconds']}s, "
            f"{res['non_empty_fields']}/{res['total_fields']} fields, "
            f"{res['fallacies_count']} fallacies, "
            f"{res['capabilities_used']} caps)"
        )

    ok_runs = [r for r in runs if "error" not in r]
    if not ok_runs:
        return {"doc_id": doc_id, "runs": runs, "error": "all_runs_failed"}

    fallacy_counts = [r["fallacies_count"] for r in ok_runs]
    field_counts = [r["non_empty_fields"] for r in ok_runs]
    cap_counts = [r["capabilities_used"] for r in ok_runs]
    durations = [r["duration_seconds"] for r in ok_runs]

    fallacy_range = max(fallacy_counts) - min(fallacy_counts)
    field_range = max(field_counts) - min(field_counts)

    return {
        "doc_id": doc_id,
        "n_runs_requested": n_runs,
        "n_runs_ok": len(ok_runs),
        "runs": runs,
        "variance": {
            "fallacies": _range(fallacy_counts),
            "fields": _range(field_counts),
            "capabilities": _range(cap_counts),
            "duration": _range(durations),
        },
        "acceptance": {
            "fallacy_within_1": fallacy_range <= 1,
            "fields_within_2": field_range <= 2,
        },
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=N_RUNS_DEFAULT,
                        help=f"Runs per document (default: {N_RUNS_DEFAULT})")
    parser.add_argument("--docs", nargs="+", default=DOC_IDS,
                        help="Opaque doc IDs (default: all 3)")
    parser.add_argument("--timeout", type=int, default=RUN_TIMEOUT_DEFAULT,
                        help=f"Per-run timeout in seconds (default: {RUN_TIMEOUT_DEFAULT})")
    parser.add_argument("--workflow", default="spectacular",
                        help="Workflow name (default: spectacular)")
    parser.add_argument("--isolate", action="store_true",
                        help="Run each iteration in a fresh subprocess (eliminates JVM/asyncio state accumulation)")
    parser.add_argument("--child-mode", default=None,
                        help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.child_mode:
        rc = await child_main(args.child_mode, timeout_s=args.timeout, workflow_name=args.workflow)
        sys.exit(rc)

    started = datetime.now(timezone.utc).isoformat()
    per_doc: list[dict[str, Any]] = []

    for doc_id in args.docs:
        per_doc.append(await reproducibility_for_doc(
            doc_id, args.runs, timeout_s=args.timeout, workflow_name=args.workflow, isolate=args.isolate
        ))

    finished = datetime.now(timezone.utc).isoformat()

    aggregate = {
        "issue": "#509",
        "workflow": args.workflow,
        "timeout_per_run_s": args.timeout,
        "isolate_subprocess": bool(args.isolate),
        "n_runs_per_doc": args.runs,
        "doc_count": len(args.docs),
        "started_utc": started,
        "finished_utc": finished,
        "per_doc": per_doc,
        "global_acceptance": {
            "all_docs_fallacy_within_1": all(
                d.get("acceptance", {}).get("fallacy_within_1", False)
                for d in per_doc if "acceptance" in d
            ),
            "all_docs_fields_within_2": all(
                d.get("acceptance", {}).get("fields_within_2", False)
                for d in per_doc if "acceptance" in d
            ),
        },
    }

    out_path = RESULTS_DIR / f"reproducibility_aggregate_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(aggregate, f, indent=2, default=str)
    print(f"\nAggregate saved to {out_path}")

    print("\n=== SUMMARY ===")
    for d in per_doc:
        if "error" in d:
            print(f"  {d['doc_id']}: ERROR ({d['error']})")
            continue
        v = d["variance"]
        a = d["acceptance"]
        print(
            f"  {d['doc_id']}: fallacies {v['fallacies']['min']}-{v['fallacies']['max']} "
            f"(d={v['fallacies']['range']}) | fields d={v['fields']['range']} | "
            f"caps d={v['capabilities']['range']} | dur {v['duration']['mean']}s mean | "
            f"FALL±1={a['fallacy_within_1']} FIELDS±2={a['fields_within_2']}"
        )
    print(
        f"\nGLOBAL: fallacy_within_1={aggregate['global_acceptance']['all_docs_fallacy_within_1']} "
        f"fields_within_2={aggregate['global_acceptance']['all_docs_fields_within_2']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
