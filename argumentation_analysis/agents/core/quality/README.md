# `agents/core/quality/` — évaluation de la qualité argumentative (9 vertus, tri-état)

## Rôle et frontière

3 modules (1 608 lignes avec `__init__`) + 1 ressource JSON (44 l.) — l'axe **« cet argument est-il bon ? »** : il note un texte d'argument sur **9 vertus argumentatives** et rend un score borné au **plafond réellement atteignable** sur cette unité. Il ne détecte pas de sophismes (axe `informal/`), ne formalise rien (axe `logic/`) : il consomme du **texte d'argument** et produit des scores par vertu.

Le paquet vient du projet étudiant `2.3.5_argument_quality` (racine du dépôt), intégré sous architecture BaseAgent/SK (#35) : **ce n'est pas un `BaseAgent`** — la logique est exposée via un plugin SK (`plugins/quality_scoring_plugin.py`) et, en pipeline, via l'entrée de registre `quality_evaluator` (`orchestration/registry_setup.py:120-128`).

La frontière interne importante est celle du **tri-état** (#1907, PR #1923) : une vertu qui exige plus de matière que l'unité n'en porte est `NOT_APPLICABLE` — *honnêtement absente*, ni 0.0 ni dans le dénominateur. Le `note_finale` n'est donc plus sur une échelle fixe ; c'est `note_max_applicable` qui borne chaque unité.

## Composants publics

**`quality_evaluator.py`** (696 l.) — le producteur, seule surface réellement en production

- Taxonomie : `VERTUES` :219 (**9** entrées), `DETECTORS` :499 (**9** clés), 9 `def detect_*` :374-494 ;
- Contexte (#1907) : `ContextLevel` :235 (`CLAIM`/`LOCAL_CONTEXT`/`DOCUMENT`), `VirtueStatus` :259 (`evaluated`/`not_applicable`/`unavailable`), `VIRTUE_CONTEXT_REQUIREMENTS` :272 (**9** entrées), `VIRTUE_DEPENDENCIES` :300 (`fiabilite_sources` → `presence_sources`) ;
- Bandes d'inférence : `_DOCUMENT_MIN_SENTENCES` :310 (=5), `_LOCAL_MIN_SENTENCES` :311 (=2), `_LOCAL_MIN_WORDS` :318 (=30), `infer_context_level` :355 ;
- Admission clausulaire R2 (#1907) : `_CLAUSE_AWARE_VIRTUES` :330 (`frozenset` de **3** : `refutation_constructive`, `analogie_pertinente`, `structure_logique`), `is_multi_clause` :335 (`;`/`:` OU un connecteur de `connecteurs_structure_logique` OU ≥ 2 virgules) ;
- Évaluateur : `ArgumentQualityEvaluator` :515, `evaluate` :530, `evaluer_argument` :689 ;
- Dépendances : `dll_guard` :20, `_neutralize_faulty_torch` :42 (neutralise un torch cassé pour que thinc saute son import optionnel), `_load_deps` :85 (spaCy + textstat, **échec loud** en `RuntimeError`).

**`agentic_virtue_detectors.py`** (892 l.) — les variantes LLM multi-étapes (**expérimental**, cf. Statut)

Centre d'injection : `LLMCallable = Callable[[str], str]` :56, `AgenticDetectorError` :59, `set_default_llm_callable` :72, `_resolve_llm` :83. Brique de chaîne : `_parse_json_strict` :206, `_snap_to_scale` :227 ({0.0, 0.2, 0.5, 1.0}), `_run_chain_step` :240. **7 détecteurs** : `detect_refutation_constructive_agentic` :272, `detect_analogie_pertinente_agentic` :315, `detect_clarte_agentic` :434, `detect_pertinence_agentic` :528, `detect_structure_logique_agentic` :629, `detect_exhaustivite_agentic` :728, `detect_redondance_faible_agentic` :826 — regroupés dans `AGENTIC_DETECTORS` :875. `LEXICAL_ONLY_VIRTUES` :892 (`presence_sources`, `fiabilite_sources`) : 7 + 2 = 9, la taxonomie est complète.

**Comment détecter la dépendance LLM de ce module** : un `grep` de `kernel.invoke` / `ChatCompletion` n'y trouve **rien** — et c'est exact, le module n'importe aucun client. La dépendance entre par **injection** : chercher `LLMCallable` :56 et `_resolve_llm` :83 (qui **lève** `AgenticDetectorError` :87 si aucun callable n'est fourni), pas les mots-clés LLM.

**`ressources_argumentatives.json`** (44 l.) — lexique français (6 clés : `connecteurs_pertinence`, `citation_patterns`, `marqueurs_refutation`, `connecteurs_structure_logique`, `patterns_analogies`, `credible_sources`). Chargé à l'import par `_load_resources` :205 → `RESOURCES` :216, avec `_FALLBACK_RESOURCES` :142 en repli. **Aucun texte de corpus** : uniquement des marqueurs, patrons regex et noms de sources — rien de sensible, rien à caviarder.

**`__init__.py`** (20 l.) — exporte **3 noms** (`ArgumentQualityEvaluator`, `VERTUES`, `evaluer_argument`), tous vérifiés réels : **zéro fantôme**.

## Points d'entrée valides

1. **Registre Lego** : `orchestration/registry_setup.py:120-128` — `register_agent(name="quality_evaluator", agent_class=ArgumentQualityEvaluator, capabilities=["argument_quality"], invoke=_invoke_quality_evaluator)`. **Une seule surface**, voulue (#1842) : `__init__.py:18-20` documente l'absence de `register_with_capability_registry` et un `grep` le confirme (**0** occurrence dans le paquet) ;
2. **Phases workflow** : **22** littéraux `capability="argument_quality"` en production — 9 dans `orchestration/workflows.py` (:154, :216, :279, :464, :554, :563, :652 `quality_baseline`, :675, :713), les 13 autres dans `workflows/{argument_strength,belief_dynamics,comprehensive_analysis×2,debate_tournament×2,democratech×2,fact_check_pipeline,formal_debate}.py` et `orchestration/{collaborative_debate,router,sherlock_modern_orchestrator}.py` ;
3. **Invocation** : `orchestration/invoke_callables.py:421` `_invoke_quality_evaluator` → `evaluator.evaluate(arg_text)` :496 (par argument extrait, plafonné à 8), repli texte entier :570/:572 ;
4. **Plugin SK** : `plugins/quality_scoring_plugin.py:22` — **4** `@kernel_function` (`evaluate_argument_quality` :32, `get_quality_score` :45, `evaluate_with_cross_kb_context` :59, `list_virtues` :114). Chargé paresseusement par `agents/factory.py:86-89` et atteint en mode **conversationnel** (`conversational_orchestrator.py:374` `QualityAgent`, `speciality: "quality"` → `factory.get_plugin_instances` :633 → `factory.py:226`) ;
5. **Écrivain d'état** : `orchestration/state_writers.py:2286` mappe `"argument_quality"` → `_write_quality_to_state` :367 → `state.add_quality_score` :385/:416 ;
6. **Script de recherche** : `scripts/run_fb29_agentic_headtohead.py:80/:232/:247` (appelle `AGENTIC_DETECTORS` directement — hors production).

## Amont / aval

- **Amont** : sortie de la phase `extract` (`phase_extract_output["arguments"]`) et de `hierarchical_fallacy` (`phase_hierarchical_fallacy_output["fallacies"]`, pour la pénalité #289) ;
- **Aval** : `UnifiedAnalysisState.quality_scores` via `add_quality_score` ; le résumé de trace `_quality_trace_summary` (`invoke_callables.py:592`) rapporte la **part du plafond** (`_quality_fraction` :576) et non un « /10 » qui n'existe plus (#1907) ; `note_finale` est agrégé en `aggregate_score`.

## Statut d'intégration

| Composant | Statut | Preuve mesurée |
|---|---|---|
| `quality_evaluator.py` | **actif-critique** | `registry_setup.py:120-128` + `invoke_callables.py:496` + **22** phases `capability="argument_quality"` |
| `ressources_argumentatives.json` | **actif** | chargé à l'import (`quality_evaluator.py:205` → :216) ; alimente 6 des 9 détecteurs sur le chemin production (`detect_pertinence` :398, `detect_presence_sources` :415, `detect_refutation_constructive` :428, `detect_structure_logique` :437, `detect_analogie_pertinente` :448, `detect_fiabilite_sources` :457) |
| `__init__.py` | **actif** | `VERTUES` consommé par `plugins/quality_scoring_plugin.py:18` ; `ArgumentQualityEvaluator` par `registry_setup.py:115` et `invoke_callables.py:429` |
| `agentic_virtue_detectors.py` | **expérimental** | **0 appelant de production** : production appelle `evaluate(text)` **sans** `agentic_llm` (`invoke_callables.py:496/:570/:572`) ; `evaluate(agentic_llm=…)` n'est appelé avec un LLM non-`None` que par les tests (`tests/.../test_agentic_virtue_detectors.py:699/:745`) et le harnais `scripts/run_fb29_agentic_headtohead.py:247/:252` |

Statut global : **actif-critique** pour l'axe lexical ; `agentic_virtue_detectors.py` est **expérimental** et n'entre pas dans ce verdict.

## Artefacts et lecteurs

`per_argument_scores` (`arg_N` → `scores_par_vertu` + `statuts_par_vertu` + `note_max_applicable` + `contexte_evalue` + `rapport_detaille`), plus `aggregate_score`. Lecteurs : `state_writers.py:367` (état partagé), `restitution/` (les 9 vertus servent de profil d'électeurs à l'axe gouvernance, cf. `README` voisin), route HTTP et export multi-format.

Le résultat porte aussi `llm_assessment` / `reasoning_assessment` / `evidence_quality` / `bias_indicators` — **pas** produits par ce paquet mais par la passe d'enrichissement LLM séparée `_llm_enrich_quality` (`invoke_callables.py:638`, issue #290), fusionnés par `invoke_callables.py:527-540`. Ne pas les attribuer aux détecteurs agentiques.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/quality/ -v
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py -v
```

**138 `def test_`** sur **7 fichiers** (`test_quality_virtue_detectors.py` 36, `test_agentic_virtue_detectors.py` 30, `test_fb38_adversarial_verify.py` 20, `test_quality_evaluator.py` 20, `test_clause_aware_applicability_1907.py` 13, `test_virtue_tristate_1907.py` 13, `test_fb29_adversarial_verify.py` 6), compté par `grep -c "def test_"` sur le chemin, pas par collecte pytest. Plus **92** fichiers de test croisés mentionnant l'axe (`tests/unit/argumentation_analysis/orchestration/`, `evaluation/`, `plugins/test_quality_scoring_plugin.py`, `reporting/`).

## Frères et parent

Parent : `agents/core/` ([`../README.md`](../README.md)). Plugin hôte : [`../../../plugins/quality_scoring_plugin.py`](../../../plugins/quality_scoring_plugin.py). Câblage : [`../../../orchestration/registry_setup.py`](../../../orchestration/registry_setup.py). Consommateur aval direct : [`../governance/README.md`](../governance/README.md) (les 9 vertus deviennent un profil d'électeurs). Garde d'invariant : `tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py` (:39, :189).

## Limites connues

- **`agentic_virtue_detectors.py` est expérimental, pas branché.** 892 lignes, 7 détecteurs, un point d'injection documenté — et **zéro appelant de production**. Le contrat d'injection que le module annonce n'existe pas : `agentic_virtue_detectors.py:76` renvoie à `invoke_callables._get_quality_llm`, **fonction qui n'existe nulle part** dans le dépôt, et `set_default_llm_callable` :72 n'a **aucun appelant** (ni production, ni test). Le chemin `evaluate(agentic_llm=…)` n'est donc exercé que par les tests. Non réparé (hors périmètre de ce README).
- **Le paquet est fail-loud sur ses dépendances** : sans `textstat` ou sans le modèle spaCy `fr_core_news_sm`, `_load_deps` :85 lève `RuntimeError`. C'est délibéré (#1019), mais `_invoke_quality_evaluator` n'entoure pas l'appel (:496) — la phase qualité peut donc propager l'exception dans un environnement nu.
- **`detect_exhaustivite`** :479 garde un commentaire « Texte trop court pour juger » puis retourne `0.0` — branche désormais **inatteignable** en pratique, puisque la vertu est classée `DOCUMENT` (`VIRTUE_CONTEXT_REQUIREMENTS` :297) et que `evaluate` n'appelle jamais un détecteur dont le niveau requis dépasse l'unité (:627). Le commentaire décrit un comportement que le tri-état a supprimé.
- **Étiquetage de trace inexact** : `sherlock_modern_orchestrator.py:229` attribue l'étape à `agent="QualityScoringPlugin"` alors que le chemin de code est `_invoke_quality_evaluator` (:215) — le plugin n'est pas invoqué là. Faux seulement sur l'étiquette, pas sur le résultat.
- **Un commentaire de registre nomme une capacité qui n'existe pas** : `registry_setup.py:124` justifie la suppression par « quality_scoring had zero production consumers ». `quality_scoring` est un **nom de plugin** (`factory.py:86`), jamais un littéral `capability=` — et ce plugin, lui, **est** atteint en mode conversationnel (`conversational_orchestrator.py:374` → :633). La conclusion (une seule entrée de registre) reste juste, la justification est mal formulée.
- **Deux vertus restent lexicales par choix** (`LEXICAL_ONLY_VIRTUES` :892) : `presence_sources` et `fiabilite_sources`. Les agentiser fabriquerait des sources absentes du texte — c'est une soustraction délibérée, pas un oubli.
