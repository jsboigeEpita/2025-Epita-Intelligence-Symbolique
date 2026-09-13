# `argumentation_analysis/plugins/` — paquet agrégateur des surfaces Semantic Kernel, sans contrat d'export

Paquet « à plat » : **21** modules `.py` au premier niveau, **6 480** lignes (`wc -l`), portant **86** `def` réellement décorés `@kernel_function` (mesure AST) répartis sur **18** classes plugin. En récursif il compte **36** `.py` / **12 609** lignes, le surplus venant de deux sous-paquets traités par des fiches propres (`semantic_kernel/`, `analysis_tools/`). Son `__init__.py` fait **0 octet** : le paquet n'expose rien, et tout son câblage vit hors de lui, dans `agents/factory.py` et `orchestration/registry_setup.py`.

> Deux pièges de comptage à garder en tête. (1) `grep -c '^\s*@kernel_function'` sur les 21 modules rend **88** : les 2 de trop sont `quality_scoring_plugin.py:26` et `french_fallacy_plugin.py:25`, deux **docstrings** dont une ligne commence par ce texte. Le compte honnête est **86**. (2) 6 480 est le total du **premier niveau** ; 12 609 est le total **récursif** — deux nombres exacts, deux ensembles différents.

---

## Rôle et frontière

**Ce que l'assemblage apporte que les feuilles n'apportent pas seules :**

1. **Une convention d'entrée partagée.** `kernel_input.parse_kernel_json_object` (`kernel_input.py:15`) est le contrat unique des entrées `@kernel_function` : jamais d'exception, toujours un objet d'erreur sérialisable nommant les clés reçues **et** attendues (`kernel_input.py:35-41`). Adoption mesurée : **21/21** fonctions de `tweety_logic_plugin` (22 occurrences = 1 import + 21 appels) et **5/5** de `kb_to_tweety_plugin` (6 occurrences). **Non adoptée par `logic_agent_plugin`** (8 `@kernel_function`), qui porte son propre `_error_json` (`logic_agent_plugin.py:40`) : la convention est partagée, pas universelle.
2. **Un patron master/slave de kernels imbriqués.** `fallacy_workflow_plugin.py:254` instancie `ExplorationPlugin`, puis le monte sur un kernel *esclave* à `fallacy_workflow_plugin.py:274` (`slave_kernel.add_plugin(self.exploration_plugin, "Exploration")`) ; les appels sont routés par `slave_kernel.plugins.get("Exploration")` (`:626`). C'est le **seul lien structurel intra-paquet**.
3. **Un contrat de données interne.** `identification_models.py` (`IdentifiedFallacy:7`, `FallacyAnalysisResult:39`) n'est consommé qu'en intra-paquet, par `fallacy_workflow_plugin.py:43`.
4. **Un texte de module porteur de contrat, à côté des `@kernel_function`.** Les fonctions de module de `narrative_synthesis_plugin.py` (`build_narrative:50`, `quality_fraction:277`, `quality_population_spans_weak:302`, `compute_argument_convergence:376`, `build_convergent_synthesis:518`) sont le vrai point de lecture de ses 8 consommateurs de production — pas ses 3 `@kernel_function`.

**Hors frontière, explicitement :** les agents (`agents/`), les handlers Tweety (`agents/core/logic/*_handler.py` — le paquet ne fait que les *envelopper*, par import local dans le corps de chaque fonction), les services `services/jtms/`, et les trois répertoires de prompts SK natifs (voir *Limites connues* §6).

**Aucun contrat d'export.** `plugins/__init__.py` = **0 octet** (vérifié sur disque) ; `plugins/semantic_kernel/__init__.py` et `plugins/analysis_tools/__init__.py` également 0 octet. Tous les consommateurs importent le chemin profond du module, jamais `argumentation_analysis.plugins`.

---

## Composants publics

Le paquet n'expose rien au sens Python (pas d'`__all__`, pas de ré-export). Les surfaces réelles sont les méthodes décorées et les classes :

