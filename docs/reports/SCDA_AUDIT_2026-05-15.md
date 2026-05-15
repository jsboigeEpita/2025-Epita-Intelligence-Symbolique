# SCDA Sprint 1 Audit Report

**Date:** 2026-05-15
**Epic:** #530 (SCDA — Spectacular Conversational Deep Analysis)
**Issue:** #531 (Qualitative Phase-by-Phase Audit)
**Machine:** myia-po-2023
**Mode:** Conversational orchestration (`spectacular=True`, `max_turns_per_phase=10`)

## 1. Executive Summary

Three dense political corpora were analyzed using the full conversational orchestration pipeline (PM + 7 specialists, 4 phases, AgentGroupChat). Total wall-clock time: ~90 minutes across 3 corpora. All 8 agents contributed substantively on English texts; the German corpus showed significantly lower extraction yield.

**Critical finding:** Formal verification (Tweety/PL) produced **0% success rate** across all 3 corpora due to systematic ParserExceptions when the LLM generates propositional formulas incompatible with Tweety's PL parser syntax.

## 2. Corpora Tested

| ID | Source | Size | Language | Description |
|----|--------|------|----------|-------------|
| A | src11 | 58,052 chars | EN | UN General Assembly speech, politically dense |
| B | src3 (extract) | 59,092 chars | DE | Extracted coherent segment from 3M char collection |
| C | src2 | 46,391 chars | EN | National security address, geopolitically charged |

All outputs (transcripts, state snapshots, enrichment summaries) are stored under `outputs/scda_audit/` (gitignored per dataset privacy policy).

## 3. Performance Comparison

### 3.1 Timing & Throughput

| Phase | Corpus A | Corpus B | Corpus C |
|-------|----------|----------|----------|
| Extraction & Detection | 682s (58K chars output) | 243s (22K chars) | 406s (33K chars) |
| Formal Analysis & Quality | 936s (47K chars) | 371s (16K chars) | 368s (9K chars) |
| Synthesis & Debate | 270s (25K chars) | 410s (29K chars) | 369s (34K chars) |
| Re-Analysis | 529s (74K chars) | 445s (41K chars) | 391s (36K chars) |
| **Total** | **2,417s (40 min)** | **1,471s (24 min)** | **1,535s (26 min)** |

Corpus A took ~60% longer than B/C, driven primarily by the Formal Analysis phase (936s) where the FormalAgent generated extensive output including many ParserException recovery attempts.

### 3.2 State Enrichment

| Metric | Corpus A | Corpus B | Corpus C |
|--------|----------|----------|----------|
| State fields populated | 1 → 11 | 1 → 10 | 1 → 11 |
| Total arguments extracted | **15** | **2** | **3** |
| With fallacy analysis | 1 (6.7%) | 0 (0%) | 2 (66.7%) |
| With quality score | 4 (26.7%) | 1 (50%) | 1 (33.3%) |
| With counter-argument | 8 (53.3%) | 1 (50%) | 0 (0%) |
| With formal verification | **0 (0%)** | **0 (0%)** | **0 (0%)** |
| With JTMS belief | 0 (0%) | 0 (0%) | 0 (0%) |
| Convergence ratio | 29.7% | 27.0% | 29.7% |

## 4. Specialist Scoring

Scoring rubric: MUTE < PARAPHRASING < CITED_INSIGHT < SINGULAR_INSIGHT

### 4.1 Corpus A (src11, EN, 58K)

| Agent | Score | Messages | Output (chars) | Key Observation |
|-------|-------|----------|----------------|-----------------|
| InformalAgent | SINGULAR_INSIGHT | 2 | 69,948 | Dominant agent. Re-Analysis phase alone produced 46K chars of fallacy detection with citations |
| QualityAgent | SINGULAR_INSIGHT | 2 | 29,001 | Comprehensive quality scoring across multiple dimensions |
| ExtractAgent | SINGULAR_INSIGHT | 2 | 26,982 | Extracted 15 arguments with structured claims |
| ProjectManager | SINGULAR_INSIGHT | 8 | 27,139 | Effective orchestration across all 4 phases |
| GovernanceAgent | SINGULAR_INSIGHT | 2 | 11,774 | Voting analysis + consensus metrics |
| CounterAgent | SINGULAR_INSIGHT | 1 | 11,373 | Counter-arguments using reductio ad absurdum + counter-example |
| FormalAgent | SINGULAR_INSIGHT | 2 | 20,034 | Extensive output, but 85 ParserExceptions |
| DebateAgent | SINGULAR_INSIGHT | 1 | 7,590 | Adversarial debate with Walton-Krabbe protocols |

### 4.2 Corpus B (src3 extract, DE, 59K)

