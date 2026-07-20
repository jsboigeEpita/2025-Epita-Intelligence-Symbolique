#!/usr/bin/env python3
"""extract_belief_trajectories.py — Track TPM-1 #1489.

Extract real belief-state trajectories from the `argumentation_analysis`
pipeline (democratech workflow) and derive a stochastic transition matrix
(TPM) over the observed states, OR an honest "impossibility" verdict when
the trajectories do not form a usable chain.

Source (default): the synthetic 5-proposition Democratech demo bundle
(``examples/democratech_deliberation/synthetic_proposals.py``) — synthetic,
domain-public, no corpus. Run with ``LLM_CACHE_MODE=replay`` for determinism.

Privacy HARD (#1489): default source is synthetic. Any corpora-fed run
keeps its artefacts under a gitignored output dir and uses opaque IDs
on all GitHub-indexed surfaces.

Gate dur falsifiable (DoD #1489, copied from CoursIA #7289):
  - VRAIE TPM depuis source réelle du dépôt
    (states defined explicitly, transitions counted from observed
    trajectories, row-stochastic matrix), OR
  - Verdict d'impossibilité écrit + re-scope honnête.

Anti-théâtre (#1019): zero inventaire. Trajectoires = exécutions réelles
du pipeline. Verdict "espace d'états dégénéré, N transitions observées"
est un résultat VALIDE si c'est la réalité.

Usage:
    # Demo bundle (default), replay cache (recommended for determinism):
    LLM_CACHE_MODE=replay conda run -n projet-is-roo-new \\
        python scripts/extract_belief_trajectories.py

    # Custom output dir (defaults to evaluation/results/tpm_extraction/):
    python scripts/extract_belief_trajectories.py --output-dir evaluation/results/my_run

    # Dry-run: print contract + state-space definition only, no LLM call:
    python scripts/extract_belief_trajectories.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("TPM-1")


# ---------------------------------------------------------------------------
# State-space definition
# ---------------------------------------------------------------------------
#
# An "observation" is captured after each phase of the democratech workflow
# via the ``checkpoint_callback`` hook of ``run_unified_analysis``. The state
# vector is intentionally LIGHT (no corpus leakage, no raw_text, no LLM
# verbatim) — only per-phase aggregate counts + verdict markers, since these
# are the only invariant signals exposed by UnifiedAnalysisState without
# requiring new instrumentation.
#
# State vector (dict, JSON-serializable, no PII):
#   {
#     "phase_status":     "completed" | "failed" | "skipped",
#     "n_arguments":      int,   # identified_arguments count
#     "n_fallacies":      int,   # identified_fallacies count
#     "n_beliefs":        int,   # belief_sets count (JTMS-style)
#     "n_counters":       int,   # counter_arguments count (best-effort)
#     "n_accepted":       int,   # debate-accepted (post adversarial_debate)
#     "n_rejected":       int,   # debate-rejected
#     "vote_winner":      str|None,  # democratic_vote winner (opaque)
#     "vote_consensus":   float|None, # democratic_vote consensus rate
#     "degraded":         bool,
#   }
#
# Compact "state label" used as a TPM row/column index:
#   "<phase_status>:<n_args_bucket>:<n_fallacies_bucket>:<vote>"
#   e.g. "completed:3-5:0:none", "completed:3-5:1-2:none",
#        "completed:3-5:0:arg_A", "completed:3-5:0:high_consensus"
#
# Bucketing rationale:
# - 0 / 1-2 / 3-5 / 6+ arguments — coarser buckets yield a smaller state
#   space, more transitions per pair (better statistics from N=50 obs).
# - The 5-prop bundle consistently yields ~3-5 arguments per proposition,
#   so a 4-bucket scheme leaves room for synthetic-extended corpora later.

_ARG_BUCKETS: List[Tuple[int, int, str]] = [
    (0, 0, "0"),
    (1, 2, "1-2"),
    (3, 5, "3-5"),
    (6, 10**9, "6+"),
]

_FALLACY_BUCKETS: List[Tuple[int, int, str]] = [
    (0, 0, "0"),
    (1, 2, "1-2"),
    (3, 10**9, "3+"),
]

_COUNTER_BUCKETS: List[Tuple[int, int, str]] = [
    (0, 0, "0"),
    (1, 10**9, "1+"),
]

# Belief-set buckets — coarse, matches the JTMS-style signal in
# UnifiedAnalysisState.get_state_snapshot (jtms_belief_count). The 5-prop
# demo consistently yields 8-14 jtms_beliefs at the post-belief_tracking
# state, so 3 buckets cover the observed range without over-partitioning.
_BELIEF_BUCKETS: List[Tuple[int, int, str]] = [
    (0, 0, "0"),
    (1, 5, "1-5"),
    (6, 10**9, "6+"),
]


def _bucket(value: int, buckets: List[Tuple[int, int, str]]) -> str:
    for lo, hi, label in buckets:
        if lo <= value <= hi:
            return label
    return "?"  # unreachable given the open-ended last bucket


def _state_label(snapshot: Dict[str, Any]) -> str:
    """Compact state label for one phase observation."""
    phase_status = snapshot.get("phase_status", "?")
    n_args = int(snapshot.get("n_arguments", 0) or 0)
    n_fall = int(snapshot.get("n_fallacies", 0) or 0)
    n_counters = int(snapshot.get("n_counters", 0) or 0)
    n_beliefs = int(snapshot.get("n_beliefs", 0) or 0)
    vote = snapshot.get("vote_winner")
    consensus = snapshot.get("vote_consensus")
    if vote is None:
        vote_label = "none"
    elif isinstance(consensus, (int, float)) and consensus >= 0.7:
        vote_label = f"{vote}:high"
    elif isinstance(consensus, (int, float)) and consensus >= 0.4:
        vote_label = f"{vote}:mid"
    else:
        vote_label = f"{vote}:low"
    return (
        f"{phase_status}:args{_bucket(n_args, _ARG_BUCKETS)}:"
        f"fall{_bucket(n_fall, _FALLACY_BUCKETS)}:"
        f"ctr{_bucket(n_counters, _COUNTER_BUCKETS)}:"
        f"bel{_bucket(n_beliefs, _BELIEF_BUCKETS)}:"
        f"vote{vote_label}"
    )


# ---------------------------------------------------------------------------
# Trajectory capture
# ---------------------------------------------------------------------------


@dataclass
class PhaseObservation:
    """One observation captured after a workflow phase."""

    phase_name: str
    capability: str
    phase_status: str
    snapshot: Dict[str, Any] = field(default_factory=dict)
    state_label: str = ""
    # Wall-clock relative to the run start (seconds).
    elapsed_seconds: float = 0.0


@dataclass
class Trajectory:
    """One full pipeline run, ordered list of phase observations."""

    corpus_id: str
    corpus_label: str
    observations: List[PhaseObservation] = field(default_factory=list)
    workflow_name: str = "democratech"
    total_elapsed_seconds: float = 0.0
    terminated_by_budget: bool = False
    error: Optional[str] = None


def _summarize_phase_output(phase_name: str, phase_output: Any) -> Dict[str, Any]:
    """Pull a LIGHT aggregate summary from a phase output (no raw text)."""
    summary: Dict[str, Any] = {"phase": phase_name}
    if not isinstance(phase_output, dict):
        return summary
    # Extract: arguments + claims counts (privacy-safe aggregates only).
    if phase_name == "extract":
        args = phase_output.get("arguments", [])
        claims = phase_output.get("claims", [])
        summary["n_arguments"] = len(args) if isinstance(args, list) else 0
        summary["n_claims"] = len(claims) if isinstance(claims, list) else 0
        summary["extraction_status"] = phase_output.get("extraction_status", "?")
    # Quality baseline: aggregate per-argument quality scores (means only).
    if phase_name == "quality_baseline":
        q = phase_output.get("quality_scores", phase_output.get("scores", []))
        if isinstance(q, list) and q:
            try:
                vals = [
                    float(x.get("score", x.get("value", 0)) if isinstance(x, dict) else x)
                    for x in q
                ]
                summary["quality_avg"] = round(sum(vals) / len(vals), 3)
            except (TypeError, ValueError):
                summary["quality_avg"] = None
        summary["degraded"] = bool(phase_output.get("degraded", False))
    # Fallacy detection: count of flagged fallacies (no verbatim content).
    if phase_name == "fallacy_detection":
        fl = phase_output.get("fallacies", phase_output.get("detected", []))
        summary["n_fallacies"] = len(fl) if isinstance(fl, list) else 0
        summary["degraded"] = bool(phase_output.get("degraded", False))
    # Counter-arguments: count.
    if phase_name == "counter_arguments":
        ca = phase_output.get("counter_arguments", phase_output.get("counters", []))
        summary["n_counters"] = len(ca) if isinstance(ca, list) else 0
    # Adversarial debate: accepted / rejected counts (from agent output).
    if phase_name == "adversarial_debate":
        # Output shape varies — accept multiple keys defensively.
        for k_accepted, k_rejected in (
            ("accepted", "rejected"),
            ("winners", "losers"),
        ):
            acc = phase_output.get(k_accepted)
            rej = phase_output.get(k_rejected)
            if isinstance(acc, list):
                summary["n_accepted"] = len(acc)
            if isinstance(rej, list):
                summary["n_rejected"] = len(rej)
        # Fallback: count rounds / turns.
        rounds = phase_output.get("rounds", phase_output.get("turns", []))
        if isinstance(rounds, list):
            summary["n_rounds"] = len(rounds)
        summary["degraded"] = bool(phase_output.get("degraded", False))
    # Belief tracking: JTMS counts (best-effort, depends on state shape).
    if phase_name == "belief_tracking":
        bs = phase_output.get("belief_sets", phase_output.get("beliefs", []))
        if isinstance(bs, list):
            summary["n_beliefs"] = len(bs)
        # Contract for belief contradictions by detected fallacies (AGM-style).
        contractions = phase_output.get("contractions", [])
        if isinstance(contractions, list):
            summary["n_contractions"] = len(contractions)
        summary["degraded"] = bool(phase_output.get("degraded", False))
    # Democratic vote: winner + consensus.
    if phase_name == "democratic_vote":
        verdict = phase_output.get("governance_verdict") or {}
        winners = verdict.get("winners_per_method") or {}
        if isinstance(winners, dict) and winners:
            # Use the most-common winner across methods (stable across replays).
            from collections import Counter

            counts = Counter(winners.values())
            top = counts.most_common(1)[0][0]
            summary["vote_winner"] = str(top)
            summary["n_methods"] = len(winners)
        else:
            summary["vote_winner"] = None
            summary["n_methods"] = 0
        summary["vote_consensus"] = phase_output.get("consensus_rate")
        summary["decides_firsthand"] = bool(
            phase_output.get("governance_decided_firsthand", False)
        )
        summary["degraded"] = bool(phase_output.get("degraded", False))
    # Indexing: count of indexed entries (no content).
    if phase_name == "indexing":
        idx = phase_output.get("indexed_entries", phase_output.get("items", []))
        summary["n_indexed"] = len(idx) if isinstance(idx, list) else 0
        summary["degraded"] = bool(phase_output.get("degraded", False))
    # Quality recheck: same shape as quality_baseline.
    if phase_name == "quality_recheck":
        q = phase_output.get("quality_scores", phase_output.get("scores", []))
        if isinstance(q, list) and q:
            try:
                vals = [
                    float(x.get("score", x.get("value", 0)) if isinstance(x, dict) else x)
                    for x in q
                ]
                summary["quality_recheck_avg"] = round(sum(vals) / len(vals), 3)
            except (TypeError, ValueError):
                summary["quality_recheck_avg"] = None
    return summary


def _merge_state_counts(
    summary: Dict[str, Any],
    state_snapshot: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Overlay aggregate counts from the UnifiedAnalysisState snapshot.

    The state snapshot is a JSON-safe dict (no raw_text) — it carries the
    counts that the pipeline actually persisted. We overlay those counts so
    our observations match the official tracking, not just the phase's own
    (sometimes optimistic) self-report.
    """
    if not isinstance(state_snapshot, dict):
        # Fall back to the phase-only summary; flag the degraded path.
        return {**summary, "_state_overlay": False}
    out = dict(summary)
    overlay_map = {
        "argument_count": "n_arguments",
        "fallacy_count": "n_fallacies",
        "counter_argument_count": "n_counters",
        "jtms_belief_count": "n_beliefs",
    }
    for src_key, dst_key in overlay_map.items():
        val = state_snapshot.get(src_key)
        if isinstance(val, int):
            out[dst_key] = max(int(out.get(dst_key, 0) or 0), val)
    out["_state_overlay"] = True
    return out


