# Pattern: 2-Pass Coordinated Pipeline with Shared State

## Problem

When multiple logic agents (PL, FOL) translate arguments independently, each generates its own vocabulary of symbols. This produces:
- **Inconsistent symbols**: `P1` in one agent vs `argument_1` in another for the same proposition
- **Cross-argument incoherence**: Agent A's `P1` and Agent B's `P2` refer to the same concept but can't be reasoned about together
- **Tweety incompatibility**: Ad-hoc proposition names fail Tweety's grammar (`^[a-zA-Z_][a-zA-Z0-9_]*$`)

The 0-shot baseline (#549) demonstrated that a single LLM call produces 8-13 FOL formulas, while the multi-agent pipeline produced 0 — because each agent re-discovered vocabulary independently and agents couldn't agree on a shared symbol space.

## Solution: 2-Pass Pipeline

The **2-pass coordinated pipeline** establishes a shared symbol vocabulary in Pass 1, then enforces exclusive use of that vocabulary in Pass 2.

### Invariant

```
Pass 1: Full text → shared symbol inventory (stored in state)
Pass 2: Per-argument → formulas using ONLY shared symbols
```

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                  UnifiedAnalysisState                    │
│  atomic_propositions: Dict[str, List[str]]   (PL atoms) │
│  fol_shared_signature: Dict[str, Dict]       (FOL sig)  │
└───────────────┬─────────────────────┬───────────────────┘
                │                     │
    Pass 1 stores PL atoms here       Pass 1 stores FOL signature here
    (invoke_callables:3224)           (invoke_callables:3465)
                │                     │
                ▼                     ▼
    _invoke_propositional_logic       _invoke_fol_reasoning
    (invoke_callables:3137-3357)      (invoke_callables:3366-3600)
                │                     │
    Pass 2 reads atoms from state     Pass 2 reads signature from state
    Embeds in per-arg prompt:         Embeds in per-arg prompt:
    "Use ONLY these propositions"     "Use ONLY these predicates"
                │                     │
                ▼                     ▼
    PL formulas with shared atoms     FOL formulas with shared signature
                │                     │
                ▼                     ▼
    PLFormulaSanitizer (normalize)    TweetyBridge.check_consistency
    (pl_formula_sanitizer.py)         (agents/core/logic/)
```

## PL 2-Pass (PR #550)

**File**: `invoke_callables.py:_invoke_propositional_logic` (lines 3137-3357)

### Pass 1 — Atom Inventory

1. Full source text (truncated to 4000 chars) sent to LLM
2. Prompt asks: "Identify all atomic propositions as simple variable names"
3. LLM returns JSON: `{"propositions": ["p", "q", "r", ...]}`
4. Each atom validated against Tweety grammar: `^[a-zA-Z_][a-zA-Z0-9_]*$`
5. Stored in state: `state.atomic_propositions[source_id] = validated_atoms`

### Pass 2 — Per-Argument Formulas

1. For each of the first 6 identified arguments:
2. Prompt embeds shared atoms as JSON constraint
3. Explicit instruction: "Use ONLY the propositions from the list below. Do NOT invent new ones."
4. LLM generates PL formulas using exclusively shared atoms
5. Results collected and passed through `PLFormulaSanitizer` for Tweety normalization

### Fallback Chain

1. If `phase_nl_to_logic_output` already has validated PL translations → use directly (backward compat)
2. If 2-pass produces formulas → use them
3. If 2-pass fails → `NLToLogicTranslator` then template variables (`p1`, `p2`, ...)

## FOL 2-Pass (PR #554)

**File**: `invoke_callables.py:_invoke_fol_reasoning` (lines 3366-3600)

### Pass 1 — Shared Signature Extraction

1. Full source text (4000 chars) sent to LLM
2. Prompt asks for a FOL signature as JSON with three keys:
   - `sorts`: e.g., `{"Person": ["socrates", "plato"], "Concept": ["mortality"]}`
   - `predicates`: e.g., `{"Mortal/1": "x is mortal", "Teacher/2": "x teaches y"}`
   - `constants`: e.g., `{"socrates": "Person"}`
3. Fallback: if only constants found, auto-generates `Thing` sort
4. Stored in state: `state.fol_shared_signature[source_id] = {sorts, predicates, constants_raw}`

### Pass 2 — Per-Argument FOL Formulas

1. For each of the first 6 arguments:
2. Prompt embeds full signature as JSON
3. Explicit instruction: "Use ONLY the predicates and constants from the signature"
4. LLM generates FOL formulas (e.g., `∀x:Person(Mortal(x) → ∃y:Concept(Knows(x,y)))`)
5. Results checked via `TweetyBridge.check_consistency` with pre-declared sorts

### Fallback Chain

1. 2-pass formulas → Tweety consistency check
2. If 2-pass fails → `NLToLogicTranslator` (FOL mode)
3. If translator fails → template predicates (`Asserted(arg1)`, `Undermines(fallacy1, arg2)`)

## FormalAgent Wiring (PR #556)

**File**: `conversational_orchestrator.py:AGENT_CONFIG["FormalAgent"]["instructions"]` (lines 162-213)

FormalAgent is the conversational-mode agent that performs formal reasoning. It now includes:

### ETAPE 0 — Consult Shared State

```
1. Read state via get_current_state_snapshot()
2. If atomic_propositions present → use as base for PL translation
3. If fol_shared_signature present → use sorts/predicates/constants for FOL
4. Shared atoms/signatures guarantee inter-argument coherence
```

### ETAPE 1 — Translation (FOL by Default)

```
1. For each key argument, start with translate_to_fol()
   — FOL is default because it captures relations, quantifiers, predicates
2. If FOL fails or argument is purely propositional → translate_to_pl() as fallback
```

This wiring ensures the conversational FormalAgent respects the same shared vocabulary that the pipeline 2-pass established.

## State Fields

| Field | Type | Line (shared_state.py) | Purpose |
|-------|------|----------------------|---------|
| `atomic_propositions` | `Dict[str, List[str]]` | 427 | PL shared atoms per source |
| `fol_shared_signature` | `Dict[str, Dict[str, Any]]` | 429 | FOL shared signature per source |

Both fields are exposed in `get_state_snapshot()`:
- **Summarized** (line 967-972): counts and source keys only
- **Full** (line 998-999): complete data structures

## Test Coverage

| Test File | Lines | Tests | Covers |
|-----------|-------|-------|--------|
| `test_pl_2pass_pipeline.py` | 295 | 16 | PL Pass 1, Pass 2, fallback, backward compat |
| `test_fol_2pass_pipeline.py` | 272 | 12 | FOL Pass 1, Pass 2, signature extraction, fallback |
| `test_formalagent_shared_state.py` | 146 | 10 | ETAPE 0, snapshot fields, end-to-end |
| `test_formalagent_fol_default.py` | 98 | 9 | FOL-by-default, no quantifier gating, fallback |

**Total**: 47 tests, all GREEN.

## Impact (SCDA Audit Post-Sprint 3)

| Metric | Sprint 1 (before) | Sprint 3 (after) | Target |
|--------|-------------------|-------------------|--------|
| ParserExceptions | 159 | **0** | <20 |
| `arguments_found` | 0/0/0 (bug) | 5/9/2 | Correct |
| FOL formulas | 0 | SINGULAR_INSIGHT ×3 | ≥5/corpus |
| Cross-argument coherence | None | Shared signature | Yes |

ParserExceptions dropped from 159 to 0 (EXCEED target). The shared vocabulary eliminates symbol conflicts that caused Tweety parsing failures.

## When to Use This Pattern

- **Multi-agent formal analysis**: Any system where multiple agents need to reason about the same symbols
- **Logic translation pipelines**: PL or FOL generation that must be consistent across arguments
- **Tweety integration**: The shared vocabulary ensures all formulas parse correctly in Tweety

## Anti-patterns to Avoid

1. **Per-argument independent translation**: Each agent inventing its own symbols → inconsistency
2. **No validation**: LLM-generated symbols must be validated against Tweety grammar before use
3. **Gating FOL on explicit quantifiers**: The 0-shot baseline showed this produces 0 formulas. FOL should be attempted by default.
4. **Ignoring shared state in conversational mode**: The FormalAgent must read ETAPE 0 before translating, or it re-discovers vocabulary independently.
