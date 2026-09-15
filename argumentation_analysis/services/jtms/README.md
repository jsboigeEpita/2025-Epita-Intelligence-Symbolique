# jtms/ — Systèmes de maintenance de vérité (JTMS, ATMS, croyances étendues, résolution de conflits)

## Rôle et frontière

Moteurs de *truth maintenance* purs, sans I/O ni dépendance réseau. Le JTMS
(justification-based) propage la vérité courante d'une croyance via ses
justifications ; l'ATMS (assumption-based) énumère les environnements
d'hypothèses sous lesquels un nœud est dérivable ; `ExtendedBelief` /
`JTMSSession` enrobent les croyances avec source agent, confiance et piste
d'audit ; `ConflictResolver` réconcilie des croyances contradictoires issues
d'agents multiples (5 stratégies, #214). Intégré du projet étudiant
`1.4.1-JTMS`, étendu par #214.

La frontière exclut : les agents JTMS (`agents/jtms_agent_base.py`,
`agents/sherlock_jtms_agent.py` ; le bras mort `agents/watson_jtms/` et le hub
`agents/jtms_communication_hub.py` ont été retirés, #2122 A4) et les plugins
d'exposition (`plugins/atms_plugin.py`, plugins d'état). Ce répertoire ne
fournit que la logique que ces consommateurs orchestrent.

## Composants publics

| Composant | Fichier | Ce qu'il fait |
|---|---|---|
| `JTMS`, `Belief`, `Justification` | `jtms_core.py` | moteur justification-based : ajout/retrait de croyances, propagation de validité (`set_belief_validity` accepte un tri-état `Optional[bool]`) |
| `ATMS`, `ATMSNode`, `ATMSJustification` | `atms_core.py` | moteur assumption-based : environnements de dérivation par nœud |
| `ExtendedBelief`, `JTMSSession` | `extended_belief.py` | croyance avec `agent_source`, `confidence`, historique de modifications ; session par agent avec détection de contradiction |
| `ConflictResolver` | `conflict_resolution.py` | 5 stratégies de résolution pour croyances conflictuelles multi-agents |

`__init__.py` ré-exporte l'ensemble — import canonique :
`from argumentation_analysis.services.jtms import JTMS, ATMS, ExtendedBelief, ConflictResolver`.

## Points d'entrée valides

- Import du package (voie principale, cf. importeurs ci-dessous).
- Enregistrement service : `jtms_service` (`orchestration/registry_setup.py:177-186`)
  et `atms_service` (`registry_setup.py:192`) auprès de la `CapabilityRegistry`.
- Invokers d'orchestration : `_invoke_jtms`
  (`orchestration/invoke_callables.py:2236`) et `_invoke_atms`
  (`invoke_callables.py:2570`).

## Amont / aval

- **Amont (consommateurs prouvés)** : `orchestration/registry_setup.py`
  (services), `orchestration/invoke_callables.py` (invokers +
  `ExtendedBelief`), `plugins/atms_plugin.py:31` (4 `@kernel_function`),
  `agents/sherlock_jtms_agent.py:17`
  (`agents/watson_jtms/agent.py` et `agents/jtms_communication_hub.py`
  consommateurs retirés avec le bras mort, #2122 A4),
  `agents/core/oracle/hypothesis_tracker.py:19` (ATMS),
  `core/state_manager_plugin.py` et `core/phase_scoped_state.py`
  (`ExtendedBelief`), `orchestration/conversational_orchestrator.py:2912,2915`
  (`ConflictResolver`).
- **Aval** : aucun — feuille du graphe de dépendances (aucun module du repo
  n'est importé depuis ici).

## Statut d'intégration

| Famille | Statut | Preuve |
|---|---|---|
| `jtms_core` | **actif** | service `jtms_service` enregistré (`registry_setup.py:177`) + invoker production `_invoke_jtms` (`invoke_callables.py:2236`) |
| `atms_core` | **actif** | `plugins/atms_plugin.py:31`, `registry_setup.py:192`, `invoke_callables.py:2570`, `hypothesis_tracker.py:19` |
| `extended_belief` | **actif** | 6 importeurs production : sherlock, watson, hub, `state_manager_plugin.py`, `phase_scoped_state.py`, `invoke_callables.py` |
| `conflict_resolution` | **actif** | appelant production unique `conversational_orchestrator.py:2912-2915` (mode conversationnel) |

## Artefacts et lecteurs

Tout est en mémoire : croyances et justifications vivent dans l'instance
`JTMS`/`ATMS`, les croyances étendues dans la `JTMSSession` de chaque agent.
Aucune écriture disque, aucun état global de module — les lecteurs sont les
agents et l'orchestration qui détiennent les instances.

## Tests représentatifs

```bash
# unitaires (une par composant public)
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/unit/argumentation_analysis/services/test_jtms_core.py \
  tests/unit/argumentation_analysis/services/test_extended_belief.py \
  tests/unit/argumentation_analysis/services/test_jtms_conflict_resolution.py -v

# invariants structurels (propriété)
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/property/test_jtms_invariants.py tests/property/test_atms_invariants.py -v
```

## Frères et parent

- Parent : [services/](../) — README parent : [../README.md](../README.md)
- Frères consommateurs directs dans `services/` : aucun (les consommateurs
  sont dans `agents/`, `plugins/`, `orchestration/`, `core/`).

## Limites connues

- Contrat ATMS (**décision documentée**, #2094 — la phrase originale « l'ATMS
  ne re-propage pas les labels après retrait d'une hypothèse » décrivait une
  opération qui n'existe pas) : les labels ne sont calculés qu'à l'insertion
  d'une justification (`add_justification`) et ne sont retirés que par un
  `invalidate_environment` explicite. Il n'existe ni API de retrait
  d'hypothèse ni re-propagation. `invalidate_environment` retire l'env et ses
  sur-ensembles de **tous** les nœuds, `⊥` compris : un nogood n'est pas
  mémorisé (`is_consistent(nogood)` redevient vrai), et invalider le
  singleton d'une hypothèse la rend sous-dérivable (son propre label est
  retiré et rien ne le ressème). C'est pourquoi `hypothesis_tracker.py` tient
  son propre registre (`_contradicted_by`). Épinglé par
  `tests/property/test_atms_invariants.py` (stabilité des labels hors
  insertion ; oubli du nogood par `⊥`).
- Corrigé (#2094) — affichage tri-état : `explain_belief` et `visualize`
  rendent désormais `None` comme indéterminé (« unknown » / gris), alignés
  sur `Belief.__str__` qui rend UNKNOWN.
- Corrigé (#2094) — `remove_belief` : démontage symétrique — les
  justifications concluant vers la croyance supprimée quittent les
  `implications` des prémisses, et celles dont elle était prémisse quittent
  la conclusion ET les co-prémisses ; une propagation postérieure ne peut
  plus traverser (ni tracer) une conclusion disparue.
