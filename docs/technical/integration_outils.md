# Guide d'Intégration des Outils Rhétorique

> ⚠️ **Note de véracité (2026-06-30).** Les versions précédentes de ce guide décrivaient une
> façade `RhetoricalAnalysisSystem` (`system.configure_tool(...)`, `system.create_pipeline([...])`,
> `pipeline.analyze(...)`) ainsi qu'une dépendance `mermaid` et un paquet `argumentation-analysis`
> installable par pip. **Aucun de ces éléments n'existe dans le code** (vérifié : pas de classe
> `RhetoricalAnalysisSystem`, pas de paquet publié, pas de dépendance `mermaid`). Le vrai système
> suit l'**architecture Lego** (`CapabilityRegistry` + `UnifiedPipeline` + `WorkflowDSL` +
> `AgentFactory`) documentée dans `CLAUDE.md` et `docs/architecture/INTEGRATION_STRATEGY.md`.
> Les exemples ci-dessous sont ancrés sur les **vrais** points d'entrée du dépôt.

## Points d'entrée réels

| Usage | Point d'entrée | Statut |
|---|---|---|
| API REST (recommandé) | `api/main.py` (FastAPI, `uvicorn api.main:app`) | réel |
| CLI multi-modes | `argumentation_analysis/run_orchestration.py` (`--mode pipeline\|conversational`, `--workflow light\|standard\|full`) | réel |
| Appel programmatique | `argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis` (async) | réel |

## Exemple programmatique (`run_unified_analysis`)

```python
import asyncio
from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

async def main():
    result = await run_unified_analysis(
        text="Argumentation à analyser.",
        workflow_name="standard",   # "light" | "standard" | "full"
    )
    print(result)   # Dict[str, Any]

asyncio.run(main())
```

`run_unified_analysis` crée un `CapabilityRegistry` (via `setup_registry()`) si aucun n'est fourni, exécute un workflow pré-construit, et retourne un `Dict[str, Any]`. Voir la signature complète dans `argumentation_analysis/orchestration/unified_pipeline.py`.

## Installation

Ce dépôt n'est **pas** un paquet pip publié. C'est un projet local (Python 3.10+) :
1. Cloner le dépôt.
2. Activer un environnement Conda (`projet-is-roo-new` ou `projet-is`) — voir `CLAUDE.md`.
3. Copier `.env.example` en `.env` et renseigner les clés API.

## Déploiement (FastAPI)

L'application REST réelle est `api/main.py` :

```bash
uvicorn api.main:app --reload --port 8000
```

```dockerfile
FROM python:3.10
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Pour les routes disponibles, voir `api/main.py` (7 routeurs, 25+ routes).
