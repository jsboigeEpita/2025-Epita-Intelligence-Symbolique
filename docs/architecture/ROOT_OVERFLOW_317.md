# Root-level overflow cleaned up by Epic #317

Moved verbatim from the root `CLAUDE.md` (claudish#874: the root file is re-read by every request of this workspace; its detail is read here, on demand). The root file keeps the rule and a pointer to this page.

Root-level directories that were cleaned up during Epic #317 consolidation:

| Root directory | Overlaps with | Status |
|---|---|---|
| `api/` | `argumentation_analysis/api/` | **KEPT** — root has general FastAPI endpoints, inside has JTMS-specific |
| ~~`core/`~~ | ~~`argumentation_analysis/core/`~~ | **DELETED** (PR #154) |
| ~~`demos/`~~ | ~~`argumentation_analysis/demos/`~~ | **MOVED** → `examples/03_demos_overflow/` |
| ~~`services/`~~ | ~~`argumentation_analysis/services/`~~ | **CONSOLIDATED** (#322) — React frontend kept (load-bearing `STATIC_FILES_DIR`); `interface-simple/` archived; management scripts kept |
| ~~`plugins/`~~ | ~~`argumentation_analysis/plugins/`~~ | **CONSOLIDATED** (#321) — orphan SK prompts archived to `docs/archives/plugins_overflow/` |
| ~~`src/`~~ | ~~`argumentation_analysis/agents/`~~ | **CONSOLIDATED** (#321) — `fallacy_families.yaml` moved to consuming plugin; empty dir removed |
| ~~`reports/`~~ | — | **ARCHIVED** (#323) → `docs/archives/reports_legacy_317/` (28 files, June 2025) |
| ~~`validation/`~~ | — | **ARCHIVED** (#323) → `docs/archives/validation_legacy_317/` (3 files) |
| ~~`data/`~~ | — | **RELOCATED** (#323) → `argumentation_analysis/data/datasets/legacy_fixtures/` (4 JSON files) |
| `project_core/` | `argumentation_analysis/core/` | **KEPT** — infrastructure utilities (NOT business logic) |
