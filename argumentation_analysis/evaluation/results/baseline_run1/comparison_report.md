# Multi-Model Benchmark Report

**Generated**: 2026-03-19T03:01:22.793682
**Models**: default
**Workflows**: light, standard, quality_gated
**Documents**: 3
**Total cells**: 9
**Total duration**: 428.9s

## Results Matrix

| Model | Workflow | Success Rate | Avg Duration | Completion |
|-------|---------|:---:|:---:|:---:|
| default | light | 100% (3/3) | 41.9s | 100% |
| default | quality_gated | 100% (3/3) | 15.4s | 100% |
| default | standard | 100% (3/3) | 82.9s | 100% |

## Best Combinations

- **best_by_success**: default + light (success_rate: 1.0)
- **best_by_speed**: default + quality_gated (avg_duration: 15.45)
- **best_overall**: default + quality_gated (composite_score: 0.812)

## Model Rankings (per workflow)

### light
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | default | 100% | 41.9s | 100% |

### standard
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | default | 100% | 82.9s | 100% |

### quality_gated
| Rank | Model | Success | Duration | Completion |
|:---:|-------|:---:|:---:|:---:|
| 1 | default | 100% | 15.4s | 100% |

## Workflow Rankings (per model)

### default
| Rank | Workflow | Success | Duration | Completion |
|:---:|---------|:---:|:---:|:---:|
| 1 | quality_gated | 100% | 15.4s | 100% |
| 2 | light | 100% | 41.9s | 100% |
| 3 | standard | 100% | 82.9s | 100% |
