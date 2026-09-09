# Inventaire README `argumentation_analysis/` — lot 0 (#2088)

**Date** : 2026-09-09 · **Branche source** : `main` `0c5554b1` · **Exécutant** : Claude Code @ myia-po-2025

## Méthode & reproductibilité

L'inventaire est produit par un instrument commité, `scripts/docs/inventory_argumentation_readmes.py`
(commandé : `python scripts/docs/inventory_argumentation_readmes.py > rapport.md`).

- **Base = contenu suivi par git** (`git ls-files`), jamais le disque : les arbres vendorisés
  (`libs/`, `portable_jdk/`), caches locaux et résidus de cleanups (#2055) sont sur disque
  mais ne sont pas first-party.
- **Règle « substantiel » déclarée** : ≥ 3 fichiers suivis OU au moins un `.py`.
- **4 contrôles positifs** (exit 1 en cas d'échec) : le répertoire documenté connu
  (`orchestration/`), ≥ 5 substantiels sans README (l'instrument en voit 71), l'exclusion
  vendorisée prouvée (`libs`+`portable_jdk` tous deux hors inventaire suivi), les arbres
  morts #2055 (`orchestration/engine/`, `orchestration/cluedo_components/`) absents de la
  base suivie. **Exécutés : 4/4 PASS.**

## Chiffres clés

| Mesure | Valeur |
|---|---|
| Répertoires suivis (hors racine `argumentation_analysis/`) | **119** |
| Dont vendorisés suivis | **0** (preuve : `libs/` + `portable_jdk/` sont gitignorés sur disque) |
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
| `agents/tools/analysis/new` | 4 | 6 | 5 | oui | — |
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

## 2. Exclusions — preuve que l'inventaire ne voit que le first-party

- **0 répertoire vendorisé suivi** : les racines `libs/` et `portable_jdk/` n'apparaissent dans
  AUCUNE ligne `git ls-files` sous `argumentation_analysis/` (contrôle positif 3, PASS).
- **Présents sur disque mais non suivis** (hors inventaire par construction) : `libs/` (gitignored —
  JDK 15.0.2, JDK 17.0.11, node v20 + arbre npm complet, tweety/native), `portable_jdk/` (gitignored —
  JDK 17.0.2), `evaluation/results/` (gitignored — sorties de runs), `results/`, `temp_downloads/`,
  `text_cache/`, `tests/`, `mocks/` (untracked, non-ignorés), et les résidus #2055
  `orchestration/engine/`, `orchestration/cluedo_components/` (untracked, non-ignorés — hors base
  suivie, contrôle positif 4, PASS). Les quelques dossiers « suivi (résiduel) » (ex.
  `agents/prompts/TaxonomyDisplayPlugin`, `pipelines/orchestration/orchestrators`) sont des
  coquilles dont les fichiers ont été déplacés — candidats nettoiement, pas inventaire.

## 3. README existants — signaux objectifs

Critère : « dérive » = dernier commit touchant le README antérieur au dernier commit touchant
le répertoire. Colonne « Liens cassés » : chemins relatifs du README qui ne résolvent pas sur
disque (les liens ligne-anchored `fichier.py:24` sont déduits ; `http(s)` non comptés ;
jusqu'à 4 exemples affichés, le **total** est le nombre affiché).

| README | Lignes | Dernier commit README | Dernière activité rép. | Liens cassés (total) |
|---|---|---|---|---|
| `agents/README.md` | 238 | 2026-05-01 ← dérive | 2026-09-09 | **9** : ./tools/optimization/README.md, ./tools/encryption/README.md, ./runners/README.md, ./data/ … |
| `agents/core/README.md` | 30 | 2025-06-03 ← dérive | 2026-09-09 | 0 |
| `agents/core/extract/README.md` | 107 | 2025-06-03 ← dérive | 2026-02-16 | 0 |
| `agents/core/informal/README.md` | 33 | 2025-06-03 ← dérive | 2026-09-06 | 0 |
| `agents/core/logic/README.md` | 43 | 2025-06-15 ← dérive | 2026-09-03 | **3** : ../../abc/agent_bases.py:24, ../../abc/agent_bases.py:159, first_order_logic_agent.py:0 |
| `agents/core/pl/README.md` | 38 | 2025-06-03 ← dérive | 2025-10-15 | 0 |
| `agents/core/pm/README.md` | 122 | 2025-06-04 ← dérive | 2026-06-12 | 0 |
| `agents/docs/README.md` | 46 | 2025-06-03 ← dérive | 2026-05-01 | 0 |
| `agents/templates/README.md` | 60 | 2025-06-03 ← dérive | 2026-05-01 | 0 |
| `agents/templates/student_template/README.md` | 37 | 2026-05-01 | 2026-05-01 | 0 |
| `agents/tools/README.md` | 47 | 2025-06-03 ← dérive | 2026-06-10 | 0 |
| `agents/tools/analysis/README.md` | 102 | 2025-06-03 ← dérive | 2026-06-10 | **3** : ./enhanced/README.md, ./enhanced/README.md, ../../tests/tools/README.md |
| `agents/tools/analysis/new/README.md` | 179 | 2025-06-03 ← dérive | 2026-06-10 | **1** : ../enhanced/README.md |
| `config/README.md` | 72 | 2025-06-03 ← dérive | 2026-08-31 | 0 |
| `core/README.md` | 115 | 2025-07-19 ← dérive | 2026-09-07 | 0 |
| `core/communication/README.md` | 16 | 2025-06-21 ← dérive | 2026-09-05 | 0 |
| `models/README.md` | 68 | 2026-09-05 | 2026-09-05 | 0 |
| `orchestration/README.md` | 50 | 2026-09-06 ← dérive (3 j) | 2026-09-09 | 0 |
| `orchestration/hierarchical/README.md` | 75 | 2025-06-21 ← dérive | 2026-08-17 | 0 |
| `orchestration/hierarchical/interfaces/README.md` | 87 | 2025-06-03 ← dérive | 2026-07-26 | **1** : ../../../../core/communication/README.md |
| `orchestration/hierarchical/operational/README.md` | 22 | 2025-06-21 ← dérive | 2026-07-16 | 0 |
| `orchestration/hierarchical/operational/adapters/README.md` | 126 | 2025-06-03 ← dérive | 2026-06-02 | 0 |
| `orchestration/hierarchical/strategic/README.md` | 21 | 2025-06-21 ← dérive | 2026-08-17 | 0 |
| `orchestration/hierarchical/tactical/README.md` | 22 | 2025-06-21 ← dérive | 2026-08-14 | 0 |
| `orchestration/hierarchical/templates/README.md` | 65 | 2025-06-03 ← dérive | 2026-02-14 | 0 |
| `pipelines/README.md` | 29 | 2025-06-21 ← dérive | 2026-09-09 | 0 |
| `pipelines/orchestration/README.md` | 21 | 2025-06-21 ← dérive | 2026-08-04 | 0 |
| `plugin_framework/agents/README.md` | 33 | 2026-02-25 | 2026-02-25 | 0 |
| `plugin_framework/core/plugins/README.md` | 42 | 2026-02-25 ← dérive | 2026-06-10 | 0 |
| `scripts/README.md` | 102 | 2026-09-03 | 2026-09-03 | 0 |
| `services/README.md` | 210 | 2025-06-03 ← dérive | 2026-09-06 | 0 |
| `services/mcp_server/README.md` | 54 | 2026-02-25 ← dérive | 2026-09-01 | 0 |
| `services/web_api/README.md` | 66 | 2025-06-21 ← dérive | 2026-08-24 | 0 |
| `ui/README.md` | 229 | 2025-06-03 ← dérive | 2026-08-25 | **2** : ../../scripts/embed_all_sources.py, ./extract_editor/extract_marker_editor.ipynb |
| `ui/extract_editor/README.md` | 172 | 2025-06-03 ← dérive | 2026-08-25 | **1** : ./extract_marker_editor.ipynb |
| `utils/README.md` | 30 | 2025-06-15 ← dérive | 2026-09-06 | 0 |
| `utils/extract_repair/README.md` | 288 | 2026-09-03 ← dérive (1 j) | 2026-09-04 | **6** : ./repair_extract_markers.py, ./verify_extracts.py, ./docs/repair_report.html, ./docs/verify_extracts_report.html … |

### Classification

Critère déclaré, appliqué aux signaux mesurés (jamais une lecture subjective) :

| Classe | Critère | Nombre | Répertoires |
|---|---|---|---|
| **Courant** | README au dernier commit du répertoire (0 dérive) | 4 | `models`, `scripts`, `agents/templates/student_template`, `plugin_framework/agents` |
| **Partiel** | Dérive marquée, zéro lien cassé (décrit un état ancien, liens internes tenaces) | 25 | `agents/core`, `agents/core/extract`, `agents/core/informal`, `agents/core/pl`, `agents/core/pm`, `agents/docs`, `agents/templates`, `agents/tools`, `config`, `core`, `core/communication`, `hierarchical` (5), `pipelines`, `pipelines/orchestration`, `plugin_framework/core/plugins`, `services`, `services/mcp_server`, `services/web_api`, `utils` — avec une nuance « dérive récente » (≤ 7 j : `orchestration`, `utils/extract_repair`) |
| **Périmé** | Dérive marquée **et** liens cassés (état ancien qui pointe vers des cibles disparues) | 8 | `agents`, `agents/core/logic` (3), `agents/tools/analysis` (3), `agents/tools/analysis/new` (1), `hierarchical/interfaces` (1), `ui` (2), `ui/extract_editor` (1), `utils/extract_repair` (6) |
| **Spécialisé** | `README_*.md` complémentaires (hors `README.md`) | 3 fichiers, 2 répertoires | `agents/docs` (optimisation_informal, test_orchestration_complete) ; `agents/tools/encryption` (README_encryption_system.md **seul** — substantiel sans `README.md`, promouvable) |

Total 4 + 25 + 8 = 37. Les 26 liens cassés vivent tous dans la classe « périmé ».

## 4. DAG — feuilles substantielles sans README groupées par parent

Décompte vérifié : **55 feuilles sous 10 racines documentées + 16 racines elles-mêmes sans
README = 71**. (Chaque feuille = répertoire substantiel sans `README.md`.)

### Racines de niveau 1 SANS README (16)

`adapters` · `analytics` · `api` · `cli` · `data` · `evaluation` · `integrations` · `kernel` ·
`nlp` · `plugin_framework` · `plugins` · `reporting` · `service_setup` · `visualization` ·
`webapp` · `workflows`

### Feuilles sous racine documentée, par parent immédiat

| Parent (README ?) | Feuilles substantielles sans README |
|---|---|
| `agents/` (oui) | `channels` · `concrete_agents` · `core/abc` · `core/counter_argument` · `core/debate` · `core/governance` · `core/oracle` · `core/political` · `core/quality` · `core/synthesis` · `extract` · `plugins` · `tools/encryption` (README_ seul) · `tools/support` · `utils` · `watson_jtms` — **16** |
| `core/` (oui) | `communication/tests` · `integration` · `interfaces` · `models` · `setup` · `utils` · `utils/tests` — **7** |
| `orchestration/` (oui) | `operational` (exécuteur direct, distinct de `hierarchical/operational`) · `plugins` — **2** |
| `pipelines/` (oui) | `orchestration/analysis` · `orchestration/config` · `orchestration/core` · `orchestration/execution` · `orchestration/orchestrators/specialized` — **5** |
| `plugin_framework/` (NON) | `agents/personalities` · `benchmarking` · `core` · `core/plugins/standard` · `core/plugins/standard/external_verification` · `core/plugins/standard/taxonomy_explorer` · `core/plugins/workflows` · `core/services` — **8** |
| `plugins/` (NON) | `analysis_tools` · `analysis_tools/logic` · `analysis_tools/tests` · `semantic_kernel` — **4** |
| `reporting/` (NON) | `restitution` — **1** |
| `services/` (oui) | `ai_shield` · `ai_shield/layers` · `jtms` · `mcp_server/tools` · `web_api/models` · `web_api/routes` · `web_api/services` · `web_api/tests` — **8** |
| `utils/` (oui) | `core_utils` · `dev_tools` · `extract_repair/docs` — **3** |
| `data/` (NON) | `datasets/legacy_fixtures` — **1** |

## 5. Lots proposés (tranches livrables, ordre suggéré)

| Lot | Contenu | Justification |
|---|---|---|
| **L1 — racines niveau 1 (16)** | Écrire 16 `README.md` courts (ou consolider dans `CLAUDE.md` pour les coquilles `cli`/`kernel`/`service_setup`/`integrations`) | La porte d'entrée du dépôt est muette : aucune racine de premier niveau n'explique ce qu'elle fait. Priorité : `plugins` (21 py), `evaluation` (23 py), `reporting` (16 py), `workflows` (9 py), `api` (4), `visualization` (5), `adapters` (4), `analytics` (4) ; `data` (0 py — documenter le contenu chiffré, pas le format) |
| **L2 — sous-arbre `agents/` (16 feuilles + 1 promu)** | README par famille (`core/abc`, `core/debate`, `core/governance`, `core/oracle`, `core/synthesis`, `watson_jtms`…) + promotion de `agents/tools/encryption` (README_encryption_system.md → README.md) | Plus gros bassin de feuilles sous une racine documentée ; les fichiers sont chauds (activité 09-09 sur `agents/`) |
| **L3 — orchestration + pipelines (7)** | `orchestration/operational`, `orchestration/plugins` + 5 feuilles `pipelines/orchestration/*` ; enchaîner avec la remise à jour des 7 README hiérarchie (dérive généralisée 06-21→08-17) | Le pilote ci-dessous fournit déjà les preuves d'intégration (mode, capacités, registre, CLI) ; pas de re-découverte à faire |
| **L4 — services (8)** | `ai_shield` (+`layers`), `jtms`, `web_api/models/routes/services/tests`, `mcp_server/tools` | Sous-racine à forte valeur (API publique, serveur MCP) |
| **L5 — plugin_framework + core (15)** | `plugin_framework` racine + 7 feuilles, `core/` 7 feuilles | Deux surfaces qui se chevauchent avec `plugins/` — écrire l'un avec l'autre pour trancher les redondances |
| **L6 — réparation des liens cassés (26)** | Décider cible par cible dans les 8 README « périmés » : pointer vers la cible réelle, ou retirer la ligne si la cible est partie | `agents` (9), `utils/extract_repair` (6), `agents/core/logic` (3), `analysis` (3+1), `ui` (2+1), `hierarchical/interfaces` (1) — à vérifier à la lecture, certaines cibles (ex. `./data/`) sont des répertoires qui existent mais mal référencés |

Chaque lot est indépendant ; l'ordre ci-dessus maximise la valeur par unité de lecture.

## 6. Pilote — sous-arbre `orchestration/` (sans modifier son README)

DoD #2088 : « les statuts d'intégration sont étayés par des appelants, routes, workflows ou
tests — **jamais inférés du nom** ». Chaque ligne ci-dessous cite les preuves.

### Cartographie des 8 README du sous-arbre

| README | Lignes | Dérive | Liens cassés |
|---|---|---|---|
| `orchestration/README.md` | 50 | 3 j (09-06 → 09-09) | 0 |
| `orchestration/hierarchical/README.md` | 75 | 06-21 → 08-17 | 0 |
| `…/hierarchical/interfaces/README.md` | 87 | 06-03 → 07-26 | **1** (`core/communication/README.md` via `../../../../`) |
| `…/hierarchical/operational/README.md` | 22 | 06-21 → 07-16 | 0 |
| `…/hierarchical/operational/adapters/README.md` | 126 | 06-03 → 06-02 | 0 |
| `…/hierarchical/strategic/README.md` | 21 | 06-21 → 08-17 | 0 |
| `…/hierarchical/tactical/README.md` | 22 | 06-21 → 08-14 | 0 |
| `…/hierarchical/templates/README.md` | 65 | 06-03 → 02-14 | 0 |

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
noms voisins ; à consolider ou à distinguer explicitement dans la doc du lot 3. Par ailleurs
`CLAUDE.md` nomme `strategic_bridge.py` alors que le module réel est `hierarchy_bridge.py` —
écart doc à corriger, hors périmètre lot 0.

### Verdict du pilote

Le sous-arbre `orchestration/` est le mieux docmenté du dépôt : racine fraîche (3 j) et
faible dérive des 7 README de hiérarchie (4-14 semaines), 1 seul lien cassé. Le pattern à
généraliser : chaque assertion d'intégration est vérifiable par appelant (CLI, DSL, registry,
runner). Les lots L3/L6 en repartent avec les preuves déjà assemblées.