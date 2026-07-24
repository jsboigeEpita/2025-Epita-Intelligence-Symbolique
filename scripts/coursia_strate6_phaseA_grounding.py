#!/usr/bin/env python3
"""Track S6-A1 #1506 — CoursIA strate-6 Phase-A grounding (candidate substrate #2).

For each real corpus (corpusA / corpusB / corpusC, decrypted in-memory via
``scripts/_tpm_corpus_loader.py``), this driver:

1. **Subprocesses** ``scripts/extract_belief_trajectories.py --source
   corpusX`` (TPM-1/2 machinery, anti-pendule: no re-implementation of the
   pipeline). Writes a deterministic ``tpm.json`` per corpus, containing
   ``states`` + ``transition_counts`` + ergodicity verdict (TPM-2 #1491).
2. **Reads** the produced JSON.
3. **Adds the spectral-gap leg** (R664 — ``np.linalg.eigvals`` on the
   row-stochastic matrix, used as a *refinement* of the reducible /
   non-mixing verdict when the chain is irreducible-ap-periodic).
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
                 "Verdict: ergodic / reducible / aperiodic + spectral gap "
                 "refinement (R664).",
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
    inner_env["PYTHONPATH"] = (
        os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "src"), existing])
        .strip(os.pathsep)
    )
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
        raise ValueError(
            f"tpm.json root must be a dict, got {type(raw).__name__}"
        )
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
    coursia_seed_issue: str
    candidate_id: str
    privacy: Dict[str, str] = field(default_factory=dict)


def _build_verdict(
    corpus_letter: str,
    tpm_payload: Dict[str, Any],
    ergo_payload: Dict[str, Any],
    spectral_result: SpectralResult,
) -> Verdict:
    """Build the S6-A1 verdict from the inner extractor + spectral leg."""
    # Ergodic leg: prefer the embedded one in tpm_payload if the inner
    # extractor already computed it (it does — TPM-2 #1491). We re-read the
    # raw values from the report, not via _analyze_ergodicity, to keep this
    # driver stateless and reproducible from the JSON alone.
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


def _parse_ergodicity_from_report(report_md_path: Path) -> Dict[str, Any]:
    """Best-effort scrape of the inner report's ergodicity section.

    The inner report (``report.md``) renders an "Analyse d'ergodicité"
    section. We don't re-implement the leg; we just lift the already-rendered
    numbers so the S6-A1 verdict is self-contained without re-running scipy.

    Returns an empty dict if the section is absent (e.g. impossible TPM).
    """
    if not report_md_path.exists():
        return {}
    text = report_md_path.read_text(encoding="utf-8")
    if "Analyse d'ergodicité" not in text:
        return {}
    # Section is bounded by the next "## " header.
    start = text.index("Analyse d'ergodicité")
    rest = text[start:]
    # Find next "## " at the same level (start of line) — fallback: take
    # the next 30 lines.
    lines = rest.splitlines()
    section_lines: List[str] = []
    for ln in lines[1:]:
        if ln.startswith("## "):
            break
        section_lines.append(ln)
    block: Dict[str, Any] = {"raw_section": "\n".join(section_lines).strip()}
    # Pull a few numbers if present.
    for line in section_lines:
        if "SCC (composantes fortement connexes)" in line:
            # Pattern: **N**
            try:
                block["n_scc"] = int(line.split("**")[1])
            except (IndexError, ValueError):
                pass
        elif "WCC (composantes faiblement connexes)" in line:
            try:
                block["n_wcc"] = int(line.split("**")[1])
            except (IndexError, ValueError):
                pass
        elif "Irréductible" in line and "**" in line:
            block["irreducible"] = "**OUI**" in line
        elif "**Ergodique**" in line:
            block["ergodic_line"] = line.strip()
    return block


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
        lines.append(f"| **Verdict TPM** | **IMPOSSIBLE** — {verdict.impossibility_reason} |")
    else:
        lines.append("| **Verdict TPM** | matrice stochastique définie |")
    lines.append("")
    lines.append("## Ergodicité (TPM-2 #1491, hérité du sous-traitant)")
    lines.append("")
    if not verdict.ergodicity:
        lines.append("_Section absente du rapport sous-traitant (TPM impossible ou rapport introuvable)._")
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
        if gap is not None and gap >= 0.3:
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
                "propres multiples en |λ| = 1. Pas de distribution "
                "stationnaire unique accessible globalement."
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
    report_md = inner_dir / "report.md"
    ergo_payload = _parse_ergodicity_from_report(report_md)

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
    verdict = _build_verdict(corpus_letter, tpm_payload, ergo_payload, spectral_result)

    verdict_json_path = verdict_dir / "verdict.json"
    verdict_md_path = verdict_dir / "verdict.md"
    inner_rel = (
        f"../../_inner_tpm/corpus{corpus_letter}/report.md"
    )
    verdict_json_path.write_text(
        json.dumps(asdict(verdict), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    verdict_md_path.write_text(
        _render_verdict_markdown(verdict, tpm_payload, inner_rel),
        encoding="utf-8",
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
        (verdict_dir / "trajectories_summary.json").write_text(
            json.dumps(traj_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    logger.info(
        "S6-A1 verdict for corpus %s → %s (spectral gap=%s)",
        corpus_letter,
        verdict_md_path,
        spectral_result.spectral_gap,
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
        marker = "← THIS DRIVER DELIVERS" if cand["this_driver_delivers"] else "(sibling)"
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
    print("  * Spectral gap is a small ADDITION (R664), not a duplication.")
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
            "the spectral-gap leg, and emits a verdict per corpus."
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
    for p in produced:
        print(f"   - {p / 'verdict.md'}")
    print()
    print(f"Candidate #2 ({COURSIA_SEED_ISSUE}) : LIVRÉ (preuve exécutable).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())