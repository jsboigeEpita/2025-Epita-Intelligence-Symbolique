#!/usr/bin/env python
"""RA-3 #1048 item 4 — wall-clock benchmark: parallel vs forced-sequential
recursive fallacy descent in ``FallacyWorkflowPlugin``.

What this measures
------------------
``FallacyWorkflowPlugin.run_guided_analysis`` (Phase 2) fans out branch
exploration with ``asyncio.gather`` over the wide-net candidate PKs
(``fallacy_workflow_plugin.py`` L1182). This harness measures the wall-clock
benefit of that fan-out by running the SAME engine two ways on the SAME input:

  - ``parallel``   : engine as-is — gather runs branches concurrently.
  - ``sequential`` : ``asyncio.gather`` is swapped for a cap=1 shim that awaits
                     branch coroutines one at a time. The descent is NOT
                     disabled — the same branches run, just serially
                     (anti-pendule #1019: cap=1 forces sequential of the SAME
                     engine, it does not turn descent off).

Why a latency stub (default ``--mode sim``)
-------------------------------------------
The parallel speedup of ``gather`` is entirely about overlapping the network
latency of LLM round-trips. Measuring it with a live LLM would (a) cost tokens
on a tight quota and (b) drown the signal in LLM-latency variance (0.5–10s).
So the default mode injects a fixed-latency LLM stub: each round-trip is a
controlled ``asyncio.sleep(latency)`` and the stub returns canned tool calls
that drive the REAL descent structurally (first-child descent, beam selection).
Only the LLM responses are synthetic — every line of concurrency logic measured
is the real engine's. The numbers are real wall-clock of real engine code; the
LLM latency is a controlled constant, not a fabricated result.

Because the stub navigates the taxonomy structurally (it ignores the argument
text), SIM wall-clock is content-independent — so no corpus decryption is
needed and there is zero dataset-privacy surface. ``--mode real`` is provided
for confirmation when a funded key exists; without one it SKIPS visibly rather
than emitting a fake number.

Output discipline (CLAUDE.md §Dataset Privacy)
----------------------------------------------
Detailed per-run JSON is written under the gitignored
``argumentation_analysis/evaluation/results/``. Only the aggregated wall-clock
table printed to stdout belongs in a PR body — and it contains no corpus
content (opaque case labels + timings only).

Usage
-----
  python scripts/benchmarks/bench_parallel_descent.py --branches 2 4 8 --runs 3
  python scripts/benchmarks/bench_parallel_descent.py --mode real --corpus-idx 17
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from semantic_kernel.kernel import Kernel  # noqa: E402
from semantic_kernel.connectors.ai.chat_completion_client_base import (  # noqa: E402
    ChatCompletionClientBase,
)
from semantic_kernel.contents import (  # noqa: E402
    ChatMessageContent,
    FunctionCallContent,
)
from semantic_kernel.contents.utils.author_role import AuthorRole  # noqa: E402

from argumentation_analysis.plugins.fallacy_workflow_plugin import (  # noqa: E402
    FallacyWorkflowPlugin,
)

TAXONOMY_CSV = (
    REPO_ROOT / "argumentation_analysis" / "data" / "argumentum_fallacies_taxonomy.csv"
)
RESULTS_DIR = REPO_ROOT / "argumentation_analysis" / "evaluation" / "results"

# A synthetic, rhetoric-laden text. Content is IGNORED by the stub (structural
# navigation), so SIM timings do not depend on it; it only fills the prompts.
SYNTHETIC_TEXT = (
    "Everyone knows this policy is right because all the experts agree, and "
    "if you disagree you clearly do not care about the future of our children. "
    "We have always done it this way, so it must be correct. Either we act now "
    "or we lose everything — there is no middle ground. My opponent is a known "
    "liar, therefore his budget figures cannot be trusted."
)

# --- prompt parsing patterns ------------------------------------------------
_PK_PAREN_RE = re.compile(r"\(PK:\s*(\d+)\)")
_PK_EXPLORE_RE = re.compile(r"explore_branch\(node_pk='(\d+)'\)")
_ROOT_RE = re.compile(r"^- (.+?) \(PK:\s*(\d+)\)", re.MULTILINE)


class LatencyStubChatCompletion(ChatCompletionClientBase):
    """Latency-controlled LLM stub driving the descent structurally.

    Models each LLM round-trip as a fixed ``latency`` sleep and returns canned
    tool calls / JSON so the REAL descent engine runs end-to-end with no
    network / API / token cost. Navigation is purely structural (first-child
    descent for branch exploration, first-k children for beam), which is what
    makes the parallel/sequential ratio a clean function of branch-count×depth.
    """

    # extra pydantic fields (subclass-declared; allowed regardless of extra policy)
    latency: float = 0.3
    max_branches: int = 8
    call_log: List[Dict[str, Any]] = []  # mutated in place; reset per run

    # -- helpers --
    @staticmethod
    def _last_user(chat_history: Any) -> str:
        msgs = getattr(chat_history, "messages", []) or []
        for m in reversed(msgs):
            if getattr(m, "role", None) == AuthorRole.USER:
                return str(getattr(m, "content", ""))
        return str(msgs[-1].content) if msgs else ""

    def _decide_tool(self, prompt: str) -> FunctionCallContent:
        """Plural path: branch exploration + leaf confirmation."""
        if "LEAF node" in prompt:
            m = _PK_PAREN_RE.search(prompt)
            pk = m.group(1) if m else ""
            # Confirm at the leaf: deep node, different lineage per branch, so no
            # cross-branch supersession — keeps all branches doing full work and
            # yields a non-empty result (skips the one-shot fallback).
            return FunctionCallContent(
                id="call_leaf",
                name="confirm_fallacy",
                arguments={
                    "node_pk": pk,
                    "confidence": "high",
                    "justification": "stub: structural leaf confirm",
                },
            )
        m = _PK_EXPLORE_RE.search(prompt)
        if m:  # double-selection: descend into the first listed child
            return FunctionCallContent(
                id="call_explore",
                name="explore_branch",
                arguments={"node_pk": m.group(1)},
            )
        return FunctionCallContent(
            id="call_none",
            name="conclude_no_fallacy",
            arguments={"reason": "stub: no explorable child"},
        )

    def _decide_json(self, prompt: str) -> str:
        """Singular path: wide-net Phase 1 + beam selection."""
        if "Available root categories" in prompt:
            roots = _ROOT_RE.findall(prompt)
            chosen = roots[: self.max_branches]
            arr = [
                {"fallacy_name": name, "root_category": name, "confidence": 0.85}
                for name, _pk in chosen
            ]
            return json.dumps(arr, ensure_ascii=False)
        if "Select the TOP" in prompt or "Children:" in prompt:
            pks = _PK_PAREN_RE.findall(prompt)
            arr = [{"pk": pk, "confidence": 0.7, "reason": "stub"} for pk in pks[:3]]
            return json.dumps(arr, ensure_ascii=False)
        return "[]"

    # -- ChatCompletionClientBase overrides --
    async def get_chat_message_contents(
        self, chat_history: Any, settings: Any = None, **kwargs: Any
    ) -> List[ChatMessageContent]:
        await asyncio.sleep(self.latency)
        prompt = self._last_user(chat_history)
        self.call_log.append({"kind": "tool", "t": time.perf_counter()})
        return [
            ChatMessageContent(
                role=AuthorRole.ASSISTANT, items=[self._decide_tool(prompt)]
            )
        ]

    async def get_chat_message_content(
        self, chat_history: Any, settings: Any = None, **kwargs: Any
    ) -> ChatMessageContent:
        await asyncio.sleep(self.latency)
        prompt = self._last_user(chat_history)
        self.call_log.append({"kind": "json", "t": time.perf_counter()})
        return ChatMessageContent(
            role=AuthorRole.ASSISTANT, content=self._decide_json(prompt)
        )


async def _sequential_gather(*aws: Any, return_exceptions: bool = False) -> List[Any]:
    """cap=1 replacement for ``asyncio.gather``: await each awaitable serially.

    Mirrors ``return_exceptions`` semantics so the engine's result-collection
    code (which inspects exceptions) behaves identically — only the concurrency
    changes.
    """
    out: List[Any] = []
    for aw in aws:
        try:
            out.append(await aw)
        except BaseException as exc:  # noqa: BLE001 — mirror gather(return_exceptions)
            if return_exceptions:
                out.append(exc)
            else:
                raise
    return out


def build_plugin(
    latency: float, max_branches: int, llm_service: Any = None
) -> Tuple[FallacyWorkflowPlugin, Any]:
    with open(TAXONOMY_CSV, encoding="utf-8") as f:
        taxonomy = list(csv.DictReader(f))
    if llm_service is None:
        llm_service = LatencyStubChatCompletion(
            ai_model_id="stub-llm", latency=latency, max_branches=max_branches
        )
    master = Kernel()
    master.add_service(llm_service)
    plugin = FallacyWorkflowPlugin(
        master_kernel=master, llm_service=llm_service, taxonomy_data=taxonomy
    )
    return plugin, llm_service


async def _run_once(
    plugin: FallacyWorkflowPlugin, text: str, sequential: bool
) -> Tuple[float, Dict[str, Any]]:
    svc = plugin.llm_service
    if hasattr(svc, "call_log"):
        svc.call_log.clear()
    t0 = time.perf_counter()
    if sequential:
        with patch("asyncio.gather", _sequential_gather):
            result_json = await plugin.run_guided_analysis(argument_text=text)
    else:
        result_json = await plugin.run_guided_analysis(argument_text=text)
    elapsed = time.perf_counter() - t0
    meta: Dict[str, Any] = {"llm_calls": len(getattr(svc, "call_log", []))}
    try:
        parsed = json.loads(result_json)
        meta["branches_explored"] = parsed.get("branches_explored")
        meta["exploration_method"] = parsed.get("exploration_method")
        meta["n_fallacies"] = len(parsed.get("fallacies", []))
    except (json.JSONDecodeError, TypeError):
        pass
    return elapsed, meta


def _median(xs: List[float]) -> float:
    return statistics.median(xs) if xs else float("nan")


async def main_async(args: argparse.Namespace) -> int:
    if args.mode == "real":
        # Real-LLM wiring (a live llm_service + encrypted-corpus loading) is NOT
        # implemented in this harness: build_plugin always injects the latency
        # stub. Emitting the stub's timings under a "real" label would be
        # fabricated numbers (anti-théâtre #1019), so real mode refuses outright
        # rather than mislabel stub output — regardless of whether a key is set.
        print(
            "[ABORT] --mode real is not wired: this harness only drives the "
            "latency-stub engine, so it cannot produce live-LLM numbers. sim "
            "mode is the accepted, primary measurement (see "
            "RA3_1048_parallel_descent_findings.md). Refusing to emit stub "
            "timings under a 'real' label. No numbers emitted (not faked).",
            file=sys.stderr,
        )
        return 2

    text = SYNTHETIC_TEXT
    rows: List[Dict[str, Any]] = []

    for n in args.branches:
        plugin, _svc = build_plugin(args.latency, n)

        # warm-up (taxonomy index build etc.) — discarded
        await _run_once(plugin, text, sequential=False)

        par_times: List[float] = []
        seq_times: List[float] = []
        meta_par: Dict[str, Any] = {}
        meta_seq: Dict[str, Any] = {}
        for _ in range(args.runs):
            e, meta_par = await _run_once(plugin, text, sequential=False)
            par_times.append(e)
        for _ in range(args.runs):
            e, meta_seq = await _run_once(plugin, text, sequential=True)
            seq_times.append(e)

        par_med = _median(par_times)
        seq_med = _median(seq_times)
        ratio = seq_med / par_med if par_med else float("nan")
        rows.append(
            {
                "branches_requested": n,
                "branches_explored": meta_par.get("branches_explored"),
                "llm_calls": meta_par.get("llm_calls"),
                "par_median_s": round(par_med, 4),
                "seq_median_s": round(seq_med, 4),
                "ratio": round(ratio, 2),
                "par_runs_s": [round(x, 4) for x in par_times],
                "seq_runs_s": [round(x, 4) for x in seq_times],
                "exploration_method": meta_par.get("exploration_method"),
            }
        )

    # --- aggregated table (PR-body safe: no corpus content) ---
    print()
    print(
        f"RA-3 #1048 item 4 — parallel vs sequential descent  "
        f"(mode={args.mode}, latency={args.latency}s/call, runs={args.runs})"
    )
    print("-" * 78)
    print(
        f"{'branches':>9} {'explored':>9} {'llm_calls':>10} "
        f"{'seq (s)':>9} {'par (s)':>9} {'ratio':>7}"
    )
    print("-" * 78)
    for r in rows:
        print(
            f"{r['branches_requested']:>9} {str(r['branches_explored']):>9} "
            f"{str(r['llm_calls']):>10} {r['seq_median_s']:>9} "
            f"{r['par_median_s']:>9} {r['ratio']:>6}x"
        )
    print("-" * 78)

    # --- detailed JSON to gitignored results dir ---
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"bench_parallel_descent_{args.mode}_{stamp}.json"
    payload = {
        "task": "RA-3 #1048 item 4",
        "mode": args.mode,
        "latency_s": args.latency,
        "runs": args.runs,
        "rows": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[detail] {out_path}")
    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--branches",
        type=int,
        nargs="+",
        default=[2, 4, 8],
        help="branch-count sweep (wide-net candidate cap per config)",
    )
    p.add_argument("--runs", type=int, default=3, help="runs per config (median)")
    p.add_argument(
        "--latency",
        type=float,
        default=0.3,
        help="modeled per-LLM-call latency in seconds (sim mode)",
    )
    p.add_argument(
        "--mode",
        choices=["sim", "real"],
        default="sim",
        help="sim=latency stub (default, $0); real=NOT WIRED, aborts (no faked numbers)",
    )
    p.add_argument(
        "--corpus-idx",
        type=int,
        default=None,
        help="(real mode) encrypted-corpus index; tracked blob, in-memory only",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async(parse_args())))