| Nom | Fichier | `@kernel_function` | Statut mesuré (ancre de production) |
|---|---|---|---|
| `TweetyLogicPlugin` | `tweety_logic_plugin.py:82` | 21 | vivant — `registry_setup.py:363`, `agents/factory.py:87-90` |
| `CoordinatedLogicPlugin` | `coordinated_logic_plugin.py:99` | 5 | vivant, **1 seul consommateur** — `agents/factory.py:165-168` |
| `LogicAgentPlugin` | `logic_agent_plugin.py:44` | 8 | vivant (registre) — `registry_setup.py:382` |
| `TweetyResultInterpretationPlugin` | `tweety_result_interpretation_plugin.py:153` | 7 | vivant — `registry_setup.py:407`, `invoke_callables.py:9719` |
| `GovernancePlugin` | `governance_plugin.py:37` | 6 | vivant — `agents/factory.py:99-102`, `invoke_callables.py:1928` |
| `KBToTweetyPlugin` | `kb_to_tweety_plugin.py:313` | 5 | vivant — `registry_setup.py:444`, `invoke_callables.py:9564` |
| `NLToLogicPlugin` | `nl_to_logic_plugin.py:19` | 5 | vivant — `agents/factory.py:91-94` |
| `QualityScoringPlugin` | `quality_scoring_plugin.py:22` | 4 | vivant — `agents/factory.py:95-98` |
| `ATMSPlugin` | `atms_plugin.py:36` | 4 | vivant — `agents/factory.py:115-118` |
| `TextToKBPlugin` | `text_to_kb_plugin.py:201` | 3 | vivant — `registry_setup.py:426`, `invoke_callables.py:9484` |
| `NarrativeSynthesisPlugin` | `narrative_synthesis_plugin.py:660` | 3 | vivant — `agents/factory.py:156-159`, `invoke_callables.py:9031` |
| `FrenchFallacyPlugin` | `french_fallacy_plugin.py:21` | 3 | vivant — `agents/factory.py:83-86` |
| `BeliefRevisionPlugin` | `belief_revision_plugin.py:14` | 3 | vivant — `agents/factory.py:132-135` |
| `ExplorationPlugin` | `exploration_plugin.py:21` | 3 | vivant **en intra-paquet** — `fallacy_workflow_plugin.py:41,254,274` |
| `ASPICPlugin` | `aspic_plugin.py:14` | 2 | vivant — `agents/factory.py:128-131` |
| `RankingPlugin` | `ranking_plugin.py:16` | 2 | vivant — `agents/factory.py:124-127` |
| `FallacyWorkflowPlugin` | `fallacy_workflow_plugin.py:51` | 1 | vivant, surface la plus large — `registry_setup.py:253,299`, `invoke_callables.py:2853,5309,5751` |
| `ToulminPlugin` | `toulmin_plugin.py:17` | 1 | **déclaré sans implémentation, et monté nulle part** (#2145) — registre `agents/factory.py:160-163`, corps `NotImplementedError` `toulmin_plugin.py:43` |
| `JTMSSemanticKernelPlugin` | `semantic_kernel/jtms_plugin.py:36` | 5 | vivant (sous-paquet, fiche propre) — `api/jtms_endpoints.py:53` |

Non-classes porteuses de contrat : `identification_models.py` (2 modèles Pydantic, `:7`, `:39`), `kernel_input.py` (`parse_kernel_json_object:15`). Modèles Pydantic au total : **9** sur **3** modules (`identification_models.py` 2 ; `kb_to_tweety_plugin.py` 3 : `:27`, `:43`, `:52` ; `text_to_kb_plugin.py` 4 : `:26`, `:32`, `:40`, `:46`).

**Cinq collisions de noms enregistrés — mesurées** (quatre sur `formal_logic`, une sur `watson` ; #2145 a mesuré la cinquième, que le recensement d'origine ne nommait pas). Quatre noms de `@kernel_function` sont définis dans **deux** modules différents, avec des corps distincts :

| Nom enregistré | Site « enveloppe mince » | Site `tweety_logic_plugin` | Même spécialité d'agent ? |
|---|---|---|---|
| `analyze_aspic` | `aspic_plugin.py:25` | `tweety_logic_plugin.py:400` | oui (`formal_logic`, `agents/factory.py:60,66`) |
| `check_fol_consistency` | `logic_agent_plugin.py:200` | `tweety_logic_plugin.py:181` | oui (`agents/factory.py:60,68` **et** `watson` `:78`) |
| `rank_arguments` | `ranking_plugin.py:25` | `tweety_logic_plugin.py:264` | oui (`agents/factory.py:60,65`) |
| `revise_beliefs` | `belief_revision_plugin.py:24` | `tweety_logic_plugin.py:431` | oui (`agents/factory.py:60,67`) |

Aucun `name=` de décorateur ne renomme ces `def` : **0 écart** entre nom de `def` et kwarg `name=` sur l'ensemble du paquet (mesure AST). Les deux implémentations diffèrent réellement — `aspic_plugin.py:25-37` appelle `ASPICHandler.analyze_aspic_framework` sur un `json.loads` brut, sans normalisation ; `tweety_logic_plugin.py:400-418` passe par `parse_kernel_json_object` puis `json.dumps(..., default=str)` et porte `@_jvm_required`. **Conséquence mesurable : les deux côtés de chaque paire sont montés sur la même spécialité**, donc un agent `formal_logic` voit deux outils homonymes sous deux préfixes différents.

**Ce n'est plus silencieux (#2145).** La fabrique détecte la surface et la **rapporte** : `_plugin_function_names` (`agents/factory.py:176`) énumère les fonctions qu'un kernel tient réellement après montage, `_function_collisions` (`:202`) est **pure** — l'arbitrage peut être rejoué hors d'un kernel, ce qui est précisément ce qui le rend vérifiable — et `_report_function_collisions` (`:221`) émet un `WARNING` par nom homonyme depuis les deux voies de montage (`get_plugin_instances:251`, `load_plugins_for_agent:352`). Le garde `tests/unit/argumentation_analysis/agents/test_plugin_mount_health_2145.py` pin la surface entière dans `EXPECTED_COLLISIONS` : il rougit **dans les deux sens** — une collision nouvelle apparaît, ou une entrée listée disparaît (une entrée périmée doit être retirée à la main, jamais absorbée). Les cinq paires restent **dette nommée**, pas contrat : les deux côtés de chaque paire sont épinglés par des tests, donc aucun ne peut être supprimé sans arbitrage.

---

## Points d'entrée valides

| Entrée | Emplacement | Nature |
|---|---|---|
| Fabrique d'agents | `agents/factory.py:82-173` (`_PLUGIN_REGISTRY`, **17 entrées** vers ce paquet) → `:56-79` (`AGENT_SPECIALITY_MAP`) → `:352-433` (`load_plugins_for_agent`, montage `kernel.add_plugin` à `:384` et `:420`) ou `:251-349` (`get_plugin_instances`, pour `ChatCompletionAgent(plugins=…)`) | voie réelle de montage sur un kernel |
| Registre de capacités | `orchestration/registry_setup.py:363`, `:382`, `:407`, `:426`, `:444` (5 `register_plugin`) | déclaration, sans montage de kernel |
| Registre de capacités (service) | `registry_setup.py:253` et `:299` — `FallacyWorkflowPlugin` enregistré comme **service**, pas plugin (il exige un kernel + un LLM) | service |
| Services miroirs | `registry_setup.py:538-557` — `text_to_kb_service`, `kb_to_tweety_service`, `tweety_interpretation_service`, corps `type(name, (), {})` + `invoke=_invoke_*` | redéclaration en service |
| Harnais de benchmark | `evaluation/plugin_benchmark.py:447-500` (`PLUGIN_REGISTRY`, 13 entrées) | exécution hors run d'analyse |
| Routes API (sous-paquet) | `api/jtms_endpoints.py:53` ← `api/main.py` | seule entrée HTTP du paquet |
| Mode conversationnel | `orchestration/conversational_orchestrator.py:633` → `factory.get_plugin_instances` | montage par spécialité |

**Aucune entrée CLI.** Aucun `if __name__ == "__main__"` dans les 21 modules du premier niveau ; les 4 seuls gardes `__main__` de l'arbre sont dans `analysis_tools/logic/` (`complex_fallacy_analyzer.py:1580`, `contextual_fallacy_analyzer.py:951`, `fallacy_severity_evaluator.py:433`, `rhetorical_result_visualizer.py:533`), et aucun `argparse`/`click` n'existe dans le paquet.

**Une entrée qui ne mène nulle part** : `agents/core/plugin_loader.py` ne peut charger aucun module de ce paquet — voir *Limites connues* §4.

---

## Amont / aval

**Amont** — les handlers et services que les plugins enveloppent, jamais l'inverse. Les handlers Tweety sont importés **dans le corps de chaque `@kernel_function`**, pas au niveau module (ex. `tweety_logic_plugin.py:410`) : c'est ce qui rend le module importable sans JVM. Autres amonts : `services/jtms/` (sous-paquet), `agents/utils/taxonomy_navigator.py` (pour `ExplorationPlugin`), `agents/core/quality/quality_evaluator.py`, `agents/core/governance/social_choice.py`, et `core/models/toulmin_model.py` sous `TYPE_CHECKING` seulement (`toulmin_plugin.py:13-14`).

**Aval** — quatre familles, par volume :

1. **`agents/factory.py`** — 17 entrées de `_PLUGIN_REGISTRY` vers ce paquet, montées par spécialité.
2. **`orchestration/invoke_callables.py`** — les invokers : `governance_plugin` (`:1928`), `fallacy_workflow_plugin` (`:2853`, `:5309`, `:5751`), `narrative_synthesis_plugin` (`:9031`), `text_to_kb_plugin` (`:9484`), `kb_to_tweety_plugin` (`:9564`), `tweety_result_interpretation_plugin` (`:9719`).
3. **La restitution** — `narrative_synthesis_plugin`, par ses **fonctions de module** : `reporting/restitution/conclusion_salience.py:168`, `global_projection.py:74`, `specialist_roles.py:275` et `:336`, `core/shared_state.py:1546`, `agents/core/synthesis/deep_synthesis_agent.py:650`, `:699`, `:1460`.
4. **Le harnais** — `evaluation/plugin_benchmark.py`.

---

## Statut d'intégration

Le verdict n'est **pas homogène** : l'**enregistrement** est vivant, la **demande de capacité** ne l'est presque pas. Quatre régimes coexistent.

**a) Vivant par la fabrique.** 17 des 18 modules du premier niveau sont listés dans `_PLUGIN_REGISTRY` (`agents/factory.py:82-173`). **16** d'entre eux sont nommés par au moins une spécialité de `AGENT_SPECIALITY_MAP` (`:56-79`), soit **82** des 86 `@kernel_function` du premier niveau (mesuré après #2145) : le 17e, `toulmin`, est *enregistré mais monté nulle part* — arbitrage #2145, cf. §*Composants publics* et §*Limites connues* 2. Le 18e module, `exploration_plugin` (3 `@kernel_function`), n'a **aucune** entrée dans la fabrique — le commentaire `agents/factory.py:170` l'assume — et n'est atteint que par `fallacy_workflow_plugin.py:254,274` : **86 des 86** premiers niveaux sont donc montables, mais par deux chemins de nature différente.

**b) Vivant par le registre de capacités.** Les 5 `register_plugin` de `registry_setup.py:363-455` déclarent **12** capacités. En cherchant les littéraux `capability="…"` dans `argumentation_analysis/` (**48** littéraux distincts, **218** occurrences), **3 seulement** sont demandées par une phase :

