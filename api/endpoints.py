from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import List, Dict, Optional

from .models import (
    AnalysisRequest, AnalysisResponse, Fallacy, StatusResponse, ExampleResponse, Example,
    InformalAnalysisRequest, InformalAnalysisResponse
)
from .dependencies import (
    get_analysis_service, AnalysisService, get_dung_analysis_service,
    get_informal_analysis_service, InformalAnalysisService
)
from .models import FrameworkAnalysisRequest, FrameworkAnalysisResponse
from .services import DungAnalysisService
import asyncio
import uuid
from datetime import datetime

# --- Pydantic Models for /endpoints route ---
class EndpointDetail(BaseModel):
    path: str
    methods: List[str]
    description: Optional[str] = None

class EndpointsListResponse(BaseModel):
    endpoints: List[EndpointDetail]

# --- Routeur pour l'analyse de sophismes informels (Facade) ---
informal_router = APIRouter(prefix="/api/v1/informal", tags=["Informal Fallacy Analysis"])

@informal_router.post("/analyze", response_model=InformalAnalysisResponse)
async def analyze_informal_fallacy(
    request: InformalAnalysisRequest,
    analysis_service: InformalAnalysisService = Depends(get_informal_analysis_service)
):
    """
    Analyzes a text for informal fallacies using the main facade.

    - **text**: The text to analyze.
    - **strategy**: The analysis strategy ('parallel', 'cluster', 'auto').

    Returns a structured analysis result based on the chosen strategy.
    """
    result = await analysis_service.analyze(request.text, request.strategy)
    return result

router = APIRouter()

# --- Nouveau routeur pour l'argumentation de Dung ---
framework_router = APIRouter(prefix="/api/v1/framework", tags=["Dung's Argumentation Framework"])

@framework_router.post("/analyze", response_model=FrameworkAnalysisResponse)
async def analyze_framework_endpoint(
    request: FrameworkAnalysisRequest,
    dung_service: DungAnalysisService = Depends(get_dung_analysis_service)
):
    """
    Analyse un framework d'argumentation de Dung.

    - **arguments**: Une liste de chaînes représentant les noms des arguments.
    - **attacks**: Une liste de paires (listes) représentant les attaques,
      ex: `[["a", "b"]]` signifie que `a` attaque `b`.

    Retourne une analyse sémantique complète, le statut de chaque argument, et les
    propriétés structurelles du graphe.
    """
    # L'appel à la méthode `analyze_framework` est bloquant (I/O, calcul),
    # il doit donc être exécuté dans un thread séparé pour ne pas bloquer
    # la boucle d'événements de FastAPI.
    analysis_result = await asyncio.to_thread(
        dung_service.analyze_framework,
        request.arguments,
        [tuple(attack) for attack in request.attacks], # Convertit les listes en tuples
        request.options.dict() if request.options else {}
    )
    
    # Pas besoin de convertir le résultat car le service retourne déjà un dictionnaire
    # qui correspond à la structure du modèle Pydantic FrameworkAnalysisResponse.
    return {"analysis": analysis_result}

# --- Ancien routeur (peut être conservé, modifié ou supprimé selon la stratégie) ---
import time
import logging

logger = logging.getLogger(__name__)

def _perform_tweety_analysis(text: str, project_context) -> Dict:
    """Effectue l'analyse argumentative avec TweetyProject."""
    if not project_context or not project_context.jvm_initialized:
        raise ValueError("Le contexte du projet ou la JVM n'est pas initialisé.")
    if 'AspicParser' not in project_context.tweety_classes:
        raise ValueError("La classe 'AspicParser' n'est pas chargée.")

    parser = project_context.tweety_classes['AspicParser']
    kb = parser.parseBeliefBase(text)
    arguments = kb.getArguments()
    arguments_list = [str(arg) for arg in arguments]

    # Logique de séparation simple pour correspondre au frontend
    premises = []
    conclusion = ""
    if arguments_list:
        premises = arguments_list[:-1]
        conclusion = arguments_list[-1]

    return {
        "argument_structure": {
            "premises": premises,
            "conclusion": conclusion
        },
        "summary": f"{len(premises)} prémisses et 1 conclusion extraites.",
        "suggestions": ["Analyser chaque argument individuellement."],
        "fallacies": [],
        "components_used": ["TweetyArgumentReconstructor_centralized_v2"],
    }

