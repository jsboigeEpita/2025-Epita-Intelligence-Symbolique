# Audit A-06: Gouvernance Multi-Agents

**Issue**: N/A | **SUIVI**: Score 85% | **Date audit**: 2026-05-31

## Status: 🟢 Integrated

## What was delivered (student source)

Student project `2.1.6_multiagent_governance_prototype` delivered a multi-agent governance simulation with 7 voting methods, conflict resolution, consensus metrics, coalition analysis (Shapley value), and manipulability detection. The system models agent personalities (BDI, Q-learning, reactive) and simulates governance decisions.

## What exists in `argumentation_analysis/`

| File | Description |
|------|-------------|
| `agents/core/governance/governance_methods.py` | 7 voting functions: `majority_voting`, `plurality_voting`, `borda_count`, `condorcet_method`, `quadratic_voting`, `byzantine_consensus`, `raft_consensus` |
| `agents/core/governance/conflict_resolution.py` | `detect_conflicts()`, `resolve_conflict()` with 3 strategies: collaborative, competitive, compromise mediation |
| `agents/core/governance/simulation.py` | `simulate_governance()`, `shapley_value()`, `distributed_gossip_consensus()`, `simulate_manipulation()`, `manipulability_analysis()` |
| `agents/core/governance/metrics.py` | 8 metric functions: `consensus_rate`, `gini`, `fairness_index`, `efficiency`, `satisfaction`, `stability`, `per_agent_satisfaction`, `summarize_results`, `validate_scenario` |
| `agents/core/governance/governance_agent.py` | `Agent`, `BDIAgent`, `ReactiveAgent`, `AgentFactory` -- agent personality models with Q-learning, BDI, and reactive strategies |
| `agents/core/governance/social_choice.py` | 5 bonus social-choice methods: `approval_voting`, `stv`, `copeland`, `kemeny_young`, `schulze`, plus `condorcet_winner`, `pairwise_matrix` helpers |
| `plugins/governance_plugin.py` | `GovernancePlugin` with 6 `@kernel_function` methods (not 4 as documented) |
| `orchestration/registry_setup.py` | :149-168 `governance_agent` registered with capabilities |

### GovernancePlugin `@kernel_function` Methods

| Method | Description |
|--------|-------------|
| `detect_conflicts_fn` | Detect conflicts between agent positions |
| `resolve_conflict_fn` | Resolve a conflict with strategy selection |
| `compute_consensus_metrics` | Calculate consensus/fairness metrics |
| `list_governance_methods` | List available governance methods |
| `social_choice_vote` | Execute a social-choice voting method |
| `find_condorcet_winner` | Find Condorcet winner from pairwise preferences |

## Preservation Assessment

- **All 7 core voting methods** preserved 1:1 (majority, plurality, Borda, Condorcet, quadratic, Byzantine, Raft).
- **5 bonus social-choice methods** added beyond student scope (approval, STV, Copeland, Kemeny-Young, Schulze).
- **Conflict resolution** fully preserved with 3 mediation strategies.
- **Consensus metrics** fully preserved (8 functions including Gini, fairness, efficiency).
- **Coalition analysis** preserved: Shapley value computation + distributed gossip consensus.
- **Manipulability analysis** preserved: `simulate_manipulation()` + `manipulability_analysis()`.
- **Agent personality models** preserved: BDI, Q-learning, reactive agents with `AgentFactory`.
- **Plugin integration** with 6 `@kernel_function` methods (SUIVI and `CLAUDE.md` incorrectly state 4).

## Gap Analysis

1. **Documentation mismatch**: `CLAUDE.md` states "4 `@kernel_function` methods" but `governance_plugin.py` has 6. The 2 additional methods (`social_choice_vote`, `find_condorcet_winner`) were added to expose the bonus social-choice methods via SK.
2. **Not a BaseAgent**: `GovernanceAgent` classes in `governance_agent.py` do not inherit from `BaseAgent` -- they are standalone agent models. Logic is exposed via the `GovernancePlugin` instead. This is an architectural choice, not a gap.

## Recommended Action

Update `CLAUDE.md` to state "6 `@kernel_function` methods" for the governance plugin. The integration is comprehensive -- all student features are preserved with bonus social-choice methods added.

## Source Files

- `argumentation_analysis/agents/core/governance/governance_methods.py`
- `argumentation_analysis/agents/core/governance/conflict_resolution.py`
- `argumentation_analysis/agents/core/governance/simulation.py`
- `argumentation_analysis/agents/core/governance/metrics.py`
- `argumentation_analysis/agents/core/governance/governance_agent.py`
- `argumentation_analysis/agents/core/governance/social_choice.py`
- `argumentation_analysis/plugins/governance_plugin.py`
- `argumentation_analysis/orchestration/registry_setup.py`
