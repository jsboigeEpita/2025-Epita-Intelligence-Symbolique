# FP-4 — Extension / Structured-Argumentation Emptiness Diagnosis (read-only)

**Track FP-4** · parent **Epic #1191** · owner **po-2023** · dispatch **R450 (ai-01)**.
**Opaque id**: `fp4_extension_diagnosis`. Base: main `72586016` (post-FP-3). **Read-only**
(no handler edits — serializes after the fix tracks; file-disjoint from FP-3/F-6).

> **Scope.** Why the extension / structured-argumentation capabilities produce **0
> extensions or are broken** on real corpora, while Dung-core (grounded/preferred/
> stable) yields 9 real extensions. Each capability is root-caused and classed:
> **(a) translation-gap** / **(b) wiring-bug** / **(c) honest-absent** / **(d) jar-gap**.
> Counts/classifications only; **no corpus content, no raw text, no source identifiers**.

## TL;DR verdict

The extension layer is **not uniformly broken** — it falls into **two clear buckets**:
- **Structured-argumentation (ASPIC+/ABA/SETAF/weighted/bipolar) = translation-gap (a)**:
  the handlers and the orchestrator shapers are **wired correctly and fail-loud**, but
  the pipeline **never feeds them structured input** (defeasible rules, collective
  attacks, weights) from the text. They run on auto-shaped synthetic rules → produce
  extensions, but on **non-authentic input**. Empty-on-real-corpus is an
  **input-contract gap**, not a handler bug. Fix = a translator (depth-track), OR
  honest-absent documentation — NOT fabrication.
- **DL / DeLP / CF2 = wiring-bug (b) + jar-gap (d)**: real handler defects (DL query
  semantic, DeLP fed raw text, CF2 class missing in Tweety 1.29).

This **refines FP-2's root-cause classes** with per-capability precision and gives
the one-line fix proposals the dispatch asked for.

## Census table

