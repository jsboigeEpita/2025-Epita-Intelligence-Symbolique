# Cartographie des instruments

**Ce que ce document est.** Une carte `objectif → instruments`. Pour chaque question que le
projet se pose, elle nomme **tous** les dispositifs qui y répondent, parce que la situation
normale ici n'est pas « un objectif, un outil » : c'est **un objectif, plusieurs outils qui
ne se connaissent pas**. Un an et demi de construction a laissé des instruments qui se
juxtaposent, et le coût n'est pas la redondance — c'est qu'on en trouve **un** et qu'on
conclut de lui à la question.

**Ce que ce document n'est pas.** Un inventaire de fichiers (les README de chaque répertoire
le font mieux, voir #2088), ni une promesse d'exhaustivité. Une ligne absente ici signifie
« pas encore cartographié », jamais « n'existe pas ».

## Règle de rot

Une doc qui met en garde est le pire site de pourriture : elle est crue et jamais
re-mesurée. Donc :

1. **Chaque ligne porte la date de sa dernière mesure firsthand** et le geste qui l'a
   produite. Sans date, la ligne est périmée par défaut.
2. **Aucun chiffre n'est recopié d'un rapport** — ni d'une PR, ni d'un résumé, ni de ce
   fichier lui-même à la relecture suivante. On rejoue.
3. Un instrument dont la dernière mesure a plus de **3 mois** est marqué `⚠ non re-mesuré`
   et sa conclusion ne peut pas être citée comme un état courant.

---

## Objectif : « qu'apporte notre orchestration face à un jugement zero-shot ? »

**Au moins deux instruments, de natures différentes, sans référence croisée.** C'est le cas
d'école qui a motivé cette carte : le 18/09 j'ai trouvé le premier, conclu de lui, et
affirmé à tort qu'aucune mesure récente n'existait.

