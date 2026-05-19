# SCDA Multi-Format Export Pipeline + Re-Prompt Trace Extraction

**Date:** 2026-05-19
**Issue:** #609 (Sprint 8 Track P)
**Depends on:** #605 (tool gating, merged `47f909ab`)

## 1. Summary

Two new reporting modules enabling spectacular multi-format export of the rich shared state and structured extraction of re-prompt traces from the growth validation hook.

## 2. MultiFormatExporter

**File:** `argumentation_analysis/reporting/multi_format_exporter.py`

Exports `UnifiedAnalysisState` into 6 formats:

| Format | Method | Output |
|--------|--------|--------|
| JSON | `to_json(pretty=True)` | Full state dict, all 30+ dimensions |
| XML | `to_xml()` | Hierarchical XML with arguments/fallacies/JTMS/Dung sections |
| Markdown | `to_markdown(sections=None)` | Rendered markdown with count headers |
| CSV bundle | `to_csv_bundle(out_dir)` | 6 CSVs: args, fallacies, quality, counter_args, debate, governance |
| HTML | `to_html(template='spectacular')` | Single-page with collapsible sections + summary cards |
| Rich terminal | `to_rich_terminal()` | Wraps existing `cli/output_formatter.render_state_snapshot()` |

**Design:** Lazy snapshot caching — `get_state_snapshot()` called once, cached until `_reset_cache()`.

## 3. RepromptTraceExtractor

**File:** `argumentation_analysis/reporting/reprompt_trace.py`

Captures structured `RepromptTrace` records from growth validation re-prompt events:

- `RepromptTrace` dataclass: phase_name, turn, attempt_idx, fingerprint_before/after, delta, outcome, agent_name
- Outcomes: `"ok"` (growth achieved), `"reran"` (re-prompted again), `"gave_up"` (limit reached)
- `to_json()` / `to_markdown()` for reporting
- `from_phase_log()` for reconstructing traces from existing phase logs

## 4. Orchestrator Integration

**File:** `argumentation_analysis/orchestration/conversational_orchestrator.py`

New parameter `enable_reprompt_tracing: bool = False` (opt-in, backward compat):

- Creates `RepromptTraceExtractor` when enabled
- Passes to `_run_phase()` via new `reprompt_extractor` parameter
- Records trace on each re-prompt fire (both AgentGroupChat and round-robin paths)
- Includes `reprompt_traces` in result dict

## 5. CLI

**File:** `scripts/analysis/export_scda_state.py`

```bash
python scripts/analysis/export_scda_state.py --state state.json --format json --out outputs/
python scripts/analysis/export_scda_state.py --state state.json --format all --out outputs/
```

## 6. Test Coverage

| File | Tests | Status |
|------|-------|--------|
| `test_multi_format_exporter.py` | 14 (JSON:3, XML:3, MD:3, CSV:2, HTML:3, Rich:1, Cache:1) | GREEN |
| `test_reprompt_trace.py` | 11 (Trace:5, Extractor:6) | GREEN |
| **Total** | **27** | **27 passed** |

Regression: 358/358 reporting tests passed, 0 failures.

## 7. Files Changed

| File | Action | LOC |
|------|--------|-----|
| `argumentation_analysis/reporting/multi_format_exporter.py` | NEW | ~320 |
| `argumentation_analysis/reporting/reprompt_trace.py` | NEW | ~220 |
| `scripts/analysis/export_scda_state.py` | NEW | ~80 |
| `tests/unit/.../test_multi_format_exporter.py` | NEW | ~140 |
| `tests/unit/.../test_reprompt_trace.py` | NEW | ~120 |
| `argumentation_analysis/orchestration/conversational_orchestrator.py` | MOD | +30 |
| **Total** | | **~910** |

## 8. DoD Status

- [x] `MultiFormatExporter` with 6 formats (JSON, XML, Markdown, CSV, HTML, Rich terminal)
- [x] `RepromptTraceExtractor` with structured trace capture
- [x] CLI `export_scda_state.py`
- [x] Orchestrator integration via `enable_reprompt_tracing` flag
- [x] 27 unit tests, all GREEN
- [x] No regressions (358/358 reporting tests pass)
- [x] Backward compatible (opt-in flags, default off)
- [x] Privacy: opaque IDs only in export templates
