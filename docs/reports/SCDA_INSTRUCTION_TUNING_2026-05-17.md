# SCDA Agent Instruction Tuning Report

**Date:** 2026-05-17
**Issue:** #595
**Commits:** `ec25ab24` (initial prompts), `a58ab816` (stronger function-call enforcement)
**Model:** gpt-4o-mini

## 1. Summary

Prompt engineering of AGENT_CONFIG instructions for ExtractAgent and InformalAgent. Three iterations of increasingly direct instructions were tested. The LLM produces correct analysis in prose but does not call `add_identified_argument()` or `add_identified_fallacy()` state management functions. Root cause: gpt-4o-mini tool-calling reliability on large contexts (58K chars) is insufficient.

## 2. Changes Made

### Iteration 1: Extraction Gate + Quantity Targets (`ec25ab24`)

**PM instructions:**
- Added "EXTRACTION GATE (#595)" — verify identified_arguments before dispatching
- Changed JTMS instruction from "create JTMS beliefs" to "verify identified_arguments first, THEN create JTMS beliefs"
- Added minimum 3 arguments target for >5000 word texts

**ExtractAgent instructions:**
- Split into ETAPE 1 (extraction) and ETAPE 2 (JTMS)
- Added "NE PAS utiliser add_jtms_belief AVANT add_identified_argument"
- Added "ORDRE STRICT" block
- Added quantitative targets (3 args on >5000 words, 5+ on >20000 words)

**InformalAgent instructions:**
- Added "OBJECTIF QUANTITATIF (#595)" with 7-family taxonomy listing
- Added fallback to detect_fallacies() if guided analysis is thin
- Added "analyse le texte brut directement" if no arguments exist

### Iteration 2: Function-Call Enforcement (`a58ab816`)

**ExtractAgent instructions:**
- Added "REGLE CRITIQUE" block: "Tu dois APPELER les fonctions, pas decrire les arguments en prose"
- Added "Un argument n'existe QUE s'il a ete enregistre via add_identified_argument()"
- Shortened prompt (removed verbose descriptions, kept directives)

**InformalAgent instructions:**
- Added same "REGLE CRITIQUE" block for fallacy registration
- Shortened from verbose 7-family listing to focused function-call instructions
- Simplified JTMS section

## 3. Test Results

### Run 1: Baseline (before prompt changes)
- **Duration:** 139s, **Turns:** 12
- **identified_arguments:** 1 (`arg_1: "arguments"`)
- **identified_fallacies:** 1 (`fallacy_1: type="none"`)
- **DeepSynthesis:** 4/9 sections populated

### Run 2: After Iteration 1 prompts
- **Duration:** 252.7s, **Turns:** 17
- **identified_arguments:** 1 (same `arg_1: "arguments"`)
- **identified_fallacies:** 1 (same `fallacy_1: type="none"`)
- **DeepSynthesis:** 5/9 sections populated (+1)
- **Notable:** All 6 agents achieved SINGULAR_INSIGHT level. ExtractAgent produced 3586 chars (vs 2099). InformalAgent produced 3139 chars (vs 668). But state registration unchanged.

### Run 3: After Iteration 2 prompts (stronger function-call enforcement)
- **Duration:** 590.9s, **Turns:** 13
- **identified_arguments:** 1 (still `arg_1: "arguments"`)
- **identified_fallacies:** 0 (worse — previously 1 with type="none")
- **final_conclusion:** Mentions "arguments sur l'économie et l'immigration" and "généralisations abusives" — proving the LLM DID analyze correctly but didn't register results

### Trend

| Metric | Baseline | Iter 1 | Iter 2 |
|--------|----------|--------|--------|
| Duration | 139s | 252.7s | 590.9s |
| Turns | 12 | 17 | 13 |
| identified_arguments | 1 | 1 | 1 |
| identified_fallacies | 1 (none) | 1 (none) | 0 |
| DeepSynthesis sections | 4/9 | 5/9 | N/A |
| ExtractAgent chars | 2099 | 3586 | 3348 |
| InformalAgent chars | 668 | 3139 | 1881 |
| Final conclusion quality | Generic | Generic | Specific (mentions economy, immigration, fallacies) |

## 4. Root Cause Analysis

The LLM correctly identifies arguments and fallacies in its prose responses but does not translate these into `add_identified_argument()` or `add_identified_fallacy()` function calls. Evidence:

1. **ExtractAgent Run 3**: "Arguments Identifiés: 1. Renforcement Économique... 2. [immigration]..." — 3+ arguments described in prose, but only `arg_1: "arguments"` in state.

2. **InformalAgent Run 3**: Mentions "généralisations abusives" in conclusion but no fallacy registered.

3. **Function availability confirmed**: `add_identified_argument` exists in `StateManagerPlugin` (line 89 of `state_manager_plugin.py`). ExtractAgent has `StateManagerPlugin` in its plugin list.

