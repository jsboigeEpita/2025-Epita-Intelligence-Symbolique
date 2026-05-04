# Coverage Audit — Baseline Measurement

**Date**: 2026-05-03
**Issue**: #402 (A.5 Coverage audit + targeted tests)
**Environment**: Windows 11, Python 3.10, conda `projet-is-roo-new`
**Command**: `pytest --cov=argumentation_analysis --cov-report=term-missing`

## Executive Summary

Overall package coverage is moderate. Core orchestration modules (post-#401 mypy strict) have
high coverage (95%+ for capability_registry). Student project integrations vary widely.
The JTMS conflict_resolution module is critically undertested (19%).

## Modules Below 80% Coverage

### Services (argumentation_analysis/services/)

| Module | Stmts | Miss | Cover | Priority |
|--------|-------|------|-------|----------|
| `jtms/conflict_resolution.py` | 90 | 73 | **19%** | CRITICAL |
| `jtms/jtms_core.py` | 165 | 32 | **81%** | LOW |
| `jtms/extended_belief.py` | 99 | 16 | **84%** | LOW |
| `jtms/atms_core.py` | 92 | 14 | **85%** | LOW |

### Agents (argumentation_analysis/agents/core/)

| Module | Stmts | Miss | Cover | Priority |
|--------|-------|------|-------|----------|
| `quality/quality_evaluator.py` | 151 | 61 | **60%** | HIGH |
| `governance/governance_agent.py` | 153 | 44 | **71%** | MEDIUM |
| `governance/simulation.py` | 135 | 36 | **73%** | MEDIUM |

### Modules Above 80% (no action needed)

| Module | Cover |
|--------|-------|
| `governance/governance_methods.py` | 100% |
| `governance/metrics.py` | 100% |
| `governance/social_choice.py` | 94% |
| `debate/protocols.py` | 98% |
| `debate/debate_scoring.py` | 97% |
| `debate/debate_definitions.py` | 100% |
| `debate/knowledge_base.py` | 100% |
| `counter_argument/strategies.py` | 100% |
| `counter_argument/parser.py` | 93% |
| `core/capability_registry.py` | 95% |

## Targeted Test Plan

### 1. jtms/conflict_resolution.py (19% → target 80%+)
- Test `detect_conflicts()` with overlapping positions
- Test `resolve_conflict()` with each strategy (collaborative, competitive, compromise)
- Test edge cases: single agent, no conflicts, all conflicts

### 2. quality/quality_evaluator.py (60% → target 80%+)
- Test individual virtue detectors (clarity, coherence, relevance)
- Test `_evaluate_virtue()` scoring paths
- Test edge cases: empty arguments, very long arguments, unicode

### 3. governance/governance_agent.py (71% → target 85%+)
- Test BDI agent belief/desire/intention lifecycle
- Test ReactiveAgent rule-based decisions
- Test Q-learning updates
- Test negotiation flow

### 4. governance/simulation.py (73% → target 85%+)
- Test `shapley_value()` computation
- Test `manipulability_analysis()` scenarios
- Test `distributed_gossip_consensus()` with adjacency matrix

## Notes

- 29 pre-existing test failures (torch DLL `WinError 182`, service_manager import errors)
- These are unrelated to coverage improvements and tracked separately
- Coverage measured without JVM-dependent tests (--disable-jvm-session flag)
