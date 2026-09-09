from fastapi import APIRouter, HTTPException

from app.schemas import ConversationUpdate
from app.storage import database as db

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations() -> list[dict]:
    return db.list_conversations()


@router.post("", status_code=201)
async def create_conversation() -> dict:
    return db.create_conversation()


@router.get("/{conversation_id}")
async def get_conversation_detail(conversation_id: str) -> dict:
    conv = db.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    conv["messages"] = db.get_messages(conversation_id)
    return conv


@router.patch("/{conversation_id}")
async def rename_conversation(conversation_id: str, payload: ConversationUpdate) -> dict:
    updated = db.rename_conversation(conversation_id, payload.title.strip())
    if updated is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return updated


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    if not db.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
