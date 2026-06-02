# TRACK-counter-strategy — Design Spec

**ID**: TRACK-counter-strategy
**Issue**: #901 (North-Star, po-2023 lane)
**Effort**: S (~120 LOC)
**Owner**: po-2023 (conceptual, non-argparse → po-2025 implements CLI)
**Date**: 2026-06-02

---

## Summary

Expose the 5 rhetorical counter-argument strategies as a selectable `--counter-strategy` parameter, allowing users to force a specific strategy or use the default auto-selection logic.

---

## Current State

### Strategies (5)

Defined in `argumentation_analysis/agents/core/counter_argument/definitions.py`:

| Strategy | Enum | Description |
|----------|------|-------------|
| Socratic Questioning | `SOCRATIC_QUESTIONING` | Challenge assumptions through targeted questions |
| Reductio ad Absurdum | `REDUCTIO_AD_ABSURDUM` | Show the argument leads to absurd consequences |
| Analogical Counter | `ANALOGICAL_COUNTER` | Use analogies to illustrate flaws |
| Authority Appeal | `AUTHORITY_APPEAL` | Cite experts/research contradicting the claim |
| Statistical Evidence | `STATISTICAL_EVIDENCE` | Use data/studies to contradict |

### Auto-Selection Logic

`RhetoricalStrategies.suggest_strategy(argument_type, content)` in `strategies.py` picks based on:
- Content keywords (`"statistique"` → STATISTICAL_EVIDENCE, `"tous"` → ANALOGICAL_COUNTER)
- Argument type mapping (`deductive` → REDUCTIO_AD_ABSURDUM, etc.)
- Default fallback → SOCRATIC_QUESTIONING

### Current Wiring

- `_invoke_counter_argument()` in `invoke_callables.py:979` — uses `plugin.suggest_strategy()` then `plugin.generate_counter_argument()`
- No CLI flag, no context parameter, no way to force a specific strategy
- The `suggest_strategy()` result is used to pick the template, but LLM enrichment can override

---

## Proposed Design

### CLI Signature

```bash
python -m argumentation_analysis.run_orchestration \
  --mode pipeline \
  --counter-strategy auto           # default: auto-selection
  --counter-strategy socratic       # force Socratic questioning
  --counter-strategy reductio       # force Reductio ad Absurdum
  --counter-strategy analogy        # force Analogical Counter
  --counter-strategy authority      # force Authority Appeal
  --counter-strategy statistical    # force Statistical Evidence
```

### Choices

| Value | Strategy | Effect |
|-------|----------|--------|
| `auto` (default) | Auto-selected | Current behavior unchanged |
| `socratic` | `SOCRATIC_QUESTIONING` | Force Socratic method |
| `reductio` | `REDUCTIO_AD_ABSURDUM` | Force reductio ad absurdum |
| `analogy` | `ANALOGICAL_COUNTER` | Force analogical counter |
| `authority` | `AUTHORITY_APPEAL` | Force authority appeal |
| `statistical` | `STATISTICAL_EVIDENCE` | Force statistical evidence |

### Context Propagation

```python
# run_orchestration.py
parser.add_argument(
    "--counter-strategy",
    choices=["auto", "socratic", "reductio", "analogy", "authority", "statistical"],
    default="auto",
)
context["counter_strategy"] = args.counter_strategy
```

### Pipeline Dispatch

In `_invoke_counter_argument()` (invoke_callables.py:979):

```python
# After plugin instantiation:
forced_strategy = context.get("counter_strategy", "auto")
if forced_strategy != "auto":
    from argumentation_analysis.agents.core.counter_argument.definitions import RhetoricalStrategy
    strategy_map = {
        "socratic": RhetoricalStrategy.SOCRATIC_QUESTIONING,
        "reductio": RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
        "analogy": RhetoricalStrategy.ANALOGICAL_COUNTER,
        "authority": RhetoricalStrategy.AUTHORITY_APPEAL,
        "statistical": RhetoricalStrategy.STATISTICAL_EVIDENCE,
    }
    # Override auto-selection with forced strategy
    strategy = {"strategy": strategy_map[forced_strategy].value}
```

### Point of Wiring

- **CLI**: `run_orchestration.py` → `argparse` (1 argument)
- **Context**: `run_unified_analysis(context={"counter_strategy": ...})`
- **Dispatch**: `_invoke_counter_argument()` line ~990, after `plugin.suggest_strategy()`
- **Tests**: `tests/unit/argumentation_analysis/test_counter_strategy_selector.py`

### LOC Estimate

| Change | LOC |
|--------|-----|
| argparse addition | 6 |
| context propagation | 1 |
| dispatch logic in invoke_callables | 15 |
| tests (6 parametrized) | 90 |
| **Total** | **~112** |

---

## Backward Compatibility

- Default `auto` = exact current behavior (no breaking change)
- Forced strategies only change the template selection; LLM enrichment still runs
- No changes to `RhetoricalStrategies` class or `definitions.py`

---

## Questions for User

1. **Naming**: `--counter-strategy` or `--rhetorical-strategy`? (Currently `--counter-strategy` feels more user-facing)
2. **Multiple strategies**: Should we support `--counter-strategy socratic,statistical` (apply multiple strategies to different arguments)? Or single-only for simplicity?
3. **Auto-mode enhancement**: Should `auto` also consider fallacy types (e.g., `Appeal to Authority` → `AUTHORITY_APPEAL` strategy)?
