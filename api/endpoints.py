from fastapi import APIRouter, Depends
from .models import AnalysisRequest, AnalysisResponse, Fallacy, StatusResponse, ExampleResponse, Example
from .dependencies import get_analysis_service, AnalysisService # Import AnalysisService for type hinting
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text_endpoint(
    request: AnalysisRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Analyzes a given text for logical fallacies.
    Utilizes the AnalysisService injected via FastAPI's dependency system.
    Returns the analysis result.
    """
    analysis_id = str(uuid.uuid4())[:8]
    # Note: start_time could be used to calculate endpoint processing time if needed,
    # but service_result usually provides its own processing duration.
    # start_time = datetime.now()

    # Call the analysis service
    # Assuming analysis_service.analyze_text is an async method
    # and returns a dict: {'fallacies': [], 'duration': float, 'components_used': [], 'summary': str}
    service_result = await analysis_service.analyze_text(request.text) # Correction: analyze -> analyze_text

    # Extract and map fallacies
    fallacies_data = service_result.get('fallacies', [])
    fallacies = [Fallacy(**f_data) for f_data in fallacies_data]

    status = "success"  # Assuming success, error handling can be added

    # Construct metadata, inspired by interface_web/app.py
    metadata = {
        "duration_seconds": service_result.get('duration', 0.0),  # Duration from the service
        "service_status": "active",  # Simplified status
        "components_used": service_result.get('components_used', [])  # Components from the service
    }

    # Get summary from the service
    summary = service_result.get('summary', "L'analyse a été complétée.")

    return AnalysisResponse(
        analysis_id=analysis_id,
        status=status,
        fallacies=fallacies,
        metadata=metadata,
        summary=summary
    )

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