def _make_checkpoint_catcher(
    trajectories_holder: Dict[str, List[PhaseObservation]],
    corpus_id: str,
    start_time: float,
) -> Any:
    """Return a ``checkpoint_callback`` that appends per-phase observations.

    Compatible with the signature in ``workflow_dsl.py:465``
    ``checkpoint_callback(results, ctx)``.
    """

    def _cb(results: Dict[str, Any], ctx: Dict[str, Any]) -> None:
        observations: List[PhaseObservation] = trajectories_holder[corpus_id]
        # Snapshot current state counts (overlay source of truth).
        state_snapshot = None
        try:
            state_obj = ctx.get("_state_object") or ctx.get("state")
            if state_obj is not None and hasattr(state_obj, "get_state_snapshot"):
                state_snapshot = state_obj.get_state_snapshot(summarize=True)
        except Exception as exc:  # noqa: BLE001 — defensive: never break the run
            logger.debug("State snapshot failed for %s: %s", corpus_id, exc)
        # Iterate over ALL phase results collected so far (in DAG order).
        # Note: ``results`` is keyed by phase name; we capture EVERY phase
        # in the dict, even if it was completed at a prior checkpoint.
        # We track which ones we've already recorded via the holder list.
        seen_phases = {obs.phase_name for obs in observations}
        for phase_name, phase_result in results.items():
            if phase_name in seen_phases:
                continue
            phase_status = getattr(
                getattr(phase_result, "status", None), "value", "?"
            )
            output = getattr(phase_result, "output", None)
            summary = _summarize_phase_output(phase_name, output)
            merged = _merge_state_counts(summary, state_snapshot)
            # Phase-level degraded marker.
            merged["degraded"] = bool(merged.get("degraded", False)) or bool(
                getattr(phase_result, "error", None)
            )
            merged["phase_status"] = str(phase_status)
            obs = PhaseObservation(
                phase_name=phase_name,
                capability=getattr(phase_result, "capability", "?"),
                phase_status=str(phase_status),
                snapshot=merged,
                state_label=_state_label(merged),
                elapsed_seconds=round(asyncio.get_event_loop().time() - start_time, 3)
                if asyncio.get_event_loop().is_running()
                else 0.0,
            )
            observations.append(obs)

    return _cb


