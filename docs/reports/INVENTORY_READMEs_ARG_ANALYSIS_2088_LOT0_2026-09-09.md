# Inventaire README `argumentation_analysis/` — lot 0 (#2088)

**Date** : 2026-09-09 (rév. 2 du 2026-09-10 après seconde revue coordinateur PR #2091) · **Branche** : `docs/2088-lot0-readme-inventory` · **Exécutant** : Claude Code @ myia-po-2025

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

- **courant** : le README couvre le répertoire **sans présenter un sous-ensemble comme la
  totalité** — les éléments décrits sont recoupés présents ET les composants significatifs
  non décrits sont inexistants ou négligeables (la présence des chemins cités ne suffit
  pas : revue #2091, 2e tour) ;
- **partiel** : le noyau décrit est exact mais le périmètre réel est plus large (briques
  significatives non couvertes, énumération incomplète) ou des chemins cités sont erronés
  de façon réparable ;
- **périmé** : le README décrit des chemins, scripts ou procédures qui **n'existent plus**
  dans l'arbre suivi — le lecteur est activement trompé ;
- **spécialisé seulement** : pas de `README.md` mais un `README_*.md` thématique.

| README | Verdict | Raison vérifiable (recoupement fait) |
|---|---|---|
| `agents/` | **périmé** | 9 liens cassés ; `tools/optimization/` et `runners/` cités n'existent pas dans l'arbre suivi (ls : `analysis`, `encryption`, `support` seulement) ; l'inventaire des familles d'agents listées couvre 4 des 16 feuilles réelles |
| `agents/core/` | partiel | liste 4 familles (pm, informal, pl, extract) sur 13 présentes (abc, counter_argument, debate, governance, logic, oracle, political, quality, synthesis absentes de la liste) |
| `agents/core/extract/` | courant | décrit les 3 modules réels (`extract_agent.py`, `extract_definitions.py`, `prompts.py`, `__init__` trivial) — couverture complète du répertoire |
| `agents/core/informal/` | partiel | décrit 2 fichiers ; le module en porte 8 `.py` non couverts (`taxonomy_sophism_detector.py`, `dung_arbitration_stage.py`, `neuro_symbolic_arbitrator.py`, `detection_candidate_bridge.py`…) ; exemple d'import préfixé `agents.` obsolète |
| `agents/core/logic/` | partiel | hiérarchie et composants exacts (BaseAgent/BaseLogicAgent, 3 agents, TweetyBridge, BeliefSet) ; 3 liens erronés d'un niveau (`../../abc/…` alors que abc/ est sous core/, pas sous agents/) |
| `agents/core/pl/` | partiel | rôle et BNF exacts ; mais `PLAnalyzer` cité vit désormais dans `core/logic/propositional_logic_agent.py` (grep) — la fiche ne reflète pas la répartition pl/↔logic/ |
| `agents/core/pm/` | partiel | « Composants Clés » couvre `pm_agent.py`/`pm_definitions.py`/`prompts.py` mais PAS `sherlock_enquete_agent.py` (5ᵉ module du répertoire, l'agent PM d'investigation) — énumération incomplète |
| `agents/docs/` | partiel | notice générique « reports/ » ; le contenu réel = 2 docs spécialisés (README_optimisation_informal, README_test_orchestration_complete) non distingués |
| `agents/templates/` | courant | « Structure » = `student_template/`, l'unique enfant réel — exact et complet |
| `agents/templates/student_template/` | courant | les 4 fichiers décrits + le README = exactement les 5 fichiers réels du template |
| `agents/tools/` | **périmé** | section « optimization/ » : ce répertoire n'existe plus dans l'arbre suivi (ls réel : analysis, encryption, support) |
| `agents/tools/analysis/` | **périmé** | `enhanced/` cité (liens ×2) n'existe pas ; `rhetorical_result_analyzer.py` cité absent (seul `rhetorical_result_visualizer.py` présent) |
| `agents/tools/analysis/new/` | **périmé** | lien `../enhanced/README.md` : `enhanced/` n'existe pas |
| `config/` | partiel | l'arbre montré (` .env.template` + README) ne couvre pas les 4 fichiers suivis réels |
| `core/` | partiel | la section « Contenu » décrit 5 piliers (`shared_state`, `state_manager_plugin`, `strategies`, `jvm_setup`, `llm_service`) mais omet `capability_registry.py` (cœur de l'architecture Lego) et `communication/` — sous-ensemble présenté comme contenu |
| `core/communication/` | partiel | concepts (Message/Channel/Pub-Sub) exacts ; `LocalChannel`/`local_channel.py` cité comme implémentation de référence : le fichier n'existe pas (seul `channel_interface.py` recoupé) |
| `models/` | courant | couvre les 3 fichiers réels du répertoire, `extract_definition.py` recoupé |
| `orchestration/` | partiel | ne documente que 2 approches (moteur `pipelines/orchestration/execution/engine.py` + hiérarchique) ; omet conversationnel, Cluedo, sous-modes bridge/delegation, DSL/registry/writers — familles prouvées vivantes en §7 (`run_orchestration.py:363-387` expose 4 modes + 2 sous-modes) |
| `orchestration/hierarchical/` | partiel | architecture 3 couches exacte (strategic/tactical/operational présents) ; les sous-modes `bridge`/`delegation` et `hierarchy_bridge.py` (RA-10 #1069) ne sont pas couverts |
| `…/hierarchical/interfaces/` | partiel | `strategic_tactical.py` + `tactical_operational.py` présents conformes ; 1 lien erroné d'un niveau vers core/communication |
| `…/hierarchical/operational/` | partiel | « Composants Clés » cite `manager.py`, `adapters/`, `agent_registry.py`, `state.py` mais omet `agent_interface.py` et `feedback_mechanism.py` (présents dans l'arbre suivi) |
| `…/hierarchical/operational/adapters/` | courant | décrit exactement les 4 adaptateurs réels (`extract`, `informal`, `pl`, `rhetorical_tools`) — énumération complète |
| `…/hierarchical/strategic/` | partiel | décrit le rôle conceptuel de la couche sans section composants — `manager.py`, `planner.py`, `allocator.py`, `state.py` non couverts |
| `…/hierarchical/tactical/` | courant | « Composants Clés » couvre les 5 modules réels (`manager`, `coordinator`, `monitor`, `resolver`, `state`) — énumération complète |
| `…/hierarchical/templates/` | courant | décrit exactement les 4 templates réels (`agent`, `analysis_tool`, `analysis_type`, `strategy`) — énumération complète |
| `pipelines/` | partiel | rôle et distinction vs `orchestration/` exacts, mais les 7 modules racine (`unified_text_analysis.py`, `analysis_pipeline.py`, `embedding_pipeline.py`, `reporting_pipeline.py`, `advanced_rhetoric.py`…) ne sont pas énumérés — le README reste conceptuel |
| `pipelines/orchestration/` | courant | énumère exactement ses 5 sous-répertoires réels (`analysis/`, `config/`, `core/`, `execution/`, `orchestrators/`) avec le rôle de chacun — couverture structurelle complète |
| `plugin_framework/agents/` | **périmé** | le mécanisme décrit scanne « `src/agents` » — `src/` racine n'existe plus (consolidation #321) ; les loaders existent mais l'arbre décrit est faux |
| `plugin_framework/core/plugins/` | **périmé** | même défaut : scan de « `src/core/plugins/` » disparu |
| `scripts/` | **périmé** | les 2 scripts décrits (`repair_extract_markers.py`, `verify_extracts.py`) ne sont pas ceux du répertoire (contenu réel : `run_fix_missing_first_letter.py`, `run_verify_extracts_llm.py`, `simulate_balanced_participation.py`, `test_performance_extraits.py`) |
| `services/` | partiel | noyau décrit exact (cache, crypto, definition, extract présents) ; la périphérie réelle non couverte (21 fichiers : `benchmark_service.py`, `fact_verification_service.py`, jtms/, local_llm, speech, web_api, mcp_server) |
| `services/mcp_server/` | partiel | procédure docker exacte, mais `server_config.py` et `session_manager.py` (modules racine) non couverts |
| `services/web_api/` | **périmé** | procédure de lancement via `scripts/launch_webapp_background.py` : ce fichier n'existe pas |
| `ui/` | **périmé** | 2 liens cassés dont la source d'amorçage `../../scripts/embed_all_sources.py` disparue ; le notebook cité absent |
| `ui/extract_editor/` | **périmé** | l'outil central décrit `extract_marker_editor.ipynb` n'est pas dans l'arbre suivi (liens cassés) |
| `utils/` | partiel | notice de 30 lignes face à 35 `.py` réels (`dev_tools/` 14, `extract_repair/`, `core_utils/` non couverts) |
| `utils/extract_repair/` | **périmé** | les scripts décrits ont été renommés (`repair_extract_markers.py`/`verify_extracts.py` → `fix_missing_first_letter.py`/`verify_extracts_with_llm.py`/`marker_repair_logic.py`) ; 6 liens cassés |

**Spécialisé seulement** : `agents/tools/encryption` (README_encryption_system.md sans
`README.md`) — promouvable en README.md lors de son lot.

**Bilan** : 8 courants · 18 partiels · 11 périmés (37). Les 11 périmés trompent activement
le lecteur (chemins/scripts/procédures morts) et portent presque tous les 26 liens cassés ;
les 18 partiels présentent un sous-ensemble comme totalité — l'écart le plus fréquent est
l'énumération incomplète des modules réels du répertoire (7 verdicts abaissés au 2ᵉ tour de
revue après relecture des README concernés).

## 5. DAG enfants → parents — vagues par profondeur réelle

Règle de l'Epic #2088 : un README **parent** s'écrit après ceux de ses enfants — il doit
pouvoir pointer vers des README enfants existants. **Vague(nœud) = 1 + max(vague de ses
enfants ayant du travail)**, où « travail » = README à créer (71) ou README à rénover
(29 = 37 − 8 courants). Un parent léger/résiduel sur le chemin est **exclu explicitement**
et compte comme dépendance satisfaite. Une même vague ne contient **jamais** un nœud et un
de ses descendants.

### Exclusions explicites (dépendances satisfaites avant leurs parents)

- `pipelines/orchestration/orchestrators/` — coquille résiduelle (fichiers déplacés) :
  exclu AVANT que `pipelines/orchestration/` ne soit (re)documenté ; son unique enfant
  substantiel `orchestrators/specialized/` est traité comme feuille.
- `data/datasets/` — coquille légère (ne contient que `legacy_fixtures/`) : exclu, `data/`
  dépend directement de `legacy_fixtures/`.
- `evaluation/corpus/`, `agents/prompts/` (et sous-dossiers), `webapp/config/` — légers
  (< 3 fichiers, 0 `.py`) : exclus, parents traités comme feuilles.
- `agents/tools/encryption` : `README.md` absent mais `README_encryption_system.md` présent
  — **promotion** en `README.md` dans la vague 1, pas une création.
- `pipelines/orchestration/` (verdict courant) : aucune rénovation requise ; un simple
  ajout de liens vers les README enfants créés en vague 1 peut accompagner la vague 2.

### Vague 1 — feuilles profondes et rénovations sans enfant (74)

Nouveaux README (62) :

```
agents/ (16)          : core/abc, core/counter_argument, core/debate, core/governance,
                        core/oracle, core/political, core/quality, core/synthesis,
                        channels, concrete_agents, extract, plugins, tools/encryption
                        (promotion), tools/support, utils, watson_jtms
core/ (6)             : communication/tests, integration, interfaces, models, setup, utils/tests
orchestration/ (2)    : operational, plugins
pipelines/orchestration/ (5) : analysis, config, core, execution, orchestrators/specialized
plugin_framework/ (6) : agents/personalities, benchmarking, core/services,
                        core/plugins/standard/external_verification,
                        core/plugins/standard/taxonomy_explorer, core/plugins/workflows
plugins/ (3)          : semantic_kernel, analysis_tools/logic, analysis_tools/tests
services/ (7)         : ai_shield/layers, jtms, mcp_server/tools,
                        web_api/models, web_api/routes, web_api/services, web_api/tests
reporting/ (1)        : restitution
utils/ (3)            : core_utils, dev_tools, extract_repair/docs
data/ (1)             : datasets/legacy_fixtures
racines orphelines (12) : adapters, analytics, api, cli, evaluation, integrations,
                        kernel, nlp, service_setup, visualization, webapp, workflows
```

Rénovations sans enfant à documenter (12) : `agents/core/informal`, `agents/core/logic`,
`agents/core/pl`, `agents/core/pm`, `agents/docs`, `config`, `…/hierarchical/strategic`,
`…/hierarchical/operational`, `…/hierarchical/interfaces`, `agents/tools/analysis/new`,
`scripts`, `ui/extract_editor`.

### Vague 2 — parents directs des feuilles (16)

Nouveaux README (7) : `core/utils`, `services/ai_shield`, `plugins/analysis_tools`,
`plugin_framework/core/plugins/standard`, `plugin_framework/core`, `data`, `reporting`.

Rénovations dont les enfants sont couverts en vague 1 (9) : `core/communication`
(enfant `tests`), `agents/tools/analysis` (enfant `new`), `agents/core` (8 enfants créés +
4 rénovés en v1), `services/web_api`, `services/mcp_server`, `ui`, `utils/extract_repair`,
`plugin_framework/agents`, `orchestration/hierarchical`.

### Vague 3 — grands parents (9)

Nouveaux README (2) : `plugin_framework` (enfant `core` en v2), `plugins` (enfant
`analysis_tools` en v2).

Rénovations (7) : `agents/tools` (enfant `analysis` v2), `services` (enfants `ai_shield`
v2, `web_api` v2, `mcp_server` v2), `utils` (enfant `extract_repair` v2), 
`plugin_framework/core/plugins` (enfant `standard` v2), `orchestration` (enfants v1 +
`hierarchical` v2), `core` (enfants `utils` v2, `communication` v2), `pipelines`
(enfant `pipelines/orchestration` rafraîchi en v2).

### Vague 4 — racines tardives (1)

`agents/` (rénovation périmé) — bloquée sur : 16 enfants créés v1, `agents/core` v2,
`agents/tools` v3, `agents/docs` v1.

**Fermeture vérifiée** : nouveaux 62+7+2 = **71** ✓ ; rénovations 12+9+7+1 = **29** = 37 − 8
courants ✓ ; chaque chaîne parent→enfant citée en revue (`core/utils/tests→core/utils`,
`ai_shield/layers→ai_shield`, `analysis_tools/logic→analysis_tools`,
`standard/*→standard→core/plugins→core→plugin_framework`, `pipelines/orchestration/*→…→pipelines`,
`agents/core/*→agents/core→agents`) s'étale maintenant sur des vagues distinctes ✓.

## 6. Lots proposés (découpe des vagues en tranches livrables)

| Lot | Vague | Contenu | Blocage |
|---|---|---|---|
| **A1** | 1 | 16 feuilles `agents/` (dont promotion `tools/encryption`) | aucun |
| **A2** | 1 | 7 feuilles `services/` | aucun |
| **A3** | 1 | 6 feuilles `plugin_framework/` + 6 feuilles `core/` | aucun |
| **A4** | 1 | 5 feuilles `pipelines/orchestration/` + 2 `orchestration/` + exclusion explicite `orchestrators/` | aucun |
| **A5** | 1 | 3 feuilles `plugins/` + `reporting/restitution` + `data/datasets/legacy_fixtures` + exclusions (`data/datasets/`, `evaluation/corpus/`) | aucun |
| **A6** | 1 | 12 racines-orphelines | aucun |
| **A7** | 1 | 12 rénovations feuilles (`agents/core/{informal,logic,pl,pm}`, `agents/docs`, `config`, `hierarchical/{strategic,operational,interfaces}`, `analysis/new`, `scripts`, `ui/extract_editor`) | aucun |
| **B1** | 2 | parents directs : `core/utils`, `ai_shield`, `analysis_tools`, `pf/core/plugins/standard`, `pf/core`, `data`, `reporting` | bloqué sur A3 (core/pf), A4, A5 |
| **B2** | 2 | 9 rénovations niveau 2 (`core/communication`, `tools/analysis`, `agents/core`, `web_api`, `mcp_server`, `ui`, `extract_repair`, `pf/agents`, `hierarchical`) | bloqué sur A1-A7 |
| **C1** | 3 | `plugin_framework`, `plugins` + 7 rénovations grands-parents (`agents/tools`, `services`, `utils`, `pf/core/plugins`, `orchestration`, `core`, `pipelines`) | bloqué sur B1/B2 |
| **C2** | 4 | rénovation `agents/` (racine) | bloqué sur C1 |

Les 26 liens cassés sont réparés par les rénovations qui les portent (A7 : `analysis/new`,
`scripts`, `ui/extract_editor` ; B2 : `tools/analysis`, `web_api`, `ui`, `extract_repair` ;
C1 : `agents/tools`, `services`, `utils`, `pipelines`… — cf. colonne §3).

## 7. Pilote — sous-arbre `orchestration/` (sans modifier son README)

DoD #2088 : « les statuts d'intégration sont étayés par des appelants, routes, workflows ou
tests — **jamais inférés du nom** ». Chaque ligne ci-dessous cite les preuves.

### Cartographie des 8 README du sous-arbre

| README | Lignes | Verdict (§4) | Liens cassés |
|---|---|---|---|
| `orchestration/README.md` | 50 | partiel (2 approches sur 4 modes + sous-modes omis) | 0 |
| `orchestration/hierarchical/README.md` | 75 | partiel (sous-modes non couverts) | 0 |
| `…/hierarchical/interfaces/README.md` | 87 | partiel (1 chemin erroné) | 1 |
| `…/hierarchical/operational/README.md` | 22 | partiel (`agent_interface.py`, `feedback_mechanism.py` non couverts) | 0 |
| `…/hierarchical/operational/adapters/README.md` | 126 | courant (4 adaptateurs réels exactement) | 0 |
| `…/hierarchical/strategic/README.md` | 21 | partiel (aucune section composants) | 0 |
| `…/hierarchical/tactical/README.md` | 22 | courant (5 modules réels couverts) | 0 |
| `…/hierarchical/templates/README.md` | 65 | courant (4 templates réels couverts) | 0 |

### Statuts d'intégration prouvés

**Modes d'orchestration (assertion : 4 modes exécutables).** Preuves :
`run_orchestration.py:363-373` — `--mode` entre `pipeline|conversational|hierarchical|cluedo`,
défaut `pipeline` ; descriptions `:375-377` ; mode hiérarchique sous-mode `--hierarchical-mode`
`{bridge,delegation}` défaut `bridge` `:381-387` ; aiguillage `elif mode == "hierarchical"`
`:714`. Le README racine (50 lignes) ne documente que le moteur externe et l'hiérarchique —
les familles conversationnelle, Cluedo, bridge/delegation et DSL/registry/writers ci-dessus
sont **absentes de la fiche** (d'où son verdict partiel) : le pilote prouve les familles,
pas leur couverture documentaire.

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

Le sous-arbre `orchestration/` est le mieux documenté du dépôt (1 seul lien cassé, racine
fraîche à 3 j), mais la fraîcheur n'est pas la couverture : sa racine est **partiel** au
verdict lecture — les familles qu'il orchestre réellement (prouvées ci-dessus par appelants)
sont majoritairement absentes de sa fiche. Le pattern à généraliser : chaque assertion
d'intégration est vérifiable par appelant (CLI, DSL, registry, runner), et le verdict de
contenu est prononcé après recoupement de la **couverture**, pas de la seule existence des
chemins — c'est la méthode que les lots A/B/C appliqueront aux 71 sans README et 29 à rénover.