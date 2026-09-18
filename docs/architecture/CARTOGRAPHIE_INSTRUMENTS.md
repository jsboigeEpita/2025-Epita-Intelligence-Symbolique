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
  #2130 muette en runs réels) ;
- benchmarks : `benchmark_runner`, `fallacy_benchmark`, `multi_model_benchmark`,
  `plugin_benchmark`, `conversational_benchmark`, `run_baseline_benchmark` — **six
  surfaces au moins, relations non établies** ;
- juges LLM : `judge.py`, `run_llm_judge.py`, `run_agentic_eval.py` — idem.

Ces quatre zones sont l'ordre de travail suggéré : la dernière (benchmarks + juges) est
celle où la juxtaposition est la plus probable, à en juger par le nombre de points d'entrée.