| Capacité | Phase demandeuse |
|---|---|
| `nl_extraction` | `orchestration/workflows.py:978` |
| `kb_to_tweety` | `orchestration/workflows.py:985` |
| `formal_result_interpretation` | `orchestration/workflows.py:993`, `:1177` |

Les **9 autres** — `tweety_logic`, `propositional_reasoning`, `first_order_reasoning`, `modal_reasoning`, `dung_interpretation`, `argument_extraction`, `kb_construction`, `formula_translation`, `tweety_validation` — n'ont **aucun demandeur** : zéro occurrence en `capability="…"` dans tout `argumentation_analysis/`. Les trois services miroirs `registry_setup.py:538-557` redéclarent les mêmes listes, donc chacune de ces 9 capacités est déclarée **deux fois**.

Ce n'est pas un oubli silencieux : c'est une **dette tracée**. Le garde `tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py` pin la propriété « toute capacité déclarée a un demandeur de production » (`:156-171`) — mais son périmètre est `IN_SCOPE_COMPONENTS` (`:37-43`), qui ne contient **aucun** composant de ce paquet, et son docstring l'assume : « *Out of scope by design (#1842 ≠ #1604): the formal/Tweety specialists' declarations are not covered by guard 2 — their orphan census is #1604's* » (`:24-25`). **Le garde existe, il est vert, et il ne regarde pas ici.**

