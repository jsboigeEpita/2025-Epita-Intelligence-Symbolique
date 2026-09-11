# `argumentation_analysis/reporting/` — paquet parent de restitution et d'export multi-format

Le paquet agrège **deux populations disjointes** : une chaîne d'assemblage de rapports
`models → data_collector → document_assembler` **scaffold, sans consommateur production**
(données factices), et des **producteurs d'artefacts vivants** (`multi_format_exporter`,
les deux analyseurs de trace, `conversation_balance`, `cross_reference_graph`,
`reprompt_trace`, `summary_generator`) dont la sortie est écrite dans
`docs/reports/spectacular/` — **répertoire suivi par git**, donc surface indexée GitHub.
Le point de fuite potentiel n'est pas dans le paquet : la décontamination vit
entièrement chez l'appelant, `multi_format_exporter` étant un exportateur **brut**.

Mesuré : **16 fichiers `.py` au premier niveau = 6 774 lignes** ; le sous-arbre entier
(avec `restitution/`) porte **36 `.py`**.

---

## Rôle et frontière

Le paquet ne fabrique pas d'analyse : il **transforme un état d'analyse déjà produit en
artefacts lisibles** (JSON/XML/Markdown/CSV/HTML/terminal) et **extrait des rapports de
trace** d'une exécution. Frontière amont unique pour la branche export :
`state.get_state_snapshot(summarize=...)`, attendu par duck-typing
(`multi_format_exporter.py:71-80`) — le type n'est jamais importé.

Frontière aval : le paquet **produit des chaînes ou des fichiers**, jamais de décision.
La seule écriture disque de la chaîne export est faite par l'appelant
(`scripts/analysis/generate_spectacular_bundle.py:381-547`,
`scripts/analysis/export_scda_state.py:29-49`) ; `MultiFormatExporter.to_csv_bundle`
reçoit un répertoire en paramètre (`multi_format_exporter.py:203`) et ne choisit rien.

**Sous-paquet enfant** : `restitution/` (20 fichiers `.py`, ~9 100 lignes) — le rapport
3 actes lisible, qui **remplace** le dump dimensionnel comme sortie par défaut
(`restitution/__init__.py:1-9`, `restitution/renderer.py:4-6`). Il porte sa propre
surface publique (`restitution/__init__.py:32-49`, 15 noms exportés) et son propre
README — le paquet parent n'a **ni l'un ni l'autre**.

Écart de compte à noter : l'énoncé annonce « 16 fichiers `.py`, 15911 lignes ». Mesuré :
16 `.py` **au premier niveau** = **6 774 lignes** ; 15911 = le **sous-arbre entier**
(36 `.py` avec `restitution/`). Les deux moitiés de la phrase ne mesurent pas le même objet.

## Composants publics

`reporting/__init__.py` fait **0 octet** (vérifié : `wc -c` = 0). Le paquet parent
**n'expose rien** : aucun `__all__`, aucun ré-export, aucun import de commodité. Chaque
consommateur paie le chemin complet (`from argumentation_analysis.reporting.X import Y`).
C'est l'inverse exact du sous-paquet `restitution/`, dont l'`__init__.py` (1 364 octets)
déclare un `__all__` de 15 noms. **Il n'existe aucun README.md à la racine du paquet**
(`ls argumentation_analysis/reporting/*.md` → aucun fichier) : l'assemblage n'est
documenté nulle part au niveau parent.

Les 16 modules et leur statut mesuré (sites d'appel production externes / internes au
paquet / fichiers de test) :

