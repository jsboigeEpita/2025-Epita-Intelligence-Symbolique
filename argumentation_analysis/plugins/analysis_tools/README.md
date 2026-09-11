# `argumentation_analysis/plugins/analysis_tools/` — façade d'orchestration rhétorique **non-Semantic-Kernel**, ses six moteurs « Enhanced » et une surface déclarative inerte

Façade Python ordinaire (`plugin.py`) plus six moteurs métier : **13 `.py`, 5 498 lignes** en récursif, dont **zéro `@kernel_function`** (AST sur les 13 fichiers, pas `grep`). Le nom dit « plugin » et `manifest.json` déclare trois capacités, mais le paquet n'est montable sur aucun kernel : il est appelé comme un objet Python. La façade est atteinte par **deux chaînes** seulement ; `manifest.json` est rejeté par le seul lecteur de son format, et **20 des 33 tests in-package échouent au *setup***.

> Le titre historiquement associé à ce paquet (« façade SK ») est faux par construction : `@kernel_function` = **0/13 fichiers**. Deux des trois méthodes publiques de la façade ont un corps vide (`pass`), et **trois moteurs refusent la construction sans argument** — vérifié à l'exécution, pas seulement au graphe d'appels.

---

## Rôle et frontière

**Ce que l'assemblage apporte que les feuilles n'apportent pas seules :**

1. **Un graphe de dépendances explicite entre six moteurs qui s'ignorent.** `plugin.py:42-53` instancie dans un ordre contraint : `EnhancedContextualFallacyAnalyzer` et `EnhancedComplexFallacyAnalyzer` reçoivent **le même `AbstractFallacyDetector` injecté** (`:42-44`, `:46-48`) ; `EnhancedRhetoricalResultAnalyzer` reçoit `complex_fallacy_analyzer` **et** `severity_evaluator` (`:49-52`). Aucun des six moteurs ne connaît ce montage.
2. **L'unique orchestration `analyze_text`** (`plugin.py:57-100`) : analyse contextuelle → sophismes composites → cohérence inter-arguments, assemblés en `raw_results` (`:88-92`) au format attendu par `EnhancedRhetoricalResultAnalyzer.analyze_rhetorical_results` (`:95-97`).
3. **Le point d'injection du détecteur** (`AnalysisToolsPlugin(fallacy_detector=…)`, `plugin.py:32`) — seul endroit où ce contrat externe est distribué.
4. **Une convention d'import courte** par `logic/__init__.py:11-15` (6 noms, `__all__` `:17-24`, tous définis, zéro fantôme).

**Hors frontière :** le paquet ne contient aucun `@kernel_function`, aucune entrée CLI, aucune route HTTP, aucune entrée de registre de capacités. Il ne contient ni le détecteur (`argumentation_analysis.core.interfaces.fallacy_detector.AbstractFallacyDetector`, importé `plugin.py:11-13`) ni la taxonomie.

**Portées de comptage, mesurées séparément** (un total récursif ne se compare pas à un total direct) :

| Portée | Contenu | Lignes |
|---|---|---|
| Direct | `__init__.py` (**0 octet**), `plugin.py` (127), `manifest.json` (1 203 o) | 127 |
| `logic/` | `__init__.py` (24) + 6 moteurs (4 571) | **4 595** |
| `tests/` | `__init__.py` (0 o) + 3 fichiers | 776 |
| **Récursif** | 13 `.py` | **5 498** |

---

## Composants publics

| Nom | Fichier | Statut mesuré |
|---|---|---|
| `AnalysisToolsPlugin` | `plugin.py:27` | 3 méthodes : `analyze_text:57` **implémentée**, `evaluate_argument_list:102` (**`pass` :114**), `generate_visual_report:116` (**`pass` :127**) |
| `EnhancedComplexFallacyAnalyzer` | `logic/complex_fallacy_analyzer.py:57` | réel, 1 608 l. ; `__init__(fallacy_detector)` **requis** (`:74`) |
| `EnhancedContextualFallacyAnalyzer` | `logic/contextual_fallacy_analyzer.py:82` | réel, 975 l. ; `fallacy_detector` **requis** (`:98-101`) |
| `EnhancedFallacySeverityEvaluator` | `logic/fallacy_severity_evaluator.py:36` | réel, 446 l. ; `__init__(self)` sans dépendance — **seul constructible sans argument** |
| `EnhancedRhetoricalResultAnalyzer` | `logic/rhetorical_result_analyzer.py:173` | réel, 817 l. ; paramètres optionnels, mais le **défaut est cassé** (`:201-203`) |
| `EnhancedRhetoricalResultVisualizer` | `logic/rhetorical_result_visualizer.py:43` | réel, 568 l. ; 5 méthodes publiques (`:60,165,233,319,408`), **aucune appelée par la façade** |
| `NLPModelManager` + singleton `nlp_model_manager` | `logic/nlp_model_manager.py:47`, `:157` | réel, **jamais atteint en production** (`get_model:134` rend toujours `None`, `:144-149`) |
| `RecommendationGenerator` | `logic/rhetorical_result_analyzer.py:36` | non exporté, usage interne |

