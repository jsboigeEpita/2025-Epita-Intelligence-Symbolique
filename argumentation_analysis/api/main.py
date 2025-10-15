from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from argumentation_analysis.agents.core.orchestration_service import (
    OrchestrationService,
    BasePlugin,
    PluginDependencyError,
)


# This is a mock plugin for demonstration and testing purposes.
class TestPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "TestPlugin"

    def get_metadata(self):
        return {"description": "A simple test plugin."}

    def execute(self, **kwargs) -> dict:
        """Exécute la logique du plugin."""
        return {"status": "executed", "received_args": kwargs}


# Initialize the OrchestrationService and register the mock plugin
def get_orchestration_service():
    """Cette fonction sera utilisée par FastAPI pour l'injection de dépendances."""
    service = OrchestrationService.get_instance()
    # On s'assure que le plugin de test par défaut est enregistré si l'instance est nouvelle
    if not service.get_plugin("TestPlugin"):
        service.register_plugin(TestPlugin())
    return service


app = FastAPI()


class AnalysisRequest(BaseModel):
    text: str
    plugin_name: str


@app.post("/api/v2/analyze")
async def analyze(
    request: AnalysisRequest,
    service: OrchestrationService = Depends(get_orchestration_service),
):
    """
    Analyzes a given text using a specified plugin.
    """
    try:
        result = service.execute_plugin(
            plugin_name=request.plugin_name, text=request.text
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PluginDependencyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plugin execution failed: {e}")
