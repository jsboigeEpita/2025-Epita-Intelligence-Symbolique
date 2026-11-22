#!/usr/bin/env python3
"""Track S6-A1 #1506 — CoursIA strate-6 Phase-A grounding (candidate substrate #2).

For each real corpus (corpusA / corpusB / corpusC, decrypted in-memory via
``scripts/_tpm_corpus_loader.py``), this driver:

1. **Subprocesses** ``scripts/extract_belief_trajectories.py --source
   corpusX`` (TPM-1/2 machinery, anti-pendule: no re-implementation of the
   pipeline). Writes a deterministic ``tpm.json`` per corpus, containing
   ``states`` + ``transition_counts`` + ergodicity verdict (TPM-2 #1491).
2. **Reads** the produced JSON.
3. **Adds the spectral-gap and entropy-production legs** (R664 / R1107 —
   ``np.linalg.eigvals`` and the stationary entropy production on the
   row-stochastic matrix; the gap is a mixing rate only when the chain is
   irreducible).
4. **Emits** the S6-A1 verdict (``verdict.json`` + ``verdict.md``) under
   ``evaluation/results/strate6_phaseA/corpusX/`` (gitignored).

Privacy HARD: identical contract to TPM-1/2 — no raw_text, no source name,
opaque ``prop_<8hex>`` IDs, decrypt in-memory only. Verdict files do not
persist the corpus text.

Candidate #2 for CoursIA seed [#7289](https://github.com/jsboige/CoursIA/issues/7289)
("the transition matrix over *belief states*"), independently from sibling
candidate #1 ("labelling trajectory", S6-A2 PR #1509). Two substrates are
the ≥2 independent falsifiability substrates required by contract
[#7291](https://github.com/jsboige/CoursIA/issues/7291).

Usage::

    # Inspect the contract + candidate mapping without running:
    python scripts/coursia_strate6_phaseA_grounding.py --dry-run

    # Generate verdicts for all 3 real corpora (in-memory decrypt only):
    python scripts/coursia_strate6_phaseA_grounding.py

    # Single corpus + custom output dir:
    python scripts/coursia_strate6_phaseA_grounding.py --corpus A \\
        --output-dir evaluation/results/strate6_phaseA/manual_A
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("S6-A1")


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR_SCRIPT = REPO_ROOT / "scripts" / "extract_belief_trajectories.py"

# Default output root (gitignored — see repo .gitignore).
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "evaluation" / "results" / "strate6_phaseA"

# In-memory scratch for the inner TPM extractor (gitignored).
INNER_TPM_ROOT = REPO_ROOT / "evaluation" / "results" / "strate6_phaseA" / "_inner_tpm"

# Corpus → CoursIA seed candidate mapping (issue #7289 requires ≥2
# independent substrates; this driver delivers candidate #2).
COURSIA_SEED_ISSUE = "jsboige/CoursIA#7289"
COURSIA_FALSIFIABILITY_CONTRACT = "jsboige/CoursIA#7291"

CANDIDATES_FOR_SEED = [
    {
        "id": "candidate_1_labelling_trajectory",
        "delivered_in": "PR #1509 (MERGED)",
        "scope": "Dung labelling trajectory under sequential argument arrival "
        "(refutation + reinstatement dynamics over symbolic states).",
        "engine": "argumentation_analysis.orchestration.dung_labelling_trajectory",
        "data_substrate": "synthetic opaque discourse exemplar (privacy HARD)",
        "this_driver_delivers": False,
    },
    {
        "id": "candidate_2_belief_state_tpm",
        "delivered_in": "this driver (S6-A1, PR pending)",
        "scope": "Stochastic transition matrix over *belief states* extracted "
        "from real corpus propositions via the democratech pipeline. "
        "Verdict: structured ergodicity + spectral gap (R664) + entropy "
        "production (R1107).",
        "engine": "scripts.extract_belief_trajectories + this driver",
        "data_substrate": "real corpus (corpusA / corpusB / corpusC) "
        "decrypted in-memory via _tpm_corpus_loader",
        "this_driver_delivers": True,
    },
]


# ---------------------------------------------------------------------------
# Spectral gap refinement (R664 — anti-pendule: small helper, not a duplicate
# of _analyze_ergodicity in scripts/extract_belief_trajectories.py).
# ---------------------------------------------------------------------------


@dataclass
class SpectralResult:
    """Spectral refinement of an irreducible stochastic matrix.

    Notes
    -----
    The spectral gap is defined as ``1 - |lambda_2|`` where ``lambda_2`` is
    the second-largest-magnitude eigenvalue of the row-stochastic matrix
    ``P``. It refines the "irreducible" verdict from
    :func:`scripts.extract_belief_trajectories._analyze_ergodicity` with a
    quantitative rate of convergence toward the (would-be) stationary
    distribution:

    - gap → 1 : fast mixing (chain converges in O(log 1/eps) steps),
    - gap → 0 : slow / non-mixing (block-diagonal structure or near-zero
      off-diagonal mass).

    The helper is *strictly an addition*: it does NOT modify the upstream
    TPM-2 verdict, only refines it.
    """

    n: int
    eigenvalues_abs: List[float]
    spectral_gap: Optional[float]
    second_largest_abs: Optional[float]
    analysis_skipped: bool
    skip_reason: Optional[str] = None


def spectral_gap(stochastic_matrix: List[List[float]]) -> SpectralResult:
    """Compute the spectral gap of a row-stochastic matrix.

    Parameters
    ----------
    stochastic_matrix
        Square row-stochastic matrix (``P[i][j] = Pr(next=j | current=i)``)
        as a list of lists of floats. The shape is preserved from
        :meth:`scripts.extract_belief_trajectories.TPM.as_stochastic_matrix`.

    Returns
    -------
    SpectralResult
        Always returned (never raises). If numpy is unavailable or the
        input is degenerate, ``analysis_skipped=True`` with a reason. The
        eigenvalues are sorted by decreasing absolute magnitude.
    """
    n = len(stochastic_matrix)
    if n < 2:
        return SpectralResult(
            n=n,
            eigenvalues_abs=[],
            spectral_gap=None,
            second_largest_abs=None,
            analysis_skipped=True,
            skip_reason=f"degenerate matrix (n={n} < 2)",
        )
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover — numpy is a soft dep
        return SpectralResult(
            n=n,
            eigenvalues_abs=[],
            spectral_gap=None,
            second_largest_abs=None,
            analysis_skipped=True,
            skip_reason=f"numpy unavailable: {exc}",
        )

    P = np.asarray(stochastic_matrix, dtype=float)
    if P.shape != (n, n):
        return SpectralResult(
            n=n,
            eigenvalues_abs=[],
            spectral_gap=None,
            second_largest_abs=None,
            analysis_skipped=True,
            skip_reason=f"non-square shape: {P.shape}",
        )

    # Eigenvalues of P (full spectrum — n is small for our state spaces).
    eigs = np.linalg.eigvals(P)
    # Sort by decreasing absolute magnitude.
    order = np.argsort(-np.abs(eigs))
    eigs_sorted = eigs[order]
    abs_sorted = [float(abs(e)) for e in eigs_sorted]

    # Top eigenvalue of a row-stochastic matrix is 1 (Perron-Frobenius).
    # Spectral gap = 1 - |lambda_2|.
    if len(abs_sorted) < 2:
        return SpectralResult(
            n=n,
            eigenvalues_abs=abs_sorted,
            spectral_gap=None,
            second_largest_abs=None,
            analysis_skipped=True,
            skip_reason="fewer than 2 eigenvalues",
        )
    top1 = abs_sorted[0]
    lambda2 = abs_sorted[1]
    # Numerical hygiene: if top1 drifts below 1.0 (small N), re-normalize.
    gap = 1.0 - lambda2
    if top1 < 0.999:
        # Re-normalize: gap defined relative to actual dominant |lambda|.
        gap = top1 - lambda2

    return SpectralResult(
        n=n,
        eigenvalues_abs=abs_sorted,
        spectral_gap=float(gap),
        second_largest_abs=float(lambda2),
        analysis_skipped=False,
    )


# ---------------------------------------------------------------------------
# Entropy production (#1506 R1107 — the third discrimination quantity)
# ---------------------------------------------------------------------------


def ergodicity_from_matrix(stochastic_matrix: List[List[float]]) -> Dict[str, Any]:
    """Derive structural ergodicity without scraping the rendered report.

    The inner extractor owns the graph analysis.  This adapter rebuilds its
    already-delivered ``TPM`` from the transition probabilities, preserving
    their support and the self-loop evidence used by its aperiodicity
    heuristic.  A periodic chain may still have a unique stationary
    distribution; ``ergodic`` deliberately keeps the extractor's stricter
    irreducible-and-aperiodic meaning.
    """
    from scripts.extract_belief_trajectories import TPM, _analyze_ergodicity

    counts = [[int(value > 0.0) for value in row] for row in stochastic_matrix]
    tpm = TPM(
        states=[f"state_{i}" for i in range(len(stochastic_matrix))],
        transition_counts=counts,
        n_transitions=sum(sum(row) for row in counts),
        n_trajectories=1,
        n_observations_total=sum(sum(row) for row in counts) + 1,
    )
    result = _analyze_ergodicity(tpm)
    return asdict(result)


@dataclass
class EntropyProductionResult:
    """Entropy-production rate of a stationary finite Markov chain."""

    n: int
    sigma: Optional[float]
    stationary: Optional[List[float]]
    irreducible: bool
    one_way_pairs: int
    analysis_skipped: bool
    skip_reason: Optional[str] = None


def entropy_production(stochastic_matrix: List[List[float]]) -> EntropyProductionResult:
    """Compute ``sigma = sum(pi_i * P_ij * ln(P_ij / P_ji))``.

    ``pi`` is a stationary distribution.  The computation requires it to be
    unique: that also covers a reducible chain with one recurrent class and
    transient states.  Aperiodicity is not required (the four-state periodic
    reference ring still has the uniform stationary distribution).
    Forward-only pairs contribute ``+inf`` and are counted explicitly.  With
    several recurrent classes no occupancy surrogate is substituted for the
    missing unique stationary reference.
    """
    n = len(stochastic_matrix)
    empty = EntropyProductionResult(
        n=n,
        sigma=None,
        stationary=None,
        irreducible=False,
        one_way_pairs=0,
        analysis_skipped=True,
    )
    if n < 2:
        empty.skip_reason = f"degenerate matrix (n={n} < 2)"
        return empty
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover — numpy is a soft dep
        empty.skip_reason = f"numpy unavailable: {exc}"
        return empty

    P = np.asarray(stochastic_matrix, dtype=float)
    if (
        P.shape != (n, n)
        or not np.all(np.isfinite(P))
        or np.any(P < 0.0)
        or not np.allclose(P.sum(axis=1), 1.0, atol=1e-9)
    ):
        empty.skip_reason = (
            "expected a finite, non-negative row-stochastic square matrix"
        )
        return empty

    ergodicity = ergodicity_from_matrix(stochastic_matrix)
    empty.irreducible = bool(ergodicity.get("irreducible", False))
    if ergodicity.get("analysis_skipped"):
        empty.skip_reason = str(
            ergodicity.get("skip_reason") or "ergodicity unavailable"
        )
        return empty

    # pi P = pi, sum(pi) = 1.  Append the normalisation constraint and check
    # the original stationary equations explicitly below.
    system = np.vstack([P.T - np.eye(n), np.ones(n)])
    target = np.concatenate([np.zeros(n), [1.0]])
    pi, *_ = np.linalg.lstsq(system, target, rcond=None)
    if not np.all(np.isfinite(pi)) or abs(float(pi.sum())) < 1e-12:
        empty.skip_reason = "stationary solve did not produce a valid distribution"
        return empty
    pi = np.clip(pi, 0.0, None)
    pi /= pi.sum()
    empty.stationary = [float(value) for value in pi]

    # Rank(πP − π) = n − 1 iff the stationary distribution is unique.  A
    # reducible chain with one recurrent class passes; two recurrent classes
    # do not.  The sum constraint is redundant whenever this rank is full.
    if int(np.linalg.matrix_rank(P.T - np.eye(n), tol=1e-8)) != n - 1:
        empty.skip_reason = (
            "no unique stationary distribution (several recurrent classes)"
        )
        return empty

    sigma = 0.0
    one_way_pairs = 0
    for i in range(n):
        for j in range(n):
            forward = float(P[i, j])
            reverse = float(P[j, i])
            mass = float(pi[i]) * forward
            # A transient state's stationary mass is exactly 0; the least-
            # squares solve leaves ~1e-17 there.  That numerical dust must not
            # turn a zero-mass one-way edge into sigma = +inf.
            if mass <= 1e-12:
                continue
            if reverse == 0.0:
                one_way_pairs += 1
                continue
            sigma += mass * math.log(forward / reverse)
    if one_way_pairs:
        empty.stationary = [float(value) for value in pi]
        empty.one_way_pairs = one_way_pairs
        empty.skip_reason = (
            f"entropy production is +inf: {one_way_pairs} one-way transition pair(s)"
        )
        return empty

    return EntropyProductionResult(
        n=n,
        sigma=float(max(sigma, 0.0) if abs(sigma) < 1e-12 else sigma),
        stationary=[float(value) for value in pi],
        irreducible=bool(ergodicity.get("irreducible", False)),
        one_way_pairs=0,
        analysis_skipped=False,
    )


# ---------------------------------------------------------------------------
# What the state space actually carries (#1506 R1107)
# ---------------------------------------------------------------------------

#: The snapshot fields the inner extractor folds into its state label —
#: ``<phase status>:args<bucket>:fall<bucket>:ctr<bucket>:bel<bucket>:vote<…>``.
_BELIEF_STATE_COORDINATES = ("n_arguments", "n_fallacies", "n_counters", "n_beliefs")


def belief_state_coverage(tpm_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Whether the state space carries BELIEF information at all.

    A state label has five coordinates: the phase status word, the four
    bucketed counts (arguments, fallacies, counter-arguments, beliefs), and the
    vote. When every observation shows **0** in all four counts, the only
    varying coordinate is the phase status word — the transition matrix then
    counts ``completed`` / ``failed`` / ``skipped`` transitions, and the
    candidate's thesis (a chain over *belief states*) is not measured at all.

    This is not hypothetical. Measured on ``main`` (2026-10-23) under the
    zero-spend ``LLM_CACHE_MODE=replay``: the ``extract`` phase fails on every
    proposition with a replay cache miss, everything downstream is skipped, all
    four counts stay 0, and corpora A / B / C produce the **same** matrix
    (3 states, λ = [1, 0, 0]). A driver that still printed « CANDIDAT #2 LIVRÉ »
    on that state would be selling a status-word chain as a belief-state chain
    (anti-theatre #1019).
    """
    maxima = {key: 0 for key in _BELIEF_STATE_COORDINATES}
    observations = 0
    for trajectory in tpm_payload.get("trajectories") or []:
        if not isinstance(trajectory, dict):
            continue
        for observation in trajectory.get("observations") or []:
            if not isinstance(observation, dict):
                continue
            snapshot = observation.get("snapshot")
            if not isinstance(snapshot, dict):
                continue
            observations += 1
            for key in _BELIEF_STATE_COORDINATES:
                value = snapshot.get(key)
                if isinstance(value, int) and value > maxima[key]:
                    maxima[key] = value
    block: Dict[str, Any] = dict(maxima)
    block["observations"] = observations
    block["carries_belief_state"] = any(value > 0 for value in maxima.values())
    return block


