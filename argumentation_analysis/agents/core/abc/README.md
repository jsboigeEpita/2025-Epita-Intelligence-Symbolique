# `agents/core/abc/` — contrats racines des agents (`BaseAgent` / `BaseLogicAgent`)

## Rôle et frontière

3 modules, 790 lignes (`agent_bases.py` 668, `plugin.py` 106, `__init__.py` 16). Le paquet ne contient **aucune logique d'agent** : il définit les contrats que les 13 agents concrets du dépôt héritent. `BaseAgent` (:54) étend `ChatCompletionAgent` de Semantic Kernel — l'héritage est **requis** pour `AgentGroupChat` (commentaire historique :32-36). `BaseLogicAgent` (:262) le spécialise pour le raisonnement formel (pipeline belief-set → requêtes → interprétation).

Frontière : ce paquet ne connaît ni les fallacies, ni la qualité, ni Tweety au-delà d'un type de retour. Il garantit qu'un agent a un kernel, un nom, un prompt, un service LLM, et — pour les agents logiques — un `TweetyBridge`.

## Composants publics

**`agent_bases.py`**

- `BaseAgent(ChatCompletionAgent, ABC)` :54 — `__init__` :84 `(kernel, agent_name, system_prompt=None, description=None, **kwargs)` ; propriétés `logger` :141, `agent_name` :147, `system_prompt` :152 ; `get_agent_info()` :171 ; `invoke()` :238 (transforme `invoke_single` en flux) ; `invoke_stream()` :246.
- Contrat abstrait **mesuré** (`__abstractmethods__`) : exactement 3 méthodes — `get_agent_capabilities` :156, `get_response` :209, `invoke_single` :223.
- `BaseLogicAgent(BaseAgent, ABC)` :262 — `__init__` :290 `(kernel, agent_name, logic_type_name, system_prompt=None, **kwargs)` ; propriétés `logic_type` :314, `tweety_bridge` :324 (lève `RuntimeError` :340 si non initialisé) ; `setup_agent_components()` :345 ; `process_task()` :484 async.
- Contrat abstrait **mesuré** : 10 méthodes — `text_to_belief_set` :365, `generate_queries` :383, `execute_query` :404, `interpret_results` :424, `validate_formula` :453, `is_consistent` :468, `_create_belief_set_from_data` :661, + les 3 héritées.
- `setup_agent_components` :345, `_handle_translation_task` :512 et `_handle_query_task` :560 sont **concrets** (non abstraits).

**`plugin.py`** — interface plugin *distincte* de celle du registry : `BasePlugin(ABC)` :6 (`name`/`execute` abstraits), `ParameterSpec` :22, `LegoPlugin` :32 (`provides`/`requires`/`parameters`, `get_capabilities()` :64, `check_requirements()` :81, `is_available()` :93).

**`__init__.py:16`** — `__all__ = ["agent_bases"]` uniquement ; `plugin` n'est pas ré-exporté.

## Points d'entrée valides

1. **Héritage direct** — `from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent` (`core/pm/pm_agent.py:13`, `core/debate/debate_agent.py:79`, `core/synthesis/synthesis_agent.py:22`…), puis `MyAgent(kernel=kernel, agent_name="…")`. 16 sites d'import production mesurés (`grep -rn 'abc\.agent_bases\|abc\.plugin' argumentation_analysis/` = 18 lignes, moins 1 ligne commentée `orchestration/cluedo_extended_orchestrator.py:21` et 1 import mort sous `TYPE_CHECKING` — voir Limites).
2. **Fabrique logique** — `LogicAgentFactory.create_agent(logic_type: str, kernel: Kernel, llm_service: Optional[Any] = None) -> Optional[BaseLogicAgent]` (`core/logic/logic_factory.py:41`, mapping `_agent_classes` :31). C'est le point d'entrée production pour instancier un agent logique sans nommer sa classe.
3. **Contrôle de type d'un plugin** — `PluginLoader.load_plugins_from_directory(plugins_directory: str) -> dict[str, BasePlugin]` (`core/plugin_loader.py:19`) rejette tout entrypoint qui n'est pas une sous-classe : `issubclass(plugin_class, BasePlugin)` :140.

## Amont / aval

- **Amont** : `semantic_kernel` (`Kernel`, `ChatCompletionAgent`), `pydantic` (`PrivateAttr` :30), et par typage seulement (`TYPE_CHECKING` :46-48) `logic/belief_set.BeliefSet` et `logic/tweety_bridge.TweetyBridge`.
- **Aval** : 13 modules d'agents — `informal_fallacy_agent` :23, `counter_argument/counter_agent` :96, `debate/debate_agent` :193, `extract/extract_agent` :78, `informal/informal_agent` :53, `logic/{fol :188, modal :141, propositional :241}_logic_agent`, `oracle/oracle_base_agent` :383, `pm/{pm_agent :24, sherlock_enquete_agent :232}`, `synthesis/{synthesis_agent :26, deep_synthesis_agent :41}`.
- **Jamais aval** : `agents/factory.py` (AgentFactory) ne référence pas ce paquet (grep vide) ; `registry_setup.py` n'y touche pas non plus.