**c) Faux-vivant par homonymie de vocabulaire.** La fabrique `formal_logic` (`agents/factory.py:60-72`) monte `logic_agents` (`LogicAgentPlugin`) à côté de `tweety_logic` — or les deux ne parlent pas la même langue. `LogicAgentPlugin` déclare `propositional_reasoning`, `first_order_reasoning`, `modal_reasoning` (`registry_setup.py:385-389`), tandis que les phases réclament `propositional_logic` (`orchestration/workflows.py:194`), `fol_reasoning` (`:200`) et `modal_logic` (`:756`) — capacités servies par des **services distincts** (`registry_setup.py:468-483`, invokers `_invoke_propositional_logic` etc., défini à `orchestration/invoke_callables.py:6350`). Les deux vocabulaires ne se croisent **jamais**. Il en va de même pour `argument_extraction` (déclaré) face à `fact_extraction` (demandé, `collaborative_debate.py:356`). Un plugin « vivant » au sens du montage peut donc être fonctionnellement hors-circuit.

**d) Surface déclarée sans corps — et, depuis #2145, sans montage par la fabrique.** `toulmin_plugin.py` est enregistré (`agents/factory.py:160-173`) et benchmarké (`evaluation/plugin_benchmark.py:379`, registre `:496`). Son unique `@kernel_function` (`toulmin_plugin.py:23`, `def` `:27`) lève `NotImplementedError` dès la première instruction (`:43`) : tout appel échoue. #2145 en a tiré deux conséquences mesurées. **(1)** Le montage a été **retiré** de `informal_fallacy` et `extract` : offrir à un agent vivant un outil qui ne peut que lever, c'est lui vendre une promesse intenable et lui faire brûler un tour. Le plugin, son entrée de registre, son test d'épinglage du `raise` et son cas de benchmark restent tous en place — ce qui a été retiré est une *promesse*, pas un fichier. **(2)** La prémisse « aucun test ne porte sur ce module », que portait ce document, était **fausse** : `tests/unit/argumentation_analysis/plugins/test_tweety_plugins.py:289-296` **exécute** `analyze_argument` sous `pytest.raises(NotImplementedError, match="not yet implemented")`. Le mécanisme meurt donc *avec* un rouge, pas en silence — voir *Tests représentatifs*.