# ---------------------------------------------------------------------------
# Inner TPM extraction (subprocess wrapper)
# ---------------------------------------------------------------------------


def _run_inner_extractor(
    corpus_letter: str,
    inner_output_dir: Path,
    max_wall_seconds: float,
    timeout_seconds: float,
) -> Path:
    """Subprocess ``scripts/extract_belief_trajectories.py --source corpusX``.

    Returns the path to the produced ``tpm.json``. The extractor handles
    its own determinism (LLM_CACHE_MODE=replay recommended) and writes a
    complete report (``tpm.json`` + ``report.md``). No re-implementation of
    the pipeline here — anti-pendule.
    """
    if not EXTRACTOR_SCRIPT.exists():
        raise FileNotFoundError(
            f"Inner extractor missing: {EXTRACTOR_SCRIPT}. "
            "Track TPM-1 #1489 / TPM-2 #1491 must be merged first."
        )
    inner_output_dir.mkdir(parents=True, exist_ok=True)
    cmd: List[str] = [
        sys.executable,
        str(EXTRACTOR_SCRIPT),
        "--source",
        f"corpus{corpus_letter.upper()}",
        "--output-dir",
        str(inner_output_dir),
        "--max-wall-seconds",
        str(max_wall_seconds),
        # Quiet verbosity; we render our own verdict report.
        "--verbose",
    ]
    logger.info("Subprocess: %s", " ".join(cmd))
    inner_env = os.environ.copy()
    # Inner extractor imports `argumentation_analysis.core.utils.crypto_utils`
    # which lives at repo root and `src/`. pytest injects `pythonpath = . src`
    # via pytest.ini — outside pytest we must do it ourselves.
    existing = inner_env.get("PYTHONPATH", "")
    inner_env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), str(REPO_ROOT / "src"), existing]
    ).strip(os.pathsep)
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=inner_env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Inner extractor failed for corpus{corpus_letter} "
            f"(exit={proc.returncode}).\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    tpm_json = inner_output_dir / "tpm.json"
    if not tpm_json.exists():
        raise RuntimeError(
            f"Inner extractor returned 0 but tpm.json missing in {inner_output_dir}."
        )
    return tpm_json


