# S6-A1 — Belief-state stochastic matrix: source verdict

**Track**: S6-A1 (issue #1506) · **Epic**: CoursIA strate-6 ICT.
**CoursIA gate**: Phase-A candidate **#2** for seed
[`jsboige/CoursIA#7289`](https://github.com/jsboige/CoursIA/issues/7289) —
a *belief-state transition matrix* over a real corpus — one of the ≥2
independent falsifiability substrates required by contract
[`jsboige/CoursIA#7291`](https://github.com/jsboige/CoursIA/issues/7291).
**Driver**: [`scripts/coursia_strate6_phaseA_grounding.py`](../../scripts/coursia_strate6_phaseA_grounding.py) ·
**Sub-traitant TPM-1/2**: [`scripts/extract_belief_trajectories.py`](../../scripts/extract_belief_trajectories.py)
(Track TPM-1 #1489, TPM-2 #1491).

> ## Status 2026-10-23 — candidate #2 is NOT proposed, and this page says why
>
> The re-run the R1105 audit asked for was executed on `main` under the
> zero-spend `LLM_CACHE_MODE=replay`, and it settles the question negatively.
> **The state space carries no belief information**: the inner extractor's
> `extract` phase fails on every proposition with a replay cache miss (no
> fixtures are committed for these corpora), everything downstream is skipped,
> and all four label coordinates — arguments, fallacies, counter-arguments,
> beliefs — stay at **0**. The only varying coordinate is the **phase status
> word**, so the matrix counts `completed` / `failed` / `skipped` transitions.
>
> Measured consequence, corpora A / B / C: **3 states, λ = [1, 0, 0],
> g = 1.0** — the same matrix three times. Nothing separates them, so the
> R1107 criterion ("the instrument must separate two contrasted inputs, else do
> not propose the artifact") is not met, and **no artifact is proposed to the
> partner**.
>
> What would unblock it is a **paid** run (`LLM_CACHE_MODE=record` over the
> corpora, or committed fixtures). Until then this leg is **blocked on budget**,
> not on code: the driver refuses the delivery claim by itself
> (`belief_state_coverage`, and the « NON MESURÉ » status it renders).
>
> Also corrected here: `g = 1 − |λ₂|` was read as « mixing rapide » even on a
> chain the same page called « réductible ». **g is a mixing rate only for an
> irreducible chain** — on a reducible one λ₂ = 0 says an absorbing class is
> reached in one step, and there is no unique stationary distribution to
> converge to.

## The thesis

A corpus, observed through the democratech pipeline, yields a sequence of
*belief states* over its propositions. The transition counts across states
form a **stochastic matrix** $P$ of size $|S| \times |S|$ where $S$ is the
set of distinct belief states observed. The matrix is row-normalised
($P_{ij} = n_{ij} / \sum_k n_{ik}$) and its **ergodicity verdict** is the
TPM-2 #1491 deliverable. We add here a refinement leg: the **spectral gap**
$g = 1 - |\lambda_2|$, where $\lambda_2$ is the second-largest-magnitude
eigenvalue of $P$ (R664). A gap of $g \approx 0$ exposes a near-block-diagonal
chain (slow mixing); a gap of $g \approx 1$ confirms rapid convergence.

The substrate is *the matrix itself*: a downstream CoursIA model can read off
(1) the irreducible-structure (SCC/WCC), (2) the stationary distribution, and
(3) the mixing rate, from a single JSON artifact (`verdict.json`).

## The candidate scope (delivered here)

**Candidate #2 — belief-state TPM.** The driver
[`scripts/coursia_strate6_phaseA_grounding.py`](../../scripts/coursia_strate6_phaseA_grounding.py)
is a **thin coordinator**:

1. **Subprocess** the inner extractor
   [`scripts/extract_belief_trajectories.py --source corpusX`](../../scripts/extract_belief_trajectories.py)
   for each real corpus (A / B / C) — *no re-implementation* of the TPM
   pipeline (anti-pendule).
2. **Read** the inner extractor output (`tpm.json` + `report.md`).
3. **Add** the spectral-gap leg on the already-row-normalised stochastic
   matrix — a small, additive refinement (R664).
4. **Render** a verdict per corpus: ergodicity (inherited from #1491),
   spectral gap (this driver), corpus-level counts, and a candidate-mapping
   block that points at CoursIA seed issue #7289.

The driver is the *CoursIA-facing* artifact. The verdict is *machine-checked*
and *falsifiable*: any disagreement between the candidate matrix and the
ergodicity verdict scrapes from the inner report is reported verbatim — never
auto-reconciled (anti-théâtre #1019).

## Anti-pendule invariants

- **No re-implementation.** The TPM pipeline lives in the inner extractor;
  this driver is a black-box subprocess.
- **Spectral gap is an addition, not a duplication.** It reads the matrix
  the inner extractor already produced; it does not recompute TPMs.
- **Privacy HARD.** No `full_text` / `raw_text` / `text` field reaches the
  verdict artifact. Only opaque `prop_<8hex>` IDs, counts, and eigenvalues.
  Decryption happens in-memory only via
  [`scripts/_tpm_corpus_loader.py`](../../scripts/_tpm_corpus_loader.py).
- **Output path is gitignored.** Verdict artifacts live under
  `evaluation/results/strate6_phaseA/` — never on a GitHub-indexed surface
  (R685 boundary).

## Reproduce

```bash
# Dry-run (contract + candidate mapping, no execution):
python scripts/coursia_strate6_phaseA_grounding.py --dry-run

# Real run on corpus A (per-corpus budget 180s, outer timeout 30 min):
python scripts/coursia_strate6_phaseA_grounding.py \
    --corpus A \
    --max-wall-seconds 180 \
    --timeout-seconds 1800

# All three corpora (serially; the inner extractor is single-corpus):
python scripts/coursia_strate6_phaseA_grounding.py --corpus ALL

# JSON verdict + Markdown report (per corpus):
#   evaluation/results/strate6_phaseA/<corpus>/verdict.json
#   evaluation/results/strate6_phaseA/<corpus>/verdict.md
#   evaluation/results/strate6_phaseA/<corpus>/trajectories_summary.json
```

## Scope & honesty (what this is, and is not)

- **What it is**: a Phase-A *candidate substrate* — a stochastic matrix over
  belief states, machine-checked on the real encrypted corpora (A/B/C), with
  ergodicity + spectral-gap refinement. The verdict is **computed**, not
  asserted.
- **What it is not (yet)**: a corpus-derived belief-state trajectory at
  scale (current corpora are small — see `verdict.md` per corpus). The
  scaling lane (TPM-2 #1491) is delivered and merged; the substrate is
  reproducible on any future corpus that exposes the same decryption contract.
- **Falsifiability**: a candidate verdict that fails to expose (1) ergodicity
  (SCC, WCC, irreducible) and (2) a numeric spectral gap in $[0, 1]$ is
  **incomplete**. The driver fails-fast on missing fields and reports the
  underlying reason verbatim — no auto-padding.

## Relation to the sibling substrate

S6-A2 (po-2023, MERGED PR #1509) produced candidate **#1** — a trajectory
over *Dung labelling states* from abstract argumentation. This candidate **#2**
is its stochastic complement: a stationary distribution over *belief states*
extracted from real text. The two are independent (one reasons over symbolic
labellings on a synthetic opaque exemplar, the other over empirical beliefs
on encrypted corpora), satisfying the contract's ≥2-substrate requirement.

## Links

- **CoursIA seed** (candidates mapping): [`jsboige/CoursIA#7289`](https://github.com/jsboige/CoursIA/issues/7289)
- **Falsifiability contract**: [`jsboige/CoursIA#7291`](https://github.com/jsboige/CoursIA/issues/7291)
- **Sibling candidate #1 doc**: [`s6_a2_labelling_trajectory.md`](s6_a2_labelling_trajectory.md)
- **Inner extractor (TPM-1 #1489 / TPM-2 #1491)**: [`../../scripts/extract_belief_trajectories.py`](../../scripts/extract_belief_trajectories.py)
- **Corpus loader (privacy HARD)**: [`../../scripts/_tpm_corpus_loader.py`](../../scripts/_tpm_corpus_loader.py)

— Track S6-A1 · worker myia-po-2025 · #1506