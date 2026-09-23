# Tests FOL (`FOLLogicAgent`)

Ce guide décrit les tests de la logique du premier ordre (FOL) qui existent dans le dépôt, et comment les lancer. Il ne nomme que des fichiers, classes et méthodes présents sur `main` (vérifié le 2026-09-23 sur `781e1c18`, #2442).

L'agent FOL est `FOLLogicAgent` (`argumentation_analysis/agents/core/logic/fol_logic_agent.py`). Aucune classe `FirstOrderLogicAgent` n'existe : c'est un ancien nom, encore présent dans d'autres documents.

## Où sont les tests

| Fichier | Ce qu'il vérifie | JVM réelle ? | Dans l'argv de la CI ? |
|---|---|---|---|
| `tests/unit/agents/test_fol_logic_agent.py` | configuration (`UnifiedConfig`, `PresetConfigs.authentic_fol()`), syntaxe générée, pipeline d'analyse avec un bridge doublé | non | oui (`tests/unit/`) |
| `tests/unit/argumentation_analysis/test_fol_logic_agent.py` | l'agent sur l'architecture `BaseLogicAgent` | non | oui |
| `tests/unit/argumentation_analysis/agents/core/logic/test_fol_handler.py` | repli du solveur quand le solveur externe (eprover/prover9) est absent (#949) | non | oui |
| `tests/unit/argumentation_analysis/agents/core/logic/test_fol_agent_verdict_2338.py` | un verdict FOL est propagé tel que calculé, jamais fabriqué (#2338) | non | oui |
| `tests/unit/argumentation_analysis/agents/core/logic/test_fol_lifecycle_and_dialect_2360.py` | cycle de vie sync et prompts au dialecte Semantic Kernel (#2360) | non | oui |
| `tests/unit/argumentation_analysis/agents/core/logic/test_fol_signature_predeclaration.py`, `test_fol_bool_constant_sanitizer.py`, `tests/unit/argumentation_analysis/test_fol_constant_predeclaration.py`, `tests/unit/argumentation_analysis/agents/test_fol_signature_extraction.py` | construction de la signature (sortes, constantes, prédicats) et réécriture des constantes `T`/`F` avant le parseur Tweety | non | oui |
| `tests/unit/argumentation_analysis/test_fol_2pass_pipeline.py`, `test_fol_solver_selector.py`, `test_formalagent_fol_default.py` | pipeline FOL en deux passes (#544), sélecteur `--fol-solver` (#900), traduction de l'agent formel où PL, FOL et modale sont à égalité (#1396) | non | oui |
| `tests/unit/argumentation_analysis/orchestration/test_fol_isolation_net_1630.py`, `test_fp6_fol_faillloud.py`, `test_track_b_fol_fail_loud_1278.py` | l'appel FOL de l'orchestration : verdict à trois états propagé (#1197), isolation par formule (#1630), contrat « vivant ou fail-loud » (#1278) | non | oui |
| **`tests/integration/workers/test_worker_fol_tweety.py`** | **l'agent contre le vrai Tweety** : formules acceptées par le parseur, incohérence `P(a)` / `!P(a)` détectée, inférence par implication universelle, gestion d'erreurs, stabilité | **oui** | oui (`tests/integration/workers/`) |
| `tests/integration/test_fol_pipeline_integration.py` (lance `workers/worker_fol_pipeline.py` dans un sous-processus) | pipeline FOL de bout en bout, JVM isolée | oui | **non** |
| `tests/integration/argumentation_analysis/agents/core/logic/test_fol_handler_config.py` | choix du solveur par `FOLHandler` pour la requête et la cohérence | non (doublures) | **non** |
| `tests/agents/core/logic/test_first_order_logic_agent_authentic.py` | initialisation de l'agent avec un bridge injecté | oui (`@pytest.mark.jpype`) | **non** (`tests/agents/` est hors argv, voir #1867) |

L'argv de la CI est la commande `pytest` du job `automated-tests` dans `.github/workflows/ci.yml`. Relisez-la avant de citer cette colonne : elle bouge.

## Lancer les tests

```bash
# Tests FOL sans JVM (jpype est remplacé par un mock)
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/agents/test_fol_logic_agent.py tests/unit/argumentation_analysis/agents/core/logic/ -q --disable-jvm-session

# Tests contre le vrai Tweety (JVM démarrée par la fixture de session)
conda run -n projet-is-roo-new --no-capture-output pytest tests/integration/workers/test_worker_fol_tweety.py -q -rs
```

- La JVM est démarrée une fois par session par la fixture `jvm_session` (`tests/conftest.py`). Aucune variable d'environnement n'est à positionner.
- `--disable-jvm-session` remplace `jpype` par un mock. `test_worker_fol_tweety.py` se saute alors en entier (`pytestmark` : « FOL-Tweety tests require real JVM »). Un run avec ce drapeau ne dit donc rien du vrai Tweety.
- Les JARs Tweety vivent sous `libs/tweety/` (non suivi par git). Un worktree neuf ne les a pas : copiez-les, sinon la JVM ne démarre pas.
- Avec `-n N` (pytest-xdist), `--disable-jvm-session` n'atteint pas les workers : ils tournent avec le vrai `jpype` et sans JVM (#2402). La CI lance la suite en série.
- `-rs` affiche la raison de chaque test sauté. Un fichier Tweety « vert » dont tous les tests sont sautés n'a rien vérifié.

Mesure du 2026-09-23 sur ai-01 (`projet-is-roo-new`, `main` `2ceae29e` plus le correctif de `validate_argument` de #2447) : `test_worker_fol_tweety.py` rend 19 passed, 0 skipped, avec la JVM (16 avant les tests ajoutés par #2447 : deux de requête, un de validation d'argument), et `tests/unit/agents/test_fol_logic_agent.py` rend 17 passed.

## Syntaxe FOL de Tweety

Le parseur FOL de Tweety (`FolParser`) n'accepte que la syntaxe ASCII, avec les sortes et les prédicats déclarés **avant** les formules :

```
human = {socrate, platon}
type(Man(human))
type(Mortal(human))

forall X: (Man(X) => Mortal(X))
Man(socrate)
```

| Opérateur | Syntaxe Tweety |
|---|---|
| pour tout / il existe | `forall X: (...)`, `exists X: (...)` |
| et / ou / non | `&&`, `\|\|`, `!` |
| implique / équivaut | `=>`, `<=>` |
| ou exclusif | `^^` |
| contradiction / tautologie | `+`, `-` |

La grammaire complète est recopiée en tête de `tests/integration/workers/test_worker_fol_tweety.py`. `FOLLogicAgent.unicode_to_ascii_fol()` convertit la notation Unicode (`∀`, `∃`, `∧`, `∨`, `→`, `¬`, `↔`) vers cette syntaxe. Une formule en notation Unicode envoyée telle quelle au parseur est rejetée.

## API utilisée par les tests

**Bridge** (`argumentation_analysis/agents/core/logic/tweety_bridge.py`) :

- `TweetyBridge().check_consistency(belief_set: str, logic_type: str = "propositional")`. La méthode est synchrone, et son type par défaut est **propositionnel** : pour la FOL, passez `"first_order"`. Sans ce paramètre, une base FOL part au parseur propositionnel, qui peut l'accepter et répondre `True` (mesuré sur l'exemple ci-dessus : `(True, 'PL knowledge base is consistent.')`). Elle rend `Tuple[Optional[bool], str]`, où `None` veut dire « non décidé » (reasoner absent, belief set illisible).
- `TweetyBridge().execute_fol_query(belief_set: str, query: str)` rend `Tuple[Optional[bool], str]`. `True` et `False` ne viennent que du reasoner. `None` veut dire « non vérifié » : pas d'initialiseur Tweety, belief set ou requête illisible, erreur du reasoner. Le message commence alors par `Degraded:` et donne la raison. Sur l'exemple ci-dessus :
  - `Mortal(socrate)` rend `(True, "Query 'Mortal(socrate)': entailed")` ;
  - `Mortal(platon)` rend `(False, "Query 'Mortal(platon)': not entailed")`. `platon` n'apparaît dans aucune formule, seulement dans la sorte `human` : le belief set garde la signature déclarée par le parseur, et la requête est analysée avec elle (#2447) ;
  - `Mortal(aristote)` rend `None`, car `aristote` n'est déclaré nulle part.
- `TweetyBridge().fol_handler` (`FOLHandler`, dans `fol_handler.py`) : `parse_fol_formula`, `create_belief_set_from_string`, `check_consistency`, `execute_fol_query`, `validate_formula_with_signature`.

Le bridge n'a pas de méthode d'initialisation propre à la FOL : la JVM est prise en charge par `jvm_setup.py` et la fixture de session.

**Agent** (`FOLLogicAgent`) : `setup_agent_components(llm_service_id)`, `analyze(text)` (rend un `FOLAnalysisResult`), `text_to_belief_set(text)`, `is_consistent(belief_set)`, `execute_query(belief_set, query)`, `validate_argument(premises, conclusion)`, et `BeliefSetBuilderPlugin` (`agent._builder_plugin`) pour construire un belief set par programme (`add_sort`, `add_predicate_schema`, `add_atomic_fact`, `add_negated_atomic_fact`, `add_universal_implication`, `build_tweety_belief_set`).

**Configuration** : `PresetConfigs.authentic_fol()` (`config/unified_config.py`) rend une configuration avec `LogicType.FOL`, `MockLevel.NONE` et l'agent `AgentType.FOL_LOGIC`, et `get_agent_classes()["fol_logic"]` vaut `"FOLLogicAgent"`.

`validate_argument(premises, conclusion)` vérifie que {prémisses} ∪ {`!(conclusion)`} est incohérent. Elle construit la signature, appelle `check_consistency(…, "first_order")`, et rend `True` (valide) ou `False` (le solveur a trouvé les prémisses compatibles avec la négation de la conclusion). Sans bridge, ou quand le solveur n'a pas décidé, elle lève `RuntimeError` avec la raison (#2447). Sur les prémisses de l'exemple (`forall X: (Man(X) => Mortal(X))`, `Man(socrate)`), `Mortal(socrate)` rend `True` et `Man(platon)` rend `False`.

## Limites connues

- `FOLLogicAgent.text_to_belief_set()` n'appelle pas le LLM : elle passe par la conversion heuristique `_basic_fol_conversion()`. `test_end_to_end_fol_syllogism_with_llm` passe donc sans aucune requête LLM (mesuré le 2026-09-23 : 0 requête au compteur d'egress, dont le contrôle de vivacité a tourné dans la même session), et l'inférence qu'il vise échoue au parseur sans faire échouer le test (elle n'est qu'un avertissement). Ce test ne vérifie pas la conversion par le LLM. Suivi dans #2447.
- `analyze()` ne rend `consistency_check` à `True` ou `False` que si un solveur a décidé. Sinon il vaut `None`, et `consistency_message` dit pourquoi (pas de bridge, solveur non décidé, erreur) (#2447). L'étape d'enrichissement par le LLM ajoute encore au résultat les `inferences`, les `errors` et la `confidence` du modèle sans les étiqueter : #2447.

## Historique

- Les anciens `tests/validation/test_fol_complete_validation.py` et `tests/migration/test_modal_to_fol_migration.py` sont archivés sous `tests/_archived/validation/` et `tests/_archived/migration/`. `scripts/run_fol_tests.py` n'existe plus.
- #2442 a retiré `tests/integration/workers/worker_fol_tweety.py` et son lanceur `tests/integration/test_fol_tweety_integration.py`. Le fichier worker n'était pas collecté (son nom ne suit pas `test_*.py`), il appelait une méthode d'initialisation FOL que le bridge n'a jamais eue, et ses tests Tweety se sautaient faute d'une variable `USE_REAL_JPYPE=true` que rien ne positionne. Chacun de ses 14 tests a un homonyme dans `tests/integration/workers/test_worker_fol_tweety.py`, qui les couvre contre le vrai Tweety.
