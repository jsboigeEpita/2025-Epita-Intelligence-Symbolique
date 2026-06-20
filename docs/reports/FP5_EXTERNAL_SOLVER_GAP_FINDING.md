# FP-5 intercalaire — External-solver gap finding (cluster-wide regression)

**Track**: FP-5 #1196 (interrupted) · **Finding type**: infrastructure regression ·
**Priority**: URGENT (user-flagged) · **Author**: po-2025 · **Date**: 2026-06-20

> Aggregate-only / diagnostic. No corpus content. All findings empirically
> reproduced this session (0 LLM cost, pure solver plumbing).

## TL;DR

While running the FP-5 formal-richness matrix, the FOL axis returned
`degraded (None)` (the honest FP-3 outcome). Investigating *why* revealed that
**every configured external formal solver is absent or broken on this machine**.
The FOL layer has never produced a real decision — before FP-3 that was masked
as a fabricated `consistent=True`; now it is honest `degraded`, but the root
cause is **infrastructure, not algorithm**. This is very likely one of several
such "forgotten integrated components" the user flagged ("il doit y en avoir
d'autres").

## Empirical findings (verify-the-verification)

| Solver | Config | Binary present? | Works? |
|--------|--------|-----------------|--------|
| **EProver** (FOL) | `settings.solver=EPROVER` (default) | ❌ absent (`ext_tools/EProver/` missing, `shutil.which('eprover')=None`) | N/A |
| **SPASS** (modal) | `settings.modal_solver=SPASS` (default) | ❌ absent (`ext_tools/spass/` missing) | N/A |
| **Prover9** (FOL alt) | not selected | ✅ bundled `libs/prover9/bin/` | ❌ **broken** (format bugs) |
| **Clingo** (ASP) | auto-download | ✅ `ext_tools/clingo/clingo.exe` | not tested this turn |

### Evidence

1. **EProver absent + path not wired.**
   `jvm_setup._configure_external_tools` (lines 703-710) searches `eprover` on
   PATH or `ext_tools/EProver/eprover.exe` → neither exists. The async path
   `_fol_check_consistency_with_eprover` (fol_handler.py) would raise
   `RuntimeError` → fall back to Tweety → OOM. **Furthermore**, spectacular does
   not call that async path at all: `invoke_callables.py` routes
   `bridge.check_consistency(..., "first_order")` → sync
   `fol_handler.check_consistency` → Tweety direct → OOM. So even a correctly
   installed EProver would not be invoked for FOL consistency in spectacular.

2. **SPASS absent.** Same pattern (lines 694-701). Modal falls back to Tweety
   `SimpleMlReasoner` (no real decision procedure). Matches ai-01's R452
   firsthand constat: "modal valid=None" on a corpus saturated with
   must/cannot/should.

3. **Prover9 broken (3 format bugs).** The binary itself runs and decides
   (`prover9.exe` on `p ∧ ¬p` → `THEOREM PROVED` ✓). But `run_prover9`
   (prover9_runner.py) and `_fol_check_consistency_with_prover9`
   (fol_handler.py:307-327) are broken:
   - (a) calls the `.bat` wrapper whose exit code is misinterpreted by subprocess;
   - (b) generates a `goals.` section that Prover9 v2009-11A rejects
     (`Fatal error: Unrecognized command or list`);
   - (c) detects `"END OF PROOF"` but Prover9 emits `"THEOREM PROVED"`.

## Why not just add an auto-download script now?

The `download_clingo` model (jvm_setup.py:220) cannot be cleanly mirrored for
EProver:
- EProver official = build from source under Cygwin (no stable prebuilt Windows
  binary on its GitHub releases).
- `philzook58/pyeprover` ships a cosmopolitan binary committed in-repo (0 GitHub
  releases → no stable auto-download URL).
- Prover9 (the bundled alternative) is broken by format bugs, not merely absent.

→ This is an env/archi decision (which solver, pipeline wiring), not a simple
forgotten script. Escalated to coordinator ai-01 (msg
`msg-20260620T144259-xet3ar`).

## Open questions for coordinator (cluster-wide audit)

- **Q1 FOL solver**: EProver (config default, absent) vs Prover9 (bundled,
  runner-broken)? User wants EProver-vs-Prover9 verified "pour ne rien laisser
  au hasard".
- **Q2 Modal solver**: SPASS absent, no bundled alternative. Modal stays
  Tweety-only?
- **Q3 Proactive audit**: user suspects other forgotten integrated components.
  Coordinator to inventory all `settings.*_solver` + `ext_tools/` + `libs/`
  expectations across all cluster machines, not just po-2025.

## Immediate worker action available (pending ACK)

Fix the Prover9 runner (format bugs (a)(b)(c) above) — ~30 min, empirically
grounded, anti-pendule (repair the broken tool, not add a fallback), and
Prover9 is the fastest path to a FOL layer that actually decides. Recommended
direction (a) in the ASK. Awaits coordinator ACK before touching the runner.

## Anti-pendule / anti-theater notes

- This finding is the *honest* version of what FP-3 surfaced: FP-3 made the
  FOL verdict honest (`degraded`), this finding shows the verdict is degraded
  because the infrastructure is missing, not because FOL is undecidable.
- FP-5 was **interrupted** rather than allowed to report `fol→degraded` as if
  that were an accepted engineering state — measuring a gap-by-omission would
  be a subtle form of theater.
- No fallback was added. No fabricated output. Pure diagnostic.
