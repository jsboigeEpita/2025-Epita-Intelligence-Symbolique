# `plugin_framework/core/plugins/standard/external_verification/` — plugin de fact-checking (simulé)

## Rôle et frontière

Plugin de vérification factuelle multi-sources d'affirmations : statuts de vérification à 7 états, fiabilité par domaine, cache mémoire 24 h, sémaphore de concurrence. Déclaré par `plugin.yaml` (entrypoint `plugin.py`, classe `ExternalVerificationPlugin`, capacité `verify_claims`).

N'est **pas** :

- un module branché à de vraies APIs — les recherches sont **simulées** et le disent : `_search_sources` journalise un WARNING quand des clés API sont configurées (le cas où la simulation pourrait se lire à tort comme une recherche réelle) et retourne les fixtures explicites de `_simulate_search` ;
- le porteur canonique des statuts — depuis #2101, les enums `VerificationStatus`/`SourceReliability` et la carte de fiabilité par domaine viennent de la **source unique** `services/fact_verification_service.py` (surface de production mesurée), que ce plugin importe ;
- un plugin découvrable — aucun chargeur ne peut l'activer (voir Statut).

## Composants publics

Tous dans `plugin.py` :

- enums **importés** de `services/fact_verification_service.py` (`VerificationStatus`, `SourceReliability` + `SOURCE_RELIABILITY_MAP`), `VerificationSource`, `FactVerificationResult` ;
- `ExternalVerificationPlugin(BasePlugin)` — importe le **vrai** `BasePlugin` de `core/plugins/interfaces.py` (contrairement à son frère `taxonomy_explorer`) ; constructeur `(api_config)` sans injection de taxonomie (#2101 : l'injection `taxonomy_plugin` n'était jamais consommée) ;
- capacité principale `verify_claims` ; pipeline : `_verify_one_claim` → recherche simulée annoncée → `_analyze_sources` / `_calculate_relevance` / `_analyze_source_stance` → `_determine_verification_status` → `_analyze_fallacy_implications`.

## Points d'entrée valides

**Aucun importeur de production** — depuis #2101, les deux derniers imports module-level (orchestrateur, analyzer) ont été retirés : le premier était mort (nom jamais référencé), le second soutenait une annotation de type mensongère (l'objet runtime est le service shim, jamais ce plugin). Le plugin rejoint un futur consommateur par import direct — le branchement réel est l'arbitrage E1 (audit C-06).

## Amont / aval

- Amont : `FactualClaim` de `agents/tools/analysis/fact_claim_extractor.py` ; enums + carte de fiabilité de `services/fact_verification_service.py` (source unique #2101).
- Aval : personne en production ; garde né-rouge `tests/unit/argumentation_analysis/services/test_external_verification_honesty_2101.py`.

## Statut d'intégration

**expérimental** — jamais construit en production ; ses I/O externes sont simulées et annoncées. Corroboré par l'audit `docs/reports/subjects_audit/C-06_indexation_automatisation.md` (E1 HIGH : « brancher un ExternalVerificationPlugin fonctionnel ») alors que `docs/architecture/fallacy_operational_plan.md:688-689` annonce la migration « TERMINÉ ».

De plus, **il n'existe plus de chargeur pour l'activer** : les trois mécanismes de découverte du paquet ont été retirés (#2099, aucun appelant de production — les deux chargeurs cités historiquement ne pouvaient de toute façon pas le voir). Il rejoint le système par import direct, comme son frère `taxonomy_explorer`.

## Artefacts et lecteurs

Aucun fichier écrit ; cache mémoire uniquement (expiration 24 h, plafond 100 entrées).

## Tests représentatifs

Garde d'honnêteté directe de la classe (construction sans injection morte, simulation annoncée, source unique des enums, dépendances mortes absentes) : `tests/unit/argumentation_analysis/services/test_external_verification_honesty_2101.py`. Les suites qui l'entourent :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/orchestration/test_fact_checking_orchestrator.py -v
```

## Frères et parent

- Parent `standard/` : **pas de README** ; son `plugin_manifest.json:7` pointe vers un `main.py` inexistant.
- Grand-parent [`core/plugins/README.md`](../../README.md) : existe mais décrit le mécanisme manifest JSON, incompatible avec les `plugin.yaml` réels.
- Frère : [`taxonomy_explorer/`](../taxonomy_explorer/README.md) (documenté dans ce même lot).

## Limites connues

Corrigées par #2101 (mesuré sur `9dc3fd86`, corrigé sur cette branche) :

- ~~`import aiohttp` jamais utilisé — dépendance déclarée (`plugin.yaml`) pour rien~~ — import et déclaration retirés ;
- ~~`taxonomy_plugin` injecté puis stocké mais jamais consommé~~ — paramètre retiré du constructeur ;
- ~~recherches simulées malgré les clés API lues — les résultats factices alimentent tout le pipeline en aval~~ — les fixtures provider-shaped (`example-tavily.com`) sont retirées : une seule simulation explicite, annoncée WARNING si clés configurées ;
- ~~duplication divergente `VerificationStatus`/`SourceReliability` avec `services/fact_verification_service.py` (maps inversées)~~ — le shim est la source unique, le plugin importe et dérive sa vue par inversion.

Reste ouvert : le branchement réseau réel (arbitrage E1, audit C-06) — la simulation est désormais assumée, pas cachée.