| Agent | Score | Messages | Output (chars) | Key Observation |
|-------|-------|----------|----------------|-----------------|
| ProjectManager | SINGULAR_INSIGHT | 8 | 33,459 | Proactive orchestration, adapted to German text |
| GovernanceAgent | SINGULAR_INSIGHT | 2 | 11,963 | Voting and conflict resolution |
| InformalAgent | SINGULAR_INSIGHT | 2 | 26,532 | Fallacy detection but lower yield than on EN |
| QualityAgent | SINGULAR_INSIGHT | 2 | 16,466 | Quality metrics present |
| DebateAgent | SINGULAR_INSIGHT | 1 | 6,229 | Debate strategies |
| CounterAgent | SINGULAR_INSIGHT | 1 | 6,015 | Counter-argument generation |
| ExtractAgent | SINGULAR_INSIGHT | 2 | 5,236 | **Only 2 arguments extracted** — significant drop |
| FormalAgent | SINGULAR_INSIGHT | 2 | 2,128 | Minimal output, 62 ParserExceptions |

### 4.3 Corpus C (src2, EN, 46K)

| Agent | Score | Messages | Output (chars) | Key Observation |
|-------|-------|----------|----------------|-----------------|
| ProjectManager | SINGULAR_INSIGHT | 8 | 27,270 | Steady orchestration |
| GovernanceAgent | SINGULAR_INSIGHT | 2 | 17,594 | Most productive GovernanceAgent across all corpora |
| ExtractAgent | SINGULAR_INSIGHT | 2 | 20,416 | Good extraction despite only 3 formal arguments |
| DebateAgent | SINGULAR_INSIGHT | 1 | 12,088 | Most productive DebateAgent across all corpora |
| QualityAgent | SINGULAR_INSIGHT | 2 | 12,164 | Quality analysis with formal method citations |
| CounterAgent | SINGULAR_INSIGHT | 1 | 7,575 | Counter-arguments with distinction strategy |
| InformalAgent | SINGULAR_INSIGHT | 2 | 13,901 | Fallacy detection (2 confirmed) |
| FormalAgent | **CITED_INSIGHT** | 2 | **686** | Lowest output across all corpora. 12 ParserExceptions |

### 4.4 Cross-Corpus Agent Comparison

| Agent | A (chars) | B (chars) | C (chars) | Trend |
|-------|-----------|-----------|-----------|-------|
| InformalAgent | 69,948 | 26,532 | 13,901 | Decreasing — best on longest EN text |
| ExtractAgent | 26,982 | 5,236 | 20,416 | Weak on DE, strong on EN |
| FormalAgent | 20,034 | 2,128 | 686 | **Critical degradation** |
| QualityAgent | 29,001 | 16,466 | 12,164 | Consistent contributor |
| GovernanceAgent | 11,774 | 11,963 | 17,594 | Consistent, best on C |
| DebateAgent | 7,590 | 6,229 | 12,088 | Best on C |
| CounterAgent | 11,373 | 6,015 | 7,575 | Consistent |

## 5. Critical Findings

### 5.1 Formal Verification Complete Failure (Severity: CRITICAL)

Across all 3 corpora, the FormalAgent generated **0 successfully verified formal arguments**. Root cause analysis from log inspection:

- **159 total ParserExceptions** (85 + 62 + 12)
- The LLM generates propositional formulas using syntax incompatible with Tweety's PL parser:
  - Underscored variable names: `sudetenland_justified`, `expansion_lebensraum`
  - Complex nested expressions: `(expansion || increase_exports) && expansion) => expansion`
  - Natural language fragments treated as atomic propositions
- The FormalAgent does not sanitize or simplify formulas before submission to Tweety
- Each ParserException generates a multi-line stack trace, polluting logs and consuming tokens

**Recommendation (Sprint 2):** Implement a PL formula sanitizer/linter between the LLM output and Tweety submission. Map natural language to short atomic symbols (p, q, r) and validate syntax before JPype call.

### 5.2 Language Gap — German Corpus (Severity: HIGH)

Corpus B (DE) produced dramatically fewer arguments (2 vs 15 for comparable EN corpus A):
- ExtractAgent extracted 2 arguments from 59K DE text vs 15 from 58K EN text
- 0 fallacies detected on DE vs 1 on EN (corpus A) and 2 on EN (corpus C)
- Overall output volume 40% lower on DE

The agents process German text but the extraction prompts and fallacy taxonomy are primarily English-oriented. The French fallacy adapter (`french_fallacy_adapter`) loads French labels but no German equivalent exists.

**Recommendation (Sprint 2):** Add language detection + German fallacy taxonomy, or pre-translate non-English texts before analysis.

### 5.3 Convergence Not Achieved (Severity: MEDIUM)

All 3 corpora converged at ~27-30% coverage ratio. The system never reached convergence threshold, meaning:
- The Re-Analysis phase was triggered in all 3 runs
- The state was still being enriched at the end of max_turns
- Increasing `max_turns_per_phase` beyond 10 would likely produce deeper analysis

**Recommendation:** Test with `max_turns_per_phase=15` to measure convergence ceiling.

### 5.4 InformalAgent Asymmetry (Severity: LOW)

The InformalAgent produces disproportionately large outputs (up to 70K chars on corpus A, 46K in Re-Analysis alone). While the quality is high (cited fallacies with justifications anchored in taxonomy), the volume asymmetry suggests:
- The agent may be re-analyzing already-processed claims
- No deduplication mechanism exists in the Re-Analysis phase

