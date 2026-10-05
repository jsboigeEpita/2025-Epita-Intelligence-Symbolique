# Module `argumentation_analysis` — analyse d'argumentation multi-agents

Paquet canonique du tronc commun (professeur). Tout le code production vit ici ;
le CLAUDE.md racine du dépôt (règles et conventions du dépôt) reste la référence
opérationnelle — ce README décrit l'organisation du paquet et la filiation de
ses sous-répertoires documentés.

## Rôle

Analyse collaborative de l'argumentation : agents spécialisés (extraction,
logique formelle, détection de sophismes informels, débat, contre-argumentation,
synthèse) coordonnés par plusieurs familles d'orchestrateurs, avec intégration
JVM/Tweety (raisonneur formel), Semantic Kernel (LLM orchestration), et
infrastructure d'évaluation à posteriori.

## Points d'entrée réels

| Point d'entrée | Commande / Route | Statut |
|---|---|---|
| **CLI multi-modes** ([`run_orchestration.py`](./run_orchestration.py)) | `python -m argumentation_analysis.run_orchestration --mode pipeline\|conversational\|hierarchical\|cluedo\|sherlock_modern` (l.370-386) | ACTIF — 5 modes mesurés, dispatch interne cité par [`orchestration/README.md`](./orchestration/README.md) |
| **CLI interactif Tkinter** ([`main_orchestrator.py`](./main_orchestrator.py)) | `python -m argumentation_analysis.main_orchestrator [--skip-ui --text-file <path>]` (l.72-91) | ACTIF — `--skip-ui` + `--text-file` requis ensemble (l.90-91) |
| **API FastAPI** (racine `api/`, hors de ce paquet) | `uvicorn api.main:app` | ACTIF — monte le router JTMS de [`api/`](./api/README.md) sous `/api/v1/jtms/*` |

Utilitaires racine : [`paths.py`](./paths.py) (chemins du projet),
[`utils.py`](./utils.py) (helpers transverses, 15 lignes).

## Structure des sous-répertoires documentés

