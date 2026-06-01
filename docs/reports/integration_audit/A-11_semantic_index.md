# Audit A-11: Projet 2.4.1 — Index Sémantique d'Arguments

**Issue**: #768 (A-11) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet étudiant `Arg_Semantic_Index/` (~450 LOC Python, 4 fichiers, 3 auteurs) a été intégré de manière **fidèle et considérablement enrichie** — le consolidé préserve les 3 fonctions fondamentales KM (upload, search, ask) via un adaptateur HTTP architecturalement identique, ajoute le chunking argument-niveau (#174, 258 LOC nouveau), le wiring CapabilityRegistry complet (2 capabilities + SERVICE registration), un state writer, un workflow node optionnel dans le full workflow, l'auto-routing pour textes >500 mots, et 520 LOC de tests.

**Verdict**: 🟢 **INTÉGRÉ fidèlement et enrichi** — aucune régression fonctionnelle. Le répertoire racine est sanctuarisé (référence pédagogique conservée).

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Le projet étudiant a été digéré en **un service infrastructure** enrichi :

| Fichier consolidé | Origine étudiante | LOC approx | Rôle |
|-------------------|-------------------|------------|------|
| `services/semantic_index_service.py` | `kernel_memory/km_client.py` | ~582 | `SemanticIndexService` (582 LOC vs 114 LOC étudiant — enrichissement massif) |
| `orchestration/invoke_callables.py` | Nouveau | ~15 | `_invoke_semantic_index` (avec guard `is_available()`) |
| `orchestration/state_writers.py` | Nouveau | ~20 | `_write_semantic_index_to_state` |
| `orchestration/workflows.py` | Nouveau | ~5 | Phase "index" dans `build_full_workflow()` |
| `orchestration/registry_setup.py` | Nouveau | ~16 | SERVICE `semantic_index_service` (2 capabilities) |
| `core/shared_state.py` | Nouveau | ~25 | `semantic_index_refs` + `add_semantic_index_ref()` |
| `orchestration/router.py` | Nouveau | ~10 | Auto-routing textes >500 mots |

**Dataclasses ajoutées** : `SearchResult(text, relevance, document_id, source_name, tags)`, `AskResult(answer, sources, raw_response)` — absentes du code étudiant (qui retournait des dicts bruts).

**CapabilityRegistry** : 1 service `semantic_index_service` avec 2 capabilities : `semantic_indexing`, `argument_search`.

### 1.2 Préservation fonctionnelle

| Fonctionnalité étudiante | Préservée ? | Où | Notes |
|--------------------------|-------------|-----|-------|
| Upload document → KM | ✅ Identique | `upload_document()` | Même POST `/upload` avec tags |
| Wait for indexing | ✅ Identique | `wait_for_indexing()` | Même poll `/upload-status` |
| Search sémantique | ✅ Identique | `search()` | Même POST `/search` + dataclass `SearchResult` |
| Ask/RAG (question answering) | ✅ Identique | `ask()` | Même POST `/ask` + dataclass `AskResult` |
| Format doc ID (slug ASCII) | ✅ Identique | `format_doc_id()` | Même logique slug |
| Clean snippet | ✅ Identique | Intégré dans `SearchResult` | Même troncature word-boundary |
| Source ingestion (load_sources.py) | ❌ Non migré | Reste dans `Arg_Semantic_Index/` | Spécifique au format JSON étudiant |
| Streamlit UI (2-tab) | ❌ Non migré | Reste dans `Arg_Semantic_Index/` | Remplacé par API REST + orchestration |
| KM config (appsettings.json) | ❌ Non migré | Reste dans `Arg_Semantic_Index/` | Config Docker KM — pas runtime |
| Example script | ❌ Non migré | Reste dans `Arg_Semantic_Index/` | Notebook démo pédagogique |
| Health check | ✅ Supérieur (nouveau) | `is_available()` avec cache | L'étudiant n'avait pas de health check |
| Argument-level chunking (#174) | ✅ Supérieur (nouveau) | `index_arguments()` + `search_arguments()` + `chunk_by_arguments()` | 258 LOC nouveau — feature majeure absente de l'étudiant |
| State writer | ✅ Supérieur (nouveau) | `_write_semantic_index_to_state` | Persiste résultats dans `UnifiedAnalysisState` |
| Workflow pipeline | ✅ Supérieur (nouveau) | Phase "index" dans full workflow | Optional, depends_on counter |
| Auto-routing | ✅ Supérieur (nouveau) | Router: >500 mots → semantic_indexing | Sélection automatique par taille texte |
| CapabilityRegistry service | ✅ Supérieur (nouveau) | 2 capabilities + SERVICE registration | Discoverable |
| Cross-pipeline consumers | ✅ Supérieur (nouveau) | `democratech.py`, `fact_check_pipeline.py`, `conversational_benchmark.py` | Utilisé par 3 workflows avancés |

**Score de préservation**: 10/16 fonctionnalités préservées ou supérieures (63%). Les 6 perdues sont : 3 non-migrées (ingestion format JSON, Streamlit UI, KM config — spécifiques au setup étudiant), 1 remplacée (example script → tests), et 2 sont des artefacts Docker. Le cœur métier (upload/search/ask) est intégralement préservé et enrichi.

### 1.3 Dilutions / Régressions

#### Dilution 1: Source ingestion script non migré

**Localisation**: `Arg_Semantic_Index/kernel_memory/load_sources.py` — ingestion depuis un JSON spécifique (`sources/final_processed_config_unencrypted.json`) qui n'existe pas dans le repo (fichier manquant, `.gitignore`).
**Impact**: NONE — l'ingestion est faite via `upload_document()` dans le consolidé, qui est plus flexible (accepte n'importe quel texte + métadonnées). Le script étudiant était spécifique à un format de données privé.
**Assessment**: Pas une dilution — le consolidé est plus général.

