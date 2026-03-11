# Test Markers Reference

This document provides a comprehensive guide to all test markers available in this project. Markers help organize and filter tests by category, performance profile, and dependencies.

## Overview

Markers are used with pytest to categorize tests and enable selective test execution:

```bash
# Run only fast tests
pytest tests/ -m fast

# Run integration tests but not slow tests
pytest tests/ -m "integration and not slow"

# Run tests requiring API keys
pytest tests/ -m requires_api
```

## Marker Categories

### Test Scope & Type

| Marker | Description | Usage Count | Example |
|--------|-------------|-------------|---------|
| **unit** | Isolated unit tests | 0 | Not currently used; use implicit unittest discovery instead |
| **integration** | System integration tests | ~57 | `tests/integration/test_authentic_components_integration.py` |
| **functional** | End-to-end functional tests | 0 | Not currently used |
| **e2e** | Complete end-to-end tests | ~30 | `tests/e2e/python/test_fallacy_detector.py` |

### JVM & Java Integration

| Marker | Description | Usage Count | Example |
|--------|-------------|-------------|---------|
| **jpype** | Requires JPype (Python-Java bridge) | ~6 | `tests/integration/test_authentic_components.py` |
| **jvm** | Requires JVM startup | ~4 | `tests/integration/jpype_tweety/test_minimal_jvm_startup.py` |
| **real_jpype** | Real JPype integration (not mocked) | ~21 | `tests/integration/jpype_tweety/test_argumentation_syntax.py` |
| **tweety** | Uses Tweety/JPype (formal logic) | ~1 | `tests/unit/api/test_dung_service.py` |
| **requires_java** | Java runtime required | 0 | Reserved (jpype/jvm preferred) |

### Performance

| Marker | Description | Usage Count | Example |
|--------|-------------|-------------|---------|
| **slow** | Tests taking > 1 second | ~6 | `tests/e2e/python/test_integration_workflows.py` |
| **fast** | Tests taking < 1 second | 0 | Not currently used (implicit default) |

### LLM Testing

| Marker | Description | Usage Count | Example |
|--------|-------------|-------------|---------|
| **llm_light** | Light LLM tests (config/init, <30s, ~$0.01-0.05) | ~8 | `tests/phase2_validation/test_pilot_real_llm_api.py` |
| **llm_integration** | Full LLM integration tests (real calls, >30s, ~$0.05-0.20) | ~32 | `tests/agents/core/logic/test_watson_logic_assistant.py` |
| **llm_critical** | Critical stack tests (E2E, >60s, >$0.20) | ~7 | End-to-end orchestration with real LLM |
| **real_llm** | Authentic LLM calls (not mocked) | ~7 | `tests/integration/test_authentic_components_integration.py` |

### API Keys & Credentials

| Marker | Description | Usage Count | Example |
|--------|-------------|-------------|---------|
| **requires_api** | Requires at least one API key | ~3 | Auto-skip if no API key available |
| **requires_openai** | Requires OPENAI_API_KEY | ~9 | `tests/integration/test_authentic_components_integration.py` |
| **requires_github** | Requires GITHUB_TOKEN | 0 | Reserved for GitHub API integration |
| **requires_openrouter** | Requires OPENROUTER_API_KEY | 0 | Reserved for OpenRouter API integration |

### Browser & UI Testing

| Marker | Description | Usage Count | Example |
|--------|-------------|-------------|---------|
| **playwright** | Uses Playwright for browser automation | ~20 | `tests/e2e/python/test_fallacy_detector.py` |
| **frontend** | Frontend component tests | 0 | Not currently used |
| **backend** | Backend service tests | 0 | Not currently used |

### Mock vs. Real

| Marker | Description | Usage Count | Example |
|--------|-------------|-------------|---------|
| **mock** | Uses mocks/test doubles | 0 | Not actively used (implicit with fixtures) |
| **real** | Uses real services (not mocked) | ~28 | `tests/integration/test_authentic_components.py` |
| **validation** | Validation/verification tests | ~3 | Tests verifying system correctness |

## Marker Behavior & Fixtures

### Auto-Skip Behavior

Tests with API key requirements automatically skip if keys are unavailable:

```python
@pytest.mark.requires_openai
def test_with_openai():
    # Automatically skipped if OPENAI_API_KEY is not set
    pass
```

### JPype & JVM Behavior

- Tests marked `@pytest.mark.jpype` or `@pytest.mark.jvm` require Java and Tweety JAR
- With `--disable-jvm-session` flag (CI mode), these tests are mocked and ~25-40 are skipped
- Tests marked `@pytest.mark.real_jpype` run in subprocess workers for JVM isolation

### Real LLM vs. Mock

- `@pytest.mark.llm_light/integration/critical` indicate real API calls with cost estimates
- Without `force_authentic=True` in `create_llm_service()`, responses are mocked when `PYTEST_CURRENT_TEST` is detected
- `@pytest.mark.real_llm` + `conftest.check_mock_llm_is_forced` sets `MOCK_LLM=False`

## Running Tests by Marker

```bash
# Run only integration tests
pytest tests/ -m integration

# Run all real LLM tests (requires API keys)
pytest tests/ -m "real_llm or llm_light or llm_integration"

# Run fast tests (skip slow)
pytest tests/ -m "not slow"

# Run E2E Playwright tests
pytest tests/ -m "e2e and playwright"

# Skip JVM tests (CI mode)
pytest tests/ --disable-jvm-session -m "not jpype and not jvm"
```

### CI Environment

```bash
pytest tests/ --allow-dotenv --disable-jvm-session --ignore=tests/e2e --ignore=tests/performance -q
```

### Local Development (Full JVM)

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/ --allow-dotenv -v
```

## Marker Definitions (pytest.ini)

The complete list is defined in `pytest.ini` at the repository root. See that file for the authoritative marker registry.
