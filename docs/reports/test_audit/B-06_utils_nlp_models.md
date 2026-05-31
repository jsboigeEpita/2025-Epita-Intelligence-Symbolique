# B-06: Audit — `tests/unit/argumentation_analysis/utils/` + `nlp/` + `models/`

**Track**: B-06 #762 (Epic B #743)
**Date**: 2026-05-31
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique
**Scope**: 57 fichiers, 1128 tests collectés

---

## Méthodologie

Même classification a/b/c que B-01 à B-04. Le wiring se vérifie par grep `snake_case` dans `registry_setup.py`, `factory.py`, `workflows.py`. Pour les utilitaires (utils/), la catégorie naturelle est **(c) JUSTIFIÉ** car ce sont des helpers transversaux appelés par les agents/services wirés — ils ne sont pas des capabilities à part entière.

---

## Scoreboard

| Catégorie | Fichiers | Tests | % |
|-----------|----------|-------|---|
| **(a) Mort** | 3 | ~30 | 5% |
| **(b) Non-wiré** | 8 | ~120 | 14% |
| **(c) Justifié** | 46 | ~978 | 81% |

---

## Tableau de classification

### (a) DEAD — Composant sans consommateur

| # | Fichier | Composant testé | Pourquoi DEAD |
|---|---------|-----------------|---------------|
| 1 | `models/test_agent_communication_model.py` | `agent_communication_model` | Aucun import dans `argumentation_analysis/`. Le module existe mais n'est pas utilisé par le pipeline ni les agents wirés. Probablement un artefact du design initial du système de communication hiérarchique (pré-Lego). |
| 2 | `models/test_extended_belief_model.py` | `extended_belief_model` | Aucun import. Le modèle étendu de croyances n'est pas wiré dans le CapabilityRegistry (seul `jtms_service`/`belief_maintenance` l'est). |
| 3 | `models/test_investigation_session_model.py` | `investigation_session_model` | Aucun import. Modèle de session d'investigation probablement lié au module oracle (lui-même non wiré). |

### (b) UNWIRED — Utilitaires standalone ou scripts-only

| # | Fichier | Composant testé | Importé par | Pourquoi UNWIRED |
|---|---------|-----------------|-------------|-------------------|
| 1 | `dev_tools/test_code_formatting_utils.py` | `code_formatting_utils` | Aucun | Outil dev standalone. Pas importé par le pipeline. |
| 2 | `dev_tools/test_dev_tools_utilities.py` | `dev_tools.utilities` | Aucun | Idem. |
| 3 | `dev_tools/test_import_testing_utils.py` | `import_testing_utils` | Aucun | Idem. |
| 4 | `dev_tools/test_refactoring_utils.py` | `refactoring_utils` | Aucun | Idem. |
| 5 | `dev_tools/test_reporting_utils.py` | `dev_tools.reporting_utils` | Aucun | Idem. |
| 6 | `extract_repair/test_fix_missing_first_letter.py` | `fix_missing_first_letter` | Scripts (`run_fix_missing_first_letter.py`, `run_verify_extracts_llm.py`) | Utilitaire de réparation d'extraits. Pas wiré dans le CapabilityRegistry mais utilisé par des scripts de maintenance. **Borderline (c)** — outil de maintenance légitime. |
| 7 | `extract_repair/test_marker_repair_report.py` | `marker_repair_logic` | Scripts (`run_extract_repair.py`) | Idem — outil de réparation. |
| 8 | `test_tweety_error_analyzer.py` | `tweety_error_analyzer` | Pas trouvé dans le pipeline | Analyseur d'erreurs Tweety. Utilitaire de debug, probablement utilisé manuellement. |

### (c) JUSTIFIÉ — Infrastructure transversale

#### utils/core_utils/ (17 fichiers) — Infrastructure basique

Tous ces utilitaires sont des helpers bas niveau utilisés par les agents et services wirés. Ils ne sont pas des "capabilities" mais font partie du socle technique.

