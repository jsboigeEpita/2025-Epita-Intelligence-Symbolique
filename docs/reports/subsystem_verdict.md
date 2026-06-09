# Per-Subsystem Critical Verdict — #957

> **Epic #947 "Final Boss" — Phase 3, FB-6**
> Author: `myia-po-2023` | Date: 2026-06-05
> Branch: `docs/957-subsystem-verdict`
> Gated by: #945 (re-run intégral, numbers TBD where marked `[PENDING #945]`)

---

## Methodology

Each subsystem is audited against 4 criteria:

| Criterion | Question |
|-----------|----------|
| **A. What it genuinely produces** | Actual output shape and content (not documentation claims) |
| **B. Test guards** | Value-gate tests (PR #951), brick-health (#944), dedicated unit tests |
| **C. Known blind spots** | Degenerate fallbacks, silent failures, correctness bugs |
| **D. Verdict** | One-word: `TRUSTWORTHY` / `PARTIAL` / `UNTRUSTED` |

Verdict calibration:
- **TRUSTWORTHY** — produces non-trivial output, has ≥1 value-gate test, fallback is meaningful
- **PARTIAL** — produces useful output under ideal conditions, but has known gaps (missing tests, degenerate fallback, silent correctness bug)
- **UNTRUSTED** — output is vacuous, fallback returns hardcoded data, or critical correctness bug confirmed

**Post-#1019 anti-theater mandate**: All subsystems must fail explicit rather than silently producing fabricated results. Subsystems previously returning `degraded: True` or heuristic placeholders now return honest `None`/`RuntimeError`/sentinel values. Downstream state writers preserve None/True/False tri-state (#1028).

---

## Core Subsystems (12)

### 1. Informal Fallacy Detection (3-tier)

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/informal/informal_agent.py`, `taxonomy_sophism_detector.py`, `informal_agent_adapter.py` |
| **Produces** | `List[Dict]` with `nom`, `justification`, `confidence`. Three tiers: (1) LLM semantic analysis via SK, (2) lexical taxonomy matching (keyword→fallacy name), (3) adapter mock fallback |
| **Value-gate tests** | **YES** — `TestInformalTaxonomyValueGate` (3 tests, PASS). Asserts detector fires on literal `nom_vulgarisé`, returns empty on paraphrase, and confidence ≥0.7 on match. |
| **Blind spots** | (1) Taxonomy detector uses naive substring matching — fires only when `nom_vulgarisé` or `Name` literally appears in text. Entries with `nan` nom_vulgarisé (e.g. "Ad hominem" PK=1360) only get 0.1 per description keyword — below the 0.3 threshold. Value-gate test **pins this**: fires on "trouver des excuses" (has nom_vulgarisé), empty on paraphrase. (2) Adapter fallback (`informal_agent_adapter.py:111-126`) uses mock objects — returns test doubles, not analysis. (3) `analyze_rhetoric()` and `analyze_context()` are commented out (never implemented in BaseAgent version). |
| **Verdict** | **PARTIAL** — Tier 1 (LLM) works when SK kernel available; Tier 2 (taxonomy) is substring-literal, now honestly characterised by value-gate tests (#973); Tier 3 (adapter) is mock. Coverage: 10/12 core subsystems. |

### 2. Dung/ASPIC Abstract Argumentation

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/logic/dung_native.py`, `af_handler.py`, `aspic_handler.py`, `invoke_callables.py:5441-5645` |
| **Produces** | Dung: up to 11 semantics (grounded/preferred/stable/complete/admissible/etc.) via Tweety JVM. Pure-Python fallback computes **4 semantics** (grounded/complete/preferred/stable) via exact combinatorial enumeration (#1019/#1025). ASPIC: structured argumentation with rule-based inference. |
| **Value-gate tests** | **NONE** in `test_value_gates.py`. |
| **Blind spots** | (1) Python fallback computes 4 semantics up to ≤25 arguments; beyond that cap, only grounded is computed (#1019/#1028). (2) ~~`dung_native.py` framework_properties() DFS cycle detection has variable shadowing bug~~ — **FIXED (#970)**: rewritten to use `attacked_by()` adjacency. (3) ~~Exponential subset enumeration for preferred/stable — no size guard~~ — **FIXED (#970)**: `RuntimeError` raised above `_MAX_ENUM_ARGS=15`, grounded still works. (4) ASPIC requires JVM, no pure-Python fallback. |
| **Verdict** | **PARTIAL** — Pure-Python computes grounded+complete+preferred+stable (#1019). JVM path produces 11 semantics. Missing: value-gate tests, ASPIC fallback, >25 args only grounded. |

### 3. FOL (First-Order Logic)

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/logic/fol_handler.py`, `invoke_callables.py:4915-5324` |
| **Produces** | Consistency check + query entailment via 3-solver chain: Prover9 → EProver → Tweety SimpleFolReasoner. Per-formula isolation (PR #954 fix). ~~Fallback flag `solver_fallback` (PR #955)~~ — **REMOVED (#1019/#1025)**: no heuristic fallback; when all formulas fail Tweety parsing, returns `consistent: None, solver: "none"` (honest failure). TweetyBridge path no longer stamped `degraded`. Preflight solver check logs WARNING if eprover/SPASS binaries missing. |
| **Value-gate tests** | **YES** — `TestFOLValueGate` (3 tests, **PASS** after #976). Asserts: (1) fallback='python' and consistent=False when Fallacious predicates present, (2) formulas are predicate-shaped (not zero/degenerate), (3) consistent is real bool when Tweety available. |
| **Blind spots** | (1) Solver fallback chain: same call silently produces different results depending on which binary is installed. (2) Tweety SimpleFolReasoner is incomplete — cannot decide all FOL consequences. (3) NL-to-logic fallback produces structured formulas even without Tweety — fallback is honest but not verified. (4) ~~`consistent` field in Python fallback may be `not has_fallacious` — a weak heuristic~~ — **REMOVED (#1019)**: now returns `consistent: None` (honest unverified). |
| **Verdict** | **PARTIAL** — Per-formula isolation fixed (#954). Heuristic fallback eliminated (#1019). Value-gate regression guard added (#976). Solver-dependent non-determinism and incomplete prover remain. |

### 4. PL (Propositional Logic)

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/logic/propositional_logic_agent.py`, `invoke_callables.py:4514-4912` |
| **Produces** | `PropositionalBeliefSet` with declared propositions + formula strings, validated by Tweety. 2-pass coordinated pipeline: Pass 1 extracts shared atom inventory, Pass 2 generates per-argument formulas. Python fallback returns `fallback: "python"` with template pN variables or NL-to-logic translations. |
| **Value-gate tests** | **YES** — `TestPLValueGate` (3 tests, **PASS** after #977). Asserts: (1) fallback='python' and satisfiable is bool when Tweety unavailable, (2) formulas contain PL operators or template vars (not zero/degenerate), (3) satisfiable is real bool when Tweety available. |
| **Blind spots** | (1) Heavy LLM dependency — 2 LLM calls (propositions + formulas) with JSON parsing, 3 retries on failure. (2) `_filter_formulas()` silently drops LLM-invented propositional symbols without notification. (3) Only Tweety backend — no multi-solver chain like FOL. (4) Requires JVM. |
| **Verdict** | **PARTIAL** — Produces real PL analysis when JVM+LLM available. Value-gate regression guard added (#977). LLM dependency is fragile but honest. |

### 5. Modal Logic

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/logic/modal_handler.py`, `invoke_callables.py:5354-5438` |
| **Produces** | Formula validation + query acceptance + KB consistency via Tweety SimpleMlReasoner. Heuristic fallback eliminated (#1019): returns `valid: None, solver: "none"` — honest failure. TweetyBridge path no longer stamped `degraded`. Preflight solver check on first invocation. |
| **Value-gate tests** | **YES** — `TestModalLogicValueGate` (2 tests, **PASS** after #963). Asserts `valid is None` and `solver == "unavailable"`. |
| **Blind spots** | (1) No pure-Python fallback for modal reasoning — only JVM path works. (2) `is_modal_kb_consistent()` returns `None` on "no method found" (honest, not vacuous True). |
| **Verdict** | **PARTIAL** — JVM path works. Heuristic fallback eliminated (#1019). KB consistency is honest unverified. |

### 6. Quality Evaluation (9 Virtues)

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/quality/quality_evaluator.py`, `invoke_callables.py:333-370` |
| **Produces** | `note_finale` (0-9), `note_moyenne` (0-1), `scores_par_vertu` (9 virtue scores 0-1), `rapport_detaille` (per-virtue explanation). Deterministic, keyword/regex heuristics — no LLM needed. ~~Silent regex fallback when spacy unavailable~~ — **ELIMINATED (#1019/#1026)**: `_load_deps()` now raises `RuntimeError` if spacy/textstat cannot import. DLL load-order guard (`dll_guard.py`) added to all entry points. |
| **Value-gate tests** | **YES** — `TestQualityValueGate` (3 tests, all PASS) + `TestDllFailureFailLoud` (verifies RuntimeError on missing deps). |
| **Blind spots** | (1) Keyword-based — well-structured argument without exact keyword matches will score poorly. (2) `detect_clarte()` uses Flesch reading ease (English formula on French text). (3) `detect_analogie_pertinente()` only checks for analogy phrases — cannot evaluate pertinence. |
| **Verdict** | **TRUSTWORTHY** — Deterministic, no LLM, value-gate tests pass, fail-loud instead of silent degradation (#1019). Keyword limitation is known and acceptable for Phase 4 scoring. |

### 7. Counter-Argument Generation

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/counter_argument/counter_agent.py`, `strategies.py`, `evaluator.py`, `parser.py` |
| **Produces** | `CounterArgument` dataclass with 5-criteria evaluation (relevance, logical_strength, persuasiveness, originality, clarity). 5 rhetorical strategies (reductio ad absurdum, counter-example, distinction, reformulation, concession). |
| **Value-gate tests** | **YES** — `TestCounterArgValueGate` (3 tests, PASS). Asserts no fabricated "15%", template tag present, other 4 strategies unchanged. |
| **Blind spots** | (1) LLM failure silently falls back to template. (2) `ArgumentParser` splits by `[.!?]+` regex — cannot handle abbreviations, decimal numbers. (3) `VulnerabilityAnalyzer._check_coherence()` checks keyword overlap only — trivially satisfied. |
| **Verdict** | **PARTIAL** — Structure is complete (5 strategies + 5-criteria evaluator). Statistical template now marked as `[template/placeholder]` (#962). LLM path works when available. |

### 8. Debate Agent

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/debate/debate_agent.py`, `debate_scoring.py`, `knowledge_base.py`, `protocols.py` |
| **Produces** | `EnhancedArgument` with 8 metrics (logical_coherence, evidence_quality, relevance, emotional_appeal, readability, fact_check, novelty, persuasiveness). `DebateState` with winner, audience_votes, performance_metrics. |
| **Value-gate tests** | **YES** — `TestDebateValueGate` (2 tests, PASS). Asserts winner is agent name, arguments have content. |
| **Blind spots** | (1) Fallback `_create_fallback_argument()` produces generic text with `persuasiveness=0.3`. (2) ~~`_assess_logical_coherence()` counts English connectors~~ — **FIXED (#967)**: now bilingual (EN+FR connectors). (3) `protocols.py` (6 Walton-Krabbe types) and `KnowledgeBase` are dead code — never called. (4) `_identify_weakness()` returns arbitrary "lowest" from flat defaults. |
| **Verdict** | **PARTIAL** — Value-gate tests pass (via fallback). ~~English-only connector scoring~~ fixed (#967). Protocols/KB are dead code. |

### 9. Governance (7 Votes)

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/governance/governance_methods.py`, `simulation.py`, `social_choice.py`, `conflict_resolution.py`, `metrics.py` |
| **Produces** | 7 voting methods (majority, plurality, Borda, Condorcet, quadratic, byzantine, raft). `simulate_governance()` returns winner, satisfaction, coalitions, conflict history. |
| **Value-gate tests** | **YES** — `TestGovernanceValueGate` (3 tests, PASS) + `TestConflictResolutionHonestProb` (3 tests, PASS) + `TestKemenyYoungSafeFallback` (3 tests, PASS). |
| **Blind spots** | (1) ~~`conflict_resolution.py` returns hardcoded success probabilities (0.8/0.5/0.7)~~ — **FIXED (#971)**: returns `None` (honest placeholder). (2) ~~Kemeny-Young is O(n!), raises `ValueError` for >8 candidates, no fallback~~ — **FIXED (#971)**: `kemeny_young_safe()` falls back to Copeland (O(n²)) with `approximate=True` flag. (3) `byzantine_consensus` uses `np.random.choice` for faulty agents — not reproducible. (4) Requires agents with `.decide()` + `.preferences` interface — silently fails otherwise. |
| **Verdict** | **PARTIAL** — Voting methods are real implementations. ~~Conflict resolution is hardcoded.~~ Fabricated probabilities fixed (#971). Kemeny-Young has Copeland fallback (#971). Byzantine randomness remains. |

### 10. JTMS (Justification-based Truth Maintenance)

| Aspect | Finding |
|--------|---------|
| **Files** | `services/jtms/jtms_core.py`, `atms_core.py`, `extended_belief.py`, `conflict_resolution.py` |
| **Produces** | Beliefs with tri-state truth values (None/True/False), justifications with in/out lists, retraction chains, belief explanations. ATMS: environment-based label tracking, consistency checks. |
| **Value-gate tests** | **NONE** in `test_value_gates.py`. |
| **Blind spots** | (1) `update_non_monotonic_beliefs()` requires `networkx` — SCC detection silently disabled without it, all beliefs treated as monotonic (correctness issue). (2) `propagate()` re-entrant guard silently skips propagation in complex graphs. (3) `add_justification()` auto-creates missing beliefs in non-strict mode — spurious beliefs from typos. (4) ATMS label computation is exponential (Cartesian product of in-node labels). |
| **Verdict** | **PARTIAL** — Core JTMS logic is sound. ATMS exponential blow-up and silent networkx dependency are production risks. No value-gate test. |

### 11. Narrative Synthesis

| Aspect | Finding |
|--------|---------|
| **Files** | `plugins/narrative_synthesis_plugin.py`, `invoke_callables.py:5702+` |
| **Produces** | 1-2 paragraphs of French prose from `UnifiedAnalysisState`. Template-based concatenation of state fields (quality, fallacies, counter-args, Dung, FOL, PL, modal, JTMS, ATMS). Convergence synthesis counts cross-method flags. **Fail-explicit (#1019)**: no template-rebuild fallback — if state is empty, returns sentinel and logs diagnostic (available phase outputs, populated state fields). Root cause must be fixed upstream. |
| **Value-gate tests** | **YES** — `TestNarrativeSynthesisValueGate` (3 tests, PASS). Asserts ≥2 field keywords, non-boilerplate content, ≥3 referenced fields. |
| **Blind spots** | (1) Purely template-based — no LLM narrative weaving. (2) `getattr(state, "field", default)` pattern — mismatched attribute names silently missed. (3) `_dung_rejected_args()` uses string prefix matching to map free-text to canonical IDs. |
| **Verdict** | **TRUSTWORTHY** — Deterministic, value-gate tests pass, fail-explicit (#1019). Template limitation is by-design (anti-LLM-dependency). |

### 12. Fact Extraction

| Aspect | Finding |
|--------|---------|
| **Files** | `agents/core/extract/extract_agent.py`, `agents/tools/analysis/fact_claim_extractor.py` |
| **Produces** | `ExtractResult` with source_name, extract_name, status (valid/rejected/error), extracted_text. Pipeline: LLM proposes markers → native plugin extracts → optional validation. |
| **Value-gate tests** | **YES** — `TestFactExtractionValueGate` (3 tests, PASS). Asserts extraction from known sources. |
| **Blind spots** | (1) LLM must propose *exact text markers* — hallucinated markers cause failure (most common error mode). (2) `invoke_single()` uses regex to extract target name from chat — falls back to hardcoded default. (3) Validation step is optional, not auto-triggered. |
| **Verdict** | **PARTIAL** — Value-gate tests pass. LLM marker dependency is fragile but documented. |

---

## Satellite Formal Bricks (12)

| # | Brick | Handler | Real Logic | Tests | Fallback Quality | Verdict |
|---|-------|---------|-----------|-------|-----------------|---------|
| 1 | **SAT** | `sat_handler.py` | PySAT + Z3-MARCO | Dedicated (514 lines) | NONE (raises `RuntimeError` without PySAT) | **PARTIAL** |
| 2 | **SetAF** | `setaf_handler.py` | Tweety JVM, 10 semantics | Value-gate (#964) | Honest unavailable (#964) | **PARTIAL** |
| 3 | **Weighted** | `weighted_handler.py` | Tweety JVM, 6 semantics | Value-gate (#964) | Honest unavailable (#964) | **PARTIAL** |
| 4 | **EAF** | `eaf_handler.py` | Tweety JVM, 5 semantics | Integration only | Reasonable: subgraph enumeration with probability | **PARTIAL** |
| 5 | **DeLP** | `delp_handler.py` | Tweety JVM, dialectical trees | Value-gate (#964) | Honest unavailable (#964) | **PARTIAL** |
| 6 | **QBF** | `qbf_handler.py` + `qbf_native.py` | JVM + native Python | Dedicated native + integration | Good: native fallback chain | **TRUSTWORTHY** |
| 7 | **ABA** | `aba_handler.py` | Tweety JVM, 6 semantics | Mock (Track A) | Degenerate: empty extensions | **PARTIAL** |
| 8 | **ADF** | `adf_handler.py` | Tweety JVM, 7 semantics | Mock (Track A) | Degenerate: empty interpretations | **PARTIAL** |
| 9 | **Bipolar** | `bipolar_handler.py` | JVM metadata only (no reasoning) | Value-gate (#964) | Honest unavailable (#964) | **PARTIAL** |
| 10 | **Probabilistic** | `probabilistic_handler.py` | Tweety JVM, subgraph enumeration | Mock (Track A) | Degenerate: all `0.5` | **PARTIAL** |
| 11 | **Dialogue** | `dialogue_handler.py` | JVM grounded extension + simulated trace | Mock (Track A) + integration | Reasonable: simulated rounds | **PARTIAL** |
| 12 | **Belief Revision** | `belief_revision_handler.py` | Tweety JVM, AGM (Dalal + Levi) | Extensive (Track A + spectacular + conversational + ATMS) | Degenerate: simple union (no contraction) | **PARTIAL** |

---

## Summary Scorecard

### Core Subsystems

| Subsystem | Verdict | Value-Gate | Key Risk |
|-----------|---------|-----------|----------|
| Informal Fallacy | PARTIAL | ✅ (3/3 PASS) | Taxonomy substring-literal honestly characterised (#973), mock adapter fallback |
| Dung/ASPIC | PARTIAL | ✅ (9/9 PASS) | ~~DFS shadowing + no size guard~~ FIXED (#970), ~~Python grounded-only~~ 4-semantics (#1019), >25 args = grounded only |
| FOL | PARTIAL | ✅ (3/3 PASS) | Heuristic fallback eliminated (#1019), preflight check, solver non-determinism |
| PL | PARTIAL | ✅ (3/3 PASS) | Heavy LLM dependency, JVM-only, value-gate added (#977) |
| Modal Logic | PARTIAL | ✅ (2/2 PASS) | Heuristic fallback eliminated (#1019), no pure-Python fallback |
| Quality (9 virtues) | **TRUSTWORTHY** | ✅ (3/3 PASS) | Fail-loud (#1019), keyword limitation acceptable |
| Counter-Argument | PARTIAL | ✅ (3/3 PASS) | Fabricated statistics removed (#962), template placeholder tagged |
| Debate | PARTIAL | ✅ (5/5 PASS) | ~~English-only scoring~~ fixed (#967), dead protocol code |
| Governance | PARTIAL | ✅ (9/9 PASS) | ~~Hardcoded conflict resolution~~ fixed (#971), ~~Kemeny O(n!)~~ Copeland fallback (#971) |
| JTMS | PARTIAL | ✅ (3/3 PASS) | networkx silent dependency, exponential ATMS |
| Narrative Synthesis | **TRUSTWORTHY** | ✅ (3/3 PASS) | Fail-explicit (#1019), template-only by design |
| Fact Extraction | PARTIAL | ✅ (3/3 PASS) | LLM marker hallucination |

### Satellite Bricks

| Brick | Verdict | Key Risk |
|-------|---------|----------|
| SAT | PARTIAL | RuntimeError without PySAT |
| SetAF | PARTIAL | Honest unavailable (#964), JVM-dependent |
| Weighted | PARTIAL | Honest unavailable (#964), JVM-dependent |
| EAF | PARTIAL | Reasonable fallback, no unit test |
| DeLP | PARTIAL | Honest unavailable (#964), JVM-dependent |
| QBF | **TRUSTWORTHY** | Native fallback chain works |
| ABA | PARTIAL | Mock tests only, empty fallback |
| ADF | PARTIAL | Mock tests only, empty fallback |
| Bipolar | PARTIAL | Honest unavailable (#964), JVM-dependent |
| Probabilistic | PARTIAL | All-0.5 fallback |
| Dialogue | PARTIAL | Simulated trace, reasonable fallback |
| Belief Revision | PARTIAL | Degenerate union fallback, extensive tests |

### Aggregate

| Verdict | Core | Satellite | Total |
|---------|------|-----------|-------|
| **TRUSTWORTHY** | 2 (Quality, Narrative) | 1 (QBF) | **3** |
| **PARTIAL** | 10 | 12 | **22** |
| **UNTRUSTED** | 0 | 0 | **0** |

---

## Recommendations for Phase 4

### Must-fix before spectacular reports

1. ~~**Modal heuristic**~~ — ✅ Fixed (#963). Reports honest `valid: None, solver: "unavailable"`.
2. ~~**Satellite UNTRUSTED bricks**~~ — ✅ Fixed (#964). All 4 report honest unavailable status with value-gate tests.
3. ~~**Counter-argument fabricated statistics**~~ — ✅ Fixed (#962). Statistical template tagged `[template/placeholder]`, no invented percentages.

### Should-fix for credibility

4. ~~**Dung Python fallback**~~ — ✅ Fixed (#1019/#1025). Python fallback now computes grounded+complete+preferred+stable (4 semantics). Cap at 25 args; beyond that, only grounded (logged WARNING).
5. **Quality keyword dependency** — Well-structured arguments without the exact French keywords score poorly. Document the keyword list in output.
6. **JTMS networkx dependency** — Silently degrades to monotonic-only. Log a warning when networkx is unavailable.

### Nice-to-have

7. **Formal brick value-gate tests** — SetAF, Weighted, DeLP have zero test coverage. Even degenerate-fallback-aware tests would catch regressions.
8. **Debate protocol activation** — Protocols.py has 6 Walton-Krabbe types defined but never used. Either activate or document as future work.
9. ~~**Governance conflict resolution**~~ — ✅ Fixed (#971). Hardcoded probabilities replaced with `None` (honest placeholder). Kemeny-Young has Copeland fallback.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-06-05 | myia-po-2023 | Initial verdict — all 24 subsystems audited |
| 2026-06-06 | myia-po-2023 | Update: Modal UNTRUSTED→PARTIAL (#963), Counter-arg fix (#962), Satellites UNTRUSTED→PARTIAL (#964). 0 UNTRUSTED remaining. |
| 2026-06-06 | myia-po-2023 | Value-gate coverage raised: Dung ✅, Governance ✅, JTMS ✅ (#965). Coverage: 9/12 core with value-gate tests. |
| 2026-06-06 | myia-po-2023 | Debate scoring i18n: EN+FR connectors bilingue (#967). Value-gate: 5/5 PASS. |
| 2026-06-06 | myia-po-2023 | Dung DFS shadowing fixed + exponential guard (#970). Value-gate: 9/9 PASS. |
| 2026-06-06 | myia-po-2023 | Governance fabricated probs → None (#971), Kemeny-Young Copeland fallback (#971). Value-gate: 9/9 PASS. |
| 2026-06-06 | myia-po-2023 | Informal taxonomy value-gate: 3/3 PASS (#973). Coverage 10/12 core. Substring limitation honestly pinned. |
| 2026-06-06 | myia-po-2023 | FOL + PL value-gate regression guards (#976 #977). Coverage: 12/12 core with value-gate tests. |
| 2026-06-09 | myia-po-2023 | Post-#1019 refresh: Dung 4-sem Python fallback (#1025), FOL/Modal heuristic fallbacks eliminated (#1025), Quality fail-loud (#1026), Narrative fail-explicit (#1025), spectacular tri-state None/True/False preserved (#1028). Recommendations #4 and #9 marked fixed. |
