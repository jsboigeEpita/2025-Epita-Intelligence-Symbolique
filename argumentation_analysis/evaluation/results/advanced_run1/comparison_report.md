# Multi-Model Benchmark Report

**Generated**: 2026-03-19T03:07:17.701489
**Models**: default
**Workflows**: formal_debate, belief_dynamics, argument_strength, debate_tournament
**Documents**: 2
**Total cells**: 8
**Total duration**: 338.4s

## Results Matrix

| Model | Workflow | Success Rate | Avg Duration | Completion |
|-------|---------|:---:|:---:|:---:|
| default | argument_strength | 100% (2/2) | 15.1s | 33% |
| default | belief_dynamics | 100% (2/2) | 42.0s | 80% |
| default | debate_tournament | 100% (2/2) | 83.4s | 100% |
| default | formal_debate | 100% (2/2) | 24.7s | 25% |

## Best Combinations

- **best_by_success**: default + formal_debate (success_rate: 1.0)
- **best_by_speed**: default + argument_strength (avg_duration: 15.12)
- **best_overall**: default + debate_tournament (composite_score: 0.802)

## Model Rankings (per workflow)

### formal_debate
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | default | 100% | 24.7s | 25% |

### belief_dynamics
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | default | 100% | 42.0s | 80% |

### argument_strength
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | default | 100% | 15.1s | 33% |

### debate_tournament
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | default | 100% | 83.4s | 100% |

## Workflow Rankings (per model)

### default
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | debate_tournament | 100% | 83.4s | 100% |
| 2 | belief_dynamics | 100% | 42.0s | 80% |
| 3 | argument_strength | 100% | 15.1s | 33% |
| 4 | formal_debate | 100% | 24.7s | 25% |
