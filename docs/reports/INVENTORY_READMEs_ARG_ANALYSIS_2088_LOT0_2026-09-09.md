# Inventaire README `argumentation_analysis/` — lot 0 (#2088)

**Date** : 2026-09-09 (rév. 2026-09-10 après revue coordinateur PR #2091) · **Branche** : `docs/2088-lot0-readme-inventory` · **Exécutant** : Claude Code @ myia-po-2025

## Méthode & reproductibilité

L'inventaire est produit par un instrument commité, `scripts/docs/inventory_argumentation_readmes.py`
(commande : `python scripts/docs/inventory_argumentation_readmes.py > rapport.md`).

- **Base = contenu suivi par git** (`git ls-files`), jamais le disque : les arbres vendorisés
  (`libs/`, `portable_jdk/`), caches locaux et résidus de cleanups (#2055) sont sur disque
  mais ne sont pas first-party.
- **Règle « substantiel » déclarée** : ≥ 3 fichiers suivis OU au moins un `.py`.
- **4 contrôles positifs** (exit 1 en cas d'échec), tous prouvables depuis un checkout
  propre sans contenu disque local :
  1. le répertoire documenté connu (`orchestration/`) est vu ;
  2. ≥ 5 substantiels sans README (l'instrument en voit 71) ;
  3. **exclusion vendorisée prouvée depuis git uniquement** : 0 fichier suivi sous
     `argumentation_analysis/libs` et `argumentation_analysis/portable_jdk`, et les règles
     `.gitignore` **versionnées** les couvrent (`argumentation_analysis/.gitignore:67`
     `libs/`, `.gitignore:145` `portable_jdk/`), évaluées par `check-ignore` sur un chemin
     descendant — un pattern directory-only (`libs/`) ne peut pas matcher un chemin
     inexistant (git devrait stat() le répertoire), la sonde fichier contourne le piège ;
  4. les arbres morts #2055 (`orchestration/engine/`, `orchestration/cluedo_components/`)
     sont absents de la base suivie.
- **Preuve de reproductibilité (né-rouge exécuté)** : rejeu dans un worktree propre dépourvu
  de `libs/`/`portable_jdk/` → contrôle 3 **FAIL** avec l'ancienne version (reproduit
  exactement l'audit coordinateur) ; rejeu au head corrigé → **4/4 PASS**.

## Chiffres clés

| Mesure | Valeur |
|---|---|
| Répertoires suivis (hors racine `argumentation_analysis/`) | **119** |
| Dont vendorisés suivis | **0** (preuve git-only ci-dessus) |
| First-party substantiels | **107** |
| Substantiels **SANS `README.md`** | **71** (l'issue estimait ≥ 26 — la mesure réelle est 71) |
| Avec `README.md` | **37** |
| README spécialisés (`README_*.md`) | 3 (dans 2 répertoires) |
| Liens cassés mesurés dans les 37 README | **26** |

## 1. Répertoires first-party substantiels (sortie brute de l'instrument)

| Répertoire | Prof. | Fichiers | `.py` | README.md | README_*.md |
|---|---|---|---|---|---|
| `adapters` | 1 | 4 | 4 | **NON** | — |
| `agents` | 1 | 10 | 8 | oui | — |
| `agents/channels` | 2 | 1 | 1 | **NON** | — |
| `agents/concrete_agents` | 2 | 1 | 1 | **NON** | — |
| `agents/core` | 2 | 5 | 4 | oui | — |
| `agents/core/abc` | 3 | 3 | 3 | **NON** | — |
| `agents/core/counter_argument` | 3 | 6 | 6 | **NON** | — |
| `agents/core/debate` | 3 | 7 | 7 | **NON** | — |
| `agents/core/extract` | 3 | 5 | 4 | oui | — |
| `agents/core/governance` | 3 | 7 | 7 | **NON** | — |
| `agents/core/informal` | 3 | 10 | 9 | oui | — |
| `agents/core/logic` | 3 | 41 | 39 | oui | — |
| `agents/core/oracle` | 3 | 10 | 10 | **NON** | — |
| `agents/core/pl` | 3 | 5 | 4 | oui | — |
| `agents/core/pm` | 3 | 6 | 5 | oui | — |
| `agents/core/political` | 3 | 2 | 2 | **NON** | — |
| `agents/core/quality` | 3 | 4 | 3 | **NON** | — |
| `agents/core/synthesis` | 3 | 5 | 5 | **NON** | — |
| `agents/docs` | 2 | 7 | 1 | oui | README_optimisation_informal.md, README_test_orchestration_complete.md |
| `agents/extract` | 2 | 1 | 1 | **NON** | — |
| `agents/plugins` | 2 | 3 | 3 | **NON** | — |
| `agents/templates/student_template` | 3 | 5 | 4 | oui | — |
| `agents/tools` | 2 | 2 | 1 | oui | — |
| `agents/tools/analysis` | 3 | 8 | 7 | oui | — |
| `agents/tools/analysis/new` | 3 | 6 | 5 | oui | — |
| `agents/tools/encryption` | 3 | 5 | 4 | **NON** | README_encryption_system.md |
| `agents/tools/support` | 3 | 1 | 1 | **NON** | — |
| `agents/utils` | 2 | 3 | 3 | **NON** | — |
| `agents/watson_jtms` | 2 | 8 | 8 | **NON** | — |
| `analytics` | 1 | 4 | 4 | **NON** | — |
| `api` | 1 | 4 | 4 | **NON** | — |
| `cli` | 1 | 2 | 2 | **NON** | — |
| `config` | 1 | 4 | 1 | oui | — |
| `core` | 1 | 26 | 25 | oui | — |
| `core/communication` | 2 | 13 | 12 | oui | — |
| `core/communication/tests` | 3 | 4 | 4 | **NON** | — |
| `core/integration` | 2 | 2 | 2 | **NON** | — |
| `core/interfaces` | 2 | 2 | 2 | **NON** | — |
| `core/models` | 2 | 1 | 1 | **NON** | — |
| `core/setup` | 2 | 2 | 2 | **NON** | — |
| `core/utils` | 2 | 23 | 23 | **NON** | — |
| `core/utils/tests` | 3 | 2 | 2 | **NON** | — |
| `data` | 1 | 11 | 0 | **NON** | — |
| `data/datasets/legacy_fixtures` | 3 | 4 | 0 | **NON** | — |
| `evaluation` | 1 | 23 | 23 | **NON** | — |
| `integrations` | 1 | 1 | 1 | **NON** | — |
| `kernel` | 1 | 2 | 2 | **NON** | — |
| `models` | 1 | 3 | 2 | oui | — |
| `nlp` | 1 | 2 | 2 | **NON** | — |
| `orchestration` | 1 | 37 | 36 | oui | — |
| `orchestration/hierarchical` | 2 | 5 | 4 | oui | — |
| `orchestration/hierarchical/interfaces` | 3 | 4 | 3 | oui | — |
| `orchestration/hierarchical/operational` | 3 | 7 | 6 | oui | — |
| `orchestration/hierarchical/operational/adapters` | 4 | 6 | 5 | oui | — |
| `orchestration/hierarchical/strategic` | 3 | 6 | 5 | oui | — |
| `orchestration/hierarchical/tactical` | 3 | 7 | 6 | oui | — |
| `orchestration/hierarchical/templates` | 3 | 5 | 4 | oui | — |
| `orchestration/operational` | 2 | 3 | 3 | **NON** | — |
| `orchestration/plugins` | 2 | 2 | 2 | **NON** | — |
| `pipelines` | 1 | 8 | 7 | oui | — |
| `pipelines/orchestration` | 2 | 2 | 1 | oui | — |
| `pipelines/orchestration/analysis` | 3 | 3 | 3 | **NON** | — |
| `pipelines/orchestration/config` | 3 | 2 | 2 | **NON** | — |
| `pipelines/orchestration/core` | 3 | 1 | 1 | **NON** | — |
| `pipelines/orchestration/execution` | 3 | 2 | 2 | **NON** | — |
| `pipelines/orchestration/orchestrators/specialized` | 4 | 2 | 2 | **NON** | — |
| `plugin_framework` | 1 | 2 | 2 | **NON** | — |
| `plugin_framework/agents` | 2 | 3 | 2 | oui | — |
| `plugin_framework/agents/personalities` | 3 | 1 | 1 | **NON** | — |
| `plugin_framework/benchmarking` | 2 | 2 | 2 | **NON** | — |
| `plugin_framework/core` | 2 | 4 | 4 | **NON** | — |
| `plugin_framework/core/plugins` | 3 | 4 | 3 | oui | — |
| `plugin_framework/core/plugins/standard` | 4 | 2 | 1 | **NON** | — |
| `plugin_framework/core/plugins/standard/external_verification` | 5 | 3 | 2 | **NON** | — |
| `plugin_framework/core/plugins/standard/taxonomy_explorer` | 5 | 3 | 2 | **NON** | — |
| `plugin_framework/core/plugins/workflows` | 4 | 1 | 1 | **NON** | — |
| `plugin_framework/core/services` | 3 | 1 | 1 | **NON** | — |
| `plugins` | 1 | 21 | 21 | **NON** | — |
| `plugins/analysis_tools` | 2 | 3 | 2 | **NON** | — |
| `plugins/analysis_tools/logic` | 3 | 7 | 7 | **NON** | — |
| `plugins/analysis_tools/tests` | 3 | 4 | 4 | **NON** | — |
| `plugins/semantic_kernel` | 2 | 2 | 2 | **NON** | — |
| `reporting` | 1 | 16 | 16 | **NON** | — |
| `reporting/restitution` | 2 | 20 | 20 | **NON** | — |
| `scripts` | 1 | 7 | 6 | oui | — |
| `service_setup` | 1 | 2 | 2 | **NON** | — |
| `services` | 1 | 21 | 20 | oui | — |
| `services/ai_shield` | 2 | 3 | 3 | **NON** | — |
| `services/ai_shield/layers` | 3 | 4 | 4 | **NON** | — |
| `services/jtms` | 2 | 5 | 5 | **NON** | — |
| `services/mcp_server` | 2 | 7 | 4 | oui | — |
| `services/mcp_server/tools` | 3 | 6 | 6 | **NON** | — |
| `services/web_api` | 2 | 6 | 5 | oui | — |
| `services/web_api/models` | 3 | 3 | 3 | **NON** | — |
| `services/web_api/routes` | 3 | 4 | 4 | **NON** | — |
| `services/web_api/services` | 3 | 7 | 7 | **NON** | — |
| `services/web_api/tests` | 3 | 3 | 3 | **NON** | — |
| `ui` | 1 | 9 | 8 | oui | — |
| `ui/extract_editor` | 2 | 3 | 2 | oui | — |
| `utils` | 1 | 36 | 35 | oui | — |
| `utils/core_utils` | 2 | 1 | 1 | **NON** | — |
| `utils/dev_tools` | 2 | 14 | 14 | **NON** | — |
| `utils/extract_repair` | 2 | 6 | 4 | oui | — |
| `utils/extract_repair/docs` | 3 | 2 | 1 | **NON** | — |
| `visualization` | 1 | 5 | 5 | **NON** | — |
| `webapp` | 1 | 2 | 2 | **NON** | — |
| `workflows` | 1 | 9 | 9 | **NON** | — |

(Préfixe `argumentation_analysis/` omis par ligne. Table identique à la sortie de
l'instrument — régénérer avec la commande ci-dessus.)

### First-party NON substantiels (classpath léger — pas de README exigé)

`agents/prompts` (1) · `agents/prompts/InformalFallacyAgent` (1) · `agents/prompts/ProjectManagerAgent` (1) ·
`agents/prompts/TaxonomyDisplayPlugin/DisplayBranch` (2) · `agents/templates` (1) · `evaluation/corpus` (2) ·
`plugin_framework/agents/simple_analyst` (1) · `plugin_framework/core/plugins/standard/taxonomy_explorer/data` (1) ·
`plugins/ExplorationPlugin/Explore` (2) · `plugins/GuidingPlugin/GuidingPlugin` (2) · `plugins/SynthesisPlugin/Synthesize` (2) ·
`webapp/config` (1) — soit **12 répertoires légers**.

## 2. Exclusions — preuve depuis git uniquement

- **0 répertoire vendorisé suivi** : `git ls-files` ne retourne aucun fichier sous
  `argumentation_analysis/libs/` ni `argumentation_analysis/portable_jdk/`, et les règles
  `.gitignore` **versionnées** couvrent ces racines (`argumentation_analysis/.gitignore:67`
  `libs/`, `.gitignore:145` `portable_jdk/`). Vérifié par rejeu dans un worktree propre où
  ces répertoires n'existent pas : contrôle PASS.
- **Signal machine local (hors base de preuve)** : sur la machine de travail, `libs/`
  (JDK 15/17, node v20 + arborescence npm, tweety/native) et `portable_jdk/` (JDK 17.0.2)
  occupent le disque non suivis ; `evaluation/results/`, `results/`, `temp_downloads/`,
  `text_cache/`, `tests/`, `mocks/` et les résidus #2055 (`orchestration/engine/`,
  `orchestration/cluedo_components/`) également. Cette liste varie par machine et ne
  participe à aucun contrôle.
- Coquilles « suivi (résiduel) » (ex. `agents/prompts/TaxonomyDisplayPlugin`,
  `pipelines/orchestration/orchestrators`) : dossiers dont les fichiers ont été déplacés —
  candidats nettoyage, pas inventaire.

## 3. Signaux automatiques sur les 37 README existants

Ces mesures sont des **signaux de relecture, pas des verdicts** — l'âge d'un README n'est
pas une preuve que son contenu est faux, et un contenu peut être faux sans lien cassé. Les
verdicts qualitatifs suivent en §4 (après lecture).

- **Dérive d'âge** (dernier commit README antérieur à la dernière activité du répertoire) :
  33/37 README dérivent, dont 2 de ≤ 7 jours (`orchestration` 3 j, `utils/extract_repair` 1 j).
- **Liens cassés** : 26 au total, concentrés sur 8 README — `agents` (9),
  `utils/extract_repair` (6), `agents/core/logic` (3), `agents/tools/analysis` (3),
  `agents/tools/analysis/new` (1), `hierarchical/interfaces` (1), `ui` (2),
  `ui/extract_editor` (1). (Liens `http(s)` exclus, ancres ligne-anchored déduites,
  jusqu'à 4 exemples affichés par README — le total est le nombre mesuré.)

Table brute (L = lignes ; âge = dernier commit README ; activité = dernier commit du répertoire) :

| README | L | Âge README | Activité rép. | Liens cassés |
|---|---|---|---|---|
| `agents/README.md` | 238 | 2026-05-01 | 2026-09-09 | **9** : ./tools/optimization/README.md, ./tools/encryption/README.md, ./runners/README.md, ./data/ … |
| `agents/core/README.md` | 30 | 2025-06-03 | 2026-09-09 | 0 |
| `agents/core/extract/README.md` | 107 | 2025-06-03 | 2026-02-16 | 0 |
| `agents/core/informal/README.md` | 33 | 2025-06-03 | 2026-09-06 | 0 |
| `agents/core/logic/README.md` | 43 | 2025-06-15 | 2026-09-03 | **3** : ../../abc/agent_bases.py:24, ../../abc/agent_bases.py:159, first_order_logic_agent.py:0 |
| `agents/core/pl/README.md` | 38 | 2025-06-03 | 2025-10-15 | 0 |
| `agents/core/pm/README.md` | 122 | 2025-06-04 | 2026-06-12 | 0 |
| `agents/docs/README.md` | 46 | 2025-06-03 | 2026-05-01 | 0 |
| `agents/templates/README.md` | 60 | 2025-06-03 | 2026-05-01 | 0 |
| `agents/templates/student_template/README.md` | 37 | 2026-05-01 | 2026-05-01 | 0 |
| `agents/tools/README.md` | 47 | 2025-06-03 | 2026-06-10 | 0 |
| `agents/tools/analysis/README.md` | 102 | 2025-06-03 | 2026-06-10 | **3** : ./enhanced/README.md ×2, ../../tests/tools/README.md |
| `agents/tools/analysis/new/README.md` | 179 | 2025-06-03 | 2026-06-10 | **1** : ../enhanced/README.md |
| `config/README.md` | 72 | 2025-06-03 | 2026-08-31 | 0 |
| `core/README.md` | 115 | 2025-07-19 | 2026-09-07 | 0 |
| `core/communication/README.md` | 16 | 2025-06-21 | 2026-09-05 | 0 |
| `models/README.md` | 68 | 2026-09-05 | 2026-09-05 | 0 |
| `orchestration/README.md` | 50 | 2026-09-06 | 2026-09-09 | 0 |
| `orchestration/hierarchical/README.md` | 75 | 2025-06-21 | 2026-08-17 | 0 |
| `…/hierarchical/interfaces/README.md` | 87 | 2025-06-03 | 2026-07-26 | **1** : ../../../../core/communication/README.md |
| `…/hierarchical/operational/README.md` | 22 | 2025-06-21 | 2026-07-16 | 0 |
| `…/hierarchical/operational/adapters/README.md` | 126 | 2025-06-03 | 2026-06-02 | 0 |
| `…/hierarchical/strategic/README.md` | 21 | 2025-06-21 | 2026-08-17 | 0 |
| `…/hierarchical/tactical/README.md` | 22 | 2025-06-21 | 2026-08-14 | 0 |
| `…/hierarchical/templates/README.md` | 65 | 2025-06-03 | 2026-02-14 | 0 |
| `pipelines/README.md` | 29 | 2025-06-21 | 2026-09-09 | 0 |
| `pipelines/orchestration/README.md` | 21 | 2025-06-21 | 2026-08-04 | 0 |
| `plugin_framework/agents/README.md` | 33 | 2026-02-25 | 2026-02-25 | 0 |
| `plugin_framework/core/plugins/README.md` | 42 | 2026-02-25 | 2026-06-10 | 0 |
| `scripts/README.md` | 102 | 2026-09-03 | 2026-09-03 | 0 |
| `services/README.md` | 210 | 2025-06-03 | 2026-09-06 | 0 |
| `services/mcp_server/README.md` | 54 | 2026-02-25 | 2026-09-01 | 0 |
| `services/web_api/README.md` | 66 | 2025-06-21 | 2026-08-24 | 0 |
| `ui/README.md` | 229 | 2025-06-03 | 2026-08-25 | **2** : ../../scripts/embed_all_sources.py, ./extract_editor/extract_marker_editor.ipynb |
| `ui/extract_editor/README.md` | 172 | 2025-06-03 | 2026-08-25 | **1** : ./extract_marker_editor.ipynb |
| `utils/README.md` | 30 | 2025-06-15 | 2026-09-06 | 0 |
| `utils/extract_repair/README.md` | 288 | 2026-09-03 | 2026-09-04 | **6** : ./repair_extract_markers.py, ./verify_extracts.py, ./docs/repair_report.html, ./docs/verify_extracts_report.html … |

## 4. Classification qualitative — verdicts après lecture

Chaque README a été lu et ses affirmations saillantes recoupées contre l'arbre réel
(fichiers, symboles, chemins). Définitions déclarées :

- **courant** : les éléments décrits (fichiers, classes, structure, procédures) ont été
  recoupés présents et exacts ;
- **partiel** : le noyau décrit est exact mais le périmètre réel est plus large (briques
  non couvertes) ou des chemins cités sont erronés de façon réparable ;
- **périmé** : le README décrit des chemins, scripts ou procédures qui **n'existent plus**
  dans l'arbre suivi — le lecteur est activement trompé ;
- **spécialisé seulement** : pas de `README.md` mais un `README_*.md` thématique.

| README | Verdict | Raison vérifiable (recoupement fait) |
|---|---|---|
| `agents/` | **périmé** | 9 liens cassés ; `tools/optimization/` et `runners/` cités n'existent pas dans l'arbre suivi (ls : `analysis`, `encryption`, `support` seulement) ; l'inventaire des familles d'agents listées couvre 4 des 16 feuilles réelles |
| `agents/core/` | partiel | liste 4 familles (pm, informal, pl, extract) sur 13 présentes (abc, counter_argument, debate, governance, logic, oracle, political, quality, synthesis absentes de la liste) |
| `agents/core/extract/` | courant | les 3 fichiers décrits (`extract_agent.py`, `extract_definitions.py`, `prompts.py`) existent tels quels — description complète pour un répertoire de 4 fichiers |
| `agents/core/informal/` | partiel | décrit 2 fichiers ; le module en porte 8 `.py` non couverts (`taxonomy_sophism_detector.py`, `dung_arbitration_stage.py`, `neuro_symbolic_arbitrator.py`, `detection_candidate_bridge.py`…) ; exemple d'import préfixé `agents.` obsolète |
| `agents/core/logic/` | partiel | hiérarchie et composants exacts (BaseAgent/BaseLogicAgent, 3 agents, TweetyBridge, BeliefSet) ; 3 liens erronés d'un niveau (`../../abc/…` alors que abc/ est sous core/, pas sous agents/) |
| `agents/core/pl/` | partiel | rôle et BNF exacts ; mais `PLAnalyzer` cité vit désormais dans `core/logic/propositional_logic_agent.py` (grep) — la fiche ne reflète pas la répartition pl/↔logic/ |
| `agents/core/pm/` | courant | `prompt_define_tasks_v11` présent (2 occurrences dans `prompts.py`), `pm_definitions.py` présent — workflow décrit recoupé |
| `agents/docs/` | partiel | notice générique « reports/ » ; le contenu réel = 2 docs spécialisés (README_optimisation_informal, README_test_orchestration_complete) non distingués |
| `agents/templates/` | courant | structure standard template toujours en place (`student_template/` conforme) |
| `agents/templates/student_template/` | courant | les 4 fichiers du template décrits (`agent.py`, `definitions.py`, `prompts.py`, `__init__.py`) existent |
| `agents/tools/` | **périmé** | section « optimization/ » : ce répertoire n'existe plus dans l'arbre suivi (ls réel : analysis, encryption, support) |
| `agents/tools/analysis/` | **périmé** | `enhanced/` cité (liens ×2) n'existe pas ; `rhetorical_result_analyzer.py` cité absent (seul `rhetorical_result_visualizer.py` présent) |
| `agents/tools/analysis/new/` | **périmé** | lien `../enhanced/README.md` : `enhanced/` n'existe pas |
| `config/` | partiel | l'arbre montré (` .env.template` + README) ne couvre pas les 4 fichiers suivis réels |
| `core/` | courant | piliers décrits recoupés présents (`shared_state.py`, `state_manager_plugin.py`, llm/jvm) — les 26 fichiers du répertoire tournent autour de ces piliers |
| `core/communication/` | partiel | concepts (Message/Channel/Pub-Sub) exacts ; `LocalChannel`/`local_channel.py` cité comme implémentation de référence : le fichier n'existe pas (seul `channel_interface.py` recoupé) |
| `models/` | courant | `extract_definition.py` présent, structure conforme (3 fichiers) |
| `orchestration/` | courant | pilote §6 : modes CLI, DSL, registry, writers tous prouvés par appelants file:line |
| `orchestration/hierarchical/` | partiel | architecture 3 couches exacte (strategic/tactical/operational présents) ; les sous-modes `bridge`/`delegation` et `hierarchy_bridge.py` (RA-10 #1069) ne sont pas couverts |
| `…/hierarchical/interfaces/` | partiel | `strategic_tactical.py` + `tactical_operational.py` présents conformes ; 1 lien erroné d'un niveau vers core/communication |
| `…/hierarchical/operational/` | courant | `manager.py`, `adapters/`, registre de capacités décrits — tous recoupés présents |
| `…/hierarchical/operational/adapters/` | courant | les 4 adaptateurs décrits (`extract`, `informal`, `pl`, `rhetorical_tools`) existent exactement |
| `…/hierarchical/strategic/` | courant | `manager.py`, `planner.py`, `allocator.py` décrits = présents |
| `…/hierarchical/tactical/` | courant | `manager.py`/`coordinator.py`, `monitor.py`, `resolver.py` décrits = présents |
| `…/hierarchical/templates/` | courant | les 4 templates décrits (`agent`, `analysis_tool`, `analysis_type`, `strategy`) existent |
| `pipelines/` | courant | la distinction pipelines vs orchestration décrite est conforme (le moteur vit bien dans `pipelines/orchestration/execution/engine.py`) |
| `pipelines/orchestration/` | courant | structure décrite recoupée intégralement : `analysis/`, `config/`, `core/`, `execution/engine.py` + `strategies.py`, `orchestrators/` |
| `plugin_framework/agents/` | **périmé** | le mécanisme décrit scanne « `src/agents` » — `src/` racine n'existe plus (consolidation #321) ; les loaders existent mais l'arbre décrit est faux |
| `plugin_framework/core/plugins/` | **périmé** | même défaut : scan de « `src/core/plugins/` » disparu |
| `scripts/` | **périmé** | les 2 scripts décrits (`repair_extract_markers.py`, `verify_extracts.py`) ne sont pas ceux du répertoire (contenu réel : `run_fix_missing_first_letter.py`, `run_verify_extracts_llm.py`, `simulate_balanced_participation.py`, `test_performance_extraits.py`) |
| `services/` | partiel | noyau décrit exact (cache, crypto, definition, extract présents) ; la périphérie réelle non couverte (21 fichiers : `benchmark_service.py`, `fact_verification_service.py`, jtms/, local_llm, speech, web_api, mcp_server) |
| `services/mcp_server/` | courant | `Dockerfile`, `main.py`, `tools/` recoupés présents — procédure docker conforme |
| `services/web_api/` | **périmé** | procédure de lancement via `scripts/launch_webapp_background.py` : ce fichier n'existe pas |
| `ui/` | **périmé** | 2 liens cassés dont la source d'amorçage `../../scripts/embed_all_sources.py` disparue ; le notebook cité absent |
| `ui/extract_editor/` | **périmé** | l'outil central décrit `extract_marker_editor.ipynb` n'est pas dans l'arbre suivi (liens cassés) |
| `utils/` | partiel | notice de 30 lignes face à 35 `.py` réels (`dev_tools/` 14, `extract_repair/`, `core_utils/` non couverts) |
| `utils/extract_repair/` | **périmé** | les scripts décrits ont été renommés (`repair_extract_markers.py`/`verify_extracts.py` → `fix_missing_first_letter.py`/`verify_extracts_with_llm.py`/`marker_repair_logic.py`) ; 6 liens cassés |

**Spécialisé seulement** : `agents/tools/encryption` (README_encryption_system.md sans
`README.md`) — promouvable en README.md lors de son lot.

**Bilan** : 15 courants · 11 partiels · 11 périmés (37). Les 11 périmés trompent activement
le lecteur (chemins/scripts/procédures morts) — ils sont prioritaires sur les partiels pour
la rénovation, et les 26 liens cassés vivent presque tous dedans.

## 5. DAG enfants → parents et ordre topologique des lots

Règle de l'Epic #2088 : un README **parent** s'écrit après ceux de ses enfants — il doit
pouvoir pointer vers des README enfants existants. Un nœud est *prêt* quand tous ses enfants
substantiels sont documentés ou exclus.

### Graphe de dépendances (71 sans README + parents concernés)

Chaque ligne : `enfant → parent` (le parent est bloqué tant que l'enfant n'est pas couvert).

```
# sous agents/ (README parent existe mais périmé — rénovation après les feuilles)
agents/core/abc, /counter_argument, /debate, /governance, /oracle, /political,
  /quality, /synthesis, agents/channels, /concrete_agents, /extract, /plugins,
  /tools/encryption (promouvable), /tools/support, /utils, /watson_jtms   → agents/
# sous core/
core/communication/tests, core/integration, core/interfaces, core/models,
  core/setup, core/utils, core/utils/tests                                → core/
# sous orchestration/
orchestration/operational, orchestration/plugins                           → orchestration/
# sous pipelines/
pipelines/orchestration/analysis, /config, /core, /execution,
  /orchestrators/specialized                                              → pipelines/orchestration/ → pipelines/
# sous plugin_framework/
plugin_framework/agents/personalities, /benchmarking, /core, /core/plugins/standard,
  /core/plugins/standard/external_verification, /core/plugins/standard/taxonomy_explorer,
  /core/plugins/workflows, /core/services                                 → plugin_framework/
# sous plugins/
plugins/analysis_tools, /analysis_tools/logic, /analysis_tools/tests,
  plugins/semantic_kernel                                                 → plugins/
# sous reporting/
reporting/restitution                                                     → reporting/
# sous services/
services/ai_shield, /ai_shield/layers, /jtms, /mcp_server/tools,
  /web_api/models, /web_api/routes, /web_api/services, /web_api/tests      → services/
# sous utils/
utils/core_utils, /dev_tools, /extract_repair/docs                        → utils/
# sous data/
data/datasets/legacy_fixtures                                             → data/
# racines SANS enfant substantiel (feuilles au sens du DAG)
adapters, analytics, api, cli, evaluation, integrations, kernel, nlp,
  service_setup, visualization, webapp, workflows                          → (aucun parent interne)
```

### Vagues topologiques

| Vague | Contenu | Effectif |
|---|---|---|
| **V1 — feuilles** | 55 feuilles sous racines + 12 racines-orphelines (sans enfant substantiel) | **67** |
| **V2 — parents sans README** | `data`, `plugin_framework`, `plugins`, `reporting` — chacun n'a plus que des enfants V1 (ou déjà documentés : `plugin_framework/agents`) | **4** |
| **V3 — rénovation des parents existants** | les 22 README non courants (11 périmés + 11 partiels), réécrits après que leurs feuilles existent | **22** |

Fermeture vérifiée : 67 + 4 = 71 sans README ✓ ; V3 couvre les 37 − 15 courants = 22 ✓.

## 6. Lots proposés (découpe des vagues en tranches livrables)

| Lot | Vague | Contenu | Blocage |
|---|---|---|---|
| **A1** | V1 | 16 feuilles `agents/` + promotion `tools/encryption` | aucun |
| **A2** | V1 | 8 feuilles `services/` (ai_shield ×2, jtms, mcp_server/tools, web_api ×4) | aucun |
| **A3** | V1 | 8 feuilles `plugin_framework/` + 7 feuilles `core/` | aucun |
| **A4** | V1 | 5 feuilles `pipelines/orchestration/` + 2 `orchestration/` | aucun |
| **A5** | V1 | 4 feuilles `plugins/` + `reporting/restitution` + `data/datasets/legacy_fixtures` | aucun |
| **A6** | V1 | 12 racines-orphelines (`adapters`, `analytics`, `api`, `cli`, `evaluation`, `integrations`, `kernel`, `nlp`, `service_setup`, `visualization`, `webapp`, `workflows`) | aucun |
| **B1** | V2 | README parents `plugins`, `reporting` | bloqué sur A5 |
| **B2** | V2 | README parents `data`, `plugin_framework` | bloqué sur A5 (data) / A3 (plugin_framework) |
| **C1** | V3 | rénovation des 11 **périmés** (`agents`, `agents/tools`, `analysis` ×2, `plugin_framework/agents`, `plugin_framework/core/plugins`, `scripts`, `web_api`, `ui` ×2, `extract_repair`) — répare au passage les 26 liens cassés | bloqué sur les lots A/B couvrant leurs enfants |
| **C2** | V3 | rénovation des 11 partiels | après C1 |

Chaque lot est indépendant au sein de sa vague ; l'ordre A → B → C respecte le DAG.

## 7. Pilote — sous-arbre `orchestration/` (sans modifier son README)

DoD #2088 : « les statuts d'intégration sont étayés par des appelants, routes, workflows ou
tests — **jamais inférés du nom** ». Chaque ligne ci-dessous cite les preuves.

### Cartographie des 8 README du sous-arbre

| README | Lignes | Verdict (§4) | Liens cassés |
|---|---|---|---|
| `orchestration/README.md` | 50 | courant | 0 |
| `orchestration/hierarchical/README.md` | 75 | partiel (sous-modes non couverts) | 0 |
| `…/hierarchical/interfaces/README.md` | 87 | partiel (1 chemin erroné) | 1 |
| `…/hierarchical/operational/README.md` | 22 | courant | 0 |
| `…/hierarchical/operational/adapters/README.md` | 126 | courant | 0 |
| `…/hierarchical/strategic/README.md` | 21 | courant | 0 |
| `…/hierarchical/tactical/README.md` | 22 | courant | 0 |
| `…/hierarchical/templates/README.md` | 65 | courant | 0 |

### Statuts d'intégration prouvés

**Modes d'orchestration (assertion : 4 modes exécutables).** Preuves :
`run_orchestration.py:363-373` — `--mode` entre `pipeline|conversational|hierarchical|cluedo`,
défaut `pipeline` ; descriptions `:375-377` ; mode hiérarchique sous-mode `--hierarchical-mode`
`{bridge,delegation}` défaut `bridge` `:381-387` ; aiguillage `elif mode == "hierarchical"`
`:714`. Le README orchestration (50 lignes, fraîcheur 3 j) reflète l'état du code.

**Pipeline / Lego (assertion : DAG de phases exécutées par le registry).** Preuves :
`orchestration/workflow_dsl.py:254` `add_phase(capability=…)`, `:326` `build()` ;
`orchestration/workflows.py:236` et `:311` phases `capability="adversarial_debate"` des
workflows standard/full (les phases *consomment* des capacités — ce sont les demandeurs que
« requested » définit, cf. garde #1842) ; `orchestration/registry_setup.py:73` `setup_registry()` ;
`orchestration/unified_pipeline.py:138` `run_unified_analysis()`.
Checkpoints : `unified_pipeline.py:146,166,338` et `workflow_dsl.py:377,401` — callback
`checkpoint_callback` propagé au `WorkflowExecutor`.

**Conversationnel (assertion : dialogue multi-agents SK).** Preuves :
`analysis_runner_v2.py:50` — `AgentGroupChat` importé de
`semantic_kernel.agents.group_chat.agent_group_chat` ; `:313-317` construction du
`group_chat` par phase de conversation.

**Hiérarchique bridge (assertion : objectives stratégiques → exécution Lego).** Preuves :
`hierarchical/hierarchy_bridge.py:45` `RegistryBackedOperationalRegistry` (enveloppe du
`CapabilityRegistry`), `:56` fabrique `op_registry = RegistryBackedOperationalRegistry(cap_registry)`,
`:67` `find_for_capability` ; CLI `run_orchestration.py:386-387` (« strategic objectives → Lego/DAG
execution », RA-10 #1069).

**Hiérarchique delegation (assertion : 3 niveaux, fail-loud sans registre).** Preuves :
`hierarchical/delegation_orchestrator.py:142` `class DelegationError(RuntimeError)`,
`:332` `class DelegationOrchestrator`, `:419` / `:439` `raise DelegationError` (objectifs
vides ou niveau injoignable) ; CLI `run_orchestration.py:398` (« fail-loud DelegationError —
anti-pendule #1019 ») et `:406`.

**Cluedo (assertion : investigation Sherlock-Watson-Oracle).** Preuves :
`orchestration/cluedo_runner.py:19` `async def run_cluedo_oracle_game(...)`, `:42` `main()` ;
description CLI `run_orchestration.py:377` (« investigation Sherlock-Watson-Oracle, #914 »).

**Writing de l'état final (assertion : chaque mode écrit l'état via les writers).** Preuves :
`orchestration/state_writers.py:288` `CAPABILITY_STATE_WRITERS` (table nom→writer),
`:1844` (le writer sans table → sortie abandonnée — discipline #1826).

**Vigilance découverte** : `orchestration/operational/` (tracked, 3 fichiers, `direct_executor.py`)
est distinct de `orchestration/hierarchical/operational/` (7 fichiers) — deux exécuteurs de
noms voisins ; à consolider ou à distinguer explicitement dans la doc du lot A4. Par ailleurs
`CLAUDE.md` nomme `strategic_bridge.py` alors que le module réel est `hierarchy_bridge.py` —
écart doc à corriger, hors périmètre lot 0.

### Verdict du pilote

Le sous-arbre `orchestration/` est le mieux documenté du dépôt : racine fraîche (3 j) et
courante au verdict lecture (7/8 courants ou partiels légers, 1 seul lien cassé). Le pattern
à généraliser : chaque assertion d'intégration est vérifiable par appelant (CLI, DSL, registry,
runner), et le verdict de contenu est prononcé après recoupement — c'est la méthode que les
lots A/B/C appliqueront aux 71 sans README et 22 à rénover.