def _read_tpm_payload(tpm_json_path: Path) -> Dict[str, Any]:
    """Read the inner extractor output (full payload incl. trajectories)."""
    raw = json.loads(tpm_json_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"tpm.json root must be a dict, got {type(raw).__name__}")
    return raw


# ---------------------------------------------------------------------------
# S6-A1 verdict assembly
# ---------------------------------------------------------------------------


@dataclass
class Verdict:
    """The S6-A1 verdict for one corpus.

    Maps directly to CoursIA seed candidate #2 of
    `jsboige/CoursIA#7289`.
    """

    corpus_letter: str
    n_trajectories: int
    n_observations_total: int
    n_transitions: int
    n_states: int
    impossible: bool
    impossibility_reason: str
    ergodicity: Dict[str, Any]
    spectral: Dict[str, Any]
    state_space: Dict[str, Any]
    coursia_seed_issue: str
    candidate_id: str
    entropy: Dict[str, Any] = field(default_factory=dict)
    privacy: Dict[str, str] = field(default_factory=dict)


def _build_verdict(
    corpus_letter: str,
    tpm_payload: Dict[str, Any],
    ergo_payload: Dict[str, Any],
    spectral_result: SpectralResult,
    entropy_result: Optional[EntropyProductionResult] = None,
) -> Verdict:
    """Build the S6-A1 verdict from the inner extractor + structural legs."""
    # Ergodic leg: the runner derives it from the matrix through the inner
    # extractor's graph analyser (TPM-2 #1491), never from rendered Markdown.
    ergo_block = ergo_payload if ergo_payload else {}
    return Verdict(
        corpus_letter=corpus_letter,
        n_trajectories=int(tpm_payload.get("n_trajectories", 0)),
        n_observations_total=int(tpm_payload.get("n_observations_total", 0)),
        n_transitions=int(tpm_payload.get("n_transitions", 0)),
        n_states=int(tpm_payload.get("n_states", 0)),
        impossible=bool(tpm_payload.get("impossible", False)),
        impossibility_reason=str(tpm_payload.get("impossibility_reason", "") or ""),
        ergodicity=ergo_block,
        entropy=asdict(
            entropy_result
            or EntropyProductionResult(
                n=spectral_result.n,
                sigma=None,
                stationary=None,
                irreducible=False,
                one_way_pairs=0,
                analysis_skipped=True,
                skip_reason="entropy production was not computed",
            )
        ),
        # #1506 R1107 — what the matrix is actually made of. A chain over
        # phase status words is not a chain over belief states, and the verdict
        # must say which one it holds.
        state_space=belief_state_coverage(tpm_payload),
        spectral={
            "n": spectral_result.n,
            "eigenvalues_abs": spectral_result.eigenvalues_abs,
            "spectral_gap": spectral_result.spectral_gap,
            "second_largest_abs": spectral_result.second_largest_abs,
            "analysis_skipped": spectral_result.analysis_skipped,
            "skip_reason": spectral_result.skip_reason,
        },
        coursia_seed_issue=COURSIA_SEED_ISSUE,
        candidate_id="candidate_2_belief_state_tpm",
        privacy={
            "raw_text_persisted": "no",
            "source_name_persisted": "no",
            "opaque_ids_only": "yes",
            "in_memory_decrypt": "yes",
        },
    )