| Surface | Mesure |
|---|---|
| `@kernel_function` | **0** (AST, 13 fichiers) |
| Exports de `analysis_tools/__init__.py` | **aucun** — fichier de **0 octet** |
| Exports de `logic/__init__.py` | 6 noms (`:11-15`, `__all__` `:17-24`) |

**Collisions de noms.** Aucune collision de `@kernel_function` n'est possible ici (il n'y en a aucun) ; les classes `Enhanced*` et `NLPModelManager` sont **uniques dans tout le dépôt** (grep `^class EnhancedComplexFallacyAnalyzer` & co : 1 occurrence chacune). Deux homonymies réelles subsistent néanmoins : (a) `AnalysisToolsPlugin.analyze_text:57` porte le même nom que ~15 autres `analyze_text` du dépôt (`services/web_api/services/analysis_service.py:258`, `pipelines/unified_pipeline.py:96`, …) — un `grep` sur ce nom ne désigne pas ce paquet ; (b) le nom « Enhanced » **n'est pas un doublon accidentel** : les versions de base vivent ailleurs, `ContextualFallacyAnalyzer:47`, `ComplexFallacyAnalyzer:91`, `FallacySeverityEvaluator:81`, `RhetoricalResultVisualizer:41` dans `argumentation_analysis/agents/tools/analysis/` — mêmes rôles, implémentations et arbres distincts.

---

## Points d'entrée valides

| Entrée | Emplacement | Nature |
|---|---|---|
| Façade (chemin nominal) | `argumentation_analysis.plugins.analysis_tools.plugin.AnalysisToolsPlugin` | construite par 3 sites de production (`pipelines/unified_text_analysis.py:249`, `rhetorical_tools_adapter.py:72`, `pipelines/advanced_rhetoric.py:60`) |
| Moteurs en direct | `…analysis_tools.logic.contextual_fallacy_analyzer` / `.fallacy_severity_evaluator` | `services/web_api/services/fallacy_service.py:16-20` — **contourne la façade** |
| Export paquet | `…analysis_tools.logic` (`__init__.py:11-24`) | 6 noms |
| Descripteur | `analysis_tools/manifest.json` | **aucun lecteur valide** |
| `__main__` de démonstration | `logic/complex_fallacy_analyzer.py:1580`, `contextual_fallacy_analyzer.py:951`, `fallacy_severity_evaluator.py:433`, `rhetorical_result_visualizer.py:533` | 4 blocs gardés — **2 sont cassés** (voir *Limites connues* §1) |

**Aucune entrée de registre de capacités, aucune entrée HTTP, aucune entrée CLI.** Mesuré sur les deux surfaces d'enregistrement : `orchestration/registry_setup.py` **ne contient aucune occurrence** de `analysis_tools` (la seule ligne proche, `:726`, est une description « rhetorical register » sans rapport) ; `agents/factory.py` `_PLUGIN_REGISTRY:73-104` ne le liste pas. Un composant peut donc être importable **et** invisible du registre — c'est ici le régime exact.

---

## Amont / aval

**Amont**

- `AbstractFallacyDetector` — **contrat d'injection obligatoire** (`plugin.py:32`) ; sans lui `EnhancedContextualFallacyAnalyzer` / `EnhancedComplexFallacyAnalyzer` ne se construisent pas.
- `logic/nlp_model_manager.py` — singleton (`:157`) dont `load_models_sync:82` **n'a aucun appelant nulle part** (le seul site qui l'exécutait est commenté, `plugin.py:39`).
- `matplotlib` (visualiseur, `:159,225,311`), `networkx`/`pathlib` selon les moteurs.

**Aval — état des chaînes, mesuré une par une :**

