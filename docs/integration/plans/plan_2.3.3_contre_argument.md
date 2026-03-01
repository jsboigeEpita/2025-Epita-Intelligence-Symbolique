# Integration Plan: Agent de Generation de Contre-Arguments (2.3.3)

## 1. Sujet (resume spec professeur)

**Spec**: `docs/projets/sujets/2.3.3_Agent_Generation_Contre_Arguments.md` (29 KB)
**Etudiant**: leo.sambrook (PR #17, +5979 lignes, merge 2025-06-28)
**Niveau**: Avance

### Objectif pedagogique
Agent specialise dans la generation automatique de contre-arguments. Couvre toute la chaine : analyse structurelle de l'argument, identification des vulnerabilites, selection de strategie rhetorique, generation via LLM, validation logique via TweetyProject, et evaluation de la qualite.

### Fonctionnalites demandees par la spec
1. **Analyse d'argument** : extraction premisses/conclusion, classification type (deductif, inductif, abductif), score de confiance
2. **5 types de contre-arguments** : refutation directe, contre-exemple, explication alternative, remise en question premisses, reductio ad absurdum
3. **3+ strategies rhetoriques** : questionnement socratique, reductio, analogie contrastive
4. **Integration LLM** : generation de texte via modele de langage (GPT ou local)
5. **Validation TweetyProject** : formalisation en theorie de Dung, calcul extensions (grounded, complete), verification attaque valide
6. **Evaluation qualite** : pertinence, force logique, persuasivite, originalite, clarte

### Contraintes techniques spec
- Utiliser TweetyProject via JPype pour la validation formelle
- Interface Semantic Kernel (plugins, kernel.invoke)
- Pipeline modulaire (chaque etape est un outil/plugin independant)

---

## 2. Travail Etudiant (analyse PR + code)

### PR #17: +5979 lignes, Leo Sambrook

### Structure livree (26 fichiers Python)
```
2.3.3-generation-contre-argument/
  counter_agent/
    agent/
      counter_agent.py          <- Orchestrateur SK avec kernel.invoke() et plugins!
      definitions.py            <- Enums + dataclasses (CounterArgumentType, Argument, etc.)
      parser.py                 <- ArgumentParser (marqueurs francais)
      strategies.py             <- RhetoricalStrategies (5 strategies + prompts)
      orchestration/
        fallacy_workflow_orchestrator.py  <- Workflow 3 etapes avec asyncio.gather
      plugins/
        exploration_tool.py              <- SK plugin avec @kernel_function
        hypothesis_validation_tool.py    <- SK plugin validation hypotheses
        aggregation_tool.py              <- SK plugin agregation rapports
      utils/hybrid_decorator.py
    evaluation/
      evaluator.py              <- CounterArgumentEvaluator (5 criteres ponderes)
      metrics.py                <- Metriques additionnelles
    llm/
      llm_generator.py          <- Generateur LLM (hardcode gpt-3.5-turbo)
      prompts.py                <- Templates de prompts
    logic/
      tweety_bridge.py          <- TweetyBridge (JPype, Dung Theory, validation formelle)
      taxonomy.py               <- Taxonomie de sophismes
      validator.py              <- Validateur logique
    ui/
      web_app.py                <- Flask web UI
    tests/
      _disabled_test_counter_agent.py
  example.py
  run_app.py
```

### Decouverte critique
**Le code etudiant avait DEJA une integration SK !** Le fichier `agent/counter_agent.py` est un orchestrateur qui :
- Prend un `kernel: Kernel` en constructeur
- Utilise `kernel.add_plugin(instance, tool_name)` pour enregistrer les plugins
- Appelle `await kernel.invoke(plugin["function_name"], ...)` pour chaque etape
- A 3 plugins SK avec `@kernel_function` (exploration, validation hypotheses, agregation)
- Execute les validations en parallele avec `asyncio.gather()`

L'integration actuelle a **degrade** cette architecture en remplacant le kernel par un `llm_client` generique.

### Algorithmes/structures cles a preserver
| Composant | Fichier etudiant | Ce qu'il fait | Qualite |
|-----------|-----------------|---------------|---------|
| Definitions | `definitions.py` | 5 enums + 5 dataclasses | BON — fidele a la spec |
| Parser | `parser.py` | Extraction premisses/conclusion (marqueurs FR) | BON — heuristiques solides |
| Strategies | `strategies.py` | 5 strategies + prompts FR | BON — templates complets |
| Evaluator | `evaluator.py` | 5 criteres ponderes (0.25/0.25/0.20/0.15/0.15) | BON — poids raisonnables |
| SK Plugins | `plugins/*.py` | 3 plugins kernel_function | BON — pattern correct |
| Orchestrateur SK | `agent/counter_agent.py` | Workflow 3 etapes avec kernel | BON — pattern reference |
| TweetyBridge | `logic/tweety_bridge.py` | Validation Dung (grounded+complete) | MOYEN — JAR path hardcode, mais logique correcte |

### Bugs/problemes dans le code etudiant
- `llm_generator.py` : hardcode `gpt-3.5-turbo` avec cle API en dur
- `tweety_bridge.py` : cherche le JAR dans des chemins relatifs fragiles (devrait utiliser notre `jvm_setup.py`)
- `strategies.py` : `get_best_strategy()` essayait `values()` sur un dict de fonctions (bug fixe dans l'integration actuelle)
- `web_app.py` : Flask UI non necessaire
- `kernel.remove_all_plugins()` dans l'orchestrateur : dangereux si d'autres agents partagent le kernel

---

## 3. Etat Actuel dans le Tronc Commun

### Fichiers existants dans `argumentation_analysis/agents/core/counter_argument/`
| Fichier | Source | Etat |
|---------|--------|------|
| `definitions.py` | Adapte de `agent/definitions.py` | OK — enums/dataclasses fideles |
| `parser.py` | Adapte de `agent/parser.py` | OK — parsing FR preservee |
| `strategies.py` | Adapte de `agent/strategies.py` | OK — 5 strategies, bug corrige |
| `evaluator.py` | Adapte de `evaluation/evaluator.py` | OK — 5 criteres, poids identiques |
| `counter_agent.py` | **REECRIT** depuis zero | PROBLEME — classe nue, pas de BaseAgent/SK |
| `__init__.py` | Nouveau | OK — registration CapabilityRegistry |

### Ecarts critiques avec notre architecture
1. `CounterArgumentAgent` n'herite PAS de `BaseAgent(ChatCompletionAgent, ABC)`
2. N'utilise PAS Semantic Kernel (pas de `kernel.invoke()`, pas de plugins)
3. N'utilise PAS la communication multi-canal
4. N'est PAS cable dans `AgentFactory`, `bootstrap`, ou les orchestrateurs
5. LLM via `llm_client.chat.completions.create()` (OpenAI brut) au lieu de SK
6. **Les 3 plugins SK de l'etudiant ont ete perdus** (exploration, validation, agregation)
7. **La validation TweetyProject a ete perdue** (le TweetyBridge n'a pas ete integre)

### Ce qui fonctionne
- Le pipeline parse → vulnerabilites → strategie → generation → evaluation est correct
- Le fallback template quand LLM absent est un bon pattern a conserver
- Les 41 tests passent (mais testent la version standalone, pas l'integration SK)
- Registration CapabilityRegistry fonctionne

---

## 4. Plan de Consolidation

### Classification: **BaseAgent** avec plugins SK

### Fichiers cibles (refactoring en place)

| Fichier | Action | Detail |
|---------|--------|--------|
| `definitions.py` | GARDER TEL QUEL | Enums + dataclasses OK |
| `parser.py` | GARDER TEL QUEL | Parsing FR OK |
| `strategies.py` | GARDER TEL QUEL | 5 strategies OK |
| `evaluator.py` | GARDER TEL QUEL | 5 criteres OK |
| `counter_agent.py` | **RECRIRE** | BaseAgent + SK, delegue au parser/strategies/evaluator |
| `counter_argument_plugin.py` | **CREER** | Plugin SK natif (@kernel_function) |
| `__init__.py` | ADAPTER | Exporter `CounterArgumentAgent`, garder registration |

### Ce qu'on garde de l'etudiant
- **Toutes les definitions** (enums, dataclasses) — identiques a la spec
- **Le parser** (marqueurs FR, extraction premisses/conclusion, vulnerabilites)
- **Les strategies** (5 strategies rhetoriques + prompts + templates)
- **L'evaluateur** (5 criteres ponderes)
- **Le pattern orchestrateur SK** (pipeline en etapes via kernel.invoke) — s'inspirer du code etudiant original
- **Le fallback template** (de l'integration actuelle)

### Ce qu'on ecrit nous-memes
- **`CounterArgumentAgent(BaseAgent)`** : herite de BaseAgent, utilise kernel
  - `__init__(kernel, agent_name="CounterArgumentAgent", **kwargs)`
  - `setup_agent_components(llm_service_id)` : enregistre le plugin + fonctions semantiques
  - `invoke_single(messages)` : recoit ChatMessageContent, retourne analyse JSON
  - `get_agent_capabilities()` : declare counter_argument, vulnerability_detection, etc.
- **`CounterArgumentPlugin`** : plugin SK natif avec `@kernel_function`
  - `parse_argument(text) -> str` (JSON)
  - `identify_vulnerabilities(argument_json) -> str` (JSON)
  - `generate_counter_argument(argument_json, strategy) -> str` (texte)
  - `evaluate_counter_argument(original_json, counter_json) -> str` (JSON scores)

### Ce qu'on supprime/ecarte
- `llm_generator.py` — remplace par SK kernel.invoke avec fonctions semantiques
- `logic/tweety_bridge.py` — remplace par notre `core/jvm_setup.py` + `TweetyInitializer` existant (si validation Dung necessaire, reutiliser `abs_arg_dung`)
- `ui/web_app.py` — Flask UI, pas necessaire
- `run_app.py`, `example.py` — scripts demo
- Le pattern `llm_client.chat.completions.create()` — remplace par SK

### Decision sur TweetyBridge
La validation Dung formelle du code etudiant est interessante (modelise attaques selon le type de contre-argument, calcule extensions grounded/complete). Plutot que reimplementer un TweetyBridge, on peut :
1. Utiliser notre `abs_arg_dung` (DungAgent + EnhancedDungAgent) deja integre
2. Ajouter une methode `validate_with_dung(original, counter)` dans le plugin
3. Marquer comme optionnel (depends de JPype/JVM)

---

## 5. Cablage Architecture

### AgentFactory (`agents/factory.py`)
```python
def create_counter_argument_agent(self, **kwargs) -> CounterArgumentAgent:
    return self._create_agent(CounterArgumentAgent, **kwargs)
```

### CapabilityRegistry (conserver, mettre a jour)
```python
registry.register_agent(
    name="counter_argument_agent",
    agent_class=CounterArgumentAgent,   # maintenant un BaseAgent
    capabilities=["counter_argument_generation", "vulnerability_detection",
                   "argument_parsing", "rhetorical_strategy", "argument_evaluation"],
    metadata={"description": "Generates counter-arguments using 5 strategies + 5 evaluation criteria"},
)
```

### unified_pipeline.py
Corriger l'import : la classe sera bien `CounterArgumentAgent` (meme nom, pas de changement necessaire ici).

### Orchestrateurs
- `real_llm_orchestrator.py` : optionnel — ajouter le CounterArgumentAgent au pipeline d'analyse rhetorique
- Le DebateAgent (quand il sera consolide) pourra utiliser le CounterArgumentAgent via AgentGroupChat

### Plugins SK a creer
1. `CounterArgumentPlugin` — fonctions kernel natives (parse, vulnerabilities, generate, evaluate)
2. Fonctions semantiques — prompts LLM pour la generation (via PromptTemplateConfig)

### Tests a ecrire/adapter
1. **Tests BaseAgent** : verifier heritage, constructeur avec kernel, invoke_single
2. **Tests Plugin SK** : verifier que les @kernel_function sont appelables via kernel.invoke
3. **Tests pipeline** : bout-en-bout parse → vulnerabilites → strategie → generation → evaluation
4. **Tests fallback** : template generation quand LLM absent
5. **Tests regression** : les 41 tests existants doivent continuer a passer (adapter les imports)

---

## 6. Criteres d'Acceptation

- [ ] `CounterArgumentAgent` herite de `BaseAgent(ChatCompletionAgent, ABC)`
- [ ] Constructeur accepte `kernel: Kernel` et `agent_name: str`
- [ ] Implemente `get_agent_capabilities()`, `get_response()`, `invoke_single()`
- [ ] `setup_agent_components(llm_service_id)` enregistre le CounterArgumentPlugin
- [ ] Appels LLM via `kernel.invoke()` (pas de `llm_client.chat.completions.create`)
- [ ] Fallback template quand LLM indisponible
- [ ] Enregistre dans CapabilityRegistry via `register_with_capability_registry()`
- [ ] Cable dans `AgentFactory.create_counter_argument_agent()`
- [ ] Les 5 types de contre-arguments fonctionnent (DIRECT_REFUTATION, COUNTER_EXAMPLE, ALTERNATIVE_EXPLANATION, PREMISE_CHALLENGE, REDUCTIO_AD_ABSURDUM)
- [ ] Les 5 strategies rhetoriques fonctionnent
- [ ] Les 5 criteres d'evaluation fonctionnent avec les memes poids
- [ ] Tests passent (anciens adaptes + nouveaux BaseAgent)
- [ ] Zero regression sur la suite existante (2631 passed)
