# FP-9 — External-Solver Cluster-Wide Audit (Epic #1191)

**Scope:** read-only audit of the 3 external formal solvers wired through Tweety, after PR #1202 (EProver fix) landed on `029bdf7c`.
**Machine:** `myia-po-2023` (worker).
**Tracking issue:** #1205.
**Date:** 2026-06-20.

## Context — the static-method API-drift class

PR #1202 (po-2025, merged) fixed the EProver 3-layer regression. Root cause: the legacy *static* API
`EFOLReasoner.setPathToEProver()` / `ClingoSolver.setPathToClingo()` / `SPASSMlReasoner.setPathToSpass()`
was removed in Tweety 1.28+ (now **instance** methods). Every call raised `AttributeError`, silently
swallowed by `except Exception: logger.debug(...)` → no external solver was ever wired, yet the pipeline
reported the configured solver name as if active (formal theater, #1019).

The fix introduced a module-level `EXTERNAL_TOOL_PATHS` registry (`jvm_setup.py:54`) populated by
`_configure_external_tools` (`jvm_setup.py:660-759`), and an EProver **consumer** in `fol_handler.py`
that reads the registry and passes the path to the `EFOLReasoner(path)` ctor.

## Audit question

po-2025's PROPOSAL (R454) flagged: *"Clingo `setPathToClingo` is also now an instance method — check
whether ASP is also unwired (same potential bug). User mandate: 'there must be others'."*

**Which external solvers still have the bug?**

## Method (verify-the-verification, not memo)

1. `git grep "EXTERNAL_TOOL_PATHS"` → enumerate consumers of the registry.
2. Read the actual handler source for each solver's reasoner instantiation.
3. Confirm against the bundled Tweety 1.28/1.29 JARs present in `libs/`.

## Findings — per solver

### EProver (FOL) — ✅ FIXED (#1202, `029bdf7c`)

`fol_handler.py:24-26` reads `EXTERNAL_TOOL_PATHS.get("eprover")`; `_fol_*_with_eprover` builds
`EFOLReasoner(path)`; sync `check_consistency` dispatches on `settings.solver == EPROVER`.
Firsthand E2E-verified by ai-01 R454 (inconsistent → `(False, '(EProver): inconsistent')`).

### Clingo (ASP) — ✅ UNAFFECTED (pre-existing Python bypass)

**Not the same bug.** `core/integration/tweety_clingo_utils.py` already bypasses the buggy
`ClingoSolver` Java API:
- `check_clingo_installed_python_way(clingo_exe_path, jpype)` (line 14) — subprocess `--version` check.
- `get_clingo_models_python_way(clingo_exe_path, ...)` (line 44) — subprocess to the binary directly.

Documented at line 11: *"Fonctions Helper pour contourner les appels ClingoSolver défectueux."*
Binary present on po-2023: `ext_tools/clingo/clingo.exe` (3.4 MB), auto-downloaded by `download_clingo`.

**Conclusion:** ASP was never victim of the static-method drift because it never went through the
Tweety Java reasoner for execution — only for parsing. No action needed.

### SPASS (Modal) — ❌ RESIDUAL BUG (this audit, #1205)

**Same no-arg ctor bug that EProver had pre-fix.** `modal_handler.py:36-48`:

```python
def _get_spass_reasoner(self):
    if self._spass_reasoner is None:
        try:
            SPASSMlReasoner = jpype.JClass(
                "org.tweetyproject.logics.ml.reasoner.SPASSMlReasoner"
            )
            self._spass_reasoner = SPASSMlReasoner()   # ← no-arg ctor (bug)
        except Exception as e:
            logger.warning(f"Failed to load SPASSMlReasoner: {e}")
            raise RuntimeError(f"SPASS reasoner not available: {e}") from e
    return self._spass_reasoner
```

- The detected SPASS path (`EXTERNAL_TOOL_PATHS["spass"]`, `jvm_setup.py:716-722`) is **never passed**
  to the ctor.
- Under Tweety 1.28+, `SPASSMlReasoner` ctor requires the binary path (same API-drift family as
  `EFOLReasoner`). `SPASSMlReasoner()` raises → `except` swallows → `RuntimeError` →
  `_get_active_reasoner` (`modal_handler.py:50-54`) returns the degraded `SimpleMlReasoner`, or the
  orchestrator degrades the whole modal axis to `None`.
- Net: **the SPASS path is never wired**, mirroring the EProver theater R454 exactly.
- Corroboration: ai-01 R452 firsthand observed `modalities: none_detected` / `valid: None` on a
  corpus saturated with must/cannot/should — consistent with a never-wired SPASS reasoner.

**Consumer gap proof:** `git grep "EXTERNAL_TOOL_PATHS"` returns only `fol_handler.py` (EProver) +
`jvm_setup.py` (producer). Modal handler does NOT read the registry.

## Binary availability across the cluster (observed on po-2023)

| Solver | po-2023 | Notes |
|--------|---------|-------|
| EProver | ❌ absent | `ext_tools/` gitignored; ai-01 has it locally (R454) |
| SPASS | ❌ absent | manual install per `jvm_setup.py:399` |
| Clingo | ✅ present | auto-download works |
| Prover9 | ✅ bundled in `libs/prover9/bin/prover9.exe` (518 KB, **committed**) | FP-8 runner (#1203) tested against it |

> Note: `libs/prover9/bin/prover9.exe.original` (518 KB) sits beside the `.exe` — someone patched the
> binary at some point. Not investigated here (out of audit scope); flagging for awareness.

## Recommendation (not implemented — gated on SPASS binary)

The SPASS binary is absent on po-2023 and ai-01, so the fix cannot be E2E-verified firsthand here.
Fix shape (mirror the EProver consumer in `fol_handler.py`):

```python
def _get_spass_reasoner(self):
    if self._spass_reasoner is None:
        try:
            from argumentation_analysis.core.jvm_setup import EXTERNAL_TOOL_PATHS
            spass_path = EXTERNAL_TOOL_PATHS.get("spass")
            if not spass_path:
                raise RuntimeError(
                    "SPASS binary not detected (EXTERNAL_TOOL_PATHS['spass'] unset); "
                    "modal axis degraded to SimpleMlReasoner."
                )
            SPASSMlReasoner = jpype.JClass(
                "org.tweetyproject.logics.ml.reasoner.SPASSMlReasoner"
            )
            # VERIFY the exact 1.28+/1.29 ctor signature via jpype before committing.
            JString = jpype.JClass("java.lang.String")
            self._spass_reasoner = SPASSMlReasoner(JString(spass_path))
        except Exception as e:
            logger.warning(f"Failed to load SPASSMlReasoner: {e}")
            raise RuntimeError(f"SPASS reasoner not available: {e}") from e
    return self._spass_reasoner
```

Plus a contract test pinning dispatch + fail-loud (mirror EProver contract tests in #1202).
**Should be implemented on a machine with the SPASS binary**, or gated on SPASS availability.

## Summary

Of the 3 external formal solvers:
- **EProver (FOL)**: ✅ fixed (#1202).
- **Clingo (ASP)**: ✅ unaffected (pre-existing Python subprocess bypass).
- **SPASS (Modal)**: ❌ residual no-arg ctor bug (#1205) — the last external-solver theater of the
  static-method-API-drift class flagged by po-2025's PROPOSAL.

This closes the **modal axis wiring gap** of Epic #1191 (blind-spot elimination).
