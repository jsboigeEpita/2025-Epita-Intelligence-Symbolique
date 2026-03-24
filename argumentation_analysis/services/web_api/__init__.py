"""
Package web_api — business logic services and models.

NOTE (2026-03-24, #217): The Flask app layer (app.py, routes/, start_api.py,
asgi.py) has been archived to docs/archives/services_web_api_flask/.
The modern REST API is at api/main.py (FastAPI, 25+ routes, WebSocket).

The business logic services (services/*.py) and data models (models/*.py)
remain here and are actively used by:
  - argumentation_analysis.services.mcp_server (MCP tool exposure)
  - argumentation_analysis.core.argumentation_analyzer
  - Various integration tests
"""
