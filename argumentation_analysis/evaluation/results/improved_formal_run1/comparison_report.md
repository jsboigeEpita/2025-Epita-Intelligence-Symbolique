# Multi-Model Benchmark Report

**Generated**: 2026-03-19T11:43:12.037637
**Models**: default, openrouter
**Workflows**: formal_debate, argument_strength, belief_dynamics, debate_tournament, standard
**Documents**: 2
**Total cells**: 20
**Total duration**: 619.2s

## Results Matrix

| Model | Workflow | Success Rate | Avg Duration | Completion |
|-------|---------|:---:|:---:|:---:|
| default | argument_strength | 100% (2/2) | 15.4s | 100% |
| default | belief_dynamics | 100% (2/2) | 27.1s | 100% |
| default | debate_tournament | 100% (2/2) | 53.4s | 100% |
| default | formal_debate | 100% (2/2) | 15.2s | 100% |
| default | standard | 100% (2/2) | 63.9s | 100% |
| openrouter | argument_strength | 100% (2/2) | 10.3s | 100% |
| openrouter | belief_dynamics | 100% (2/2) | 22.4s | 100% |
| openrouter | debate_tournament | 100% (2/2) | 42.6s | 100% |
| openrouter | formal_debate | 100% (2/2) | 9.8s | 100% |
| openrouter | standard | 100% (2/2) | 43.8s | 100% |

## Best Combinations

- **best_by_success**: default + formal_debate (success_rate: 1.0)
- **best_by_speed**: openrouter + formal_debate (avg_duration: 9.82)
- **best_overall**: openrouter + formal_debate (composite_score: 0.818)

## Model Rankings (per workflow)

### formal_debate
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 9.8s | 100% |
| 2 | default | 100% | 15.2s | 100% |

### argument_strength
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 10.3s | 100% |
| 2 | default | 100% | 15.4s | 100% |

### belief_dynamics
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 22.4s | 100% |
| 2 | default | 100% | 27.1s | 100% |

### debate_tournament
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 42.6s | 100% |
| 2 | default | 100% | 53.4s | 100% |

### standard
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | openrouter | 100% | 43.8s | 100% |
| 2 | default | 100% | 63.9s | 100% |

## Workflow Rankings (per model)

### default
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | formal_debate | 100% | 15.2s | 100% |
| 2 | argument_strength | 100% | 15.4s | 100% |
| 3 | belief_dynamics | 100% | 27.1s | 100% |
| 4 | debate_tournament | 100% | 53.4s | 100% |
| 5 | standard | 100% | 63.9s | 100% |

### openrouter
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | formal_debate | 100% | 9.8s | 100% |
| 2 | argument_strength | 100% | 10.3s | 100% |
| 3 | belief_dynamics | 100% | 22.4s | 100% |
| 4 | debate_tournament | 100% | 42.6s | 100% |
| 5 | standard | 100% | 43.8s | 100% |