**Résidu nommé, hors du grain de #2145** : `agents/tools/analysis/new/semantic_argument_analyzer.py:25` monte encore `ToulminPlugin()` sur **son propre** kernel (`kernel.add_plugin(ToulminPlugin(), plugin_name="Toulmin")`), et son prompt (`:30`) instruit explicitement le LLM d'appeler `Toulmin.analyze_argument`. C'est un second chemin de montage, indépendant de la fabrique : retirer le nom de `AGENT_SPECIALITY_MAP` ne le ferme pas.

---

## Artefacts et lecteurs

**Aucun artefact de données.** Le paquet ne persiste rien : les 91 `@kernel_function` retournent des chaînes JSON, et l'écriture d'état est **déléguée** — `orchestration/state_writers.py:2285-2333` (`CAPABILITY_STATE_WRITERS`) associe capacité → écrivain, dont `nl_extraction:2327`, `kb_to_tweety:2329`, `formal_result_interpretation:2330`. Ce sont exactement les trois capacités que les phases demandent (`workflows.py:978,985,993`).

**Lecteurs humains** : `docs/architecture/PATTERN_NESTED_SK_KERNELS.md` (patron master/slave), `docs/architecture/CAPABILITY_DUALITY.md:32-40` (les plugins sur deux surfaces), `plugins/semantic_kernel/README.md` (fiche du sous-paquet) et `plugins/analysis_tools/logic/README.md`.

**Lecteur machine** : `evaluation/plugin_benchmark.py` — le seul code qui *exécute* les plugins hors d'un run d'analyse (`PLUGIN_REGISTRY:447-500`, `_instantiate_plugin:505`, `_create_instance:534`). Sa gestion d'échec est **silencieuse** : `except Exception` → `logger.warning` → `self._plugin_cache[name] = None` (`:529-532`) ; `fallacy_workflow` est en outre *volontairement* non instanciable (`:565`, `raise RuntimeError("FallacyWorkflowPlugin requires SK kernel setup")`). Un plugin cassé et un plugin non configurable produisent le même `None`.

---

## Tests représentatifs

```bash
pytest tests/unit/argumentation_analysis/plugins/ -o addopts= -v
```

**29** fichiers de test portent un segment de chemin `plugins/` — **27** sous `tests/unit/argumentation_analysis/plugins/` (dont 4 dans `analysis_tools/logic/`) et **2** ailleurs (`tests/orchestration/plugins/test_enquete_state_manager_plugin.py`, `tests/unit/core/plugins/test_plugin_loader.py`, ce dernier portant sur `agents/core/`, pas sur ce paquet). Les plus denses :

| `def test_` | Fichier |
|---|---|
| 76 | `tests/unit/argumentation_analysis/plugins/analysis_tools/logic/test_rhetorical_result_analyzer.py` |
| 55 | `tests/unit/argumentation_analysis/plugins/analysis_tools/logic/test_enhanced_contextual_fallacy_analyzer.py` |
| 46 | `tests/unit/argumentation_analysis/plugins/test_tweety_result_interpretation_plugin.py` |
| 44 | `tests/unit/argumentation_analysis/plugins/test_fallacy_workflow_plugin.py` |
| 41 | `tests/unit/argumentation_analysis/plugins/test_jtms_sk_plugin.py` |
| 31 | `tests/unit/argumentation_analysis/plugins/test_logic_agent_plugin.py` |
| 29 | `tests/unit/argumentation_analysis/plugins/test_text_to_kb_plugin.py` |
| 28 | `tests/unit/argumentation_analysis/plugins/test_kb_to_tweety_plugin.py` |