| Module | Lignes | Statut mesuré | Ancrage |
|---|---|---|---|
| `__init__.py` | 0 | **vide** — aucune surface | 0 octet |
| `models.py` | 38 | **vivant, consommé interne** (3 sites) | `data_collector.py:16`, `orchestrator.py:4`, `section_formatter.py:38` |
| `document_assembler.py` | 951 | **scaffold** — 0 prod externe, 2 internes | `data_collector.py:17`, `orchestrator.py:38` |
| `section_formatter.py` | 1146 | **résiduel / doublon** — 0 prod, 0 interne | `section_formatter.py:45` |
| `data_collector.py` | 353 | **scaffold** — 1 interne, données factices | `orchestrator.py:26`, `data_collector.py:314-351` |
| `orchestrator.py` | 73 | **résiduel** — 0 prod, 1 test de garde | `tests/.../test_import_guard_2076.py:30` |
| `reporting.py` | 25 | **résiduel** — 0 consommateur, 0 test | `reporting.py:5` |
| `graph_generator.py` | 37 | **coquille vide** — 100 % commentaires | `graph_generator.py:1-37` |
| `trace_analyzer.py` | 1191 | **résiduel** — 0 prod, 3 tests ; **collision de nom** | `trace_analyzer.py:273` |
| `enhanced_real_time_trace_analyzer.py` | 738 | **vivant** — 2 sites prod | `analysis_runner_v2.py:81`, `enhanced_pm_analysis_runner.py:70` |
| `real_time_trace_analyzer.py` | 465 | **vivant** — 2 sites prod | `orchestrate_with_existing_tools.py:19`, `educational_showcase_system.py:94` |
| `multi_format_exporter.py` | 394 | **vivant** — 2 sites prod | `export_scda_state.py:47`, `generate_spectacular_bundle.py:371` |
| `conversation_balance.py` | 182 | **vivant** — 1 site prod (bundle) | `generate_spectacular_bundle.py:407` |
| `cross_reference_graph.py` | 448 | **vivant** — 1 site prod (bundle) | `generate_spectacular_bundle.py:419` |
| `reprompt_trace.py` | 219 | **vivant** — 2 sites prod | `generate_spectacular_bundle.py:454`, `conversational_orchestrator.py:962` |
| `summary_generator.py` | 514 | **vivant** — 1 site prod (script) | `generate_rhetorical_analysis_summaries.py:39-40,215` |

Développement des porteurs de sens :

- **`models.py` — la seule convention partagée du paquet.** `ReportMetadata` (`models.py:15`)
  et `ReportConfiguration` (`models.py:28`) sont le vocabulaire commun ; trois modules
  les importent. Mais `ReportMetadata` est **aussi redéfini localement** dans
  `document_assembler.py:22` avec **des champs identiques** (source_component,
  analysis_type, generated_at, version, generator, format_type, template_name) —
  duplication de définition, pas seulement de nom.
- **`multi_format_exporter.py` — le cœur de la chaîne d'export.** `MultiFormatExporter`
  (`:62`) couvre les 6 formats : `to_json:90`, `to_xml:98`, `to_markdown:154`,
  `to_csv_bundle:203`, `to_html:239`, `to_rich_terminal:319`. Il lit l'état par
  `get_state_snapshot(summarize=False)` pour le détail et `summarize=True` pour la
  synthèse (`:71-80`), avec cache (`:82-84`). `_DIMENSION_LABELS` (`:21-46`) fixe les
  24 libellés de dimensions — c'est la table de correspondance que tout le rendu partage.
- **Les deux analyseurs de trace sont frères, pas doublons.** `real_time_trace_analyzer.py`
  (`RealTimeTraceAnalyzer:165`, singleton `global_trace_analyzer:407`) et
  `enhanced_real_time_trace_analyzer.py` (`EnhancedRealTimeTraceAnalyzer:285`, singleton
  `enhanced_global_trace_analyzer:657`) exposent **chacun un singleton de module** et une
  famille de fonctions libres parallèles (`tool_call_tracer:410` / `enhanced_tool_call_tracer:660`).
  Vocabulaire distinct (`RealToolCall:25` vs `EnhancedToolCall:108`), pas d'héritage commun.

## Points d'entrée valides

Trois entrées réelles, toutes **hors du paquet** (le paquet ne porte aucun `__main__`) :

1. `scripts/analysis/generate_spectacular_bundle.py` — le producteur du bundle capstone.
   Lit `outputs/scda_audit/` (`:47-52`), écrit dans `docs/reports/spectacular` (`:54`).
   Il appelle `MultiFormatExporter` (`:371`), `ConversationBalanceAnalyzer` (`:407`),
   `CrossReferenceGraph` (`:419`), `RepromptTraceExtractor` (`:454`).
2. `scripts/analysis/export_scda_state.py` — export d'un état unique vers un format.
   `--format` ∈ {json,xml,md,csv,html,rich,all} (`:36-38`), `--out` **défaut `"."`** (`:40`).
3. `scripts/reporting/generate_rhetorical_analysis_summaries.py` — appelle
   `run_summary_generation_pipeline` (`:215`), la seule fonction de pipeline de
   `summary_generator.py:434`.