| Capability | Symptom on real corpus | Root-cause class | Evidence (file:line) |
|---|---|---|---|
| **ASPIC+** | 0 / synthetic extensions | **(a) translation-gap** | orchestrator auto-shapes strict/defeasible rules from claims/args (invoke_callables.py:3136-3184); no upstream `strict_rules`/`defeasible_rules` ever produced. Handler `analyze_aspic_framework` itself correct. |
| **ABA** | 0 / synthetic | **(a) translation-gap** | orchestrator shapes rules via `_aba_rules_from_context` from arg graph (invoke_callables.py:3036); no upstream `assumptions`/`rules`/`contraries`. Handler correct (E1b fixed input contract #1168). |
| **SETAF** | 0 / synthetic | **(a) translation-gap** | orchestrator shapes set-attacks from pairwise graph (invoke_callables.py:3449-3456); no upstream `set_attacks`. Handler correct. |
| **weighted** | 0 / synthetic | **(a) translation-gap** | orchestrator shapes (src,tgt,0.5) triples with neutral weight (invoke_callables.py:3483-3494, comment cites #1019 "no fabricated confidence"); no upstream `weighted_attacks`. Handler correct. |
| **bipolar** | 0 / synthetic | **(a) translation-gap** | orchestrator uses `context.get("supports", [])` (invoke_callables.py:3006); no upstream support-relations extractor → empty supports → trivial framework. Handler correct. |
| **DL** | `AtomicConcept cannot be cast to DlAxiom` | **(b) wiring-bug** | `is_consistent` calls `reasoner.query(kb, AtomicConcept("⊤"))` (dl_handler.py:163) — semantically invalid query (top via AtomicConcept constructor, not TopConcept); also empty tbox/abox fed (invoke_callables.py:3352). |
| **DeLP** | parse error on `:` | **(a)+(b)** translation-gap + raw-text-fed | orchestrator passes `input_text[:500]` as `program_text` (invoke_callables.py:3612) → `DelpParser.parseBeliefBase` rejects French prose (delp_handler.py:68). No DeLP-program translator. |
| **CF2 (Dung ext)** | `CF2Reasoner class not found` | **(d) jar-gap** | `SEMANTICS_REASONERS["cf2"] = "org.tweetyproject.arg.dung.reasoner.CF2Reasoner"` (af_handler.py:20); class absent/moved in bundled Tweety 1.29. |

## Detail per capability

### ASPIC+ / ABA / SETAF / weighted / bipolar — translation-gap (a), not broken

These handlers are **correctly wired and fail-loud** (confirmed in FP-2 #1193: all
`_python_*_fallback` raise; the orchestrator `except` paths raise RuntimeError). The
reason they show **0 real extensions** is that the pipeline **generates no structured
formal input** for them:

- **ASPIC+** needs `strict_rules` (factual → conclusion) and `defeasible_rules`
  (underminable). The orchestrator **auto-shapes** these from extracted claims and
  arguments (invoke_callables.py:3136-3184) — synthetic, not LLM-derived. No upstream
  phase emits `strict_rules`/`defeasible_rules` in `context`.
- **ABA** needs `assumptions`/`rules`/`contraries`. Orchestrator shapes from the arg
  graph (invoke_callables.py:3036). No upstream emitter.
- **SETAF** needs collective `set_attacks` (multiple attackers → one target).
  Orchestrator derives from pairwise attacks (invoke_callables.py:3449). Real corpora
  have no explicit collective-attack structure extracted → the shaper produces trivial
  singletons.
- **weighted** needs `(src, tgt, weight)` triples. Orchestrator assigns **neutral 0.5**
  (#1019: deliberately not fabricated, invoke_callables.py:3483). No upstream
  confidence/weight extractor.
- **bipolar** needs support-relations. Orchestrator reads `context["supports"]` which
  is **never populated** (invoke_callables.py:3006) → empty support graph.

**Anti-pendule conclusion**: do NOT fabricate structured input to reach "parity."
Two honest options: **(1) document as honest-absent** (these need a translator phase —
a depth-track, user/coord-gated), or **(2)** for the ones whose shaper already
produces *something* verifiable (ASPIC synthetic rules, Dung-shaped attacks), accept
the synthetic-input result **tagged** (the handler runs real Tweety on shaped input —
verifiable, like the Dung fallback). The Dung "legitimate fallback" line from FP-2
applies: shaped-but-verifiable is OK; fabricated-verdict is not.

### DL — wiring-bug (b)

`DLHandler.is_consistent` (dl_handler.py:159-173) calls
`reasoner.query(kb, self._AtomicConcept("⊤"))`. Two issues:
1. **Semantic**: `⊤` (top) should be a `TopConcept`, not constructed via
   `AtomicConcept("⊤")`. The NaiveDL reasoner may reject or mis-cast it.
2. **The cast error** `AtomicConcept cannot be cast to DlAxiom` indicates that
   somewhere an `AtomicConcept` is added directly to the `DlBeliefSet` (which expects
   `DlAxiom`). In `create_knowledge_base` (dl_handler.py:131-155) all adds are wrapped
   in `EquivalenceAxiom`/`ConceptAssertion`/`RoleAssertion` — so the cast error likely
   originates from the **query path** or the reasoner internals on an empty KB.

**One-line fix proposal (for fix-track)**: replace the top-concept query with the
reasoner's native consistency method, or query entailment of `⊥` (bottom): an
inconsistent KB entails bottom. E.g. `reasoner.query(kb, bottom)` → consistent iff
not entailed. Also: skip + degraded when `tbox`/`abox` are empty (avoid the vacuous
`consistent=True` flagged in FP-2).

### DeLP — translation-gap + raw-text-fed (a)+(b)

The orchestrator passes `input_text[:500]` (raw corpus prose) as `program_text`
(invoke_callables.py:3612). `DelpParser.parseBeliefBase(StringReader(program_text))`
(delp_handler.py:68) expects DeLP syntax (`<-` strict rules, `<.` defeasible rules,
predicates) → rejects French prose → RuntimeError on the `:` lexical token. The handler
is correct; the input contract is violated.

**Fix proposal**: fail-loud when no structured `program` is in context (remove the
raw-text default — subtraction, anti-pendule), OR add a DeLP-program translator
(depth-track). Until then, DeLP is honest-absent on free-text corpora.

### CF2 — jar-gap (d)

`SEMANTICS_REASONERS["cf2"]` maps to
`org.tweetyproject.arg.dung.reasoner.CF2Reasoner` (af_handler.py:20). In the bundled
Tweety 1.29, CF2 lives under `org.tweetyproject.arg.dung.cf2` (or the class was
renamed) → `ClassNotFound`. The 10 other Dung semantics compute fine (9 extensions
verified firsthand by ai-01).

**Fix proposal**: correct the class FQN for the installed Tweety version, or gate CF2
out of the 11-semantics batch until the JAR is updated (honest-absent, not a crash).
Verify the real FQN via `javap`/reflection before editing (E1b lesson #1179).

## FIX-tracks (prioritized — anti-pendule, feed next dispatch)

1. **DL wiring fix** (b): native consistency / bottom-entailment query + empty-KB
   skip-degraded. **Smallest, highest-confidence** — real handler bug, one method.
2. **CF2 class FQN** (d): verify real FQN via `javap`, correct mapping OR gate CF2
   out of the batch (honest-absent). Verify before edit (#1179).
3. **DeLP raw-text removal** (a): remove the `input_text[:500]` default → fail-loud
   when no structured program. Subtraction.
4. **Structured-argumentation depth-track** (a): a shared translator phase that emits
   `strict_rules`/`defeasible_rules` (ASPIC), `assumptions`/`contraries` (ABA),
   `set_attacks` (SETAF), `weighted_attacks` (weighted), `supports` (bipolar) from the
   extracted argument graph + fallacy data. **This is the real lever** to lift all 5
   from 0/synthetic to authentic — but it's a depth-track (new phase + prompt work),
   user/coord-gated, NOT a quick fix.
5. **Tagging policy**: for the shaped-input capabilities (ASPIC/ABA/SETAF/weighted),
   tag results `"input_source": "auto_shaped"` so the FP-5 matrix distinguishes
   authentic-Tweety-on-shaped-input from authentic-Tweety-on-translated-input.

## Methodology (verify > memo)

- All file:line citations verified by direct `Read` this round.
- The "(a) translation-gap" verdict for ASPIC/ABA/SETAF/weighted rests on reading the
  orchestrator shapers (invoke_callables.py:3006, 3036, 3136-3184, 3449-3494) + the
  FP-2 finding that these handlers raise (not fabricate) on JVM absence.
- The DL/DeLP/CF2 verdicts rest on reading the handler methods + the orchestrator
  input-contract paths. The exact DL cast origin and CF2 real FQN need a JVM probe
  to finalize (flagged for the fix-track, not assumed here).

## DoD FP-4

- [x] Each capability classed (a/b/c/d) with file:line evidence
- [x] translation-gap → named the missing structured field + which prompt/extractor
      should emit it (strict/defeasible rules, assumptions/contraries, set_attacks,
      weighted_attacks, supports)
- [x] wiring bugs (DL/DeLP) → repro + one-line fix proposal
- [x] prioritized fix-track list

Privacy HARD: counts/classifications only, opaque IDs, no corpus content.
Anti-pendule: every recommendation is removal (fail-loud) or honest-absent — never
fabrication to reach "parity."
