#!/usr/bin/env python3
"""Generate static OpenAPI spec from the FastAPI application."""
import json
import sys
import os
import unittest.mock as m

# Prevent JVM startup — mock all jpype submodules
_jpype_mock = m.MagicMock()
_jpype_mock.isJVMStarted = m.MagicMock(return_value=False)
sys.modules["jpype"] = _jpype_mock
sys.modules["jpype._core"] = m.MagicMock()
sys.modules["jpype.imports"] = m.MagicMock()
sys.modules["jpype.types"] = m.MagicMock()
os.environ["PYTEST_CURRENT_TEST"] = "gen_openapi"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.factory import create_app
from api.endpoints import router as api_router, framework_router, informal_router

app = create_app(
    title="Argumentation Analysis API",
    description=(
        "API d'analyse argumentative multi-agents avec intégration Java/Tweety, "
        "composants Lego (CapabilityRegistry), et pipelines unifiés. "
        "Supporte l'analyse Dung, Toulmin, ASPIC+, détection de sophismes, "
        "et orchestration de débats."
    ),
    version="2.1.0",
)
app.include_router(api_router, prefix="/api")
app.include_router(framework_router)
app.include_router(informal_router)

# Try to include JTMS endpoints
try:
    from argumentation_analysis.api.jtms_endpoints import jtms_router
    app.include_router(jtms_router)
    print("JTMS endpoints included")
except Exception as e:
    print(f"JTMS endpoints skipped: {e}")

spec = app.openapi()

# Add server info
spec["servers"] = [
    {"url": "http://localhost:8000", "description": "Local development"},
]

# Add integration capabilities info to the spec
spec["info"]["x-integration-status"] = {
    "registered_capabilities": 25,
    "integrated_projects": 10,
    "architecture": "Lego (CapabilityRegistry + Semantic Kernel plugins)",
}

output_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "docs", "api", "openapi.json",
)
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)

print(f"OpenAPI spec written to {output_path}")
print(f"Paths: {len(spec.get('paths', {}))}")
print(f"Schemas: {len(spec.get('components', {}).get('schemas', {}))}")
