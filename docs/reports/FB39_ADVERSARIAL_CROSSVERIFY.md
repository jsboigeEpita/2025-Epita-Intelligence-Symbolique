# FB-39 — Adversarial cross-verify (po-2023, independent of po-2025's measurement)

**Track**: FB-39 #1132 · **Role**: adversarial cross-verify (reserved per coordinator R418/R422) · **Target**: po-2025's PR #1133 (`fix/1132-fb39-pl-normalize`, head `99e900ab`)
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique · **Date**: 2026-06-16

> Privacy: opaque IDs only. No corpus content — this report covers a deterministic
> PL-parsing code path (no LLM, no dataset).

---

## TL;DR — verdict

**FB-39 HOLDS. The fix is root-cause, non-regressing, and fail-loud. Recommend merge #1133.**

The load-bearing root-cause claim — *Tweety's `PlParser` rejects the single-form
`&`/`|` and requires the double-form `&&`/`||`* — is **independently confirmed by
feeding formulas DIRECTLY to real Tweety** (no normalisation). po-2025's own unit
tests do NOT do this: they mock `jpype` (`_pl_parser` is a `MagicMock`), so they
verify the canonicalisation *logic* but never Tweety's actual grammar. Closing
that gap is this cross-verify's contribution.

---

## Why this cross-verify exists

