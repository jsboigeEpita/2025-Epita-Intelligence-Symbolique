# Audit A-04: JTMS/ATMS

**Issue**: #164 (ATMS) | **SUIVI**: Score 85% | **Date audit**: 2026-05-31

## Status: 🟢 Integrated

The JTMS/ATMS system is fully integrated into the core platform. Both the JTMS belief maintenance engine and the ATMS extension are present, registered, and wired into the pipeline.

## What was delivered (student source)

- `1.4.1-JTMS/` — Student project directory with original JTMS implementation
- Belief and Justification data structures for truth maintenance
- ATMS (Assumption-based Truth Maintenance System) extension (#164)

## What exists in `argumentation_analysis/`

| Layer | File | Detail |
|---|---|---|
| Core JTMS | `services/jtms/jtms_core.py` | `Belief`, `Justification`, `JTMS` classes |
| ATMS extension | `services/jtms/atms_core.py` | ATMS implementation (PR #164) |
| Extended belief | `services/jtms/extended_belief.py` | Extended belief model |
| Conflict resolution | `services/jtms/conflict_resolution.py` | Belief conflict resolution logic |
| SK Plugin (legacy) | `plugins/semantic_kernel/jtms_plugin.py` | `@kernel_function` JTMS tools |
| SK Plugin (ATMS) | `plugins/atms_plugin.py` | `@kernel_function` ATMS tools |
| API routes | `api/jtms_endpoints.py` | REST + WebSocket endpoints for JTMS |
| State | `core/shared_state.py` | `jtms_beliefs` field + `add_jtms_belief()` method + `jtms_retraction_chain` |
| Registry | `orchestration/registry_setup.py:172-185` | `jtms_service` registered with capabilities `belief_maintenance`, `truth_maintenance`, `jtms_reasoning` |
| SK Integration | `integrations/semantic_kernel_integration.py` | Plugin wiring |
| Docs | `README_JTMS_PLUGIN.md` | Plugin documentation |

## Preservation Assessment

- Belief data model: **PRESENT** — `Belief` class with justification tracking
- Justification chains: **PRESENT** — `Justification` class with support/invalidation
- Retraction propagation: **PRESENT** — `jtms_retraction_chain` in shared state
- ATMS assumptions: **PRESENT** — `atms_core.py` + dedicated plugin
- SK kernel functions: **PRESENT** — both JTMS and ATMS plugins with `@kernel_function`
- REST/WebSocket API: **PRESENT** — full CRUD endpoints
- State integration: **PRESENT** — `add_jtms_belief()` with ID generation and metadata

## Gap Analysis

- **No critical gaps.** The 85% score reflects the fact that the original student code lives in `1.4.1-JTMS/` and the in-house version in `services/jtms/` may have diverged from the student's exact API surface.
- The ATMS extension was added separately (#164) and may not exercise all ATMS features from the student spec.

## Recommended Action

**No work needed.** Score is accurate. Consider:
- Adding a round-trip integration test that exercises JTMS belief → retraction → ATMS environment expansion
- Documenting any API differences between `1.4.1-JTMS/` student source and `services/jtms/` production code

## Source Files

- `argumentation_analysis/services/jtms/jtms_core.py`
- `argumentation_analysis/services/jtms/atms_core.py`
- `argumentation_analysis/services/jtms/extended_belief.py`
- `argumentation_analysis/services/jtms/conflict_resolution.py`
- `argumentation_analysis/plugins/semantic_kernel/jtms_plugin.py`
- `argumentation_analysis/plugins/atms_plugin.py`
- `argumentation_analysis/api/jtms_endpoints.py`
- `argumentation_analysis/core/shared_state.py` (lines 29, 400-402, 525-530)
- `argumentation_analysis/orchestration/registry_setup.py` (lines 172-185)
