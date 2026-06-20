# FP-5 intercalaire — External-solver gap finding (cluster-wide regression)

**Track**: FP-5 #1196 (interrupted) · **Finding type**: infrastructure regression ·
**Priority**: URGENT (user-flagged) · **Author**: po-2025 · **Date**: 2026-06-20

> Aggregate-only / diagnostic. No corpus content. All findings empirically
> reproduced this session (0 LLM cost, pure solver plumbing).

## UPDATE 2026-06-20 (post-investigation correction) — EProver WAS available; the bug was silent API-drift, NOT a missing binary

The original finding below (TL;DR + table) concluded **EProver was absent**.
That conclusion was **wrong** and has been corrected by deeper investigation
(user challenge: *"eprover est régulièrement utilisé sur le dépôt CoursIA… tu
n'as pas bien investigué"*). The verified reality:

- **The EProver binary exists and works.** It is present in this repo's git
  history (`_archives/Argument_Analysis/ext_tools/EProver/eprover.exe`,
  commit `93bf136e`) and in the CoursIA reference repo (`E 2.0 Turzum`,
  4366144 bytes — identical). With its `cygwin1.dll` dependency, it runs and
  decides (`# Proof found!` on an inconsistent TPTP input).
- **The real bug was a silent Tweety API-drift**, in two places:
  1. `jvm_setup._configure_external_tools` called the **legacy static** API
     `EFOLReasoner.setPathToEProver(path)` — but in Tweety 1.28+ this method
     **does not exist** (replaced by instance method `setBinaryLocation`). The
     call raised `AttributeError`, swallowed by the surrounding
     `except Exception: logger.debug(...)`. EProver was therefore **never
     wired at startup**, yet the pipeline reported the configured solver name
     as if it were active.
  2. `fol_handler._fol_check_consistency_with_eprover` / `_fol_query_with_eprover`
     instantiated `EFOLReasoner()` **with no argument** — but the constructor
     requires the binary path (`EFOLReasoner(String)`). And the sync path
     `check_consistency` (the one spectacular actually uses) **hardcoded
     `SimpleFolReasoner` regardless of `settings.solver`** — so even a correctly
     installed EProver was never invoked for FOL consistency.

**The fix (committed this update)** is anti-pendule (remove the bug, not add a
counterweight): a module-level `EXTERNAL_TOOL_PATHS` registry populated by
`_configure_external_tools` replaces the dead static calls; the FOL handler
reads `EXTERNAL_TOOL_PATHS["eprover"]`, builds `EFOLReasoner(path)`, and
`check_consistency` now dispatches to EProver when `settings.solver == EPROVER`
and the path is registered (falling back to `SimpleFolReasoner` only when the
binary is genuinely absent — fail-loud, not fabricated).

**End-to-end proof on a real JVM with the real binary:**

| KB | `fol_handler.check_consistency` verdict | solver |
| --- | --- | --- |
| `p(a), !p(a)` | `(False, "FOL consistency check (EProver): inconsistent")` | EProver ✓ |
| `p(a), ∀x:p(x)⇒q(x)` | `(True, "FOL consistency check (EProver): consistent")` | EProver ✓ |

**What remains a genuine infrastructure gap (still open, cluster-wide):**

- **EProver binary is `ext_tools/`-gitignored** → must be installed on each
  machine (manual, like Clingo before `download_clingo` existed). There is no
  `download_eprover`. Coordinator cluster-wide audit still required.
- **SPASS (modal) still absent** — unchanged.
- **Prover9 runner still broken (3 format bugs)** — unchanged.
- The original `SimpleFolReasoner` path still OOMs on large KBs, so without
  the EProver binary deployed, FOL still degrades on real corpora.

The table/sections below are the **original (pre-correction) findings** kept
for traceability — read them as the diagnostic path that *led* to the fix, not
as the current state.

---

## TL;DR (original, pre-correction)

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
