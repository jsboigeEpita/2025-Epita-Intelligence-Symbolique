# Multi-Model Benchmark Report

**Generated**: 2026-03-19T03:37:36.381941
**Models**: default, openrouter
**Workflows**: comprehensive, debate_tournament, standard
**Documents**: 2
**Total cells**: 12
**Total duration**: 798.7s

## Results Matrix

| Model | Workflow | Success Rate | Avg Duration | Completion |
|-------|---------|:---:|:---:|:---:|
| default | comprehensive | 100% (2/2) | 100.9s | 100% |
| default | debate_tournament | 100% (2/2) | 62.0s | 100% |
| default | standard | 100% (2/2) | 60.4s | 100% |
| openrouter | comprehensive | 100% (2/2) | 81.9s | 100% |
| openrouter | debate_tournament | 100% (2/2) | 44.3s | 100% |
| openrouter | standard | 100% (2/2) | 45.9s | 100% |

## Best Combinations

- **best_by_success**: default + comprehensive (success_rate: 1.0)
- **best_by_speed**: openrouter + debate_tournament (avg_duration: 44.31)
- **best_overall**: openrouter + debate_tournament (composite_score: 0.804)

## Model Rankings (per workflow)

### comprehensive
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 81.9s | 100% |
| 2 | default | 100% | 100.9s | 100% |

### debate_tournament
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 44.3s | 100% |
| 2 | default | 100% | 62.0s | 100% |

### standard
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 45.9s | 100% |
| 2 | default | 100% | 60.4s | 100% |

## Workflow Rankings (per model)

### default
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | standard | 100% | 60.4s | 100% |
| 2 | debate_tournament | 100% | 62.0s | 100% |
| 3 | comprehensive | 100% | 100.9s | 100% |

### openrouter
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | debate_tournament | 100% | 44.3s | 100% |
| 2 | standard | 100% | 45.9s | 100% |
| 3 | comprehensive | 100% | 81.9s | 100% |
