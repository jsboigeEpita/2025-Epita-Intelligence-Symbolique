# Tests: Hierarchical Orchestration Mode

## Status: DORMANT

The hierarchical orchestration mode (Strategic → Tactical → Operational) is **not activated** in the current pipeline. It is defined in `argumentation_analysis/orchestration/hierarchical/` but never wired into `CapabilityRegistry` or any active workflow.

All tests in this directory are **skipped** via `pytestmark = pytest.mark.skip("Hierarchical mode dormant — not in active pipeline (B-09 #798)")`.

## Test Coverage

| Directory | Files | Tests | Description |
|-----------|-------|-------|-------------|
| `strategic/`   | 3  | ~90  | Strategic planner, state, resource allocator          |
| `tactical/`    | 4  | ~120 | Tactical resolver (basic + advanced), state, progress |
| `operational/` | 2  | ~60  | Operational state, feedback mechanism                 |
| `templates/`   | 1  | ~32  | Task/situation/report templates                       |
| **Total**      | **10** | **~302** |                                                  |

## Activation Prerequisites

To reactivate these tests:
1. Wire `HierarchicalOrchestrator` into `CapabilityRegistry` (`registry_setup.py`)
2. Add a workflow phase in `WorkflowDSL` that uses the hierarchical mode
3. Remove the `pytestmark` line from each test file
4. Verify against a live hierarchical run

## Reference

- Audit report: `docs/reports/test_audit/B-09_orchestration.md`
- Issue: #798
- Epic: B-09 (#765)
- CLAUDE.md: Orchestration Modes → Hierarchical → DORMANT