Aucun de ces trois scripts n'est référencé par un workflow CI (`.github/workflows/` : 0
occurrence) — les entrées sont **manuelles**.

## Amont / aval

**Amont.** `argumentation_analysis/core/shared_state.py` — `UnifiedAnalysisState`
porte **deux** `get_state_snapshot` (`shared_state.py:405` et `:1660`) ; c'est le
contrat que `multi_format_exporter` consomme par duck-typing. Le bundle amont réel
est `outputs/scda_audit/` (JSON), **gitignoré** (`.gitignore:171` `outputs/`).

**Aval.** Deux familles :
- *Scripts* (ci-dessus) → artefacts sur disque.
- *Orchestration* : `analysis_runner_v2.py:81` et `enhanced_pm_analysis_runner.py:70`
  pour l'analyseur de trace enrichi (ce dernier l'appelle réellement :
  `:283-284`, `:622`) ; `conversational_orchestrator.py:962` pour `RepromptTraceExtractor` ;
  `project_core/rhetorical_analysis_from_scripts/educational_showcase_system.py:94` pour
  l'analyseur de trace simple.

**Aval du paquet parent = `restitution/`**, qui n'est pas dans cette fiche : branché sur
`unified_pipeline.py:418` et `invoke_callables.py:9130/9250/9354`. Le paquet parent et
son enfant sont **deux chaînes indépendantes** : rien dans les 16 modules top-level
n'importe `restitution.*` (0 occurrence).

## Statut d'intégration

Trois régimes coexistent dans le même dossier.

**(a) Vivant et consommé (7 modules).** `multi_format_exporter`, les deux analyseurs de
trace, `conversation_balance`, `cross_reference_graph`, `reprompt_trace`, `summary_generator`.
Chacun a ≥ 1 appelant production nommé ci-dessus. Pour les cinq du bundle, l'unique
appelant est `generate_spectacular_bundle.py` : **facteur de bus 1**, mais appelant réel.

**(b) Scaffold interne (3 modules).** `models`, `data_collector`, `document_assembler`,
plus `orchestrator` qui les pilote. La chaîne est complète et testée, mais son **producteur
de données est factice** : `DataCollector.gather_all_data` retourne une structure codée en
dur (`data_collector.py:314-351` — titre « Rapport d'Analyse Automatique », un sophisme
d'exemple, `text_fragment: "..."`). `orchestrator.py` l'appelle (`:52`) puis
assemble (`:70`). Aucun appelant production : le seul import externe est une **garde
d'import** de test (`test_import_guard_2076.py:26,30`), qui vérifie que le module
s'importe, pas qu'il sert. `document_assembler` et `data_collector` sont donc « vivants par
import, morts par usage ».

**(c) Résiduel (5 modules).** `section_formatter`, `reporting`, `graph_generator`,
`trace_analyzer`, et `orchestrator` (0 prod). Détail en « Limites connues ».

## Artefacts et lecteurs

**Ce que le paquet écrit, et où — c'est la frontière de confidentialité.**

- Le **seul** chemin d'écriture vers une surface indexée GitHub est
  `scripts/analysis/generate_spectacular_bundle.py`. `OUT_DIR = ROOT / "docs/reports/spectacular"`
  (`:54`). Mesuré : **60 fichiers sont suivis par git** dans ce répertoire
  (`git ls-files docs/reports/spectacular`), `git check-ignore` ne les matche pas.
  Ce sont `corpus_{A..D}.{json,xml,md,html}`, `A/B/C/csv/*.csv`, `balance_corpus_*.md`,
  `cross_ref_graph_corpus_*.{json,dot,mmd}`, `reprompt_trace_corpus_*.{json,md}`,
  `conversation_replay_corpus_*.md`, `README.md`.
- L'amont, `outputs/scda_audit/`, est **gitignoré** (`.gitignore:171`).

**Où vit la décontamination.** Elle est **entièrement chez l'appelant**, jamais dans le
paquet : `generate_spectacular_bundle.py:30` `_PRIVACY_STRIP_FIELDS`, `:36` `_NL_SCRUB_KEYS`,
`:45` `_EXCHANGE_SCRUB_KEYS`, `:74` `_strip_privacy`, `:122` `_scrub_state_for_export`,
`:319` `_global_entity_scrub`. Séquence vérifiée : `:373` `_scrub_state_for_export(state_data)`
→ `:374` `_DictStateProxy(safe_data)` → `:375` `MultiFormatExporter(proxy)` : l'exportateur
ne voit **que** des données déjà nettoyées.

**Contre-vérification.** `grep` de `raw_text|full_text|scrub|privacy` dans
`multi_format_exporter.py` → **0 occurrence**. L'exportateur est brut par conception ;
c'est le découplage qui tient la frontière, pas une garde défensive. Preuve que le
nettoyage tient dans l'artefact commité : `docs/reports/spectacular/A/csv/args.csv`
ligne 2 = `arg_1,<scrubbed>` — identifiants opaques, valeur neutralisée.

**Lecteurs de restitution.** Le paquet parent ne lit aucun de ses propres artefacts : il
n'y a **aucune fonction de relecture** dans les 16 modules (les seules lectures sont
`yaml` de config dans `data_collector.py:83,140`). Les lecteurs vivent dans
`restitution/` (`renderer.py`, `appendix.py`, `readability_gate.py`) et dans
`scripts/analysis/export_scda_state.py:14` (`_load_state`).

