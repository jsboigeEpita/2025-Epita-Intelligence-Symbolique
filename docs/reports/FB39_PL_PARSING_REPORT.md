# FB-39 — PL-parsing hardening: recover formal coverage lost to the `&`-collapse bug

**Track**: FB-39 #1132 · **Parent**: Epic #947 (closed), Formal-axis hardening · **Lane**: po-2025
**Base**: main `246b0226` (FB-38 cross-verify landed)
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique · **Date**: 2026-06-16

## TL;DR

1. **Root cause was NOT what the prior note claimed.** The standing debt note
   (`project_pl_parsing_paren_space_debt.md`, R408) blamed *paren over-spacing*.
   An empirical probe against Tweety disproved that: over-spaced parens parse fine
   (`( p && q ) => r` → OK). The actual cause: **Tweety's `PlParser` requires the
   DOUBLE-form conjunction/disjunction (`&&`, `||`) and rejects the single-form
   (`&`, `|`) with "General parsing error"** — and `_normalize_formula` was
   actively collapsing `&&`→`&` (and `||`→`|`) before submission. *Verify the
   verification: the note was a guess, the probe was the truth.*

2. **The fix is root-cause, not a counterweight (anti-pendule).** `_normalize_formula`
   now canonicalises any run of `&`/`|` (1+) to the double form (`&&`/`||`)
   instead of collapsing it. No try/except, no error-swallowing. A genuinely-
   illegal formula (`p =>`, unbalanced parens) stays dropped+counted (fail-loud,
   R369). Same fix applied to the parallel `PLFormulaSanitizer._normalize_operators`
   and its `_SPECIAL_TOKENS`/`_TWEETY_OPERATORS` sets (pre-validation parity).

3. **Measured impact on real pipeline formulas is large.** Re-parsing the 81
   unique PL formulas the pipeline actually emitted (FB-32 corpus_C run):
   **parse-success 21/81 (26%) → 81/81 (100%)**; **60 formulas resolved**, **0
   newly broken** (no regression by construction). Formal coverage that was
   silently dropped is now recovered — DECIDES is *strengthened*, not weakened.

## Methodology — reproduce the root cause directly against Tweety

A no-LLM diagnostic fed known patterns and hand-crafted variants **directly** to
Tweety's `PlParser` (no normalization), then through the production path:

| Variant (raw, fed to Tweety) | Result |
|---|---|
| `(p && q) => r` (compact, double-and) | **OK** |
| `( p && q ) => r` (over-spaced parens + double-and) | **OK** |
| `(p & q) => r` (compact, **single-&**) | **FAIL** |
| `( p & q ) => r` (over-spaced + single-&) | **FAIL** |
| `p && q` / `p <=> q` / `p => q` / `((p=>q)=>r)=>s` / `p=>q` | **OK** |
| `p & q` (single-&) | **FAIL** |

**Conclusion**: the operator form (`&` vs `&&`) is the sole discriminator. Parens
spacing is irrelevant. The latent `=>|<=>` alternation concern (po-2023) is a
non-bug: `p <=> q` parses (because `=>` cannot match at the `<` position).

## The fix

`argumentation_analysis/agents/core/logic/pl_handler.py::_normalize_formula`:

```python
# BEFORE (the bug): collapsed the valid double-form into the rejected single-form
formula_str = formula_str.replace("&&", " & ").replace("||", " | ")
...
formula_str = re.sub(r"\s*(=>|<=>|&|\||!|\(|\))\s*", r" \1 ", formula_str)
...
operators_and_parentheses = {"=>", "<=>", "&", "|", "!", "(", ")"}

# AFTER (#1132): canonicalise any run of & / | to the Tweety double-form
formula_str = re.sub(r"\s*&+\s*", " && ", formula_str)
formula_str = re.sub(r"\s*\|+\s*", " || ", formula_str)
formula_str = formula_str.replace("<->", " <=> ").replace("->", " => ")
formula_str = formula_str.replace(" NOT ", " ! ").replace(" Not ", " ! ")
formula_str = re.sub(r"\s*(<=>|=>|!|\(|\))\s*", r" \1 ", formula_str)
...
operators_and_parentheses = {"=>", "<=>", "&&", "||", "!", "(", ")"}
```