| Chaîne | Site | Statut mesuré |
|---|---|---|
| Pipeline unifié | `pipelines/unified_text_analysis.py:85,249` (`_initialize_analysis_tools:233`, appelée `:208`) | **vivant** — fonction d'entrée `run_unified_text_analysis_pipeline:1015`, appelée `pipelines/unified_pipeline.py:333` |
| Adaptateur hiérarchique | `orchestration/hierarchical/operational/adapters/rhetorical_tools_adapter.py:25,72` | **vivant** — enregistré comme agent `"rhetorical"` (`agent_registry.py:70`) |
| Service web | `services/web_api/services/fallacy_service.py:16-20` | **vivant, mais par import direct des moteurs** ; consommé `services/mcp_server/main.py:33,84,349` |
| Showcase pédagogique | `project_core/rhetorical_analysis_from_scripts/educational_showcase_system.py:66-67,356` | **cassé à l'exécution** — le call-site lève (`§1`) et l'erreur est avalée (`:413-415`) |
| Analyse avancée | `orchestration/advanced_analyzer.py:10,17` | **mort** — 1 seul appelant, `pipelines/advanced_rhetoric.py:111` |
| Pipeline rhétorique avancé | `pipelines/advanced_rhetoric.py:12,23` | **mort** — 0 appelant de production ; seul appelant `tests/unit/…/pipelines/test_advanced_rhetoric.py:21` |

La façade est donc vivante par **deux** chaînes, pas quatre ; `advanced_rhetoric` ↔ `advanced_analyzer` forment une **boucle fermée sur les tests**, sans entrée amont.

---

## Statut d'intégration

**Verdict : vivant, à population hétérogène** — trois régimes coexistent et ne se recouvrent pas.

| Élément | Statut | Ancrage |
|---|---|---|
| `analyze_text` | **vivant, consommé** | `plugin.py:57-100` ; `unified_text_analysis.py:249` ; `rhetorical_tools_adapter.py:72` |
| 6 moteurs `logic/` | **vivants** (les 6 sont importables ; 4 sont réellement exercés via la façade, 2 seulement par import direct) | `logic/__init__.py:11-15` |
| `evaluate_argument_list`, `generate_visual_report` | **déclarés, corps vide** | `plugin.py:110-114`, `:120-127` |
| `self.visualizer` | **champ mort** | `plugin.py:53` — instancié, jamais lu hors des deux `pass` |
| `manifest.json` | **inerte, rejeté par son lecteur** | `§ Limites 2` |
| `analysis_tools/__init__.py` | **vide** | 0 octet |
| `tests/` in-package | **cassé (20/33 en ERROR au setup)** | `§ Tests` |
| Chaînes `advanced_rhetoric` / `advanced_analyzer` | **mortes** | `§ Amont / aval` |

Le cas le plus net : **le descripteur dit trois capacités, le code en tient une.** Un consommateur qui se fierait à `manifest.json` obtiendrait `None` là où il attend un `Dict`, pour deux des trois entrées. **Relevé, non corrigé.**

---

## Artefacts et lecteurs

**Artefacts produits** — uniquement par `EnhancedRhetoricalResultVisualizer`, et **seulement si un appelant l'atteint**, ce que la façade ne fait jamais (`plugin.py:53`) :

| Artefact | Producteur | Destination par défaut |
|---|---|---|
| `argument_network_<ts>.png`, `fallacy_distribution_<ts>.png`, `argument_quality_<ts>.png` (`dpi=300`) | `:108/159`, `:198/225`, `:269/311` | `<racine du dépôt>/results/visualizations` (`:25` + `:108,198,269`) |
| `*.mmd` (mermaid), `report.html` | `visualize_rhetorical_results:319`, `generate_enhanced_html_report:408` | `output_dir` fourni par l'appelant |
| `enhanced_report_<ts>.html` | `:408-432` | `<racine du dépôt>/results/reports` (`:430`) |

Le HTML embarque `<script src='https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js'>` (`:444`) : l'artefact **dépend d'un CDN à l'ouverture**. `<racine>` est bien la racine du dépôt, pas le parent du paquet — `parent_dir = current_dir.parent.parent.parent.parent` (`:24-25`) remonte 4 niveaux depuis `logic/`.

**Lecteurs.** `docs/technical/complex_fallacy_analyzer.md` (documente le moteur principal, cite `logic/complex_fallacy_analyzer.py` comme source de vérité) ; `logic/README.md` et `tests/README.md` dans l'arbre. **Aucun lecteur du `manifest.json`.** Le paquet **ne lit** ni n'écrit aucun fichier de données du dépôt : ses seules écritures sont les images/HTML ci-dessus.

---

## Tests représentatifs

**Deux suites, un seul régime sain.**

