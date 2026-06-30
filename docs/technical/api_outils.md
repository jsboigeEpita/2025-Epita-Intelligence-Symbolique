# Référence API — Analyse Rhétorique

> ⚠️ **Note d'exactitude.** Les versions précédentes de cette page décrivaient une
> classe `RhetoricalAnalysisSystem` (`configure_tool` / `create_pipeline` / `analyze`)
> ainsi que des modules `tools/`, `BaseRhetoricalTool`, `RhetoricalResults`,
> `StrategicLayer`, `TacticalLayer`, `OperationalLayer`, `MermaidVisualizer`,
> `LLMValidator`, etc. **Aucun de ces éléments n'existe dans le code.**
> Cette page documente les vrais points d'entrée. Le code source reste la source
> de vérité (`argumentation_analysis/`).

## Hiérarchie d'agents (3 tiers)

```text
Strategic   → Orchestrators (workflows multi-étapes)
Tactical    → Coordinators (interactions entre agents)
Operational → Base agents (Sherlock, Watson, FOL, Modal, PL, détection de sophismes)
```

Source : `argumentation_analysis/agents/core/`, `docs/architecture/`.

## Point d'entrée principal — `run_unified_analysis`

```python
import asyncio
from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

async def main():
    results = await run_unified_analysis(
        text="Texte à analyser",
        workflow_name="standard",   # "light" | "standard" | "full"
    )
    print(results)

asyncio.run(main())
```

Signature vérifiée dans `argumentation_analysis/orchestration/unified_pipeline.py` :

```python
async def run_unified_analysis(
    text: str,
    workflow_name: str = "standard",
    registry: Optional[CapabilityRegistry] = None,
    custom_workflow: Optional[WorkflowDefinition] = None,
    ...
) -> Dict[str, Any]
```

## Architecture Lego — `CapabilityRegistry`

Le registre central câble agents, plugins et services. `UnifiedPipeline.setup_registry()`
enregistre automatiquement tous les composants.

```python
from argumentation_analysis.core.capability_registry import CapabilityRegistry

registry = CapabilityRegistry()
registry.register_agent(name="my_agent", agent_class=MyAgent)
registry.register_plugin(name="my_plugin", plugin_class=MyPlugin)
registry.register_service(name="my_service", service_class=MyService)

# Recherche par capacité (find_*_for_capability)
agent = registry.find_agent_for_capability("...")
```

Source : `argumentation_analysis/core/capability_registry.py`.

## Écrire un nouvel outil / plugin

Le mécanisme d'extension réel est un **plugin Semantic Kernel** (méthode décorée
`@kernel_function`) enregistré dans `CapabilityRegistry`. Il n'existe pas de
classe de base `BaseRhetoricalTool` ni de `tool_registry`.

```python
from semantic_kernel.functions import kernel_function
from argumentation_analysis.core.capability_registry import CapabilityRegistry

class MyToolPlugin:
    @kernel_function(description="Analyse personnalisée")
    def analyze(self, text: str) -> dict:
        return {"score": 0.8, "details": "..."}

registry = CapabilityRegistry()
registry.register_plugin(name="my_tool", plugin_class=MyToolPlugin)
```

Voir aussi les plugins existants : `argumentation_analysis/plugins/`
(`quality_scoring_plugin.py`, `french_fallacy_plugin.py`, `governance_plugin.py`).

## Autres points d'entrée

| Point d'entrée | Localisation | Usage |
|----------------|--------------|-------|
| API REST FastAPI | `api/main.py` | 7 routers, 25+ routes, WebSocket streaming |
| CLI multi-mode | `argumentation_analysis/run_orchestration.py` | `--mode pipeline\|conversational\|legacy` |
| Web UI Starlette | `interface_web/app.py` | Frontend React + API d'analyse |

## Workflows pré-construits

`UnifiedPipeline` expose 3 workflows : `light`, `standard`, `full`
(plus `collaborative`), construits déclarativement via `WorkflowDSL`
(`argumentation_analysis/orchestration/workflow_dsl.py`).
