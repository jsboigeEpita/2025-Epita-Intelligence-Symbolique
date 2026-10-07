# Classement des README existants — `argumentation_analysis/` (#2088, DoD n°3)

**Date** : 2026-10-07 · **Base** : main `5f583e8b5` (mesuré ; le chiffre « 97 » du
dashboard datait d'avant les merges des vagues — la population mesurée aujourd'hui
est **101 README suivis**) · **Exécutant** : Claude Code @ myia-po-2025

## Ce que « classer » produit et qui le lit

Le classement n'est pas une fin : c'est la **file de travail des lots restants** de
l'Epic #2088.

- **Consommateur 1 — les lots restants** : la classe « à réécrire » est exactement la
  liste des README encore à reprendre (5 fichiers, §2). Les 93 « courant » sortent du
  périmètre de réécriture : les lots ne les retouchent plus.
- **Consommateur 2 — l'audit DoD du coordinateur** : l'item n°3 (« chaque README
  existant a été classé : courant, à réécrire, spécialisé seulement, ou hors
  périmètre ») se vérifie en lisant ce rapport ; le tableau complet fait foi.
- **Consommateur 3 — la garde légère du DoD n°10** : la garde existante
  (`tests/unit/docs/test_argumentation_readmes_cover_dirs_2088.py`, rework #2962)
  ne mesure que les cibles de liens **`.md`** (360 liens rendus markdown-it). Le
  classement étend la mesure à **toute** cible relative (`.py`, `.ipynb`,
  répertoires) : les 5 lignes rouges du §2 sont rouges sous cet instrument et
  invisibles de la garde actuelle — c'est l'écart mesuré que son extension
  éventuelle couvrira (décision séparée, pas faite ici).

## Méthode & reproductibilité

Instrument commité : `scripts/docs/classify_argumentation_readmes.py`.

```bash
python scripts/docs/classify_argumentation_readmes.py > rapport.md
python scripts/docs/classify_argumentation_readmes.py --selftest   # contrôles nés-rouges
```

- Base = contenu **suivi par git** sous `argumentation_analysis/` (même règle que le
  Lot 0 : jamais le disque — arbres vendorisés et caches exclus par construction).
- Chaque classe est **mesurée**, jamais inférée du nom :
  - `spécialisé seulement` — motif `README_*.md` : document compagnon (3 fichiers) ;
  - `hors périmètre` — sous une racine couverte par un `.gitignore` versionné
    (sonde fichier descendant, contrôle 3 du Lot 0) : **0**, cohérent avec la preuve
    Lot 0 « 0 fichier suivi vendorisé » ;
  - `à réécrire` — ≥ 1 lien relatif cassé (cible markdown qui ne résout pas) OU
    répertoire sous le plancher de prose (5 lignes) ;
  - `courant` — les autres.
- **Contrôles positifs** (`--selftest`, exit 1 en cas d'échec) : détecteur de lien
  cassé qui déclenche sur fixture, plancher stub qui déclenche, motif spécialisé qui
  matche, énumération qui voit ≥ 90 README (mesuré : 101), overlay de jugement qui se
  câble. Un zéro (« hors périmètre : 0 ») n'est affirmé que parce que la branche
  correspondante est exécutable et que le selftest prouve les détecteurs vivants.
- **Overlay de jugement** (`_JUDGMENT` dans l'instrument) : seam documenté pour une
  classe posée par lecture datée quand la mesure ne voit pas (ex. README
  mono-famille sur répertoire multi-familles). **Resté vide cette passe** : chaque
  ligne « à réécrire » a été produite par la mesure PUIS confirmée par lecture des 5
  fichiers (§2) — aucune classe n'a eu besoin d'être posée à la main. Les « courant »
  sont portés par la mesure (0 lien cassé, plancher de prose, dates de toucher), pas
  par une relecture intégrale des 93 : c'est la portée exacte de l'affirmation.

## Résultat mesuré

**101 README suivis** : **93 courant · 5 à réécrire · 3 spécialisé seulement · 0 hors périmètre.**

## §2 — Les 5 « à réécrire », preuves vérifiées sur disque et dans git

| README | Liens cassés mesurés | Preuve lue |
|---|---|---|
| `agents/README.md` | `./data/`, `./libs/` | les deux répertoires n'existent pas sous `agents/` (les données vivent à la racine du paquet ; `libs/` n'est pas suivi — sa résolution dépendrait du disque local) |
| `agents/tools/README.md` | `../../../../scripts/security/verify_encrypted_dataset_completeness.py` | le script existe à la racine ; le lien a un `../` de trop (3 niveaux, pas 4) |
| `ui/README.md` | `../../scripts/embed_all_sources.py`, `./extract_editor/extract_marker_editor.ipynb` | `embed_all_sources.py` n'existe plus nulle part dans le dépôt suivi ; le notebook a été converti en `.py` |
| `ui/extract_editor/README.md` | `./extract_marker_editor.ipynb` | le fichier suivi est désormais `extract_marker_editor.py` |
| `utils/extract_repair/README.md` | 6 cibles (`./repair_extract_markers.py`, `./verify_extracts.py`, `./docs/repair_report.html`, `./docs/verify_extracts_report.html`, …) | le répertoire porte `repair_extract_markers.ipynb` (notebook, pas `.py`), `verify_extracts_with_llm.py`, et `docs/repair_extract_markers_report.md` — le README nomme des fichiers qui n'existent plus sous ces noms |

Ces 5 fichiers sont la file des lots restants ; l'Epic ne les réécrit pas ici (une PR
documentaire par feuille, stratégie de livraison de l'issue). Les anomalies de code
découvertes en documentant continuent d'aller dans des issues séparées.

## §3 — Les 3 « spécialisé seulement »

`README_JTMS_PLUGIN.md`, `README_optimisation_informal.md`,
`README_test_orchestration_complete.md` — documents compagnons datés ; ils ne
remplacent pas le `README.md` de leur répertoire (distinction posée par le Lot 0) et
restent classés ici sans autre jugement.

## §4 — Tableau complet (sortie instrument, non retouchée)
**Total README suivis** : 101
- **courant** : 93
- **à réécrire** : 5
- **spécialisé seulement** : 3
- **hors périmètre** : 0

| README | Prose | Dernier toucher | Classe | Motif (mesuré) |
|---|---:|---|---|---|
| `argumentation_analysis/README.md` | 26 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/adapters/README.md` | 23 | 2026-09-16 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/channels/README.md` | 12 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/concrete_agents/README.md` | 18 | 2026-09-27 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/README.md` | 29 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/abc/README.md` | 29 | 2026-09-27 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/counter_argument/README.md` | 28 | 2026-09-26 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/debate/README.md` | 36 | 2026-10-05 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/extract/README.md` | 62 | 2026-09-14 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/governance/README.md` | 43 | 2026-09-26 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/informal/README.md` | 16 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/logic/README.md` | 27 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/oracle/README.md` | 43 | 2026-09-27 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/pl/README.md` | 26 | 2025-06-03 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/pm/README.md` | 16 | 2026-09-27 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/political/README.md` | 51 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/quality/README.md` | 38 | 2026-09-26 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/core/synthesis/README.md` | 30 | 2026-09-26 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/docs/README.md` | 24 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/extract/README.md` | 43 | 2026-09-27 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/plugins/README.md` | 18 | 2026-09-11 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/templates/README.md` | 34 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/templates/student_template/README.md` | 24 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/tools/analysis/README.md` | 57 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/tools/analysis/new/README.md` | 114 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/tools/support/README.md` | 17 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/utils/README.md` | 19 | 2026-09-27 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/analytics/README.md` | 17 | 2026-09-15 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/api/README.md` | 22 | 2026-09-24 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/cli/README.md` | 20 | 2026-09-11 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/config/README.md` | 39 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/core/README.md` | 73 | 2026-09-15 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/core/communication/README.md` | 9 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/core/communication/tests/README.md` | 16 | 2026-09-11 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/core/integration/README.md` | 14 | 2026-09-11 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/core/interfaces/README.md` | 22 | 2026-09-14 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/core/models/README.md` | 25 | 2026-09-11 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/core/setup/README.md` | 26 | 2026-09-23 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/core/utils/README.md` | 66 | 2026-10-05 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/data/README.md` | 24 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/data/datasets/legacy_fixtures/README.md` | 13 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/evaluation/README.md` | 25 | 2026-09-11 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/kernel/README.md` | 12 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/models/README.md` | 38 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/nlp/README.md` | 18 | 2026-09-16 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/orchestration/README.md` | 65 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/orchestration/hierarchical/README.md` | 64 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/orchestration/hierarchical/interfaces/README.md` | 47 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/orchestration/hierarchical/operational/README.md` | 14 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/orchestration/hierarchical/operational/adapters/README.md` | 73 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/orchestration/hierarchical/strategic/README.md` | 12 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/orchestration/hierarchical/tactical/README.md` | 13 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/orchestration/hierarchical/templates/README.md` | 43 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/orchestration/plugins/README.md` | 28 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/pipelines/README.md` | 12 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/pipelines/orchestration/README.md` | 31 | 2026-10-06 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/pipelines/orchestration/config/README.md` | 19 | 2026-09-17 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/pipelines/orchestration/execution/README.md` | 30 | 2026-09-17 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugin_framework/README.md` | 86 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugin_framework/agents/README.md` | 13 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugin_framework/benchmarking/README.md` | 41 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugin_framework/core/README.md` | 55 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugin_framework/core/plugins/README.md` | 31 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugin_framework/core/plugins/standard/README.md` | 36 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugin_framework/core/plugins/standard/external_verification/README.md` | 29 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugin_framework/core/plugins/standard/taxonomy_explorer/README.md` | 33 | 2026-09-15 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugin_framework/core/services/README.md` | 31 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugins/README.md` | 66 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugins/analysis_tools/README.md` | 51 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugins/analysis_tools/logic/README.md` | 22 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/plugins/semantic_kernel/README.md` | 17 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/reporting/README.md` | 227 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/reporting/restitution/README.md` | 24 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/scripts/README.md` | 57 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/service_setup/README.md` | 18 | 2026-09-28 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/README.md` | 132 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/ai_shield/README.md` | 93 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/ai_shield/layers/README.md` | 79 | 2026-09-14 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/jtms/README.md` | 69 | 2026-09-16 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/mcp_server/README.md` | 39 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/mcp_server/tools/README.md` | 67 | 2026-09-15 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/web_api/README.md` | 43 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/web_api/models/README.md` | 48 | 2026-09-16 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/web_api/routes/README.md` | 33 | 2026-09-11 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/web_api/services/README.md` | 57 | 2026-09-15 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/services/web_api/tests/README.md` | 37 | 2026-09-24 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/utils/README.md` | 17 | 2026-10-07 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/utils/core_utils/README.md` | 11 | 2026-09-11 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/utils/dev_tools/README.md` | 16 | 2026-09-12 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/utils/extract_repair/docs/README.md` | 11 | 2026-09-11 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/visualization/README.md` | 18 | 2026-09-15 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/webapp/README.md` | 24 | 2026-09-15 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/workflows/README.md` | 19 | 2026-09-15 | courant | 0 lien cassé, prose suffisante |
| `argumentation_analysis/agents/README.md` | 142 | 2026-10-07 | à réécrire | 2 lien(s) relatif(s) cassé(s) : ./data/, ./libs/ |
| `argumentation_analysis/agents/tools/README.md` | 25 | 2026-10-07 | à réécrire | 1 lien(s) relatif(s) cassé(s) : ../../../../scripts/security/verify_encrypted_dataset_completeness.py |
| `argumentation_analysis/ui/README.md` | 138 | 2025-06-03 | à réécrire | 2 lien(s) relatif(s) cassé(s) : ../../scripts/embed_all_sources.py, ./extract_editor/extract_marker_editor.ipynb |
| `argumentation_analysis/ui/extract_editor/README.md` | 106 | 2025-06-03 | à réécrire | 1 lien(s) relatif(s) cassé(s) : ./extract_marker_editor.ipynb |
| `argumentation_analysis/utils/extract_repair/README.md` | 167 | 2026-10-07 | à réécrire | 6 lien(s) relatif(s) cassé(s) : ./repair_extract_markers.py, ./verify_extracts.py, ./docs/repair_report.html, ./docs/verify_extracts_report.html |
| `argumentation_analysis/README_JTMS_PLUGIN.md` | 196 | 2026-09-15 | spécialisé seulement | README_*.md : document compagnon, pas le README du répertoire |
| `argumentation_analysis/agents/docs/README_optimisation_informal.md` | 122 | 2025-06-03 | spécialisé seulement | README_*.md : document compagnon, pas le README du répertoire |
| `argumentation_analysis/agents/docs/README_test_orchestration_complete.md` | 115 | 2026-09-12 | spécialisé seulement | README_*.md : document compagnon, pas le README du répertoire |
