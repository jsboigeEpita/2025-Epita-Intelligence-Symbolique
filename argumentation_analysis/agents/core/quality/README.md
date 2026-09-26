# `agents/core/quality/` — évaluation de la qualité argumentative (9 vertus, tri-état)

## Rôle et frontière

3 modules (1 608 lignes avec `__init__`) + 1 ressource JSON (44 l.) — l'axe **« cet argument est-il bon ? »** : il note un texte d'argument sur **9 vertus argumentatives** et rend un score borné au **plafond réellement atteignable** sur cette unité. Il ne détecte pas de sophismes (axe `informal/`), ne formalise rien (axe `logic/`) : il consomme du **texte d'argument** et produit des scores par vertu.

Le paquet vient du projet étudiant `2.3.5_argument_quality` (racine du dépôt), intégré sous architecture BaseAgent/SK (#35) : **ce n'est pas un `BaseAgent`** — la logique est exposée via un plugin SK (`plugins/quality_scoring_plugin.py`) et, en pipeline, via l'entrée de registre `quality_evaluator` (`orchestration/registry_setup.py`).

La frontière interne importante est celle du **tri-état** (#1907, PR #1923) : une vertu qui exige plus de matière que l'unité n'en porte est `NOT_APPLICABLE` — *honnêtement absente*, ni 0.0 ni dans le dénominateur. Le `note_finale` n'est donc plus sur une échelle fixe ; c'est `note_max_applicable` qui borne chaque unité.

## Composants publics

**`quality_evaluator.py`** (696 l.) — le producteur, seule surface réellement en production

- Taxonomie : `VERTUES` (**9** entrées), `DETECTORS` (**9** clés), 9 `def detect_*` ;
- Contexte (#1907) : `ContextLevel` (`CLAIM`/`LOCAL_CONTEXT`/`DOCUMENT`), `VirtueStatus` (`evaluated`/`not_applicable`/`unavailable`), `VIRTUE_CONTEXT_REQUIREMENTS` (**9** entrées), `VIRTUE_DEPENDENCIES` (`fiabilite_sources` → `presence_sources`) ;
- Bandes d'inférence : `_DOCUMENT_MIN_SENTENCES` (=5), `_LOCAL_MIN_SENTENCES` (=2), `_LOCAL_MIN_WORDS` (=30), `infer_context_level` ;
- Admission clausulaire R2 (#1907) : `_CLAUSE_AWARE_VIRTUES` (`frozenset` de **3** : `refutation_constructive`, `analogie_pertinente`, `structure_logique`), `is_multi_clause` (`;`/`:` OU un connecteur de `connecteurs_structure_logique` OU ≥ 2 virgules) ;
- Évaluateur : `ArgumentQualityEvaluator`, `evaluate`, `evaluer_argument` ;
- Dépendances : `dll_guard`, `_neutralize_faulty_torch` (neutralise un torch cassé pour que thinc saute son import optionnel), `_load_deps` (spaCy + textstat, **échec loud** en `RuntimeError`).

**`agentic_virtue_detectors.py`** (892 l.) — les variantes LLM multi-étapes (**expérimental**, cf. Statut)

Centre d'injection : `LLMCallable = Callable[[str], str]`, `AgenticDetectorError`, `_resolve_llm` (le paramètre `llm=` par détecteur est l'UNIQUE point d'injection depuis #2137 — `set_default_llm_callable` retiré, zéro appelant). Brique de chaîne : `_parse_json_strict`, `_snap_to_scale` ({0.0, 0.2, 0.5, 1.0}), `_run_chain_step`. **7 détecteurs** : `detect_refutation_constructive_agentic`, `detect_analogie_pertinente_agentic`, `detect_clarte_agentic`, `detect_pertinence_agentic`, `detect_structure_logique_agentic`, `detect_exhaustivite_agentic`, `detect_redondance_faible_agentic` — regroupés dans `AGENTIC_DETECTORS`. `LEXICAL_ONLY_VIRTUES` (`presence_sources`, `fiabilite_sources`) : 7 + 2 = 9, la taxonomie est complète.

**Comment détecter la dépendance LLM de ce module** : un `grep` de `kernel.invoke` / `ChatCompletion` n'y trouve **rien** — et c'est exact, le module n'importe aucun client. La dépendance entre par **injection** : chercher `LLMCallable` et `_resolve_llm` (qui **lève** `AgenticDetectorError` si aucun callable n'est fourni), pas les mots-clés LLM.

**`ressources_argumentatives.json`** (44 l.) — lexique français (6 clés : `connecteurs_pertinence`, `citation_patterns`, `marqueurs_refutation`, `connecteurs_structure_logique`, `patterns_analogies`, `credible_sources`). Chargé à l'import par `_load_resources` → `RESOURCES`, avec `_FALLBACK_RESOURCES` en repli. **Aucun texte de corpus** : uniquement des marqueurs, patrons regex et noms de sources — rien de sensible, rien à caviarder.

**`__init__.py`** (20 l.) — exporte **3 noms** (`ArgumentQualityEvaluator`, `VERTUES`, `evaluer_argument`), tous vérifiés réels : **zéro fantôme**.

## Points d'entrée valides

1. **Registre Lego** : `orchestration/registry_setup.py` — `register_agent(name="quality_evaluator", agent_class=ArgumentQualityEvaluator, capabilities=["argument_quality"], invoke=_invoke_quality_evaluator)`. **Une seule surface**, voulue (#1842) : `__init__.py` documente l'absence de `register_with_capability_registry` et un `grep` le confirme (**0** occurrence dans le paquet) ;
2. **Phases workflow** : **22** littéraux `capability="argument_quality"` en production — 9 dans `orchestration/workflows.py` (dont la phase `quality_baseline`), les 13 autres dans `workflows/{argument_strength,belief_dynamics,comprehensive_analysis×2,debate_tournament×2,democratech×2,fact_check_pipeline,formal_debate}.py` et `orchestration/{collaborative_debate,router,sherlock_modern_orchestrator}.py` ;
3. **Invocation** : `orchestration/invoke_callables.py` `_invoke_quality_evaluator` → `evaluator.evaluate(arg_text)` (par argument extrait, plafonné à 8), repli texte entier ;
4. **Plugin SK** : `plugins/quality_scoring_plugin.py` — **4** `@kernel_function` (`evaluate_argument_quality`, `get_quality_score`, `evaluate_with_cross_kb_context`, `list_virtues`). Chargé paresseusement par `agents/factory.py` et atteint en mode **conversationnel** (`conversational_orchestrator.py` `QualityAgent`, `speciality: "quality"` → `factory.get_plugin_instances` → `factory.py`) ;
5. **Écrivain d'état** : `orchestration/state_writers.py` mappe `"argument_quality"` → `_write_quality_to_state` → `state.add_quality_score` ;
6. **Script de recherche** : `scripts/run_fb29_agentic_headtohead.py` (appelle `AGENTIC_DETECTORS` directement — hors production).

## Amont / aval

- **Amont** : sortie de la phase `extract` (`phase_extract_output["arguments"]`) et de `hierarchical_fallacy` (`phase_hierarchical_fallacy_output["fallacies"]`, pour la pénalité #289) ;
- **Aval** : `UnifiedAnalysisState.quality_scores` via `add_quality_score` ; le résumé de trace `_quality_trace_summary` (`invoke_callables.py`) rapporte la **part du plafond** (`_quality_fraction`) et non un « /10 » qui n'existe plus (#1907) ; `note_finale` est agrégé en `aggregate_score`.

## Statut d'intégration

| Composant | Statut | Preuve mesurée |
|---|---|---|
| `quality_evaluator.py` | **actif-critique** | `registry_setup.py` + `invoke_callables.py` + **22** phases `capability="argument_quality"` |
| `ressources_argumentatives.json` | **actif** | chargé à l'import (`quality_evaluator.py` →) ; alimente 6 des 9 détecteurs sur le chemin production (`detect_pertinence`, `detect_presence_sources`, `detect_refutation_constructive`, `detect_structure_logique`, `detect_analogie_pertinente`, `detect_fiabilite_sources`) |
| `__init__.py` | **actif** | `VERTUES` consommé par `plugins/quality_scoring_plugin.py` ; `ArgumentQualityEvaluator` par `registry_setup.py` et `invoke_callables.py` |
| `agentic_virtue_detectors.py` | **expérimental** | **0 appelant de production** : production appelle `evaluate(text)` **sans** `agentic_llm` (`invoke_callables.py`) ; `evaluate(agentic_llm=…)` n'est appelé avec un LLM non-`None` que par les tests (`tests/.../test_agentic_virtue_detectors.py`) et le harnais `scripts/run_fb29_agentic_headtohead.py` |

Statut global : **actif-critique** pour l'axe lexical ; `agentic_virtue_detectors.py` est **expérimental** et n'entre pas dans ce verdict.

## Artefacts et lecteurs

`per_argument_scores` (`arg_N` → `scores_par_vertu` + `statuts_par_vertu` + `note_max_applicable` + `contexte_evalue` + `rapport_detaille`), plus `aggregate_score`. Lecteurs : `state_writers.py` (état partagé), `restitution/` (les 9 vertus servent de profil d'électeurs à l'axe gouvernance, cf. `README` voisin), route HTTP et export multi-format.

Le résultat porte aussi `llm_assessment` / `reasoning_assessment` / `evidence_quality` / `bias_indicators` — **pas** produits par ce paquet mais par la passe d'enrichissement LLM séparée `_llm_enrich_quality` (`invoke_callables.py`, issue #290), fusionnés par `invoke_callables.py`. Ne pas les attribuer aux détecteurs agentiques.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/quality/ -v
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py -v
```

**138 `def test_`** sur **7 fichiers** (`test_quality_virtue_detectors.py` 36, `test_agentic_virtue_detectors.py` 30, `test_fb38_adversarial_verify.py` 20, `test_quality_evaluator.py` 20, `test_clause_aware_applicability_1907.py` 13, `test_virtue_tristate_1907.py` 13, `test_fb29_adversarial_verify.py` 6), compté par `grep -c "def test_"` sur le chemin, pas par collecte pytest. Plus **92** fichiers de test croisés mentionnant l'axe (`tests/unit/argumentation_analysis/orchestration/`, `evaluation/`, `plugins/test_quality_scoring_plugin.py`, `reporting/`).

## Frères et parent

Parent : `agents/core/` ([`../README.md`](../README.md)). Plugin hôte : [`../../../plugins/quality_scoring_plugin.py`](../../../plugins/quality_scoring_plugin.py). Câblage : [`../../../orchestration/registry_setup.py`](../../../orchestration/registry_setup.py). Consommateur aval direct : [`../governance/README.md`](../governance/README.md) (les 9 vertus deviennent un profil d'électeurs). Garde d'invariant : `tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py`.

## Limites connues

- **`agentic_virtue_detectors.py` est expérimental, pas branché — MARQUÉ (#2137)** : bannière EXPERIMENTAL en tête de docstring. 7 détecteurs, **zéro appelant de production** — le chemin lexical (`evaluate(text)`) est ce que le pipeline exécute. `set_default_llm_callable` (aucun appelant ni production ni test) a été **retiré (#2137)** avec le global `_DEFAULT_LLM` ; la citation fantôme `_get_quality_llm` n'existe plus (le docstring citait le vrai point d'injection : le paramètre `llm=`, désormais seul). Le chemin `evaluate(agentic_llm=…)` reste exercé par les tests et le harnais `scripts/run_fb29_agentic_headtohead.py`. Terminer le câblage = scope **#1105/FB-29**, pas de ce triage.
- **Le paquet est fail-loud sur ses dépendances** : sans `textstat` ou sans le modèle spaCy `fr_core_news_sm`, `_load_deps` lève `RuntimeError`. C'est délibéré (#1019), mais `_invoke_quality_evaluator` n'entoure pas l'appel — la phase qualité peut donc propager l'exception dans un environnement nu.
- **`detect_exhaustivite`** retourne `0.0` sous le libellé « Texte trop court pour juger » — branche **inatteignable sur le chemin courant**, puisque la vertu est classée `DOCUMENT` (`VIRTUE_CONTEXT_REQUIREMENTS`) et que `evaluate` n'appelle jamais un détecteur dont le niveau requis dépasse l'unité. La mesure est plus étroite qu'elle n'en a l'air : `evaluate` accepte un `context_level` **déclaré**, et `infer_context_level` ne le déduit qu'en l'absence de déclaration. C'est donc **l'absence de tout appelant déclarant un niveau** (aucun `context_level=` en production — seul l'appel interne) qui rend la branche morte, pas le dispositif lui-même : un appelant déclarant `DOCUMENT` sur un texte court la réveillerait. Le libellé décrit un comportement que le tri-état a supprimé.
- **Étiquetage de trace inexact — résolu (#2138)** : `sherlock_modern_orchestrator.py` attribuait l'étape à `agent="QualityScoringPlugin"` alors que le chemin de code est `_invoke_quality_evaluator` (le plugin n'est pas invoqué là). L'étiquette porte désormais le composant réel, `ArgumentQualityEvaluator`.
- **Un commentaire de registre nomme une capacité qui n'existe pas** : `registry_setup.py` justifie la suppression par « quality_scoring had zero production consumers ». `quality_scoring` est un **nom de plugin** (`factory.py`), jamais un littéral `capability=` — et ce plugin, lui, **est** atteint en mode conversationnel (`conversational_orchestrator.py` →). La conclusion (une seule entrée de registre) reste juste, la justification est mal formulée.
- **Deux vertus restent lexicales par choix** (`LEXICAL_ONLY_VIRTUES`) : `presence_sources` et `fiabilite_sources`. Les agentiser fabriquerait des sources absentes du texte — c'est une soustraction délibérée, pas un oubli.