## Tests représentatifs

Deux ensembles, très déséquilibrés :

- **Premier niveau : 12 fichiers** dans `tests/unit/argumentation_analysis/reporting/`
  (`test_multi_format_exporter.py`, `test_conversation_balance.py`,
  `test_cross_reference_graph.py`, `test_document_assembler.py`,
  `test_section_formatter.py`, `test_trace_analyzer.py`,
  `test_enhanced_real_time_trace_analyzer.py`, `test_enhanced_trace_analyzer.py`,
  `test_real_time_trace_analyzer.py`, `test_reprompt_trace.py`,
  `test_summary_generator.py`, plus un README et un `__init__.py`).
- **Sous-paquet : 33 fichiers** dans `.../reporting/restitution/`.

Quatre modules sont **testés sans être consommés** : `section_formatter`
(`test_section_formatter.py:8`), `trace_analyzer` (3 fichiers), `document_assembler`
(`test_document_assembler.py:10`), `orchestrator`. Le test devient alors la seule
preuve de vie — un module dont la seule intégration est son test est un module
dont la suppression ne casserait que son test (cf. la garde d'import
`test_import_guard_2076.py:26,30` qui affirme exactement cela).

`test_section_formatter.py` et `test_document_assembler.py` testent **la même classe
sous le même nom** (`UnifiedReportTemplate`) dans deux modules différents — les deux
suites passent, ce qui garantit que la duplication est fonctionnelle, pas accidentelle.

## Frères et parent

**Parent** : `argumentation_analysis/`. Le paquet est un frère de
`orchestration/`, `core/`, `agents/`, `plugins/`, `services/`, `analytics/`,
`visualization/`, `utils/dev_tools/`, `pipelines/`, `cli/`.

**Frère à surveiller — collision de nom de module.** `argumentation_analysis/orchestration/trace_analyzer.py`
existe (10 502 octets, classe `ConversationalTraceAnalyzer:87`) et est **le seul des deux
à être consommé en production** : `conversational_orchestrator.py:51` importe de
`orchestration.trace_analyzer`, pas de `reporting.trace_analyzer`. Deux modules homonymes,
deux contenus sans rapport (`TurnTrace`/`PhaseTrace`/`ConvergenceMetrics` d'un côté,
`ExtractMetadata`/`StateEvolution`/`AgentSession` de l'autre), un seul vivant. Un
`grep trace_analyzer` mesure indifféremment les deux.

**Frère de contrat** : `orchestration/invoke_callables.py` (9 000+ lignes) est le gros
voisin qui consomme `restitution/` et non le paquet parent.

**Enfant** : `restitution/` — décrit en « Rôle et frontière ». Deux chaînes parallèles,
zéro import croisé parent→enfant.

## Limites connues

Relevé d'anomalies, **aucune corrigée** (lecture seule).

1. **Duplication lourde `section_formatter.py` / `document_assembler.py`.** Même nom de
   classe (`:45` / `:38`), **mêmes 13 méthodes** (`__init__`, `render`, `_render_markdown`,
   `_render_console`, `_render_json`, `_render_html`, `_extract_sk_retry_attempts`,
   `_extract_error_context`, `_extract_tweety_errors`, `_generate_logic_failure_diagnostic`,
   `_generate_contextual_recommendations`, `_count_modal_failures`,
   `_is_generic_recommendation`), **créés par le même commit** `3aefda0e
   feat(reporting): Refactor report_generation.py into new package`, et modifiés par
   les mêmes deux commits de formatage ultérieurs. Diff sur le code hors commentaires :
   **367 lignes divergentes** sur ~870/901. `document_assembler` est le survivant branché
   (2 sites internes) ; `section_formatter` n'a **que** son test. → **#2143**.
2. **`ReportMetadata` défini deux fois avec les mêmes champs** — `models.py:15` (le
   canonique, importé 3 fois) et `document_assembler.py:22` (copie locale). Le commentaire
   d'intention de `data_collector.py:15` (« UnifiedReportTemplate est défini dans
   document_assembler.py (pas dans models) ») montre que la confusion a déjà coûté.
