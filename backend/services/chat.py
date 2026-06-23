import uuid
from datetime import datetime
from supabase import Client
from typing import Optional
from pipelines.retrieval.rag_chain import run_rag
from schemas.chat import Message, MessageSource


class ChatService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def process_query(
        self, 
        user_query: str, 
        project_id: Optional[str] = None
    ) -> dict:
        """
        Process a user query through the RAG pipeline
        Returns answer and sources
        """
        try:
            rag_result = run_rag(user_query, project_id=project_id)
            return rag_result
        except Exception as e:
            raise Exception(f"RAG pipeline error: {str(e)}")

    async def save_message(
        self,
        project_id: str,
        user_id: str,
        role: str,
        content: str,
        sources: Optional[list] = None
    ) -> Message:
        """Save a message to chat history"""
        message_id = str(uuid.uuid4())
        
        message_data = {
            "id": message_id,
            "project_id": project_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "created_at": datetime.utcnow().isoformat(),
        }
        
        result = self.supabase.table("chat_history").insert(message_data).execute()
        
        if result.data:
            return Message(**result.data[0])
        raise Exception("Failed to save message")

    async def get_chat_history(
        self, 
        project_id: str, 
        limit: int = 50
    ) -> list:
        """Get chat history for a project"""
        result = self.supabase.table("chat_history")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=False)\
            .limit(limit)\
            .execute()
        
        return result.data or []

    async def clear_chat_history(self, project_id: str) -> None:
        """Clear chat history for a project"""
        self.supabase.table("chat_history")\
            .delete()\
            .eq("project_id", project_id)\
            .execute()
