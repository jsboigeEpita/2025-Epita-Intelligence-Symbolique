# Structured Logging

## Overview

Orchestration modules use structured logging with correlation IDs to enable per-document tracing across all pipeline phases. This allows filtering logs for a specific analysis run and tracking request flow through extract → fallacy → FOL → synthesis.

## Architecture

```
argumentation_analysis/orchestration/structured_logging.py  ← core module
  ├── JsonFormatter    — JSON lines to stderr
  ├── HumanFormatter   — human-readable with [correlation_id] prefix
  ├── PhaseLogger      — logging.LoggerAdapter with correlation_id + phase_name
  └── get_phase_logger() — factory, respects LOG_FORMAT env var
```

## Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `LOG_FORMAT` | `json`, anything else | human-readable | `json` → JSON lines to stderr for production |

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

```bash
# Filter by correlation ID
python run_analysis.py 2>&1 | jq 'select(.correlation_id == "abc12345")'

# All phase transitions
python run_analysis.py 2>&1 | jq 'select(.phase_name) | {timestamp, phase_name, message}'

# Failed phases only
python run_analysis.py 2>&1 | jq 'select(.level == "ERROR" and .phase_name)'

# Duration summary per phase
python run_analysis.py 2>&1 | jq 'select(.duration) | {phase_name, duration}'
```

## Testing

```bash
pytest tests/unit/argumentation_analysis/orchestration/test_structured_logging.py
```

12 tests covering: PhaseLogger injection, JsonFormatter output, HumanFormatter prefix, LOG_FORMAT env control, correlation propagation across phases.