3. **Docstring contredisant le code.** `data_collector.py:120` : « Nécessite
   UnifiedReportTemplate de `.models` » ; or la ligne 17 importe de `.document_assembler`.
   La ligne 15 commente la correction, la ligne 120 ne l'a pas reçue.
4. **`graph_generator.py` est une coquille** : 37 lignes, 100 % docstring et commentaires
   (`:1-37`), zéro `def`, zéro `class`. Il s'annonce comme un module d'accueil pour de
   futures implémentations.
5. **Deux modules morts confirmés par une source tierce.** `restitution/pipeline_adapter.py:9`
   qualifie le dump `render_markdown` (`UnifiedReportTemplate`) de « dead code on the
   spectacular path » ; `restitution/renderer.py:4-6` dit le remplacer. Le paquet
   parent héberge donc une classe que son propre successeur déclare morte.
6. **`orchestrator → data_collector → document_assembler` : chaîne complète à données
   factices.** `data_collector.py:314-351` retourne une structure d'exemple codée en dur
   (dont un sophisme d'illustration). Le `reporting/__init__.py` vide et l'absence de
   README parent signent le même état : l'assemblage n'est jamais devenu un chemin réel.
7. **Surface déclarée sans consommateur (mineure).** `analysis_runner_v2.py:81` importe 7
   noms de `enhanced_real_time_trace_analyzer` ; **2 ne sont jamais utilisés** dans le
   fichier (`enhanced_global_trace_analyzer`, `get_enhanced_pm_report` — 1 occurrence
   chacun = la ligne d'import). Les 5 autres sont réellement appelés.
8. **`export_scda_state.py` a un défaut d'écriture non sûr.** `--out` par défaut à `"."`
   (`:40`), puis écritures directes `out_dir / "state.json"` etc. (`:29-49`). Lancé depuis
   la racine du dépôt sans `--out`, il dépose `state.json|xml|md|html|state_terminal.txt`
   et un bundle CSV **dans le répertoire de travail suivi par git**. Rien dans le script
   ne neutralise le contenu, et `MultiFormatExporter` — on l'a mesuré — ne décontamine
   rien lui-même : c'est la seule entrée du paquet où la frontière de confidentialité
   repose entièrement sur la discipline de l'opérateur. → **#2143**.
9. **`restitution/state_adapter.py.bak`** (5 516 octets, non suivi par git) traîne dans
   l'arbre de travail. **Correction d'une affirmation initiale** : il n'est **pas**
   capturable par un `git add -A` — `git check-ignore -v` le résout sur
   `.gitignore:103:*.bak`. Il reste visible dans un `ls`, mais l'index l'exclut : le
   risque est celui d'un fichier de travail oublié, pas celui d'une fuite par staging.
10. **Aucun appelant CI.** Les trois points d'entrée sont manuels : le bundle commité
    dans `docs/reports/spectacular/` (60 fichiers suivis) peut donc dériver du code qui
    le produit sans qu'aucun contrôle automatique ne le signale.

---

*Provenance de mesure : branche `docs/readme/2088-parents`, 2026-09-11. Les 16 modules `.py` de*
*premier niveau de `argumentation_analysis/reporting/` sont identiques à ceux d'`origin/main`*
*(`git diff --name-only origin/main...HEAD -- argumentation_analysis/reporting/` → vide).*
*Vérifié sur cette branche : `__init__.py` 0 octet · 16 `.py` / 6 774 lignes au premier niveau ·*
*36 `.py` dans le sous-arbre · 60 fichiers suivis dans `docs/reports/spectacular` · `
.gitignore:103` couvre `*.bak`. Fiche produite en **lecture seule** — aucun fichier du dépôt*
*modifié hors ce README.*
