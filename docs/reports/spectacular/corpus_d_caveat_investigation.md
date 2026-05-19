# Corpus D "0 Formal Arguments" Investigation

**Issue:** #621 | **Track:** T (Sprint 10) | **Date:** 2026-05-19
**Status:** Root cause identified — data plumbing bug, not pipeline failure

## Summary

Corpus D's SCDA pipeline **produced 16 arguments** and 17 fallacies. The "0 formal arguments" reported in the spectacular bundle is a reporting artefact caused by two independent bugs in the demo runner and bundle pipeline.

## Root Cause (2 bugs)

### Bug 1: Slim state snapshot (`summarize=True`)

The soutenance demo runner (`examples/soutenance/_shared.py:237`) calls:

```python
snap = state.get_state_snapshot(summarize=True)
```

This produces a **counts-only** snapshot (1.4 KB) where `identified_arguments` is absent and only `argument_count: 16` remains. The full audit pipeline (which generated A/B/C snapshots at 66 KB each) calls `get_state_snapshot(summarize=False)`, preserving the full argument content.

The bundle generator reads `state_snapshot.json` and accesses `state_data.get("identified_arguments", {})` → returns `{}` → reports 0 arguments.

### Bug 2: Wrong attribute name in metric extraction

`examples/soutenance/_shared.py:140`:

```python
args = getattr(state, "arguments", []) or []
```

The actual attribute on `UnifiedAnalysisState` is `identified_arguments`, not `arguments`. This means `arguments_found` in `summary.json` is always 0 for ALL corpora, not just D. The tolerance bands (e.g. 15±5 for D) were never actually validating argument counts.

## Evidence

| Source | What it shows |
|--------|---------------|
| `outputs/scda_audit/corpus_dense_D/state_snapshot.json` | `argument_count: 16`, `tasks_answered: ["task_extract_all_args", ...]` |
| `outputs/soutenance_demo/corpus_dense_D/deep_synthesis_report.md` | 16 arguments (arg_1...arg_16), 17 fallacies, Dung framework (24 nodes), 4 counter-args |
| `outputs/soutenance_demo/corpus_dense_D/state.json` | 1.4 KB slim summary (same as state_snapshot.json) |
| `outputs/scda_audit/corpus_dense_A/state_snapshot.json` | 66 KB rich snapshot with full `identified_arguments` dict |

## Hypotheses Evaluated

| # | Hypothesis | Verdict |
|---|-----------|---------|
| 1 | Long context verbosity (~99K chars) | **Partially valid** — long context may stress the LLM, but pipeline still extracted 16 args |
| 2 | Tool gating interaction | **Invalid** — tool gating is OFF by default; `add_identified_argument` always available to ExtractAgent |
| 3 | Growth hook misclassification | **Invalid** — growth hook correctly detected extraction phase and would re-prompt on zero growth; fingerprint showed growth (16 args) |
| 4 | Source-specific prompt failure | **Invalid** — ExtractAgent successfully called `add_identified_argument` 16 times per state counters |

## Impact Assessment

- **Bundle artefacts affected:** `corpus_D.{json,xml,md,html}`, `cross_ref_graph_corpus_D.*`, README table
- **Bundle artefacts NOT affected:** `soutenance_slides.md`, other corpora (A/B/C), `cross_ref_viz.html`
- **Pipeline correctness:** The SCDA pipeline itself worked correctly for D. All 4 phases ran, 16 args extracted, 17 fallacies detected, JTMS/Dung/counter-args activated.

## Recommended Fixes

### Fix 1 (High priority): `_shared.py` attribute name

```python
# Line 140: change "arguments" → "identified_arguments"
args = getattr(state, "identified_arguments", {}) or {}
metrics["arguments_found"] = len(args) if isinstance(args, dict) else len(args)
```

Same fix needed for `fallacies` → `identified_fallacies` (line 143), `jtms_beliefs` (line 146 OK), `counter_arguments` (line 149 OK).

### Fix 2 (High priority): Rich state snapshot for D

The soutenance demo runner should produce a full snapshot, not a summarized one:

```python
# Line 237: change summarize=True → summarize=False
snap = state.get_state_snapshot(summarize=False)
```

After this fix, re-run the bundle generator for corpus D to populate the full artefact set.

### Fix 3 (Low priority): Bundle generator defensive check

Add a warning in `generate_spectacular_bundle.py` when `identified_arguments` is empty but `argument_count > 0`:

```python
if not state_data.get("identified_arguments") and state_data.get("argument_count", 0) > 0:
    logger.warning(f"State snapshot has argument_count={state_data['argument_count']} "
                   f"but no identified_arguments content. Was summarize=True used?")
```

## Lessons Learned

1. **Never trust a single metric source.** The "0 args" was visible in the bundle, the README, and `summary.json` — but all three derived from the same broken snapshot.
2. **`get_state_snapshot(summarize=True)` discards content.** This is by design for quick summaries, but the soutenance runner should use `summarize=False` when the output feeds the bundle generator.
3. **Attribute name bugs are invisible when defaults hide them.** `getattr(state, "arguments", [])` silently returns `[]` because the attribute doesn't exist — no error raised.

## Reproduction

```bash
# Verify the slim snapshot
python -c "import json; d=json.load(open('outputs/scda_audit/corpus_dense_D/state_snapshot.json')); print(d.get('argument_count'), d.get('identified_arguments'))"
# Expected: 16, None

# Verify the rich synthesis
grep -c "arg_" outputs/soutenance_demo/corpus_dense_D/deep_synthesis_report.md
# Expected: many matches (16 unique args)
```

---
*Investigation by po-2023, Track T (#621), Sprint 10.*
