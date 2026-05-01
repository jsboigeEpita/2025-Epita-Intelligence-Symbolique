# Test Suite

Unit, integration, and functional tests for the argumentation analysis system.

## Running Tests

```bash
# Activate environment first
conda activate projet-is-roo-new

# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Skip slow tests
pytest tests/ -m "not slow" -v

# Single test file / function
pytest tests/unit/argumentation_analysis/test_foo.py -v
pytest tests/unit/argumentation_analysis/test_foo.py::TestClass::test_method -v

# With coverage
pytest --cov=argumentation_analysis tests/ -v

# LLM tests by cost tier
pytest tests/ -m "llm_light" -v          # <30s, ~$0.01-0.05
pytest tests/ -m "llm_integration" -v    # >30s, ~$0.05-0.20
pytest tests/ -m "llm_critical" -v       # E2E, >60s, >$0.20
```

Tests auto-skip when API keys are unavailable (no failures).

## Structure

```text
tests/
├── conftest.py              # Global fixtures (JVM session, env setup)
├── unit/                    # Unit tests (no external services)
│   └── argumentation_analysis/
│       ├── agents/          # Agent tests
│       ├── services/        # Service tests
│       └── orchestration/   # Orchestration tests
├── integration/             # Integration tests (cross-module)
└── functional/              # E2E tests (Playwright, full workflows)
```

## Key Conventions

### Async

`asyncio_mode = auto` in `pyproject.toml` — no need for `@pytest.mark.asyncio`.

### JVM / JPype

Tests requiring the JVM use `@pytest.mark.usefixtures("jvm_session")`. A session-scoped fixture starts the JVM once. Tests that must NOT have a JVM active (e.g., E2E subprocess tests) use `@pytest.mark.no_jvm_session`.

### Windows DLL Load Order

`conftest.py` imports torch/transformers BEFORE jpype to avoid `WinError 182`. Do not reorder.

### Conditional Skips

Some tests skip on Windows when PyTorch's `fbgemm.dll` fails to load, or when `OPENAI_API_KEY` is absent. See `docs/guides/testing/conditional_skips.md` for the full catalog and reactivation steps.

### Test Markers

50+ markers defined in `pyproject.toml` under `[tool.pytest.ini_options]`. Common ones: `slow`, `integration`, `e2e`, `api`, `real_jpype`, `playwright`, `belief_set`, `propositional`.

## Detailed Guides

- **Advanced patterns & module-specific patterns** — `docs/guides/testing/advanced_patterns.md`

- **Integration & functional test best practices** — `docs/guides/testing/best_practices.md`

- **FOL agent tests** — `docs/guides/testing/fol_tests.md`

- **UnifiedConfig tests** — `docs/guides/testing/unified_config_tests.md`

- **Conditional skip catalog** — `docs/guides/testing/conditional_skips.md`
