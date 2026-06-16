# FB-37 — Terminal opaque-safe full spectacular deliverable on the corpora

**Track**: FB-37 #1125 · **Parent**: Epic #947 (Final Boss), Phase 4 · **Theme**: terminal deliverable (run + report)
**Base**: main `395744e4` (FB-36 #1124 merged — the real `doc_A` >2h hang fixed fail-loud)
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique · **Date**: 2026-06-16

## TL;DR (honest verdict)

1. **The terminal full spectacular deliverable is now produced on all three corpora — the artifact that was never reachable because `doc_A` hung.** `spectacular` + `fallacy_tier:"full"` **completes, bounded**, on `doc_A` (532.5s), `doc_C` (715.3s), and `doc_B` (593.3s — the ~3M-char corpus completes bounded too, not size-bound). This is Epic #947's named "spectacular reports" deliverable: the concrete artifact the user needs to arbitrate the EDGES closure verdict.

2. **The pipeline is LLM-conducted end-to-end, formal axis DECIDES, quality EDGES, and the output is opaque-by-construction.** Every corpus completes the **formal axis fully Tweety-verified** (`pl`/`fol`/`fol_solver`/`modal`/`modal_solver`/`kb_to_tweety` all `completed`) and produces the **9-section synthesis** (`synthesis`/`deep_synthesis`/`formal_synthesis` all `completed`). Descent richness is non-vacuous (38/2/5 fallacies; 138/84/6580 extracted args).

3. **Privacy is opaque, non-vacuously.** The synthesis output carries **0** corpus chunks across all three corpora (`synth_leak=0`), and the committed aggregate report is leak-clean against **126715** corpus chunks (`0` hits). The opaque-ID discipline (FB-34) holds at the producer: every entity is `doc_*` / `Speaker_*` / `State_*` / `arg_*`. No `raw_text` or source name anywhere in this report; raw runs are gitignored under `evaluation/results/fb37/`.

4. **Anti-pendule honored.** No `standard` fallback when `full` was slow — `full` completes on every corpus, so the question did not arise; had a corpus been size-bound it would be documented fail-loud (the harness records `TIMED_OUT_*` / `ERROR:*` verdicts, never a silent downgrade). No new caps/templates — the de-castration is *soldée*; the LLM is the only producer. This is a RUN + REPORT capstone (no pipeline code change).

## DoD checklist (#1125)

- [x] `spectacular`+`full` completes on `doc_A` (bounded) — opaque-leak verify = **0 hits** (COMPLETED 532.5s; `synth_leak=0`).
- [x] `spectacular`+`full` on `doc_C` — completes + opaque-leak verify = **0 hits** (COMPLETED 715.3s; `synth_leak=0`).
- [x] `doc_B` attempted under bounded timeout; result documented — **COMPLETED 593.3s** (best case: the ~3M-char corpus completes bounded under the 1800s ceiling, not size-bound; no silent `standard` fallback).
- [x] Aggregate opaque report committed (this file; opaque IDs only).
- [x] No `raw_text`/source names anywhere; raw runs gitignored under `evaluation/results/fb37/`; harness referencing the encrypted dataset untracked (FB-34/35/36 precedent). Aggregate leak audit: **0/126715** corpus chunks.

## Context — why this exists

All three technical blockers of Epic #947's terminal deliverable are cleared on `main` `395744e4`:
- **#1118 (FB-34)** — synthesis opaque-by-construction.
- **#1121 (FB-35)** — cost-based descent breaker (fail-loud, no depth cap).
- **#1123 (FB-36)** — the real `doc_A` >2h hang (per-arg recursion) fixed fail-loud → `spectacular`+`full` now completes on `doc_A`.

The one thing never produced because `doc_A` hung was the terminal full spectacular report on the hard corpus. This capstone produces it on all corpora and aggregates the deliverable. After this lands, only the user's EDGES-verdict arbitration remains for formal Epic closure.

## 1. Results — per-corpus full spectacular run

Each run: `run_unified_analysis(corpus_text, workflow_name="spectacular", context={"fallacy_tier": "full"})` with a hard per-corpus `asyncio.wait_for` ceiling (900s for A/C, 1800s generous for B). Corpus loaded in-memory from the encrypted dataset (opaque IDs; no plaintext on disk).

| Corpus | raw len | verdict | elapsed | phases (done/total) | fallacies (richness) | args | belief sets | synth_leak |
|--------|---------|---------|---------|---------------------|----------------------|------|-------------|------------|
| `doc_A` (hard) | 58052 | COMPLETED | 532.5s | 24/28 | **38** | 138 | 126 | **0** |
| `doc_C` | 46391 | COMPLETED | 715.3s | 24/28 | **2** | 84 | 75 | **0** |
| `doc_B` (~3M chars) | 3063493 | COMPLETED | 593.3s | 24/28 | **5** | 6580 | — | **0** |

The 4 consistently-failed phases are **non-critical and corpus-independent**: `probabilistic`, `stakes`, `aspic_analysis`, `belief_revision` (identical across all three corpora — they are pre-existing solver/service gaps, not corpus-specific failures, and do not affect the formal axis, the fallacy descent, or the synthesis report). The 24 completed phases include the full formal axis, the full fallacy descent (FB-30 agentic + FB-35 cost-bounded), and the full synthesis chain.

## 2. Formal axis — Tweety-verified (DECIDES)

Every corpus completes the entire formal axis through the Tweety bridge (Java/JPype):

| Phase | doc_A | doc_C | doc_B | Role |
|-------|-------|-------|-------|------|
| `pl` | completed | completed | completed | Propositional logic parse |
| `fol` | completed | completed | completed | First-order logic parse |
| `fol_solver` | completed | completed | completed | FOL consistency/entailment (Tweety) |
| `modal` | completed | completed | completed | Modal logic parse |
| `modal_solver` | completed | completed | completed | Modal satisfiability (Tweety) |
| `kb_to_tweety` | completed | completed | completed | Belief-set → Tweety translation |

The formal axis DECIDES end-to-end on every corpus — the pipeline does not stop at extraction; it reasons formally with a verified solver. (Belief-set counts: doc_A=126, doc_C=75 — non-vacuous formal activity.)

## 3. Synthesis — the 9-section spectacular report (LLM-conducted)

Every corpus completes the synthesis chain that produces the spectacular report:

| Phase | doc_A | doc_C | doc_B |
|-------|-------|-------|-------|
| `synthesis` | completed | completed | completed |
| `deep_synthesis` | completed | completed | completed |
| `formal_synthesis` | completed | completed | completed |

The synthesis is **LLM-conducted** (de-castration soldée FB-30..FB-33) and **opaque-by-construction** (FB-34 `OPAQUE_ID_DIRECTIVE` at the top of every synthesis prompt). Section-9 variance is non-determinized: FB-31 (#1108) deleted the count-template fallback and FB-32 (#1112) wired all three LLM synthesis paths; the prose is produced fresh by the LLM per run, not filled from a static f-string. (The per-run prose is gitignored under `evaluation/results/fb37/`; only opaque metrics are committed here.)

## 4. doc_B — bounded, not size-bound

`doc_B` (~3M chars, a verbatim multi-paragraph transcript) was the size-risk corpus. It **completes bounded** at 593.3s under the 1800s generous ceiling — it is **not** size-bound. The per-argument fallacy harness extracts 6580 arguments (Source 3 `\n\n` split — cf. FB-36 path-probe), so it takes the NORMAL per-arg path (the FB-36 fixed branch is doc_A-only). No `standard` fallback was needed or used. Had it been size-bound, the harness would have recorded `TIMED_OUT_1800s` and this section would document it fail-loud per the anti-pendule mandate.

## 5. Privacy — opaque, leak-audited

| Artifact | leak audit (corpus chunks present) | verdict |
|----------|-----------------------------------|---------|
| `doc_A` synthesis output | 0 | PASS |
| `doc_C` synthesis output | 0 | PASS |
| `doc_B` synthesis output | 0 | PASS |
| This aggregate report | 0 / 126715 | PASS |

Leak audit method: generate overlapping 40-char windows (stride 20–25) over each corpus's `full_text`, then substring-search the artifact. A corpus-chunk present un-redacted = a leak. **Zero** across all committed artifacts. The raw per-corpus JSONs (state snapshots) under `evaluation/results/fb37/` are gitignored as raw runs; their `raw_text`/`raw_text_snippet` fields were purged in post-process for discipline, and nothing from them is propagated into this report.

Opaque IDs only: `doc_A`/`doc_C`/`doc_B`, `Speaker_*`, `State_*`, `arg_*`. No source names (author, title, date, venue, party) appear in this report, the commits, or the dashboard posts.

## 6. Methodology

- **Harness** (`scripts/run_fb37_capstone.py`, untracked — references the encrypted dataset path): per-corpus `spectacular`+`full` under hard `asyncio.wait_for` ceilings, corpus loaded in-memory via `derive_encryption_key`/`load_extract_definitions`. Global redact-filter over corpus chunks + redacted stdout wrapper + no-full-traceback exception handler (FB-36 privacy-hardening pattern).
- **Post-process** (untracked): re-extract `fallacy_count`/`argument_count`/`belief_set_count` from `state_snapshot` (the canonical richness source), purge `raw_text` snippets from the per-corpus JSONs, emit the opaque aggregate.
- **Anti-runaway**: per-corpus hard timeout (no unbounded >2h run possible — the FB-36 recursion fix + the ceilings bound every run).
- **No pipeline code change** beyond the untracked harness. This is a RUN + REPORT capstone.

## 7. What this unblocks

With the terminal full spectacular deliverable produced (bounded, opaque, formal-verified, synthesis-complete) on all three corpora including the hard `doc_A`, the Epic #947 technical work is complete. The remaining gate is the **user's EDGES-verdict arbitration** for formal Epic closure: the user now has the concrete artifact (this report + the gitignored per-corpus spectacular outputs) to arbitrate whether the spectacular deliverable meets the Epic's trustworthy-measurement bar.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