| # | Fichier | Composant testé | Rôle |
|---|---------|-----------------|------|
| 1 | `test_cli_utils.py` | `cli_utils` | Interface CLI pour les scripts |
| 2 | `test_code_manipulation_utils.py` | `code_manipulation_utils` | Manipulation AST/code |
| 3 | `test_crypto_utils.py` | `crypto_utils` | Chiffrement/déchiffrement dataset |
| 4 | `test_error_management.py` | `error_management` | Gestion centralisée des erreurs |
| 5 | `test_file_loaders.py` | `file_loaders` | Chargement fichiers (config, données) |
| 6 | `test_file_savers.py` | `file_savers` | Sauvegarde fichiers |
| 7 | `test_file_utils.py` | `file_utils` | Opérations fichiers génériques |
| 8 | `test_file_validation_utils.py` | `file_validation_utils` | Validation structure fichiers |
| 9 | `test_filesystem_utils.py` | `filesystem_utils` | Opérations filesystem |
| 10 | `test_json_utils.py` | `json_utils` | Sérialisation JSON |
| 11 | `test_logging_utils.py` | `logging_utils` | Configuration logging |
| 12 | `test_markdown_utils.py` | `markdown_utils` | Génération markdown (rapports) |
| 13 | `test_network_utils.py` | `network_utils` | Requêtes réseau |
| 14 | `test_parsing_utils.py` | `parsing_utils` | Parsing texte/structures |
| 15 | `test_path_operations.py` | `path_operations` | Manipulation chemins |
| 16 | `test_reporting_utils.py` | `reporting_utils` (core) | Utilitaires de rapport |
| 17 | `test_shell_utils.py` | `shell_utils` | Exécution commandes shell |
| 18 | `test_string_utils.py` | `string_utils` | Manipulation chaînes |
| 19 | `test_system_utils.py` | `system_utils` (core) | Info système |
| 20 | `test_text_utils.py` | `text_utils` | Normalisation/tokenisation texte |

#### utils/ racine (27 fichiers) — Utilitaires pipeline

| # | Fichier | Composant testé | Rôle |
|---|---------|-----------------|------|
| 1 | `test_analysis_comparison.py` | `analysis_comparison` | Comparaison résultats d'analyses (utilisé par reporting) |
| 2 | `test_async_manager.py` | `async_manager` | Gestion async (gathering, timeouts) |
| 3 | `test_config_utils.py` | `config_utils` | Recherche dans config sources |
| 4 | `test_config_validation.py` | `config_validation` | Validation configuration |
| 5 | `test_correction_utils.py` | `correction_utils` | Correction d'extraits |
| 6 | `test_data_generation.py` | `data_generation` | Génération données de test |
| 7 | `test_data_loader.py` | `data_loader` | Chargement données (dataset chiffré) |
| 8 | `test_data_processing_utils.py` | `data_processing_utils` | Traitement/groupement résultats |
| 9 | `test_debug_utils.py` | `debug_utils` | Affichage debug extraits sources |
| 10 | `test_error_estimation.py` | `error_estimation` | Estimation d'erreurs |
| 11 | `test_informal_integration.py` | `informal_integration` | Intégration module informel |
| 12 | `test_metrics_aggregation.py` | `metrics_aggregation` | Agrégation métriques |
| 13 | `test_metrics_calculator.py` | `metrics_calculator` | Calcul métriques |
| 14 | `test_metrics_extraction.py` | `metrics_extraction` | Extraction métriques |
| 15 | `test_performance_monitoring.py` | `performance_monitoring` | Monitoring performance |
| 16 | `test_report_generator.py` | `report_generator` | Génération rapports |
| 17 | `test_system_utils.py` | `system_utils` | Utilitaires système |
| 18 | `test_taxonomy_loader.py` | `taxonomy_loader` | Chargement taxonomie (8 familles) |
| 19 | `test_text_processing.py` | `text_processing` | Découpage texte en arguments |
| 20 | `test_version_validator.py` | `version_validator` | Validation version SK |
| 21 | `test_visualization_generator.py` | `visualization_generator` | Génération visualisations |

#### utils/dev_tools/ (utilisés en dev, justifiés)

| # | Fichier | Composant testé | Rôle |
|---|---------|-----------------|------|
| 1 | `test_code_validation.py` | `code_validation` | Validation code |
| 2 | `test_encoding_utils.py` | `encoding_utils` | Encodage |
| 3 | `test_env_checks.py` | `env_checks` | Vérification environnement |
| 4 | `test_format_utils.py` | `format_utils` | Formatage |

#### nlp/ (1 fichier)

| # | Fichier | Composant testé | Rôle |
|---|---------|-----------------|------|
| 1 | `test_embedding_utils.py` | `embedding_utils` | Utilitaires embeddings (chunking, vectorisation) |