| Instrument | Nature | Ce qu'il répond | Dernière mesure firsthand |
|---|---|---|---|
| `scripts/measure_both_paths_vs_zeroshot.py` | **externe**, head-to-head sur corpus : DAG `spectacular` / conversationnel / référence zero-shot | quel *chemin d'orchestration* bat l'autre, dimension par dimension | **run : 31/05/2026** ⚠ non re-mesuré · imports revérifiés le 18/09 (3 points d'entrée OK) · référence : `docs/reports/BASELINE_0SHOT_2026-05-16.md` |
| `reporting/restitution/conclusion_salience.py` (#1914) | **interne**, déterministe, dérivé de l'état, rendu dans l'Acte III | ce que *ce run-ci* a établi qu'une lecture zero-shot forte ne donne pas | **vivant, rendu le 18/09** sur run corpus réel (2 documents) |

**Différence à ne pas confondre** : le premier compare des *chemins* entre eux et a besoin
d'une référence zero-shot enregistrée ; le second déclare un *surplus par run*, sans jamais
exécuter de zero-shot — il dérive le surplus de la nature des trouvailles (réfutations
formelles, exclusions de Dung, relations structurelles, convergences portant au moins un
signal non-LLM).

**Trou mesuré le 18/09.** Le surplus #1914 est calculé sur l'objet d'évidence de l'Acte III
et rendu en prose, mais **il n'est jamais persisté dans l'état** : recherche sur les dumps
complets de deux documents (≈ 500 Ko chacun) → **0 occurrence** de `surplus` / `salience` /
`ranked` / `load_bearing`. Conséquence : le surplus est **lisible document par document,
non agrégeable à l'échelle d'une campagne**. On ne peut pas aujourd'hui répondre « sur N
documents, combien de fois l'orchestration a-t-elle apporté un surplus non procédural ».

---

## Objectif : « ce run a-t-il tourné dans un environnement vivant ? »

| Instrument | Nature | Dernière mesure firsthand |
|---|---|---|
| `evaluation/env_manifest.py` — `environment_manifest()` / `render_environment_stamp()` (#2282) | sonde run-level (jvm / llm / torch / overrides), imprimée sur stdout | **18/09** — `jvm: started (76 jars, target=1.31)` à côté de résultats réels |

**Limite connue et réparée.** Le tampon est imprimé en fin de `main()` — position porteuse
(`jvm_started` doit décrire le run qui a eu lieu) mais qui le rendait muet sur un run qui
**avorte**, c'est-à-dire le cas où l'environnement est le suspect n°1. Chemin d'abort
instrumenté dans la PR #2294.

**Pourquoi cet instrument existe** : #2276 a rendu 11 phases sur une JVM morte sans que rien
ne le dise. Une CI verte ne certifie jamais l'environnement d'un run de production.

---

## Objectif : « les modules spécialisés décident-ils quelque chose ? »

| Instrument | Nature | Dernière mesure firsthand |
|---|---|---|
| Epic #1644 — carte des 4 modes (échoué / aplati / témoin-sans-décideur / producteur cassé) | classification manuelle, re-dérivée par énumération des phases et des writers | corps de l'Epic ; **23 sous-issues fermées / 4 modules ouverts** au 18/09 |
| note de portée déterministe de l'Acte III | rend en prose les axes **non aboutis** sur ce texte | **18/09** — a nommé « la force pondérée des attaques, les attaques collectives » |
| `tests/.../test_one_capability_surface_1842.py` | garde : tout définisseur non câblé rougit | voir CLAUDE.md (compte daté, à re-mesurer avant citation) |

⚠ **L'existence d'un test unitaire ne garantit rien de l'intégration réelle.** C'est la leçon
JVM : des suites vertes coexistaient avec `initialize_jvm()` rendant `False` en production.
Un test est une boussole pour l'archéologie, pas une preuve de câblage.

---

## Objectif : « une bande de tests a-t-elle réellement tourné ? »

| Instrument | Nature | Dernière mesure firsthand |
|---|---|---|
| `.github/workflows/ci.yml` — gate par push | désélectionne `requires_api` | — |
| `.github/workflows/requires_api_band.yml` (#2286) | lane hebdo, sélectionne ce que le gate désélectionne | **18/09** — 7/8 passed, 0 skip de signature JVM |
| gardes fail-loud de la lane | #1556 (compteurs sur `<testsuite>`), #1799 (rapport absent + clés configurées = échec), #1385/#1873 (famille de signatures JVM), bande morte (`total == 0` avec clés) | 18/09 |

**Portée mesurée le 18/09**, à re-mesurer avant citation : `-m "requires_api and llm_light"`
sur l'argv de la lane → 8 tests ; `-m "requires_api"` même argv → 59 ; sur `tests/` entier
→ 90. L'écart (31) est hors-argv : élargir l'argv est une **décision user** (#1867).

---

## Objectif : « comparer les modes d'orchestration entre eux »

| Instrument | Nature | Dernière mesure firsthand |
|---|---|---|
| `scripts/compare_orchestration_modes.py` (#1735) | 7 modes sur un même corpus, sortie markdown + JSON | ⚠ **non re-mesuré dans cette session** |

Budget : au défaut de 180 s tous les modes meurent en plein DAG ; `pipeline_standard`
demande ≈ 500 s pour atteindre 15/15 phases sur un corpus court.

---

## Objectif : « comparer des modèles ou des workflows entre eux » (benchmarks)

**Six surfaces sous `argumentation_analysis/evaluation/`**, cartographiées le **18/09/2026**
(dispatch #2299) par trois gestes firsthand : census des importateurs (grep sur tout le dépôt,
hors `tests/`), datation `git log --all` par surface, et preuves d'exécution (en-têtes de
rapports commités dans `docs/reports/`, mtimes des artefacts locaux gitignorés dans
`evaluation/results/`).

| Instrument | Ce qu'il répond | Appelant hors `tests/` | Dernière exécution attestée |
|---|---|---|---|
| `benchmark_runner.py` — atomes `BenchmarkRunner`, `ResultCollector`, `ModelRegistry` | la **cellule** corpus × modèle × workflow ; bibliothèque de collection (`BenchmarkResult`) | 5 modules `evaluation/` (`multi_model_benchmark`, `run_agentic_eval`, `run_baseline_benchmark`, `run_iteration`, `result_collector`) + le wrapper `scripts/run_benchmark_multimodel.py` | via le wrapper : `docs/reports/benchmark_evaluation_report.md` (**08/03/2026**) ⚠ non re-mesuré · dernier toucher substantiel 19/03 (643e2dc2) |
| `fallacy_benchmark.py` | qualité de **détection de sophismes** (modes dont C contraint) | `scripts/run_fallacy_benchmark.py`, qui écrit `docs/reports/fallacy_benchmark_results.json` | artefact commité **11/03/2026** ⚠ non re-mesuré · le module reste compilation-courant via les sweeps taxonomie (#1930, #2036/#2043 — 06/09), qui ne sont **pas** des runs |
| `multi_model_benchmark.py` | orchestration multi-modèles + vLLM (créé 19/03) | **aucun** — le wrapper `scripts/run_benchmark_multimodel.py` compose les atomes directement, sans importer le module | aucune trouvée · dernier toucher 19/08 (#1794, sweep env-loaders) |
| `plugin_benchmark.py` | benchmark **au niveau plugin** (navigateur d'exploration CSV) | aucun (CLI) | aucune trouvée · dernier toucher 06/09 (#2041/#2044) = réparation de famille de crash par audit, pas un run |
| `conversational_benchmark.py` | **conversationnel vs séquentiel** (#308) | **aucun** — vérifié 18/09 : `ConversationalBenchmarkRunner` n'est instancié que sous `tests/` ; les seules autres mentions du module sont de la documentation (`evaluation/README.md`, 4 rapports d'audit) | aucune trouvée · dernier toucher 12/09 (#2170, sweep IDs opaques) |
| `run_baseline_benchmark.py` | cadre de baseline par capacité | aucun (CLI) | aucune trouvée · dernier toucher = son origine `feat(` du **13/03**, puis black ; cité seulement dans un audit de tests |

**Doublons réels et qui fait foi.** Deux axes portent des implémentations qui ne se
connaissent pas — trois pour le premier, deux pour le second (compte corrigé le 18/09, voir
le piège mesuré plus bas) :

- **Axe « comparer des modèles »** : le module `multi_model_benchmark` (sans appelant), le
  wrapper `scripts/run_benchmark_multimodel.py` et les atomes
  `benchmark_runner`. **Fait foi : le wrapper** `scripts/run_benchmark_multimodel.py` —
  seule surface de l'axe avec une exécution attestée (le rapport commité de mars). Le module
  est une couche d'orchestration que plus rien n'appelle.
- **Axe « comparer le conversationnel »** : `conversational_benchmark.py` (module sans
  appelant) et `scripts/compare_orchestration_modes.py` (#1735). **Fait foi :
  `compare_orchestration_modes.py`** — seul instrument de l'axe calibré et mesuré récemment
  (campagne #1735, rungs 180–1200 s, septembre 2026) ; le module n'a pas d'exécution
  attestée.

⚠ **Piège mesuré sur cette carte même, le 18/09** : une première rédaction de cette section
datait cet axe d'un troisième larron — « `scripts/run_baselines.py:164` réimplémente une
`run_conversational_benchmark()` homonyme ». **Faux, et faux de trois façons**, vérifié au
contrôle (positif et négatif) avant correction :

1. **Le chemin.** `scripts/run_baselines.py` n'existe pas et n'a jamais existé
   (`git log --all --diff-filter=D` rend vide). Le fichier réel est
   `.analysis_kb/run_baselines.py`.
2. **Le statut.** `.analysis_kb/` est **gitignoré** (`.gitignore:201`). C'est un brouillon
   local de la machine qui a mesuré, pas une surface du dépôt — aucun lecteur de cette carte
   ne peut l'ouvrir. Une entrée de cartographie qui cite un artefact injoignable décrit la
   machine de l'auteur, pas le dépôt.
3. **Le littéral.** `run_conversational_benchmark` n'apparaît **nulle part**, ni dans les
   fichiers suivis (`git grep` vide) ni sur le disque (`grep -r` vide) — y compris dans le
   fichier accusé, qui définit `run_single_baseline` / `run_all_baselines` et dont la ligne
   164 appelle `run_unified_analysis`. Le module `conversational_benchmark.py`, lui, n'expose
   pas de fonction de ce nom : il expose la classe `ConversationalBenchmarkRunner`.

La leçon utile n'est pas celle qui était écrite. Ce n'est pas « un grep sur le nom ne dit pas
lequel a tourné » — c'est qu'**un doublon affirmé se vérifie en ouvrant les deux côtés**. Ici
un seul côté existait. Et le geste qui l'a révélé est le contrôle positif : le même grep, sur
un littéral connu présent, rend un résultat ; sur celui-ci, rien. Un zéro rendu par un
instrument qu'on n'a pas prouvé ne vaut rien — dans les deux sens.

⚠ **Une boussole n'est pas un fait** (leçon JVM, cf. objectif « modules spécialisés ») :
`test_fallacy_benchmark::test_mode_c_constrained` existe dans la bande replay #1603 — mais
son exécution en test ne prouve rien d'un run de benchmark. Symétriquement, « aucun appelant
production » n'est **pas** une preuve de non-utilité (Cleanup Gate) : les cinq surfaces sans
appelant restent en place, datées ci-dessus ; aucune ne porte de `feat(` récent comme
dernier toucher — la plus suspecte est `run_baseline_benchmark.py`, dont le dernier toucher
est son propre `feat(` d'origine (13/03).

---

## Objectif : « noter la qualité d'un run par un juge LLM »

Cartographié le **18/09/2026** (dispatch #2299), mêmes gestes que la section benchmarks.

| Instrument | Ce qu'il répond | Appelant hors `tests/` | Dernière exécution attestée |
|---|---|---|---|
| `judge.py` — `LLMJudge`, `JudgeScore` | **socle** de scoring LLM partagé | 5 importeurs (`capability_eval`, `run_agentic_eval`, `run_baseline_benchmark`, `run_llm_judge`, `__init__`) + le wrapper multimodel (pour `JudgeScore`) — mais `capability_eval` n'est importé nulle part hors `evaluation/` : la chaîne se termine en CLIs | via le wrapper multimodel (**08/03/2026**) ⚠ non re-mesuré · sweeps récents le tenant compilation-courant : #1786 (17/08, fenêtre calculée), #1934 (28/08) |
| `run_llm_judge.py` | CLI de scoring qualité (#Mission11) | aucun | aucune trouvée · dernier toucher 20/03 (cc726a98, fix critique) |
| `run_agentic_eval.py` | conversation **agentique mono-passe vs multi-tours** (#97) | aucun | aucune trouvée · dernier toucher = origine 21/03, puis lint seul |

**Fait foi : `judge.py`** comme bibliothèque — c'est le socle que tous les CLIs de l'axe
importent. Mais la seule exécution attestée de tout l'axe date de mars (le rapport du
wrapper). **Un quatrième juge, hors du triptyque et découvert par le census, fait mieux** :
`scripts/run_full_judgment.py` — qui **n'importe pas** `LLMJudge` (il s'appuie sur
`run_provenance` + `unified_pipeline`) et a produit les artefacts locaux
`evaluation/results/full_judgment/` du **05/09/2026**. Les juges réellement exécutés en
septembre ne passent donc pas par `judge.py`.

**Trou mesuré** : l'axe « juge » a quatre surfaces vivantes au sens large mais **aucune
exécution attestée de `judge.py` lui-même depuis mars 2026** — toute conclusion citant un
score « du juge LLM » comme état courant doit nommer lequel des quatre a tourné.

---

## Objectif : « le dataset fuit-il ? »

| Instrument | Nature | Dernière mesure firsthand |
|---|---|---|
| `scripts/security/scan_indexed_surfaces.py` | scan des surfaces indexées GitHub | tourne en gate sur la lane #2286 |
| `evaluation/leak_patterns.py` | détection **par classe**, jamais par énumération d'identifiants | — |
| `evaluation/sanitize_state.py` | scrub de l'état avant signature | connaît `analysis_trace` (clé `summary`) |
| `scripts/security/verify_encrypted_dataset_completeness.py` | prouve que le chiffré est un sur-ensemble avant toute suppression | — |

---

## Zones non cartographiées

Nommées pour que leur absence soit lisible, pas silencieuse :

- évaluation de la qualité argumentative (plusieurs surfaces : `quality_evaluator`,
  `agentic_virtue_detectors`, `QualityScoringPlugin`, #1907) — **combien d'instruments
  réellement, non établi** ;
- détection de sophismes (taxonomie 8 familles, plugin FR 3 étages, détection neuronale
  #2130 muette en runs réels).

Les benchmarks et juges LLM (ex-zone non cartographiée) sont couverts ci-dessus depuis le
18/09 (#2299). Ces deux zones restantes sont l'ordre de travail suggéré.
