import json
import traceback
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from supabase import Client

from core.intent import get_direct_reply
from dependencies import get_current_user, get_supabase
from pipelines.retrieval.rag_chain import run_rag_stream
from schemas.chat import ChatMessageRequest, SessionCreate

router = APIRouter(prefix="/api/v1/projects", tags=["chat"])


def _verify_project_owner(supabase: Client, project_id: str, user_id: str):
    result = (
        supabase.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Proyek tidak ditemukan atau akses ditolak")


def _verify_session(supabase: Client, session_id: str, project_id: str):
    result = (
        supabase.table("chat_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("project_id", project_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Session tidak ditemukan")


# ── Session CRUD ─────────────────────────────────────────────────────────────


@router.post("/{project_id}/sessions")
async def create_session(
    project_id: str,
    body: SessionCreate = SessionCreate(),
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    _verify_project_owner(supabase, project_id, current_user.id)

    result = (
        supabase.table("chat_sessions")
        .insert(
            {
                "project_id": project_id,
                "user_id": current_user.id,
                "title": body.title,
            }
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(500, "Gagal membuat session")

    return result.data[0]


@router.get("/{project_id}/sessions")
async def list_sessions(
    project_id: str,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    _verify_project_owner(supabase, project_id, current_user.id)

    result = (
        supabase.table("chat_sessions")
        .select("id, title, created_at, updated_at")
        .eq("project_id", project_id)
        .eq("user_id", current_user.id)
        .order("updated_at", desc=True)
        .execute()
    )

    return {"sessions": result.data or []}


@router.get("/{project_id}/sessions/{session_id}/messages")
async def get_messages(
    project_id: str,
    session_id: str,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    _verify_project_owner(supabase, project_id, current_user.id)
    _verify_session(supabase, session_id, project_id)

    result = (
        supabase.table("chat_messages")
        .select("id, role, content, created_at")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )

    return {"messages": result.data or []}


@router.delete("/{project_id}/sessions/{session_id}")
async def delete_session(
    project_id: str,
    session_id: str,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """Hapus sebuah chat session beserta semua pesannya.

    Hapus child (chat_messages) DULU, baru parent (chat_sessions). FK
    `chat_messages.session_id` NOT NULL + ON DELETE SET NULL: menghapus session
    yang masih punya messages akan membuat Postgres mencoba set session_id=NULL
    → melanggar NOT NULL (error 23502, gejala Bug #8). Endpoint ini pakai
    service-role client (bypass RLS) sehingga delete-nya pasti terjadi — beda
    dengan delete langsung dari frontend (RLS) yang bisa diam-diam no-op lalu
    memicu error constraint saat session dihapus.
    """
    _verify_project_owner(supabase, project_id, current_user.id)
    _verify_session(supabase, session_id, project_id)

    supabase.table("chat_messages").delete().eq("session_id", session_id).execute()
    supabase.table("chat_sessions").delete().eq("id", session_id).execute()

    return {"message": "Session dihapus", "session_id": session_id}


# ── Chat SSE streaming ──────────────────────────────────────────────────────


@router.post("/{project_id}/sessions/{session_id}/chat")
async def chat_stream(
    project_id: str,
    session_id: str,
    body: ChatMessageRequest,
    current_user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    print(f"\n[CHAT] === Incoming request: project={project_id} session={session_id} ===", flush=True)
    print(f"[CHAT] message: {body.message!r}", flush=True)

    _verify_project_owner(supabase, project_id, current_user.id)
    _verify_session(supabase, session_id, project_id)

    # Intent ringan (heuristik, tanpa LLM): sapaan / pertanyaan kemampuan produk
    # / cara pakai fitur → jawab LANGSUNG tanpa RAG. None artinya perlu RAG penuh.
    direct_reply = get_direct_reply(body.message)

    # 1. Load chat history HANYA kalau perlu RAG (jawaban langsung tidak butuh
    #    history → lebih cepat). Wajib di-load SEBELUM simpan pesan user supaya
    #    history tidak ikut menyertakan pertanyaan yang baru saja dikirim.
    chat_history = []
    system_instruction = None
    if direct_reply is None:
        history_result = (
            supabase.table("chat_messages")
            .select("role, content")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        chat_history = history_result.data or []
        print(f"[CHAT] loaded {len(chat_history)} history messages", flush=True)

        # Instruksi khusus per-project (projects.master_prompt) yang ditetapkan
        # user saat membuat project → disuntikkan ke system prompt generator.
        try:
            proj = (
                supabase.table("projects")
                .select("master_prompt")
                .eq("id", project_id)
                .single()
                .execute()
            )
            system_instruction = (proj.data or {}).get("master_prompt")
            if system_instruction:
                print(f"[CHAT] project instruction aktif ({len(system_instruction)} char)", flush=True)
        except Exception as e:
            print(f"[CHAT] gagal load master_prompt (lanjut tanpa): {e}", flush=True)

    # 2. Save user message
    supabase.table("chat_messages").insert(
        {
            "project_id": project_id,
            "session_id": session_id,
            "role": "user",
            "content": body.message,
        }
    ).execute()
    print("[CHAT] user message saved to DB", flush=True)

    # 3. Stream response
    def generate():
        full_answer = ""

        # 3a. Jawaban LANGSUNG (sapaan / kemampuan produk / cara pakai fitur) →
        #     SKIP RAG (instan, tanpa retrieval/grading/generator). Pertanyaan
        #     substantif (hukum) tetap masuk RAG.
        if direct_reply is not None:
            print("[CHAT] direct-reply intent terdeteksi — skip RAG, jawab langsung", flush=True)
            full_answer = direct_reply
            yield f"data: {json.dumps({'type': 'token', 'data': full_answer}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'data': {'chunks_retrieved': 0, 'chunks_after_grading': 0, 'direct': True}}, ensure_ascii=False)}\n\n"
        else:
            event_count = 0
            print("[CHAT] >>> entering run_rag_stream loop", flush=True)
            try:
                for event in run_rag_stream(
                    query=body.message,
                    project_id=project_id,
                    chat_history=chat_history,
                    system_instruction=system_instruction,
                ):
                    event_count += 1
                    etype = event.get("type")
                    if etype == "token":
                        full_answer += event["data"]
                    else:
                        print(f"[CHAT] event #{event_count}: type={etype} data={event.get('data')!r}", flush=True)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as e:
                print("[CHAT] !!! EXCEPTION inside run_rag_stream:", flush=True)
                traceback.print_exc()
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
                    friendly = (
                        "⚠️ Batas penggunaan harian AI (Gemini free tier) sudah tercapai. "
                        "Layanan grading/jawaban memakai kuota gratis yang terbatas "
                        "(20 permintaan/hari). Silakan coba lagi nanti — kuota direset otomatis "
                        "setiap hari. (Optimasi batch grading sedang dalam pengerjaan tim.)"
                    )
                else:
                    friendly = f"⚠️ Terjadi kesalahan saat memproses jawaban: {msg}"
                yield f"data: {json.dumps({'type': 'error', 'data': friendly}, ensure_ascii=False)}\n\n"
                return

            print(f"[CHAT] <<< stream finished. {event_count} events, answer length={len(full_answer)}", flush=True)

        if not full_answer.strip():
            print("[CHAT] WARNING: full_answer is empty — nothing useful to save", flush=True)

        # 4. Save assistant message after stream completes
        try:
            supabase.table("chat_messages").insert(
                {
                    "project_id": project_id,
                    "session_id": session_id,
                    "role": "assistant",
                    "content": full_answer,
                }
            ).execute()
            print("[CHAT] assistant message saved to DB", flush=True)

            # 5. Update session timestamp
            supabase.table("chat_sessions").update(
                {"updated_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", session_id).execute()
            print("[CHAT] session timestamp updated. DONE.", flush=True)
        except Exception:
            print("[CHAT] !!! EXCEPTION while saving assistant message:", flush=True)
            traceback.print_exc()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
