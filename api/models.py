from pydantic import BaseModel
from typing import List, Dict

class AnalysisRequest(BaseModel):
    text: str

class Fallacy(BaseModel):
    type: str
    description: str

class AnalysisResponse(BaseModel):
    fallacies: List[Fallacy]
    analysis_id: str
    status: str
    metadata: Dict
    summary: str
class StatusResponse(BaseModel):
    status: str
    service_status: Dict

class Example(BaseModel):
    title: str
    text: str
    type: str

class ExampleResponse(BaseModel):
    examples: List[Example]