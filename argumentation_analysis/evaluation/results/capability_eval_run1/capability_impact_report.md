# Capability Impact Evaluation Report

**Generated**: 2026-03-20T16:03:06.643776
**Subsets tested**: 8
**Documents**: 5
**Total cells**: 40

## Results by Capability Subset

| Subset | Capabilities | Avg Completion | Avg Duration | Avg State Richness |
|--------|:---:|:---:|:---:|:---:|
| all_available | 11 | 100% | 52.0s | 17 |
| core_full | 5 | 100% | 49.4s | 11 |
| core_plus_belief | 6 | 100% | 53.9s | 12 |
| core_plus_formal | 8 | 100% | 48.8s | 14 |
| core_plus_ranking | 6 | 100% | 58.0s | 12 |
| core_trio | 3 | 100% | 42.6s | 4 |
| minimal | 1 | 100% | 0.1s | 2 |
| quality_counter | 2 | 100% | 18.8s | 3 |

## Marginal Value Analysis

Compares each subset against its predecessor to measure marginal impact:

| From → To | +Capabilities | Completion Δ | Duration Δ | Richness Δ |
|-----------|:---:|:---:|:---:|:---:|
| minimal → quality_counter | counter_argument_generation | +0pp | +18.7s | +1 |
| quality_counter → core_trio | adversarial_debate | +0pp | +23.8s | +1 |
| core_trio → core_full | belief_maintenance, governance_simulatio | +0pp | +6.8s | +7 |
| core_full → core_plus_ranking | ranking_semantics | +0pp | +8.6s | +1 |
| core_plus_ranking → core_plus_formal | aspic_plus_reasoning, dialogue_protocols | +0pp | -9.1s | +2 |
| core_plus_formal → all_available | belief_revision, bipolar_argumentation,  | +0pp | +3.2s | +3 |

## Interpretation

- **State richness** measures how much data the pipeline produces (argument counts, fallacy counts, quality scores, etc.)
- **Completion rate** should be ~100% for all subsets (fallbacks ensure this)
- **Duration delta** shows the cost of each additional capability
- **Richness delta** shows the data gain — high delta = high-value capability