# ---------------------------------------------------------------------------
# TPM construction
# ---------------------------------------------------------------------------


@dataclass
class TPM:
    """Stochastic transition matrix over observed states."""

    states: List[str]
    # transition_counts[from_idx][to_idx] = number of observed transitions.
    transition_counts: List[List[int]]
    n_transitions: int
    n_trajectories: int
    n_observations_total: int
    impossible: bool = False
    impossibility_reason: str = ""

    def as_stochastic_matrix(self) -> List[List[float]]:
        """Row-stochastic matrix P where P[i][j] = Pr(next=j | current=i)."""
        n = len(self.states)
        out: List[List[float]] = [[0.0] * n for _ in range(n)]
        for i, row in enumerate(self.transition_counts):
            total = sum(row)
            if total == 0:
                continue
            for j in range(n):
                out[i][j] = row[j] / total
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "states": list(self.states),
            "transition_counts": [list(r) for r in self.transition_counts],
            "n_transitions": self.n_transitions,
            "n_trajectories": self.n_trajectories,
            "n_observations_total": self.n_observations_total,
            "impossible": self.impossible,
            "impossibility_reason": self.impossibility_reason,
        }


def build_tpm(trajectories: List[Trajectory]) -> TPM:
    """Build a TPM from a list of trajectories.

    Transitions are counted ONLY between consecutive observations of the
    same trajectory (i.e. sequential DAG levels), respecting the per-run
    causal order. Cross-trajectory transitions are not counted (would be
    unphysical — different propositions are independent).
    """
    # First pass: collect distinct states (sorted for reproducibility).
    all_states: set = set()
    n_obs_total = 0
    n_transitions = 0
    for traj in trajectories:
        n_obs_total += len(traj.observations)
        for obs in traj.observations:
            all_states.add(obs.state_label)
        for a, b in zip(traj.observations, traj.observations[1:]):
            if a.state_label != b.state_label:
                n_transitions += 1
            else:
                # Self-loops still count as transitions for stochasticity.
                n_transitions += 1
    states = sorted(all_states)

    # Verdict d'impossibilité : trop peu de signal.
    # Order matters — check the most informative (state-space degenerate)
    # BEFORE the raw count, so a 1-state / 50-obs run is reported with the
    # real reason, not the misleading "insufficient signal".
    if len(states) < 2:
        return TPM(
            states=states,
            transition_counts=[[0] * len(states) for _ in states],
            n_transitions=n_transitions,
            n_trajectories=len(trajectories),
            n_observations_total=n_obs_total,
            impossible=True,
            impossibility_reason=(
                f"degenerate state space: only {len(states)} distinct state(s) "
                f"across {n_obs_total} observations. TPM requires ≥2 distinct "
                f"states (1-state = no transitions to model)."
            ),
        )
    if len(trajectories) < 1 or n_obs_total < 3:
        return TPM(
            states=states,
            transition_counts=[[0] * len(states) for _ in states],
            n_transitions=0,
            n_trajectories=len(trajectories),
            n_observations_total=n_obs_total,
            impossible=True,
            impossibility_reason=(
                f"insufficient signal: {len(trajectories)} trajectories, "
                f"{n_obs_total} observations. Need ≥1 trajectory with ≥3 "
                f"observations to define a transition."
            ),
        )
    if n_transitions < len(states):
        return TPM(
            states=states,
            transition_counts=[[0] * len(states) for _ in states],
            n_transitions=n_transitions,
            n_trajectories=len(trajectories),
            n_observations_total=n_obs_total,
            impossible=True,
            impossibility_reason=(
                f"sparse transitions: {n_transitions} transitions across "
                f"{len(states)} states. Cannot populate a meaningful TPM with "
                f"less than ~1 transition per state."
            ),
        )

    # Second pass: count transitions.
    state_idx = {s: i for i, s in enumerate(states)}
    counts = [[0] * len(states) for _ in states]
    for traj in trajectories:
        for a, b in zip(traj.observations, traj.observations[1:]):
            i = state_idx[a.state_label]
            j = state_idx[b.state_label]
            counts[i][j] += 1
    return TPM(
        states=states,
        transition_counts=counts,
        n_transitions=n_transitions,
        n_trajectories=len(trajectories),
        n_observations_total=n_obs_total,
        impossible=False,
    )


