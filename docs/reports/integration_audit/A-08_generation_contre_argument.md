# Audit A-08: Projet 2.3.3 — Génération de Contre-Arguments

**Issue**: #754 (A-08) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet étudiant `2.3.3-generation-contre-argument/` (~3700 LOC, 25 fichiers Python, auteur "leo.sambrouck") a été intégré de manière **fidèle et enrichie** — le consolidé préserve les 5 stratégies rhétoriques et l'évaluateur 5-critères pondérés, ajoute l'intégration Semantic Kernel complète, le wiring CapabilityRegistry (5 capabilities), et le branchement dans 6 workflows DAG distincts.

**Verdict**: 🟢 **INTÉGRÉ fidèlement et enrichi** — aucune régression fonctionnelle. Le répertoire racine est archivable sans perte.

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Le projet étudiant a été digéré en **un bloc cohérent** sous `argumentation_analysis/agents/core/counter_argument/` :

| Fichier consolidé | Origine étudiante | LOC approx | Rôle |
|-------------------|-------------------|------------|------|
| `definitions.py` | `counter_agent/agent/definitions.py` | ~120 | Data classes + enums (Argument, Vulnerability, CounterArgument, EvaluationResult, CounterArgumentType, RhetoricalStrategy, ArgumentStrength) |
| `parser.py` | `counter_agent/agent/parser.py` | ~150 | `ArgumentParser` + `VulnerabilityAnalyzer` (NLP heuristique français) |
| `strategies.py` | `counter_agent/agent/strategies.py` | ~200 | 5 templates stratégiques + moteur de recommandation |
| `evaluator.py` | `counter_agent/evaluation/evaluator.py` | ~200 | `CounterArgumentEvaluator` 5-critères pondérés |
| `counter_agent.py` | `counter_agent/agent/` (agent+orchestrator) | ~300 | `CounterArgumentAgent(BaseAgent)` + `CounterArgumentPlugin` (3 @kernel_function) |
| `__init__.py` | Nouveau | ~60 | `register_with_capability_registry()` |

**CapabilityRegistry**: 1 service `counter_argument_agent` avec 5 capabilities : `counter_argument_generation`, `argument_parsing`, `vulnerability_analysis`, `rhetorical_strategy`, `counter_argument_evaluation`.

### 1.2 Préservation fonctionnelle

| Fonctionnalité étudiante | Préservée ? | Où | Notes |
|--------------------------|-------------|-----|-------|
| Parsing argumentaire (premises, conclusion, type) | ✅ Identique | `parser.py` | Même heuristique keyword-based |
| Analyse vulnérabilités (6 patterns) | ✅ Identique | `parser.py` VulnerabilityAnalyzer | Même regex patterns français |
| 5 stratégies rhétoriques | ✅ Identique | `strategies.py` | Socratic, Reductio, Analogical, Authority, Statistical |
| 5 critères d'évaluation pondérés | ✅ Identique | `evaluator.py` | Relevance(0.25), LogicalStrength(0.25), Persuasiveness(0.20), Originality(0.15), Clarity(0.15) |
| Génération LLM (OpenAI) | ✅ Supérieur | Via SK kernel (pas OpenAI direct) | Abstraction SK > couplage direct |
| Validation formelle Tweety (Dung) | ✅ Intégré | Pipeline DAG global | Tweety déjà intégré via af_handler |
| Pipeline end-to-end | ✅ Supérieur | 6 workflows DAG avec dépendances | Intégré au pipeline global |
| Web UI (Flask) | ❌ Perdu (remplacé) | API REST (FastAPI) | Normal — API = superset |
| Semantic Kernel orchestrator | ✅ Enrichi | `CounterArgumentPlugin` (3 @kernel_function) | Plugin natif SK |
| Taxonomie CSV | ❌ Non migré | Reste dans `2.3.3/data/` | Non nécessaire au runtime (taxonomy_medium.csv existe dans le core) |

**Score de préservation**: 8/10 fonctionnalités préservées ou supérieures (80%). Les 2 perdues sont des utilitaires/remplaçants (Web UI → API, taxonomie déjà dans le core).

### 1.3 Dilutions / Régressions

#### Dilution 1: Templates stratégiques sont des stubs (hérité de l'original)

**Localisation**: `strategies.py` — les méthodes `_apply_socratic_questioning()`, etc. contiennent des templates basiques. La génération réelle est déléguée au LLM via SK.
**Impact**: NONE — c'était déjà le cas dans le projet étudiant original. Les templates servent de fallback.
**Assessment**: Pas une dilution — fidèle à l'original.

#### Pas d'autre dilution

L'intégration est **fidèle et complète** : le core business logic (parsing, stratégies, évaluation, agent) a été porté tel quel, avec les ajouts nécessaires (SK plugin, registry, state writer, invoke callable, workflows).

### 1.4 Statut du répertoire racine `2.3.3-generation-contre-argument/`

**Verdict**: 🟡 **Référence pédagogique** (archivable)

- **0 import live Python** — aucun `from 2.3.3` n'existe dans le codebase
- **Docstrings référencent l'origine** : chaque fichier consolidé mentionne `"Adapted from 2.3.3-generation-contre-argument/..."`
- **Fichiers non-migrés** : `web_app.py`, `tweety_bridge.py`, `llm_generator.py`, `prompts.py`, `fallacy_workflow_orchestrator.py`, `tests/_disabled_test_counter_agent.py`, `libs/tweety-full.jar`, `data/*.csv`
- **Tests désactivés** : `_disabled_test_counter_agent.py` — préfixé `_disabled`, pas découvert par pytest