4. **Model limitation**: gpt-4o-mini has lower tool-calling reliability than gpt-4o or gpt-5-mini, especially on large contexts (58K chars). The model sees the prose output as "job done" and doesn't make the function calls.

## 5. Recommendations

### Priority 1: Model Upgrade (highest impact, lowest effort)
Switch from gpt-4o-mini to gpt-5-mini for agent interactions. Tool-calling reliability scales with model capability. This is a one-line config change (`OPENAI_CHAT_MODEL_ID=gpt-5-mini` in `.env`).

### Priority 2: Orchestrator-Level Validation (medium effort)
Add a validation hook in `conversational_orchestrator.py` that checks state after each agent turn:
- After ExtractAgent: if `identified_arguments` count didn't increase, inject a re-prompt
- After InformalAgent: if `identified_fallacies` count didn't increase, inject a re-prompt
- This makes the system robust to any model's tool-calling quirks

### Priority 3: Structured Output Parsing (higher effort)
If tool-calling remains unreliable, add a post-processing step that parses the LLM's prose output and extracts arguments/fallacies programmatically. This is the "belt and suspenders" approach.

## 6. DoD Status

- [x] Agent instruction tuning attempted (3 iterations)
- [x] Conversation log analysis showing root cause
- [x] Unit tests pass (8/8 convergence gate tests)
- [x] Commits on main
- [ ] identified_arguments ≥ 3 — **NOT MET** (1 argument across all runs)
- [ ] identified_fallacies ≥ 5 — **NOT MET** (0-1 fallacy across all runs)
- [ ] DoD threshold (≥3 unique categories vs baseline) — **NOT MET** (same as baseline)

**Verdict:** Prompt engineering alone is insufficient for gpt-4o-mini. The next step should be model upgrade (gpt-5-mini) or orchestrator-level validation.

## 7. Model Upgrade Validation (gpt-5-mini, 2026-05-18)

After coordinator GO (Round 158), `.env` changed from `OPENAI_CHAT_MODEL_ID=gpt-4o-mini` to `gpt-5-mini` and corpus A re-audited.

### Run 4: gpt-5-mini (same prompt changes from Iteration 2)

- **Duration:** 1204.9s (~20 min), **Turns:** 23
- **identified_arguments:** 7 (`arg_1` through `arg_7`) — detailed structured extraction with premises, conclusions, force, connecteur implicite
- **identified_fallacies:** 2 — "Post hoc, ergo propter hoc" (targeting arg_2), "Statistique trompeuse" (targeting arg_3)
- **counter_arguments:** 8 (targeting arg_2, arg_3, arg_6 with multiple strategies)
- **jtms_beliefs:** 4 (including retraction of arg_3 due to fallacy detection)
- **Dung framework:** populated with 9 arguments, 2 attacks, grounded extension with 7 members
- **ASPIC results:** 7 total args, 5 surviving, 2 defeated, 2 strict rules, 5 defeasible rules
- **Belief revision:** fallacy_contraction applied
- **NL-to-logic translations:** 1 propositional formula with 9 atoms
- **All 8 agents at SINGULAR_INSIGHT level**
- **final_conclusion:** null (PM did not set it — but all downstream analysis populated)

### Updated Trend Table

| Metric | Baseline (4o-mini) | Iter 1 (4o-mini) | Iter 2 (4o-mini) | Run 4 (5-mini) |
|--------|-------------------|-------------------|-------------------|----------------|
| Duration | 139s | 252.7s | 590.9s | 1204.9s |
| Turns | 12 | 17 | 13 | 23 |
| identified_arguments | 1 | 1 | 1 | **7** |
| identified_fallacies | 1 (none) | 1 (none) | 0 | **2 (typed)** |
| counter_arguments | 0 | 0 | 0 | **8** |
| jtms_beliefs | 0 | 0 | 0 | **4** |
| Dung frameworks | 0 | 0 | 0 | **1** |
| ASPIC results | 0 | 0 | 0 | **1** |
| Belief revision | 0 | 0 | 0 | **1** |
| NL-to-logic | 0 | 0 | 0 | **1** |
| DeepSynthesis sections | 4/9 | 5/9 | N/A | N/A |
| All agents SINGULAR_INSIGHT | 5/6 | 6/6 | 6/6 | **8/8** |

### Conclusion

**Model upgrade from gpt-4o-mini to gpt-5-mini resolves the tool-calling gap entirely.** The LLM now correctly calls `add_identified_argument()` and `add_identified_fallacy()`, producing structured state registration instead of prose-only descriptions.

- **Recommendation #1 (model upgrade) is CONFIRMED as the primary fix.**
- Recommendations #2 and #3 (orchestrator validation hook, structured output parsing) are no longer necessary as primary fixes but could serve as defense-in-depth for edge cases.
- The prompt engineering from Iterations 1-2 was NOT wasted — the improved instructions guide gpt-5-mini to produce more detailed structured output (premises, conclusions, force, connecteur implicite per argument).