```bash
# Suite canonique (collectée par défaut) — 185 collectés / 185 passés avec JVM désactivée
python -m pytest tests/unit/argumentation_analysis/plugins/analysis_tools/logic/ -o addopts= --disable-jvm-session
# Suite in-package — NON collectée par défaut, et cassée
python -m pytest argumentation_analysis/plugins/analysis_tools/tests/ -o addopts=
```

| Suite | Fichiers | `def test_` | Mesure d'exécution |
|---|---|---|---|
| `tests/unit/argumentation_analysis/plugins/analysis_tools/logic/` (**collectée**) | 4 (`rhetorical_result_analyzer` 76, `contextual_fallacy_analyzer` 55, `severity_evaluator` 37, `nlp_model_manager` 12) | **180** | **185 collectés → 185 passed** (52 s, avec `--disable-jvm-session`) ; **sans ce drapeau : 100 % *skipped*, run vide** (signature JVM `pytest_sessionstart`, garde #2021) |
| `argumentation_analysis/plugins/analysis_tools/tests/` (**non collectée**) | 3 | 31 lignes `def test_` (dont **2 fixtures** mal nommées `test_arguments:34` / `test_fallacies:45`) → **33 collectés** | **13 passed, 20 ERROR au *setup*** — `severity_evaluator` passe seul ; `complex` et `contextual` sont à **0/10** |

**Ces tests mesurent le contrat, pas le chemin réel.** La suite canonique appelle les moteurs directement avec des dépendances injectées (p.ex. `test_rhetorical_result_analyzer.py:181-184` fournit toujours les trois analyseurs, ce qui **contourne** le défaut cassé de `:201-203`), ou mocke `AnalysisToolsPlugin` (`test_advanced_analyzer.py:26`, `MagicMock(spec=…)` — toute évolution de la surface rougit ce fichier). **Aucun test ne construit la façade réelle ni n'exécute `analyze_text` de bout en bout** ; `pipelines/advanced_rhetoric.py` est mocké au niveau module (`test_advanced_rhetoric.py:56`). Deux gardes de non-régression visent le proxy web : `tests/unit/api/test_starlette_proxy.py:54-59` et `tests/unit/test_interface_web_starlette.py:142-145` asservissent le fait que `interface_web.app` **n'importe pas** `nlp_model_manager`.

---

## Frères et parent

- **Parent** : `argumentation_analysis/plugins/` — README présent sur cette branche (`docs/readme/2088-parents`, non suivi), qui recense 36 `.py` / 12 609 l. récursif et mentionne explicitement `analysis_tools/` comme l'un de ses deux sous-paquets à fiche propre. Ce paquet ne figure dans **aucune** des deux surfaces d'enregistrement du parent (`agents/factory.py:73-104`, `orchestration/registry_setup.py`) : **invisible du registre de capacités**.
- **Frères directs, mesurés** : `semantic_kernel/` (1 module `jtms_plugin.py`, **5 `@kernel_function`** vérifiés AST, monté sur route API dédiée — l'anti-modèle exact de `analysis_tools`) et trois répertoires de **prompts SK natifs sans aucun `.py`** : `ExplorationPlugin/Explore/`, `GuidingPlugin/GuidingPlugin/`, `SynthesisPlugin/Synthesize/` (chacun `config.json` + `skprompt.txt`).
- **Frères structurels** (mêmes rôles, autre arbre) : `argumentation_analysis/agents/tools/analysis/` — versions **non** « Enhanced ». Toute affirmation « le `ContextualFallacyAnalyzer` est consommé par X » doit qualifier l'arbre.
- **Faux frère** : `agents/core/plugin_loader.py` (`PluginLoader`) — c'est lui, et lui seul, qui cherche le format `manifest.json` ; son homonyme `plugin_framework/core/plugins/plugin_loader.py:33` cherche un autre nom de fichier (`plugin_manifest.json`).

---

## Limites connues

**Suivi** : les items **1, 5, 6** sont portés par **#2147** (constructions no-arg, chargement
NLP sans appelant, échec silencieux du showcase). L'item **8** a été requalifié sur **#2124** :
la suite n'est pas « non collectée », elle est **collectée et cassée** (13 passed / 20 errors).
Les items **2, 3, 4, 7, 9** restent locaux.

1. **Trois chemins de construction sans argument sont cassés** — mesuré à l'exécution, pas déduit : `EnhancedContextualFallacyAnalyzer()` → `TypeError: missing 1 required positional argument: 'fallacy_detector'`. Sites : `logic/contextual_fallacy_analyzer.py:952` (`__main__`), `logic/complex_fallacy_analyzer.py:1581` (`__main__`), et **`logic/rhetorical_result_analyzer.py:201-203`** où le repli `complex_fallacy_analyzer or EnhancedComplexFallacyAnalyzer()` reproduit l'erreur — `EnhancedRhetoricalResultAnalyzer()` sans argument lève également. Le seul moteur constructible sans dépendance est `EnhancedFallacySeverityEvaluator` (`:36`). **Relevé, non corrigé.**
2. **`manifest.json` est rejeté par le seul lecteur de son format.** `agents/core/plugin_loader.py:67` exige `name`, `entrypoint_module`, `entrypoint_class` ; le descripteur porte `entry_point` (un **fichier** : `"plugin.py"`) et **aucun** des deux derniers → `PluginManifestError` (`:70-72`). Ce lecteur n'a lui-même **aucun appelant de production** (seulement `tests/unit/argumentation_analysis/agents/core/test_plugin_loader.py`). Inerte par les deux bouts.
3. **Deux capacités déclarées sans corps** : `evaluate_argument_list` (`plugin.py:110-114`) et `generate_visual_report` (`:120-127`), toutes deux annoncées dans `manifest.json`.
4. **`self.visualizer` mort** (`plugin.py:53`) : le producteur de **tous** les artefacts du paquet n'est jamais appelé par la façade, qui ne sait donc produire aucune visualisation.
5. **Chargement NLP désactivé** (`plugin.py:39`, ligne commentée) et `load_models_sync` (`nlp_model_manager.py:82`) sans **aucun appelant** dans le dépôt : `nlp_model_manager.get_model:134` retourne structurellement `None` + *warning* (`:144-149`). Le singleton est importé (`plugin.py:21`) mais jamais utilisé.
6. **Un call-site de production lève et l'erreur est avalée.** `educational_showcase_system.py:356` construit `EnhancedContextualFallacyAnalyzer()` sans détecteur dans un `try` (`:345`) dont l'`except Exception` (`:413-415`) journalise et `return False` : l'agent rhétorique n'est **jamais** créé et l'échec est silencieux pour l'appelant.
7. **Deux entrées « production » mortes** formant une boucle fermée avec leurs tests : `run_advanced_rhetoric_pipeline` (`pipelines/advanced_rhetoric.py:23`) et `analyze_extract_advanced` (`orchestration/advanced_analyzer.py:17`).
8. **La suite in-package n'est pas seulement non collectée, elle est cassée.** 20 des 33 tests collectés **ERROR au *setup*** : les 10 de `test_enhanced_contextual_fallacy_analyzer.py` par cible de `patch` fossile `"plugins.AnalysisToolsPlugin.logic.…"` (`:47`, `:300` — chemin pré-consolidation), les 10 de `test_enhanced_complex_fallacy_analyzer.py` par la limite §1 (`:81`). Seul `test_enhanced_fallacy_severity_evaluator.py` passe (13/13). Doc et `tests/README.md` annoncent « 31 tests » : c'est un **compte de lignes `def test_`**, la collecte réelle en donne **33**.
9. **La suite canonique ne décide rien par défaut dans cet environnement** : sans `--disable-jvm-session`, 185/185 *skipped* sur une signature JVM (`pytest_sessionstart`) et la garde #2021 déclare le run vide. Le « 185 passed » ci-dessus n'a été obtenu qu'avec le drapeau.
10. **Ancrages de la fiche amont corrigés** (portée de mesure, sans re-exécution) : `logic/__init__.py` exporte `:11-15` et `__all__` `:17-24` (et non `:9-14` / `:16-23`) ; le graphe de dépendances de la façade est `plugin.py:42-53` (et non `:47-60`), `self.visualizer` `:53` (et non `:60`), `raw_results` `:88-92` (et non `:78-82`) ; le CDN mermaid est `rhetorical_result_visualizer.py:444` (et non `:474`).
11. **Réserve de mesure** : tous les statuts sont statiques (`git grep` sur les fichiers suivis + AST) sauf les trois `TypeError` et les deux comptes pytest, observés à l'exécution. « Vivant » signifie *référencé par du code de production*, jamais *exercé*.

---

*Fiche produite le **2026-09-11** sur la branche `docs/readme/2088-parents` (aucun changement de branche), par mesure directe : AST Python sur les 13 `.py` du sous-paquet, `git grep` sur les fichiers suivis, lecture des call-sites un par un, et deux exécutions pytest (`--collect-only` puis run réel, avec et sans `--disable-jvm-session`). La fiche de départ a été traitée comme une hypothèse et non comme une source : ses affirmations réfutées sont listées dans le rapport de tâche, non reprises ici. **Aucun fichier du dépôt modifié hors ce README** — ni `git add`, ni commit.*
