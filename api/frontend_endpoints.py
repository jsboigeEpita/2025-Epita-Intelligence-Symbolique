"""Routes the React frontend calls that no other router of ``api.main`` serves (#2526).

The frontend (``services/web_api/interface-web-argumentative/src``) was written
against the Flask app of ``services/web_api_from_libs``. That app was archived in
``df031b34`` (#34), ``api.main:app`` did not take its routes over, and each call
below answered 404. Each route here is the archived handler, on the service that
still computes it (``argumentation_analysis/services/web_api/services``) and with
its request and response models.

Routes:
    POST /api/validate          — ``ValidationService.validate_argument``
    POST /api/logic/belief-set  — ``LogicService.text_to_belief_set``

The services are built once, on first use, as the MCP server builds them
(``argumentation_analysis/services/mcp_server/main.py``, ``AppServices``).
"""

import logging

from fastapi import APIRouter, Depends

from argumentation_analysis.services.web_api.models.request_models import (
    LogicBeliefSetRequest,
    ValidationRequest,
)
from argumentation_analysis.services.web_api.models.response_models import (
    LogicBeliefSetResponse,
    ValidationResponse,
)

logger = logging.getLogger(__name__)

frontend_router = APIRouter(tags=["Frontend"])

_logic_service = None
_validation_service = None


def get_logic_service():
    """The ``LogicService``, with its own LLM service, built on first use."""
    global _logic_service
    if _logic_service is None:
        from argumentation_analysis.core.llm_service import create_llm_service
        from argumentation_analysis.services.web_api.services.logic_service import (
            LogicService,
        )

        _logic_service = LogicService(
            llm_service=create_llm_service(service_id="logic_service")
        )
    return _logic_service


def get_validation_service(logic_service=Depends(get_logic_service)):
    """The ``ValidationService``, on the ``LogicService`` above."""
    global _validation_service
    if _validation_service is None:
        from argumentation_analysis.services.web_api.services.validation_service import (
            ValidationService,
        )

        _validation_service = ValidationService(logic_service)
    return _validation_service


@frontend_router.post("/validate", response_model=ValidationResponse)
async def validate_argument(
    request: ValidationRequest, service=Depends(get_validation_service)
):
    """Validity and soundness scores of an argument, from its premises and conclusion.

    The scores are heuristic: ``result.logical_structure.method`` says so.
    """
    return await service.validate_argument(request)


@frontend_router.post("/logic/belief-set", response_model=LogicBeliefSetResponse)
async def logic_belief_set(
    request: LogicBeliefSetRequest, service=Depends(get_logic_service)
):
    """A text converted into a belief set of ``logic_type``, by the logic agent.

    A malformed request is a 422 before the service runs. A failed conversion is
    a 500: the service wraps every error, its own included, in ``ValueError``
    with the traceback, which is not the caller's input and not for the client.
    """
    return await service.text_to_belief_set(request)
