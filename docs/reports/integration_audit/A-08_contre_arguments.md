# Audit A-08: Generation de Contre-Arguments

**Issue**: N/A | **SUIVI**: Score 95% | **Date audit**: 2026-05-31

## Status: 🟢 Integrated

## What was delivered (student source)

Student project `2.3.3-generation-contre-argument` delivered a counter-argument generation system with 5 rhetorical strategies, a 5-criteria weighted evaluator, and a `CounterArgumentValidator` using TweetyBridge for formal logic validation. Adapted from `counter_agent/`.

## What exists in `argumentation_analysis/`

| File | Description |
|------|-------------|
| `agents/core/counter_argument/counter_agent.py` | `CounterArgumentAgent(BaseAgent)` + `CounterArgumentPlugin` with 3 `@kernel_function` methods |
| `agents/core/counter_argument/definitions.py` | 5 `RhetoricalStrategy` enum values, `Argument`, `CounterArgument`, `CounterArgumentType`, `ArgumentStrength`, `EvaluationResult`, `ValidationResult` dataclasses |
| `agents/core/counter_argument/evaluator.py` | `CounterArgumentEvaluator` with 5 weighted criteria: relevance (0.25), logical_strength (0.25), persuasiveness (0.20), originality (0.15), clarity (0.15) |
| `agents/core/counter_argument/strategies.py` | `RhetoricalStrategies` manager with 5 `_apply_*` implementations |

### Actual Rhetorical Strategies (enum values in code)

| Strategy | Enum Value |
|----------|------------|
| Socratic Questioning | `SOCRATIC_QUESTIONING` |
| Reductio ad Absurdum | `REDUCTIO_AD_ABSURDUM` |
| Analogical Counter | `ANALOGICAL_COUNTER` |
| Authority Appeal | `AUTHORITY_APPEAL` |
| Statistical Evidence | `STATISTICAL_EVIDENCE` |

**Note**: SUIVI and `CLAUDE.md` incorrectly list the strategies as "distinction, reformulation, concession". These names do not appear anywhere in the code. The actual strategies are socratic, reductio, analogical, authority, and statistical.

## Preservation Assessment

- **5 rhetorical strategies** fully preserved with template-based generation fallbacks (LLM-dependent generation replaced with deterministic templates).
- **5-criteria weighted evaluator** fully preserved with French-language NLP heuristics (no LLM required for scoring).
- **CounterArgumentAgent** correctly inherits from `BaseAgent(ChatCompletionAgent)` for `AgentGroupChat` compatibility.
- **Plugin integration** complete with 3 `@kernel_function` methods.
- **ValidationResult dataclass** exists in definitions but is not wired to any validator.

## Gap Analysis

1. **Tweety formal validation NOT wired.** The student's `TweetyBridge` + `CounterArgumentValidator` (which formally verified counter-argument logical validity) was not ported. The `ValidationResult` dataclass exists but is an orphan export -- no code populates it.
2. **Strategy name mismatch in documentation.** SUIVI and `CLAUDE.md` claim strategies are "distinction, reformulation, concession" but the actual enum values are `SOCRATIC_QUESTIONING`, `REDUCTIO_AD_ABSURDUM`, `ANALOGICAL_COUNTER`, `AUTHORITY_APPEAL`, `STATISTICAL_EVIDENCE`. This is a documentation error, not a code issue.
3. **LLM-dependent generation replaced with templates.** The student's original used LLM calls for strategy application. The integrated version provides template-based fallbacks, which is a reasonable adaptation for offline/no-API scenarios but may produce less nuanced counters.

## Recommended Action

1. Fix `CLAUDE.md` to list the correct strategy names: socratic questioning, reductio ad absurdum, analogical counter, authority appeal, statistical evidence.
2. If formal logic validation is desired, wire `ValidationResult` to `TweetyBridge` (requires JVM). Otherwise, remove the orphan dataclass to avoid confusion.

## Source Files

- `argumentation_analysis/agents/core/counter_argument/counter_agent.py`
- `argumentation_analysis/agents/core/counter_argument/definitions.py`
- `argumentation_analysis/agents/core/counter_argument/evaluator.py`
- `argumentation_analysis/agents/core/counter_argument/strategies.py`
