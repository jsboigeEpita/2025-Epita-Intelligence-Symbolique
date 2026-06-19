# W1 #1178 — Dormant-Reasoner Handler-Fix Inventory Report

**Track:** file-disjoint follow-up to W1 #1169 (Epic #1165 mandate: *tous les
reasoners exercés ou documentés*). W1 wired 5 reasoners (SetAF/ABA/DeLP/DL/
Dialogue) whose failure was an **input-contract mismatch** in the invoke
callables. This track fixes the 6 reasoners W1 documented out-of-scope because
their failure was a **handler-level Tweety API bug** (one layer deeper).

**Privacy HARD:** opaque IDs only (`arg_a`, `doc_A`). No corpus content, no
source identifiers. Handler probes use synthetic corpus-like input.

## Verify-the-verification (FB-39 lesson)

Each handler's real Tweety API was discovered by **direct JVM reflection**
(`getDeclaredMethods`, `getParameterTypes`) + bytecode disassembly
(`javap -c`) of the official Tweety `*Example` classes — not by guessing from
the handler source. The dispatch framing ("missing initializer") was wrong for
all 6; the real failure modes are below.

## Outcome: 4 fixed + wired, 2 documented out-of-scope

### Fixed + wired into spectacular (#1178, file-disjoint from W1)

| Handler | Root cause (verified) | Fix (anti-pendule: subtraction) | Non-trivial result |
|---------|----------------------|---------------------------------|--------------------|
| **weighted** | `getModels(WAF)` 1-arg doesn't exist; real sig is `getModels(WAF, T, T)` where `T` is the semiring weight type. The no-arg `WeightedArgumentationFramework()` ctor instantiates `<Boolean>`, so `setWeight(JDouble)` then `getModels(Double)` → ClassCastException. | Build the framework with `FuzzySemiring()` (Double-typed, standard order on [0,1]); pass `(weight_threshold or 0.0, 1.0)` bounds. | `extensions_count`, real `weight_statistics` (min/max/avg). |
| **social** | `SocialAbstractArgumentationFramework` has no `vpiPlus`/`vpiMinus`; real API is `voteUp(Argument, int)`/`voteDown(Argument, int)`. And `framework.add(Attack)` is ambiguous (`add(Formula)`/`add(Object)`/`DungTheory.add(Attack)`). | Use `voteUp`/`voteDown`; add attacks via explicit `DungTheory.add(framework, attack)` static dispatch. | Real ISS social-strength scores in [0,1], ranked. |
| **qbf** | `Disjunction(PlFormula, PlFormula)` is ambiguous against the `(PlFormula...)` varargs ctor → `TypeError: Ambiguous overloads`. Same for `Conjunction`. | Cast both args to the `PlFormula` supertype (`jpype.JObject(f, PlFormula)`) to disambiguate the binary ctor. | NaiveQbfReasoner runs, formula parses (multi-arg &/\| chains). |
| **cl** | `SimpleCReasoner.query` signature is `(ClBeliefSet, PlFormula)` — it answers on the **conclusion**, but the handler built a `Conditional` and passed it → ClassCastException (`Conditional` is not a `PlFormula`). Same Disjunction/Conjunction ambiguity in the formula builders. ClParser requires every formula to be a conditional `(B\|A)`. | Pass the conclusion as a PlFormula; cast connective args; wrap bare facts as `(fact \| TRUE)` in `parse_and_query`. | `query` returns ACCEPTED/REJECTED; `parse_and_query` works. |

### Documented out-of-scope (handler registered, state-writer stays)

| Handler | Specific blocker (verified) | Why not wired (anti-theater #1019) |
|---------|----------------------------|-------------------------------------|
| **eaf** | `EpistemicArgumentationFramework` is generic over FOL/modal formulas — each argument must carry an epistemic claim like `[](in(x))`. The reasoner `getModels` raises `IllegalArgumentException: Unsupported classical formula type: Tautology` when claims are absent; the official example builds claims via a modal-logic parser. | Spectacular's arguments are flat IDs, not structured FOL/modal claims. Wiring would require **fabricating** epistemic formulas per argument = theater. Documented, not faked. |
| **adf** | ADF reasoners (`Ground/Complete/Preferred`) require an `IncrementalSatSolver` in their constructor. The native solver (`NativeMinisatSolver`) hangs on init under JPype; the `PooledIncrementalSatSolver` wrapper requires a configured Executor. | Same env-dependency family as `sat_solving` (already out-of-scope). The handler builder also targeted the wrong class (`GraphAbstractDialecticalFramework` has no public ctor — must use `AbstractDialecticalFramework.builder()`), but even fixed, the solver hangs. Documented. |

## Wiring

4 spectacular phases added (L4b, after `aspic_analysis`, all `optional=True`,
`timeout_seconds=180`): `weighted_reasoning`, `social_reasoning`,
`qbf_reasoning`, `cl_reasoning`. Each consumes an existing registered
capability with an existing state-writer — no new wiring infra, only the
phase + the handler fix.

Spectacular phase count: 31 → 35 (file-disjoint from W1's 31 → 36; the two
PRs converge on 40 once both merge).

## Validation

- mypy strict clean on the 4 CI-gated files (`invoke_callables.py`,
  `workflows.py`, `state_writers.py`, `registry_setup.py`).
- 7 real-jpype contract tests (test_1178_handler_fixes.py) green — each drives
  the real handler against the real JVM and asserts non-trivial state.
- spectacular DAG + regression suite green (35 phases, DAG valid, 76 tests).
- Per-handler direct JVM probe: all 4 fixed reasoners produce real Tweety
  state (extensions/scores/formula-parse/query-result).
- 0 LLM spend (deterministic JVM/Tweety work).
