from pydantic import BaseModel
from typing import List

class AnalysisRequest(BaseModel):
    text: str

class Fallacy(BaseModel):
    type: str
    description: str

class AnalysisResponse(BaseModel):
    fallacies: List[Fallacy]