def _render_verdict_markdown(
    verdict: Verdict,
    tpm_payload: Dict[str, Any],
    inner_report_relpath: str,
) -> str:
    """Render the human-readable verdict markdown."""
    lines: List[str] = []
    lines.append(f"# S6-A1 #1506 — Verdict corpus {verdict.corpus_letter}")
    lines.append("")
    lines.append(
        "**Track**: S6-A1 (CoursIA strate-6 Phase-A candidate substrate #2). "
        f"Seed [`{COURSIA_SEED_ISSUE}`](https://github.com/{COURSIA_SEED_ISSUE}) "
        f"— one of the ≥2 independent falsifiability substrates required by "
        f"contract [`{COURSIA_FALSIFIABILITY_CONTRACT}`]"
        f"(https://github.com/{COURSIA_FALSIFIABILITY_CONTRACT})."
    )
    lines.append("")
    lines.append("## Candidate scope (delivered here)")
    lines.append("")
    lines.append(
        "**Candidate #2 — belief-state TPM**: a stochastic transition matrix "
        "over *belief states* observed across the democratech pipeline "
        "(TPM-1 #1489 / TPM-2 #1491), refined with a **spectral gap** leg "
        "(`np.linalg.eigvals` on the row-stochastic matrix). The substrate "
        "is independent from sibling candidate #1 (S6-A2 — Dung labelling "
        "trajectory, MERGED PR #1509) — one reasons over Dung labellings, "
        "the other over belief states."
    )
    lines.append("")
    lines.append("## Corpus-level verdict")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Corpus | `corpus{verdict.corpus_letter}` |")
    lines.append(f"| Trajectoires (propositions) | **{verdict.n_trajectories}** |")
    lines.append(f"| Observations totales | **{verdict.n_observations_total}** |")
    lines.append(f"| Transitions observées | **{verdict.n_transitions}** |")
    lines.append(f"| Taille espace d'états | **{verdict.n_states}** |")
    if verdict.impossible:
        lines.append(
            f"| **Verdict TPM** | **IMPOSSIBLE** — {verdict.impossibility_reason} |"
        )
    else:
        lines.append("| **Verdict TPM** | matrice stochastique définie |")
    lines.append("")
    lines.append("## Espace d'états — ce que la matrice compte réellement")
    lines.append("")
    space = verdict.state_space or {}
    if space and not space.get("carries_belief_state", True):
        lines.append(
            "- **La matrice ne mesure PAS des états de croyance.** Les quatre "
            "coordonnées du label d'état (arguments, sophismes, contre-"
            "arguments, croyances) valent **0** sur les "
            f"{space.get('observations', 0)} observation(s) : seul le **mot de "
            "statut de phase** varie. La TPM décrit donc des transitions "
            "`completed` / `failed` / `skipped`, pas des états de croyance — "
            "le candidat #2 n'est pas mesuré par cette exécution."
        )
        lines.append(
            "- **Cause mesurée** : la phase `extract` échoue sur chaque "
            "proposition (sous `LLM_CACHE_MODE=replay`, un cache miss faute de "
            "fixtures) ; tout l'aval est sauté, d'où des compteurs à 0."
        )
        lines.append(
            "- **Conséquence** : aucun artefact n'est proposé au partenaire. "
            "Le critère R1107 exige que l'instrument sépare deux entrées "
            "contrastées ; un espace d'états réduit aux mots de statut ne "
            "sépare rien, et trois corpus distincts donnent la même matrice."
        )
    elif space:
        maxima = ", ".join(
            f"{key}={space.get(key, 0)}" for key in _BELIEF_STATE_COORDINATES
        )
        lines.append(f"- Coordonnées maximales observées : {maxima}.")
        lines.append(
            "- Au moins une coordonnée non nulle : la matrice porte bien de "
            "l'information d'état, au-delà du mot de statut."
        )
    lines.append("")
    lines.append("## Ergodicité (TPM-2 #1491, hérité du sous-traitant)")
    lines.append("")
    if not verdict.ergodicity:
        lines.append(
            "_Section absente du rapport sous-traitant (TPM impossible ou rapport introuvable)._"
        )
    else:
        if "ergodic_line" in verdict.ergodicity:
            lines.append(f"- {verdict.ergodicity['ergodic_line']}")
        if "n_scc" in verdict.ergodicity:
            lines.append(f"- SCC : **{verdict.ergodicity['n_scc']}**")
        if "n_wcc" in verdict.ergodicity:
            lines.append(f"- WCC : **{verdict.ergodicity['n_wcc']}**")
        if "irreducible" in verdict.ergodicity:
            lines.append(f"- Irréductible : **{verdict.ergodicity['irreducible']}**")
    lines.append("")
    lines.append("## Production d'entropie (R1107 — troisième quantité)")
    lines.append("")
    entropy = verdict.entropy
    sigma = entropy.get("sigma")
    if entropy.get("analysis_skipped"):
        if entropy.get("one_way_pairs", 0):
            lines.append(
                f"- **σ = +inf** : {entropy['one_way_pairs']} paire(s) de "
                "transitions à sens unique sous la distribution stationnaire."
            )
        else:
            lines.append(f"- **σ non calculable** : {entropy.get('skip_reason')}.")
    elif sigma is not None:
        lines.append(f"- σ = **{sigma:.4f}** nat(s)/transition.")
        lines.append(
            "- σ = Σᵢⱼ πᵢPᵢⱼ ln(Pᵢⱼ/Pⱼᵢ), avec π stationnaire ; "
            "0 décrit une chaîne réversible."
        )
    else:
        lines.append(
            f"- **σ non calculé** : {entropy.get('skip_reason') or 'jambe absente du verdict'}."
        )
    lines.append("")
    lines.append("## Spectrale (R664 — jambe ajoutée par ce driver)")
    lines.append("")
    if verdict.spectral["analysis_skipped"]:
        lines.append(
            f"- **Skipped** : `{verdict.spectral['skip_reason']}` "
            "(verdict ergodicité tient debout seul)."
        )
    else:
        gap = verdict.spectral["spectral_gap"]
        lam2 = verdict.spectral["second_largest_abs"]
        lines.append(f"- n = **{verdict.spectral['n']}** états")
        lines.append(f"- λ₂ (|deuxième valeur propre|) = **{lam2:.4f}**")
        lines.append(f"- **Spectral gap** (1 − |λ₂|) = **{gap:.4f}**")
        # #1506 R1107 — the gap is a MIXING RATE only for an irreducible chain.
        # On a reducible one λ₂ = 0 gives g = 1, which the old branch read as
        # « mixing rapide » while the same page said « réductible ».  And
        # reducibility alone does not decide stationarity: one recurrent class
        # plus transient states still has a unique pi, several recurrent
        # classes do not.  The entropy leg owns that question, not the spectre.
        irreducible = verdict.ergodicity.get("irreducible")
        if irreducible is False:
            lines.append(
                "- **g n'est pas un taux de mélange ici** : la chaîne est "
                "réductible (≥ 2 SCC). Une chaîne réductible peut avoir une "
                "stationnaire unique (une seule classe récurrente) ou non "
                "(plusieurs) — ce n'est pas la spectrale qui en décide : la "
                "jambe « Production d'entropie » ci-dessus nomme l'unicité."
            )
        elif gap is not None and gap >= 0.3:
            lines.append(
                "- **Mixing rapide** : convergence en O(log 1/ε) steps. "
                "Distribution stationnaire accessible (si irréductible + "
                "apériodique, déjà vérifié par TPM-2 #1491)."
            )
        elif gap is not None and gap > 0.0:
            lines.append(
                "- **Mixing lent** : convergence polynomiale. Spectre proche "
                "d'une structure en blocs."
            )
        elif gap == 0.0:
            lines.append(
                "- **Non-mixing** : structure bloc-diagonale ou valeurs "
                "propres multiples en |λ| = 1 (ex. chaîne périodique). "
                "Le gap seul ne décide pas de l'unicité du stationnaire — "
                "voir la jambe « Production d'entropie »."
            )
        lines.append("")
        eigs = verdict.spectral["eigenvalues_abs"]
        if eigs:
            lines.append("| # | |λ| |")
            lines.append("|---|------|")
            for i, lam in enumerate(eigs[: min(8, len(eigs))]):
                lines.append(f"| {i} | {lam:.4f} |")
            if len(eigs) > 8:
                lines.append(f"| … | _(truncated)_ |")
    lines.append("")
    lines.append("## Synthèse CoursIA — candidat #2")
    lines.append("")
    if verdict.impossible:
        lines.append(
            "**Statut** : LIVRABLE PARTIEL — la TPM est dégénérée pour ce "
            f"corpus ({verdict.impossibility_reason}). Le candidat #2 est "
            "toujours LIVRÉ (preuve exécutable + verdict honnête), mais la "
            "piste `corpusL` est non-exploitée pour ce subset. Voir "
            "l'autre sous-ensemble (corpus A / B / C) pour une TPM non-"
            "dégénérée. Anti-théâtre #1019 : le verdict est premier, le "
            "ré-échelonnage est un suivi."
        )
    elif space and not space.get("carries_belief_state", True):
        # #1506 R1107 — the honest status. The matrix exists and is
        # reproducible, but it counts phase status words: calling that
        # « CANDIDAT #2 LIVRÉ » is the theatre #1019 forbids.
        lines.append(
            "**Statut** : **NON MESURÉ**. La matrice est reproductible, mais "
            "elle ne porte aucune coordonnée d'état de croyance (les quatre "
            "compteurs restent à 0) : elle compte des transitions entre mots "
            "de statut de phase. Le candidat #2 n'est donc pas démontré par "
            "cette exécution, et aucun artefact n'est proposé au partenaire "
            "(critère R1107 : un instrument qui ne sépare pas deux entrées "
            "contrastées n'est pas proposé)."
        )
    else:
        lines.append(
            "**Statut** : **CANDIDAT #2 LIVRÉ**. La TPM est définie depuis "
            "une source réelle du dépôt (corpus chiffré déchiffré in-memory). "
            "Le verdict ergodicité (TPM-2 #1491) + la jambe spectrale "
            "(R664) sont publiés. Le candidat est FALSIFIABLE : le script "
            "re-joué produit la même TPM (déterminisme LLM_CACHE_MODE=replay) "
            "+ la même jambe spectrale (calcul déterministe sur la matrice)."
        )
    lines.append("")
    lines.append("## Limites honnêtes")
    lines.append("")
    lines.append(
        f"- **{verdict.n_trajectories} trajectoires × "
        f"{verdict.n_observations_total // max(verdict.n_trajectories, 1)} "
        f"obs/trajectoire en moyenne** → matrice peu profonde (peu de "
        "transitions par paire d'états). Confiance sur le verdict "
        "qualitatif (SCC/WCC) plutôt que sur la valeur exacte de λ₂."
    )
    lines.append(
        f"- **Espace d'états compact ({verdict.n_states})** issu du bucketing "
        "coarse hérité du TPM-1. Choix délibéré pour stabiliser les comptes."
    )
    lines.append(
        "- **Sous-traitance** : ce driver **ne ré-implémente pas** le "
        "pipeline (anti-pendule). Il subprocesse `extract_belief_trajectories."
        "py` et lit son JSON. La jambe spectrale est ajoutée par-dessus, "
        "pas en doublon."
    )
    lines.append(
        "- **Privacy HARD** : 0 raw_text persisté, 0 nom de source "
        "persisté, IDs opaques (`prop_<8hex>`), déchiffrement in-memory "
        "uniquement. Sortie sous `evaluation/results/strate6_phaseA/` "
        "(gitignored)."
    )
    lines.append(
        f"- **Artefact sous-traitant** : rapport complet `{inner_report_relpath}` "
        "(TPM + trajectoires + ergodicité intégrée)."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Per-corpus runner
# ---------------------------------------------------------------------------


def run_for_corpus(
    corpus_letter: str,
    output_root: Path,
    max_wall_seconds: float,
    timeout_seconds: float,
) -> Path:
    """Drive S6-A1 for one corpus. Returns the verdict directory."""
    corpus_letter = corpus_letter.upper()
    verdict_dir = output_root / f"corpus{corpus_letter}"
    inner_dir = INNER_TPM_ROOT / f"corpus{corpus_letter}"
    if verdict_dir.exists():
        shutil.rmtree(verdict_dir)
    if inner_dir.exists():
        shutil.rmtree(inner_dir)
    verdict_dir.mkdir(parents=True, exist_ok=True)
    inner_dir.mkdir(parents=True, exist_ok=True)

    tpm_json_path = _run_inner_extractor(
        corpus_letter, inner_dir, max_wall_seconds, timeout_seconds
    )
    tpm_payload = _read_tpm_payload(tpm_json_path)

    # Reconstruct the row-stochastic matrix from the JSON for the spectral
    # leg — anti-pendule: do NOT re-run the pipeline, just re-normalize
    # the already-counted transitions.
    if tpm_payload.get("impossible"):
        stochastic = []
    else:
        counts = tpm_payload["tpm"]["transition_counts"]
        n = len(counts)
        stochastic = [[0.0] * n for _ in range(n)]
        for i, row in enumerate(counts):
            total = sum(row)
            if total <= 0:
                continue
            for j in range(n):
                stochastic[i][j] = counts[i][j] / total

    spectral_result = spectral_gap(stochastic)
    ergo_payload = ergodicity_from_matrix(stochastic) if stochastic else {}
    entropy_result = entropy_production(stochastic)
    verdict = _build_verdict(
        corpus_letter,
        tpm_payload,
        ergo_payload,
        spectral_result,
        entropy_result=entropy_result,
    )

    verdict_json_path = verdict_dir / "verdict.json"
    verdict_md_path = verdict_dir / "verdict.md"
    inner_rel = f"../../_inner_tpm/corpus{corpus_letter}/report.md"
    # Write gitignored run artifacts with the checkout's LF convention, rather
    # than letting Windows text mode introduce CRLF into reproducible outputs.
    verdict_json_path.write_bytes(
        (json.dumps(asdict(verdict), indent=2, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
    )
    verdict_md_path.write_bytes(
        _render_verdict_markdown(verdict, tpm_payload, inner_rel).encode("utf-8")
    )

    # Drop the bulky trajectories into a sibling file under the verdict dir
    # (no raw_text) for self-containment.
    if tpm_payload.get("trajectories"):
        traj_payload = [
            {
                "corpus_id": t.get("corpus_id"),
                "corpus_label": t.get("corpus_label"),
                "total_elapsed_seconds": t.get("total_elapsed_seconds"),
                "terminated_by_budget": t.get("terminated_by_budget"),
                "error": t.get("error"),
                "n_observations": len(t.get("observations", [])),
            }
            for t in tpm_payload["trajectories"]
        ]
        (verdict_dir / "trajectories_summary.json").write_bytes(
            (json.dumps(traj_payload, indent=2, ensure_ascii=False) + "\n").encode(
                "utf-8"
            )
        )

    logger.info(
        "S6-A1 verdict for corpus %s → %s (spectral gap=%s, sigma=%s)",
        corpus_letter,
        verdict_md_path,
        spectral_result.spectral_gap,
        entropy_result.sigma,
    )
    return verdict_dir


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    )


def _print_dry_run() -> int:
    print("=" * 72)
    print(" S6-A1 #1506 — Dry-run contract")
    print("=" * 72)
    print()
    print("Candidate mapping (CoursIA seed #7289 — ≥2 substrates required):")
    print()
    for cand in CANDIDATES_FOR_SEED:
        marker = (
            "← THIS DRIVER DELIVERS" if cand["this_driver_delivers"] else "(sibling)"
        )
        print(f"  [{marker}]")
        print(f"    id          : {cand['id']}")
        print(f"    delivered_in: {cand['delivered_in']}")
        print(f"    scope       : {cand['scope']}")
        print(f"    engine      : {cand['engine']}")
        print(f"    data        : {cand['data_substrate']}")
        print()
    print("Anti-pendule invariants:")
    print("  * This driver does NOT re-implement the TPM pipeline.")
    print("  * Inner extractor is subprocessed as a black box (TPM-1/2).")
    print("  * Spectral gap and entropy production are small ADDITIONS.")
    print("  * Non-unique stationarity names sigma as uncomputable.")
    print("  * Privacy HARD: 0 raw_text, opaque IDs, in-memory decrypt only.")
    print()
    print(f"Output root: {DEFAULT_OUTPUT_ROOT}")
    print(f"Inner TPM scratch: {INNER_TPM_ROOT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "S6-A1 #1506 — CoursIA strate-6 Phase-A grounding (candidate #2). "
            "Subprocesses the TPM-1/2 extractor for each real corpus, adds "
            "the spectral-gap and entropy-production legs, and emits a "
            "verdict per corpus."
        )
    )
    parser.add_argument(
        "--corpus",
        choices=("A", "B", "C", "ALL"),
        default="ALL",
        help="Which corpus to drive (default: ALL).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Output root (default: evaluation/results/strate6_phaseA).",
    )
    parser.add_argument(
        "--max-wall-seconds",
        type=float,
        default=300.0,
        help="Per-proposition wall-clock cap passed to inner extractor.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=3600.0,
        help="Outer subprocess timeout (default 1h, generous for full corpus).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the contract + candidate mapping, do not run.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    _setup_logging(args.verbose)

    if args.dry_run:
        return _print_dry_run()

    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    corpora: List[str]
    if args.corpus == "ALL":
        corpora = ["A", "B", "C"]
    else:
        corpora = [args.corpus]

    produced: List[Path] = []
    for letter in corpora:
        try:
            verdict_dir = run_for_corpus(
                corpus_letter=letter,
                output_root=output_root,
                max_wall_seconds=args.max_wall_seconds,
                timeout_seconds=args.timeout_seconds,
            )
            produced.append(verdict_dir)
        except Exception as exc:
            logger.error("S6-A1 failed for corpus %s: %s", letter, exc)
            return 1

    print()
    print(f"→ S6-A1 verdicts ({len(produced)} corpus):")
    measured = 0
    for p in produced:
        print(f"   - {p / 'verdict.md'}")
        try:
            payload = json.loads((p / "verdict.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (payload.get("state_space") or {}).get("carries_belief_state"):
            measured += 1
    print()
    if measured:
        print(
            f"Candidate #2 ({COURSIA_SEED_ISSUE}) : MESURÉ sur "
            f"{measured}/{len(produced)} corpus (preuve exécutable)."
        )
    else:
        # #1506 R1107 — no state coordinate ever fired: the matrix counts
        # phase status words. Saying « LIVRÉ » here is the theatre #1019 bans,
        # and the R1107 criterion forbids proposing such an artifact.
        print(
            f"Candidate #2 ({COURSIA_SEED_ISSUE}) : NON MESURÉ — la matrice ne "
            "porte aucune coordonnée d'état de croyance (compteurs à 0, seul "
            "le statut de phase varie). Aucun artefact proposé."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
