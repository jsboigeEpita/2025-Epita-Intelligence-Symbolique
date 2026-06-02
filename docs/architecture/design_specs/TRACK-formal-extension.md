# TRACK-formal-extension — Design Spec

**ID**: TRACK-formal-extension
**Issue**: #901 (North-Star, po-2023 lane)
**Effort**: M (~180 LOC)
**Owner**: po-2023 (conceptual, non-argparse → po-2025 implements CLI)
**Date**: 2026-06-02

---

## Summary

Expose the formal logic extension handlers (Tweety/JPype) as a selectable `--formal-extension` parameter, allowing users to pick which advanced formal reasoning capabilities run in the pipeline.

---

## Current State

### Formal Extension Handlers (17 invoke callables)

All in `argumentation_analysis/orchestration/invoke_callables.py`:

| Handler | Line | Capability | Status |
|---------|------|-----------|--------|
| `_invoke_ranking` | 2583 | `ranking` | Active in spectacular |
| `_invoke_bipolar` | 2641 | `bipolar` | Active in spectacular |
| `_invoke_aba` | 2667 | `aba` | Active in spectacular |
| `_invoke_adf` | 2697 | `adf` | Active in spectacular |
| `_invoke_aspic` | 2798 | `aspic_analysis` | Active in spectacular |
| `_invoke_probabilistic` | 2929 | `probabilistic` | Active in spectacular |
| `_invoke_dialogue` | 2968 | `dialogue_games` | Active in spectacular |
| `_invoke_dl` | 3087 | `description_logic` | Active in spectacular |
| `_invoke_cl` | 3124 | `cl` | Active in spectacular |
| `_invoke_sat` | 3162 | `sat` | Active in spectacular |
| `_invoke_setaf` | 3188 | `setaf` | Active in spectacular |
| `_invoke_weighted` | 3216 | `weighted` | Active in spectacular |
| `_invoke_social` | 3250 | `social` | Active in spectacular |
| `_invoke_eaf` | 3471 | `eaf` | Active in spectacular |
| `_invoke_delp` | 3496 | `delp` | Active in spectacular |
| `_invoke_qbf` | 3524 | `qbf` | Active in spectacular |
| `_invoke_asp_reasoning` | 3555 | `asp_reasoning` | Active in spectacular |

### Base Formal Phases (always run in spectacular)

| Handler | Line | Capability |
|---------|------|-----------|
| `_invoke_propositional_logic` | 4465 | `pl` |
| `_invoke_fol_reasoning` | 4866 | `fol` |
| `_invoke_modal_logic` | 5318 | `modal` |
| `_invoke_dung_extensions` | 5405 | `dung_extensions` |

### Wiring

- All 17 are registered as capabilities in `registry_setup.py` and appear as phases in the `spectacular` workflow
- They require JPype/Tweety JVM — skipped gracefully if unavailable
- No CLI flag to enable/disable individual extensions

---

## Proposed Design

### CLI Signature

```bash
python -m argumentation_analysis.run_orchestration \
  --formal-extension all              # default: run all 17
  --formal-extension core             # only base 4 (pl, fol, modal, dung)
  --formal-extension ranking,bipolar  # specific subset
  --formal-extension none             # skip all formal extensions
```

### Extension Groups

| Group | Extensions | Description |
|-------|-----------|-------------|
| `core` | pl, fol, modal, dung_extensions | Always-run base formal phases |
| `dung-family` | ranking, bipolar, setaf, weighted, social, eaf | Dung semantics variants |
| `structured` | aspic, aba, adf, delp | Structured argumentation |
| `logic-extended` | dl, cl, sat, qbf, asp, dialogue, probabilistic | Advanced logic |

### CLI Choices

```
--formal-extension all|core|none|<comma-separated-list>
```

Default: `all` (current behavior — no breaking change).

### Context Propagation

```python
# run_orchestration.py
parser.add_argument(
    "--formal-extension",
    default="all",
    help="Formal extensions to run: all, core, none, or comma-separated list",
)
context["formal_extension_filter"] = args.formal_extension
```

### Pipeline Dispatch

In the spectacular workflow builder (or `_invoke_*` callables):

```python
formal_filter = context.get("formal_extension_filter", "all")

if formal_filter == "none":
    # Skip all formal phases
    return {"status": "skipped", "reason": "formal_extension=none"}
elif formal_filter == "core":
    # Only run pl/fol/modal/dung, skip the 17 extensions
    if capability not in ("pl", "fol", "modal", "dung_extensions"):
        return {"status": "skipped", "reason": f"not in core: {capability}"}
elif formal_filter != "all":
    # Parse comma-separated list
    allowed = set(formal_filter.split(","))
    if capability not in allowed:
        return {"status": "skipped", "reason": f"not in filter: {capability}"}
```

### Point of Wiring

- **CLI**: `run_orchestration.py` → argparse (1 argument)
- **Context**: `run_unified_analysis(context={"formal_extension_filter": ...})`
- **Dispatch**: Each `_invoke_*` callable reads context at entry; OR workflow builder filters phases
- **Preferred**: Filter at workflow construction time (remove phases from WorkflowDefinition before execution)
- **Tests**: `tests/unit/argumentation_analysis/test_formal_extension_selector.py`

### LOC Estimate

| Change | LOC |
|--------|-----|
| argparse addition | 7 |
| context propagation | 1 |
| workflow phase filter function | 30 |
| invoke-callable guards (or workflow filter) | 25 |
| tests (8 parametrized) | 120 |
| **Total** | **~183** |

---

## Backward Compatibility

- Default `all` = exact current behavior
- `core` provides a fast path for CI (skip 17 Tweety phases, keep base 4)
- `none` enables pure-NLP pipeline (fallacy + quality + synthesis only)
- No changes to individual invoke callables — filter is at workflow level

---

## Implementation Notes

- **JVM dependency**: The `--formal-extension core` option reduces JVM load (4 phases instead of 21), useful for CI without JPype
- **Comma-separated parsing**: Validate against the 17 known extensions; error on unknown names
- **Workflow-level filtering** is cleaner than per-callable guards — modify `workflows.py` spectacular builder to respect the filter

---

## Questions for User

1. **Default**: Should `all` remain default, or should `core` be the new default (faster CI, fewer JVM crashes)?
2. **Group shortcuts**: Are the 4 groups (`core`, `dung-family`, `structured`, `logic-extended`) useful, or should we only support explicit comma-separated lists?
3. **Validation**: Should unknown extension names be a hard error, or silently ignored (with a warning)?