## Statut d'intégration

| Famille | Statut | Preuve mesurée |
|---|---|---|
| `BaseAgent` / `BaseLogicAgent` | **actif-critique** | 16 imports production ; 13 classes concrètes en héritent ; `tests/unit/argumentation_analysis/test_architecture_compliance.py:51,63` asserte `isinstance(agent, BaseAgent)` sur `CounterArgumentAgent` et `DebateAgent` ; `agent_bases` fait partie du MRO de tout agent du pipeline Lego |
| `plugin.BasePlugin` | **résiduel** | 1 seul importeur production (`core/plugin_loader.py:6`), et `PluginLoader` lui-même n'est importé que par 2 fichiers de test ; la surface plugin réellement câblée est SK (`registry_setup.py:363,382,407,426,444`) et n'utilise pas cette ABC |
| `plugin.LegoPlugin` / `ParameterSpec` | **résiduel** | **zéro** importeur production (grep sur `argumentation_analysis/`) ; seuls `tests/unit/argumentation_analysis/test_plugin_loader.py:17-18` les importent. `capability_registry.py:60` ne fait que *mentionner* « compatibilite LegoPlugin » dans une docstring d'alias |

## Artefacts et lecteurs

Aucun artefact persisté : ce paquet ne produit ni fichier ni état, il produit des **classes**. La seule surface descriptive est `BaseAgent.get_agent_info()` :171 (nom, classe, prompt, `llm_service_id`, capacités) — **aucun lecteur production mesuré**, seul le test :537 l'appelle.

## Tests représentatifs

```bash
/c/Tools/miniconda3/envs/projet-is/python.exe -m pytest \
  tests/unit/argumentation_analysis/agents/core/abc/ -o addopts= --disable-jvm-session -v
```

**20 `def test_` sur 1 fichier** (`grep -c 'def test_'`), **20 passed en 2,42 s** (mesuré le 2026-09-11). Le fichier mocke le kernel (`MagicMock(spec=Kernel)`) — aucun appel LLM, aucune JVM. Couvre : instanciation refusée des ABC, `id`/`name`/`description`, nommage du logger, méthodes abstraites exigées, `invoke`/`invoke_stream` rendant un générateur async, `get_agent_info`.

13 autres fichiers de test mentionnent ce chemin (`grep -rln`), mais ils testent les **agents dérivés**, pas les classes de base — ne pas leur attribuer la couverture de l'ABC.

## Frères et parent

Parent : [`../`](../README.md) (`agents/core/`, sans README propre à ce niveau — voir [`../../README.md`](../../README.md)). Frères déjà documentés : [`../counter_argument/`](../counter_argument/README.md), [`../extract/`](../extract/README.md), [`../informal/`](../informal/README.md), [`../logic/`](../logic/README.md), [`../pm/`](../pm/README.md), [`../synthesis/`](../synthesis/README.md) — tous aval de ce paquet.

## Limites connues

- **Import mort sous `TYPE_CHECKING`** : `core/strategies.py:39` fait `from …abc.agent_bases import Agent`, or `agent_bases.py` ne définit ni n'importe `Agent` (vérifié par AST et `getattr`). Inoffensif à l'exécution (bloc `TYPE_CHECKING`), faux pour tout vérificateur de types. [inféré : jamais exécuté, donc jamais testé]
- **Nom `BasePlugin` défini 3 fois** dans des paquets différents : `abc/plugin.py:6`, `agents/core/orchestration_service.py:20` (classe nue, sans ABC), `plugin_framework/core/plugins/interfaces.py:4` (marqueur `pass`). `api/main.py:6` consomme celui d'`orchestration_service`, `fact_checking_orchestrator.py:27` celui de `plugin_framework` : aucune n'est la classe de `abc/plugin.py`.
- **Docstring contradictoire** : `agent_bases.py:63-65` affirme que le contrat « impose d'implémenter » `setup_agent_components` et `invoke_single`. Mesure : `setup_agent_components` **n'existe pas sur `BaseAgent`** et n'est abstrait nulle part ; les seuls abstraits sont `get_agent_capabilities`, `get_response`, `invoke_single`.
- **Commentaire de test périmé** : `tests/agents/core/informal/test_informal_agent_authentic.py:81` affirme que `get_agent_capabilities()` et `get_agent_info()` « n'existent plus » — les deux existent (:156, :171).
- Pydantic V2 : le logger est `_agent_logger` (`PrivateAttr` :81) exposé via la **property** `logger` :141. Il n'existe **aucun** attribut public `agent_logger` (mesure `dir(BaseAgent)`).