---

## Récit du framework — 3 épisodes

### Épisode 1 : Le socle utilitaire du monolithe (~2025-Q1)

Le répertoire `utils/core_utils/` (20 fichiers, ~400 tests) cristallise le **socle utilitaire** du projet original. Ce sont les briques de base qui existaient avant toute architecture agentique : `text_utils.py` (normalisation, tokenisation), `file_loaders.py` (chargement de données), `crypto_utils.py` (chiffrement dataset), `logging_utils.py` (configuration logging). Ces utilitaires sont toujours actifs — le dataset chiffré passe par `crypto_utils`, le logging pipeline par `logging_utils`. Ils ont survécu à toutes les refontes architecturales car ils sont agnostiques de l'architecture au-dessus.

**Trace dans les tests** : `test_crypto_utils.py` teste le chiffrement/déchiffrement AES — fonctionnalité critique pour la privacy du dataset. `test_text_utils.py` teste `normalize_text` et `tokenize_text` — utilisés par l'extract pipeline. Le pipeline actuel les appelle indirectement via les agents wirés.

### Épisode 2 : L'explosion des métriques et du reporting (~2025-Q2-Q3)

Le répertoire `utils/` racine contient un **bouquet de métriques et de reporting** qui témoigne d'une phase d'enrichissement progressif : `metrics_calculator.py`, `metrics_aggregation.py`, `metrics_extraction.py`, `error_estimation.py`, `performance_monitoring.py`, `report_generator.py`, `visualization_generator.py`. Ces modules ont été créés pour mesurer et rapporter les performances du pipeline à une époque où les métriques étaient calculées manuellement dans des scripts.

**Trace dans les tests** : Les 7 fichiers de métriques (~150 tests) testent des calculs isolés (accuracy, precision, recall) qui sont aujourd'hui partiellement couverts par les invoke callables du CapabilityRegistry (ex: `quality_scoring` via `QualityScoringPlugin`). Le recouvrement est partiel — les utilitaires de métriques calculent des agrégats cross-corpus qui ne sont pas dans le CapabilityRegistry.

### Épisode 3 : Les models orphelins (~2025-Q1-Q2)

Les 3 fichiers dans `models/` (`agent_communication_model.py`, `extended_belief_model.py`, `investigation_session_model.py`) sont des **data models sans consommateur**. Ils représentent des designs qui n'ont jamais été complètement intégrés : le modèle de communication agent-à-agent (pré-`communication/` middleware), le modèle de croyance étendu (pré-JTMS `belief_maintenance`), et le modèle de session d'investigation (pré-sherlock/oracle). Le pipeline actuel a des implémentations différentes : `communication/` pour le messaging, `jtms_service` pour les croyances, et `sherlock_modern_workflow` pour l'investigation.

**Trace dans les tests** : Les tests de `agent_communication_model` testent des structures de messages (Message, Channel, CommunicationMiddleware) qui n'ont pas été adoptées. `extended_belief_model` test des structures de croyance plus riches que le JTMS simple. `investigation_session_model` test des sessions d'investigation qui n'ont pas été wirées dans le pipeline Cluedo.

---

## Actions recommandées

### Priorité HAUTE — Models orphelins

| Action | Fichier | Impact |
|--------|---------|--------|
| Archiver ou supprimer | `models/test_agent_communication_model.py` | ~10 tests morts |
| Archiver ou supprimer | `models/test_extended_belief_model.py` | ~10 tests morts |
| Archiver ou supprimer | `models/test_investigation_session_model.py` | ~10 tests morts |

Les 3 modules sources (`argumentation_analysis/models/`) n'ont aucun consommateur dans le pipeline. Si les data models sont jugés utiles pour une future extension, les conserver mais marquer les tests `@pytest.mark.skip("orphan model — no pipeline consumer")`.

### Priorité BASSE — Dev tools

Les 8 fichiers `dev_tools/` ne sont pas importés par le pipeline mais sont des utilitaires de développement légitimes (validation code, vérification environnement). **Pas d'action recommandée** — les conserver.

### Priorité BASSE — Métriques overlap

Les 7+ fichiers de métriques ont un recouvrement partiel avec les invoke callables wirés. Une consolidation future pourrait réduire ce packet, mais ce n'est pas une urgence.

---

*Généré par Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track B-06 #762 — Epic B #743*
