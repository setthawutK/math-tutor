from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    id: Optional[str]
    question: str
    wolfram_query: str
    wolfram_raw: Optional[str]
    images: List[str]
    llama_response: str
    gemini_response: str
    qwen_response: str
    created_at: Optional[datetime] = None

class VoteRequest(BaseModel):
    response_id: str
    voted_model: str
    comment: Optional[str] = None