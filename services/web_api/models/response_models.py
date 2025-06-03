# services/web_api/models/response_models.py
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class BeliefSetDetail(BaseModel):
    id: str
    logic_type: str
    content: str
    source_text: Optional[str] = None

class LogicBeliefSetResponse(BaseModel):
    success: bool
    belief_set: Optional[BeliefSetDetail] = None
    message: Optional[str] = None
    processing_time: Optional[float] = None

class QueryResultDetail(BaseModel):
    query: str
    result: Any
    formatted_result: Optional[str] = None
    explanation: Optional[str] = None

class LogicQueryResponse(BaseModel):
    success: bool
    belief_set_id: Optional[str] = None
    logic_type: Optional[str] = None
    result: Optional[QueryResultDetail] = None
    message: Optional[str] = None
    processing_time: Optional[float] = None

class LogicGenerateQueriesResponse(BaseModel):
    success: bool
    belief_set_id: Optional[str] = None
    logic_type: Optional[str] = None
    queries: Optional[List[str]] = None
    message: Optional[str] = None
    processing_time: Optional[float] = None