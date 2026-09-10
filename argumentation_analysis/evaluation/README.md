# `evaluation/` — benchmarks, juge LLM et infrastructure privacy des résultats

## Rôle et frontière

L'infrastructure d'évaluation : benchmarks multi-modèles, juge LLM, minage de patterns, et — partie **critique pour tout le dépôt** — les utilitaires privacy qui opacifient les résultats avant toute sortie git (`opaque_id`, `sanitize_state`, `leak_patterns`).

N'est **pas** consommé par le pipeline d'analyse : c'est une couche a posteriori, alimentée par les states/résultats produits en amont. Le répertoire `results/` est **entièrement gitignoré** (discipline dataset, CLAUDE.md — outputs de benchmark, scores juge, snapshots n'y vivent jamais).

## Composants publics (inventaire raisonné)

- **Runners** (points d'entrée script) : `run_agentic_eval.py`, `run_baseline_benchmark.py`, `run_llm_judge.py`, `run_iteration.py`, `run_provenance.py`, `run_synergy_analysis.py` ;
- **Benchmarks** : `benchmark_runner.py` (BenchmarkRunner), `multi_model_benchmark.py`, `fallacy_benchmark.py`, `plugin_benchmark.py`, `conversational_benchmark.py` ;
- **Juge & analyse** : `judge.py` (juge LLM), `capability_eval.py`, `synergy_analyzer.py`, `pattern_mining.py`, `encompassment.py`, `designate_contract.py` ;
- **Socle** : `model_registry.py` (ModelRegistry), `result_collector.py` ;
- **Privacy (load-bearing)** : `opaque_id(source_name, salt=None)` (`opaque_id.py:34`) — IDs opaques des sources ; `sanitize_state(state)` (`sanitize_state.py:411`) — retire les champs nominatifs en gardant les agrégats quantitatifs ; `leak_patterns.py` — motifs de fuite chargés par le gate CI privacy **via importlib** (`scripts/security/scan_indexed_surfaces.py:51,64` — chargement sans exécuter le `__init__` du package pour éviter de tirer la stack LLM) ;
- `corpus/` — fixtures de corpus ; `results/` — sorties locales (gitignoré).

## Points d'entrée valides

- [`scripts/run_benchmark.py:34`](../../scripts/run_benchmark.py) — `from argumentation_analysis.evaluation import …` ;
- [`scripts/benchmark/multi_model_run.py:103,165`](../../scripts/benchmark/multi_model_run.py) — `BenchmarkRunner`, `ModelRegistry` ;
- [`scripts/dataset/run_corpus_batch.py`](../../scripts/dataset/run_corpus_batch.py) — `:42` `run_provenance.provenance_block`, `:278` `opaque_id`, `:506` `sanitize_state` ;
- [`scripts/dataset/add_extract.py:162`](../../scripts/dataset/add_extract.py) — `opaque_id` ; [`scripts/dataset/build_pattern_report.py:206`](../../scripts/dataset/build_pattern_report.py) — `pattern_mining` ;
- CI : `scripts/security/scan_indexed_surfaces.py:51,64` charge `leak_patterns` (gate privacy des commits et textes GitHub-indexés).

## Amont / aval

- Amont : states/résultats des pipelines (via `state_snapshot`), config modèles (`model_registry`), dataset chiffré (in-memory).
- Aval : rapports locaux sous `results/` (gitignorés), rapports agrégés curated à la main, gate CI privacy.

## Statut d'intégration

**actif — critique** : l'infrastructure privacy (`opaque_id`/`sanitize_state`/`leak_patterns`) est le socle du gate CI #2014 et de la discipline dataset ; les runners sont consommés par les scripts benchmark/dataset ci-dessus.

## Artefacts et lecteurs

`results/` (gitignoré — benchmark outputs, LLM judge scores, baselines, state snapshots). Tout partage passe par un rapport agrégé curated avec IDs opaques.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/evaluation/ -v
```

Suite dédiée sous `tests/unit/argumentation_analysis/evaluation/` (benchmark_runner, capability_eval, conversational, designate_contract #1983, CLI runners…).

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `evaluation/`. Frères : [`analytics/`](../analytics/README.md) (analyse des résultats), [`services/`](../services/README.md).

## Limites connues

- `results/` gitignoré : aucun rapport n'est partageable sans curation manuelle — voulu (discipline privacy), mais aucun agrégateur automatisé vers une surface partageable n'existe ;
- le salt d'`opaque_id` dépend de la config (sel #1998 en attente d'arbitrage utilisateur) ;
- la docstring du gate CI (`scan_indexed_surfaces.py:23`) encode le contrat : seuls des compteurs peuvent sortir de `leak_patterns` — toute évolution de `leak_patterns` doit vérifier le gate en CI.
