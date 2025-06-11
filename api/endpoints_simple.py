#!/usr/bin/env python3
"""
Endpoints FastAPI Simplifiés - GPT-4o-mini Authentique
======================================================
"""

from fastapi import APIRouter, Depends, HTTPException
from .models import AnalysisRequest, AnalysisResponse, Fallacy, StatusResponse, ExampleResponse, Example
from .dependencies_simple import get_simple_analysis_service, SimpleAnalysisService
import uuid
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text_endpoint(
    request: AnalysisRequest,
    analysis_service: SimpleAnalysisService = Depends(get_simple_analysis_service)
):
    """
    Analyse authentique du texte via GPT-4o-mini
    """
    analysis_id = str(uuid.uuid4())[:8]
    
    try:
        # Appel au service d'analyse authentique
        service_result = await analysis_service.analyze_text(request.text)
        
        # Conversion des données pour le modèle de réponse
        fallacies_data = service_result.get('fallacies', [])
        fallacies = [Fallacy(**f_data) for f_data in fallacies_data]
        
        # Métadonnées
        metadata = {
            "duration_seconds": service_result.get('duration', 0.0),
            "service_status": "active" if service_result.get('authentic_gpt4o_used') else "fallback",
            "components_used": service_result.get('components_used', []),
            "gpt_model": service_result.get('gpt_model_used', 'N/A'),
            "tokens_used": service_result.get('tokens_used', 0),
            "authentic_analysis": service_result.get('authentic_gpt4o_used', False)
        }
        
        summary = service_result.get('summary', "Analyse terminée")
        
        return AnalysisResponse(
            analysis_id=analysis_id,
            status="success",
            fallacies=fallacies,
            metadata=metadata,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")

@router.get("/status", response_model=StatusResponse)
async def status_endpoint(
    analysis_service: SimpleAnalysisService = Depends(get_simple_analysis_service)
):
    """
    Statut du service d'analyse
    """
    try:
        service_available = analysis_service.is_available()
        status_details = analysis_service.get_status_details()
        
        if service_available:
            return StatusResponse(
                status="operational",
                service_status=status_details
            )
        else:
            return StatusResponse(
                status="degraded",
                service_status={**status_details, "details": "GPT-4o-mini non disponible, mode fallback"}
            )
            
    except Exception as e:
        logger.error(f"Erreur de statut: {e}")
        return StatusResponse(
            status="error",
            service_status={"error": str(e)}
        )

@router.get("/examples", response_model=ExampleResponse)
async def get_examples_endpoint():
    """
    Exemples de textes pour l'analyse
    """
    examples_data = [
        {
            'title': 'Logique Propositionnelle Simple',
            'text': 'Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.',
            'type': 'propositional'
        },
        {
            'title': 'Généralisation Hâtive',
            'text': 'Tous les corbeaux que j\'ai vus sont noirs, donc tous les corbeaux sont noirs.',
            'type': 'fallacy'
        },
        {
            'title': 'Ad Hominem Potentiel',
            'text': 'Cette théorie climatique est fausse car son auteur a été condamné pour fraude fiscale.',
            'type': 'fallacy'
        },
        {
            'title': 'Argumentation Complexe',
            'text': 'L\'intelligence artificielle représente à la fois une opportunité et un défi. Elle peut révolutionner la médecine mais pose des questions éthiques sur l\'emploi.',
            'type': 'comprehensive'
        },
        {
            'title': 'Logique Modale',
            'text': 'Il est nécessaire que tous les hommes soient mortels. Socrate est un homme. Il est donc nécessaire que Socrate soit mortel.',
            'type': 'modal'
        }
    ]
    
    examples = [Example(**ex) for ex in examples_data]
    return ExampleResponse(examples=examples)

@router.get("/health")
async def api_health():
    """Health check spécifique API"""
    return {
        "status": "healthy",
        "message": "API endpoints fonctionnels",
        "version": "1.0.0",
        "endpoints": {
            "analyze": True,
            "status": True,
            "examples": True,
            "health": True
        }
    }