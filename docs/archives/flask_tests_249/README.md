# Flask Tests Archive (#249)

These test files were archived because the Flask app was deprecated in favor of FastAPI.

## Archived Files

| Original Location | Reason |
|-------------------|--------|
| `tests/integration/test_argument_analyzer_client.py` | Flask TestClient tests |
| `tests/integration/argumentation_analysis/workers/worker_hardening_cases.py` | Flask hardening tests |
| `tests/integration/argumentation_analysis/test_hardening_cases.py` | Flask integration tests |
| `argumentation_analysis/services/web_api/tests/test_endpoints.py` | Flask endpoint tests — all 25 skipped via the #242 `client` guard since the archive; never collected anyway (`testpaths = tests`). Archived #1783. |
| `argumentation_analysis/services/web_api/tests/test_basic.py` | Vacuous — 11 pure-Python assertions (`assert True`, json/list ops), zero project imports. Archived #1783. |

## Migration

The Flask app has been replaced by FastAPI at `api/main.py`:
- **Old**: `from argumentation_analysis.services.web_api.app import create_app`
- **New**: `from api.main import app`

For tests:
```python
# Old Flask
from flask import Flask
app = create_app()
client = app.test_client()

# New FastAPI
from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)
```

## Related

- Issue #249
- PR #242 (web_api consolidation)
- Issue #217 (208-R)
