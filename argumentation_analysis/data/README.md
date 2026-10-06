# `argumentation_analysis/data/` — taxonomies, mocks et le corpus chiffré

## Rôle et frontière

11 fichiers suivis (chemin de données pur, aucun `__pycache__`). Trois familles :
les **taxonomies de sophismes** (source Argumentum + sous-ensembles générés), les
**fixtures/mock** pédagogiques, et le **corpus chiffré canonique**. Chaque fichier
ci-dessous porte son **lecteur réel mesuré** (`git grep` du nom de fichier dans le
code — jamais inféré du nom). Les fixtures relocalisées de 2025-06 vivent dans
[`datasets/legacy_fixtures/`](datasets/legacy_fixtures/README.md).

## Fichiers et lecteurs réels

| fichier | rôle | lecteur réel (mesuré) |
|---|---|---|
| `argumentum_fallacies_taxonomy.csv` | taxonomies Argumentum des sophismes (source) | `api/fallacy_detection.py:40` et `agents/core/informal/informal_definitions.py:226` en production ; `evaluation/fallacy_benchmark.py`, `evaluation/plugin_benchmark.py` en évaluation |
| `argumentum_virtues_taxonomy.csv` | taxonomies Argumentum des vertus (source) | emballé par `pyproject.toml:121` (package data) ; intégrité gardée par `tests/unit/scripts/test_argumentum_taxonomy_integrity.py` ; enregistré dans le JSON de provenance ci-dessous |
| `argumentum_taxonomy_provenance.json` | provenance/épinglage des taxonomies Argumentum | `utils/taxonomy_loader.py:32` (`PROVENANCE_FILE`) |
| `taxonomy_full.csv` | taxonomie complète (toutes profondeurs) | `adapters/french_fallacy_adapter.py:64` (structure hiérarchique) ; générée/consommée par `scripts/data_preparation/generate_taxonomy_subsets.py`, `scripts/migrate_taxonomy.py` ; restitutions via `reporting/restitution/act2_narrative_plugin.py` |
| `taxonomy_medium.csv` | sous-ensemble profondeurs 1+2 | `adapters/french_fallacy_adapter.py:62` (`_TAXONOMY_CSV`, étiquettes de détection) ; générée par `scripts/data_preparation/generate_taxonomy_subsets.py` |
| `taxonomy_small.csv` | sous-ensemble réduit | `scripts/run_experiments.py:41` (`TAXONOMIES`) ; générée par `scripts/data_preparation/generate_taxonomy_subsets.py` |
| `taxonomy_full.json` | forme JSON de la taxonomie complète | `scripts/migrate_taxonomy.py`, `scripts/update_corpus_taxonomy.py` |
| `mock_taxonomy_cards.csv` | cartes de taxonomie factices (pédagogie/tests) | produite par `scripts/validation/create_mock_taxonomy_script.py:16` |
| `learning_data.json` | apprentissage continu de l'analyseur contextuel (poids de confiance ajustés par feedback) | `plugins/analysis_tools/logic/contextual_fallacy_analyzer.py:216,238` (chargement/sauvegarde) |
| `extract_sources.json.gz.enc` | **corpus chiffré canonique** — voir ci-dessous | `config/settings.py`, `core/bootstrap.py` (via `core/io_manager.load_extract_definitions`, mémoire uniquement) |
| `datasets/` | fixtures relocalisées sans lecteur | voir [`datasets/legacy_fixtures/README.md`](datasets/legacy_fixtures/README.md) |

## Corpus chiffré — discipline

`extract_sources.json.gz.enc` est le dataset chiffré canonique (discours politiquement
sensibles). Il se charge **en mémoire uniquement** via
`argumentation_analysis.core.io_manager.load_extract_definitions` (clé dérivée de
`TEXT_CONFIG_PASSPHRASE`, `.env`). **Aucun contenu, nom de source, compte de documents
ou identifiant de corpus n'apparaît ici** : la discipline complète vit dans la section
« Dataset Privacy Discipline » de [`CLAUDE.md`](../../CLAUDE.md) (jamais de plaintext
suivi, downstream gitignoré par défaut, IDs opaques sur les surfaces indexées).

## Amont / aval

- **Amont** : taxonomies Argumentum (sources CSV + JSON de provenance) ;
  `scripts/data_preparation/generate_taxonomy_subsets.py` génère small/medium depuis full ;
  `scripts/migrate_taxonomy.py` maintient la forme JSON.
- **Aval** : la détection de sophismes (adapter français, agents informels, API),
  l'évaluation (benchmarks, expériences), l'analyseur contextuel (learning data).

## Statut d'intégration

**vivant** — chaque fichier hors `datasets/legacy_fixtures/` a un lecteur mesuré
dans le dépôt. (`mock_taxonomy.csv`, orphelin nommé ici en #2088, a été retiré :
census complet dispatch R1069 — zéro lecteur littéral, zéro chaîne suffixe
(`mock_taxonomy_cards`/`_small` sont les produits nommés du script), zéro
itérateur `*.csv` sur `data/` ; hors-dépôt CoursIA/Argumentum insondable.)
