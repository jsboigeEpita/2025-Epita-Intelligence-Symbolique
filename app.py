"""
Fallacy Detection API using FastAPI

This API provides an endpoint for detecting logical fallacies in text using a
local fallacy detection model.
The API is designed to mimic the structure of OpenAI's API, making it easy to
integrate with other services and applications.

### Endpoints:
- **POST /v1/fallacy-detection**:
    - Analyzes a given text for logical fallacies.
    - The request body should include the `model` to be used for detection, the
    `text` to be analyzed.
    - The response returns a list of detected fallacies (if any), including
    their type, validity of the argument, description, and the specific
    context where the fallacy was found in the input text.

### Request Example:
    POST /v1/fallacy-detection
    {
        "model": "fallacy-detector-v1",
        "text": "If you don't support this policy, you're against progress.",
    }

### Response Example:
    {
        "id": "fallacy-12345",
        "object": "fallacy_detection",
        "created": 1625143931,
        "model": "fallacy-detector-v1",
        "fallacies": [
            {
                "text": "If you don't support this policy, you're against progress.",
                "is_valid": false,
                "fallacy_type": "Straw Man",
                "explanation": "Misrepresenting someone's argument to make it easier to attack."
            }
        ]
    }
"""

import random
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from local_llm.local_llm import LocalLlm
from local_llm.constants import ModelEnum
from local_llm.utils import extract_json_from_string

app = FastAPI()

instances = LocalLlm(list(ModelEnum), max_window_size=2048)


class FallacyDetectionRequest(BaseModel):
    """
    A model to represent the request data for fallacy detection.

    This class defines the input data expected when making a request to the
    `/v1/fallacy-detection` endpoint. It includes the following fields:

    - `model` (str): The name or identifier of the model to be used for fallacy detection.
                      This allows for future model flexibility if multiple models are available.
    - `text` (str): The text to analyze for logical fallacies.

    Attributes:
    - model: Specifies which model should be used for fallacy detection.
    - text: The input text that will be analyzed for logical fallacies.
    """

    model: str
    text: str


@app.post("/v1/fallacy-detection")
async def fallacy_detection(request: FallacyDetectionRequest):
    """
    Detect fallacies in the provided text using a specified model.

    Args:
        request (FallacyDetectionRequest).

    Returns:
        dict: A dictionary with the detection result, including a unique ID,
              timestamp, model name, and a list of detected fallacies (if any),
              with details like type, validity, and context.
    """
    try:
        model = ModelEnum[request.model]
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Model '{request.model}' not found or not supported.",
                    "type": "model_not_found",
                    "param": "model",
                    "code": None,
                }
            },
        ) from exc

    fallacies = extract_json_from_string(instances(model, request.text, max_tokens=500))

    if not fallacies:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"The model '{request.model}' produced invalid content.",
                    "type": "model_error",
                    "param": None,
                    "code": None,
                }
            },
        )

    return {
        "id": f"fallacy-{random.randint(1000, 9999)}",
        "object": "fallacy_detection",
        "created": int(datetime.now().timestamp()),
        "model": request.model,
        "fallacies": fallacies["arguments"],
    }
