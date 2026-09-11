# `plugin_framework/core/plugins/standard/taxonomy_explorer/` — exploration de la taxonomie des sophismes

## Rôle et frontière

Exploration de la taxonomie des 8 familles de sophismes : charge `data/fallacy_families.yaml` (`_load_families`, `plugin.py:91`), mappe chaque sophisme de la taxonomie à une famille par scoring de patterns, expose des requêtes et des statistiques. Déclaré par `plugin.yaml` (entrypoint `plugin.py`, classe `TaxonomyExplorerPlugin`, 5 capacités :13-67).

N'est **pas** :

- un détecteur autonome — la détection est déléguée au `TaxonomySophismDetector` global via `get_global_detector` (`plugin.py:27-30`) ;
- le service effectivement consommé par défaut — le shim `services/fallacy_taxonomy_service.py` bypass ce plugin (docstring « déléguant au plugin » :6, zéro import du plugin) ;
- le navigateur de la taxonomie CoursIA 1408 nœuds (besoins distincts, voir `2.3.2-detection-sophismes/STATUS.md`).

## Composants publics

Tous dans `plugin.py` :

- `FallacyFamily` (:34, BaseModel), `ClassifiedFallacy` (:47) ;
- `TaxonomyExplorerPlugin` (:62) — capacités async : `list_families` (:145), `get_family_details` (:152), `find_fallacies_by_family` (:157), `get_fallacy_details` (:176), `get_full_taxonomy` (:185), plus `detect_and_classify` (:195) et `get_family_statistics` (:249).

## Points d'entrée valides

Imports module-level production (aucune instanciation) :

- `orchestration/fact_checking_orchestrator.py:28-30` — via `plugin_registry.get("taxonomy_explorer")` (:131) quand un registre est fourni ;
- `agents/tools/analysis/fallacy_family_analyzer.py:20-21` — injection optionnelle (:127) ;
- son frère `external_verification/plugin.py:23-25`.

**La donnée, elle, est réellement consommée — sans le plugin** : `reporting/restitution/act1_framing_plugin.py:74-88` lit `data/fallacy_families.yaml` directement (choix documenté #1914 : rester disjoint du SK `plugin_framework` et ses dépendances JVM lourdes, échec bruyant si le fichier bouge), et les tests FB-15 chargent les mêmes chemins réels.

## Amont / aval

- Amont : `agents/core/informal/taxonomy_sophism_detector.py` (détecteur global) ; `data/fallacy_families.yaml` (8 familles, enrichi #1034 FB-15 D3/D6/D7).
- Aval : `external_verification` (l'instance injectée y reste non consommée), `FallacyFamilyAnalyzer`, la restitution act1 (via fichier).

## Statut d'intégration

Deux statuts distincts :

- **la classe `TaxonomyExplorerPlugin` : `expérimental`** — jamais instanciée hors injection de test ; et comme pour son frère, aucun chargeur ne peut la découvrir (`core/plugin_loader.py:33` préfixe module `src.core.plugins.standard.*` mort post-#34, ImportError avalée ; `core/plugins/plugin_loader.py:33-38` scanne des `plugin_manifest.json` alors que ce plugin déclare `plugin.yaml`) ;
- **la donnée `data/fallacy_families.yaml` : `actif`** — consommée par la production (restitution #1914, lecture directe) et gardée par les tests FB-15 (#1034, chemins réels non mockés).

## Artefacts et lecteurs

Aucune écriture ; lecture de `data/fallacy_families.yaml` (:91) et de la taxonomy CSV via `self.detector._get_taxonomy_df()` (:111, :187).

## Tests représentatifs

Le plugin lui-même n'a aucun test direct (mocks dans `tests/unit/argumentation_analysis/orchestration/test_fact_checking_orchestrator.py:499-542`). La **donnée** est couverte par :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/orchestration/test_fb15_fr_detection_enrichment.py -v
```

## Frères et parent

- Parent `standard/` : **pas de README** ; son `plugin_manifest.json:7` pointe vers un `main.py` inexistant.
- Grand-parent [`core/plugins/README.md`](../../README.md) : drifté (mécanisme manifest JSON vs `plugin.yaml` réels).
- Frère : [`external_verification/`](../external_verification/README.md).

## Limites connues

- **Bug latent** : `detect_and_classify` appelle `self._calculate_context_relevance(text, family_info)` (:210) alors que la méthode définie s'appelle `_calculate_contextual_relevance` (:293) — `AttributeError` dès qu'un sophisme détecté a une famille mappée ; invisible car jamais exécuté en production (signalé en issue séparée) ;
- `BasePlugin` **local factice** (:21-23, commenté comme tel :17-20) au lieu d'importer `core/plugins/interfaces.py` — un `issubclass` de chargeur échouerait ; divergence avec `external_verification` qui importe le vrai ;
- accès aux privés du détecteur (`detector._get_taxonomy_df()` :111, :187) ;
- duplication `ClassifiedFallacy` avec le shim `services/fallacy_taxonomy_service.py:31-44`.
