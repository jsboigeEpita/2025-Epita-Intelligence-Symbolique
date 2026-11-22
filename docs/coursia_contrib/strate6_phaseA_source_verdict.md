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
> reached in one step. Reducibility alone does not decide stationarity: one
> recurrent class plus transient states still has a unique stationary
> distribution, several recurrent classes do not — the entropy leg names
> which case holds.
>
> **Instrument update 2026-11-22 (R1107, before the coordinator's paired
> record run):** the driver now reports all three quantities per input —
> entropy production σ, the directed spectral gap, and the structured
> ergodicity verdict. It no longer scrapes ergodicity out of the inner
> Markdown report. For an irreducible chain,
> `σ = Σᵢⱼ πᵢPᵢⱼ ln(Pᵢⱼ/Pⱼᵢ)` uses the unique stationary distribution π;
> a forward-only stationary transition gives σ = +inf with its pair count. A
> stationary distribution is required and must be unique. This also covers a
> reducible chain with one recurrent class and transient states. With several
> recurrent classes σ is explicitly uncomputable — no trajectory-occupancy
> surrogate is substituted.
>
> The zero-spend discrimination control uses two four-state reference rings.
> Both are irreducible and have directed gap 0, but the reversible ring has
> σ = 0 while the 0.9/0.1 drift ring has σ = 0.8 ln 9 ≈ 1.7578. Thus σ
> separates a pair the gap does not. This proves the analysis leg on reference
> regimes only; it does not supply the two missing argumentative inputs and
> does not change the decision not to propose candidate #2.

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
(1) the irreducible-structure (SCC/WCC), (2) the entropy production and the
stationary-uniqueness verdict, and (3) the spectral gap — read as a mixing
rate only when the chain is irreducible — from a single JSON artifact
(`verdict.json`).

## The candidate scope (delivered here)

**Candidate #2 — belief-state TPM.** The driver
[`scripts/coursia_strate6_phaseA_grounding.py`](../../scripts/coursia_strate6_phaseA_grounding.py)
is a **thin coordinator**:

1. **Subprocess** the inner extractor
   [`scripts/extract_belief_trajectories.py --source corpusX`](../../scripts/extract_belief_trajectories.py)
   for each real corpus (A / B / C) — *no re-implementation* of the TPM
   pipeline (anti-pendule).
2. **Read** the inner extractor output (`tpm.json` + `report.md`).
3. **Add** the spectral-gap and entropy-production legs on the
   already-row-normalised stochastic matrix — small, additive refinements
   (R664 / R1107).
4. **Render** a verdict per corpus: structured ergodicity derived through the
   inner extractor's graph analyser, spectral gap, entropy production,
   corpus-level counts, and a candidate-mapping block that points at CoursIA
   seed issue #7289.

The driver is the *CoursIA-facing* artifact. The verdict is *machine-checked*
and *falsifiable*: ergodicity is derived from the matrix through the inner
extractor's graph analyser — the runner never scrapes it back out of the
rendered Markdown — and every skipped analysis names its reason instead of
being auto-padded (anti-théâtre #1019).

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

# Zero-spend discrimination controls: reversible and drift reference regimes.
# The same invocation runs the prior Phase-A witnesses and the egress liveness
# controls; none of these tests reads a corpus or invokes an LLM.
python -m pytest tests/unit/scripts/test_strate6_phase_a_entropy_1506.py \
    tests/unit/scripts/test_strate6_phase_a_grounding_1506.py \
    tests/unit/test_llm_egress_counter.py -q

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
- **Falsifiability**: a candidate verdict that fails to expose (1) structured
  ergodicity (SCC, WCC, irreducible), (2) a numeric directed spectral gap in
  $[0, 1]$, and (3) entropy production σ — finite, +inf, or an explicit
  uncomputability reason — is **incomplete**. Missing numerical analysis is
  reported with its reason, never auto-padded.

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