po-2025 both **produced** the FB-39 fix (#1133) and **reported** the root cause +
measurement (21/81 → 81/81). Per R418/R422, formel-axis changes require an
independent non-regression cross-verify before merge (po-2023's FB-29/FB-38 role).
Two things to check independently: (1) is the root cause REAL (not a guess like the
R408 "paren over-spacing" note it supersedes)? (2) does the fix add coverage by
canonicalising valid operators, or by swallowing errors (R369 anti-fallback)?

---

## Method — probe REAL Tweety (the gap po-2025's mocked tests leave)

A standalone diagnostic (`32 tests, all PASS`, committed as
`tests/.../test_fb39_adversarial_verify.py`) does three things against real Tweety
(`USE_REAL_JPYPE=true`, JVM via `TweetyBridge`):

1. **Part A — raw grammar**: feed formulas to `PlParser.parseFormula` with NO
   normalisation. Settles whether single-`&` is really rejected.
2. **Part B — production path**: run the NEW `_normalize_formula` then parse, on
   real-style formulas + genuinely-illegal negative controls.
3. **Part C — no-JVM invariants**: pure-function canonicalisation checks (CI-runnable).

---

## Results — all 32 PASS (Part A+B against real Tweety, Part C in-process)

### Part A — root cause CONFIRMED ✅ (the load-bearing claim)

| Raw formula (no normalisation) | Tweety | Note |
|---|:---:|---|
| `(p && q) => r` (compact double) | ✅ OK | |
| `( p && q ) => r` (**over-spaced** + double) | ✅ OK | **disproves the R408 "over-space" note** |
| `p && q` / `p || q` / `p => q` / `p <=> q` / `((p=>q)=>r)=>s` | ✅ OK | |
| `(p & q) => r` (compact single) | ❌ FAIL | ParserException |
| `( p & q ) => r` (**over-spaced** + single) | ❌ FAIL | spacing is NOT the cause — single-`&` is |
| `p & q` / `p \| q` (bare single) | ❌ FAIL | "General parsing error" |
| `p &&& q` (raw triple) | ❌ FAIL | Tweety wants EXACTLY `&&` — *why* canonicalisation is needed |

**Conclusion**: single-form `&`/`|` is rejected even with perfect spacing; double-form
parses even over-spaced. po-2025's root cause is correct; the R408 paren-over-space
note was wrong. The `&&`-collapse was the real bug.

### Part B — production path (NEW fix) ✅

- **Dropped formulas recovered**: `(p & q) => r`, `p & q`, `(a | b) => (c & d)`,
  `(p => q) & (q => r)`, `!(p & q)`, `p -> q`, `p <-> q` → all now parse.
- **Non-regression (0 newly broken)**: `p => q`, `((p=>q)=>r)=>s`, `p <=> q`
  (parsed before the fix) still parse.
- **Fail-loud preserved (R369)**: `p =>` (dangling), `(p && q` (unbalanced), `&&`
  (bare operators), `""` (empty) → all still **rejected**. The fix adds coverage by
  canonicalising valid operators, NOT by swallowing parse errors. The parse path
  returns `None`/raises `ValueError` for illegal (enabling the caller to drop+count).

### Part C — canonicalisation invariants (CI, no JVM) ✅

Single-`&`→`&&`, single-`|`→`||`, double-form idempotent, `<=>` round-trips, arrow
variants canonicalised.

---

## Two probe-expectation corrections (honesty — mine, not the fix's)

An initial probe run reported 2 "mismatches". Both were **my test-design errors**, not
fix defects; the committed test asserts the corrected (true) expectations:

1. **Raw `p &&& q`** — I initially expected Tweety to accept it. It doesn't (wants
   exactly `&&`). This is precisely *why* the canonicalisation (`&+`→`&&`) is needed.
   Corrected: assert FAIL.
2. **`xyzzy ???` → `xyzzy ___`** (parsed OK) — I labelled this "illegal garbage". It
   isn't: the `???` is junk *punctuation* that the **pre-existing** prop-name
   sanitiser (`[^a-zA-Z0-9_]`→`_`, unchanged by FB-39) cleans into a valid proposition.
   This is pre-existing salvage, NOT a FB-39 regression and NOT a swallow (no logical
   structure fabricated). Removed from the illegal-logic controls.

---

## Honest correction — my R421 "alternation order" flag was a non-bug

In R421 I flagged the OLD regex alternation `=>|<=>` as a "latent bug" (claimed `=>`
matches inside `<=>`). po-2025's test `test_biconditional_preserved` notes this is a
**confirmed non-bug**, and they're right: `re` matches `<=>` as a unit at the leading
`<` (the `=>` alternative only triggers at an `=`), so `<=>` round-trips correctly
under both old and new ordering. My R421 hypothesis was wrong; the new longest-first
`<=>|=>` ordering is harmless/cleaner but not a fix. **Verify > assume** — recorded.

---

## DoD checklist (per R422)

- [x] **Delta parse-success REAL** — confirmed by raw-Tweety grammar probe (Part A),
      not a log re-parse. Single-form fails, double-form parses.
- [x] **Non-regression DECIDES** — Part B: pre-fix-OK formulas still parse; the fix
      recovers dropped ones (0 newly broken). pl/fol/solver path unchanged (PL parse
      only; FOL/modal untouched by the PR).
- [x] **Zero swallow added (R369)** — diff adds NO try/except; genuinely-illegal
      formulas stay rejected (Part B negative controls). (Pre-existing
      `except Exception: pass` at pl_handler.py:128 for sanitizer-unavailable is
      NOT added by FB-39 — out of scope, noted not a regression.)
- [x] **Negative controls** — dangling/unbalanced/bare-ops/empty all stay dropped
      (fail-loud), so the caller can count them.
- [x] **Lane file-disjoint** — companion test file `test_fb39_adversarial_verify.py`
      + this report; no overlap with po-2025's `test_pl_handler_normalize.py`.

---

## Recommendation

**Merge #1133.** The fix is root-cause-correct (independently verified against real
Tweety), non-regressing (0 newly broken), and fail-loud (no swallow added). DECIDES is
*strengthened* — 60 previously-dropped PL formulas are recovered, not fabricated.

### Honest limitations

1. **Pipeline-level re-run not reproduced** — po-2025's 21/81→81/81 figure comes from
   re-parsing the FB-32 corpus_C run's emitted formulas (gitignored, needs the
   encrypted dataset + API lane). I verified the *grammar fact* that makes the delta
   real (Part A) + the production-path correctness (Part B), not the full pipeline run.
2. **FOL/modal unaffected** — the PR touches only the PL path; FOL/modal parse were
   not cross-verified here (out of scope for FB-39).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
