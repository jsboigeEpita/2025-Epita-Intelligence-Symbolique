# Orchestration Mode Depth-Parity — Trade-off Documented (C3 #1500)

**Track C3 of #1500** (Epic: rigorous apples-to-apples comparison of the 4 orchestration modes). Generated from firsthand structural introspection (po-2023, env `projet-is`).

## TL;DR

The 4 orchestration modes are **comparable in interface** (all produce a verdict on the same synthetic input) but **NOT in work-perimeter**. They occupy three different depth dimensions. This asymmetry is a **deliberate design trade-off, not a defect**: aligning the catalogue would be a pendulum swing the project rejects (anti-#1019). This document makes the trade-off explicit and firsthand-chiffred — the honest C3 deliverable.

## The depth asymmetry (firsthand chiffres)

| Mode | Depth dimension | Count | Nature |
|------|-----------------|-------|--------|
| `pipeline_light` | workflow phases (DAG) | 3 | breadth |
| `pipeline_standard` | workflow phases (DAG) | 15 | breadth |
| `pipeline_full` | workflow phases (DAG) | 17 | breadth |
| `hierarchical_bridge` | strategic objectives (default axes) | 4 | delegation |
| `hierarchical_delegation` | strategic objectives (LLM-derived, measured) | 4–4 objectives → 5–5 tasks (n=3, corpus_A/B/C) | delegation (3-tier depth) |
| `conversational` | dialogue macro-phases (multi-turn) | 3 | dialogue-depth |
| `conversation_deterministic` | dialogue macro-phases (deterministic) | 3 | dialogue-depth (no LLM) |

The pipeline breadth chiffres are **verified firsthand** by introspecting the real workflow builders (`build_light_workflow` / `build_standard_workflow` / `build_full_workflow` in [`argumentation_analysis/orchestration/workflows.py`](../../argumentation_analysis/orchestration/workflows.py)) — not hand-written constants. The hierarchical `4` is the documented M2-bridge default ([`delegation_orchestrator.py`](../../argumentation_analysis/orchestration/hierarchical/delegation_orchestrator.py) — "the M2 bridge would inject 4 default objectives"). The conversational `3` is the macro-phase count (informal → formal → synthesis).

The `hierarchical_delegation` row is **not** a structural constant — its strategic tier is LLM-driven, so the objective/task count is a **firsthand-measured range** over ≥3 inputs (see [Delegation depth chiffrage](#delegation-depth-chiffrage-firsthand) below). It is injected into the deterministic render path as a constant + provenance (no LLM call at render time).

## Three depth dimensions, not one common scale

The modes do **not** share a single depth axis. The `depth_dimension` column names what each count measures:

- **Pipeline = breadth.** A wide capability catalogue (registry exposes ~50 capabilities; the workflows exercise a subset per workflow). Each phase is shallow-per-capability. The verdict is the aggregation of many per-capability micro-verdicts by `WorkflowExecutor`.
- **Hierarchical = delegation.** A narrow set of strategic objectives (4 default axes for the bridge; LLM-derived for the delegation tier), decomposed through the Strategic → Tactical → Operational chain. Depth comes from the 3-tier decomposition, not from capability count.
- **Conversational = dialogue-depth.** Few macro-phases, but each is a deep multi-agent `AgentGroupChat` dialogue (unbounded turn count — bounded in wall-time by C1 #1500). Depth comes from turn-level exchange, not from phase count.

## Why "align the catalogue" is rejected (anti-pendule, anti-#1019)

The R653 reframe of the parent Epic falsified the idea that a mode was "dormant" — all 4 modes are already `--mode`-selectable. The depth asymmetry is the *next* layer of honesty: even with all modes selectable, they are not comparable in work-perimeter.

Two alignment strategies were considered and **rejected**:

1. **Gut pipeline's breadth** to match hierarchical/conversational (e.g. trim `standard` from 15 to ~4 phases). Rejected: the pipeline's breadth is its purpose — it is the "full analysis" surface. Trimming it destroys capability (pendulum subtract).
2. **Inflate hierarchical/conversational** to match pipeline's phase count (e.g. fabricate 15 "phases" inside the hierarchical chain). Rejected: this is exactly the theatre #1019 forbids — cosmetic phases that look comparable but do no genuine work (pendulum add).

Both swings move the problem to the other extreme. The equilibrium is reached by **documenting the trade-off** (this doc + the `--depth-parity` report section), not by adding a counterweight.

## Delegation depth chiffrage (firsthand)

Unlike the pipeline's deterministic phase count (introspected statically), the delegation mode's strategic tier is **LLM-driven** — the objective/task count *could* vary per input. The chiffre is therefore a **measured range** over ≥3 benchmark corpora, not a structural constant. Firsthand R711 measurement (po-2023, env `projet-is`, post-CC #1531 corpus fix — so the operational tier received the real text):

| Corpus | Objectives | Tasks | Completed | Failed | Success rate | Wall-time |
|--------|-----------:|------:|----------:|-------:|-------------:|----------:|
| `corpus_A` | 4 | 5 | 5 | 0 | 1.0 | 127.2s |
| `corpus_B` | 4 | 5 | 5 | 0 | 1.0 | 109.5s |
| `corpus_C` | 4 | 5 | 5 | 0 | 1.0 | 95.5s |

**Result: a degenerate range `4–4` objectives → `5–5` tasks (n=3).** This is the honest finding, not a failed measurement: on these inputs the LLM-derived delegation tier goes **no deeper** than the 4 hardcoded bridge axes — it produced exactly them (obj-1 decomposes into 2 tasks, hence 5). The non-differentiation is itself the DoD-3 deliverable (the DoD allows "documented as a trade-off" over "aligned"). Written as the range `4–4` rather than the int `4` so a reader sees it is a *measured distribution* (that happens to be degenerate), not a structural constant disguised as a measurement.

**Reader fold-in (coord R710 FINDING):** pre-C3, `run_hierarchical_delegation_mode` read `result["summary"]` and `result["capabilities_used"]` — two keys `DelegationOrchestrator.analyze` never emits — so the report line showed `0/0` phases and `0.0%` fill on a run where 5 tasks really executed. Those zeros were **unread fields, not measurements**. C3 reads the real keys (`tasks_created` → phase denominator; `operational_results[].status` → completed/failed numerator; `evaluation["overall_success_rate"]`), so the Phases column now reflects the work performed.

## Reproducing the chiffres

The depth-parity table is generated deterministically (JVM/LLM-free) by the orchestration-mode harness:

```bash
# Print ONLY the depth-parity trade-off section (fast, no mode runs):
python scripts/compare_orchestration_modes.py --depth-parity

# The depth-parity section is also appended to EVERY full comparison report:
python scripts/compare_orchestration_modes.py --output report.md
```

The underlying functions are `compute_depth_parity()` and `render_depth_parity_section()` in [`scripts/compare_orchestration_modes.py`](../../scripts/compare_orchestration_modes.py). The chiffres are re-introspected on every call — if a workflow gains or loses a phase, the table and the unit tests ([`test_depth_parity_1500.py`](../../tests/unit/argumentation_analysis/orchestration/test_depth_parity_1500.py)) update/surface the drift (no silent staleness).

## What this means for the mode comparison

- The modes ARE comparable on: **termination** (C1 bounds conversational), **broadcast delivery** (C2 repairs the shared bus), and **decision** (does the mode emit a verdict). These are the Trade-off Summary columns of the harness report.
- The modes are NOT comparable on: **work-perimeter depth**. The depth-parity section makes this explicit so a reader of the comparison report does not mistake "pipeline ran 15 phases" for "pipeline is 5× better than hierarchical" — the phases measure a different dimension than the objectives/turns.

## Discipline

- **Privacy HARD**: the chiffres are structural (phase/objective/macro-phase counts), not corpus-derived. No corpus names, no raw text — the comparison runs on synthetic opaque IDs (`corpus_A/B/C`).
- **Anti-pendule**: reuses the existing workflow builders + the documented hierarchical/conversational constants; no new mode, no catalogue inflation/deflation.
- **Anti-#1019**: the verdict makes the asymmetry explicit as a deliberate trade-off; nothing is faked into parity.

## References

- Parent Epic: #1500 (rigorous 4-mode comparison). Track C3 = this document.
- Harness: BO-4 #1480 (`scripts/compare_orchestration_modes.py`).
- R653 firsthand mode-comparison (the asymmetry observation).
- Related tracks: C1 (bounded conversational termination), C2 (shared broadcast bus).