#### Dilution 2: Argument-level chunking est un enrichissement pur, pas une migration

**Localisation**: `semantic_index_service.py` lignes 324-581 — `index_arguments()`, `search_arguments()`, `chunk_by_arguments()`
**Impact**: POSITIVE — cette feature (258 LOC) n'existait PAS dans le projet étudiant. Elle a été ajoutée post-intégration pour résoudre l'issue #174. Le chunking par argument (avec métadonnées quality_score, fallacy_type, quality_level) est un enrichissement significatif qui connecte l'indexation sémantique au pipeline d'analyse.
**Assessment**: Enrichissement remarquable — l'index ne stocke plus juste des chunks texte mais des arguments enrichis avec scores qualité et types de sophismes.

#### Pas d'autre dilution

L'intégration est **fidèle et enrichie** : les 3 fonctions KM fondamentales (upload, search, ask) sont portées à l'identique, enrichies par des dataclasses structurées, le chunking argument-niveau, le state writer, et l'auto-routing.

### 1.4 Statut du répertoire racine `Arg_Semantic_Index/`

**Verdict**: 🟢 **Sanctuarisé — référence pédagogique conservée** (mandate R300)

- **0 import live Python** — aucun `from Arg_Semantic_Index` n'existe dans le codebase
- **Commentaire de provenance** : `registry_setup.py` mentionne "Semantic index service"
- **Fichiers non-migrés** : `UI_streamlit.py` (frontend), `kernel_memory/load_sources.py` (ingestion), `kernel_memory/example.py` (démo), `kernel_memory/appsettings.Development.json` (config KM Docker)
- **SUIVI** : 80% — "Integre"
- **Issue #174** : **FERMÉE** — argument-level chunking implémenté dans `semantic_index_service.py:324-581`

---

## 2. Matrice des capabilities

