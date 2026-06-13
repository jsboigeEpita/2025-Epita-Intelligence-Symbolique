# FB-21 — PL Verification Root-Cause Analysis (#1083)

**Track**: FB-21 #1083 — Epic #947 (Final Boss), PL formal-verification gap
**Date**: 2026-06-14
**Base**: main `f8b39ed8`
**Privacy**: Opaque IDs only. Synthetic test arguments only (no corpus content). $0-API for diagnosis.

---

## Summary

The FB-20 terminal report (#1068) attributed **PL=0 on corpus_B/C** to "Tweety rejecting LLM-generated
formula syntax" and **corpus_A's PL=25** to "the only corpus where verification succeeded". **Both
claims were wrong.** FB-21 proves:

1. **corpus_A's PL=25 was Python-heuristic fallback theater** (`"fallback": "python"`,
   `has_contradiction = any(f.startswith("!"))`), not real Tweety verification — the exact #1019
   anti-pattern the Epic exists to kill.
2. **PL=0 on B/C was a latent missing-method bug**, unmasked by RA-8 #1066's *correct* removal of
   that fallback. It was **not** a formula-syntax issue, and **not** a regression in `nl_to_logic`.

The fix adds the missing `PLHandler.check_consistency` (mirroring `FOLHandler`). Post-fix corpus_C
re-run yields **pl_verified=18** (real 2-pass LLM formulas, `template:0`, per-formula Tweety-isolated).

---

## Investigation method (SDDD triple grounding)

### Technique (code = truth)

**Git archaeology** discriminated the two hypotheses the issue framed:

