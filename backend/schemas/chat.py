from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MessageSource(BaseModel):
    id: str
    document_id: Optional[str] = None
    metadata: dict
    rrf_score: float


class ChatRequest(BaseModel):
    query: str
    project_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[MessageSource]
    chunks_retrieved: int
    chunks_after_grading: int


class Message(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[List[MessageSource]] = None
    created_at: datetime


class ChatHistory(BaseModel):
    messages: List[Message]
