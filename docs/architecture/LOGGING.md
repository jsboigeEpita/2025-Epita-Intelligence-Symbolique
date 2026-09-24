# Structured Logging

## Overview

Orchestration modules use structured logging with correlation IDs to enable per-document tracing across all pipeline phases. This allows filtering logs for a specific analysis run and tracking request flow through extract → fallacy → FOL → synthesis.

## Architecture

```
argumentation_analysis/orchestration/structured_logging.py  ← core module
  ├── JsonFormatter    — JSON lines to stderr
  ├── HumanFormatter   — human-readable with [correlation_id] prefix
  ├── PhaseLogger      — logging.LoggerAdapter with correlation_id + phase_name
  ├── get_phase_logger() — factory; configures nothing
  └── formatter_from_env() — reads LOG_FORMAT; called by the entry points
```

The module configures no handler. The process's logging belongs to the entry
point, which installs the formatter `formatter_from_env()` returns:

| Entry point | Where |
|-------------|-------|
| `python -m argumentation_analysis.run_orchestration` | `setup_logging()`, called by `main()` |
| `python scripts/compare_orchestration_modes.py` | `_configure_logging()`, called by `main()` |

Both configure with `basicConfig(..., force=True)`. Library modules still call
`basicConfig` at import (#2346); without `force`, the first one imported wins
and the entry point's call does nothing. Some library modules also attach
handlers to their own loggers at import, so their lines can print a second
time, in their own format (#2346).

## Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `LOG_FORMAT` | `json`, anything else | human-readable | `json` → one JSON object per line on stderr, with every field passed in `extra`. Otherwise `%(asctime)s [%(levelname)s] [%(name)s] %(message)s`, prefixed with `[<first 8 chars of correlation_id>] [<phase_name>]` when the record carries them. Read when the entry point configures logging. |

## Usage

### In orchestration code

```python
from argumentation_analysis.orchestration.structured_logging import get_phase_logger

# One logger per module, correlation_id set once
slog = get_phase_logger("workflow_executor", correlation_id="run-abc-123")

# Per-phase logging
slog.info("Phase completed", extra={"phase_name": "extract", "duration": 1.2})

# Child logger for a specific phase
phase_log = slog.with_phase("fol_validate")
phase_log.info("Validation result")  # includes correlation_id + phase_name
```

### In WorkflowExecutor

The executor automatically generates or accepts a `correlation_id`:
1. If `ctx["correlation_id"]` is set → uses it
2. If `state.run_id` exists → uses it
3. Otherwise → generates UUID4

The correlation_id is stored in `ctx` and propagates to all phase executions.

## JSON Output Example

```json
{"timestamp": "2026-05-14T10:30:00", "level": "INFO", "logger": "orchestration.workflow_executor", "message": "Starting phase", "correlation_id": "abc12345-6789", "phase_name": "extract", "capability": "fact_extraction"}
```

## Recommended jq Queries

The CLI prints its results on stdout and its logs on stderr, so the queries
read stderr alone. Other lines reach stderr too (`print` diagnostics, the
library handlers above): `fromjson?` skips them.

```bash
export LOG_FORMAT=json
RUN="python -m argumentation_analysis.run_orchestration --file texte.txt"

# Filter by correlation ID
$RUN 2>&1 >/dev/null | jq -R 'fromjson? | select(.correlation_id == "abc12345")'

# Phase starts, in order
$RUN 2>&1 >/dev/null | jq -R 'fromjson? | select(.message == "Starting phase") | {timestamp, phase_name, capability}'

# Run summary: completed and degraded phases
$RUN 2>&1 >/dev/null | jq -R 'fromjson? | select(.phases_completed != null) | {workflow, phases_completed, phases_total, phases_degraded}'
```

The executor's structured lines are three: `Executing workflow ...` (`workflow`,
`phases_total`), `Starting phase` (`phase_name`, `capability`) and
`Workflow '...' finished: ...` (`workflow`, `phases_completed`, `phases_total`,
`phases_degraded`, `structured_arg_degraded`). All carry `correlation_id`.
Phase failures are logged by the `WorkflowDSL` logger, without these fields.

## Testing

```bash
pytest tests/unit/argumentation_analysis/orchestration/test_structured_logging.py        tests/unit/argumentation_analysis/orchestration/test_log_format_reader_2346.py
```

`test_structured_logging.py` covers PhaseLogger injection, JsonFormatter output,
HumanFormatter prefix, `formatter_from_env`, and correlation propagation.
`test_log_format_reader_2346.py` runs each entry point's real `__main__` path in a
subprocess, then checks the executor's line in both formats, so every
import-time configuration of the real import graph has happened first.
