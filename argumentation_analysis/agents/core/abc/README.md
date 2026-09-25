# `agents/core/abc/` — contrats racines des agents (`BaseAgent` / `BaseLogicAgent`)

## Rôle et frontière

2 modules, 684 lignes (`agent_bases.py` 668, `__init__.py` 16) — `plugin.py` (ABC plugin `BasePlugin`/`LegoPlugin`/`ParameterSpec`) a été retiré (#2145) : son seul importeur production était `core/plugin_loader.py`, lui-même sans appelant de production. Le paquet ne contient **aucune logique d'agent** : il définit les contrats que les 13 agents concrets du dépôt héritent. `BaseAgent` (:54) étend `ChatCompletionAgent` de Semantic Kernel — l'héritage est **requis** pour `AgentGroupChat` (commentaire historique :32-36). `BaseLogicAgent` (:262) le spécialise pour le raisonnement formel (pipeline belief-set → requêtes → interprétation).

Frontière : ce paquet ne connaît ni les fallacies, ni la qualité, ni Tweety au-delà d'un type de retour. Il garantit qu'un agent a un kernel, un nom, un prompt, un service LLM, et — pour les agents logiques — un `TweetyBridge`.

## Composants publics

**`agent_bases.py`**

- `BaseAgent(ChatCompletionAgent, ABC)` :54 — `__init__` :84 `(kernel, agent_name, system_prompt=None, description=None, **kwargs)` ; propriétés `logger` :141, `agent_name` :147, `system_prompt` :152 ; `invoke()` :238 (transforme `invoke_single` en flux) ; `invoke_stream()` :246. `get_agent_info()` a été retiré (#2137 : 0 lecteur production, le registre porte l'info agent).
- Contrat abstrait **mesuré** (`__abstractmethods__`) : exactement 3 méthodes — `get_agent_capabilities` :156, `get_response` :209, `invoke_single` :223.
- `BaseLogicAgent(BaseAgent, ABC)` :246 — `__init__` :286 `(kernel, agent_name, logic_type_name, system_prompt=None, **kwargs)` ; propriétés `logic_type` :311, `tweety_bridge` :321 (lève `RuntimeError` :336 si non initialisé) ; `setup_agent_components()` :341 ; `process_task()` :476 async.
- Contrat abstrait **mesuré** : 10 méthodes — `text_to_belief_set` :362, `generate_queries` :380, `execute_query` :401, `interpret_results` :421, `validate_formula` :446, `is_consistent` :461, `_create_belief_set_from_data` :654, + les 3 héritées.
- **Convention d'appel (#2641)** : les cinq étapes (`text_to_belief_set`, `generate_queries`, `execute_query`, `is_consistent`, `interpret_results`) sont des coroutines, attendues par tout appelant ; `validate_formula` et `_create_belief_set_from_data` sont synchrones. La raison est dans la docstring de la classe. `tests/unit/argumentation_analysis/agents/core/abc/test_logic_agent_calling_convention_2641.py` garde le genre de chaque surcharge et l'`await` de chaque appel en production.
- `setup_agent_components` :341, `_handle_translation_task` :504 et `_handle_query_task` :552 sont **concrets** (non abstraits).

**`__init__.py:16`** — `__all__ = ["agent_bases"]`.

## Points d'entrée valides

1. **Héritage direct** — `from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent` (`core/pm/pm_agent.py:13`, `core/debate/debate_agent.py:79`, `core/synthesis/synthesis_agent.py:22`…), puis `MyAgent(kernel=kernel, agent_name="…")`. 15 sites d'import production mesurés (`grep -rn 'abc\.agent_bases' argumentation_analysis/` = 17 lignes, moins 1 ligne commentée `orchestration/cluedo_extended_orchestrator.py:21` et 1 commentaire #2137 — voir Limites).
2. **Fabrique logique** — `LogicAgentFactory.create_agent(logic_type: str, kernel: Kernel, llm_service: Optional[Any] = None) -> Optional[BaseLogicAgent]` (`core/logic/logic_factory.py:41`, mapping `_agent_classes` :31). C'est le point d'entrée production pour instancier un agent logique sans nommer sa classe.

## Amont / aval

- **Amont** : `semantic_kernel` (`Kernel`, `ChatCompletionAgent`), `pydantic` (`PrivateAttr` :30), et par typage seulement (`TYPE_CHECKING` :46-48) `logic/belief_set.BeliefSet` et `logic/tweety_bridge.TweetyBridge`.
- **Aval** : 13 modules d'agents — `informal_fallacy_agent` :23, `counter_argument/counter_agent` :96, `debate/debate_agent` :193, `extract/extract_agent` :78, `informal/informal_agent` :53, `logic/{fol :188, modal :141, propositional :241}_logic_agent`, `oracle/oracle_base_agent` :383, `pm/{pm_agent :24, sherlock_enquete_agent :232}`, `synthesis/{synthesis_agent :26, deep_synthesis_agent :41}`.
- **Jamais aval** : `agents/factory.py` (AgentFactory) ne référence pas ce paquet (grep vide) ; `registry_setup.py` n'y touche pas non plus.

## Statut d'intégration

| Famille | Statut | Preuve mesurée |
|---|---|---|
| `BaseAgent` / `BaseLogicAgent` | **actif-critique** | 16 imports production ; 13 classes concrètes en héritent ; `tests/unit/argumentation_analysis/test_architecture_compliance.py:51,63` asserte `isinstance(agent, BaseAgent)` sur `CounterArgumentAgent` et `DebateAgent` ; `agent_bases` fait partie du MRO de tout agent du pipeline Lego |

## Artefacts et lecteurs

Aucun artefact persisté : ce paquet ne produit ni fichier ni état, il produit des **classes**. La surface descriptive `BaseAgent.get_agent_info()` (nom, classe, prompt, `llm_service_id`, capacités) a été **retirée (#2137)** : aucun lecteur production mesuré, seul son propre test l'appelait.

## Tests représentatifs

```bash
/c/Tools/miniconda3/envs/projet-is/python.exe -m pytest \
  tests/unit/argumentation_analysis/agents/core/abc/ -o addopts= --disable-jvm-session -v
```

**19 `def test_` sur 1 fichier** (`grep -c 'def test_'` ; 20 avant le retrait du test `get_agent_info`, #2137), **19 passed** (mesuré le 2026-09-11 pour 20). Le fichier mocke le kernel (`MagicMock(spec=Kernel)`) — aucun appel LLM, aucune JVM. Couvre : instanciation refusée des ABC, `id`/`name`/`description`, nommage du logger, méthodes abstraites exigées, `invoke`/`invoke_stream` rendant un générateur async.

13 autres fichiers de test mentionnent ce chemin (`grep -rln`), mais ils testent les **agents dérivés**, pas les classes de base — ne pas leur attribuer la couverture de l'ABC.

## Frères et parent

Parent : [`../`](../README.md) (`agents/core/`, sans README propre à ce niveau — voir [`../../README.md`](../../README.md)). Frères déjà documentés : [`../counter_argument/`](../counter_argument/README.md), [`../extract/`](../extract/README.md), [`../informal/`](../informal/README.md), [`../logic/`](../logic/README.md), [`../pm/`](../pm/README.md), [`../synthesis/`](../synthesis/README.md) — tous aval de ce paquet.

## Limites connues

- **Nom `BasePlugin` défini 2 fois** dans des paquets différents : `agents/core/orchestration_service.py:20` (classe nue, sans ABC) et `plugin_framework/core/plugins/interfaces.py:4` (marqueur `pass`). `api/main.py:6` consomme celui d'`orchestration_service`, `fact_checking_orchestrator.py:27` celui de `plugin_framework` — le tiers (`abc/plugin.py`, sans consommateur) a été retiré (#2145).
- **Docstring contradictoire** : `agent_bases.py:63-65` affirme que le contrat « impose d'implémenter » `setup_agent_components` et `invoke_single`. Mesure : `setup_agent_components` **n'existe pas sur `BaseAgent`** et n'est abstrait nulle part ; les seuls abstraits sont `get_agent_capabilities`, `get_response`, `invoke_single`.
- `get_agent_info()` retiré (#2137) — le commentaire de test `tests/agents/core/informal/test_informal_agent_authentic.py:81` est désormais exact et a été mis à jour pour ne nommer que ce qui est vrai.
- Pydantic V2 : le logger est `_agent_logger` (`PrivateAttr` :81) exposé via la **property** `logger` :141. Il n'existe **aucun** attribut public `agent_logger` (mesure `dir(BaseAgent)`).

---

*Révision — 2026-09-14, `#2145` (grain finition). `plugin.py` (`BasePlugin`/`LegoPlugin`/`ParameterSpec`) et l'entrée « Contrôle de type d'un plugin » ont été retirés avec le chargeur qui les consommait (`agents/core/plugin_loader.py`, 0 appelant de production, format de manifeste incompatible avec l'unique `manifest.json` du dépôt). La limite « import mort sous `TYPE_CHECKING` » de `core/strategies.py` était périmée — #2137 l'avait déjà corrigée en important `Agent` depuis Semantic Kernel ; l'item est retiré, non réécrit. Compteurs re-mesurés après retrait (2 modules / 684 lignes / 15 sites d'import production).*

*Révision — 2026-09-16, `#2137` (triage agents/core) : `get_agent_info()` retiré (0 lecteur production ; le registre porte l'info agent) avec son test dédié.*