**Contrat mesuré ou chemin réel ?** Les deux, et la distinction est ici décisive.

- `tests/unit/argumentation_analysis/agents/test_plugins_active_in_kernel.py` (19 `def test_`, hors d'un chemin `plugins/`) mesure le **contrat d'enregistrement** : importabilité de chaque entrée de `_PLUGIN_REGISTRY`, instanciation sans argument, montage effectif des `@kernel_function` dans un `Kernel`, chargement par spécialité. C'est le contre-test réel de la déclaration, mais il valide le **montage**, pas l'**usage**.
- `tests/unit/argumentation_analysis/plugins/test_1773_kernel_input_convention.py` (13 `def test_`) garde la convention d'entrée partagée (`kernel_input.py:15`).
- **Le chemin réel est mesuré par un seul test — et ce document l'avait manqué (#2145).** La version antérieure de ce document affirmait qu'« aucun fichier de test ne porte sur `toulmin_plugin.py` » et que rien ne devenait rouge quand son corps lève : **c'était faux**. `tests/unit/argumentation_analysis/plugins/test_tweety_plugins.py:289-296` **exécute** `analyze_argument` et épingle le `raise` (`pytest.raises(NotImplementedError, match="not yet implemented")`). Les autres fichiers qui mentionnent « toulmin » (`evaluation/test_plugin_benchmark.py`, `agents/test_plugins_active_in_kernel.py`, `test_plugin_per_agent.py`, `test_conversational_orchestrator.py`) l'atteignent, eux, par la **déclaration**. La leçon instrumentale : un recensement par `grep` compte des *mentions*, pas des *exécutions* — lire le corps du test, pas son titre.
- **Les collisions sont désormais couvertes** : `tests/unit/argumentation_analysis/agents/test_plugin_mount_health_2145.py` pin la surface entière (`EXPECTED_COLLISIONS`) **et** le fait qu'elle est rapportée (`test_collisions_are_reported_loudly_2145`). Il rougit dans les deux sens — collision nouvelle, ou entrée listée devenue périmée. Il porte aussi un **contrôle positif** (`test_collision_detector_is_not_blind`) : un détecteur qui rend `[]` n'a rien prouvé s'il ne sait pas rendre non-vide.
- Les 9 capacités sans demandeur ne sont couvertes par aucun test **de ce paquet** : le garde qui en serait le lieu s'exclut explicitement (`test_one_capability_surface_1842.py:24-25`).

---

## Frères et parent

- **Parent** : `argumentation_analysis/` (README racine du dépôt). Le parent direct `plugins/` **n'a pas de README propre** — c'est ce fichier ; `plugins/semantic_kernel/README.md:43` l'actait déjà (« Parent : `plugins/` (sans README propre…) »).
- **Frères dans `argumentation_analysis/`** : `agents/` (le principal consommateur), `orchestration/` (registre de capacités + invokers + écrivains d'état), `core/capability_registry.py` (le mécanisme d'enregistrement), `services/` (JTMS/ATMS/LLM — les porteurs de service, distincts des plugins qui les enveloppent), `evaluation/` (le harnais).
- **Enfants** : `semantic_kernel/` (fiche propre, 1 plugin, 5 `@kernel_function`, route API dédiée — **ne pas confondre** avec `argumentation_analysis/integrations/semantic_kernel_integration.py`, autre montage, résiduel) et `analysis_tools/` (fiche propre : `logic/` + `plugin.py` + `manifest.json` + `tests/`).
- **Homonymes à ne pas confondre — un `grep plugin` les mesure indifféremment :**
  - **`argumentation_analysis/plugin_framework/`** — framework de plugins **séparé**, prédécesseur abandonné, avec **deux** chargeurs (`core/plugin_loader.py`, `core/plugins/plugin_loader.py`) qui cherchent des fichiers **`plugin_manifest.json`** (`core/plugins/plugin_loader.py:33`). Sans rapport avec `agents/core/plugin_loader.py`, qui cherche **`manifest.json`**.
  - **`argumentation_analysis/agents/plugins/`** et **`argumentation_analysis/orchestration/plugins/`** — deux autres répertoires nommés `plugins`, avec leurs propres fiches, hors de ce paquet.
  - `argumentation_analysis/agents/core/` contient ses propres `*_plugin.py` (`state_manager_plugin`, `SherlockAgentPlugin`) **hors** de ce paquet.

---

## Limites connues

Relevées pour la plupart **non corrigées** (lot documentaire). Trois d'entre elles — **1, 2 et 5** — ont été **corrigées par #2145** ; elles restent listées ici, avec leur statut, parce qu'un item retiré en silence serait indistinguable d'un item jamais relevé.

**Suivi** : les items **1, 2, 4, 5, 6, 7** sont portés par **#2145**. L'item **3** (capacités
déclarées sans phase demandeuse) est la dette **tracée** de **#1604** — le garde
`test_one_capability_surface_1842.py:24-25` s'en exclut explicitement par design.

