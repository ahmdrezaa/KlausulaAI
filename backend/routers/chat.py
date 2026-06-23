from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from typing import Optional
import uuid

from dependencies import get_current_user, get_supabase
from services.chat import ChatService
from schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/query")
async def chat_query(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Process a user query through the RAG pipeline
    Returns answer with sources
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # If project_id provided, verify ownership
    if request.project_id:
        project = supabase.table("projects")\
            .select("id")\
            .eq("id", request.project_id)\
            .eq("user_id", current_user.id)\
            .execute()
        
        if not project.data:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    try:
        chat_service = ChatService(supabase)
        
        # Run RAG pipeline
        rag_result = await chat_service.process_query(
            request.query,
            project_id=request.project_id
        )
        
        # Save user message
        await chat_service.save_message(
            project_id=request.project_id or "default",
            user_id=current_user.id,
            role="user",
            content=request.query
        )
        
        # Save assistant message with sources
        await chat_service.save_message(
            project_id=request.project_id or "default",
            user_id=current_user.id,
            role="assistant",
            content=rag_result["answer"],
            sources=rag_result.get("sources", [])
        )
        
        return ChatResponse(
            answer=rag_result["answer"],
            sources=rag_result.get("sources", []),
            chunks_retrieved=rag_result.get("chunks_retrieved", 0),
            chunks_after_grading=rag_result.get("chunks_after_grading", 0)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.get("/history")
async def get_chat_history(
    project_id: Optional[str] = None,
    limit: int = 50,
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Get chat history for a project
    """
    if not project_id:
        project_id = "default"
    
    try:
        chat_service = ChatService(supabase)
        messages = await chat_service.get_chat_history(project_id, limit=limit)
        
        return {
            "project_id": project_id,
            "messages": messages,
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.delete("/history")
async def clear_chat_history(
    project_id: Optional[str] = None,
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Clear chat history for a project
    """
    if not project_id:
        project_id = "default"
    
    try:
        chat_service = ChatService(supabase)
        await chat_service.clear_chat_history(project_id)
        
        return {"message": "Chat history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")
