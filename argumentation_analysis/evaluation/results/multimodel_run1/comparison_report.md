# Multi-Model Benchmark Report

**Generated**: 2026-03-19T03:21:30.323095
**Models**: default, openrouter
**Workflows**: light, standard, quality_gated, debate_tournament, belief_dynamics
**Documents**: 2
**Total cells**: 20
**Total duration**: 835.3s

## Results Matrix

| Model | Workflow | Success Rate | Avg Duration | Completion |
|-------|---------|:---:|:---:|:---:|
| default | belief_dynamics | 100% (2/2) | 42.4s | 80% |
| default | debate_tournament | 100% (2/2) | 70.0s | 100% |
| default | light | 100% (2/2) | 50.0s | 100% |
| default | quality_gated | 100% (2/2) | 17.8s | 100% |
| default | standard | 100% (2/2) | 94.2s | 100% |
| openrouter | belief_dynamics | 100% (2/2) | 20.4s | 80% |
| openrouter | debate_tournament | 100% (2/2) | 42.9s | 100% |
| openrouter | light | 100% (2/2) | 20.5s | 100% |
| openrouter | quality_gated | 100% (2/2) | 9.6s | 100% |
| openrouter | standard | 100% (2/2) | 46.0s | 100% |

## Best Combinations

- **best_by_success**: default + light (success_rate: 1.0)
- **best_by_speed**: openrouter + quality_gated (avg_duration: 9.59)
- **best_overall**: openrouter + quality_gated (composite_score: 0.819)

## Model Rankings (per workflow)

### light
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 20.4s | 100% |
| 2 | default | 100% | 50.0s | 100% |

### standard
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 46.0s | 100% |
| 2 | default | 100% | 94.2s | 100% |

### quality_gated
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 9.6s | 100% |
| 2 | default | 100% | 17.8s | 100% |

### debate_tournament
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 42.9s | 100% |
| 2 | default | 100% | 70.0s | 100% |

### belief_dynamics
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 20.4s | 80% |
| 2 | default | 100% | 42.4s | 80% |

## Workflow Rankings (per model)

### default
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | quality_gated | 100% | 17.8s | 100% |
| 2 | light | 100% | 50.0s | 100% |
| 3 | debate_tournament | 100% | 70.0s | 100% |
| 4 | standard | 100% | 94.2s | 100% |
| 5 | belief_dynamics | 100% | 42.4s | 80% |

### openrouter
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | quality_gated | 100% | 9.6s | 100% |
| 2 | light | 100% | 20.4s | 100% |
| 3 | debate_tournament | 100% | 42.9s | 100% |
| 4 | standard | 100% | 46.0s | 100% |
| 5 | belief_dynamics | 100% | 20.4s | 80% |