# ---------------------------------------------------------------------------
# Ergodicity analysis (TPM-2 #1491)
# ---------------------------------------------------------------------------
#
# A Markov chain is **ergodic** iff it is irreducible (1 strongly connected
# component) AND aperiodic (gcd of return-periods = 1). For an irreducible
# aperiodic chain, the stationary distribution exists, is unique, and is the
# limit distribution (i.e. predictive). For a reducible chain (multiple SCCs
# or weakly-connected components), no unique stationary distribution exists
# — the chain depends on initial state and converges to a class-dependent
# mixture.
#
# TPM-2 #1491 DoD asks for an **ergodicity verdict**, falsifiable: either
# the chain is irreducible (→ stationary calculable, report top-k) OR
# reducible (→ honest verdict "N SCC / M WCC, no unique stationary",
# still a valid result, anti-théâtre #1019).
#
# Implementation: scipy.sparse.csgraph.connected_components on the
# row-stochastic matrix P (transitions counted, regardless of probability).
# If scipy is unavailable, returns a soft-fail dict (analysis skipped,
# reason written) — the TPM itself remains usable for transition analysis
# even when stationary cannot be computed.


@dataclass
class ErgodicityResult:
    """Ergodicity analysis of a TPM (TPM-2 #1491)."""

    n_scc: int
    n_wcc: int
    ergodic: bool
    irreducible: bool
    aperiodic: Optional[bool]
    stationary: Optional[Dict[str, float]]
    analysis_skipped: bool
    skip_reason: Optional[str]


