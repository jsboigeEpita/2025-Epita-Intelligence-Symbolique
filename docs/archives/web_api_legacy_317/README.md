# Archived: interface-simple (Flask Legacy Web App)

**Archived:** 2026-04-09 (Epic #317, PR #322)
**Original location:** `services/web_api/interface-simple/`
**Superseded by:** `interface_web/app.py` (Starlette)

## Contents

- `app.py` — Standalone Flask web app with Bootstrap UI
- `templates/index.html` — HTML template
- `test_api_validation.py`, `test_fallacy_detection.py`, `test_integration.py`, `test_webapp.py` — Tests
- `README_INTEGRATION.md` — Integration documentation

## Reason for Archival

The Flask-based simple interface was superseded by the Starlette web app at `interface_web/app.py` which:
- Uses async/await natively
- Integrates with `ServiceManager` from `argumentation_analysis/orchestration/`
- Serves the React frontend from `services/web_api/interface-web-argumentative/build/`
- Has proper WebSocket support

## No External Dependencies

No active code imports from `interface-simple/`. All references were to the Starlette app.
