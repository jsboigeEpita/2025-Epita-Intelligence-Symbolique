# Multi-Model Benchmark Report

**Generated**: 2026-03-20T06:10:30.452009
**Models**: default, openrouter
**Workflows**: formal_debate, argument_strength, belief_dynamics, quality_gated, standard, comprehensive
**Documents**: 10
**Total cells**: 120
**Total duration**: 4207.7s

## Results Matrix

| Model | Workflow | Success Rate | Avg Duration | Completion |
|-------|---------|:---:|:---:|:---:|
| default | argument_strength | 100% (10/10) | 11.8s | 100% |
| default | belief_dynamics | 100% (10/10) | 24.8s | 100% |
| default | comprehensive | 100% (10/10) | 108.9s | 100% |
| default | formal_debate | 100% (10/10) | 15.1s | 100% |
| default | quality_gated | 100% (10/10) | 12.6s | 100% |
| default | standard | 100% (10/10) | 58.3s | 100% |
| openrouter | argument_strength | 100% (10/10) | 10.9s | 100% |
| openrouter | belief_dynamics | 100% (10/10) | 22.4s | 100% |
| openrouter | comprehensive | 100% (10/10) | 88.3s | 100% |
| openrouter | formal_debate | 100% (10/10) | 11.2s | 100% |
| openrouter | quality_gated | 100% (10/10) | 10.5s | 100% |
| openrouter | standard | 100% (10/10) | 45.1s | 100% |

## Best Combinations

- **best_by_success**: default + formal_debate (success_rate: 1.0)
- **best_by_speed**: openrouter + quality_gated (avg_duration: 10.5)
- **best_overall**: openrouter + quality_gated (composite_score: 0.817)

## Model Rankings (per workflow)

### formal_debate
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 11.2s | 100% |
| 2 | default | 100% | 15.2s | 100% |

### argument_strength
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 10.9s | 100% |
| 2 | default | 100% | 11.8s | 100% |

### belief_dynamics
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 22.4s | 100% |
| 2 | default | 100% | 24.8s | 100% |

### quality_gated
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 10.5s | 100% |
| 2 | default | 100% | 12.6s | 100% |

### standard
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 45.1s | 100% |
| 2 | default | 100% | 58.3s | 100% |

### comprehensive
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 88.3s | 100% |
| 2 | default | 100% | 108.9s | 100% |

## Workflow Rankings (per model)

### default
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | argument_strength | 100% | 11.8s | 100% |
| 2 | quality_gated | 100% | 12.6s | 100% |
| 3 | formal_debate | 100% | 15.2s | 100% |
| 4 | belief_dynamics | 100% | 24.8s | 100% |
| 5 | standard | 100% | 58.3s | 100% |
| 6 | comprehensive | 100% | 108.9s | 100% |

### openrouter
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | quality_gated | 100% | 10.5s | 100% |
| 2 | argument_strength | 100% | 10.9s | 100% |
| 3 | formal_debate | 100% | 11.2s | 100% |
| 4 | belief_dynamics | 100% | 22.4s | 100% |
| 5 | standard | 100% | 45.1s | 100% |
| 6 | comprehensive | 100% | 88.3s | 100% |