24 sous-répertoires portent un README (filiation vérifiée dans l'ordre enfant →
parent, Epic #2088). Les tableaux ci-dessous citent chaque enfant **depuis son
README lu en entier** — jamais sur la foi de son nom.

### Familles d'orchestration et agents

| Répertoire | Rôle (cité depuis l'enfant) | README enfant |
|---|---|---|
| [`orchestration/`](./orchestration/README.md) | **5 familles vivantes** : pipeline déclaratif Lego (WorkflowExecutor), conversationnel (**2 orchestrateurs distincts**), hiérarchique bridge/delegation, Cluedo, sherlock_modern. Chaque famille avec point d'entrée mesuré et preuve d'intégration | [README](./orchestration/README.md) |
| [`agents/`](./agents/README.md) | Définitions des agents IA (extraction, logique FOL/modale/propositionnelle, JTMS, informel, débat, contre-argument, synthèse, gouvernance, qualité, oracle) — héritage `BaseAgent(ChatCompletionAgent)` | [README](./agents/README.md) |
| [`workflows/`](./workflows/README.md) | 8 macro-workflows déclaratifs (`build_X_workflow()` + `run_X()`), pure construction de DAG sans exécution propre. Distinct du catalogue `orchestration/workflows.py` (~20 workflows) | [README](./workflows/README.md) |

### Noyau et surfaces d'intégration

| Répertoire | Rôle (cité depuis l'enfant) | README enfant |
|---|---|---|
| [`core/`](./core/README.md) | Classes fondamentales : gestion d'état (`shared_state.py` — `RhetoricalAnalysisState`), intégration LLM (`llm_service.py`), JVM/Tweety (`jvm_setup.py`), configuration, `CapabilityRegistry`, communication multi-canaux. 25 `.py` + 6 sous-répertoires | [README](./core/README.md) |
| [`plugins/`](./plugins/README.md) | **21 modules SK** à plat, **86** `@kernel_function` réels (mesure AST — `grep -c` rend 88, 2 sont des docstrings), convention d'entrée partagée `kernel_input.parse_kernel_json_object` (21/21 fonctions tweety_logic, 5/5 kb_to_tweety, NON adoptée par logic_agent_plugin) | [README](./plugins/README.md) |
| [`api/`](./api/README.md) | Package JTMS-spécifique : router FastAPI monté par l'app racine sous `/api/v1/jtms/*`. **Disambiguïsation** : pas l'app générale (celle-ci = `api/` racine du dépôt) | [README](./api/README.md) |
| [`services/`](./services/README.md) | Services centralisés : accès extraits/sources, JTMS core (`jtms/jtms_core.py` — Belief/Justification/JTMS), cache, clients externes | [README](./services/README.md) |
| [`service_setup/`](./service_setup/README.md) | Initialisation des services dépendants (JVM, LLM, cache) | [README](./service_setup/README.md) |

### Traitement et analyse

| Répertoire | Rôle (cité depuis l'enfant) | README enfant |
|---|---|---|
| [`nlp/`](./nlp/README.md) | Utilitaires NLP (embeddings, tokenisation) | [README](./nlp/README.md) |
| [`models/`](./models/README.md) | Modèles de données Pydantic partagés | [README](./models/README.md) |
| [`pipelines/`](./pipelines/README.md) | Pipelines linéaires séquentiels (chaîne de montage). Distinction mesurée avec `orchestration/` (collaboration dynamique) | [README](./pipelines/README.md) |
| [`analytics/`](./analytics/README.md) | Calculs statistiques et analyse quantitative de texte | [README](./analytics/README.md) |
| [`reporting/`](./reporting/README.md) | Génération de rapports (restitution finale) | [README](./reporting/README.md) |
| [`visualization/`](./visualization/README.md) | Visualisations des résultats d'analyse | [README](./visualization/README.md) |

### Infrastructure et outillage

| Répertoire | Rôle (cité depuis l'enfant) | README enfant |
|---|---|---|
| [`config/`](./config/README.md) | Gestion de la configuration du paquet | [README](./config/README.md) |
| [`data/`](./data/README.md) | Taxonomies de sophismes (Argumentum), fixtures/mock pédagogiques, **corpus chiffré canonique**. Chaque fichier porte son lecteur réel mesuré (`git grep` du nom dans le code — jamais inféré) | [README](./data/README.md) |
| [`evaluation/`](./evaluation/README.md) | Benchmarks multi-modèles, juge LLM, minage de patterns, **utilitaires privacy critiques** (`opaque_id`, `sanitize_state`, `leak_patterns`). `results/` entièrement gitignoré (discipline dataset) | [README](./evaluation/README.md) |
| [`adapters/`](./adapters/README.md) | Adaptateurs externes | [README](./adapters/README.md) |
| [`cli/`](./cli/README.md) | Interface ligne de commande complémentaire | [README](./cli/README.md) |
| [`kernel/`](./kernel/README.md) | Surface Semantic Kernel partagée | [README](./kernel/README.md) |
| [`plugin_framework/`](./plugin_framework/README.md) | Framework de plugins (coquille retirée en #2102 §6) | [README](./plugin_framework/README.md) |
| [`ui/`](./ui/README.md) | Interfaces utilisateur | [README](./ui/README.md) |
| [`utils/`](./utils/README.md) | Utilitaires divers (taxonomy_loader, etc.) | [README](./utils/README.md) |
| [`webapp/`](./webapp/README.md) | Application web | [README](./webapp/README.md) |
| [`scripts/`](./scripts/README.md) | Scripts utilitaires internes au paquet | [README](./scripts/README.md) |

## Répertoires exclus (preuve)

Sous-répertoires de `argumentation_analysis/` **sans README**, avec la raison
mesurée :

| Répertoire | Contenu | Raison d'exclusion |
|---|---|---|
| `__pycache__/` | bytecode Python | généré |
| `mocks/` | `__pycache__/` seul | vide de source (mesuré 2026-10-06) |
| `results/` | `performance_tests/` seul | sorties d'exécution |
| `tests/` | `__pycache__/`, `functional/`, `resources/` | tests internes au paquet — la suite de référence vit à `tests/` racine du dépôt |
| `temp_downloads/` | vide | éphémère |
| `text_cache/` | fichiers `.txt` hashés | cache d'exécution |

## Liens transverses

- **CLAUDE.md racine du dépôt** — conventions, structure d'ensemble, points
  d'entrée de tout le dépôt (API racine, interface web, scripts, tests).
- [`docs/architecture/ORCHESTRATION_MODES.md`](../docs/architecture/ORCHESTRATION_MODES.md) —
  arbitraires d'usage et comparaison des modes d'orchestration (référencé par
  [`orchestration/README.md`](./orchestration/README.md)).
- [`docs/architecture/INTEGRATION_STRATEGY.md`](../docs/architecture/INTEGRATION_STRATEGY.md) —
  stratégie d'intégration et architecture Lego (référencé par le CLAUDE.md).

## Historique

Le README précédent (65 lignes) racontait un modèle d'orchestration obsolète
(pré-refonte #1962 et vagues ultérieures). Réécriture Epic #2088, après lecture
des 24 READMEs enfants (ordre obligatoire feuilles → racine).
