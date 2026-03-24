# Archived: 2026-03-24 — Flask app superseded by FastAPI (api/main.py) (#217)
# Full archive: docs/archives/services_web_api_flask/app.py
# Business logic services (services/) and models (models/) are preserved in-place.
# MCP server and other consumers continue to import from services/ and models/.
"""
DEPRECATED Flask application.

The Flask REST API has been superseded by the FastAPI application at api/main.py
which provides 25+ routes, WebSocket streaming, agent orchestration, and the
full CapabilityRegistry + WorkflowDSL integration.

To start the modern API:
    uvicorn api.main:app --reload --port 8000

The business logic services (AnalysisService, ValidationService, FallacyService,
FrameworkService, LogicService) remain available at their original import paths
under argumentation_analysis.services.web_api.services.* and are used by the
MCP server.
"""
import warnings

warnings.warn(
    "argumentation_analysis.services.web_api.app is deprecated. "
    "Use the FastAPI app at api.main instead: uvicorn api.main:app --port 8000",
    DeprecationWarning,
    stacklevel=2,
)

# Minimal shim: create_app returns a stub that raises on use
def create_app(*args, **kwargs):
    """Deprecated. Use FastAPI app at api.main instead."""
    raise NotImplementedError(
        "The Flask web_api app has been archived. "
        "Use the FastAPI app: uvicorn api.main:app --port 8000. "
        "Business logic services are still available at "
        "argumentation_analysis.services.web_api.services.*"
    )


# Legacy ASGI wrapper stub
app = None
asgi_app = None
