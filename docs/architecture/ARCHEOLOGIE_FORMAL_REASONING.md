# Archaeology of Formal Reasoning Patterns — Issue #283

> Date: 30 mars 2026 | Author: Claude Code | Epic #282

## Executive Summary

Analysis of 30+ commits on the formal reasoning pipeline reveals a **well-structured but partially disconnected** NL→Logic→Tweety→JTMS chain. The sequential pipeline (`_invoke_propositional`, `_invoke_fol`, `_invoke_jtms`) is properly wired since round 72-74, but the conversational mode had 8 attribute-name bugs that silently disabled JTMS retraction (fixed in `085b513b`).

---

## 1. Timeline of Formal Reasoning Infrastructure

| Date | Commit | Author | What Changed |
|------|--------|--------|-------------|
| 2025-09 | `b0ab2941` | jsboigeEpita | Initial TweetyLogicPlugin with PL/FOL/AF/ABA/ADF/DL/CL/SAT handlers |
| 2025-09 | `a1fb5676` | jsboigeEpita | Add SetAF, Weighted AF, Social AF handlers |
| 2025-09 | `f556fa72` | jsboigeEpita | Add EAF, DeLP, QBF handlers — 15+ handlers total |
| 2025-10 | `daeaf738` | jsboigeEpita | NLToLogicTranslator service (nl_to_logic.py) with Tweety validation |
| 2026-03-23 | `1c119834` | jsboigeEpita | Wire NL-to-logic into _invoke_propositional + _invoke_fol (3-tier fallback) |
| 2026-03-23 | `c64a7798` | jsboigeEpita | Implement real JTMS dependency network in _invoke_jtms |
| 2026-03-23 | `8b65a164` | jsboigeEpita | ConversationalOrchestrator with FormalAgent + TweetyLogicPlugin |
| 2026-03-24 | `ab9ce2c5` | jsboigeEpita | Cross-KB enrichment directives in agent instructions |
| 2026-03-27 | `5620e1eb` | jsboigeEpita | ConflictResolver integration + _resolve_phase_conflicts |
| 2026-03-28 | `96db7289` | jsboigeEpita | 5 orchestration weakness fixes (convergence, instructions) |
| 2026-03-29 | `ffb8d6bb` | jsboigeEpita | NLToLogicPlugin SK plugin + JTMS retraction methods in StateManagerPlugin |
| 2026-03-30 | `085b513b` | Claude Code | Fix 8 attribute-name bugs making JTMS retraction inoperant |

---

## 2. Current NL→Logic→Tweety→JTMS Flow

### Sequential Pipeline (unified_pipeline.py)

```
Input text
    │
    ├─► _invoke_nl_to_logic()     → NLToLogicTranslator → formulas
    ├─► _invoke_propositional()   → uses upstream translations OR on-the-fly NLToLogic
    │       └─► TweetyBridge.check_consistency()
    ├─► _invoke_fol_reasoning()   → same pattern with FOL
    │       └─► TweetyBridge.query()
    └─► _invoke_jtms()            → JTMSSession with ExtendedBelief
            ├─► Step 1: Add argument + claim beliefs
            ├─► Step 2: Arguments support claims (IN-list justifications)
            ├─► Step 3: Accept premises (set_fact)
            ├─► Step 4: Fallacies → retract undermined beliefs + propagate
            ├─► Step 5: Counter-arguments → competing OUT-list
            └─► Step 6: Quality scores → annotate metadata
```

**Status**: Fully wired since `1c119834` + `c64a7798`. Works with LLM. The 3-tier fallback in formal invocations ensures graceful degradation.

### Conversational Mode (conversational_orchestrator.py)

```
FormalAgent (ChatCompletionAgent)
    │
    ├── Plugins: TweetyLogicPlugin (20+ @kernel_function)
    │            NLToLogicPlugin (4 @kernel_function) — added ffb8d6bb
    │            StateManagerPlugin (15 @kernel_function including 5 JTMS methods)
    │
    ├── Instructions guide 3-step workflow:
    │   1. NL → translate_to_pl/fol
    │   2. Validate via check_propositional_consistency/check_fol_consistency
    │   3. Store via add_belief_set + log_query_result
    │
    └── JTMS integration:
        - jtms_create_belief for each formalized argument
        - jtms_add_justification for logical implications
        - jtms_check_consistency to detect issues
```