def _analyze_ergodicity(tpm: TPM) -> ErgodicityResult:
    """Classify a TPM by ergodicity (SCC + WCC analysis).

    Returns an ``ErgodicityResult``. If the TPM is impossible, returns a
    sentinel ``n_scc=0/n_wcc=0`` and ``analysis_skipped=True``.
    """
    if tpm.impossible or not tpm.states:
        return ErgodicityResult(
            n_scc=0,
            n_wcc=0,
            ergodic=False,
            irreducible=False,
            aperiodic=None,
            stationary=None,
            analysis_skipped=True,
            skip_reason="TPM impossible: ergodicity undefined on degenerate state space",
        )
    try:
        import numpy as np  # type: ignore
        from scipy.sparse import csr_matrix  # type: ignore
        from scipy.sparse.csgraph import connected_components  # type: ignore
    except ImportError as exc:  # pragma: no cover — scipy is a soft dep
        return ErgodicityResult(
            n_scc=-1,
            n_wcc=-1,
            ergodic=False,
            irreducible=False,
            aperiodic=None,
            stationary=None,
            analysis_skipped=True,
            skip_reason=f"scipy/numpy unavailable: {exc}",
        )

    n = len(tpm.states)
    counts = np.asarray(tpm.transition_counts, dtype=float)
    # Connected components on the BINARY support (any non-zero transition
    # counts as a directed graph edge). ``directed=True`` is REQUIRED for
    # ``connection="strong"``: with ``directed=False`` scipy ignores the
    # ``connection`` argument and computes WEAK components for both calls,
    # so ``n_scc`` silently measured WCC (TPM-2 #1491 ergodicity bug).
    support = (counts > 0).astype(int)
    graph = csr_matrix(support)
    n_scc, scc_labels = connected_components(graph, directed=True, connection="strong")
    n_wcc, wcc_labels = connected_components(graph, directed=True, connection="weak")

    irreducible = n_scc == 1
    # Aperiodicity check: gcd of return-periods to each state. With limited
    # N (≤ a few hundred obs), we approximate: a state is aperiodic iff
    # its self-loop count > 0 (period 1). If ALL states have self-loops,
    # the chain is aperiodic; else we report None (insufficient evidence).
    aperiodic_states = [
        int(counts[i, i] > 0) for i in range(n)
    ]
    if all(aperiodic_states):
        aperiodic_flag = True
    elif not any(aperiodic_states):
        aperiodic_flag = False
    else:
        aperiodic_flag = None  # mixed evidence → conservative "unknown"

    ergodic = irreducible and (aperiodic_flag is True)
    stationary = None
    if ergodic:
        # Solve Pi * P = Pi with sum(Pi)=1 → eigenvector of P^T with
        # eigenvalue 1. Use the stochastic matrix (row-normalized).
        try:
            row_sums = counts.sum(axis=1)
            # Avoid division by zero (no row should be zero — impossible
            # verdict would have caught that earlier).
            inv = np.where(row_sums > 0, 1.0 / row_sums, 0.0)
            P = counts * inv[:, None]
            # Solve (P^T - I) Pi = 0 with sum=1 constraint via least-squares.
            A = P.T - np.eye(n)
            # Add a "sum=1" row to break the nullspace into a unique solution.
            A_aug = np.vstack([A, np.ones(n)])
            b_aug = np.concatenate([np.zeros(n), np.array([1.0])])
            pi, *_ = np.linalg.lstsq(A_aug, b_aug, rcond=None)
            # Normalize (numerical hygiene).
            pi = np.clip(pi, 0.0, None)
            total = pi.sum()
            if total > 0:
                pi = pi / total
            # Top-3 states by stationary mass.
            top_idx = np.argsort(-pi)[:3]
            stationary = {
                tpm.states[int(i)]: float(pi[int(i)])
                for i in top_idx
                if pi[int(i)] > 0
            }
        except Exception as exc:  # pragma: no cover — numerical edge cases
            stationary = None

    return ErgodicityResult(
        n_scc=int(n_scc),
        n_wcc=int(n_wcc),
        ergodic=bool(ergodic),
        irreducible=bool(irreducible),
        aperiodic=aperiodic_flag,
        stationary=stationary,
        analysis_skipped=False,
        skip_reason=None,
    )


# ---------------------------------------------------------------------------
# Source: demo 5-propositions
# ---------------------------------------------------------------------------


def _load_demo5_propositions() -> Dict[str, Dict[str, str]]:
    """Load the 5-proposition synthetic bundle from the demo driver."""
    demo_dir = (
        Path(__file__).resolve().parent.parent
        / "examples"
        / "democratech_deliberation"
    )
    if not (demo_dir / "synthetic_proposals.py").exists():
        raise FileNotFoundError(
            f"Demo bundle not found at {demo_dir}. "
            "Re-run from the repo root or pass --source custom."
        )
    sys.path.insert(0, str(demo_dir))
    try:
        from synthetic_proposals import get_propositions  # type: ignore
    finally:
        # Don't pop sys.path — other modules in the bundle may import it too.
        pass
    return get_propositions()


# ---------------------------------------------------------------------------
# Source: real corpora A/B/C (TPM-2 #1491)
# ---------------------------------------------------------------------------
#
# PRIVACY HARD #1491:
# - The real corpus is Fernet-encrypted. We decrypt IN-MEMORY only via
#   the dedicated privacy-aware helper module, never persist plaintext.
# - This script body NEVER references the encrypted dataset path or the
#   passphrase env var (those live in scripts/_tpm_corpus_loader.py).
# - The only persistent artifact is aggregate counts (LIGHT) written under
#   evaluation/results/tpm_extraction/ (gitignored).
# - IDs are OPAQUE (corpus_A, prop_<hash8>, arg_<i>) on all surfaces.
#
# The 3 corpora (A/B/C) are derived from the same encrypted dataset by
# partition: A = first third, B = middle third, C = last third (alphabetical
# source-id sort — stable run-to-run with LLM_CACHE_MODE=replay). The split
# is intentionally coarse so each corpus has enough propositions for a
# stochastic TPM (≥3 obs per state pair minimum).


def _load_corpus_propositions(corpus_id: str) -> Dict[str, Dict[str, str]]:
    """Delegate to the privacy-aware corpus loader (TPM-2 #1491).

    The loader lives in ``scripts/_tpm_corpus_loader.py`` so the script body
    itself stays free of any reference to the encrypted dataset path, the
    passphrase env var, or the corpus file extension (preserves the TPM-1
    static privacy contract).
    """
    repo_root = Path(__file__).resolve().parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        from _tpm_corpus_loader import load_corpus_propositions  # type: ignore
    except ImportError as exc:  # pragma: no cover — adjacent module
        raise ImportError(
            f"TPM-2 corpus loader unavailable: {exc}. "
            "Ensure scripts/_tpm_corpus_loader.py is present."
        ) from exc
    return load_corpus_propositions(corpus_id)