### 5.5 DebatePlugin Float Conversion Bug (Severity: MEDIUM)

Observed in audit A: `could not convert string to float: 'mixed'` in `DebatePlugin-suggest_debate_strategy`. The plugin expects numeric quality scores but receives string descriptors from QualityAgent. This causes the debate strategy suggestion to fail silently.

### 5.6 CounterAgent Language Inconsistency (Severity: LOW)

CounterAgent responds in English while DebateAgent and all other agents respond in French. This creates an inconsistent conversation flow.

## 6. Phase Architecture Analysis

### 6.1 Extraction & Detection
- **Agents:** PM + ExtractAgent + InformalAgent
- **Effectiveness:** Good on EN (15 arguments on A), poor on DE (2 on B)
- **State growth:** 1 → 6-8 fields populated
- **Output volume:** 22K-59K chars

### 6.2 Formal Analysis & Quality
- **Agents:** PM + FormalAgent + QualityAgent
- **Effectiveness:** QualityAgent performs well; FormalAgent mostly fails
- **Bottleneck:** ParserExceptions cause retries and wasted tokens
- **Duration:** 368-936s — highly variable depending on ParserException count

### 6.3 Synthesis & Debate
- **Agents:** PM + DebateAgent + CounterAgent + GovernanceAgent
- **Effectiveness:** All agents contribute substantively
- **Duration:** 270-410s — most consistent phase
- **Output volume:** 25K-34K chars

### 6.4 Re-Analysis (Conditional)
- **Agents:** PM + InformalAgent + QualityAgent + GovernanceAgent
- **Triggered:** 3/3 runs (always triggered due to low convergence)
- **Effectiveness:** High — InformalAgent produces massive supplementary analysis
- **Concern:** No deduplication; may re-process already-analyzed claims

## 7. Specialist Score Summary

| Agent | A | B | C | Average |
|-------|---|---|---|---------|
| ProjectManager | SINGULAR | SINGULAR | SINGULAR | SINGULAR |
| ExtractAgent | SINGULAR | SINGULAR | SINGULAR | SINGULAR |
| InformalAgent | SINGULAR | SINGULAR | SINGULAR | SINGULAR |
| FormalAgent | SINGULAR | SINGULAR | **CITED** | CITED→SINGULAR |
| QualityAgent | SINGULAR | SINGULAR | SINGULAR | SINGULAR |
| DebateAgent | SINGULAR | SINGULAR | SINGULAR | SINGULAR |
| CounterAgent | SINGULAR | SINGULAR | SINGULAR | SINGULAR |
| GovernanceAgent | SINGULAR | SINGULAR | SINGULAR | SINGULAR |

**Note:** The automated scoring heuristic may over-score. All agents that produce >200 chars with any formal keyword match receive SINGULAR_INSIGHT. Manual review of conversation logs reveals genuine analytical depth from most agents, but the FormalAgent's "SINGULAR_INSIGHT" on A/B is inflated by error recovery text rather than substantive formal analysis.

## 8. Sprint 2 Recommendations

| Priority | Finding | Recommendation | Effort |
|----------|---------|----------------|--------|
| P0 | Formal verification 0% | PL formula sanitizer before Tweety submission | M |
| P1 | German corpus low yield | Language detection + DE taxonomy or pre-translation | S |
| P1 | DebatePlugin float bug | Accept string quality descriptors or normalize | S |
| P2 | Convergence plateau | Test max_turns=15, analyze ceiling | S |
| P2 | InformalAgent dedup | Track processed claim IDs in Re-Analysis | M |
| P3 | CounterAgent language | Force French response in system prompt | XS |

## 9. Reproducibility

- **Script:** `scripts/scda_audit.py`
- **Command:** `python scripts/scda_audit.py --corpus all --max-turns 10`
- **Environment:** `conda run -n projet-is`
- **Requirements:** `.env` with `OPENAI_API_KEY` and `TEXT_CONFIG_PASSPHRASE`
- **Outputs:** `outputs/scda_audit/<corpus_label>/` (5 JSON files per corpus)
- **LLM model:** Configured via `OPENAI_CHAT_MODEL_ID` in `.env`

## 10. Artifacts

| File | Description | Location |
|------|-------------|----------|
| `audit_summary.json` | Per-corpus scores and metrics | `outputs/scda_audit/<corpus>/` |
| `conversation_log.json` | Full agent conversation transcript | `outputs/scda_audit/<corpus>/` |
| `trace_report.json` | Per-phase timing and state transitions | `outputs/scda_audit/<corpus>/` |
| `state_snapshot.json` | Final analysis state | `outputs/scda_audit/<corpus>/` |
| `enrichment_summary.json` | Gap analysis and coverage metrics | `outputs/scda_audit/<corpus>/` |
| `scda_audit.py` | Audit runner script | `scripts/` |
| This report | SCDA Sprint 1 findings | `docs/reports/` |