**Status**: Plugin wiring complete since `ffb8d6bb`. Agent instructions comprehensive. JTMS retraction fixed in `085b513b`. The agent can now:
- Translate NL → PL/FOL via NLToLogicPlugin
- Validate via TweetyLogicPlugin (if JVM available)
- Store results via StateManagerPlugin
- Create/query/retract JTMS beliefs

---

## 3. What Was Lost vs Intentionally Changed

### Lost (bugs, now fixed)
1. **JTMS retraction silently inoperant** — `ext_belief.is_valid` (wrong attribute), `ext_belief.metadata` (doesn't exist), `state.fallacies` (wrong field name) made `_retract_fallacious_beliefs()` and `_resolve_phase_conflicts()` do nothing. **Fixed in `085b513b`**.

2. **add_belief_set rejected FOL** — only accepted "propositional"/"pl", not "fol"/"first_order". **Fixed in `085b513b`**.

### Intentionally Changed
1. **analysis_runner_v2.py deprecated** — the original conversational runner was replaced by ConversationalOrchestrator (cleaner, purpose-built).
2. **GroupChatTurnStrategy not used** — ConversationalOrchestrator uses direct round-robin instead of SK's native GroupChat selection. This was a deliberate simplification for reliability.
3. **HierarchicalTurnStrategy dormant** — designed but never needed; the PM agent handles orchestration via instructions.

### Never Fully Connected
1. **CamemBERT Tier 2 in conversational mode** — `FrenchFallacyPlugin.detect_fallacies()` exists but neural detector is only in sequential pipeline's `neural_symbolic` workflow.
2. **Tweety validation in conversational mode** — FormalAgent has TweetyLogicPlugin but JVM must be started before agents run. No automatic JVM init in conversational entry point.
3. **JTMS-to-debate feedback loop** — DebateAgent's instructions mention quality scores but don't read JTMS retraction status directly. The PM should relay this.

---

## 4. Agent↔Plugin Associations (Current, Post-Fixes)

| Agent | Speciality Key | Plugins Loaded | JTMS Role |
|-------|---------------|----------------|-----------|
| ProjectManager | project_manager | StateManager | Reads state, coordinates |
| ExtractAgent | extract | StateManager | Creates arg beliefs + justifications |
| InformalAgent | informal_fallacy | FrenchFallacy + FallacyWorkflow + StateManager | Detects fallacies, retracts beliefs |
| FormalAgent | formal_logic | TweetyLogic + NLToLogic + StateManager | Translates NL→PL/FOL, validates, adds JTMS justifications |
| QualityAgent | quality | QualityScoring + StateManager | Evaluates with cross-KB context |
| DebateAgent | debate | Debate + StateManager | Adversarial challenge |
| CounterAgent | counter_argument | CounterArgument + StateManager | Targeted counter-arguments |
| GovernanceAgent | governance | Governance + StateManager | Voting, consensus metrics |

---

## 5. Gaps Still to Address (Recommendations for #285, #287)

### For #285 (Tweety wiring in conversational mode)
- **Critical gap**: The `standard` and `full` workflows do NOT include PL/FOL phases or `nl_to_logic` phase. Formal reasoning only exists in `formal_verification` and `nl_to_logic` specialized workflows. The NL→Logic→Tweety bridge is dormant for the default analysis path.
- **Gap**: The `full` workflow includes `nl_to_logic` but NOT PL/FOL — translations are made but never validated.
- **Gap**: `_invoke_propositional_logic` creates a new `NLToLogicTranslator` on each call — should be memoized.
- **Gap**: Pipeline retraction uses `set_belief_validity(target, False)` but conversational uses `None` — semantics should be unified.
- **Mostly done for conversational**: NLToLogicPlugin wired (`ffb8d6bb`), TweetyLogicPlugin already in factory, JVM init done by `run_orchestration.py`.

### For #287 (JTMS retraction)
- **Fixed**: Attribute-name bugs (`085b513b`). Retraction code should now work.
- **Gap**: No unit tests for `_retract_fallacious_beliefs()` or `jtms_retract_belief()`.
- **Gap**: JTMS session is stored on `state._jtms_session` (private attr). Not persisted across pipeline phases if state is serialized/deserialized.
- **Gap**: `_retract_fallacious_beliefs()` called after each phase, but only useful after phase 1 (when fallacies are detected). Phase 2 and 3 calls are no-ops.

### For #289 (Cross-KB synergies)
- **Done**: Agent instructions have detailed cross-KB guidance (`ab9ce2c5`).
- **Done**: ConflictResolver integrated (`5620e1eb`).
- **Gap**: ConflictResolver's `resolve_conflict()` expects mock agents dict — needs real agent integration.
- **Gap**: QualityAgent's `evaluate_with_cross_kb_context()` expects JSON context but agent must construct it from state snapshot.

---

## 6. Key Commit Map

```
Formal Logic Infrastructure:
  b0ab2941 → a1fb5676 → f556fa72    TweetyLogicPlugin (15+ handlers)
  daeaf738                            NLToLogicTranslator service
  ffb8d6bb                            NLToLogicPlugin SK wrapper

Pipeline Wiring:
  1c119834                            NL→Logic in _invoke_pl/_invoke_fol (3-tier fallback)
  c64a7798                            Real JTMS dependency network in _invoke_jtms

Conversational Wiring:
  8b65a164                            ConversationalOrchestrator (8 agents + plugins)
  ab9ce2c5                            Cross-KB enrichment directives
  5620e1eb                            ConflictResolver integration
  ffb8d6bb                            JTMS methods in StateManagerPlugin
  085b513b                            Fix 8 attribute bugs (retraction now works)
  5ca3cd41                            Fix fallacy key mismatch + 21 retraction tests
  10fe11a1                            Fix ExtendedBelief dual-Belief desync (#296)
  f71689dc                            Fix dead ConflictResolver API call (#289)
```

---

## 7. Cross-KB Wiring Archaeology (#284)

### 6 Cross-KB Data Flows (by design)

| Flow | Source | Target | Mechanism | Status |
|------|--------|--------|-----------|--------|
| 1 | Extract → JTMS | Beliefs for arguments | jtms_create_belief + jtms_add_justification | Prompt-guided |
| 2 | Informal → Quality | Fallacies reduce scores | evaluate_with_cross_kb_context() | Plugin exists, pipeline not wired |
| 3 | Informal → JTMS | Retract undermined beliefs | jtms_retract_belief + _retract_fallacious_beliefs | ✅ Working (f71689dc) |
| 4 | Quality → Counter | Target weak arguments | CounterAgent instructions | Prompt-guided |
| 5 | Formal → All | Signal inconsistencies | FormalAgent instructions | Prompt-guided |
| 6 | Debate → Governance | Vote on positions | detect_conflicts + social_choice_vote | Prompt-guided |

### Broken/Missing Wiring (found by archaeology)

1. **Pipeline quality ignores fallacies**: `_invoke_quality_evaluator()` reads only `phase_extract_output`, not `phase_hierarchical_fallacy_output`
2. **JTMS output not fed back**: No `depends_on=["jtms"]` in standard workflow for debate/governance
3. **JTMSCommunicationHub (54KB) unwired**: Has global consistency + inter-agent conflict detection but unused
4. **Collaborative debate unwired**: `collaborative_debate.py` (Critic/Validator/Synthesizer) not in workflow catalog

### ConflictResolver: Three Implementations

| Location | API | Status |
|----------|-----|--------|
| `agents/jtms_communication_hub.py` | async resolve_conflict(conflict, agents, strategy) | Original, unwired |
| `services/jtms/conflict_resolution.py` | sync resolve(conflict, strategy) | Canonical, used by orchestrator |
| `orchestration/hierarchical/tactical/resolver.py` | Hierarchical mode | Dormant |
