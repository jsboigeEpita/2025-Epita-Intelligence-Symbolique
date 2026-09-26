# `agents/core/governance/` — agrégation de préférences et simulations de gouvernance

## Rôle et frontière

6 modules (970 l. avec `__init__` ; 7 modules / 1 266 l. avant le retrait de `simulation.py`, #2137) — le paquet qui **agrège des préférences** et **simule des collectifs** : scrutins d'agrégation, protocoles de consensus distribué, fonctions de choix social classiques, archétypes d'agents électeurs, détection/médiation de conflits, métriques de consensus. C'est la couche « décider ensemble » ; elle ne produit pas d'analyse du texte, elle consomme des **scores d'arguments** (les 9 vertus qualité) comme électeurs et rend un verdict de vote.

Le paquet vient du projet étudiant `2.1.6_multiagent_governance_prototype` (GitHub #43), intégré sous architecture BaseAgent/SK (#35) : il est **exposé via un plugin** (`argumentation_analysis/plugins/governance_plugin.py`), pas via `BaseAgent` — voir « Limites connues ».

Le registre des catégories a été corrigé en #1981 : `byzantine` et `raft` sont des **protocoles** de tolérance aux pannes, *pas* des scrutins, et `approval` est une fonction de choix social, *pas* une règle de vote de gouvernance. Le fichier `tests/unit/.../test_governance_category_register_1981.py` garde la disjonction entre les deux registres **sans figer les comptes** (ajouter un 8e protocole ne rougit pas).

## Composants publics

**Algorithms de gouvernance** — `governance_methods.py` (137 l.)

- 5 règles de vote (scrutins) : `majority_voting`, `plurality_voting`, `borda_count`, `condorcet_method`, `quadratic_voting` ;
- 2 protocoles de consensus distribué : `byzantine_consensus`, `raft_consensus` ;
- `GOVERNANCE_METHODS` — dictionnaire de **7 entrées** (les 5 scrutins + les 2 protocoles, telles quelles).

**Fonctions de choix social** — `social_choice.py` (344 l.), sur profils de bulletins (`ballots: List[List[str]]`)

`approval_voting`, `stv`, `copeland`, `kemeny_young`, `kemeny_young_safe`, `schulze`, `condorcet_winner`, `pairwise_matrix` — **8 `def` de module**. `SOCIAL_CHOICE_METHODS` n'en **énumère que 5** : le dict est le dispatcher du plugin, pas le recensement.

**Archétypes d'agents** — `governance_agent.py` (270 l.)

`Agent` (personnalité, préférences, réseau de confiance, mémoire, coalitions, Q-learning), `BDIAgent`, `ReactiveAgent`, `AgentFactory` (`create_agents`, `PERSONALITIES`). Ce sont des **objets Python simples** (pas de `BaseAgent`, pas de kernel).

**Simulation** — `simulation.py` **retiré (#2137)** : 257 lignes (coalitions/Shapley, gossip, `simulate_governance`, `manipulability_analysis`), zéro appelant de production — seuls `__init__` (ré-export) et ses tests l'exerçaient. Parti avec `test_governance_simulation.py`.

**Conflits** — `conflict_resolution.py` (61 l.) : `detect_conflicts`, `resolve_conflict`, `collaborative_mediation`, `competitive_mediation`, `compromise_mediation`.

**Métriques** — `metrics.py` (116 l.) : `consensus_rate` (tolérant aux 3 formes de `votes`, #1273), `gini`, `fairness_index`, `efficiency`, `satisfaction`, `stability`, `summarize_results`. `per_agent_satisfaction` et `validate_scenario` ont été retirés (#2137) : zéro appelant — leurs seuls consommateurs étaient `simulation.py` (retiré) et leurs tests. `gini`/`efficiency`/`stability` **restent** : contrairement au relevé 12-09, ils ne sont pas orphelins — `fairness_index` appelle `gini` et `summarize_results` appelle `efficiency` et `stability`.

`__init__.py` (42 l.) exporte **8 noms** (`__all__`) : `Agent`, `GOVERNANCE_METHODS`, `detect_conflicts`, `resolve_conflict`, `consensus_rate`, `fairness_index`, `satisfaction`, `summarize_results`. Les ré-exports de `BDIAgent`/`ReactiveAgent`/`AgentFactory` ont été retirés (#2137) — les classes restent importables depuis `governance_agent`.

## Points d'entrée valides

1. **Registre Lego** : `orchestration/registry_setup.py` — `register_agent(name="governance_agent", agent_class=Agent, capabilities=["governance_simulation"], invoke=_invoke_governance)`. **Une seule surface** de capacité (voir plus bas) ;
2. **Phases workflow** : 11 littéraux `add_phase(capability="governance_simulation")` en production — 6 dans `orchestration/workflows.py` et 1 chacun dans `workflows/formal_debate.py`, `workflows/democratech.py`, `workflows/debate_tournament.py`, `workflows/comprehensive_analysis.py`, `workflows/belief_dynamics.py` ;
3. **Invocation** : `orchestration/invoke_callables.py` `_invoke_governance` → `GovernancePlugin` (`list_governance_methods`, `detect_conflicts_fn`, `resolve_conflict_fn`) ; agrégation formelle `_aggregate_governance_votes` → `GOVERNANCE_METHODS.items()` + 5 appels de choix social ; profil d'électeurs dérivé honnêtement (les 9 vertus) `_derive_governance_profile`, instanciation `Agent(...)` ;
4. **HTTP** : `api/agent_routes.py` — `POST /governance` → `_run_pipeline_phase(..., "governance_simulation", ...)` ;
5. **MCP** : `services/mcp_server/tools/specialized_tools.py` — outil `run_governance_analysis` via `_invoke_by_capability("governance_simulation", ...)` ;
6. **Router** : `orchestration/router.py` (capability connue), (description), (sélection) ;
7. **Conversationnel** : `orchestration/conversational_orchestrator.py` — `capabilities_used.add("governance_simulation")` ;
8. **Écrivain d'état** : `orchestration/state_writers.py` mappe `"governance_simulation"` → `_write_governance_to_state` → `UnifiedAnalysisState.add_governance_decision` (`core/shared_state.py`).

Le plugin est aussi déclaré dans la carte de chargement paresseux `agents/factory.py` (`"governance"` → `GovernancePlugin`).

## Amont / aval

- **Amont** : sortie de la phase qualité (`per_argument_scores` / `scores_par_vertu`), arguments extraits, `llm_governance_assessment` ; `_resolve_phase_output` absorbe les variantes de nommage de phase (#1472).
- **Aval** : `UnifiedAnalysisState.governance_decisions` (`shared_state.py`) → `governance_decisions` dans le snapshot, consommé par `api/agent_routes.py` et la restitution.

## Statut d'intégration

| Module | Statut | Preuve mesurée |
|---|---|---|
| `governance_methods.py` | **actif** | `invoke_callables.py` itère `GOVERNANCE_METHODS` en production |
| `social_choice.py` | **actif** | `invoke_callables.py` (5 appels) + `governance_plugin.py` |
| `governance_agent.py` | **actif** | `invoke_callables.py` (`Agent` comme électeur) ; `registry_setup.py` |
| `conflict_resolution.py` | **actif** | `governance_plugin.py` appelés par `invoke_callables.py` |
| `metrics.py` | **actif** | `governance_plugin.py` (`consensus_rate`, `fairness_index`, `satisfaction` ; les deux dernières absentes et nommées sous `unavailable` quand l'entrée ne porte pas de scores `satisfaction`, #2344) |
| `plugins/governance_plugin.py` | **actif** | `invoke_callables.py` |
| ~~`simulation.py`~~ | **retiré (#2137)** | 0 appelant de production : seuls `__init__` (ré-export) et `tests/.../test_governance_simulation.py` l'exerçaient |

Statut global du paquet : **actif** — 8 familles de points d'entrée production mesurées, 200 `def test_` sur 9 fichiers.

Le paquet est **`actif` mais pas `actif-critique`** : dans 5 des 11 phases il est `optional=True`, et `_invoke_governance` a une branche *honnêtement dégradée* quand le profil n'est pas dérivable.

## Artefacts et lecteurs

Verdict formel `winners_per_method` + `distinct_winners` + `inter_method_disagreement` — **jamais réconcilié en un nombre unique** (discipline anti-réconciliation, cf. multi-prover FOL). Cet artefact alimente `governance_decisions` dans l'état, lu par la route HTTP et la restitution.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/governance/ -v
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py -v
```

**200 `def test_`** sur **9 fichiers** (235/10 avant les retraits #2137) — 169 sur les 6 fichiers de `tests/unit/argumentation_analysis/agents/core/governance/` (`test_social_choice.py` 37, `test_governance.py` 38, `test_governance_metrics.py` 36, `test_governance_methods.py` 27, `test_conflict_resolution.py` 25, `test_governance_category_register_1981.py` 6) + 31 croisés (`test_governance_plugin.py` 15, `test_auto_evaluate_governance.py` 9, `test_governance_ge4_1462.py` 7). Compté par `grep -c "def test_"` sur le chemin, pas par collecte pytest.

## Frères et parent

Parent : `agents/core/` ([`../README.md`](../README.md)). Plugin hôte : [`../../../plugins/governance_plugin.py`](../../../plugins/governance_plugin.py). Câblage : [`../../../orchestration/registry_setup.py`](../../../orchestration/registry_setup.py). Origine : projet étudiant `2.1.6_multiagent_governance_prototype/` (racine du dépôt).

## Limites connues

- **`simulation.py` retiré (#2137)** : 257 lignes, 5 fonctions, zéro appelant de production — ni `invoke_callables`, ni le plugin, ni une route. Seuls les tests l'exerçaient. Parti avec son fichier de tests et les ré-exports `__init__` (`simulate_governance`, `manipulability_analysis`).
- **Ce n'est pas un `BaseAgent`** : `governance_agent.py` ne contient que des objets Python (`Agent`/`BDIAgent`/`ReactiveAgent` + une factory). L'intégration SK passe entièrement par le plugin. Le registre enregistre néanmoins `agent_class=Agent` dans un slot `ComponentType.AGENT` (`registry_setup.py`) — le slot reçoit ici une classe non-SK, ce qui n'est vérifié par aucun contrat explicite.
- **Ré-exports retirés (#2137)** : `BDIAgent`, `ReactiveAgent`, `AgentFactory` ne sont plus exportés par `__init__` (seul `Agent` est consommé en production). Les classes restent dans `governance_agent.py` — hors périmètre du triage #2137, qui ne retirait que les re-exports morts du paquet.
- **Métriques** : `per_agent_satisfaction` et `validate_scenario` retirés (#2137, zéro appelant). Le relevé 12-09 qualifiait aussi `gini`/`efficiency`/`stability` d'orphelines — **périmé** : `fairness_index` appelle `gini`, `summarize_results` appelle `efficiency` et `stability` ; les trois restent, consommées intra-module. Le plugin n'importe que `consensus_rate`/`fairness_index`/`satisfaction`.
- **`plurality_voting` est un alias littéral** : `governance_methods.py` retourne `majority_voting(...)`. Les « 5 règles de vote » comptent 5 **noms** mais 4 comportements distincts — et `condorcet_method` retombe sur `borda_count` en l'absence de gagnant de Condorcet, donc deux clés du dict peuvent rendre le même résultat.
- **Choix social partiellement câblé** : l'agrégation production (`invoke_callables.py`) appelle 5 fonctions (approval, stv, copeland, schulze, condorcet_winner). `kemeny_young_safe` et `pairwise_matrix` ne sont atteignables que via les `@kernel_function` du plugin (`social_choice_vote`, `find_condorcet_winner`), elles-mêmes jamais appelées directement par production — seulement par un LLM les invoquant sur un kernel.
- **Champ déclaré non rempli** : `conflict_resolution.py` — `success_probability` vaut toujours `None`, commenté « Not measured — placeholder (#971) ». Le champ a une forme de mesure et n'en porte aucune.
- **Deux définitions de « gouvernance »** : le paquet ci-dessus, et un agent conversationnel LLM nommé `GovernanceAgent` dans `orchestration/conversational_orchestrator.py` — qui ne partage aucun code avec ce paquet. Ne pas confondre les deux surfaces.
