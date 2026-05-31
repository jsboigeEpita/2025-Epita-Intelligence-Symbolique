# Audit C-04: Section II-A/B Architecture + Sources/Données (8 sujets)

**Issue**: #782 (C-04) | **Epic**: #744 | **Date audit**: 2026-05-31

## Préambule — Table de correspondance

| Code sujet | Statut | Lien Epic A si traité |
|------------|--------|-----------------------|
| 2.1.1 Architecture multi-agents | 🟢 Treated (trunk) | — |
| 2.1.2 Orchestration agents | 🟢 Treated (trunk) | — |
| 2.1.3 Monitoring évaluation | 🟡 Partial | — |
| 2.1.6 Gouvernance | 🟢 Treated | #751 (A-06) |
| 2.2.1 Moteur extraction | 🟢 Treated (trunk) | — |
| 2.2.2 Formats étendus | 🟢 Treated (Tika/Jina) | — |
| 2.2.3 Sécurisation données | 🟢 Treated | — |
| 2.2.4 Gestion corpus | 🟡 Partial | — |

## Résultats détaillés

### 🟢 TREATED (6)

**2.1.1 Architecture multi-agents** — Trunk infrastructure. Code: `agents/core/abc/agent_bases.py` (BaseAgent hierarchy), `agents/factory.py` (AgentFactory), `core/capability_registry.py` (CapabilityRegistry + ServiceDiscovery), `core/communication/` (17 files — middleware, hierarchical/collaboration/pub_sub channels). Fully realized.

**2.1.2 Orchestration agents** — Trunk infrastructure (~80 files in `orchestration/`). Code: `workflow_dsl.py` (declarative DAG), `unified_pipeline.py`, `hierarchical/` (strategic/tactical/operational), `conversation_orchestrator.py`, `group_chat.py`. Over-delivered relative to spec.

**2.1.6 Gouvernance** — Student project (arthur.guelennoc, score 85%). Code: `agents/core/governance/` + `plugins/governance_plugin.py` (6 SK functions), 7 voting methods in `social_choice.py`. Cross-ref → Epic A #751 (A-06).

**2.2.1 Moteur extraction** — Trunk infrastructure. Code: `agents/core/extract/extract_agent.py` (ExtractAgent with semantic validation, fuzzy marker repair), `services/extract_service.py`, `ui/extract_editor/extract_marker_editor.py`.

**2.2.2 Formats étendus** — Via Tika + Jina (not native parsers). Code: `services/fetch_service.py` (3 strategies: direct text, Jina Reader for HTML, Apache Tika for PDF/DOCX/binary). Minor gap: no OCR for image-only documents.

**2.2.3 Sécurisation données** — Exceeds scope. Code: `core/utils/crypto_utils.py` (Fernet + AES-256-GCM), `core/io_manager.py` (in-memory decryption), `services/crypto_service.py`, full privacy/governance layer (evaluation/sanitize_state.py, opaque_id, bundle scrub pipeline). Minor gap: no access-control/audit (irrelevant for single-tenant).

### 🟡 PARTIAL (2)

**2.1.3 Monitoring évaluation** — Evaluation fully covered (`evaluation/` — 19 modules including benchmark_runner, LLM judge, capability_eval). Tracing/logging present (`structured_logging.py`, `trace_analyzer.py`, `metrics_collector.py`). **Gap**: No real-time/runtime monitoring (no Prometheus/OpenTelemetry), no alerting, no operational dashboard. The linked subject 3.1.2 (dashboard monitoring) was never built.

**2.2.4 Gestion corpus** — Batch runner present (`scripts/dataset/run_corpus_batch.py` with resume/checkpoint), semantic search covered by 2.4.1. **Gap**: No corpus versioning, no queryable documentary DB (corpus is a single encrypted gzip blob), no structured metadata management layer.

## Synthèse C-04

- **6/8 🟢 Treated** (fully realized trunk infrastructure + 1 student project)
- **2/8 🟡 Partial** (2.1.3 monitoring, 2.2.4 corpus management)
- **0/8 🔴 Angle mort** — no complete gaps

Only 2.1.6 is a real student project with a dedicated sujet file. The other 7 are professor/trunk infrastructure subjects defined in `docs/projets/developpement_systeme.md`.

## Fichiers sources
- `argumentation_analysis/core/capability_registry.py`, `core/communication/middleware.py`
- `argumentation_analysis/orchestration/workflow_dsl.py`, `orchestration/unified_pipeline.py`
- `argumentation_analysis/evaluation/benchmark_runner.py`
- `argumentation_analysis/plugins/governance_plugin.py`
- `argumentation_analysis/agents/core/extract/extract_agent.py`
- `argumentation_analysis/services/fetch_service.py`
- `argumentation_analysis/core/utils/crypto_utils.py`
- `scripts/dataset/run_corpus_batch.py`
