from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ChatMessageRequest(BaseModel):
    message: str


class SessionCreate(BaseModel):
    title: str = "Obrolan Baru"


class MessageSource(BaseModel):
    id: str
    document_id: Optional[str] = None
    metadata: dict
    rrf_score: float
