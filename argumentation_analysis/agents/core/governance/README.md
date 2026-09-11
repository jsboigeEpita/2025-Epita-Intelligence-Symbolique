# `agents/core/governance/` — agrégation de préférences et simulations de gouvernance

## Rôle et frontière

7 modules (1 266 l. avec `__init__`) — le paquet qui **agrège des préférences** et **simule des collectifs** : scrutins d'agrégation, protocoles de consensus distribué, fonctions de choix social classiques, archétypes d'agents électeurs, détection/médiation de conflits, métriques de consensus. C'est la couche « décider ensemble » ; elle ne produit pas d'analyse du texte, elle consomme des **scores d'arguments** (les 9 vertus qualité) comme électeurs et rend un verdict de vote.

Le paquet vient du projet étudiant `2.1.6_multiagent_governance_prototype` (GitHub #43), intégré sous architecture BaseAgent/SK (#35) : il est **exposé via un plugin** (`argumentation_analysis/plugins/governance_plugin.py`), pas via `BaseAgent` — voir « Limites connues ».

Le registre des catégories a été corrigé en #1981 : `byzantine` et `raft` sont des **protocoles** de tolérance aux pannes, *pas* des scrutins, et `approval` est une fonction de choix social, *pas* une règle de vote de gouvernance. Le fichier `tests/unit/.../test_governance_category_register_1981.py` garde la disjonction entre les deux registres **sans figer les comptes** (ajouter un 8e protocole ne rougit pas).

## Composants publics

**Algorithms de gouvernance** — `governance_methods.py` (137 l.)

- 5 règles de vote (scrutins) : `majority_voting` :32, `plurality_voting` :40, `borda_count` :45, `condorcet_method` :57, `quadratic_voting` :79 ;
- 2 protocoles de consensus distribué : `byzantine_consensus` :101, `raft_consensus` :113 ;
- `GOVERNANCE_METHODS` :129 — dictionnaire de **7 entrées** (les 5 scrutins + les 2 protocoles, telles quelles).

**Fonctions de choix social** — `social_choice.py` (344 l.), sur profils de bulletins (`ballots: List[List[str]]`)

`approval_voting` :20, `stv` :44, `copeland` :109, `kemeny_young` :149, `kemeny_young_safe` :204, `schulze` :233, `condorcet_winner` :294, `pairwise_matrix` :322 — **8 `def` de module**. `SOCIAL_CHOICE_METHODS` :338 n'en **énumère que 5** : le dict est le dispatcher du plugin, pas le recensement.

**Archétypes d'agents** — `governance_agent.py` (270 l.)

`Agent` :20 (personnalité, préférences, réseau de confiance, mémoire, coalitions, Q-learning :57/:67), `BDIAgent` :194, `ReactiveAgent` :220, `AgentFactory` :237 (`create_agents` :241, `PERSONALITIES` :17). Ce sont des **objets Python simples** (pas de `BaseAgent`, pas de kernel).

**Simulation** — `simulation.py` (257 l.)

`simulate_governance` :69, `simulate_manipulation` :187, `manipulability_analysis` :231, `shapley_value` :18, `distributed_gossip_consensus` :47.

**Conflits** — `conflict_resolution.py` (61 l.) : `detect_conflicts` :8, `resolve_conflict` :25, `collaborative_mediation` :37, `competitive_mediation` :46, `compromise_mediation` :55.

**Métriques** — `metrics.py` (154 l.) : `consensus_rate` :12 (tolérant aux 3 formes de `votes`, #1273), `gini` :48, `fairness_index` :62, `efficiency` :69, `satisfaction` :80, `stability` :87, `per_agent_satisfaction` :95, `summarize_results` :102, `validate_scenario` :121.

`__init__.py` (43 l.) exporte **13 noms** (`__all__` :24-38), tous vérifiés réels : `Agent`, `BDIAgent`, `ReactiveAgent`, `AgentFactory`, `GOVERNANCE_METHODS`, `simulate_governance`, `manipulability_analysis`, `detect_conflicts`, `resolve_conflict`, `consensus_rate`, `fairness_index`, `satisfaction`, `summarize_results`. **Zéro fantôme**, mais 5 fonctions de `metrics.py` (`gini`, `efficiency`, `stability`, `per_agent_satisfaction`, `validate_scenario`) restent hors `__all__`.

## Points d'entrée valides

1. **Registre Lego** : `orchestration/registry_setup.py:158-168` — `register_agent(name="governance_agent", agent_class=Agent, capabilities=["governance_simulation"], invoke=_invoke_governance)`. **Une seule surface** de capacité (voir plus bas) ;
2. **Phases workflow** : 11 littéraux `add_phase(capability="governance_simulation")` en production — 6 dans `orchestration/workflows.py` (:230, :305, :489, :583, :594, :956) et 1 chacun dans `workflows/formal_debate.py:88`, `workflows/democratech.py:120`, `workflows/debate_tournament.py:96`, `workflows/comprehensive_analysis.py:105`, `workflows/belief_dynamics.py:74` ;
3. **Invocation** : `orchestration/invoke_callables.py:1924 _invoke_governance` → `GovernancePlugin` :1928-1931 (`list_governance_methods`), :1977 (`detect_conflicts_fn`), :1981 (`resolve_conflict_fn`) ; agrégation formelle `_aggregate_governance_votes` :1820 → `GOVERNANCE_METHODS.items()` :1852 + 5 appels de choix social :1864/:1868/:1873/:1877/:1881 ; profil d'électeurs dérivé honnêtement (les 9 vertus) `_derive_governance_profile` :1735, instanciation `Agent(...)` :1800 ;
4. **HTTP** : `api/agent_routes.py:291` — `POST /governance` → `_run_pipeline_phase(..., "governance_simulation", ...)` :306 ;
5. **MCP** : `services/mcp_server/tools/specialized_tools.py:104` — outil `run_governance_analysis` via `_invoke_by_capability("governance_simulation", ...)` ;
6. **Router** : `orchestration/router.py:38` (capability connue), :57 (description), :347-348 (sélection) ;
7. **Conversationnel** : `orchestration/conversational_orchestrator.py:1770` — `capabilities_used.add("governance_simulation")` ;
8. **Écrivain d'état** : `orchestration/state_writers.py:2291` mappe `"governance_simulation"` → `_write_governance_to_state` :690 → `UnifiedAnalysisState.add_governance_decision` (`core/shared_state.py:971`).

Le plugin est aussi déclaré dans la carte de chargement paresseux `agents/factory.py:92` (`"governance"` → `GovernancePlugin`).

## Amont / aval

- **Amont** : sortie de la phase qualité (`per_argument_scores` / `scores_par_vertu`), arguments extraits, `llm_governance_assessment` ; `_resolve_phase_output` :1903 absorbe les variantes de nommage de phase (#1472).
- **Aval** : `UnifiedAnalysisState.governance_decisions` (`shared_state.py:511`) → `governance_decisions` dans le snapshot, consommé par `api/agent_routes.py:310` et la restitution.

## Statut d'intégration

| Module | Statut | Preuve mesurée |
|---|---|---|
| `governance_methods.py` | **actif** | `invoke_callables.py:1852` itère `GOVERNANCE_METHODS` en production |
| `social_choice.py` | **actif** | `invoke_callables.py:1864-1881` (5 appels) + `governance_plugin.py:129-160` |
| `governance_agent.py` | **actif** | `invoke_callables.py:1754/:1800` (`Agent` comme électeur) ; `registry_setup.py:154-160` |
| `conflict_resolution.py` | **actif** | `governance_plugin.py:52/:66` appelés par `invoke_callables.py:1977/:1981` |
| `metrics.py` | **actif** | `governance_plugin.py:85-92` (`consensus_rate`, `fairness_index`, `satisfaction`) |
| `plugins/governance_plugin.py` | **actif** | `invoke_callables.py:1928-1931` |
| `simulation.py` | **résiduel** | 0 appelant de production : seuls `__init__.py:20/:30-31` (ré-export) et `tests/.../test_governance_simulation.py` (20 tests) |

Statut global du paquet : **actif** — 8 familles de points d'entrée production mesurées, 235 `def test_` sur 10 fichiers.

Le paquet est **`actif` mais pas `actif-critique`** : dans 5 des 11 phases il est `optional=True`, et `_invoke_governance` a une branche *honnêtement dégradée* (:1997-2003) quand le profil n'est pas dérivable.

## Artefacts et lecteurs

Verdict formel `winners_per_method` + `distinct_winners` + `inter_method_disagreement` (:1892-1900) — **jamais réconcilié en un nombre unique** (discipline anti-réconciliation, cf. multi-prover FOL). Cet artefact alimente `governance_decisions` dans l'état, lu par la route HTTP et la restitution. `simulation.py` produirait des rapports de manipulabilité (`manipulability_analysis` :231), mais aucun lecteur production ne les déclenche.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/governance/ -v
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py -v
```

**235 `def test_`** sur **10 fichiers** — 204 sur les 7 fichiers de `tests/unit/argumentation_analysis/agents/core/governance/` (`test_governance.py` 42, `test_governance_metrics.py` 47, `test_social_choice.py` 37, `test_governance_methods.py` 27, `test_conflict_resolution.py` 25, `test_governance_simulation.py` 20, `test_governance_category_register_1981.py` 6) + 31 croisés (`test_governance_plugin.py` 15, `test_auto_evaluate_governance.py` 9, `test_governance_ge4_1462.py` 7). Compté par `grep -c "def test_"` sur le chemin, pas par collecte pytest.

## Frères et parent

Parent : `agents/core/` ([`../README.md`](../README.md)). Plugin hôte : [`../../../plugins/governance_plugin.py`](../../../plugins/governance_plugin.py). Câblage : [`../../../orchestration/registry_setup.py`](../../../orchestration/registry_setup.py). Origine : projet étudiant `2.1.6_multiagent_governance_prototype/` (racine du dépôt).

## Limites connues

- **`simulation.py` est résiduel** : 257 lignes, 5 fonctions, exporté dans `__all__`, et **zéro appelant de production** — ni `invoke_callables`, ni le plugin, ni une route. Seuls les tests l'exercent. L'export public dans `__init__.py:30-31` laisse croire à une API vivante.
- **Ce n'est pas un `BaseAgent`** : `governance_agent.py` ne contient que des objets Python (`Agent`/`BDIAgent`/`ReactiveAgent` + une factory). L'intégration SK passe entièrement par le plugin. Le registre enregistre néanmoins `agent_class=Agent` dans un slot `ComponentType.AGENT` (`registry_setup.py:158-160`) — le slot reçoit ici une classe non-SK, ce qui n'est vérifié par aucun contrat explicite.
- **Classes sans appelant production** : `BDIAgent`, `ReactiveAgent`, `AgentFactory` — ré-exportés (`__init__.py:18`) mais seul `Agent` est consommé en production. Atteignables uniquement par les tests.
- **Fonctions de `metrics.py` orphelines** : `gini` :48, `efficiency` :69, `stability` :87, `per_agent_satisfaction` :95, `validate_scenario` :121 — zéro appelant production, hors `__all__`. Le plugin n'importe que `consensus_rate`/`fairness_index`/`satisfaction`.
- **`plurality_voting` est un alias littéral** : `governance_methods.py:40-42` retourne `majority_voting(...)`. Les « 5 règles de vote » comptent 5 **noms** mais 4 comportements distincts — et `condorcet_method` :76 retombe sur `borda_count` en l'absence de gagnant de Condorcet, donc deux clés du dict peuvent rendre le même résultat.
- **Choix social partiellement câblé** : l'agrégation production (`invoke_callables.py:1864-1881`) appelle 5 fonctions (approval, stv, copeland, schulze, condorcet_winner). `kemeny_young_safe` et `pairwise_matrix` ne sont atteignables que via les `@kernel_function` du plugin (`social_choice_vote` :122, `find_condorcet_winner` :171), elles-mêmes jamais appelées directement par production — seulement par un LLM les invoquant sur un kernel.
- **Champ déclaré non rempli** : `conflict_resolution.py:40/:50/:58` — `success_probability` vaut toujours `None`, commenté « Not measured — placeholder (#971) ». Le champ a une forme de mesure et n'en porte aucune.
- **Deux définitions de « gouvernance »** : le paquet ci-dessus, et un agent conversationnel LLM nommé `GovernanceAgent` dans `orchestration/conversational_orchestrator.py:437/.1769` — qui ne partage aucun code avec ce paquet. Ne pas confondre les deux surfaces.