def _build_response_payload(analysis_result: Dict) -> Dict:
    """Construit le payload de la réponse finale."""
    fallacies = [Fallacy(**f_data) for f_data in analysis_result.get('fallacies', [])]
    return {
        "overall_quality": analysis_result.get('overall_quality', 0.0),
        "fallacy_count": len(fallacies),
        "fallacies": fallacies,
        "argument_structure": analysis_result.get('argument_structure'),
        "suggestions": analysis_result.get('suggestions', []),
        "summary": analysis_result.get('summary', "L'analyse a été complétée."),
        "metadata": {
            "duration": analysis_result.get('duration', 0.0),
            "service_status": "active",
            "components_used": analysis_result.get('components_used', [])
        }
    }

@router.post("/analyze")
async def analyze_text_endpoint(analysis_req: AnalysisRequest, fastapi_req: Request):
    """
    Analyse un texte donné pour en extraire la structure argumentative.
    """
    analysis_id = str(uuid.uuid4())[:8]
    logger.info(f"[{analysis_id}] Requête d'analyse reçue: '{analysis_req.text[:80]}...'")
    
    start_time = time.time()
    project_context = fastapi_req.app.state.project_context
    
    try:
        service_result = _perform_tweety_analysis(analysis_req.text, project_context)
        logger.info(f"[{analysis_id}] Analyse réussie.")
    except Exception as e:
        logger.error(f"[{analysis_id}] Erreur lors de l'analyse: {e}", exc_info=True)
        service_result = {"summary": f"Erreur du service d'analyse: {e}"}

    duration = time.time() - start_time
    service_result.setdefault("duration", duration)
    
    results_payload = _build_response_payload(service_result)

    return {
        "analysis_id": analysis_id,
        "status": "success",
        "results": results_payload
    }

@router.get("/status", response_model=StatusResponse)
async def status_endpoint(
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Checks the status of the analysis service.
    Returns the operational status and service details.
    """
    service_available = analysis_service.is_available() # Correction: removed await
    
    if service_available:
        # Mimic structure from interface_web/app.py status route
        # We'll assume analysis_service.get_status_details() provides necessary details
        # This method would need to be implemented in AnalysisService
        status_details = analysis_service.get_status_details() # Correction: removed await
        return StatusResponse(
            status="operational",
            service_status=status_details
        )
    else:
        return StatusResponse(
            status="degraded",
            service_status={"details": "Analysis service is not available."}
        )

@router.get("/examples", response_model=ExampleResponse)
async def get_examples_endpoint():
    """
    Route pour obtenir des exemples de textes d'analyse.
    Retourne une liste d'exemples prédéfinis pour faciliter les tests.
    """
    examples_data = [
        {
            'title': 'Logique Propositionnelle',
            'text': 'Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.',
            'type': 'propositional'
        },
        {
            'title': 'Logique Modale',
            'text': 'Il est nécessaire que tous les hommes soient mortels. Socrate est un homme. Il est donc nécessaire que Socrate soit mortel.',
            'type': 'modal'
        },
        {
            'title': 'Argumentation Complexe',
            'text': 'L\'intelligence artificielle représente à la fois une opportunité et un défi. D\'un côté, elle peut révolutionner la médecine et l\'éducation. De l\'autre, elle pose des questions éthiques fondamentales sur l\'emploi et la vie privée.',
            'type': 'comprehensive'
        },
        {
            'title': 'Paradoxe Logique',
            'text': 'Cette phrase est fausse. Si elle est vraie, alors elle est fausse. Si elle est fausse, alors elle est vraie.',
            'type': 'paradox'
        }
    ]
    examples = [Example(**ex) for ex in examples_data]
    return ExampleResponse(examples=examples)

@router.get("/health", response_model=StatusResponse)
async def health_check_endpoint():
    """
    Simple health check endpoint.
    Returns operational status.
    """
    # Reusing StatusResponse for consistency, but could be a simpler model
    return StatusResponse(
        status="operational",
        service_status={"details": "API is healthy and running."}
    )

@router.get("/endpoints", response_model=EndpointsListResponse)
async def list_endpoints_endpoint(request_fastapi: Request):
    """
    Lists available API endpoints.
    Dynamically introspects routes from the FastAPI application.
    """
    url_list = []
    for route in request_fastapi.app.routes:
        if hasattr(route, "path") and route.path not in ['/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc']: # Exclude documentation routes
            methods = []
            if hasattr(route, "methods"):
                methods = sorted(list(route.methods))
            
            description = None
            if hasattr(route, "summary") and route.summary:
                description = route.summary
            elif hasattr(route, "name") and route.name:
                description = route.name.replace("_", " ").title()


            url_list.append(EndpointDetail(
                path=route.path,
                methods=methods,
                description=description
            ))
    return EndpointsListResponse(endpoints=url_list)