Same change applied to `PLFormulaSanitizer._normalize_operators` +
`_SPECIAL_TOKENS`/`_TWEETY_OPERATORS` (so the pre-validation gate in
`parse_pl_formula` doesn't reject the now-canonical `&&`/`||` as "invalid tokens").

`WatsonLogicAssistant._normalize_formula` (a third site with the same `&&`→`&`
habit) is **deliberately left untouched** — it feeds the bridge, which re-
normalises through `pl_handler._normalize_formula`, so it is covered by
transitively by this fix (out of scope, anti-pendule/minimal change).

## DoD checklist (#1132)

- [x] **Known-failing nested PL patterns now parse** — `(p && q) => r`,
      `(p => q) && (q => r)`, `!(p && q)`, deep nesting, mixed `(a || b) => (c && d)`,
      `p <=> q` (tweety-marked integration tests, all pass).
- [x] **Negative controls for genuinely-illegal formulas** — unbalanced parens /
      markdown fence → `parse_pl_formula` returns `None`; `p =>` (passes sanitizer,
      Tweety rejects) → `ValueError` (fail-loud, no swallowing).
- [x] **JException/run measurably reduced** — **60 resolved, 0 residual** on the
      real corpus_C formulas (21→81 parse success, +74pp). See measure below.
- [x] **Formal DECIDES not regressed** — **0 newly broken** (every formula that
      parsed before still parses); formula count strictly increases. The formal
      axis is strengthened, not weakened.
- [x] **Report opaque** — opaque IDs only; proposition names and source content
      are not reproduced here. Runs gitignored under `.cache/` / `evaluation/results/`.

## Corpus measure (opaque aggregation)

Re-parsed the 81 unique PL formulas emitted by the FB-32 corpus_C run, each with
the OLD (buggy) and NEW (fixed) normalize, directly against Tweety:

| Metric | OLD (buggy) | NEW (fixed) |
|---|---|---|
| Unique formulas analysed | 81 | 81 |
| Parse success | 21 (26%) | **81 (100%)** |
| Failures | 60 | **0** |
| **Resolved by fix** | — | **60** |
| **Newly broken (regression)** | — | **0** |
| Parse-success delta | — | **+60** |

Every one of the 60 prior failures was the `&&`/`||` → `&`/`|` collapse; none was
a genuinely-unparseable formula. This is why `pl_metrics.template:0` held (the
formal verdict was real) yet ~74% of conjunctive/disjunctive formulas never
reached the solver.

## Tests

- `tests/unit/argumentation_analysis/agents/core/logic/test_pl_handler_normalize.py`
  (new): canonicalisation guards (no-JVM, CI-safe) + tweety-marked end-to-end
  integration (skipped unless `USE_REAL_JPYPE=true`). **11 tweety tests pass**
  (7 valid parse · 3 sanitizer-reject → None · 1 tweety-reject → ValueError).
- `tests/unit/argumentation_analysis/test_pl_formula_sanitizer.py` (revised): the
  6 tests that asserted the buggy single-`&` output now assert the canonical
  double-`&&`, plus new tests for single-`&`→`&&` canonicalisation and that a
  lone `&` is rejected by `validate_formula` (it is not a valid Tweety token).
- Full suite on both files: **68 pass, 9 skipped** (skips = tweety integration
  without `USE_REAL_JPYPE`).

## Honest hedges

1. **No live corpus re-run.** The delta is measured by re-parsing the formulas a
   prior run *logged*, not by re-running the pipeline end-to-end. This isolates
   the fix's effect precisely (no LLM variance) but does not re-exercise the full
   PL/FOL/solver phase wiring. Non-regression is proven by construction (0 newly
   broken) and by the tweety integration tests, not by a fresh spectacular run.
2. **`&`/`|` are now load-bearing syntax.** Any downstream code that string-
   matched a single `&`/`|` (none found in the formal path) would need updating.
   `WatsonLogicAssistant._normalize_formula` still emits single-form but is
   re-normalised by the bridge, so it is covered transitively.
3. **Pre-existing mypy-strict errors** on `pl_handler.py` (SAT-handler, `JString`,
   untyped helpers) are untouched — out of scope, and `pl_handler.py` is not in
   the CI mypy gate (`invoke_callables.py` only).

## What this means

The formal axis (DECIDES) was correct but **under-measured**: ~3 of every 4
conjunctive/disjunctive PL formulas the LLM produced were silently dropped before
they could contribute. FB-39 recovers them. The verdict is unchanged (DECIDES)
but now rests on substantially more of the formal structure the pipeline
extracted — a hardening of the axis Epic #947 was closed on.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