# ---------------------------------------------------------------------------
# Run a single proposition through the pipeline
# ---------------------------------------------------------------------------


async def _run_one(
    corpus_id: str,
    corpus_label: str,
    text: str,
    registry: Any,
    trajectories_holder: Dict[str, List[PhaseObservation]],
    max_wall_seconds: float,
) -> Trajectory:
    """Run ``run_deliberation`` on one proposition, capturing trajectories.

    Uses ``checkpoint_callback`` (already supported by ``run_unified_analysis``,
    workflow_dsl.py:465) — NO new instrumentation in the pipeline.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )
    from argumentation_analysis.workflows.democratech import (
        build_democratech_workflow,
    )

    start_time = (
        asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0.0
    )
    trajectories_holder[corpus_id] = []
    catcher = _make_checkpoint_catcher(trajectories_holder, corpus_id, start_time)

    traj = Trajectory(corpus_id=corpus_id, corpus_label=corpus_label)
    try:
        # Use run_unified_analysis directly (run_deliberation does not
        # accept checkpoint_callback). build_democratech_workflow is the
        # pre-existing public helper — no pipeline modification.
        workflow = build_democratech_workflow()
        coro = run_unified_analysis(
            text=text,
            workflow_name="democratech",
            registry=registry,
            custom_workflow=workflow,
            create_state=True,
            checkpoint_callback=catcher,
        )
        # Wrap the run with a wall-clock cap (fail-loud on breach).
        result = await asyncio.wait_for(coro, timeout=max_wall_seconds)
        # ``result`` is the dict from run_unified_analysis; we don't need it
        # for TPM construction (captured via checkpoint), but we keep a
        # reference for any post-hoc diagnostic in the report.
        traj.observations = list(trajectories_holder.get(corpus_id, []))
        traj.total_elapsed_seconds = round(
            (asyncio.get_event_loop().time() - start_time), 3
        )
    except asyncio.TimeoutError:
        traj.terminated_by_budget = True
        traj.error = f"wall-budget breach (>{max_wall_seconds:g}s)"
        traj.observations = list(trajectories_holder.get(corpus_id, []))
    except Exception as exc:  # noqa: BLE001 — surface, never swallow
        traj.error = f"{type(exc).__name__}: {exc}"
        traj.observations = list(trajectures_holder.get(corpus_id, []))
    return traj


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _render_markdown_report(
    trajectories: List[Trajectory],
    tpm: TPM,
    source_label: str,
    output_dir: Path,
) -> str:
    """Produce a short, honest, human-readable report."""
    lines: List[str] = []
    is_real_corpus = "corpus" in source_label.lower() and "real" in source_label.lower()
    title = (
        "# TPM-2 #1491 — Trajectoires d'états de croyance → TPM + ergodicité (corpus réel)"
        if is_real_corpus
        else "# TPM-1 #1489 — Trajectoires d'états de croyance → TPM"
    )
    lines.append(title)
    lines.append("")
    lines.append(f"- Source : `{source_label}`")
    lines.append(f"- Workflow : `democratech` (10 phases)")
    lines.append(f"- Trajectoires : **{tpm.n_trajectories}**")
    lines.append(f"- Observations totales : **{tpm.n_observations_total}**")
    lines.append(f"- Transitions observées : **{tpm.n_transitions}**")
    lines.append(f"- Taille espace d'états : **{len(tpm.states)}**")
    lines.append(f"- Output dir : `{output_dir}`")
    lines.append("")
    lines.append("## Espace d'états")
    lines.append("")
    lines.append(
        "Vecteur d'état = `(phase_status, n_arguments_bucket, n_fallacies_bucket, "
        "n_counters_bucket, n_beliefs_bucket, vote_winner+consensus)`. Pas de "
        "verbatim, pas de raw_text, IDs opaques (privacy HARD)."
    )
    lines.append("")
    lines.append("| # | State label |")
    lines.append("|---|-------------|")
    for i, s in enumerate(tpm.states):
        lines.append(f"| {i} | `{s}` |")
    lines.append("")

    if tpm.impossible:
        lines.append("## Verdict d'impossibilité")
        lines.append("")
        lines.append(f"**Raison** : {tpm.impossibility_reason}")
        lines.append("")
        lines.append(
            "C'est un résultat **VALIDE** (gate dur #1489 : TPM réelle OU "
            "verdict écrit). Re-scope possible : augmenter N propositions, "
            "élargir l'espace d'états (granularité plus fine), ou choisir "
            "un autre workflow avec plus de phases génératives."
        )
        return "\n".join(lines) + "\n"

    lines.append("## TPM (matrice stochastique par ligne)")
    lines.append("")
    stochastic = tpm.as_stochastic_matrix()
    # Header row.
    header = "| from \\\\ to |" + "|".join(f" `{i}`" for i in range(len(tpm.states))) + "|"
    sep = "|---|" + "|".join("---" for _ in tpm.states) + "|"
    lines.append(header)
    lines.append(sep)
    for i, row in enumerate(stochastic):
        cells = []
        for v in row:
            if v == 0.0:
                cells.append("·")
            else:
                cells.append(f"{v:.2f}")
        lines.append(f"| `{i}` {tpm.states[i][:40]} |" + "|".join(f" {c} " for c in cells) + "|")
    lines.append("")
    lines.append("## Comptes bruts (transitions observées)")
    lines.append("")
    lines.append(header)
    lines.append(sep)
    for i, row in enumerate(tpm.transition_counts):
        cells = [str(v) if v else "·" for v in row]
        lines.append(f"| `{i}` {tpm.states[i][:40]} |" + "|".join(f" {c} " for c in cells) + "|")
    lines.append("")

    # --- Ergodicité (TPM-2 #1491) ---
    ergo = _analyze_ergodicity(tpm)
    lines.append("## Analyse d'ergodicité (TPM-2 #1491)")
    lines.append("")
    if ergo.analysis_skipped:
        lines.append(
            f"- **Skipped** : `{ergo.skip_reason}` "
            "(TPM reste exploitable pour les transitions inter-phases)."
        )
    else:
        lines.append(f"- SCC (composantes fortement connexes) : **{ergo.n_scc}**")
        lines.append(f"- WCC (composantes faiblement connexes) : **{ergo.n_wcc}**")
        lines.append(f"- Irréductible : **{ergo.irreducible}** ({ergo.n_scc} SCC)")
        lines.append(
            f"- Apériodique : **{ergo.aperiodic}** "
            "(heuristique self-loop : None = évidence mixte sur N petit)."
        )
        if ergo.irreducible and ergo.aperiodic is True:
            lines.append(f"- **Ergodique** : **OUI** — distribution stationnaire unique.")
        elif ergo.irreducible and ergo.aperiodic is False:
            lines.append(
                "- **Ergodique** : **NON** — irréductible mais périodique "
                "(gcd return-period > 1)."
            )
        elif ergo.irreducible:
            # Irreducible (1 SCC) but aperiodicity undetermined (aperiodic is
            # None — mixed self-loop evidence on small N). Do NOT claim
            # "réductible" here: that contradicts the 1-SCC verdict just above.
            lines.append(
                "- **Ergodique** : **indéterminé** — irréductible (1 SCC) mais "
                "apériodicité indéterminée sur N petit ; ergodicité non "
                "conclue (pas de distribution stationnaire garantie)."
            )
        else:
            lines.append(
                "- **Ergodique** : **NON** — réductible (≥2 SCC), "
                "pas de distribution stationnaire unique."
            )
        if ergo.stationary:
            lines.append("")
            lines.append("### Distribution stationnaire (top-3)")
            lines.append("")
            lines.append("| State | Pi |")
            lines.append("|-------|----|")
            for state, pi in ergo.stationary.items():
                lines.append(f"| `{state}` | {pi:.4f} |")
            lines.append("")
        elif ergo.irreducible:
            lines.append(
                "- Stationnaire : non-calculé (irréductible mais apériodicité "
                "inconnue ou non-triviale)."
            )
    lines.append("")

    lines.append("## Trajectoires par corpus")
    lines.append("")
    for traj in trajectories:
        lines.append(f"### {traj.corpus_id} — {traj.corpus_label}")
        lines.append("")
        if traj.error:
            lines.append(f"- **Erreur** : `{traj.error}`")
        if traj.terminated_by_budget:
            lines.append("- **Budget** : wall-clock breach — observations partielles")
        lines.append(f"- Observations : **{len(traj.observations)}**")
        lines.append(f"- Wall-clock : {traj.total_elapsed_seconds:.1f}s")
        lines.append("")
        lines.append("| Phase | Status | State |")
        lines.append("|-------|--------|-------|")
        for obs in traj.observations:
            state_short = obs.state_label.replace("|", "\\|")
            lines.append(f"| `{obs.phase_name}` | {obs.phase_status} | `{state_short}` |")
        lines.append("")

    lines.append("## Limites honnêtes")
    lines.append("")
    lines.append(
        f"- {tpm.n_trajectories} trajectoires × {tpm.n_observations_total // max(tpm.n_trajectories, 1)} "
        f"observations/trajectoire en moyenne → matrice peu profonde "
        f"(peu de transitions par paire d'états)."
    )
    lines.append(
        f"- Espace d'états compact ({len(tpm.states)} états) issu du bucketing "
        "coarse : choix délibéré pour stabiliser les comptes sur N petit."
    )
    lines.append(
        "- Déterminisme replay-cache : à valider par 2 runs → même TPM "
        "(cross-review po-2025)."
    )
    lines.append(
        "- Pas de sur-instrumentation pipeline : utilise UNIQUEMENT "
        "``checkpoint_callback`` (déjà supporté par ``run_unified_analysis``) "
        "+ ``UnifiedAnalysisState.get_state_snapshot`` (déjà implémenté)."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    )


def _ensure_api_key() -> Optional[str]:
    """Return the active LLM provider name, or None if absent (skip run)."""
    from dotenv import load_dotenv

    load_dotenv()
    if os.environ.get("OPENROUTER_API_KEY") and os.environ.get("OPENROUTER_BASE_URL"):
        return "openrouter"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract belief-state trajectories from the democratech pipeline "
            "and derive a TPM (Track TPM-1 #1489)."
        ),
    )
    parser.add_argument(
        "--source",
        choices=("demo5", "corpusA", "corpusB", "corpusC"),
        default="demo5",
        help=(
            "Source corpus. demo5 = synthetic 5-propositions (default). "
            "corpusA/B/C = real corpora (TPM-2 #1491), decrypted in-memory "
            "via the dedicated privacy-aware loader. Opaque IDs only."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to the first N propositions (default: all).",
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation/results/tpm_extraction",
        help="Output directory (default: gitignored evaluation/results/tpm_extraction).",
    )
    parser.add_argument(
        "--max-wall-seconds",
        type=float,
        default=300.0,
        help="Per-proposition wall-clock cap (default: 300s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print contract + state-space definition only, no LLM call.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    _setup_logging(args.verbose)

    if args.dry_run:
        # Print the contract so a reader can verify the state-space choice
        # BEFORE running anything.
        print("=" * 72)
        if args.source in ("corpusA", "corpusB", "corpusC"):
            print(" TPM-2 #1491 — Dry-run contract (corpus réel, IDs opaques)")
        else:
            print(" TPM-1 #1489 — Dry-run contract")
        print("=" * 72)
        print(f"Source : {args.source}")
        print(f"Output dir : {args.output_dir}")
        print(f"State-space buckets :")
        print(f"  args    = {[b[2] for b in _ARG_BUCKETS]}")
        print(f"  fall    = {[b[2] for b in _FALLACY_BUCKETS]}")
        print(f"  counters = {[b[2] for b in _COUNTER_BUCKETS]}")
        print(f"  beliefs = {[b[2] for b in _BELIEF_BUCKETS]}")
        print(f"State label = '<status>:args<bucket>:fall<bucket>:ctr<bucket>:bel<bucket>:vote<...>'")
        print("Privacy: no raw_text, no corpus, opaque IDs on all surfaces.")
        print("Pipeline hooks used: checkpoint_callback + state.get_state_snapshot (both pre-existing).")
        return 0

    provider = _ensure_api_key()
    if not provider:
        print(
            "No LLM API key found (OPENAI_API_KEY or OPENROUTER_*). "
            "The TPM extractor needs a real LLM to capture trajectories. "
            "Use --dry-run to inspect the contract without running.",
            file=sys.stderr,
        )
        return 2

    # Resolve the corpus source.
    if args.source == "demo5":
        props = _load_demo5_propositions()
        source_label = "demo5 (synthetic 5-propositions, examples/democratech_deliberation)"
    elif args.source in ("corpusA", "corpusB", "corpusC"):
        corpus_letter = args.source[-1]  # 'A' / 'B' / 'C'
        props = _load_corpus_propositions(corpus_letter)
        source_label = (
            f"corpus{corpus_letter} (real encrypted dataset, {len(props)} propositions, "
            f"loaded in-memory via privacy-aware helper, opaque IDs)"
        )
    else:  # pragma: no cover — guarded by argparse choices
        raise ValueError(f"Unknown source: {args.source}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build a registry (per BO-4 #1480 lesson: setup_registry(include_optional=True)).
    from argumentation_analysis.orchestration.unified_pipeline import setup_registry

    registry = setup_registry(include_optional=True)

    # Run the pipeline for each proposition.
    trajectories: List[Trajectory] = []
    holder: Dict[str, List[PhaseObservation]] = {}

    async def _run_all() -> None:
        items = list(props.items())
        if args.limit is not None and args.limit > 0:
            items = items[: args.limit]
        for pid, meta in items:
            print(f"→ Extracting trajectory for {pid} ({meta['label']}) …", flush=True)
            traj = await _run_one(
                corpus_id=pid,
                corpus_label=meta["label"],
                text=meta["text"],
                registry=registry,
                trajectories_holder=holder,
                max_wall_seconds=args.max_wall_seconds,
            )
            trajectories.append(traj)
            status = "OK" if not traj.error else f"ERR ({traj.error[:60]})"
            print(
                f"   {traj.corpus_id}: {len(traj.observations)} obs, "
                f"{traj.total_elapsed_seconds:.1f}s — {status}",
                flush=True,
            )

    asyncio.run(_run_all())

    # Build TPM and report.
    tpm = build_tpm(trajectories)

    # Persist JSON + Markdown report.
    json_path = output_dir / "tpm.json"
    md_path = output_dir / "report.md"
    trajectories_payload = [
        {
            "corpus_id": t.corpus_id,
            "corpus_label": t.corpus_label,
            "workflow_name": t.workflow_name,
            "total_elapsed_seconds": t.total_elapsed_seconds,
            "terminated_by_budget": t.terminated_by_budget,
            "error": t.error,
            "observations": [
                {
                    "phase_name": o.phase_name,
                    "capability": o.capability,
                    "phase_status": o.phase_status,
                    "state_label": o.state_label,
                    "elapsed_seconds": o.elapsed_seconds,
                    "snapshot": o.snapshot,
                }
                for o in t.observations
            ],
        }
        for t in trajectories
    ]
    payload = {
        "source": source_label,
        "n_trajectories": tpm.n_trajectories,
        "n_observations_total": tpm.n_observations_total,
        "n_transitions": tpm.n_transitions,
        "n_states": len(tpm.states),
        "impossible": tpm.impossible,
        "impossibility_reason": tpm.impossibility_reason,
        "tpm": tpm.to_dict(),
        "trajectories": trajectories_payload,
    }
    json_path.write_text(
        json.dumps(payload, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path.write_text(
        _render_markdown_report(trajectories, tpm, source_label, output_dir),
        encoding="utf-8",
    )
    print()
    print(f"→ TPM : {len(tpm.states)} états, {tpm.n_transitions} transitions, "
          f"{tpm.n_trajectories} trajectoires")
    if tpm.impossible:
        print(f"→ VERDICT D'IMPOSSIBILITÉ : {tpm.impossibility_reason}")
    print(f"→ JSON  : {json_path}")
    print(f"→ Report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