1. ~~**4 collisions de noms enregistrés**, toutes entre deux plugins que la **même** spécialité `formal_logic` monte côte à côte … et aucun test ne les couvre.~~ → **CORRIGÉ (#2145)**. La mesure en a trouvé **cinq**, non quatre : la cinquième paire (`check_fol_consistency`, `tweety_logic` + `logic_agents`) se produit sur la spécialité **`watson`**, que le recensement d'origine ne nommait pas. La fabrique **détecte et rapporte** désormais la surface (`_report_function_collisions`, `agents/factory.py:221`, `WARNING` sur les deux voies de montage), et `test_plugin_mount_health_2145.py` la pin dans `EXPECTED_COLLISIONS` avec un contrôle positif. Les **implémentations** restent en collision : c'est de la dette *nommée*, arbitrée plus tard — les deux côtés de chaque paire étant épinglés par des tests, aucun ne peut être supprimé sans décision.
2. ~~**`toulmin_plugin.py` : surface déclarée sans corps.** Enregistré … assigné à `informal_fallacy` et `extract` … monté … **Zéro test** sur ce module : le mécanisme peut mourir sans qu'aucun rouge n'apparaisse.~~ → **CORRIGÉ (#2145)**, sur deux points distincts. (a) Le **montage** est retiré de `informal_fallacy` et `extract` : monter un outil dont le corps ne peut que lever offre une promesse intenable. Registre (`agents/factory.py:160-173`), test d'épinglage du `raise` et cas de benchmark restent — une promesse a été retirée, pas un fichier. Le couplage montage↔corps est tenu par `test_toulmin_mount_follows_its_body_2145`, qui rougit le jour où le corps est implémenté. (b) La prémisse « **zéro test** » était **fausse** : `tests/unit/argumentation_analysis/plugins/test_tweety_plugins.py:289-296` **exécute** `analyze_argument` sous `pytest.raises(NotImplementedError)`. **Résidu nommé, non corrigé** : `agents/tools/analysis/new/semantic_argument_analyzer.py:25,30` monte le plugin sur son propre kernel et dicte au LLM de l'appeler — un second chemin, indépendant de la fabrique.
3. **9 capacités déclarées sans phase demandeuse**, dont 3 (`nl_extraction`, `kb_to_tweety`, `formal_result_interpretation`) sont au contraire **demandées** et ont un écrivain d'état (`state_writers.py:2327,2329,2330`). Chacune des 9 est déclarée **deux fois** (`registry_setup.py:363-455` et `:538-557`). Le garde qui en serait le lieu s'exclut explicitement (`test_one_capability_surface_1842.py:24-25`, dette tracée #1604).
4. **`agents/core/plugin_loader.py` ne peut charger aucun plugin de ce paquet.** Il découvre les sous-répertoires portant un `manifest.json` (`:28-38`) puis exige `name`, `entrypoint_module`, `entrypoint_class` (`:67-72`). Le seul `manifest.json` du paquet, `plugins/analysis_tools/manifest.json`, porte `entry_point` (un **fichier**) et **aucun** `entrypoint_module`/`entrypoint_class` → `PluginManifestError` à la lecture. Il n'a par ailleurs **aucun appelant de production** (seuls deux fichiers de `tests/` l'exercent).
5. ~~**Configuration d'erreur silencieuse dans la fabrique.** … un plugin qui échoue … est journalisé en `_factory_logger.debug` et **disparaît** de la liste rendue.~~ → **CORRIGÉ (#2145)**. La mesure exhaustive de l'arbre pristine donne **sept** silences, pas un : **six** sites d'amputation journalisés en `_factory_logger.debug` — état partagé (`agents/factory.py:298`, `:388`), plugin non instanciable (`:340`, `:424`), plugin `fallacy_workflow` requis mais sans `llm_service` (`:328`, `:411`) — **plus un septième qui n'était pas silencieux mais *absent*** : `get_plugin_instances` faisait un `continue` nu sur un nom déclaré sans entrée de registre (pristine `:215-216`), là où son jumeau `load_plugins_for_agent` avertissait déjà (pristine `:285`). Le même échec était donc bruyant sur une voie et invisible sur l'autre. Les sept sont désormais en `WARNING` (`:298`, `:310`, `:328`, `:340`, `:388`, `:400`, `:411`, `:424`). Né-rouge **exécuté** : `test_broken_plugin_is_reported_not_swallowed_2145` et `test_declared_name_without_registry_entry_is_reported_2145` rougissent tous deux sur l'arbre pristine (0 `WARNING` émis). Le seul `debug` restant (`:286`) journalise le *succès* du plugin d'état de phase — chemin nominal, pas une amputation.
6. **Trois répertoires de prompts SK natifs sont résiduels.** `ExplorationPlugin/Explore/`, `GuidingPlugin/GuidingPlugin/`, `SynthesisPlugin/Synthesize/` (chacun `config.json` + `skprompt.txt`). Aucun `.py` ne les charge : leurs seules occurrences sont documentaires (`docs/architecture/DESIGN_PARALLEL_WORKFLOW.md`, `PARALLEL_WORKFLOW_VALIDATION.md:59,65`, `fallacy_consolidation_plan.md:255,259,263`, `fallacy_operational_plan.md:589`). **Leurs noms de répertoires collisionnent avec des classes vivantes** — `ExplorationPlugin` est aussi la classe de `exploration_plugin.py:21` ; `SynthesisPlugin` frôle `NarrativeSynthesisPlugin` (`narrative_synthesis_plugin.py:660`).
7. **Homonymie de vocabulaire déclaré/demandé** (§*Statut d'intégration* c) : `propositional_reasoning` / `first_order_reasoning` / `modal_reasoning` / `argument_extraction` n'ont aucun demandeur, tandis que leurs quasi-homologues `propositional_logic` / `fol_reasoning` / `modal_logic` / `fact_extraction` sont demandés et servis par d'autres composants.
8. **Tous les statuts de ce document sont des mesures statiques** (`git grep` sur les `.py` suivis + AST sur `argumentation_analysis/plugins/`). « Vivant » signifie *référencé ou monté par du code de production*, jamais *exécution observée*. Aucune couverture ligne n'a été mesurée ici.

---

*Provenance — 2026-09-11, branche `docs/readme/2088-parents`. Méthode : AST (`ast.FunctionDef` + décorateur se terminant par `kernel_function`, `ast.ClassDef`) et `wc -l` sur les 21 modules du premier niveau et l'arbre récursif ; `git grep` pour les consommateurs, les littéraux `capability="…"` et les chargeurs ; lecture directe des sites cités pour chaque ancre. Tous les chiffres et ancres ont été mesurés dans cette passe ; aucune affirmation reprise d'une fiche antérieure sans revérification. **Aucun fichier du dépôt modifié hors ce README.***

*Révision — 2026-09-14, `#2145`. Trois affirmations de la passe du 2026-09-11 étaient **fausses** et sont corrigées ci-dessus avec leur mesure : (a) « aucun test ne porte sur `toulmin_plugin.py` » — `tests/unit/argumentation_analysis/plugins/test_tweety_plugins.py:289-296` **exécute** `analyze_argument` ; un recensement par `grep` compte des mentions, pas des exécutions. (b) « les 4 collisions ne sont couvertes par aucun test » et « 4 collisions » — la fabrique les détecte et les rapporte désormais, et la mesure en trouve **cinq** (la cinquième sur `watson`). (c) « configuration d'erreur silencieuse … un plugin qui échoue » (au singulier, ancres `:234-240`/`:304-307`) — l'arbre pristine portait **sept** silences : six `debug` d'amputation plus un `continue` nu sur un nom sans entrée de registre, sans aucun log. Les ancres de `agents/factory.py` de tout le document ont été re-dérivées sur l'arbre modifié (`_PLUGIN_REGISTRY` `:82-173`, `AGENT_SPECIALITY_MAP` `:56-79`, `get_plugin_instances` `:251-349`, `load_plugins_for_agent` `:352-433`, montages `:384`/`:420`). Enfin la couverture par spécialité passe de **83** à **82** des 86 `@kernel_function` : le montage de `toulmin` est retiré, le plugin reste enregistré.*