- **H1 (regression in `nl_to_logic` 06-10 → 06-13)**: REFUTED. The only commit touching
  `nl_to_logic.py` in the window is `b613ee5a` (#1077 toggle fix). The PL prompt has not changed.
- The real regression window is on `invoke_callables.py`: commit **`c685ed5e` (RA-8 #1066)**
  removed the Python-heuristic PL fallback and replaced it with fail-loud `RuntimeError`. That
  diff exposed a bug that had been **latent** all along.

### Empirical probe (decisive, $0-API)

A diagnostic called the exact code path `_invoke_propositional_logic` uses:

```
PLHandler has 'check_consistency'?        False   ← TweetyBridge.check_consistency(prop) dispatches HERE (tweety_bridge.py:274)
PLHandler has 'pl_check_consistency'?     True    ← but only THIS exists (Tweety)
PLHandler has 'pl_check_consistency_sat'? True    ← and THIS (PySAT, but python-sat NOT installed)
[ATTR] 'p => q': AttributeError -> 'PLHandler' object has no attribute 'check_consistency'
```

**Every** formula — even the textbook `p => q` — raised `AttributeError`, collapsing the per-formula
isolation loop (`invoke_callables.py:4586`) to 0 survivors → `RuntimeError` → PL=0. This is
independent of formula content, so it is **not** H2 (provider variance) either.

### Verification of the existing path

`PLHandler.pl_check_consistency` (Tweety) **works** — and the suspect formula
`transfers => imposed` parses fine (consistent=True). The real Tweety parser rejects only specific
operator-precedence shapes (`&&`/`||` without parentheses, under-parenthesized nested `=>`), which
the per-formula isolation loop already handles correctly. The PySAT alternative
(`pl_check_consistency_sat`) is unavailable (`python-sat` not installed).

---

## Root cause

Two layers, one fix:

| Layer | Fact | Effect |
|-------|------|--------|
| **Latent bug** | `TweetyBridge.check_consistency("propositional")` → `PLHandler.check_consistency` — a method that **never existed** (PLHandler only exposed `pl_check_consistency` / `pl_check_consistency_sat`). | Every PL formula → `AttributeError` → batch collapses to 0. PL was **always** broken on the dispatch path. |
| **Theater mask** | `_invoke_propositional_logic` had a Python-heuristic fallback that synthesized a non-empty `formulas` list (`has_contradiction = any(f.startswith("!"))`) whenever Tweety failed. | On 06-10 (corpus_A) this returned 25 "formulas" — reported as "PL verified" but they were heuristic, not Tweety. |
| **Anti-theater (RA-8 #1066)** | Correctly removed the Python fallback, replaced with fail-loud `RuntimeError`. | Exposed the latent bug → PL=0 on 06-13. RA-8 did the right thing; it is not at fault. |

### The bitter irony

RA-8 was the **anti-theater** fix. It removed a heuristic that faked non-zero PL. But the code it
left calling (`bridge.check_consistency(prop)`) routed to a missing method — producing a *new*
theater-like symptom (PL silently = 0). The anti-theater mandate (#1019) means both the heuristic
theater (06-10) and the silent-zero theater (06-13) must be corrected, and the report must say so.

---

## The fix (anti-pendule: complete the missing method, no counterweight)

`argumentation_analysis/agents/core/logic/pl_handler.py`:

```python
def check_consistency(self, belief_set: str) -> Tuple[bool, str]:
    """Uniform handler API mirroring FOLHandler.check_consistency (#1083)."""
    is_consistent = self.pl_check_consistency(belief_set)
    msg = ("PL knowledge base is consistent." if is_consistent
           else "PL knowledge base entails a contradiction.")
    return bool(is_consistent), msg
```

- Completes the API parity with `FOLHandler.check_consistency` (which already exists and works).
- Delegates to the existing **working** `pl_check_consistency` (Tweety).
- Parse errors propagate unchanged → per-formula isolation keeps valid formulas, rejects unparseable
  ones, never swallows the batch.
- No try/except widening, no `pl_check_consistency_sat` detour (PySAT not installed).

### Regression guard

`tests/agents/core/logic/test_tweety_bridge.py::test_pl_check_consistency_delegation` asserts the
dispatch now reaches `PLHandler.check_consistency` (mocked: fast, $0-API) and that a real JVM
accepts the textbook `p => q`. **No such test existed before — that is why the bug shipped.**

---

## Verification (DoD)

| DoD item | Evidence |
|----------|----------|
| Root cause identified (regression vs variance) | H1 refuted (git: prompt unchanged); latent missing-method bug unmasked by RA-8 #1066. See §Investigation. |
| Fix at correct layer (prompt/validation, not error-swallow) | Added the missing method at the dispatch target. No try/except widened, no fallback restored. |
| PL > 0 verified on real corpus re-run | corpus_C re-run post-fix: `pl_verified=18` (gitignored `integral_C.json`, fresh `2026-06-14T00:40`). |
| Anti-theater (not template `p1/p2` dummies) | Isolated call of `_invoke_propositional_logic` on synthetic opaque args: `pl_metrics={template:0, pass1_atoms:9, pass2_candidates:4, post_tweety:3, isolation_survivors:3}`, formulas are real implications (`economic_sanctions_imposed => trade_volumes_decrease`, etc.), 0 bare-atom dummies, `rejected_count=1` (malformed `&` correctly isolated out). |
| Finding documented + FB-20 report corrected | This doc + FB-20 report §2.C/§2.E/§2.CONCLUSION/§5.1/§5.3/§7 corrections (marked `~~strikethrough~~` + FB-21 note). |

---

## Impact on Epic #947 verdict

- **PL axis is no longer a cap on DECIDES.** The "PL=0" gap was the *code bug*, now fixed.
- **corpus_A is no longer the unique "PL-deciding" corpus** — its 25 were theater.
- **Verdict remains EDGES**: the **quality radar** (spacy WinError 182) is now the single remaining
  cap on a clean DECIDES. A full A/B/C re-run with #1083 would lift the PL axis; the quality axis
  needs a separate fix (DLL load order, out of FB-21 scope).
- **Anti-theater dividend**: the investigation corrected a theater claim (corpus_A PL=25) *that this
  very report had made*. This is the mandate working as intended.

---

## Privacy / scope

- Synthetic test arguments only (no corpus content). Diagnosis was $0-API (JVM/Tweety only).
- File-disjoint from #1079 (po-2023): that targets `router.py` / `collaborative_debate.py` /
  `french_fallacy_adapter.py` / `judge.py`. This fix touches `pl_handler.py` + `test_tweety_bridge.py` + the
  FB-20 report doc. Zero overlap.
- No deletions (Cleanup Gate N/A).
