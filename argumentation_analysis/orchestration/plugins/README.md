# `orchestration/plugins/` — plugins SK d'enquête et de logique complexe

## Rôle et frontière

Deux plugins Semantic Kernel complémentaires des workflows d'orchestration : le gestionnaire d'état d'enquête (Cluedo/policière) et le plugin d'énigme d'Einstein. Sans `__init__.py` (namespace package implicite).

N'est **pas** la famille principale de plugins SK du dépôt — celle-ci est `argumentation_analysis/plugins/` (Tweety, gouvernance, sophismes français…). Les deux plugins d'ici vivent dans la chaîne Cluedo/énigmes, pas dans la surface Lego.

## Composants publics

### `EnqueteStateManagerPlugin` (`enquete_state_manager_plugin.py:27`)

Pont SK entre les agents d'enquête et l'état partagé (`BaseWorkflowState`/`EnquetePoliciereState`/`EnqueteCluedoState`). Toutes les fonctions retournent du JSON (str) ; chaque méthode spécialisée garde le type d'état par `isinstance` (erreur JSON sinon). **21 `@kernel_function`** (comptées sur les `def` décorés) :

- 6 de base : `add_task`:52, `get_task`:68, `update_task_status`:80, `get_tasks`:95, `designate_next_agent`:110, `get_designated_next_agent`:125 ;
- 11 policière : `get_case_description`:142 … `get_hypotheses`:373 ;
- 4 Cluedo : `get_cluedo_game_elements`:394, `get_cluedo_main_belief_set_id`:415, `propose_final_solution`:435, `faire_suggestion`:458 (embarque la logique de réfutation Watson, :469-494).

### `LogiqueComplexePlugin` (`logique_complexe_plugin.py:10`)

Plugin énigme d'Einstein wrappant `EinsteinsRiddleState` ; force la formalisation Tweety via garde-fous (clause ≥ 10 caractères :71, ≥ 3 clauses avant requête :91, validation syntaxique :189-207). **9 `@kernel_function`** : `get_enigme_description`:27, `get_contraintes_logiques`:51, `formuler_clause_logique`:68, `executer_requete_tweety`:86, `verifier_deduction_partielle`:104, `proposer_solution_complete`:133, `obtenir_progression_logique`:151, `generer_indice_complexe`:162, `valider_syntaxe_tweety`:183.

## Points d'entrée valides

**`EnqueteStateManagerPlugin` : monté en production par la chaîne Cluedo extended** —

- montage kernel : `cluedo_extended_orchestrator.py:233-234` (`add_plugin(state_plugin, "EnqueteStatePlugin")`, import :87-89) ;
- appelants de cet orchestrateur : `run_orchestration.py:814-819` (`--mode cluedo` → `run_cluedo_oracle_game`), `service_manager.py:81-83` (alias `CluedoOrchestrator`, lui-même consommé par `api/dependencies.py:3-4` et `pipelines/orchestration/__init__.py:21-22`), `cluedo_runner.py:8`, `pipelines/orchestration/orchestrators/specialized/cluedo_orchestrator.py:15`.

**`LogiqueComplexePlugin` : aucun monteur production** — le seul référent hors tests est `scripts/validation/orchestration_validation.py:344-345`, qui l'instancie **sans l'argument `state_instance` requis** : `TypeError` attrapée par le try/except (:357-358) — le « Test 8 » du script ne peut jamais passer, alors que le gabarit de rapport statique affiche « [OK] » (:527-528).

## Amont / aval

- Amont : `core/enquete_states`, `core/logique_complexe_states`, `semantic_kernel.functions.kernel_function`.
- Aval : la chaîne Cluedo (pour EnqueteStateManager) ; rien pour LogiqueComplexe.

## Statut d'intégration

- `EnqueteStateManagerPlugin` : **actif** — via la chaîne Cluedo extended ci-dessus. **Nuance de surface** : absent de `registry_setup.py` — c'est la surface conversationnelle `AgentGroupChat`, pas la surface Lego `add_phase(capability=…)` ; aucune capability de phase n'est servie par ce plugin.
- `LogiqueComplexePlugin` : **expérimental** — testé unitairement, monteur unique cassé (voir Points d'entrée), mention documentaire dans `docs/architecture/CAPABILITY_DUALITY.md:32` sans monteur en code.

## Artefacts et lecteurs

Aucune écriture disque — les deux plugins mutent l'état en mémoire uniquement ; logging préfixé `SK.`.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/orchestration/plugins/test_enquete_state_manager_plugin.py tests/unit/argumentation_analysis/orchestration/test_logique_complexe_plugin.py -v
```

- `test_enquete_state_manager_plugin.py` : 9 tests (initialisation policière/cluedo :48/:60, `get_case_description` :71, `add_task` :83, `get_cluedo_game_elements` :105, `designate_next_agent` :121, `add_identified_element` :149, `add_hypothesis` :175) — README dédié : `tests/orchestration/plugins/README.md` ;
- canary RA7 `tests/unit/argumentation_analysis/test_ra7_prompt_canaries.py:163-176` : asserte seulement que deux sets littéraux de noms sont non vides — n'invoque aucune fonction (garde très faible) ;
- `test_logique_complexe_plugin.py` : classes `TestLogiqueComplexePluginInit`:42, `TestGetEnigmeDescription`:59, `TestGetContraintesLogiques`:85, `TestFormulerClauseLogique`:108…

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne ni `plugins/`, ni le mode Cluedo. À distinguer de [`../../plugins/`](../../plugins/) (famille SK principale).

## Limites connues

- `orchestration/plugins/` sans `__init__.py` ;
- logique de réfutation Watson **dans le plugin** (accès direct à `belief_set_initial_watson` + parsing de chaînes `" n'est pas"`, :469-494) au lieu de l'état — mélange de couches ;
- `import random` intra-méthode + 5 indices codés en dur (`generer_indice_complexe`, :165-175) ;
- le script de validation instancie les 2 plugins sans leur état requis → test mort-né silencieusement « [OK] » (anomalie signalée en issue séparée) ;
- le canary RA7 ne garde rien (asserts tautologiques).
