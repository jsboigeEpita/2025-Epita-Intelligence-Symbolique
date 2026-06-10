# FB-18 Design Spec — Grounded Deep Synthesis + PM Agentique End-to-End

**Issue**: #1039 (Epic #947 Phase 4 follow-up)
**Author**: po-2023 worker (design spec)
**Date**: 2026-06-11
**Status**: DRAFT — awaiting review + implementation by po-2025

---

## 1. Problem Statement

The yardstick corpus_X benchmark (#1027) shows that **synthesis-level dimensions** (D1 jargon-as-structure, D5 structural parallel, D8 permission architecture) are MISSED by construction. These are *transversal insights* that no per-argument detector can produce. The current `NarrativeSynthesisAgent` is template-based by design (TRUSTWORTHY, anti-theater) — it produces deterministic convergence summaries but cannot generate the interpretive depth the yardstick demands.

More fundamentally, the user mandate (2026-06-10) identifies that this gap is not just a missing phase — it reflects the **marginalization of agent-driven intuition** over the past year. The original pipeline (CoursIA lineage, Sherlock/Watson paradigm) had an LLM PM that used its intuition **from start to finish**, directing symbolic tools as instruments. The shift to deterministic DAG (for reproducibility, budget control, value-gates) eliminated this. The mandate asks: evaluate what was lost and how to restore it without sacrificing what the DAG gained.

---

## 2. Architectural Analysis — What Was Marginalized

### 2.1 The Intuition-Driven Pattern (Sherlock / Conversational)

| Component | Location | Pattern |
|-----------|----------|---------|
| `SherlockEnqueteAgent` | `agents/core/pm/` | Single LLM role with autonomous decision-making. Chat history drives behavior — no DAG, no fixed edges. "Exceptional intuition" via prompt framing. |
| `ConversationalOrchestrator` | `orchestration/` | PM designates next agent dynamically via `designate_next_agent()`. Growth fingerprint validation + re-prompting (up to 2x per turn). Cross-KB enrichment explicitly instructed ("ask QualityAgent to account for detected fallacies"). |
| `_internal_explore_hierarchy` | `agents/core/informal/` | Iterative taxonomy drill: depth 1 → 2 → 3 per step, max 15 children per level. Agent "discovers" fallacies rather than classifying against flat list. |
| JTMS inter-phase retraction | `conversational_orchestrator.py:751` | Beliefs associated with detected fallacies are automatically retracted between phases — reactive TMS behavior. |

### 2.2 What the DAG Replaced It With

| Aspect | Intuition Pattern | DAG Pattern |
|--------|-------------------|-------------|
| Agent selection | PM decides dynamically | Fixed edges, fan-out predetermined |
| Fallacy detection | Iterative taxonomy drill (depth 1→2→3) | Flat multi-label classification |
| Growth control | Fingerprint + re-prompt feedback | Budget ceiling + turn limits |
| Cross-agent coordination | PM orchestrates via designation | Parallel independent + state merge |
| Error recovery | Re-prompt up to 2x per turn | Harness fallbacks post-phase |
| Timing | Path-dependent (turn budget, order) | Deterministic (parallel, predictable) |

### 2.3 What Was Lost

1. **Adaptive discovery** — the PM could notice it missed something and go back (re-prompt, designate differently). The DAG cannot.
2. **Cross-pollination** — the PM explicitly created synergies between agents ("ask QualityAgent to account for fallacies"). The DAG runs agents in parallel with shared state but no explicit coordination.
3. **Iterative depth** — `_internal_explore_hierarchy` lets the LLM drill progressively deeper. The DAG collapses this to a flat classification pass.
4. **Synthesis-level insight** — no phase in the DAG produces transversal, interpretive analysis anchored in verified artifacts.

### 2.4 What Was Gained (Must Preserve)

1. **Reproducibility** — same input → same DAG traversal → same phases → comparable results across runs.
2. **Budget predictability** — fixed number of LLM calls, no runaway re-prompt loops.
3. **Value-gates** — each phase has testable correctness criteria (TRUSTWORTHY/PARTIAL/UNTRUSTED).
4. **Parallelism** — independent phases run concurrently, wall-clock is bounded.

---

## 3. Design — Two Complementary Modes

The mandate's anti-pendule is clear: **do not throw away the DAG** (reproducibility, value-gates). The two modes should be **comparable axes of configuration** (north-star R311), not a replacement.

### 3.1 Mode A: DAG + Grounded Deep Synthesis (minimal, add-on)

Add a **terminal `deep_synthesis` phase** to the spectacular DAG (after all other phases complete). This is the minimum viable version.

**Input contract** (what the phase consumes from `UnifiedAnalysisState`):

| Field | Source Phase | Content |
|-------|-------------|---------|
| `identified_arguments` | extract | Extracted argument list |
| `fallacy_analysis` | hierarchical_fallacy | Detected fallacies with taxonomy labels |
| `dung_extensions` | dung_extensions | Extension sets per semantics |
| `pl_results` / `fol_results` / `modal_results` | pl / fol / modal | Verified formula analysis |
| `quality_scores` | quality | 9-virtue scores per argument |
| `counter_arguments` | counter | Generated counter-arguments |
| `jtms_beliefs` | jtms | Justified beliefs with justifications |
| `debate_results` | debate | Multi-personality debate transcript |
| `governance_results` | governance | Voting outcomes |
| `narrative_synthesis` | narrative_synthesis | Template-based convergence summary |

**Phase behavior**:

1. **Guard**: If state has < 3 populated artifact fields → `fail_explicit` (return "Insufficient artifacts for grounded synthesis — state empty or near-empty", inheriting #1019 fail-loud discipline). No boilerplate, no hallucinated synthesis.
2. **Prompt**: The LLM receives an **intelligence briefing** (not the raw text). The briefing is a structured digest of the verified artifacts, organized as:
   - **Identification**: What arguments were found, how many, their types
   - **Diagnostics**: What fallacies were detected, which families, severity
   - **Formal verification**: What the solvers proved (PL tautologies, FOL inconsistencies, Dung extensions)
   - **Quality assessment**: Virtue scores, weak spots
   - **Counter-arguments**: Generated opposition strategies
   - **Belief state**: JTMS justifications and retractions
3. **Artifact anchoring requirement**: Each insight in the synthesis MUST cite ≥1 specific artifact (e.g., "Argument 3 was flagged as ad populum [fallacy_analysis.arg3.type], which the Dung grounded extension excludes [dung_extensions.grounded.excludes=arg3], and the quality score confirms low fiabilité_sources [quality.arg3.fiabilite_sources=0.2]").
4. **Output format**: Structured markdown with sections (not free prose):
   - `## Transversal Patterns` — cross-argument insights that no single detector produces
   - `## Rhetorical Strategy Assessment` — how arguments work together as a system
   - `## Structural Vulnerabilities` — what the formal analysis reveals about argumentative weaknesses
   - `## Interpretive Synthesis` — the "so what?" — what the whole picture means
   - Each section: prose + inline artifact citations

**Value-gates**:

| Gate | Criterion | Pass Condition |
|------|-----------|---------------|
| VG-1 | Artifact citation density | ≥1 citation per 200 words of synthesis |
| VG-2 | State-empty guard | Returns explicit failure message when < 3 artifact fields populated |
| VG-3 | No boilerplate | Output is not a restatement of the narrative template |
| VG-4 | Transversal insight | At least 1 insight spans ≥2 different artifact types (e.g., fallacy + Dung) |

### 3.2 Mode B: PM-Agentique End-to-End (full restoration, comparable axis)

Restore the PM agentique as a **complete orchestration mode** comparable to the DAG, not layered on top of it.

**Design**:

1. **PM Agent** — an LLM agent (ChatCompletionAgent) with:
   - Access to all state-reading tools (`get_current_state_snapshot`, `_internal_explore_hierarchy`, individual agent invocation)
   - Explicit designation power (`designate_next_agent`)
   - Growth fingerprint validation (inherited from `ConversationalOrchestrator`)
   - Budget enforcement via circuit breaker (inherited from #708, `LLMBudgetGuard`)
   - System prompt framing: "You are the PM conducting an analysis. You have verified symbolic tools at your disposal. Your intuition guides which tools to invoke and when. After each tool result, decide: go deeper, switch tool, or synthesize."

2. **Conduction loop**:
   ```
   PM reads state → PM decides next action → invoke tool/agent → update state →
   growth validation → if no growth, re-prompt (max 2x) → if growth, PM reads updated state → ...
   → convergence: PM signals final_synthesis_ready → produce grounded deep synthesis (Mode A's prompt)
   ```

3. **Integration with taxonomy deep-descent** (FB-19 #1040): The PM's intuition guides the descent — it selects which family branches to explore deeper, not a fixed depth expansion. The `_internal_explore_hierarchy` primitive is the natural tool for this.

4. **Configuration**: `--mode pm_agentique` (alongside `--mode pipeline` and `--mode conversational`). The benchmark (yardstick scoring) can compare:
   - `pipeline-DAG` (current spectacular)
   - `pm-agentique` (PM-conducted)
   - `0-shot` (baseline)

**Why this is comparable and not a replacement**:
- Same input text, same state schema, same yardstick dimensions → scores are directly comparable
- Same value-gates apply (artifact anchoring, fail-explicit on empty state)
- Same budget guard (LLMBudgetGuard)
- Different orchestration path → different strengths/weaknesses
- North-star R311: both modes are parameters, the user chooses

### 3.3 What To Implement First (Priority)

**Phase 1 — Mode A (grounded deep synthesis terminal phase)**:
- Immediate impact on D1/D5/D8 scoring (the transversal insights the yardstick demands)
- Minimal change to the DAG (add one phase at the end)
- Testable via value-gates VG-1 through VG-4
- Implementation: `invoke_callables.py` new callable + `state_writers.py` new writer

**Phase 2 — Mode B (PM-agentique end-to-end)**:
- Larger change — re-activates ConversationalOrchestrator patterns
- Requires careful budget bounding (circuit breaker mandatory)
- Depends on taxonomy deep-descent (FB-19) for full value
- Implementation: separate orchestrator path, not modification of existing DAG

---

## 4. Reference Design Patterns

### 4.1 Sherlock as Reference (Not To Merge)

`sherlock_enquete_agent.py` demonstrates the pure intuition pattern: a single LLM with tool access, driven entirely by chat history. Key lessons:

- **Tool registration** — Sherlock registers its own plugin on the kernel. The PM agentique would register all analysis tools (not just investigation tools).
- **Chat-history-driven** — No structured prompt per step. The PM reads the conversation to decide. This is the opposite of the DAG's explicit phase prompts.
- **Autonomous decision-making** — Sherlock decides what to investigate next without external orchestration. The PM agentique needs this autonomy BUT with budget/growth constraints.

### 4.2 ConversationalOrchestrator as Base (To Extend)

The `ConversationalOrchestrator` already has 90% of what Mode B needs:

- **Growth fingerprint** (`_get_growth_fingerprint`) — 12 counters covering all state dimensions
- **Re-prompting** with explicit feedback ("Your previous response did not produce state changes")
- **Designated-agent** pattern (PM → specific agent)
- **Phase transitions** with convergence detection
- **Harness fallbacks** (post-phase enrichment for gaps)

What it lacks:
- **Deep synthesis phase** (the terminal interpretive output)
- **Full spectacular coverage** (it doesn't invoke all 30 phases — harness fallbacks fill gaps)
- **Budget hard-guard** (turn limits but no token budget enforcement)

---

## 5. Anti-Pendule Commitments

| Concern | Guard |
|---------|-------|
| Replacing the DAG | Mode B is a **separate config axis**, not a replacement. The DAG remains the default. |
| Hallucinated synthesis | VG-1 (artifact citation density) + VG-2 (state-empty guard). Each claim anchored in verified artifact. |
| Runaway PM | Circuit breaker from #708 (`LLMBudgetGuard`), max re-prompts (2), convergence detection. |
| Theater (easy-pass bar) | The rubric (#1038) can say LOSES/TIES honestly. The spec does not guarantee a pass. |
| Corpus-X tuning | Deep descent is generic (guided by text, not yardstick targets). No hardcoded PKs. |
| Boilerplate synthesis | VG-3 (no boilerplate) + prompt framing as intelligence briefing (not summary task). |

---

## 6. Expected Impact on Yardstick Scoring

### Mode A (deep synthesis phase only)

| Dimension | Current (#1027) | Expected with deep_synthesis | Rationale |
|-----------|-----------------|------------------------------|-----------|
| D1 Jargon | PARTIAL | **MATCH** | Cross-argument jargon pattern visible in synthesis |
| D2 Contradictions | MATCH | MATCH | No regression |
| D5 Historical | PARTIAL | **MATCH** | Structural pattern detection across arguments |
| D8 Permission | PARTIAL | **MATCH** | Escalation pattern synthesis across the argument chain |
| D1/D5/D8 aggregate | 3×PARTIAL | 3×MATCH | score_A shifts +3 → total +5 → EDGES |

This is the **minimum** needed to move from TIES (score_A = -1) to EDGES (score_A ≥ +3).

### Mode B (PM-agentique + FB-19 deep descent)

| Dimension | Current (#1027) | Expected | Rationale |
|-----------|-----------------|----------|-----------|
| D3 Populist | MISSED | PARTIAL | PM-guided descent reaches Populisme PK 1211 |
| D6 Circular | MISSED | PARTIAL | Iterative drill finds Argument circulaire PK 699 |
| D7 Drive-Relief | MISSED | PARTIAL | Emotional markers surfaced by PM intuition |
| D3/D6/D7 aggregate | 3×MISSED | 3×PARTIAL | score_A shifts +3 → total +8 → DECIDES |

Full Mode B + FB-19 could reach DECIDES. But this is speculative — the honest assessment is that Mode A is the surest path to EDGES, and Mode B's additional value depends on FB-19 implementation.

---

## 7. Privacy Compliance

- Opaque IDs only: `corpus_X`, `doc_A/B/C`, `D1`–`D10`, `Speaker_A`
- No source names, authors, URLs, dates
- No `raw_text`, `full_text`, `full_text_segment`
- Code references use file paths and line numbers only
- grep-clean (verified before commit)

---

## 8. Cross-References

| Artifact | Issue/PR | Role |
|----------|----------|------|
| Phase 4 verdict rubric | #1037 / PR #1038 | Closure criteria (the bar this spec tries to clear) |
| corpus_X yardstick | #952 / #958 | D1-D10 dimension definitions |
| corpus_X benchmark | #953 → #1027 | Current scoring (MATCH 2, PARTIAL 5, MISSED 3) |
| FB-15 enrichment | #1032 / #1034 | Attempted D3/D6/D7 enrichment (no delta on corpus_X) |
| FB-15 value-gates | #1036 | Proves enrichment load-bearing in pipeline chain |
| CAPSTONE comparison | #1033 | Pipeline vs 0-shot on doc_A/B/C (pipeline > 0-shot on fallacies) |
| Subsystem verdict | #957 | 3 TRUSTWORTHY, 22 PARTIAL, 0 UNTRUSTED |
| Taxonomy deep-descent | #1040 (FB-19) | Complementary — PM intuition guides descent |
| Sherlock reference | `agents/core/pm/sherlock_enquete_agent.py` | Intuition-driven PM pattern (study, not merge) |
| ConversationalOrchestrator | `orchestration/conversational_orchestrator.py` | Base for Mode B (growth validation, designated-agent) |
| LLM Budget Guard | #1029 / #1030 | Circuit breaker for PM-agentique budget enforcement |
