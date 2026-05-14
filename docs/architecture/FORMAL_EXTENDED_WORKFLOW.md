# Formal Extended Workflow (#480)

## Overview

The `formal_extended` workflow chains all Tweety formal extensions into a single analysis pipeline. It is designed to produce the richest possible formal analysis output by leveraging every registered handler.

## Architecture

```
extract → nl_to_logic → pl → fol → modal → dung_extensions
                                                  ↓
                                    ┌─────────────┼─────────────┐
                                    ↓             ↓             ↓
                                  aspic          aba           adf
                                    ↓             ↓             ↓
                                  dialogue  bipolar ←──── ranking
                                                              ↓
                                                        probabilistic

fol + modal → belief_revision → tweety_interpretation ← (aggregates all)
```

## DAG Levels

| Level | Phase | Capability | Depends On | Optional |
|-------|-------|-----------|------------|----------|
| L0 | `extract` | `fact_extraction` | — | No |
| L1 | `nl_to_logic` | `nl_to_logic_translation` | extract | Yes |
| L2 | `pl` | `propositional_logic` | nl_to_logic | Yes |
| L3 | `fol` | `fol_reasoning` | nl_to_logic | Yes |
| L4 | `modal` | `modal_logic` | nl_to_logic | Yes |
| L5 | `dung_extensions` | `dung_extensions` | pl | Yes |
| L6 | `aspic` | `aspic_plus_reasoning` | dung_extensions | Yes |
| L7 | `aba` | `aba_reasoning` | dung_extensions | Yes |
| L8 | `adf` | `adf_reasoning` | dung_extensions | Yes |
| L9 | `bipolar` | `bipolar_argumentation` | dung_extensions | Yes |
| L10 | `ranking` | `ranking_semantics` | dung_extensions | Yes |
| L11 | `probabilistic` | `probabilistic_argumentation` | ranking | Yes |
| L12 | `dialogue` | `dialogue_protocols` | aspic | Yes |
| L13 | `belief_revision` | `belief_revision` | fol, modal | Yes |
| L14 | `tweety_interpretation` | `formal_result_interpretation` | dung, fol, aspic, ranking, belief_revision | Yes |

## Usage

```bash
# CLI
python argumentation_analysis/run_orchestration.py --file texte.txt --workflow formal_extended

# Python API
from argumentation_analysis.orchestration.workflows import get_workflow_catalog
catalog = get_workflow_catalog()
workflow = catalog["formal_extended"]
```

## Graceful Degradation

All phases except `extract` are optional. When the JVM is unavailable or a specific Tweety handler isn't registered, the workflow skips that phase and continues. This means:

- Without JVM: `pl`, `fol`, `modal`, `dung_extensions` and downstream phases use heuristic fallbacks
- Without `clingo`: ASP phases skip
- Without API keys: `nl_to_logic` skips, formal logic phases receive raw text

## Spectacular Workflow Extensions

Three new conditional phases were added to `build_spectacular_workflow()`:

| Phase | Capability | Depends On | Trigger |
|-------|-----------|------------|---------|
| `ranking` | `ranking_semantics` | dung_extensions | After Dung extensions computed |
| `bipolar` | `bipolar_argumentation` | counter | After counter-arguments generated |
| `probabilistic` | `probabilistic_argumentation` | hierarchical_fallacy | After fallacy detection with confidence |

These extend the spectacular workflow's coverage from ~28/32 to ~31/32 UnifiedAnalysisState fields.

## Related

- CoursIA notebooks 5/6/7a/7b (Belief-Revision, Abstract-Arg, Structured-Arg, Extended-Frameworks)
- Issue #480 — Wire 3-4 Tweety extensions into spectacular + formal_extended workflow
- `argumentation_analysis/orchestration/workflows.py` — Implementation