**Recommandation**: Archiver `2.3.3-generation-contre-argument/` → `docs/archives/student_projects/2.3.3-generation-contre-argument/` (préservé pour référence pédagogique).

---

## 2. Matrice des capabilities

| Capability (SUIVI 95%) | Module consolidé | Statut |
|------------------------|------------------|--------|
| Parsing argumentaire | `parser.py` ArgumentParser | ✅ Identique |
| Analyse vulnérabilités | `parser.py` VulnerabilityAnalyzer | ✅ Identique |
| 5 stratégies rhétoriques | `strategies.py` RhetoricalStrategies | ✅ Identique |
| Évaluation 5-critères | `evaluator.py` CounterArgumentEvaluator | ✅ Identique |
| Génération contre-arguments | `counter_agent.py` CounterArgumentAgent (LLM via SK) | ✅ Supérieur |
| Validation formelle | Pipeline DAG → Dung → extension computation | ✅ Intégré |
| Pipeline end-to-end | 6 workflows (sequential, conversational, spectacular, deep, conditional, extended) | ✅ Supérieur |

---

## 3. Cartographie des connections

```
2.3.3-generation-contre-argument/        argumentation_analysis/
├── counter_agent/agent/
│   ├── definitions.py ───────────────►  agents/core/counter_argument/definitions.py
│   ├── parser.py ─────────────────────►  agents/core/counter_argument/parser.py
│   ├── strategies.py ─────────────────►  agents/core/counter_argument/strategies.py
│   └── orchestration/ ───────────────►  (superseded by SK plugin + DAG workflows)
├── counter_agent/evaluation/
│   └── evaluator.py ──────────────────►  agents/core/counter_argument/evaluator.py
├── counter_agent/llm/
│   └── llm_generator.py ──────────────►  (superseded by SK kernel LLM calls)
├── counter_agent/logic/
│   ├── tweety_bridge.py ──────────────►  (superseded by core tweety_bridge + af_handler)
│   └── validator.py ──────────────────►  (superseded by pipeline Dung validation)
├── counter_agent/ui/
│   └── web_app.py ────────────────────►  (superseded by API REST FastAPI)
└── data/*.csv ────────────────────────►  (taxonomy_medium.csv already in core)

                                        NOUVEAU (intégration pipeline):
                                        ├── agents/core/counter_argument/__init__.py
                                        │   (register_with_capability_registry, 5 caps)
                                        ├── agents/core/counter_argument/counter_agent.py
                                        │   (CounterArgumentPlugin: 3 @kernel_function)
                                        ├── agents/factory.py
                                        │   (create_counter_argument_agent)
                                        ├── orchestration/invoke_callables.py
                                        │   (_invoke_counter_argument, LLM batch generation)
                                        ├── orchestration/state_writers.py
                                        │   (_write_counter_argument_to_state)
                                        └── orchestration/workflows.py
                                            (6 workflow phases, depends_on=["quality"])
```

---

## 4. Fix-intents

Aucun fix-intent nécessaire. L'intégration est fidèle, complète, et sans régression.

| # | Issue proposée | Priorité | Action |
|---|---------------|----------|--------|
| F1 | `fix(a-08): archive 2.3.3-generation-contre-argument/ to student_projects` | **LOW** | Déplacer vers `docs/archives/student_projects/` (0 import live) |

---

## 5. Conclusion

Le projet 2.3.3 est **fidèlement intégré** — les 5 stratégies rhétoriques et l'évaluateur 5-critères pondérés ont été portés tel quel, enrichis par l'intégration SK (3 kernel functions), le wiring CapabilityRegistry (5 capabilities), et le branchement dans 6 workflows DAG. L'agent est instancié via `AgentFactory.create_counter_argument_agent()`.

**Cas d'usage soutenance**: couvert — `CounterArgumentAgent` est l'un des agents les plus sophistiqués du système, avec génération LLM batch (k=2 par target, batch_size=12), auto-évaluation 5-critères, et branchement qualité-dépendant (s'exécute après la phase quality).

**Test coverage**: Track UU #724 dédié au counter-argument tracing, plus intégration dans de nombreux tests de workflow.

**Le répertoire `2.3.3-generation-contre-argument/` est archivable** immédiatement (0 import live).

---

## 6. Fichiers sources
- `argumentation_analysis/agents/core/counter_argument/` — 6 fichiers (definitions, parser, strategies, evaluator, counter_agent, __init__)
- `argumentation_analysis/agents/factory.py` — `create_counter_argument_agent()`
- `argumentation_analysis/orchestration/invoke_callables.py` — `_invoke_counter_argument()` + `_generate_counters_for_targets()` + `_evaluate_counter_arguments()`
- `argumentation_analysis/orchestration/state_writers.py` — `_write_counter_argument_to_state()`
- `argumentation_analysis/orchestration/workflows.py` — 6 workflow phases avec `depends_on=["quality"]`
- `argumentation_analysis/orchestration/registry_setup.py` — registration via `register_counter_arg()`
- `argumentation_analysis/core/shared_state.py` — `counter_arguments` list + `add_counter_argument()` method