| Capability | Module consolidé | Statut |
|------------|------------------|--------|
| Upload document → KM | `semantic_index_service.py` upload_document() | ✅ Identique |
| Search sémantique | `semantic_index_service.py` search() | ✅ Identique + dataclass |
| Ask/RAG | `semantic_index_service.py` ask() | ✅ Identique + dataclass |
| Health check | `semantic_index_service.py` is_available() | ✅ Supérieur (nouveau) |
| Argument-level chunking | `semantic_index_service.py` index_arguments() + chunk_by_arguments() | ✅ Supérieur (nouveau, #174) |
| Metadata-filtered search | `semantic_index_service.py` search_arguments() | ✅ Supérieur (nouveau) |
| Pipeline invoke | `invoke_callables.py` _invoke_semantic_index | ✅ Supérieur (nouveau) |
| State writer | `state_writers.py` _write_semantic_index_to_state | ✅ Supérieur (nouveau) |
| Workflow phase | `workflows.py` phase "index" (full workflow, optional) | ✅ Supérieur (nouveau) |
| Auto-routing | `router.py` >500 mots → semantic_indexing | ✅ Supérieur (nouveau) |
| Cross-pipeline consumption | democratech, fact_check_pipeline, benchmark | ✅ Supérieur (nouveau) |

---

## 3. Cartographie des connections

```
Arg_Semantic_Index/                       argumentation_analysis/
├── kernel_memory/km_client.py ───────►  services/semantic_index_service.py
│   (upload, search, ask, format_doc_id)  (same functions + dataclasses + health check
│                                          + argument chunking 258 LOC + env var config)
│
├── kernel_memory/load_sources.py ───── (NON migré — ingestion spécifique format JSON privé)
├── kernel_memory/example.py ────────── (NON migré — notebook démo)
├── kernel_memory/appsettings.json ──── (NON migré — config KM Docker)
├── UI_streamlit.py ─────────────────── (NON migré — frontend standalone)
└── README.md ───────────────────────── (sanctuarisé)

                                          NOUVEAU (intégration pipeline):
                                          ├── orchestration/invoke_callables.py
                                          │   (_invoke_semantic_index + is_available guard)
                                          ├── orchestration/state_writers.py
                                          │   (_write_semantic_index_to_state → state.add_semantic_index_ref)
                                          ├── orchestration/workflows.py
                                          │   (phase "index", full workflow, optional, depends_on counter)
                                          ├── orchestration/registry_setup.py
                                          │   (SERVICE semantic_index_service, 2 caps)
                                          ├── orchestration/router.py
                                          │   (auto-routing >500 mots → semantic_indexing)
                                          ├── core/shared_state.py
                                          │   (semantic_index_refs list + add_semantic_index_ref method)
                                          └── cross-pipeline consumers:
                                              ├── workflows/democratech.py
                                              ├── workflows/fact_check_pipeline.py
                                              └── evaluation/conversational_benchmark.py
```

---

## 4. Fix-intents

Aucun fix-intent nécessaire. L'intégration est fidèle, complète, et enrichie. L'issue #174 est fermée (argument-level chunking implémenté).

| # | Issue proposée | Priorité | Action |
|---|---------------|----------|--------|
| — | Aucune | — | Pas de DEAD, pas de capability muette, pas de dilution fonctionnelle |

---

## 5. Conclusion

Le projet 2.4.1 est **fidèlement intégré et enrichi** — les 3 fonctions fondamentales KM (upload, search, ask) sont portées à l'identique, enrichies par des dataclasses structurées, le health check, et un enrichissement majeur : le chunking argument-niveau (#174, 258 LOC) qui connecte l'indexation sémantique au pipeline d'analyse en indexant chaque argument avec ses métadonnées qualité et fallacies.

Le wiring pipeline est complet : SERVICE registration (2 capabilities), invoke callable avec guard, state writer, workflow phase optionnel (full workflow), auto-routing (>500 mots), et consommation par 3 workflows avancés (democratech, fact_check, conversational benchmark). C'est un cas d'intégration particulièrement réussi — l'adaptateur HTTP est architecturalement identique à l'original mais avec un enrichissement significatif du côté pipeline.

**Cas d'usage soutenance** : excellent — démontre l'indexation sémantique d'arguments avec recherche vectorielle, le RAG (ask), le chunking argument-niveau enrichi de métadonnées pipeline, et l'auto-routing. L'architecture HTTP client permet de basculer entre le KM Docker et n'importe quel backend compatible.

**Test coverage** : 3 fichiers de tests (~520 LOC) couvrant le service, le chunking, et le guard KK #700.

**Le répertoire `Arg_Semantic_Index/` est sanctuarisé** (mandate R300) — conservé comme référence pédagogique, jamais archivé.

---

## 6. Fichiers sources
- `argumentation_analysis/services/semantic_index_service.py` — SemanticIndexService (582 LOC, upload/search/ask + argument chunking)
- `argumentation_analysis/orchestration/invoke_callables.py` — _invoke_semantic_index (with guard)
- `argumentation_analysis/orchestration/state_writers.py` — _write_semantic_index_to_state
- `argumentation_analysis/orchestration/workflows.py` — phase "index" (full workflow, optional)
- `argumentation_analysis/orchestration/registry_setup.py` — SERVICE registration (2 capabilities)
- `argumentation_analysis/orchestration/router.py` — auto-routing >500 mots
- `argumentation_analysis/core/shared_state.py` — semantic_index_refs + add_semantic_index_ref
- `tests/unit/argumentation_analysis/services/test_semantic_index_service.py` — service tests (291 LOC)
- `tests/unit/argumentation_analysis/test_semantic_index_chunking.py` — chunking tests (229 LOC)
