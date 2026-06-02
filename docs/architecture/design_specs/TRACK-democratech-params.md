# TRACK-democratech-params — Design Spec

**ID**: TRACK-democratech-params
**Issue**: #901 (North-Star, po-2023 lane)
**Effort**: S (~90 LOC)
**Owner**: po-2023 (conceptual, non-argparse → po-2025 implements CLI)
**Date**: 2026-06-02

---

## Summary

Expose governance/voting parameters (`--vote-method`, `--consensus-threshold`) as CLI parameters, allowing users to select the voting algorithm and consensus threshold for the governance phase.

---

## Current State

### Voting Methods (7)

Defined in `argumentation_analysis/agents/core/governance/governance_methods.py`:

| Method | Function | Description |
|--------|----------|-------------|
| Majority | `majority_voting()` | Each agent votes top choice; most votes wins |
| Plurality | `plurality_voting()` | Alias for majority (single-winner) |
| Borda | `borda_count()` | Preference scoring: n-1 for top, n-2 for second, etc. |
| Condorcet | `condorcet_method()` | Pairwise comparison; Borda fallback if no winner |
| Quadratic | `quadratic_voting()` | Budget-based allocation with personality-aware spending |
| Byzantine | `byzantine_consensus()` | Fault-tolerant consensus with traitor tolerance |
| Raft | `raft_consensus()` | Leader-based distributed consensus |

### Governance Plugin

`argumentation_analysis/plugins/governance_plugin.py` exposes 6 `@kernel_function` methods:

| Method | Signature |
|--------|-----------|
| `detect_conflicts_fn` | `(positions_json) → conflicts_json` |
| `resolve_conflict_fn` | `(conflict_json, strategy) → resolution_json` |
| `compute_consensus_metrics` | `(results_json) → metrics_json` |
| `list_governance_methods` | `() → methods_json` |
| `social_choice_vote` | `(input_json with method) → winner_json` |
| `find_condorcet_winner` | `(input_json) → winner_json` |

### Current Wiring

- `_invoke_governance()` in `invoke_callables.py:1324` — hardcodes `method="copeland"` for social choice voting
- `resolve_conflict_fn()` hardcodes `strategy="collaborative"`
- No CLI flag, no context parameter
- `consensus_threshold` not exposed anywhere (hardcoded in metrics calculation)

---

## Proposed Design

### CLI Signature

```bash
python -m argumentation_analysis.run_orchestration \
  --vote-method majority           # default: copeland (current behavior)
  --vote-method borda
  --vote-method condorcet
  --vote-method quadratic
  --consensus-threshold 0.7        # default: 0.5 (50%)
```

### Vote Method Choices

| Value | Method | Description |
|-------|--------|-------------|
| `copeland` (default) | Copeland method | Current behavior (pairwise wins scoring) |
| `majority` | `majority_voting()` | Simple majority |
| `borda` | `borda_count()` | Preference-based scoring |
| `condorcet` | `condorcet_method()` | Pairwise comparison |
| `quadratic` | `quadratic_voting()` | Budget-based quadratic |
| `byzantine` | `byzantine_consensus()` | Fault-tolerant consensus |
| `raft` | `raft_consensus()` | Leader-based consensus |

### Context Propagation

```python
# run_orchestration.py
parser.add_argument(
    "--vote-method",
    choices=["copeland", "majority", "borda", "condorcet", "quadratic", "byzantine", "raft"],
    default="copeland",
)
parser.add_argument(
    "--consensus-threshold",
    type=float,
    default=0.5,
    help="Consensus threshold (0.0-1.0). Default: 0.5",
)
context["vote_method"] = args.vote_method
context["consensus_threshold"] = args.consensus_threshold
```

### Pipeline Dispatch

In `_invoke_governance()` (invoke_callables.py:1324):

```python
# Replace hardcoded "copeland":
vote_method = context.get("vote_method", "copeland")
vote_input = json.dumps({
    "method": vote_method,    # was: "copeland"
    "ballots": ballots,
    "options": options,
})
vote_result = json.loads(plugin.social_choice_vote(vote_input))

# Use consensus threshold in metrics:
consensus_threshold = context.get("consensus_threshold", 0.5)
metrics_json = plugin.compute_consensus_metrics(json.dumps({
    **vote_result,
    "threshold": consensus_threshold,
}))
```

### Point of Wiring

- **CLI**: `run_orchestration.py` → argparse (2 arguments)
- **Context**: `run_unified_analysis(context={"vote_method": ..., "consensus_threshold": ...})`
- **Dispatch**: `_invoke_governance()` lines ~1378 (vote method) and ~1383 (threshold)
- **Tests**: `tests/unit/argumentation_analysis/test_democratech_params.py`

### LOC Estimate

| Change | LOC |
|--------|-----|
| argparse additions (2 args) | 14 |
| context propagation | 2 |
| vote method dispatch | 5 |
| consensus threshold usage | 8 |
| tests (8 parametrized) | 65 |
| **Total** | **~94** |

---

## Backward Compatibility

- Default `copeland` = exact current behavior (no breaking change)
- Default `consensus_threshold=0.5` = 50% majority (standard)
- Governance phase is already optional in non-spectacular workflows

---

## Implementation Notes

- **Validation**: `--consensus-threshold` must be in [0.0, 1.0]; argparse `type=float` + validation in dispatch
- **Social choice**: `social_choice_vote()` already accepts a `method` field — just replace the hardcoded `"copeland"`
- **Plurality**: Excluded from choices (alias for majority, adds confusion)
- **Threshold**: Used in `compute_consensus_metrics()` to classify consensus as "achieved" or "failed"

---

## Questions for User

1. **Default method**: Keep `copeland` (current) or switch to `majority` (more intuitive)?
2. **Conflict resolution strategy**: Also expose as `--conflict-strategy collaborative|competitive|avoidant|compromising`? Or keep hardcoded `collaborative`?
3. **Agent count**: Should we expose `--governance-agents N` (number of simulated agents)? Currently hardcoded to `len(arguments[:6])`.
