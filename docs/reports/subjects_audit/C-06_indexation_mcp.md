# Audit C-06: Section II-D/E Indexation + Automatisation MCP (10 sujets)

**Issue**: #784 (C-06) | **Epic**: #744 | **Date audit**: 2026-05-31

## Préambule — Table de correspondance

| Code sujet | Statut | Lien Epic A si traité |
|------------|--------|-----------------------|
| 2.4.1 Index sémantique | 🟢 Treated | #768 (A-11) |
| 2.4.2 Vecteurs types arguments | 🟠 Angle mort (partial code) | — |
| 2.4.3 Base connaissances argumentatives | 🟠 Angle mort (partial code) | — |
| 2.4.4 Fact-checking | 🟠 Angle mort (RICH code, NO sujet) | — |
| 2.5.1 Automatisation analyse | 🟢 De-facto covered (UnifiedPipeline) | — |
| 2.5.2 Pipeline traitement | 🟢 De-facto covered (pipelines/) | — |
| 2.5.3 Serveur MCP | 🟢 Treated | #773 (A-12) |
| 2.5.4 Outils MCP | 🟠 Angle mort (23 tools implemented) | — |
| 2.5.5 Serveur MCP Tweety | 🔴 Angle mort (subsumed by 2.5.3) | — |
| 2.5.6 Protection IA | 🟢 Treated (not submitted) | #774 (A-13) |

## Résultats détaillés

### 🟢 TREATED (5)

**2.4.1 Index sémantique** — Student project (score 80%). Code: `SemanticIndexService` (index, search, ask), `CapabilityRegistry`. Cross-ref → Epic A #768 (A-11).

**2.5.3 Serveur MCP** — Student project (score 90%). Code: `services/mcp_server/main.py` — FastMCP server, session manager, Dockerfile. Cross-ref → Epic A #773 (A-12).

**2.5.6 Protection IA** — Not submitted (score 0%), but AI Shield framework recreated from soutenance. Code: 688 LOC, 33 passing tests, 4 presets. Cross-ref → Epic A #774 (A-13).

**2.5.1 Automatisation analyse** — De-facto covered by `orchestration/unified_pipeline.py` (auto-registers all components, 3 workflows light/standard/full) + `run_orchestration.py` (CLI automation). Not an angle mort in practice.

**2.5.2 Pipeline traitement** — De-facto covered by `pipelines/` (analysis_pipeline, embedding_pipeline, reporting_pipeline, unified_text_analysis, advanced_rhetoric) + `pipelines/orchestration/`. Subsumed by 2.5.1.

### 🟠 ANGLE MORTS (4)

**2.4.4 Fact-checking** — ⭐ RICHEST undocumented capability. Full pipeline exists but NO sujet file:
- `services/fact_verification_service.py` — `VerificationStatus` (7 states), `SourceReliability` (5 levels)
- `agents/tools/analysis/fact_claim_extractor.py` — `FactClaimExtractor`, `ClaimType` (10 types)
- `orchestration/fact_checking_orchestrator.py` — integrates claim extraction + fallacy analysis + ExternalVerificationPlugin
- `workflows/fact_check_pipeline.py` — 6-phase declarative workflow
- `plugin_framework/.../external_verification/plugin.py`
- **Recommendation**: Warrants its own Epic A audit issue. Origin: student PR #8 (Candy Nguyen).

**2.4.2 Vecteurs types arguments** — Partial code: `nlp/embedding_utils.py` (OpenAI + Sentence Transformers), `pipelines/embedding_pipeline.py` (28 KB full pipeline), `core/models/toulmin_model.py` (typed argument components). **Gap**: the "by argument-type" vectorization angle (vectorizing arguments classified by Toulmin/rhetorical type rather than raw chunks) is the actual angle mort. Closely adjacent to 2.4.1 (#174 "argument-level chunking").

**2.4.3 Base connaissances argumentatives** — Partial: `SemanticIndexService` (Kernel Memory RAG), evaluation corpora (`baseline_corpus_v1.json`), fact-check indexing. **Gap**: no persistent structured argument KB with relations/provenance — would be a thin design layer over existing pieces.

**2.5.4 Outils MCP** — 23 MCP tools implemented (10 V1 + 13 V2 in `services/mcp_server/tools/`), but no dedicated sujet. Functionally covered by 2.5.3 audit (#773). Recommend folding into #773 scope.

### 🔴 ANGLE MORT SUBSUMED (1)

**2.5.5 Serveur MCP Tweety** — No dedicated server exists. Tweety capabilities ARE already exposed through the unified 2.5.3 MCP server (Dung semantics, PL/FOL/Modal via TweetyBridge). **Recommendation**: classify as "subsumed by #773" — no new audit needed.

## Synthèse C-06

- **5/10 🟢 Treated** (3 student + 2 de-facto covered)
- **4/10 🟠 Angle mort** (2.4.4 HIGH, 2.4.2/2.4.3/2.5.4 MEDIUM)
- **1/10 🔴 Subsumed** (2.5.5 → fold into #773)

## Fichiers sources
- `argumentation_analysis/services/semantic_index_service.py`
- `argumentation_analysis/nlp/embedding_utils.py`, `pipelines/embedding_pipeline.py`
- `argumentation_analysis/services/fact_verification_service.py`
- `argumentation_analysis/orchestration/fact_checking_orchestrator.py`
- `argumentation_analysis/workflows/fact_check_pipeline.py`
- `argumentation_analysis/services/mcp_server/main.py`, `services/mcp_server/tools/`
- `argumentation_analysis/orchestration/unified_pipeline.py`
