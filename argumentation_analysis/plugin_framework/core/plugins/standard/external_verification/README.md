# `plugin_framework/core/plugins/standard/external_verification/` — plugin de fact-checking (simulé)

## Rôle et frontière

Plugin de vérification factuelle multi-sources d'affirmations : statuts de vérification à 7 états, fiabilité par domaine, cache mémoire 24 h (`plugin.py:140`), sémaphore de concurrence (:209). Déclaré par `plugin.yaml` (entrypoint `plugin.py`, classe `ExternalVerificationPlugin`, dépendance `aiohttp` :13, capacité `verify_claims` :16).

N'est **pas** :

- un module branché à de vraies APIs — les recherches Tavily/SearXNG sont **simulées** : `_search_tavily` (:356) et `_search_searxng` (:368) retournent des fixtures `example-tavily.com` (:360, :363) alors même que des clés API sont lues ;
- le porteur canonique des statuts — `VerificationStatus` est dupliqué avec divergence dans le shim aval `services/fact_verification_service.py:22-41` ;
- un plugin découvrable — aucun chargeur ne peut l'activer (voir Statut).

## Composants publics

Tous dans `plugin.py` :

- `VerificationStatus` (:30, enum 7 états), `SourceReliability` (:42, 5 niveaux), `VerificationSource` (:53), `FactVerificationResult` (:84) ;
- `ExternalVerificationPlugin(BasePlugin)` (:118) — importe le **vrai** `BasePlugin` de `core/plugins/interfaces.py` (contrairement à son frère `taxonomy_explorer`) ;
- capacité principale `verify_claims` (:200) ; pipeline : `_verify_one_claim` (:246) → recherche simulée (:356-368) → `_analyze_sources` (:399) / `_calculate_relevance` (:430) / `_analyze_source_stance` (:451) → `_determine_verification_status` (:489) → `_analyze_fallacy_implications` (:563).

## Points d'entrée valides

Imports module-level production (chargement du module, pas construction d'instance) :

- `orchestration/fact_checking_orchestrator.py:31-33` — récupération via `plugin_registry.get("external_verification")` (:132) quand un registre est fourni ;
- `agents/tools/analysis/fallacy_family_analyzer.py:24-25` — injection optionnelle au constructeur (:127-129).

**Aucune instanciation en production** (les tests mockent le registre) ; aucun mécanisme de chargement dynamique ne l'active.

## Amont / aval

- Amont : `FactualClaim`/`ClaimVerifiability` de `agents/tools/analysis/fact_claim_extractor.py` (`plugin.py:19-22`) ; une instance `TaxonomyExplorerPlugin` est attendue au constructeur (:125).
- Aval : `FactCheckingOrchestrator` et `FallacyFamilyAnalyzer` si injectés ; le shim `services/fact_verification_service.py` (docstring « déléguant au plugin » :6) **n'importe pas ce plugin** et ré-implemente en parallèle.

## Statut d'intégration

**expérimental** — importé pour ses types mais jamais construit en production par défaut ; ses I/O externes sont simulés. Corroboré par l'audit `docs/reports/subjects_audit/C-06_indexation_automatisation.md` (E1 HIGH : « brancher un ExternalVerificationPlugin fonctionnel ») alors que `docs/architecture/fallacy_operational_plan.md:688-689` annonce la migration « TERMINÉ ».

De plus, **aucun des deux chargeurs ne peut l'activer** : `core/plugin_loader.py:33` construit des modules `src.core.plugins.standard.*` (préfixe mort post-#34, ImportError avalée :51-54) ; `core/plugins/plugin_loader.py:33-38` scanne des `plugin_manifest.json` alors que ce plugin déclare `plugin.yaml`.

## Artefacts et lecteurs

Aucun fichier écrit ; cache mémoire uniquement (expiration 24 h :140, plafond 100 entrées).

## Tests représentatifs

Aucun test unitaire direct de la classe (toujours mockée). Les suites qui l'entourent :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/orchestration/test_fact_checking_orchestrator.py -v
```

(registre mocké :74-75 ; chemins d'erreur registry :313-329) et `tests/test_orchestration_integration.py:214`.

## Frères et parent

- Parent `standard/` : **pas de README** ; son `plugin_manifest.json:7` pointe vers un `main.py` inexistant.
- Grand-parent [`core/plugins/README.md`](../../README.md) : existe mais décrit le mécanisme manifest JSON, incompatible avec les `plugin.yaml` réels.
- Frère : [`taxonomy_explorer/`](../taxonomy_explorer/README.md) (documenté dans ce même lot).

## Limites connues

- `import aiohttp` (:8) jamais utilisé — dépendance déclarée (`plugin.yaml:13`) pour rien ;
- `taxonomy_plugin` injecté (:125) puis stocké (:142) mais **jamais consommé** dans le fichier ;
- recherches simulées malgré les clés API lues — les résultats factices alimentent tout le pipeline en aval ;
- duplication divergente `VerificationStatus`/`SourceReliability` avec `services/fact_verification_service.py:22-104` (maps de fiabilité inversées l'une par rapport à l'autre).

Ces anomalies sont signalées en issues séparées ; rien n'est corrigé ici.
