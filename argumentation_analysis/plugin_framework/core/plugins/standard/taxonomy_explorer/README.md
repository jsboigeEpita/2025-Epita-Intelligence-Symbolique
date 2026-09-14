# `plugin_framework/core/plugins/standard/taxonomy_explorer/` — exploration de la taxonomie des sophismes

## Rôle et frontière

Exploration de la taxonomie des 8 familles de sophismes : charge `data/fallacy_families.yaml` (`_load_families`, `plugin.py:83`), mappe chaque sophisme de la taxonomie à une famille par scoring de patterns, expose des requêtes et des statistiques. Déclaré par `plugin.yaml` (entrypoint `plugin.py`, classe `TaxonomyExplorerPlugin`, 5 capacités :13-67).

N'est **pas** :

- un détecteur autonome — la détection est déléguée au `TaxonomySophismDetector` global via `get_global_detector` (`plugin.py:19-22`, utilisé `:70`) ;
- le service effectivement consommé par défaut — le shim `services/fallacy_taxonomy_service.py` bypass ce plugin (docstring « déléguant au plugin » :6, zéro import du plugin) ;
- le navigateur de la taxonomie CoursIA 1408 nœuds (besoins distincts, voir `2.3.2-detection-sophismes/STATUS.md`).

## Composants publics

Tous dans `plugin.py` :

- `FallacyFamily` (:26, BaseModel), `ClassifiedFallacy` (:39) ;
- `TaxonomyExplorerPlugin` (:54) — capacités async : `list_families` (:137), `get_family_details` (:144), `find_fallacies_by_family` (:149), `get_fallacy_details` (:168), `get_full_taxonomy` (:177), plus `detect_and_classify` (:187) et `get_family_statistics` (:241).

## Points d'entrée valides

Imports module-level production (aucune instanciation) :

- `orchestration/fact_checking_orchestrator.py:28-30` — via `plugin_registry.get("taxonomy_explorer")` (:131) quand un registre est fourni ;
- `agents/tools/analysis/fallacy_family_analyzer.py:20-21` — injection optionnelle (:127) ;
- son frère `external_verification/plugin.py:23-25`.

Depuis le retrait des mécanismes de découverte (#2099), il n'existe **plus** de
chargeur pour ce plugin : il rejoint le système par ces imports directs — chemin
gardé par `tests/unit/argumentation_analysis/test_plugin_framework.py::TestRealPluginsByDirectImport`
(instanciation réelle + exécution d'une capacité).

**La donnée, elle, est réellement consommée — sans le plugin** : `reporting/restitution/act1_framing_plugin.py:74-88` lit `data/fallacy_families.yaml` directement (choix documenté #1914 : rester disjoint du SK `plugin_framework` et ses dépendances JVM lourdes, échec bruyant si le fichier bouge), et les tests FB-15 chargent les mêmes chemins réels.

## Amont / aval

- Amont : `agents/core/informal/taxonomy_sophism_detector.py` (détecteur global) ; `data/fallacy_families.yaml` (8 familles, enrichi #1034 FB-15 D3/D6/D7).
- Aval : `external_verification` (l'instance injectée y reste non consommée), `FallacyFamilyAnalyzer`, la restitution act1 (via fichier).

## Statut d'intégration

Deux statuts distincts :

- **la classe `TaxonomyExplorerPlugin` : `expérimental`** — jamais instanciée en production (les sites ci-dessus l'importent pour injection) ; elle sous-classe désormais **réellement** le contrat canonique `core/plugins/interfaces.py` (corrigé #2099 — elle portait une copie locale factice, `issubclass` mesuré False avant, True après) ;
- **la donnée `data/fallacy_families.yaml` : `actif`** — consommée par la production (restitution #1914, lecture directe) et gardée par les tests FB-15 (#1034, chemins réels non mockés).

## Artefacts et lecteurs

Aucune écriture ; lecture de `data/fallacy_families.yaml` (:86) et de la taxonomy CSV via `self.detector._get_taxonomy_df()` (:103, :179).

## Tests représentatifs

Le plugin n'a pas de test métier dédié (mocks dans `tests/unit/argumentation_analysis/orchestration/test_fact_checking_orchestrator.py:499-542`), mais depuis #2099 son instanciation réelle et une capacité (`list_families`) sont gardées dans `tests/unit/argumentation_analysis/test_plugin_framework.py::TestRealPluginsByDirectImport`, et son chemin nominal `detect_and_classify` est couvert par `tests/unit/argumentation_analysis/test_taxonomy_explorer_detect_2100.py` (#2100/#2189). La **donnée** est couverte par :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/orchestration/test_fb15_fr_detection_enrichment.py -v
```

## Frères et parent

- Parent `standard/` : [`../README.md`](../README.md).
- Grand-parent [`core/plugins/README.md`](../../README.md) — documente le retrait des mécanismes de découverte (#2099).
- Frère : [`external_verification/`](../external_verification/README.md).

## Limites connues

- accès aux privés du détecteur (`detector._get_taxonomy_df()` :103, :179) ;
- duplication `ClassifiedFallacy` avec le shim `services/fallacy_taxonomy_service.py:31-44`.

Historique résolu : l'appel mort `_calculate_context_relevance` (corrigé #2189, #2100) ; le `BasePlugin` local factice (corrigé #2099 — import du contrat canonique).
