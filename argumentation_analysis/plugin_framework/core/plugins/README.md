# Plugin Architecture

This directory holds the canonical plugin contract of the `plugin_framework`
subsystem (`interfaces.py`) and the two declarative plugins under `standard/`.

## Key Components

### 1. `BasePlugin` (`interfaces.py`) — the canonical contract

`BasePlugin` is a marker ABC (empty body). A plugin of this framework subclasses
it and is joined to the system **by direct import**: the two production sites are
`agents/tools/analysis/fallacy_family_analyzer.py:20,24` and
`orchestration/fact_checking_orchestrator.py:28,31`, which import
`taxonomy_explorer` and `external_verification` directly.

There is **no discovery mechanism**. The three loaders this package used to carry
(`core/plugin_loader.py`, `core/plugins/plugin_loader.py`,
`agents/agent_loader.py`) were withdrawn (#2099) after a consumer map showed none
of them had a production caller: loader #1 was called only by two fossils of the
same package (`main.py`, non-executable; `run_benchmark.py`, whose only loaded
plugin was the fake one it wrote into the source tree at runtime), loaders #2 and
#3 only by tests. The unit guard
`tests/unit/argumentation_analysis/test_plugin_framework.py::TestDiscoveryMechanismsWithdrawn`
pins the withdrawal (ImportError on each removed module), and
`::TestRealPluginsByDirectImport` pins the surviving path.

### 2. `standard/` — the two declarative plugins

`taxonomy_explorer/` and `external_verification/`, each described by a
`plugin.yaml` (documentary declaration — no code reads it) and imported directly
where used. See `standard/README.md`.

## Withdrawn conventions — do not re-add without a consumer

- **`plugin_manifest.json`** — the JSON manifest format (`manifest_version`,
  `plugin_name`, `version`, `entry_point`, …) had no production reader, and the
  single real manifest (`standard/plugin_manifest.json`) pointed at a `main.py`
  that never existed on disk. Removed with its loaders (#2099). The fixtures
  under `tests/fixtures/plugins/` keep the format **as test data only** — read by
  plain `json` in `tests/integration/triage/test_workflow_execution.py`, not by a
  loader.
- **YAML→JSON conversion** — rejected: no real consumer justifies rewriting the
  `plugin.yaml` declarations. They stay as the documented capability list of each
  plugin.
